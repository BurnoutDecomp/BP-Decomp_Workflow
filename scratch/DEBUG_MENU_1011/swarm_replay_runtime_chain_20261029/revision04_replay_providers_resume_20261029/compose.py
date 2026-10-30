from pathlib import Path
import difflib, hashlib, json, os, subprocess, tempfile

OUT = Path(__file__).resolve().parent
CAMPAIGN = OUT.parent
WF = CAMPAIGN.parents[2]
B5 = WF / 'b5-decomp'
BASE = 'f32c7d531d98c811a89f69a6f868fdc10b74716a'
WFBASE = '5a73986a22c5a4f5f3f242dfec678688e75bad13'
ROOT = WF / 'scratch/DEBUG_MENU_1011'
COMPONENTS = [
    ('common_scheduler', CAMPAIGN / 'gamemodule_replay_scheduler_resume_20261029',
     'FROZEN_INPUTS_SEAL.json', 'cec2f27aa6f4b2d8bed0669f35319854eb0b71e933ada038f54ffe332193f5fe', 'common'),
    ('director_world', CAMPAIGN / 'world_director_resume_20261029',
     'SEAL.json', '1da1b252ba57d3c2d0ace2cd4b7cb559fa5603bc8504638d68223efc881b1054', 'director'),
    ('racecar_producers', ROOT / 'replay_racecar_actualproducer_typedframe_resume_20261029',
     'SEAL.json', 'c54a6ced1e39e2afac2f189267c2b5b743b7795065ddbbaea23b1afbcf6ad346', 'racecar'),
    ('sound_codec', ROOT / 'swarm_replay_sound_codec_resume_20261029',
     'SEAL.json', '625452cb824acad93a4bf9084bc0646cd6f2bf03db179cab3283ca8c39f6ac08', 'sound'),
]

def git(repo, *args, env=None, data=None):
    result = subprocess.run(['git', '-C', str(repo), *args], env=env, input=data, capture_output=True)
    if result.returncode:
        raise RuntimeError(str(args) + ': ' + result.stderr.decode('utf-8', errors='replace'))
    return result.stdout

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    assert not (OUT / 'CHECKPOINT_OBJECTS.json').exists(), 'checkpoint already built'
    all_rows, components, patch = [], [], []
    for label, root, seal_name, expected_seal, style in COMPONENTS:
        seal_path = root / seal_name
        assert sha(seal_path.read_bytes()) == expected_seal, label
        seal = json.loads(seal_path.read_text(encoding='utf-8'))
        files = seal['files']
        if isinstance(files, dict):
            for name, value in files.items():
                expected = value if isinstance(value, str) else value['sha256']
                path = Path(name) if Path(name).is_absolute() else root / name
                assert sha(path.read_bytes()) == expected, str(path)
        else:
            for row in files:
                path = Path(row['path']) if Path(row['path']).is_absolute() else root / row['path']
                assert sha(path.read_bytes()) == row['sha256'], str(path)
        manifest = json.loads((root / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
        if style == 'sound':
            imports = [dict(row, path=path) for path, row in manifest['files'].items()]
        else:
            imports = manifest['files']
        component_paths = []
        for row in imports:
            path = row['path']
            source = root / 'postimage' / ('b5-decomp' if style == 'racecar' else '') / path
            after = source.read_bytes()
            expected_post = row.get('after_sha256', row.get('post_sha256'))
            assert sha(after) == expected_post, str(source)
            assert b'\r' not in after, str(source) + ' is not frozen LF'
            exists = row.get('pre_exists', True)
            before = git(B5, 'show', BASE + ':' + path) if exists else b''
            expected_pre = row.get('before_sha256', row.get('pre_sha256'))
            assert sha(before) == expected_pre, path
            assert before != after, path
            for folder, raw in [('preimage', before), ('postimage', after)]:
                dest = OUT / folder / path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(raw)
            component_paths.append(path)
            all_rows.append({'path': path, 'source': str(OUT / 'postimage' / path),
                'before_sha256': sha(before), 'after_sha256': sha(after), 'before_exists': exists,
                'component': label, 'import': str(source), 'approved_source_sha256': expected_post})
            patch.extend(difflib.unified_diff(before.decode().splitlines(keepends=True), after.decode().splitlines(keepends=True),
                fromfile=('a/' + path if exists else '/dev/null'), tofile='b/' + path))
        components.append({'component': label, 'root': str(root), 'manifest_sha256': sha((root / 'SOURCE_MANIFEST.json').read_bytes()),
            'seal': str(seal_path), 'seal_sha256': expected_seal, 'source_paths': component_paths})
    assert len(all_rows) == 24 and len({row['path'] for row in all_rows}) == 24
    manifest = {'base': BASE, 'workflow_base': WFBASE, 'files': all_rows, 'components': components,
        'review_scope': 'four unchanged approved components; Traffic producer and renderer excluded pending successor review',
        'shared_checkout_changed': False, 'normal_install_changed': False, 'whole_link': 'pending', 'native_behavior': 'pending'}
    manifest_text = json.dumps(manifest, indent=2) + '\n'
    if (OUT / 'SOURCE_MANIFEST.json').exists():
        assert (OUT / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8') == manifest_text
    else:
        (OUT / 'SOURCE_MANIFEST.json').write_text(manifest_text, encoding='utf-8')
    patch_path = OUT / 'combined_source.patch'
    patch_path.write_text(''.join(patch), encoding='utf-8', newline='\n')
    with tempfile.TemporaryDirectory(prefix='replay_v4_check_') as directory:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(directory) / 'private.index'))
        git(B5, 'read-tree', BASE, env=env)
        git(B5, '-c', 'core.autocrlf=false', 'apply', '--cached', '--check', str(patch_path), env=env)
        git(B5, '-c', 'core.autocrlf=false', 'apply', '--cached', str(patch_path), env=env)
        for row in all_rows:
            assert sha(git(B5, 'show', ':' + row['path'], env=env)) == row['after_sha256']
        tree = git(B5, 'write-tree', env=env).decode().strip()
    mount = git(WF, 'show', WFBASE + ':tools/build/build_game_exe.bat').decode().replace('\r\n', '\n')
    source_cpp = [row['path'] for row in all_rows if row['path'].endswith('.cpp')]
    counts = {path: mount.count(path[4:].replace('/', '\\')) for path in source_cpp}
    new_cpp = 'src/GameSource/Replays/Serialisers/BrnReplayRaceCarEntitySerialiser.cpp'
    assert counts.pop(new_cpp) == 0
    assert all(count == 1 for count in counts.values()), counts
    anchor = '  echo "%SRC%\\GameSource\\Replays\\Serialisers\\BrnReplayGameModuleSerialiser.cpp"'
    assert mount.count(anchor) == 1
    mount_after = mount.replace(anchor, anchor + '\n  echo "%SRC%\\GameSource\\Replays\\Serialisers\\BrnReplayRaceCarEntitySerialiser.cpp"')
    workflow_path = OUT / 'workflow_postimage/tools/build/build_game_exe.bat'
    workflow_path.parent.mkdir(parents=True, exist_ok=True)
    workflow_path.write_bytes(mount_after.replace('\n', '\r\n').encode('utf-8'))
    assert workflow_path.read_bytes().count(b'\r') == workflow_path.read_bytes().count(b'\n')
    (OUT / 'workflow_source_mount.patch').write_text(''.join(difflib.unified_diff(
        mount.splitlines(keepends=True), mount_after.splitlines(keepends=True),
        fromfile='a/tools/build/build_game_exe.bat', tofile='b/tools/build/build_game_exe.bat')), encoding='utf-8', newline='\n')
    (OUT / 'WORKFLOW_SOURCE_MOUNT.json').write_text(json.dumps({'workflow_base': WFBASE,
        'path': 'tools/build/build_game_exe.bat', 'new_sources': [new_cpp],
        'before_sha256': sha(mount.encode()), 'after_lf_sha256': sha(mount_after.encode()),
        'postimage_crlf_sha256': sha(workflow_path.read_bytes())}, indent=2) + '\n', encoding='utf-8')
    (OUT / 'PATCH_CHECKS.json').write_text(json.dumps({'base': BASE, 'passed': True,
        'private_index_only': True, 'exact_postimage_round_trip': True, 'source_tree': tree,
        'source_paths': len(all_rows), 'patch_sha256': sha(patch_path.read_bytes())}, indent=2) + '\n', encoding='utf-8')
    (OUT / 'SOURCE_MOUNT_CLOSURE.json').write_text(json.dumps({'workflow_base': WFBASE,
        'changed_cpp_already_mounted_counts': counts, 'new_mount_required': [new_cpp],
        'whole_link_proof': False}, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'source_paths': len(all_rows), 'source_tree': tree, 'new_mount_required': [new_cpp]}))

if __name__ == '__main__':
    main()
