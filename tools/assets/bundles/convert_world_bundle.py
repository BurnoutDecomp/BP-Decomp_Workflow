#!/usr/bin/env python3
"""Convert an X360 ARTIST world bundle (TRK_UNIT<N>_GR.BNDL, GLOBALBACKDROPS,
WORLDTEX...) toward the platform-4 x64 form the reconstructed engine loads.

Per-type state (2026-07-25 -- see scratch/wem_recon_checkpoint.md TASK 3):
  Texture       PORTED  via Volatility porttexture (x360 -> bprx64), the
                convert_x360_bundle.py flow.
  InstanceList  PORTED  via Volatility importresource(X360) -> exportresource
                (TUB): the engine's committed consumer keeps the 32-bit LE
                layout (80-byte stride, u32 pointer slots) == the TUB format.
                Verified byte-exact endian flip on TRK_UNIT285.
  Model         PORTED  same TUB path (Volatility type name "Scene").
                NB Volatility rebuilds two serialized-null pointer slots
                (+0x18/+0x1C) with real offsets -- verify vs CgsModelResource-
                Type FixUp when the load path is boot-tested.
  Renderable / VertexDescriptor / Material / MaterialState / MaterialTechnique
  TextureState / PropGraphicsList / PropInstanceData / StaticSoundMap
                PASSTHROUGH (still big-endian!) -- recorded in the manifest;
                the bundle is NOT fully loadable until these land.

Usage:
  py tools/assets/bundles/convert_world_bundle.py <in_x360_bundle> <out_plat4_bundle>
"""
import os
import re
import subprocess
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import renderable_transcode
import world_type_transcode
import tex_transcode

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
YAP = os.path.join(ROOT, 'build', 'tools', 'yap', 'YAP.exe')
VOLA = os.path.join(ROOT, 'build', 'tools', 'volatility', 'Volatility.Cli.exe')
VOLA_RES = os.path.join(ROOT, 'build', 'tools', 'volatility', 'data', 'Resources')

# YAP type-folder name -> (volatility import type, imported-store suffix)
TUB_PORTABLE = {
    'InstanceList': ('InstanceList', 'InstanceList'),
    'Model': ('Model', 'Scene'),   # Volatility stores the game Model as ".Scene"
}
# YAP type-folder name -> world_type_transcode function (validated flips)
FLIP_PORTABLE = {
    'Material': world_type_transcode.transcode_material,
    'MaterialTechnique': world_type_transcode.transcode_materialtechnique,
    'TextureState': world_type_transcode.transcode_texturestate,
    'VertexDescriptor': world_type_transcode.transcode_vertexdescriptor,
    # widening rebuilds (round-trip-proven; PropGraphicsList also rewrites imports)
    'MaterialState': world_type_transcode.transcode_materialstate,
    'PropGraphicsList': world_type_transcode.transcode_propgraphicslist,
    'PropInstanceData': world_type_transcode.transcode_propinstancedata,
    'StaticSoundMap': world_type_transcode.transcode_staticsoundmap,
}
PASSTHROUGH = {
    'PropData',
}


def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit('command failed (%d): %s' % (r.returncode, ' '.join(args[:3])))
    return r.stdout


def port_tub(folder, fname, vtype, store_suffix):
    """X360 -> LE 32-bit (TUB) in place via Volatility import/export."""
    src = os.path.join(folder, fname)
    name = fname[:-len('.dat')] if fname.endswith('.dat') else os.path.splitext(fname)[0]
    run([VOLA, 'importresource', '--format=X360', '--type=%s' % vtype,
         '--path=%s' % src, '--output=x', '--overwrite'])
    stored = os.path.join(VOLA_RES, '%s.%s' % (name, store_suffix))
    if not os.path.isfile(stored):
        raise SystemExit('imported store missing: %s' % stored)
    run([VOLA, 'exportresource', '--format=TUB', '--respath=%s.%s' % (name, store_suffix),
         '--outpath=%s' % src, '--overwrite'])
    os.remove(stored)


def port_texture(work, folder, rid):
    """X360 split texture (rid_header.dat + rid_body.dat) -> the serialised
    renderengine::Texture header + a tight linear mip chain, in place.

    Shares the single texture porter with convert_texture_bundle.py; `work` is
    unused since the Volatility PortTexture staging was retired (its pixel
    output missed the GPUENDIAN_8IN16 swap and lost the packed mip tail -- see
    tex_transcode / x360_tex)."""
    hdr = os.path.join(folder, rid + '_header.dat')
    body = os.path.join(folder, rid + '_body.dat')
    tex_transcode.port_texture_files(hdr, body)


def convert(in_bundle, out_bundle):
    work = tempfile.mkdtemp(prefix='worldbndl_')
    manifest = {'ported': {}, 'passthrough': {}}
    try:
        ex = os.path.join(work, 'ex')
        run([YAP, 'e', in_bundle, ex])

        # Renderables first: their vertex-payload swap reads the STILL-BE
        # VertexDescriptor blobs (renderable_transcode owns headers + imports
        # rewrite + the _body payload swap, in place).
        if os.path.isdir(os.path.join(ex, 'Renderable')):
            manifest['ported']['Renderable'] = renderable_transcode.convert_dir(ex)

        for entry in sorted(os.listdir(ex)):
            folder = os.path.join(ex, entry)
            if not os.path.isdir(folder):
                continue
            files = [f for f in os.listdir(folder)
                     if not f.endswith('.yaml') and not f.endswith('_imports.yaml')]
            if entry == 'Renderable':
                continue   # already ported above
            if entry in FLIP_PORTABLE:
                fn = FLIP_PORTABLE[entry]
                for f in files:
                    if f.endswith('_body.dat'):
                        continue
                    fp = os.path.join(folder, f)
                    with open(fp, 'rb') as fh:
                        data = fh.read()
                    imp_path = fp + '_imports.yaml'
                    imp_text = None
                    if os.path.isfile(imp_path):
                        with open(imp_path, 'r', encoding='utf-8') as fh:
                            imp_text = fh.read()
                    out, new_imp = fn(data, imp_text)
                    with open(fp, 'wb') as fh:
                        fh.write(out)
                    if new_imp is not None and imp_text is not None and new_imp != imp_text:
                        with open(imp_path, 'w', encoding='utf-8') as fh:
                            fh.write(new_imp)
                manifest['ported'][entry] = len(files)
                continue
            if entry in TUB_PORTABLE:
                vtype, suffix = TUB_PORTABLE[entry]
                for f in files:
                    if f.endswith('_body.dat'):
                        continue
                    port_tub(folder, f, vtype, suffix)
                manifest['ported'][entry] = len(files)
            elif entry == 'Texture':
                count = 0
                for f in files:
                    if not f.endswith('_header.dat'):
                        continue
                    port_texture(work, folder, f[:-len('_header.dat')])
                    count += 1
                manifest['ported'][entry] = count
            elif entry in PASSTHROUGH:
                manifest['passthrough'][entry] = len(files)
            else:
                manifest['passthrough'][entry] = len(files)
                sys.stderr.write('WARNING: unknown resource type folder %s (passthrough)\n' % entry)

        # YAP sidecar naming mismatch fix: extraction emits '<file>.dat_imports.yaml'
        # (extract.cpp outputImports: generateFilePath()+importsSuffix) but creation
        # looks up '<ID>_imports.yaml' (yap.cpp validateImports: chopped suffix) --
        # without this rename YAP c silently drops EVERY import (missing sidecar ->
        # continue), stripping the bundle's whole import table.
        for lroot, _dirs, lfiles in os.walk(ex):
            for f in lfiles:
                if f.endswith('.dat_imports.yaml'):
                    base = f[:-len('.dat_imports.yaml')]
                    if base.endswith('_header'):
                        base = base[:-len('_header')]
                    os.replace(os.path.join(lroot, f),
                               os.path.join(lroot, base + '_imports.yaml'))

        # meta: platform 2 -> 4, uncompressed (the PC loader path reads raw).
        meta_path = os.path.join(ex, '.meta.yaml')
        with open(meta_path, 'r', encoding='utf-8') as fh:
            meta = fh.read()
        meta = re.sub(r'(^\s*platform:\s*)2\s*$', r'\g<1>4', meta, flags=re.M)
        meta = re.sub(r'(^\s*compressed:\s*)true\s*$', r'\g<1>false', meta, flags=re.M)
        with open(meta_path, 'w', encoding='utf-8') as fh:
            fh.write(meta)

        run([YAP, 'c', ex, out_bundle])
        return manifest
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    if len(sys.argv) != 3:
        sys.stderr.write(__doc__)
        return 2
    manifest = convert(sys.argv[1], sys.argv[2])
    print('ported     :', manifest['ported'])
    print('passthrough:', manifest['passthrough'], '(STILL BIG-ENDIAN)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
