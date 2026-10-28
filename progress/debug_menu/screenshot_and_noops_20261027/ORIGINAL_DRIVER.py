"""Root-owned immediate handoff for the two screenshot variables; Root supplies the candidate executable identity.

Invoke through reviewed Run.ps1 after Root staging. No game launch at import.
Every PowerShell child uses the absolute PowerShell 7 executable.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import time

P = Path(__file__).resolve().parent
R = Path('D:/Reverse/BP-Decomp_Workflow')
PWSH = 'C:/Program Files/PowerShell/7/pwsh.exe'
EXE = None


def load(path):
    return json.loads(path.read_text('utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-name', required=True)
    args = parser.parse_args()
    run = P / args.run_name
    assert not run.exists(), 'Fresh run directory required'
    assert all((P / name).is_file() for name in ('BINDING.json', 'STAGING.json', 'ROOT_PRELAUNCH_REVIEW.json'))
    binding = load(P / 'BINDING.json')
    EXE = binding.get('execution_exe_sha256')
    assert isinstance(EXE, str) and re.fullmatch(r'[0-9a-f]{64}', EXE), 'Root-reviewed executable identity is missing; no launch'
    slot = binding.get('slot')
    assert isinstance(slot, int) and 1 <= slot <= 65535, 'Root-selected fresh slot is missing; no launch'
    assert re.fullmatch(rf'run_debug_screenshot_{slot}_[0-9]{{8}}_[0-9]{{6}}', args.run_name), 'Run name does not bind the Root-selected slot'
    stage = load(P / 'STAGING.json')
    review = load(P / 'ROOT_PRELAUNCH_REVIEW.json')
    assert binding['status'] == 'root_reviewed_ready' and review['status'] == 'ready'
    assert stage['status'] == 'staged_not_launched' and binding['slot'] == stage['slot'] == slot
    assert binding['execution_exe_sha256'] == stage['execution_exe_sha256'] == EXE
    assert sha(Path(__file__)) == review['owner_driver_sha256'], 'Owned driver changed after Root review'
    assert sha(P / 'Run.ps1') == review['runner_sha256'] and sha(P / 'Case.ps1') == review['case_sha256']
    assert sha(P / 'CandidateArtifactGuard.ps1') == review['candidate_guard_sha256'], 'Candidate artifact guard changed after Root review'
    assert not any((P / name).exists() for name in ('ROOT_HANDOFF.json', 'ROOT_HANDOFF_RESULT.json', 'native-driver.console.log', 'trigger.console.log'))
    expected = (P / 'stage/slot/Burnout_PC.exe').resolve()
    assert sha(expected) == EXE, 'Staged executable differs'
    identity = None
    trigger_exit = None
    canonical_exit = None
    failure = None
    launched = time.monotonic()
    with (P / 'native-driver.console.log').open('xb') as output:
        command = [PWSH, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
            str(R / 'tools/tests/run_case.ps1'), '-Case', str(P / 'Case.ps1'),
            '-RunDir', str(run), '-GameDir', str(P / 'stage/slot'),
            '-WorkingDirectory', str(P / 'stage/data'), '-Slot', str(slot),
            '-LockTimeoutSec', '1', '-Label', 'Screenshot-two-control-current-candidate-owned-handoff']
        process = subprocess.Popen(command, cwd=R, stdout=output, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS)
        try:
            end = launched + 20
            match = None
            while time.monotonic() < end and process.poll() is None:
                text = (P / 'native-driver.console.log').read_text('utf8', errors='replace')
                match = re.search(r'OWNED_PROCESS pid=(\d+) image=(.*?) start=(\S+) priority=BelowNormal', text)
                if match:
                    break
                time.sleep(.05)
            if not match:
                raise RuntimeError('No canonical owned-process receipt before 20 s; no trigger sent')
            if Path(match[2]).resolve() != expected:
                raise RuntimeError('Canonical image differs; no trigger sent')
            identity = {'pid': int(match[1]), 'image': str(expected), 'start_utc': match[3],
                        'slot': slot, 'canonical_launcher_pid': process.pid}
            save(P / 'ROOT_HANDOFF.json', identity)
            context = load(run / 'ROOT_TRIGGER_CONTEXT.json')
            assert context['slot'] == slot and Path(context['image']).resolve() == expected and context['exe_sha256'] == EXE
            fixed = {'game_log': P / 'stage/slot/BrnGame.log', 'flow_log': run / 'flow_run.console.log',
                     'out_dir': run, 'working_directory': P / 'stage/data', 'frame_dir': run / 'frames',
                     'plan_path': run / 'CASE_PLAN.used.json', 'binding_path': run / 'runtime-binding.used.json'}
            assert all(Path(context[key]).resolve() == value.resolve() for key, value in fixed.items()), 'Trigger context escaped exact private paths'
            assert context['run_relative_path'] in ('../../' + args.run_name, '../../' + args.run_name + '/'), 'Unexpected private relative run path'
            assert sha(run / 'CASE_PLAN.used.json') == sha(P / 'CASE_PLAN.json')
            assert sha(run / 'runtime-binding.used.json') == sha(P / 'BINDING.json')
            assert sha(P / 'ScreenshotKeys.proposed.ps1') == review['helper_sha256']
            trigger_command = [PWSH, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(P / 'ScreenshotKeys.proposed.ps1'),
                '-GameLog', context['game_log'], '-FlowLog', context['flow_log'], '-OutDir', context['out_dir'],
                '-WorkingDirectory', context['working_directory'], '-FrameDir', context['frame_dir'],
                '-PlanPath', context['plan_path'], '-BindingPath', context['binding_path'],
                '-RunRelativePath', context['run_relative_path'], '-Slot', str(slot),
                '-ExpectedImage', str(expected), '-ExpectedExeSha256', EXE,
                '-StartedAfterUtc', context['started_after_utc'], '-ExpectedPid', match[1],
                '-ExpectedStartUtc', match[3], '-TimeoutSec', '410']
            with (P / 'trigger.console.log').open('xb') as trigger_output:
                trigger = subprocess.run(trigger_command, cwd=R, stdout=trigger_output, stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS, timeout=415)
            trigger_exit = trigger.returncode
        except BaseException as error:
            failure = type(error).__name__ + ': ' + str(error)
        finally:
            # Canonical flow owns the real game creation handle and bounded
            # cleanup. Always join it after a helper failure. Never send a
            # global key, kill a launcher, or adopt/terminate another game.
            try:
                canonical_exit = process.wait(timeout=max(1.0, launched + 450 - time.monotonic()))
            except subprocess.TimeoutExpired:
                failure = (failure + '; ' if failure else '') + 'Canonical launcher did not terminate within 450 s; cleanup is unconfirmed and acceptance is blocked'
        receipt = {'canonical_exit': canonical_exit, 'trigger_exit': trigger_exit, 'identity': identity,
                   'run_dir': str(run), 'source': binding['candidate_source'], 'workflow': binding['candidate_workflow_source'],
                   'exe_sha256': EXE, 'powershell': PWSH, 'error': failure,
                   'canonical_join_confirmed': canonical_exit is not None, 'elapsed_seconds': time.monotonic() - launched}
        save(P / 'ROOT_HANDOFF_RESULT.json', receipt)
        print(json.dumps(receipt))
        return 0 if failure is None and canonical_exit == trigger_exit == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
