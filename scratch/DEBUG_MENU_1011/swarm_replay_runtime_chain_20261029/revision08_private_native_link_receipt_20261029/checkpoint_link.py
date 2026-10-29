from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, os, subprocess, tempfile

OUT = Path(__file__).resolve().parent
CAMPAIGN = OUT.parent
WF = CAMPAIGN.parents[2]
BUILD = CAMPAIGN / 'revision06_public_playable_reconcile_20261029'
SOURCE = '22e673523a69a7a710d53a2bbba61efa0824700c'
WFBASE = '7a07483b07bec58bd52d59ec63024bd347fde28d'
TRAILER = 'Co-Authored-By: Codex GPT-6.1 Sol <noreply@openai.com>'

def sha(raw): return hashlib.sha256(raw).hexdigest()

def git(*args, env=None, data=None):
    p = subprocess.run(['git', '-C', str(WF), *args], env=env, input=data, capture_output=True)
    if p.returncode: raise RuntimeError(str(args) + ': ' + p.stderr.decode('utf-8', errors='replace'))
    return p.stdout.decode('utf-8').strip()

def put(env, path, raw):
    obj = git('hash-object', '-w', '--stdin', data=raw)
    git('update-index', '--add', '--cacheinfo', '100644,' + obj + ',' + path, env=env)

def main():
    assert not (OUT / 'CHECKPOINT_OBJECTS.json').exists()
    result_path = BUILD / 'NATIVE_BUILD_22e673523a_RESULT.json'
    result = json.loads(result_path.read_text(encoding='utf-8'))
    assert result['passed'] and result['returncode'] == 0
    assert result['source_commit'] == SOURCE and result['workflow_commit'] == WFBASE
    assert result['source_input_drift'] == [] and result['external_link_package_drift'] == []
    assert not any(result['git_statuses'].values())
    exe = Path(result['exe']); output = exe.parent
    assert sha(exe.read_bytes()) == result['exe_sha256']
    provenance = json.loads((output / 'Burnout_PC.exe.provenance.json').read_text(encoding='utf-8'))
    assert provenance['b5_head'] == SOURCE and provenance['parent_head'] == WFBASE
    assert provenance['exe_sha256'] == result['exe_sha256']
    assert not provenance['b5_dirty'] and not provenance['parent_dirty']
    log_path = Path(result['log']); log = log_path.read_text(encoding='utf-8')
    assert 'compile: 3019 TUs -- 44 compiled, 2975 up to date, 0 failed' in log
    assert 'link:    ok ->' in log and 'errors:  none' in log
    metadata_path = BUILD / 'NATIVE_SOURCE_ROOT.json'
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    source_root = Path(metadata['source_root'])
    linked_rows = [row for row in metadata['source_files'] if row['materialization'] == 'hardlink_to_verified_immutable_f1_blob']
    delta_rows = [row for row in metadata['source_files'] if row not in linked_rows]
    metadata['hardlinked_immutable_source_files'] = len(linked_rows)
    metadata['new_candidate_files'] = len(delta_rows)
    metadata['new_candidate_bytes'] = sum((source_root / row['path']).stat().st_size for row in delta_rows)
    metadata_path.write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    artifacts = []
    for name in ['Burnout_PC.exe', 'Burnout_PC.map', 'Burnout_PC.cgsmap', 'Burnout_PC.exe.provenance.json']:
        path = output / name
        assert path.exists(), name
        artifacts.append({'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())})
    receipt = {'recorded_utc': datetime.now(timezone.utc).isoformat(), 'whole_link': 'pass',
        'built_source_commit': SOURCE, 'built_workflow_commit': WFBASE,
        'full_compile_attempt': {'source': '65f58d20c63dda8f351f672b5b9fc0d30f8a7af1', 'tus': 3018,
            'compile_failures': 0, 'initial_unresolved_symbols': 7},
        'final_incremental_compile': {'source_tus': 3019, 'compiled': 44, 'unchanged_valid_cache': 2975,
            'compile_failures': 0, 'warnings_in_final_increment': 0, 'link_errors': 0},
        'exe': str(exe), 'exe_sha256': result['exe_sha256'], 'artifacts': artifacts,
        'source_input_drift': [], 'external_link_package_drift': [], 'git_statuses': result['git_statuses'],
        'immutable_source_hardlinks': len(linked_rows), 'candidate_delta_files': len(delta_rows),
        'candidate_delta_bytes': metadata['new_candidate_bytes'], 'assets_or_idbs_copied': False,
        'normal_install_changed': False, 'public_refs_changed': False, 'game_launched': False,
        'global_input_used': False, 'recording_playback_runtime': 'pending',
        'visual_audible_parity': 'pending', 'menu_site_or_count_credit': False,
        'startup_video_header_retained_from_public': 'd85e2d5e2526783406d69fedc0ab17b219eb69bc'}
    (OUT / 'NATIVE_LINK_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    (OUT / 'NATIVE_BUILD_RESULT.json').write_bytes(result_path.read_bytes())
    (OUT / 'BUILD_PROVENANCE.json').write_bytes((output / 'Burnout_PC.exe.provenance.json').read_bytes())
    (OUT / 'NATIVE_SOURCE_ROOT.json').write_bytes(metadata_path.read_bytes())
    (OUT / 'FINAL_BUILD.log').write_bytes(log_path.read_bytes())
    (OUT / 'FULL_COMPILE_INITIAL_LINK.log').write_bytes((log_path.parent / 'BUILD.log').read_bytes())
    seal_names = ['NATIVE_LINK_RECEIPT.json', 'NATIVE_BUILD_RESULT.json', 'BUILD_PROVENANCE.json',
        'NATIVE_SOURCE_ROOT.json', 'FINAL_BUILD.log', 'FULL_COMPILE_INITIAL_LINK.log', 'checkpoint_link.py']
    seal = {name: sha((OUT / name).read_bytes()) for name in seal_names}
    (OUT / 'SEAL.json').write_text(json.dumps(seal, indent=2) + '\n', encoding='utf-8')
    with tempfile.TemporaryDirectory(prefix='replay_link_receipt_checkpoint_') as directory:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(directory) / 'workflow.index'))
        git('read-tree', WFBASE, env=env)
        prefix = OUT.relative_to(WF).as_posix()
        for name in seal_names + ['SEAL.json']:
            put(env, prefix + '/' + name, (OUT / name).read_bytes())
        tree = git('write-tree', env=env)
        message = ('Record successful private Replay native link evidence\n\n'
            'Pin the clean22e67352 candidate executable hash, canonical3019-TU link result, source/package proof and prior failure closure. '
            'This metadata-only checkpoint changes no source or build inputs.\n\n'
            'The game has not been launched; recording/playback, visual/audio and menu-site evidence remain pending.\n\n' + TRAILER + '\n')
        commit = git('commit-tree', tree, '-p', WFBASE, data=message.encode())
        changed = git('diff-tree', '--no-commit-id', '--name-only', '-r', commit).splitlines()
        assert all(path.startswith(prefix + '/') for path in changed)
        assert git('ls-tree', commit, 'b5-decomp').split()[2] == SOURCE
        assert git('show', '-s', '--format=%B', commit).endswith(TRAILER)
    record = {'source_base': SOURCE, 'source_commit': SOURCE, 'source_unchanged': True,
        'workflow_base': WFBASE, 'workflow_commit': commit, 'workflow_tree': tree,
        'workflow_metadata_only': True, 'built_workflow_commit': WFBASE,
        'whole_link': 'pass', 'exe_sha256': result['exe_sha256'], 'native_game_run': False,
        'menu_site_or_count_credit': False, 'normal_install_changed': False,
        'trailer_verified': TRAILER, 'refs_updated': False}
    (OUT / 'CHECKPOINT_OBJECTS.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(record, indent=2))

if __name__ == '__main__': main()
