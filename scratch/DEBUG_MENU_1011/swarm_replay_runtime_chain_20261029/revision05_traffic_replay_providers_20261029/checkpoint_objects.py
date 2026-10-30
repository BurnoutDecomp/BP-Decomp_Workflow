from pathlib import Path
import hashlib, json, os, subprocess, tempfile

OUT = Path(__file__).resolve().parent
WF = OUT.parent.parents[2]
B5 = WF / 'b5-decomp'
TRAILER = 'Co-Authored-By: Codex GPT-6.1 Sol <noreply@openai.com>'

def git(repo, *args, env=None, data=None):
    p = subprocess.run(['git', '-C', str(repo), *args], env=env, input=data, capture_output=True)
    if p.returncode: raise RuntimeError(str(args) + ': ' + p.stderr.decode('utf-8', errors='replace'))
    return p.stdout.decode('utf-8').strip()

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def put(repo, env, path, raw):
    oid = git(repo, 'hash-object', '-w', '--stdin', data=raw)
    git(repo, 'update-index', '--add', '--cacheinfo', '100644,' + oid + ',' + path, env=env)

def main():
    assert not (OUT / 'CHECKPOINT_OBJECTS.json').exists()
    source = json.loads((OUT / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    patch = json.loads((OUT / 'PATCH_CHECKS.json').read_text(encoding='utf-8'))
    mount = json.loads((OUT / 'WORKFLOW_SOURCE_MOUNT.json').read_text(encoding='utf-8'))
    review = json.loads((OUT / 'FRESH_REVIEW.json').read_text(encoding='utf-8'))
    assert review['verdict'] == 'pass' and review['required_mount_review']['verdict'] == 'pass'
    assert sha(OUT / 'workflow_source_mount.patch') == review['required_mount_review']['patch_sha256']
    for component in source['components']:
        assert sha(Path(component['seal'])) == component['seal_sha256']
    gate_path = OUT.parent / 'immutable_gates/v5_composed_GameModule/RESULT.json'
    gate = json.loads(gate_path.read_text(encoding='utf-8'))
    assert gate['passed'] and gate['repository_header_drift'] == []
    with tempfile.TemporaryDirectory(prefix='traffic_v5_checkpoint_') as directory:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(directory) / 'b5.index'))
        git(B5, 'read-tree', source['base'], env=env)
        for row in source['files']:
            path = Path(row['source'])
            assert sha(path) == row['after_sha256']
            put(B5, env, row['path'], path.read_bytes())
        tree = git(B5, 'write-tree', env=env)
        assert tree == patch['source_tree']
        message = ('Restore original Traffic replay production and rendering\n\n'
            'Recover the typed Traffic producer, stream codec and recorded render consumers. '
            'Reset playback asset readiness at the original EnterReplay store.\n\n'
            'The same independent reviewer approves the exact producer successor and renderer. '
            'Actual TU and semantic controls pass; native linking/playback remain pending.\n\n' + TRAILER + '\n')
        commit = git(B5, 'commit-tree', tree, '-p', source['base'], data=message.encode())
        changed = git(B5, 'diff-tree', '--no-commit-id', '--name-only', '-r', commit).splitlines()
        assert sorted(changed) == sorted(row['path'] for row in source['files']) and len(changed) == 10
        record = {'source_base': source['base'], 'source_commit': commit, 'source_tree': tree,
            'workflow_base': source['workflow_base'], 'source_paths': len(changed),
            'source_manifest_sha256': sha(OUT / 'SOURCE_MANIFEST.json'),
            'fresh_review_sha256': sha(OUT / 'FRESH_REVIEW.json'), 'source_review': 'pass',
            'composed_actual_tu_pass': True, 'whole_link': 'pending', 'native_replay': 'pending',
            'site_or_count_credit': False, 'normal_install_changed': False,
            'shared_checkout_changed': False, 'private_index_only': True}
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(directory) / 'workflow.index'))
        git(WF, 'read-tree', source['workflow_base'], env=env)
        path = OUT / 'workflow_postimage' / mount['path']
        assert sha(path) == mount['postimage_crlf_sha256']
        raw = path.read_bytes().replace(b'\r\n', b'\n')
        assert hashlib.sha256(raw).hexdigest() == mount['after_lf_sha256']
        put(WF, env, mount['path'], raw)
        git(WF, 'update-index', '--add', '--cacheinfo', '160000,' + commit + ',b5-decomp', env=env)
        prefix = OUT.relative_to(WF).as_posix()
        for name in ['SOURCE_MANIFEST.json', 'combined_source.patch', 'PATCH_CHECKS.json',
                'WORKFLOW_SOURCE_MOUNT.json', 'workflow_source_mount.patch', 'SOURCE_MOUNT_CLOSURE.json',
                'FRESH_REVIEW.json', 'README.md', 'compose.py', 'checkpoint_objects.py']:
            put(WF, env, prefix + '/' + name, (OUT / name).read_bytes())
        packets = {'original_producer': 'TRAFFIC_PRODUCER_PACKET.md',
            'ready_reset_successor': 'REVIEW_PACKET.md', 'renderer': 'TRAFFIC_RENDERER_PACKET.md'}
        for component in source['components']:
            root = Path(component['root'])
            dest = prefix + '/components/' + component['component']
            for name in ['SEAL.json', packets[component['component']]]:
                put(WF, env, dest + '/' + name, (root / name).read_bytes())
        put(WF, env, prefix + '/COMPOSED_GAME_MODULE_GATE.json', gate_path.read_bytes())
        put(WF, env, prefix + '/CHECKPOINT.json', (json.dumps(record, indent=2) + '\n').encode())
        workflow_tree = git(WF, 'write-tree', env=env)
        message = ('Checkpoint approved Traffic replay provider continuation\n\n'
            'Pin the reviewed10-path Traffic continuation and mount both real stream providers. '
            'Preserve the earlier private Replay prefix and keep native/site credit pending.\n\n' + TRAILER + '\n')
        workflow_commit = git(WF, 'commit-tree', workflow_tree, '-p', source['workflow_base'], data=message.encode())
        assert git(WF, 'ls-tree', workflow_commit, 'b5-decomp').split()[2] == commit
        for repo, revision in [(B5, commit), (WF, workflow_commit)]:
            assert git(repo, 'show', '-s', '--format=%B', revision).endswith(TRAILER)
        record.update({'workflow_commit': workflow_commit, 'workflow_tree': workflow_tree,
            'trailer_verified': TRAILER, 'refs_updated': False})
        (OUT / 'CHECKPOINT_OBJECTS.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(record, indent=2))

if __name__ == '__main__':
    main()
