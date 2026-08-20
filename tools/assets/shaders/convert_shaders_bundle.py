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
        [--allow-contract-errors]
      d3d9 (default): ShaderTechnique -> structural LE flip (validated,
        round-trip-proven); ShaderProgramBuffer -> REPLACED with D3D9 SM3
        bytecode compiled from the TUB HLSL sources (fxc, base variant, no
        defines) wrapped in the LE ProgramBufferData container, descriptor
        table rebuilt from the bytecode CTAB (see FORMAT_MAP.md section 5).
        Techniques with no TUB HLSL source hard-fail unless --fallback
        substitutes tools/assets/shaders/fallback_world.fx.  tools/assets/
        shaders/recovered/*.fx (shaders decoded from the X360 microcode) is
        always searched FIRST, so a recovered technique never falls back.
        After compiling, every technique's bound constant names are checked
        against its programs' CTABs: a missing INTERNAL constant is a hard
        error (it is a runtime assert in PostFixUpShaderConstants), a
        missing EXTERNAL one a warning (a runtime "Missing shader constant"
        log line).  --allow-contract-errors downgrades the hard error to a
        report, for the deliberate all-fallback diagnostic bundle only.

      flip: ShaderProgramBuffer primaries get a structural LE flip but KEEP
        the Xenos microcode -- loader-valid, NOT drawable.  Diagnostic only.
      Both modes: Material / MaterialState / MaterialTechnique / TextureState
      via the boot-proven world_type_transcode flippers, Texture via the
      Volatility PortTexture flow (both reused from tools/assets/bundles/
      convert_world_bundle.py), meta platform 2 -> 4 + uncompressed, and the
      YAP import-sidecar rename fix.

  py convert_shaders_bundle.py patch-recovered <pc_bundle> <out_bundle> [--keep-work DIR]
      For a box WITHOUT the TUB tree: recompile only the recovered/ techniques
      and swap their ShaderProgramBuffer resources into an already converted
      platform-4 bundle (everything else carried through untouched).  Same
      bytes for those resources as a full `convert` would emit.

  py convert_shaders_bundle.py check <in_x360_bundle> <pc_bundle>
      Read-only: run that same constant-contract check against an already
      converted PC bundle (e.g. build/game/SHADERS.BNDL) and say, per miss,
      whether the X360 program had the constant.  Exit 1 on any internal miss.

Requires: build/tools/yap/YAP.exe, fxc.exe (env PC_FXC or a Windows 10/11
SDK), the TUB HLSL tree (env NUSHADERS_TUB / build.config.toml
[inputs].nushaders_tub, or --fxdir), and for the Texture resources
build/tools/volatility/Volatility.Cli.exe.

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
# ---------------------------------------------------------------------------
# The nushaders HLSL tree.
#
# It is a SUBMODULE now -- tools/nushaders, github.com/BurnoutDecomp/NuShaders -- so the
# default resolves inside this checkout and a clean clone builds SHADERS.BNDL with no
# machine configuration at all.  Until 2026-08-17 the default was one developer's absolute
# path, which meant every other box either set NUSHADERS_TUB or silently produced an
# all-fallback bundle.
#
# Resolution order, most specific first:
#   --fxdir DIR...      explicit, wins outright (repeatable)
#   env NUSHADERS_TUB   fed by build.config.toml [inputs].nushaders_tub via the build
#                       driver; still honoured, so an out-of-tree working clone can be
#                       pointed at without touching the submodule
#   tools/nushaders     the submodule (the default)
#
# NOTE THE LAYOUT DIFFERENCE.  Upstream keeps the burnout5 gamedb under Source/Bundle/,
# not the Reference/TUB/Bundle/ path the old absolute default used.  Both spellings are
# probed, so an existing NUSHADERS_TUB aimed at either tree keeps working.
NUSHADERS_SUBMODULE = os.path.join(ROOT, 'tools', 'nushaders')
# Candidate gamedb roots, in order.  Each should contain Shaders/ and Include/.
_NUSHADERS_GAMEDB_CANDIDATES = (
    os.path.join(NUSHADERS_SUBMODULE, 'Source', 'Bundle', 'gamedb', 'burnout5'),
    os.path.join(NUSHADERS_SUBMODULE, 'Reference', 'TUB', 'Bundle', 'gamedb', 'burnout5'),
)


def _resolve_nushaders_tub():
    env = os.environ.get('NUSHADERS_TUB', '').strip()
    if env:
        # An explicit setting is honoured even when it does not exist: the "tree not found"
        # error is a better diagnostic than silently ignoring what the box asked for.
        return env
    for cand in _NUSHADERS_GAMEDB_CANDIDATES:
        if os.path.isdir(os.path.join(cand, 'Shaders')):
            return cand
    return _NUSHADERS_GAMEDB_CANDIDATES[0]


NUSHADERS_TUB = _resolve_nushaders_tub()
DEFAULT_FX_DIR = os.path.join(NUSHADERS_TUB, 'Shaders')
DEFAULT_INCLUDE_DIR = os.path.join(NUSHADERS_TUB, 'Include')
# Playground/Test_Shaders carries CarStudio_DoNotShipWithThisInTheGame.fx -- the LAST
# technique still served by fallback_world.fx.  Searched AFTER Shaders/ and never before
# it: that file also defines a `ZOnlyNull` technique, and three real shaders in Shaders/
# (Cruciform_1Bit_Doublesided{,_Instanced}, Water_Specular_Opaque_Singlesided) define it
# too.  build_technique_map is first-dir-wins, so putting the playground first would
# quietly re-point the shared standalone ZOnly* keys at a do-not-ship test shader.
DEFAULT_PLAYGROUND_FX_DIR = os.path.join(NUSHADERS_TUB, 'Playground', 'Test_Shaders')
FALLBACK_FX = os.path.join(HERE, 'fallback_world.fx')
# Shaders RECOVERED from the X360 microcode (xenos.py + ctab.py) for techniques the
# nushaders HLSL tree does not carry.  Searched FIRST, so a recovered technique never
# falls through to --fallback.  Each file is self-contained (compiles without Include/).
#
# CURRENTLY ONE FILE, AND IT IS NOW ALSO UPSTREAM.  Godray_Additive_Doublesided.fx was
# contributed to the nushaders submodule on 2026-08-17, at the gamedb path the technique
# itself names (Playground/Test_Shaders/), so the bundle builds correctly from nushaders
# ALONE -- verified: 110 mapped / 0 unmapped, compiled 218 / fallback 0 with this dir
# excluded from the search.  The copy here is kept deliberately, for two reasons:
#   * it is THIS repo's attested artifact -- the annotated microcode listing in its header
#     is the decode evidence, and it should not depend on another repo's history;
#   * dropping it would change the emitted bundle's resource LAYOUT (same resources, same
#     technique sources, ~80 bytes of table ordering), and the layout that has been
#     boot-tested is the one produced with this dir in the search.
# The two copies are byte-identical; if they ever diverge, this one is the decode of
# record and upstream should be re-synced from it.
RECOVERED_FX_DIR = os.path.join(HERE, 'recovered')

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
        # The recovered/ shaders are self-contained; the TUB Include/ tree may not
        # exist on a box that only re-compiles those, so only pass /I when it does.
        inc = ['/I', include_dir] if os.path.isdir(include_dir) else []
        return subprocess.run([fxc, '/nologo', '/T', profile, '/E', entry] + inc +
                              ['/O2', '/Zpr', '/Fo', out_path, src],
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


def check_constant_contract(techniques, built, technique_le):
    """Cross-check every technique's bound constant names against the variable
    tables of the (platform-4) program buffers it imports.

    techniques: {rid: (blob, imports)}; built: {buffer_rid: LE primary bytes}.
    Returns [(kind, technique_name, stage, name, buffer_rid)] with kind
    'internal' (a runtime ASSERT in PostFixUpShaderConstants -- hard) or
    'external' (a runtime "Missing shader constant from table" log line -- soft;
    the 19 *_Instanced techniques' InstancingIndexArray/InstancingMatrixArray
    are a KNOWN gap of the TUB instanced sources, logged as such by the engine).

    This is the check that would have caught the Godray fallback defect at
    conversion time instead of at TRK_UNIT83 stream-in."""
    problems = []
    for rid, (blob, imports) in sorted(techniques.items()):
        tname = st.technique_name(blob, le=technique_le)
        lists = st.technique_constant_lists(blob, le=technique_le)
        for stage, slot in (('VS', 0), ('PS', 4)):
            key = '%08X' % imports.get(slot, 0)
            prim = built.get(key)
            if prim is None:
                continue
            have = set(v[0] for v in st.pc_program_buffer_variables(prim))
            for _h, name in lists[stage]['internal']:
                if name not in have:
                    problems.append(('internal', tname, stage, name, key))
            for name in lists[stage]['external']:
                if name not in have:
                    problems.append(('external', tname, stage, name, key))
    return problems


def report_contract(problems, strict):
    hard = [p for p in problems if p[0] == 'internal']
    soft = [p for p in problems if p[0] == 'external']
    for kind, tname, stage, name, key in soft:
        print('WARN  %-60s %s external %-28s absent from program %s'
              % (tname, stage, name, key))
    for kind, tname, stage, name, key in hard:
        print('ERROR %-60s %s INTERNAL %-28s absent from program %s '
              '(runtime assert: "Tyring to postfixup a constant not present in the '
              'programbuffer")' % (tname, stage, name, key))
    if hard and strict:
        raise SystemExit('%d technique internal constant(s) missing from their compiled '
                         'program(s) -- the shader source for those techniques must '
                         'declare AND consume them (see fallback_world.fx header / '
                         'recovered/).' % len(hard))
    return len(hard)


def check(in_x360_bundle, pc_bundle):
    """Read-only: report every technique constant the PC bundle's compiled
    programs cannot satisfy (and, for reference, whether the X360 program had it)."""
    work = tempfile.mkdtemp(prefix='shaderschk_')
    try:
        ex_x, ex_p = os.path.join(work, 'x360'), os.path.join(work, 'pc')
        run([YAP, 'e', in_x360_bundle, ex_x])
        run([YAP, 'e', pc_bundle, ex_p])
        techniques, _buffers = collect(ex_x)          # BE technique blobs + imports
        pdir = os.path.join(ex_p, 'ShaderProgramBuffer')
        built = {}
        for f in os.listdir(pdir):
            if f.endswith('_header.dat'):
                built[f[:-len('_header.dat')]] = open(os.path.join(pdir, f), 'rb').read()
        problems = check_constant_contract(techniques, built, technique_le=False)
        xdir = os.path.join(ex_x, 'ShaderProgramBuffer')
        for kind, tname, stage, name, key in problems:
            xprim = open(os.path.join(xdir, key + '_header.dat'), 'rb').read()
            xhave = set(v[0] for v in st.program_buffer_variables(xprim))
            print('%-8s %-60s %s %-28s PC program %s lacks it; X360 program %s'
                  % (kind.upper(), tname, stage, name, key,
                     'HAS it' if name in xhave else 'lacks it too'))
        n = report_contract(problems, strict=False)
        print('%d internal (assert) / %d external (logged) mismatches'
              % (n, len(problems) - n))
        return 1 if n else 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


def patch_recovered(pc_bundle, out_bundle, keep_work):
    """Recompile ONLY the techniques that have a recovered/ source and swap their
    ShaderProgramBuffer primaries into an already-converted platform-4 bundle.

    For a box without the TUB HLSL tree (which a full `convert` needs for the
    other ~108 techniques): the result is byte-for-byte the bundle `convert`
    would emit for those resources, everything else is carried through the YAP
    extract -> compile round trip untouched (payload-identical; only the
    trailing pad bytes of the last resource are re-zeroed).  The constant
    contract is re-checked on the patched set."""
    if not os.path.isdir(RECOVERED_FX_DIR):
        raise SystemExit('no recovered/ shader dir: %s' % RECOVERED_FX_DIR)
    work = keep_work or tempfile.mkdtemp(prefix='shaderspatch_')
    os.makedirs(work, exist_ok=True)
    ex = os.path.join(work, 'ex')
    if os.path.isdir(ex):
        shutil.rmtree(ex)
    run([YAP, 'e', pc_bundle, ex])

    # Techniques in a platform-4 bundle are the LE flip: read them LE.
    tdir = os.path.join(ex, 'ShaderTechnique')
    pdir = os.path.join(ex, 'ShaderProgramBuffer')
    tech_map = build_technique_map([RECOVERED_FX_DIR])
    fxc = find_fxc()
    techniques = {}
    patched = []
    for f in sorted(os.listdir(tdir)):
        if not f.endswith('.dat'):
            continue
        rid = f[:-4]
        blob = open(os.path.join(tdir, f), 'rb').read()
        imports = parse_technique_imports(os.path.join(tdir, f + '_imports.yaml'))
        techniques[rid] = (blob, imports)
        # LE technique name: the +0x94 word is flipped, the string is raw.
        noff = struct.unpack_from('<I', blob, 0x94)[0]
        name = blob[noff:blob.index(b'\0', noff)].decode('ascii')
        hit = tech_map.get(name.lower())
        if hit is None:
            continue
        fx, vs_entry, ps_entry = hit
        for slot, entry, profile in ((0, vs_entry, 'vs_3_0'), (4, ps_entry, 'ps_3_0')):
            key = '%08X' % imports[slot]
            out_path = os.path.join(work, '%s_%s.fxo' % (key, profile))
            bytecode = compile_entry(fxc, fx, entry, profile, DEFAULT_INCLUDE_DIR, out_path)
            shader_type = 0 if profile.startswith('vs') else 1
            prim, sec = st.build_pc_program_buffer(bytecode, shader_type)
            with open(os.path.join(pdir, key + '_header.dat'), 'wb') as fh:
                fh.write(prim)
            with open(os.path.join(pdir, key + '_body.dat'), 'wb') as fh:
                fh.write(sec)
            patched.append((name, profile, key, os.path.basename(fx)))
    if not patched:
        raise SystemExit('no technique in %s matches a recovered/ source' % pc_bundle)
    for name, profile, key, fx in patched:
        print('patched %-60s %s -> program %s from %s' % (name, profile, key, fx))

    built = {}
    for f in os.listdir(pdir):
        if f.endswith('_header.dat'):
            built[f[:-len('_header.dat')]] = open(os.path.join(pdir, f), 'rb').read()
    problems = check_constant_contract(techniques, built, technique_le=True)
    report_contract(problems, strict=True)

    # YAP writes `<res>.dat_imports.yaml` on extract but reads `<res>_imports.yaml`
    # on compile -- without the rename every import table is silently dropped.
    for lroot, _dirs, lfiles in os.walk(ex):
        for f in lfiles:
            if f.endswith('.dat_imports.yaml'):
                base = f[:-len('.dat_imports.yaml')]
                if base.endswith('_header'):
                    base = base[:-len('_header')]
                os.replace(os.path.join(lroot, f), os.path.join(lroot, base + '_imports.yaml'))
    run([YAP, 'c', ex, out_bundle])
    if not keep_work:
        shutil.rmtree(work, ignore_errors=True)
    return patched


def convert(in_bundle, out_bundle, mode, fx_dirs, use_fallback, keep_work,
            allow_contract_errors=False):
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
        built = {}
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
            built[rid] = prim
        # --- constant contract: every name a technique binds must exist in the
        # compiled program it imports (see check_constant_contract) --------------
        problems = check_constant_contract(techniques, built, technique_le=False)
        manifest['contract_errors'] = report_contract(problems,
                                                      strict=not allow_contract_errors)
        manifest['contract_warnings'] = len([p for p in problems if p[0] == 'external'])

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
    cv.add_argument('--allow-contract-errors', action='store_true',
                    help='report but do not fail on technique INTERNAL constants missing '
                         'from their compiled programs -- ONLY for the deliberate '
                         'all-fallback diagnostic bundle (MINIMAL_PATH.md option A), '
                         'which asserts in PostFixUpShaderConstants for every such '
                         'material at stream-in')
    cv.add_argument('--keep-work', default=None)
    ck = sub.add_parser('check', help='report technique constants the PC bundle\'s '
                                       'programs cannot satisfy (read-only)')
    ck.add_argument('in_x360_bundle')
    ck.add_argument('pc_bundle')
    pr = sub.add_parser('patch-recovered',
                        help='recompile only the recovered/ techniques and swap their '
                             'program buffers into an existing platform-4 bundle '
                             '(no TUB tree needed)')
    pr.add_argument('pc_bundle')
    pr.add_argument('out_bundle')
    pr.add_argument('--keep-work', default=None)
    a = ap.parse_args()
    if a.cmd == 'check':
        return check(a.in_x360_bundle, a.pc_bundle)
    if a.cmd == 'patch-recovered':
        patch_recovered(a.pc_bundle, a.out_bundle, a.keep_work)
        return 0
    fx_dirs = a.fxdir or [DEFAULT_FX_DIR]
    # The playground dir joins ONLY the default search (an explicit --fxdir means the
    # caller is choosing its own sources), and always AFTER Shaders/ -- see the banner on
    # DEFAULT_PLAYGROUND_FX_DIR for the ZOnlyNull collision that ordering avoids.
    if a.fxdir is None and os.path.isdir(DEFAULT_PLAYGROUND_FX_DIR):
        fx_dirs = fx_dirs + [DEFAULT_PLAYGROUND_FX_DIR]
    # Recovered-from-microcode shaders always outrank the TUB tree and the fallback.
    if os.path.isdir(RECOVERED_FX_DIR) and RECOVERED_FX_DIR not in fx_dirs:
        fx_dirs = [RECOVERED_FX_DIR] + fx_dirs
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
            'The nushaders HLSL is a SUBMODULE; the usual cause is a checkout that has '
            'not initialised it:\n'
            '    git submodule update --init tools/nushaders\n'
            'Otherwise set NUSHADERS_TUB (or [inputs].nushaders_tub in build.config.toml) '
            'to a gamedb root containing Shaders/, point --fxdir at your copy, or -- if '
            'you really want the all-fallback diagnostic bundle -- ask for it explicitly '
            'with `--fallback --fxdir <nonexistent-dir>` (MINIMAL_PATH.md option A).'
            % DEFAULT_FX_DIR)
    if a.cmd == 'inventory':
        inventory(a.in_bundle, fx_dirs)
        return 0
    manifest = convert(a.in_bundle, a.out_bundle, a.mode, fx_dirs,
                       a.fallback, a.keep_work, a.allow_contract_errors)
    print('manifest:', manifest)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
