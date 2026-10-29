from pathlib import Path
import hashlib, json, os, subprocess, tempfile

OUT = Path(__file__).resolve().parent
WF = OUT.parent.parents[2]
B5 = WF / 'b5-decomp'
TRAILER = 'Co-Authored-By: Codex GPT-6.1 Sol <noreply@openai.com>'

def sha(raw): return hashlib.sha256(raw).hexdigest()

def git(repo, *args, env=None, data=None):
    p = subprocess.run(['git', '-C', str(repo), *args], env=env, input=data, capture_output=True)
    if p.returncode: raise RuntimeError(str(args) + ': ' + p.stderr.decode('utf-8', errors='replace'))
    return p.stdout.decode('utf-8').strip()

def put(repo, env, path, raw):
    oid = git(repo, 'hash-object', '-w', '--stdin', data=raw)
    git(repo, 'update-index', '--add', '--cacheinfo', '100644,' + oid + ',' + path, env=env)

def main():
    assert not (OUT / 'CHECKPOINT_OBJECTS.json').exists()
    manifest = json.loads((OUT / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    checks = json.loads((OUT / 'PATCH_CHECKS.json').read_text(encoding='utf-8'))
    mount = json.loads((OUT / 'WORKFLOW_SOURCE_MOUNT.json').read_text(encoding='utf-8'))
    review = json.loads((OUT / 'FRESH_REVIEW.json').read_text(encoding='utf-8'))
    assert checks['passed'] and review['verdict'] == 'pass'
    assert sha((OUT / 'workflow_source_mount.patch').read_bytes()) == review['mount_patch_sha256']
    for component in manifest['components']:
        assert sha(Path(component['seal']).read_bytes()) == review['approved_seals'][component['component']]
    with tempfile.TemporaryDirectory(prefix='native_link_closure_checkpoint_') as directory:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(directory) / 'b5.index'))
        git(B5, 'read-tree', manifest['base'], env=env)
        for row in manifest['files']:
            raw = Path(row['source']).read_bytes(); assert sha(raw) == row['after_sha256']
            put(B5, env, row['path'], raw)
        tree = git(B5, 'write-tree', env=env); assert tree == checks['source_tree']
        message = ('Close native Director and RaceCar replay provider linkage\n\n'
            'Use the canonical IOBufferStack struct tag across Director declarations and callers. '
            'Supply the original typed48-byte WorldMap copy in the existing RaceCar output provider.\n\n'
            'The same independent reviewer approves both bounded successors; actual native object link controls isolate all four affected symbols. '
            'Integrated link and gameplay remain pending.\n\n' + TRAILER + '\n')
        commit = git(B5, 'commit-tree', tree, '-p', manifest['base'], data=message.encode())
        names = git(B5, 'diff-tree', '--no-commit-id', '--name-only', '-r', commit).splitlines()
        assert sorted(names) == sorted(row['path'] for row in manifest['files'])
        record = {'source_base': manifest['base'], 'source_commit': commit, 'source_tree': tree,
            'workflow_base': manifest['workflow_base'], 'source_paths': len(names), 'source_review': 'pass',
            'source_manifest_sha256': sha((OUT / 'SOURCE_MANIFEST.json').read_bytes()),
            'fresh_review_sha256': sha((OUT / 'FRESH_REVIEW.json').read_bytes()),
            'whole_link': 'pending', 'native_game_run': False, 'site_or_count_credit': False,
            'normal_install_changed': False, 'shared_checkout_changed': False}
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(directory) / 'workflow.index'))
        git(WF, 'read-tree', manifest['workflow_base'], env=env)
        raw = (OUT / 'workflow_postimage' / mount['path']).read_bytes().replace(b'\r\n', b'\n')
        assert sha(raw) == mount['after_lf_sha256']; put(WF, env, mount['path'], raw)
        git(WF, 'update-index', '--add', '--cacheinfo', '160000,' + commit + ',b5-decomp', env=env)
        prefix = OUT.relative_to(WF).as_posix()
        for name in ['SOURCE_MANIFEST.json', 'combined_source.patch', 'PATCH_CHECKS.json',
            'WORKFLOW_SOURCE_MOUNT.json', 'workflow_source_mount.patch', 'REVIEWER_PACKET.md',
            'FRESH_REVIEW.json', 'compose.py', 'checkpoint_objects.py']:
            put(WF, env, prefix + '/' + name, (OUT / name).read_bytes())
        for component in manifest['components']:
            root = Path(component['root']); dest = prefix + '/components/' + component['component']
            for name in ['SOURCE_MANIFEST.json', 'SEAL.json', 'REVIEWER_PACKET.md']:
                put(WF, env, dest + '/' + name, (root / name).read_bytes())
        quant = Path(manifest['quantiser_mount_manifest']).parent
        for name in ['MANIFEST.json', 'PROVIDER_SYMBOLS.txt', 'QUANTISER_MOUNT.patch']:
            put(WF, env, prefix + '/components/quantiser_mount/' + name, (quant / name).read_bytes())
        put(WF, env, prefix + '/CHECKPOINT.json', (json.dumps(record, indent=2) + '\n').encode())
        workflow_tree = git(WF, 'write-tree', env=env)
        message = ('Checkpoint native Replay link closure and quantiser mount\n\n'
            'Pin the reviewed two-source successor and mount the existing real Vector4 quantiser provider. '
            'Preserve all private/public reconciliation ancestry and keep native/site status pending.\n\n' + TRAILER + '\n')
        workflow_commit = git(WF, 'commit-tree', workflow_tree, '-p', manifest['workflow_base'], data=message.encode())
        assert git(WF, 'ls-tree', workflow_commit, 'b5-decomp').split()[2] == commit
        for repo, rev in [(B5, commit), (WF, workflow_commit)]:
            assert git(repo, 'show', '-s', '--format=%B', rev).endswith(TRAILER)
        record.update({'workflow_commit': workflow_commit, 'workflow_tree': workflow_tree,
            'trailer_verified': TRAILER, 'refs_updated': False})
        (OUT / 'CHECKPOINT_OBJECTS.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(record, indent=2))

if __name__ == '__main__': main()
