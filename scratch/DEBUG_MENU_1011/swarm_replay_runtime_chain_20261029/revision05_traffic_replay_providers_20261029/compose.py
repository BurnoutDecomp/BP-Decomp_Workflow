from pathlib import Path
import difflib, hashlib, json, os, subprocess, tempfile

OUT = Path(__file__).resolve().parent
CAMPAIGN = OUT.parent
WF = CAMPAIGN.parents[2]
B5 = WF / 'b5-decomp'
ROOT = WF / 'scratch/DEBUG_MENU_1011'
V4 = CAMPAIGN / 'revision04_replay_providers_resume_20261029'
PRODUCER = ROOT / 'swarm_replay_traffic_producer_recovery_20261029'
SUCCESSOR = ROOT / 'swarm_replay_traffic_enter_replay_fix_20261029'
RENDERER = ROOT / 'swarm_replay_traffic_renderer_followon_20261029'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def git(repo, *args, env=None, required=True):
    p = subprocess.run(['git', '-C', str(repo), *args], env=env, capture_output=True)
    if p.returncode and required:
        raise RuntimeError(str(args) + ': ' + p.stderr.decode('utf-8', errors='replace'))
    return p.stdout if p.returncode == 0 else None

def main():
    assert not (OUT / 'SOURCE_MANIFEST.json').exists()
    checkpoint = json.loads((V4 / 'CHECKPOINT_OBJECTS.json').read_text(encoding='utf-8'))
    base, wfbase = checkpoint['source_commit'], checkpoint['workflow_commit']
    components = []
    loaded = []
    for label, root, expected in [
        ('original_producer', PRODUCER, 'b1bd577dc13f7b3f8d95a28fa2bbad5fd632d1908da9fa24be4611e976a9959e'),
        ('ready_reset_successor', SUCCESSOR, '6cb615174c7199e0cf195dbdfa58223def7bf531ab7b42cd532ba39f65553a3a'),
        ('renderer', RENDERER, '1e0a93482d6e0838c98e91e463e2f920a93cea68d74b790a178e12d9403a5686')]:
        path = root / 'SEAL.json'
        assert sha(path.read_bytes()) == expected, label
        data = json.loads(path.read_text(encoding='utf-8'))
        for row in data.get('evidence_and_checks', []):
            assert sha(Path(row['path']).read_bytes()) == row['sha256'], row['path']
        loaded.append(data)
        components.append({'component': label, 'root': str(root), 'seal': str(path), 'seal_sha256': expected})
    producer, successor, renderer = loaded
    old_rows = {row['path']: row for row in producer['sources']}
    selected = {}
    for row in successor['sources']:
        raw = Path(row['selected_path']).read_bytes()
        assert sha(raw) == row['sha256']
        selected[row['path']] = {'raw': raw, 'source': row['selected_path'], 'raw_sha256': row['sha256']}
    assert len(selected) == 9
    for row in renderer['sources']:
        path = row['path']
        source = RENDERER / 'post' / path
        raw = source.read_bytes()
        assert sha(raw) == row['post_sha256'], path
        if path in selected:
            assert sha(selected[path]['raw'].replace(b'\r\n', b'\n')) == row['pre_normalized_sha256']
        else:
            assert sha(git(B5, 'show', base + ':' + path)) == row['pre_normalized_sha256']
        selected[path] = {'raw': raw, 'source': str(source), 'raw_sha256': row['post_sha256']}
    assert len(selected) == 10
    rows, patch = [], []
    for path, row in sorted(selected.items()):
        before = git(B5, 'show', base + ':' + path, required=False)
        exists = before is not None
        before = before if exists else b''
        if path in old_rows:
            expected = old_rows[path].get('pre_normalized_sha256')
            assert (sha(before) if exists else None) == expected, path
        after = row['raw'].replace(b'\r\n', b'\n')
        for folder, raw in [('preimage', before), ('postimage', after)]:
            dest = OUT / folder / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
        rows.append({'path': path, 'source': str(OUT / 'postimage' / path),
            'before_exists': exists, 'before_sha256': sha(before), 'after_sha256': sha(after),
            'approved_import': row['source'], 'approved_raw_sha256': row['raw_sha256'],
            'only_import_normalization': 'CRLF to LF'})
        patch.extend(difflib.unified_diff(before.decode().splitlines(keepends=True), after.decode().splitlines(keepends=True),
            fromfile='a/' + path if exists else '/dev/null', tofile='b/' + path))
    manifest = {'base': base, 'workflow_base': wfbase, 'files': rows, 'components': components,
        'source_review': 'pass with one-store successor; old failed seal preserved',
        'shared_checkout_changed': False, 'normal_install_changed': False, 'whole_link': 'pending', 'native_replay': 'pending'}
    (OUT / 'SOURCE_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    patch_path = OUT / 'combined_source.patch'
    patch_path.write_text(''.join(patch), encoding='utf-8', newline='\n')
    with tempfile.TemporaryDirectory(prefix='traffic_v5_patch_') as directory:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(directory) / 'private.index'))
        git(B5, 'read-tree', base, env=env)
        git(B5, '-c', 'core.autocrlf=false', 'apply', '--cached', '--check', str(patch_path), env=env)
        git(B5, '-c', 'core.autocrlf=false', 'apply', '--cached', str(patch_path), env=env)
        for row in rows:
            assert sha(git(B5, 'show', ':' + row['path'], env=env)) == row['after_sha256']
        tree = git(B5, 'write-tree', env=env).decode().strip()
    buildpath = 'tools/build/build_game_exe.bat'
    before = git(WF, 'show', wfbase + ':' + buildpath).decode().replace('\r\n', '\n')
    cpp = [row['path'] for row in rows if row['path'].endswith('.cpp')]
    counts = {path: before.count(path[4:].replace('/', '\\')) for path in cpp}
    new = ['src/GameSource/Replays/Serialisers/BrnReplayTrafficEntitySerialiser.cpp',
        'src/GameSource/Replays/Serialisers/BrnReplayTrafficSerialiserFrame.cpp']
    assert all(counts[path] == (0 if path in new else 1) for path in cpp), counts
    anchor = '  echo "%SRC%\\GameSource\\Replays\\Serialisers\\BrnReplayRaceCarEntitySerialiser.cpp"'
    assert before.count(anchor) == 1
    after = before.replace(anchor, anchor + ''.join('\n  echo "%SRC%\\' + path[4:].replace('/', '\\') + '"' for path in new))
    dest = OUT / 'workflow_postimage' / buildpath
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(after.replace('\n', '\r\n').encode())
    assert dest.read_bytes().count(b'\r') == dest.read_bytes().count(b'\n')
    (OUT / 'workflow_source_mount.patch').write_text(''.join(difflib.unified_diff(before.splitlines(keepends=True),
        after.splitlines(keepends=True), fromfile='a/' + buildpath, tofile='b/' + buildpath)), encoding='utf-8', newline='\n')
    (OUT / 'WORKFLOW_SOURCE_MOUNT.json').write_text(json.dumps({'workflow_base': wfbase, 'path': buildpath,
        'new_sources': new, 'before_sha256': sha(before.encode()), 'after_lf_sha256': sha(after.encode()),
        'postimage_crlf_sha256': sha(dest.read_bytes())}, indent=2) + '\n', encoding='utf-8')
    (OUT / 'PATCH_CHECKS.json').write_text(json.dumps({'base': base, 'passed': True,
        'source_tree': tree, 'source_paths': len(rows), 'private_index_only': True,
        'exact_postimage_round_trip': True, 'patch_sha256': sha(patch_path.read_bytes())}, indent=2) + '\n', encoding='utf-8')
    (OUT / 'SOURCE_MOUNT_CLOSURE.json').write_text(json.dumps({'workflow_base': wfbase,
        'before_mount_counts': counts, 'new_sources': new, 'whole_link_proof': False}, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'source_paths': len(rows), 'source_tree': tree, 'new_real_sources': new}))

if __name__ == '__main__':
    main()
