from pathlib import Path
import hashlib, json, os, subprocess, tempfile

OUT = Path(__file__).resolve().parent
WF = OUT.parent.parents[2]
B5 = WF / 'b5-decomp'
TRAILER = 'Co-Authored-By: Codex GPT-6.1 Sol <noreply@openai.com>'

def git(repo, *args, env=None, data=None):
    result = subprocess.run(['git', '-C', str(repo), *args], env=env, input=data, capture_output=True)
    if result.returncode:
        raise RuntimeError(str(args) + ': ' + result.stderr.decode('utf-8', errors='replace'))
    return result.stdout.decode('utf-8').strip()

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def put(repo, env, path, raw, mode='100644'):
    blob = git(repo, 'hash-object', '-w', '--stdin', data=raw)
    git(repo, 'update-index', '--add', '--cacheinfo', mode + ',' + blob + ',' + path, env=env)

def main():
    assert not (OUT / 'CHECKPOINT_OBJECTS.json').exists()
    source = json.loads((OUT / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    check = json.loads((OUT / 'PATCH_CHECKS.json').read_text(encoding='utf-8'))
    mount = json.loads((OUT / 'WORKFLOW_SOURCE_MOUNT.json').read_text(encoding='utf-8'))
    review = json.loads((OUT / 'FRESH_REVIEW.json').read_text(encoding='utf-8'))
    assert check['passed'] and review['verdict'] == 'pass'
    for component in source['components']:
        assert component['seal_sha256'] == review['approved_seals'][component['component']]
        assert sha(Path(component['seal'])) == component['seal_sha256']
    gate = OUT.parent / 'immutable_gates/v4_composed_GameModule/RESULT.json'
    gate_json = json.loads(gate.read_text(encoding='utf-8'))
    assert gate_json['passed'] and gate_json['repository_header_drift'] == []
    with tempfile.TemporaryDirectory(prefix='replay_v4_checkpoint_') as directory:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(directory) / 'b5.index'))
        git(B5, 'read-tree', source['base'], env=env)
        for row in source['files']:
            path = Path(row['source'])
            assert sha(path) == row['after_sha256']
            put(B5, env, row['path'], path.read_bytes())
        tree = git(B5, 'write-tree', env=env)
        assert tree == check['source_tree']
        message = ('Restore original Replay producers and frame lifetimes\n\n'
            'Retain the Director input across frame phases and restore its recorded bridge state. '
            'Recover typed World status, RaceCar channel production and the original Sound stream contract.\n\n'
            'Four unchanged source leaves passed the single independent batch review and component controls. '
            'Native linking and playback remain pending; Traffic continuation is separate.\n\n' + TRAILER + '\n')
        commit = git(B5, 'commit-tree', tree, '-p', source['base'], data=message.encode('utf-8'))
        changed = git(B5, 'diff-tree', '--no-commit-id', '--name-only', '-r', commit).splitlines()
        assert sorted(changed) == sorted(row['path'] for row in source['files'])
        record = {'source_base': source['base'], 'source_commit': commit, 'source_tree': tree,
            'workflow_base': source['workflow_base'], 'source_paths': len(changed),
            'source_manifest_sha256': sha(OUT / 'SOURCE_MANIFEST.json'),
            'fresh_review_sha256': sha(OUT / 'FRESH_REVIEW.json'), 'source_review': 'pass',
            'composed_actual_tu_pass': True, 'whole_link': 'pending', 'native_replay': 'pending',
            'site_or_count_credit': False, 'normal_install_changed': False,
            'shared_checkout_changed': False, 'private_index_only': True}
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(directory) / 'workflow.index'))
        git(WF, 'read-tree', source['workflow_base'], env=env)
        mount_path = OUT / 'workflow_postimage' / mount['path']
        assert sha(mount_path) == mount['postimage_crlf_sha256']
        mount_lf = mount_path.read_bytes().replace(b'\r\n', b'\n')
        assert hashlib.sha256(mount_lf).hexdigest() == mount['after_lf_sha256']
        put(WF, env, mount['path'], mount_lf)
        git(WF, 'update-index', '--add', '--cacheinfo', '160000,' + commit + ',b5-decomp', env=env)
        prefix = OUT.relative_to(WF).as_posix()
        artifacts = ['SOURCE_MANIFEST.json', 'combined_source.patch', 'PATCH_CHECKS.json',
            'WORKFLOW_SOURCE_MOUNT.json', 'workflow_source_mount.patch', 'SOURCE_MOUNT_CLOSURE.json',
            'FRESH_REVIEW.json', 'README.md', 'compose.py', 'checkpoint_objects.py']
        for relative in artifacts:
            put(WF, env, prefix + '/' + relative, (OUT / relative).read_bytes())
        for component in source['components']:
            root = Path(component['root'])
            dest = prefix + '/components/' + component['component']
            for name in ['SOURCE_MANIFEST.json', Path(component['seal']).name, 'REVIEWER_PACKET.md']:
                path = root / name
                assert path.exists(), str(path)
                put(WF, env, dest + '/' + name, path.read_bytes())
        put(WF, env, prefix + '/COMPOSED_GAME_MODULE_GATE.json', gate.read_bytes())
        put(WF, env, prefix + '/CHECKPOINT.json', (json.dumps(record, indent=2) + '\n').encode())
        workflow_tree = git(WF, 'write-tree', env=env)
        message = ('Checkpoint reviewed Replay provider continuation\n\n'
            'Pin the reviewed24-path continuation and mount its real RaceCar serialiser provider. '
            'Keep the previous private prefix and preserve pending native/site status.\n\n' + TRAILER + '\n')
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
