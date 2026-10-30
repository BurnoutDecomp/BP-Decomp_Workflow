from pathlib import Path
import hashlib, importlib.util, json, os, subprocess, tempfile

OUT = Path(__file__).resolve().parent
CAMPAIGN = OUT.parent
WF = CAMPAIGN.parents[2]
B5 = WF / 'b5-decomp'
PRIVATE = '15ab04aa074ae0a793a238d4cb74fc0a76f03703'
PRIVATE_WF = '33f81109004088250e596bd8ae75c311796dcf65'
PUBLIC = 'd85e2d5e2526783406d69fedc0ab17b219eb69bc'
PUBLIC_WF = 'a0123c9c5f9f10de3551014af519ea4ea5a7d365'
F1 = 'f1d1a5ebce785cfe2dc5315b2b3292d95983e6b8'
TRAILER = 'Co-Authored-By: Codex GPT-6.1 Sol <noreply@openai.com>'

def run(repo, *args, env=None, data=None, required=True):
    p = subprocess.run(['git', '-C', str(repo), *args], env=env, input=data, capture_output=True)
    if required and p.returncode:
        raise RuntimeError(str(args) + ': ' + p.stderr.decode('utf-8', errors='replace'))
    return p

def git(repo, *args, env=None, data=None):
    return run(repo, *args, env=env, data=data).stdout

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def put(repo, env, path, raw):
    oid = git(repo, 'hash-object', '-w', '--stdin', data=raw).decode().strip()
    git(repo, 'update-index', '--add', '--cacheinfo', '100644,' + oid + ',' + path, env=env)

def main():
    assert not (OUT / 'CHECKPOINT_OBJECTS.json').exists()
    merged = run(B5, 'merge-tree', '--write-tree', '--messages', '--name-only', PRIVATE, PUBLIC)
    source_tree = merged.stdout.decode().splitlines()[0]
    private_paths = git(B5, 'diff', '--name-only', F1, PRIVATE).decode().splitlines()
    retained, changed = [], []
    for path in private_paths:
        before = git(B5, 'show', PRIVATE + ':' + path)
        after = git(B5, 'show', source_tree + ':' + path)
        (retained if before == after else changed).append(path)
    traffic = 'src/GameSource/World/EntityModules/TrafficEntityModule/BrnTrafficEntityModule.cpp'
    assert changed == [traffic], changed
    video = 'src/GameSource/Gui/BrnGuiVideoEvents.h'
    video_raw = git(B5, 'show', PUBLIC + ':' + video)
    assert git(B5, 'show', source_tree + ':' + video) == video_raw
    spec = importlib.util.spec_from_file_location('frame_contract', CAMPAIGN / 'check_contract.py')
    contract = importlib.util.module_from_spec(spec); spec.loader.exec_module(contract)
    private_functions = contract.functions(git(B5, 'show', PRIVATE + ':' + traffic).decode())
    public_functions = contract.functions(git(B5, 'show', PUBLIC + ':' + traffic).decode())
    merged_raw = git(B5, 'show', source_tree + ':' + traffic)
    merged_functions = contract.functions(merged_raw.decode())
    for name in ['Construct', 'EnterReplay', 'LeaveReplay', 'UpdateSerialiser']:
        assert merged_functions[name]['body'] == private_functions[name]['body'], name
    for name in ['UpdateParams_TryToReinsertParam', 'Pressure_PickSplitToTake', 'HandleExternalResponses']:
        assert merged_functions[name]['body'] == public_functions[name]['body'], name
    reset = '    // ARTIST 8274AA74: reset before the divergence banner and all state branches.\n    muNumTrafficInsertionsThisFrame = 0;\n\n'
    assert merged_functions['PreSceneUpdate']['body'].count(reset) == 1
    assert merged_functions['PreSceneUpdate']['body'].replace(reset, '', 1) == private_functions['PreSceneUpdate']['body']
    receipt = {'source_private_parent': PRIVATE, 'source_public_parent': PUBLIC, 'source_tree': source_tree,
        'source_merge_had_conflicts': False, 'private_changed_paths': len(private_paths),
        'private_blobs_retained_exactly': retained, 'private_blob_with_disjoint_public_additions': changed,
        'startup_video_path': video, 'startup_video_exact_public_sha256': sha(video_raw),
        'private_and_public_traffic_methods_preserved': True, 'pre_scene_only_public_insertion_reset_added': True,
        'normal_install_changed': False, 'public_refs_changed': False, 'whole_link': 'pending', 'native_replay': 'pending'}
    (OUT / 'RECONCILIATION_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    dest = OUT / 'merged_overlap' / traffic
    dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(merged_raw)
    message = ('Reconcile playable public fixes into private Replay candidate\n\n'
        'Preserve the complete reviewed private Replay prefix and merge the current playable public source. '
        'Retain the exact startup video event wrapper and disjoint Traffic fixes without replacing public files wholesale.\n\n'
        'The merge has no textual conflicts; whole private linking and native Replay evidence remain pending.\n\n' + TRAILER + '\n')
    source_commit = git(B5, 'commit-tree', source_tree, '-p', PRIVATE, '-p', PUBLIC, data=message.encode()).decode().strip()
    wfmerge = run(WF, 'merge-tree', '--write-tree', '--messages', '--name-only', PRIVATE_WF, PUBLIC_WF, required=False)
    lines = wfmerge.stdout.decode().splitlines(); workflow_tree_initial = lines[0]
    conflicts = []
    if wfmerge.returncode:
        for line in lines[1:]:
            if not line: break
            conflicts.append(line)
        assert conflicts == ['b5-decomp'], lines
    with tempfile.TemporaryDirectory(prefix='replay_playable_reconcile_') as directory:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(directory) / 'workflow.index'))
        git(WF, 'read-tree', workflow_tree_initial, env=env)
        git(WF, 'update-index', '--add', '--cacheinfo', '160000,' + source_commit + ',b5-decomp', env=env)
        prefix = OUT.relative_to(WF).as_posix()
        for name in ['reconcile.py', 'RECONCILIATION_RECEIPT.json']:
            put(WF, env, prefix + '/' + name, (OUT / name).read_bytes())
        tree = git(WF, 'write-tree', env=env).decode().strip()
        message = ('Checkpoint playable-baseline reconciliation for private Replay\n\n'
            'Retain both the approved private Replay provider roster and current public build fixes. '
            'Resolve only the paired submodule pointer to their source merge; normal/public refs remain unchanged.\n\n' + TRAILER + '\n')
        workflow_commit = git(WF, 'commit-tree', tree, '-p', PRIVATE_WF, '-p', PUBLIC_WF, data=message.encode()).decode().strip()
    for repo, before, public, after in [(B5, PRIVATE, PUBLIC, source_commit), (WF, PRIVATE_WF, PUBLIC_WF, workflow_commit)]:
        git(repo, 'merge-base', '--is-ancestor', before, after)
        git(repo, 'merge-base', '--is-ancestor', public, after)
        assert git(repo, 'show', '-s', '--format=%B', after).decode().strip().endswith(TRAILER)
    record = {'source_base': PRIVATE, 'source_public_parent': PUBLIC, 'source_commit': source_commit,
        'source_tree': source_tree, 'workflow_base': PRIVATE_WF, 'workflow_public_parent': PUBLIC_WF,
        'workflow_commit': workflow_commit, 'workflow_tree': tree, 'source_reconciliation': 'no conflicts',
        'workflow_conflicts_resolved': conflicts, 'source_prefix_preserved': True,
        'exact_public_startup_video_header_retained': True, 'whole_link': 'pending', 'native_replay': 'pending',
        'normal_install_changed': False, 'public_refs_changed': False, 'refs_updated': False, 'trailer_verified': TRAILER}
    (OUT / 'CHECKPOINT_OBJECTS.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(record, indent=2))

if __name__ == '__main__':
    main()
