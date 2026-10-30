from pathlib import Path
import difflib, hashlib, json, os, subprocess, tempfile

OUT = Path(__file__).resolve().parent
CAMPAIGN = OUT.parent
WF = CAMPAIGN.parents[2]
B5 = WF / 'b5-decomp'
BASE = '65f58d20c63dda8f351f672b5b9fc0d30f8a7af1'
WFBASE = '68aa25a538f004e492de452073d4605250c5ec65'
ROOT = WF / 'scratch/DEBUG_MENU_1011'
DIRECTOR = CAMPAIGN / 'director_stack_tag_successor_20261029'
RACECAR = ROOT / 'replay_racecar_worldmap_provider_delta01_20261029'
QUANTISER = ROOT / 'swarm_replay_traffic_quantiser_mount_closure_20261029'

def sha(raw): return hashlib.sha256(raw).hexdigest()

def git(repo, *args, env=None):
    p = subprocess.run(['git', '-C', str(repo), *args], env=env, capture_output=True)
    if p.returncode: raise RuntimeError(str(args) + ': ' + p.stderr.decode('utf-8', errors='replace'))
    return p.stdout

def main():
    assert not (OUT / 'SOURCE_MANIFEST.json').exists()
    rows, components, patch = [], [], []
    for label, root, seal_sha, style in [
        ('director_stack_tag', DIRECTOR, '1efd39b81b5b1fc0fe931e18cf2aae8e7ae832026d9e41c97f07029eb278bca1', 'director'),
        ('racecar_worldmap', RACECAR, 'a5fc450cc6f5e0891c7777995459c3c4b62c0890da2f2cfe3e8951ba29d06688', 'racecar')]:
        assert sha((root / 'SEAL.json').read_bytes()) == seal_sha
        seal = json.loads((root / 'SEAL.json').read_text(encoding='utf-8'))
        entries = seal['files']
        if isinstance(entries, dict):
            for path, expected in entries.items():
                assert sha((root / path).read_bytes()) == expected, path
        else:
            for item in entries:
                assert sha((root / item['path']).read_bytes()) == item['sha256'], item['path']
        manifest = json.loads((root / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
        assert manifest['base'] == BASE
        for row in manifest['files']:
            path = row['path']
            source = root / 'postimage' / ('b5-decomp' if style == 'racecar' else '') / path
            after = source.read_bytes()
            assert b'\r' not in after
            assert sha(after) == row.get('after_sha256', row.get('post_sha256'))
            before = git(B5, 'show', BASE + ':' + path)
            assert sha(before) == row.get('before_sha256', row.get('pre_sha256'))
            for folder, raw in [('preimage', before), ('postimage', after)]:
                dest = OUT / folder / path
                dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(raw)
            rows.append({'path': path, 'source': str(OUT / 'postimage' / path), 'component': label,
                'before_sha256': sha(before), 'after_sha256': sha(after), 'approved_import': str(source)})
            patch.extend(difflib.unified_diff(before.decode().splitlines(keepends=True), after.decode().splitlines(keepends=True),
                fromfile='a/' + path, tofile='b/' + path))
        components.append({'component': label, 'root': str(root), 'seal': str(root / 'SEAL.json'), 'seal_sha256': seal_sha})
    quant = json.loads((QUANTISER / 'MANIFEST.json').read_text(encoding='utf-8'))
    assert sha((QUANTISER / 'MANIFEST.json').read_bytes()) == '8bc326cbab707f93bd5f0fd6fdf2719b238137b8271d7207ab43e69a2705eefb'
    assert sha((QUANTISER / 'QUANTISER_MOUNT.patch').read_bytes()) == quant['mount_patch_sha256']
    for row in quant['sources']:
        assert sha(git(B5, 'show', BASE + ':' + row['path'])) == row['private_source_sha256']
        assert sha(Path(row['fixture_object']).read_bytes()) == row['fixture_object_sha256']
    assert len(rows) == 2 and len({row['path'] for row in rows}) == 2
    manifest = {'base': BASE, 'workflow_base': WFBASE, 'files': rows, 'components': components,
        'quantiser_mount_manifest': str(QUANTISER / 'MANIFEST.json'),
        'quantiser_manifest_sha256': sha((QUANTISER / 'MANIFEST.json').read_bytes()),
        'native_full_compile_before_fix': '3018 of3018 passed;7 link symbols unresolved',
        'whole_link': 'pending', 'native_game_run': False, 'normal_install_changed': False}
    (OUT / 'SOURCE_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    patch_path = OUT / 'combined_source.patch'
    patch_path.write_text(''.join(patch), encoding='utf-8', newline='\n')
    with tempfile.TemporaryDirectory(prefix='replay_link_closure_patch_') as directory:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(directory) / 'b5.index'))
        git(B5, 'read-tree', BASE, env=env)
        git(B5, '-c', 'core.autocrlf=false', 'apply', '--cached', '--check', str(patch_path), env=env)
        git(B5, '-c', 'core.autocrlf=false', 'apply', '--cached', str(patch_path), env=env)
        for row in rows: assert sha(git(B5, 'show', ':' + row['path'], env=env)) == row['after_sha256']
        tree = git(B5, 'write-tree', env=env).decode().strip()
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(directory) / 'workflow.index'))
        git(WF, 'read-tree', WFBASE, env=env)
        qp = QUANTISER / 'QUANTISER_MOUNT.patch'
        git(WF, '-c', 'core.autocrlf=false', 'apply', '--cached', '--check', str(qp), env=env)
        git(WF, '-c', 'core.autocrlf=false', 'apply', '--cached', str(qp), env=env)
        buildpath = 'tools/build/build_game_exe.bat'
        before = git(WF, 'show', WFBASE + ':' + buildpath)
        after = git(WF, 'show', ':' + buildpath, env=env)
        changed = git(WF, 'diff', '--cached', '--name-only', WFBASE, env=env).decode().splitlines()
        assert changed == [buildpath]
    dest = OUT / 'workflow_postimage/tools/build/build_game_exe.bat'
    dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(after.replace(b'\n', b'\r\n'))
    assert dest.read_bytes().count(b'\r') == dest.read_bytes().count(b'\n')
    (OUT / 'workflow_source_mount.patch').write_bytes((QUANTISER / 'QUANTISER_MOUNT.patch').read_bytes())
    (OUT / 'WORKFLOW_SOURCE_MOUNT.json').write_text(json.dumps({'workflow_base': WFBASE,
        'path': buildpath, 'new_sources': [quant['provider']], 'before_sha256': sha(before),
        'after_lf_sha256': sha(after), 'postimage_crlf_sha256': sha(dest.read_bytes()),
        'approved_import_patch_sha256': quant['mount_patch_sha256']}, indent=2) + '\n', encoding='utf-8')
    (OUT / 'PATCH_CHECKS.json').write_text(json.dumps({'base': BASE, 'passed': True,
        'source_tree': tree, 'source_paths': len(rows), 'private_indexes_only': True,
        'exact_postimage_round_trip': True, 'patch_sha256': sha(patch_path.read_bytes()),
        'workflow_single_mount_patch_pass': True}, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'source_paths': len(rows), 'source_tree': tree, 'new_real_provider': quant['provider']}))

if __name__ == '__main__': main()
