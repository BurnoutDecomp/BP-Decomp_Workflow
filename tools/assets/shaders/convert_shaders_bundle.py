#!/usr/bin/env python3
"""Convert the X360 SHADERS.BNDL (bnd2 platform 2, big-endian) toward the
platform-4 form the reconstructed PC engine loads.

Commands:
  py convert_shaders_bundle.py inventory <in_x360_bundle>
      Extract with YAP and print the resource inventory, technique names,
      per-technique VS/PS program-buffer imports, and the TUB HLSL mapping
      coverage.  Read-only; work happens in a temp dir.

  py convert_shaders_bundle.py convert <in_x360_bundle> <out_plat4_bundle>
        [--mode d3d9|flip] [--fxdir DIR]... [--fallback] [--keep-work DIR]
      d3d9 (default): ShaderTechnique -> structural LE flip (validated,
        round-trip-proven); ShaderProgramBuffer -> REPLACED with D3D9 SM3
        bytecode compiled from the TUB HLSL sources (fxc, base variant, no
        defines) wrapped in the LE ProgramBufferData container, descriptor
        table rebuilt from the bytecode CTAB (see FORMAT_MAP.md section 5).
        Techniques with no TUB HLSL source (the Vehicle_* set) hard-fail
        unless --fallback substitutes tools/assets/shaders/fallback_world.fx.
      flip: ShaderProgramBuffer primaries get a structural LE flip but KEEP
        the Xenos microcode -- loader-valid, NOT drawable.  Diagnostic only.
      Both modes: Material / MaterialState / MaterialTechnique / TextureState
      via the boot-proven world_type_transcode flippers, Texture via the
      Volatility PortTexture flow (both reused from tools/assets/bundles/
      convert_world_bundle.py), meta platform 2 -> 4 + uncompressed, and the
      YAP import-sidecar rename fix.

Requires: build/tools/yap/YAP.exe, fxc.exe (env PC_FXC or a Windows 10/11
SDK), and for the Texture resources build/tools/volatility/Volatility.Cli.exe.

Do NOT stage outputs into build/game/ from this tool; write to
tools/assets/shaders/out/ or a scratch dir and hand over to the build owner.
"""
import argparse
import glob as globmod
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
BUNDLES = os.path.join(ROOT, 'tools', 'assets', 'bundles')
for p in (HERE, BUNDLES):
    if p not in sys.path:
        sys.path.insert(0, p)

import shader_transcode as st                    # noqa: E402
import world_type_transcode as wtt               # noqa: E402
import convert_world_bundle as cwb               # noqa: E402

YAP = os.path.join(ROOT, 'build', 'tools', 'yap', 'YAP.exe')
NUSHADERS_TUB = r'D:\Reverse\nushaders\Reference\TUB\Bundle\gamedb\burnout5'
DEFAULT_FX_DIR = os.path.join(NUSHADERS_TUB, 'Shaders')
DEFAULT_INCLUDE_DIR = os.path.join(NUSHADERS_TUB, 'Include')
FALLBACK_FX = os.path.join(HERE, 'fallback_world.fx')

# SHADERS.BNDL non-shader types handled by the established world flippers.
WORLD_FLIP = {
    'Material': wtt.transcode_material,
    'MaterialState': wtt.transcode_materialstate,
    'MaterialTechnique': wtt.transcode_materialtechnique,
    'TextureState': wtt.transcode_texturestate,
}


def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit('command failed (%d): %s' % (r.returncode, ' '.join(args[:3])))
    return r.stdout


def find_fxc():
    env = os.environ.get('PC_FXC')
    if env and os.path.isfile(env):
        return env
    hits = []
    for root in (r'C:\Program Files (x86)\Windows Kits\10\bin',
                 r'C:\Program Files\Windows Kits\10\bin'):
        hits += globmod.glob(os.path.join(root, '*', 'x64', 'fxc.exe'))
        hits += globmod.glob(os.path.join(root, 'x64', 'fxc.exe'))
    if hits:
        return sorted(hits)[-1]
    fxc = shutil.which('fxc.exe')
    if fxc:
        return fxc
    raise SystemExit('fxc.exe not found: set PC_FXC or install a Windows SDK '
                     '(nushaders Build/Resolve-PC-FXC.ps1 has the same search).')


# ---------------------------------------------------------------------------
# TUB HLSL technique mapping
# ---------------------------------------------------------------------------

_TECH_RE = re.compile(r'technique\s+(\w+)')
_VS_RE = re.compile(r'VertexShader\s*=\s*compile\s+vs_\d_\d\s+(\w+)\s*\(')
_PS_RE = re.compile(r'PixelShader\s*=\s*compile\s+ps_\d_\d\s+(\w+)\s*\(')


def scan_fx_techniques(fx_path):
    """[(technique_name, vs_entry, ps_entry)] for one .fx file."""
    text = open(fx_path, 'r', encoding='utf-8', errors='replace').read()
    out = []
    matches = list(_TECH_RE.finditer(text))
    for i, m in enumerate(matches):
        seg = text[m.end():matches[i + 1].start() if i + 1 < len(matches) else len(text)]
        vs, ps = _VS_RE.search(seg), _PS_RE.search(seg)
        if vs and ps:
            out.append((m.group(1), vs.group(1), ps.group(1)))
    return out


def build_technique_map(fx_dirs):
    """{lowercased X360 technique name: (fx_path, vs_entry, ps_entry)}.

    Three name forms resolve:
      '<FxBaseName>_<Technique>'  (e.g. Diffuse_Opaque_Singlesided_Default)
      '<Technique>'               (the shared standalone ZOnly* techniques)
      '<Technique>Instanced'      (from *_Instanced.fx files only: the X360
                                   bundle names the instanced Z-prepass
                                   techniques ZOnly*Instanced, while the TUB
                                   instanced sources keep the base technique
                                   name with instanced vertex fetch bodies)
    First fx dir wins; within a dir, alphabetical fx order wins for the
    standalone forms (the ZOnly bodies are per-variant identical copies).
    """
    mapping = {}
    for d in fx_dirs:
        for fx in sorted(globmod.glob(os.path.join(d, '*.fx'))):
            base = os.path.splitext(os.path.basename(fx))[0]
            instanced = base.lower().endswith('_instanced')
            for tech, vs, ps in scan_fx_techniques(fx):
                keys = ['%s_%s' % (base, tech), tech]
                if instanced:
                    keys.append(tech + 'Instanced')
                for key in keys:
                    mapping.setdefault(key.lower(), (fx, vs, ps))
    return mapping


def compile_entry(fxc, fx_path, entry, profile, include_dir, out_path):
    # /Zpr == D3DCOMPILE_PACK_MATRIX_ROW_MAJOR.  MANDATORY, not a preference: the engine
    # uploads a matrix constant as the raw run of float4s the runtime ShaderConstantTable
    # holds (row-vector rows for `world`, the dot-product rows for
    # ViewProjectionModified), so shader register N must be logical ROW N.  fxc's default
    # is column-major, which silently transposes every matrix constant.
    #
    # Attested against the X360 originals' own variable tables
    # (build/game_x360_world/SHADERS.BNDL, read with shader_transcode.program_buffer_variables):
    #                          X360    /Zpr    fxc default
    #   world                    4       4          3
    #   IrradianceQuadricA       4       4          4
    #   IrradianceQuadricB       3       3          4
    #   ShadowMap_WorldToLight  12      12         10
    # i.e. /Zpr reproduces the console register counts exactly and the default does not.
    def attempt(src):
        return subprocess.run([fxc, '/nologo', '/T', profile, '/E', entry,
                               '/I', include_dir, '/O2', '/Zpr', '/Fo', out_path, src],
                              capture_output=True, text=True)
    r = attempt(fx_path)
    if r.returncode != 0 and "undeclared identifier 'g_verletOffsets'" in (r.stdout + r.stderr):
        # Vehicle_1Bit_Tyre_Textured.fx (TUB source defect): its siblings all
        # declare the verlet bone array themselves before including
        # VehicleDeformation.fxh; this one does not.  Retry via a wrapper that
        # supplies the declaration then includes the original verbatim.
        wrapper = out_path + '.wrap.fx'
        with open(wrapper, 'w', encoding='utf-8') as fh:
            fh.write('float4 g_verletOffsets[128];\n#include "%s"\n'
                     % fx_path.replace('\\', '/'))
        r = attempt(wrapper)
    if r.returncode != 0 or not os.path.isfile(out_path):
        raise SystemExit('fxc failed for %s:%s (%s):\n%s%s'
                         % (os.path.basename(fx_path), entry, profile,
                            r.stdout, r.stderr))
    with open(out_path, 'rb') as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# Bundle walk
# ---------------------------------------------------------------------------

def parse_technique_imports(path):
    """imports yaml -> {byte_offset: resource_id} (both ints)."""
    out = {}
    for m in re.finditer(r'-\s*0x([0-9a-fA-F]+):\s*0x([0-9a-fA-F]+)',
                         open(path, 'r', encoding='utf-8').read()):
        out[int(m.group(1), 16)] = int(m.group(2), 16)
    return out


def collect(ex_dir):
    """Read the extracted tree: techniques {rid: (blob, imports)}, program
    buffer ids {rid: (primary_path, secondary_path)}."""
    techniques = {}
    tdir = os.path.join(ex_dir, 'ShaderTechnique')
    for f in sorted(os.listdir(tdir)):
        if not f.endswith('.dat'):
            continue
        rid = f[:-4]
        blob = open(os.path.join(tdir, f), 'rb').read()
        imports = parse_technique_imports(os.path.join(tdir, f + '_imports.yaml'))
        techniques[rid] = (blob, imports)
    buffers = {}
    pdir = os.path.join(ex_dir, 'ShaderProgramBuffer')
    for f in sorted(os.listdir(pdir)):
        if f.endswith('_header.dat'):
            rid = f[:-len('_header.dat')]
            buffers[rid] = (os.path.join(pdir, f),
                            os.path.join(pdir, rid + '_body.dat'))
    return techniques, buffers


def plan_shader_work(techniques, buffers, tech_map, use_fallback):
    """Decide, per program buffer, what D3D9 source to compile.

    Returns (jobs {buffer_rid: (fx, entry, profile, technique_name)},
             unmapped [technique names])."""
    jobs, unmapped = {}, []
    for rid, (blob, imports) in sorted(techniques.items()):
        name = st.technique_name(blob)
        vs_id, ps_id = imports.get(0), imports.get(4)
        if vs_id is None or ps_id is None:
            raise SystemExit('technique %s (%s): imports missing VS/PS slots: %r'
                             % (rid, name, imports))
        hit = tech_map.get(name.lower())
        if hit is None and use_fallback:
            hit = (FALLBACK_FX, 'VS_Main', 'PS_Main')
        if hit is None:
            unmapped.append(name)
            continue
        fx, vs_entry, ps_entry = hit
        for slot_id, entry, profile in ((vs_id, vs_entry, 'vs_3_0'),
                                        (ps_id, ps_entry, 'ps_3_0')):
            key = '%08X' % slot_id
            if key not in buffers:
                raise SystemExit('technique %s (%s): imported program buffer '
                                 '%s not in bundle' % (rid, name, key))
            jobs[key] = (fx, entry, profile, name)
    return jobs, unmapped


def convert(in_bundle, out_bundle, mode, fx_dirs, use_fallback, keep_work):
    work = keep_work or tempfile.mkdtemp(prefix='shadersbndl_')
    os.makedirs(work, exist_ok=True)
    ex = os.path.join(work, 'ex')
    if os.path.isdir(ex):
        shutil.rmtree(ex)
    run([YAP, 'e', in_bundle, ex])

    techniques, buffers = collect(ex)
    manifest = {'techniques': len(techniques), 'buffers': len(buffers),
                'mode': mode, 'compiled': 0, 'fallback': 0}

    # --- ShaderTechnique: validated structural LE flip -----------------------
    tdir = os.path.join(ex, 'ShaderTechnique')
    for rid, (blob, _imports) in techniques.items():
        le, _ = st.transcode_shader_technique(blob)
        with open(os.path.join(tdir, rid + '.dat'), 'wb') as fh:
            fh.write(le)

    # --- ShaderProgramBuffer -------------------------------------------------
    if mode == 'flip':
        for rid, (ppath, spath) in buffers.items():
            prim = open(ppath, 'rb').read()
            le, _sec = st.flip_program_buffer(prim, b'')
            with open(ppath, 'wb') as fh:
                fh.write(le)
        manifest['buffers_flipped'] = len(buffers)
    else:
        fxc = find_fxc()
        tech_map = build_technique_map(fx_dirs)
        jobs, unmapped = plan_shader_work(techniques, buffers, tech_map,
                                          use_fallback)
        if unmapped:
            raise SystemExit(
                'no TUB HLSL source for %d technique(s):\n  %s\n'
                'Re-run with --fallback to substitute fallback_world.fx, or '
                'add fx dirs with --fxdir.' % (len(unmapped),
                                               '\n  '.join(sorted(unmapped))))
        orphans = sorted(set(buffers) - set(jobs))
        if orphans:
            raise SystemExit('program buffers not imported by any technique: %s'
                             % ', '.join(orphans))
        cache = {}
        cache_dir = os.path.join(work, 'fxo')
        os.makedirs(cache_dir, exist_ok=True)
        for rid, (fx, entry, profile, tname) in sorted(jobs.items()):
            ckey = (fx, entry, profile)
            if ckey not in cache:
                out_path = os.path.join(cache_dir, '%s_%s_%s.fxo' % (
                    os.path.splitext(os.path.basename(fx))[0], entry, profile))
                cache[ckey] = compile_entry(fxc, fx, entry, profile,
                                            DEFAULT_INCLUDE_DIR, out_path)
                manifest['compiled'] += 1
            shader_type = 0 if profile.startswith('vs') else 1
            # cross-check against the X360 primary's own type word
            x360_type = struct.unpack('>I', open(buffers[rid][0], 'rb').read(4))[0]
            if x360_type != shader_type:
                raise SystemExit('type mismatch: buffer %s is X360 type %d but '
                                 'technique %s slot says %d'
                                 % (rid, x360_type, tname, shader_type))
            prim, sec = st.build_pc_program_buffer(cache[ckey], shader_type)
            if fx == FALLBACK_FX:
                manifest['fallback'] += 1
            with open(buffers[rid][0], 'wb') as fh:
                fh.write(prim)
            with open(buffers[rid][1], 'wb') as fh:
                fh.write(sec)

    # --- non-shader types via the established world flows --------------------
    for entry in sorted(os.listdir(ex)):
        folder = os.path.join(ex, entry)
        if not os.path.isdir(folder) or entry in ('ShaderTechnique',
                                                  'ShaderProgramBuffer'):
            continue
        files = [f for f in os.listdir(folder)
                 if f.endswith('.dat') and not f.endswith('_body.dat')]
        if entry in WORLD_FLIP:
            fn = WORLD_FLIP[entry]
            for f in files:
                fp = os.path.join(folder, f)
                blob = open(fp, 'rb').read()
                imp_path = fp + '_imports.yaml'
                imp_text = (open(imp_path, 'r', encoding='utf-8').read()
                            if os.path.isfile(imp_path) else None)
                out, new_imp = fn(blob, imp_text)
                with open(fp, 'wb') as fh:
                    fh.write(out)
                if new_imp is not None and imp_text is not None and new_imp != imp_text:
                    with open(imp_path, 'w', encoding='utf-8') as fh:
                        fh.write(new_imp)
            manifest[entry] = len(files)
        elif entry == 'Texture':
            count = 0
            for f in files:
                if not f.endswith('_header.dat'):
                    continue
                cwb.port_texture(work, folder, f[:-len('_header.dat')])
                count += 1
            manifest[entry] = count
        else:
            raise SystemExit('unhandled resource folder %s -- extend the '
                             'driver before converting' % entry)

    # --- YAP sidecar rename fix (see convert_world_bundle.py) ----------------
    for lroot, _dirs, lfiles in os.walk(ex):
        for f in lfiles:
            if f.endswith('.dat_imports.yaml'):
                base = f[:-len('.dat_imports.yaml')]
                if base.endswith('_header'):
                    base = base[:-len('_header')]
                os.replace(os.path.join(lroot, f),
                           os.path.join(lroot, base + '_imports.yaml'))

    # --- meta: platform 2 -> 4, uncompressed ---------------------------------
    meta_path = os.path.join(ex, '.meta.yaml')
    meta = open(meta_path, 'r', encoding='utf-8').read()
    meta = re.sub(r'(^\s*platform:\s*)2\s*$', r'\g<1>4', meta, flags=re.M)
    meta = re.sub(r'(^\s*compressed:\s*)true\s*$', r'\g<1>false', meta, flags=re.M)
    with open(meta_path, 'w', encoding='utf-8') as fh:
        fh.write(meta)

    run([YAP, 'c', ex, out_bundle])
    if not keep_work:
        shutil.rmtree(work, ignore_errors=True)
    return manifest


def inventory(in_bundle, fx_dirs):
    work = tempfile.mkdtemp(prefix='shadersinv_')
    try:
        ex = os.path.join(work, 'ex')
        run([YAP, 'e', in_bundle, ex])
        techniques, buffers = collect(ex)
        tech_map = build_technique_map(fx_dirs)
        print('resources: %d ShaderTechnique, %d ShaderProgramBuffer'
              % (len(techniques), len(buffers)))
        for entry in sorted(os.listdir(ex)):
            folder = os.path.join(ex, entry)
            if os.path.isdir(folder) and entry not in ('ShaderTechnique',
                                                       'ShaderProgramBuffer'):
                n = len([f for f in os.listdir(folder) if f.endswith('.dat')])
                print('           %d %s file(s)' % (n, entry))
        mapped = unmapped = 0
        for rid, (blob, imports) in sorted(techniques.items()):
            name = st.technique_name(blob)
            hit = tech_map.get(name.lower())
            tag = 'fx=%s' % os.path.basename(hit[0]) if hit else 'NO TUB SOURCE'
            if hit:
                mapped += 1
            else:
                unmapped += 1
            print('%s %-62s VS=%08X PS=%08X %s'
                  % (rid, name, imports.get(0, 0), imports.get(4, 0), tag))
        print('TUB HLSL coverage: %d mapped / %d unmapped' % (mapped, unmapped))
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    inv = sub.add_parser('inventory')
    inv.add_argument('in_bundle')
    inv.add_argument('--fxdir', action='append', default=None)
    cv = sub.add_parser('convert')
    cv.add_argument('in_bundle')
    cv.add_argument('out_bundle')
    cv.add_argument('--mode', choices=('d3d9', 'flip'), default='d3d9')
    cv.add_argument('--fxdir', action='append', default=None)
    cv.add_argument('--fallback', action='store_true')
    cv.add_argument('--keep-work', default=None)
    a = ap.parse_args()
    fx_dirs = a.fxdir or [DEFAULT_FX_DIR]
    if a.fxdir is None and not os.path.isdir(DEFAULT_FX_DIR):
        # An absent TUB tree yields an EMPTY technique map, and --fallback then maps every
        # technique to fallback_world.fx without a word -- a bundle in which nothing is the
        # real shader, indistinguishable from a good one by size, platform byte or verify.
        # MINIMAL_PATH.md asks for exactly that bundle on purpose, via an explicit
        # `--fxdir <nonexistent>`; that stays available.  What must not happen is the same
        # output arriving because a checkout is missing on this box.
        raise SystemExit(
            'TUB HLSL source tree not found:\n  %s\n'
            'Every technique would silently compile to fallback_world.fx.\n'
            'Clone the nushaders repo there, point --fxdir at your copy, or -- if you '
            'really want the all-fallback diagnostic bundle -- ask for it explicitly with '
            '`--fallback --fxdir <nonexistent-dir>` (MINIMAL_PATH.md option A).'
            % DEFAULT_FX_DIR)
    if a.cmd == 'inventory':
        inventory(a.in_bundle, fx_dirs)
        return 0
    manifest = convert(a.in_bundle, a.out_bundle, a.mode, fx_dirs,
                       a.fallback, a.keep_work)
    print('manifest:', manifest)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
