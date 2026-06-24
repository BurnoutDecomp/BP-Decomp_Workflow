#!/usr/bin/env python3
"""Reconvert a stock X360 (platform-2) bnd2 bundle to the x64 PC port format (platform-4,
uncompressed) so the reconstructed BundleLoader (which requires muPlatform==4, uncompressed,
native little-endian x64 payloads) can read it.

Pipeline (uses the project's built tools under build/tools/):
  1. YAP e  <bundle> <tmp>         -- decompress + split resources (Texture = header+body),
                                      emit .meta.yaml + per-resource imports.
  2. volatility PortTexture x360 -> bprx64  for each Texture resource (deswizzle + endian +
                                      header relayout to the x64 PC texture format).
  3. rewrite .meta.yaml  platform: 4, compressed: false.
  4. YAP c  <tmp> <out>            -- repack as a platform-4 (PCx64) little-endian bundle.

Resources whose type has no porter yet (e.g. AptData type 0x1E -- the Flash/APT GUI movie,
not reconstructed) are passed through verbatim. They are X360 big-endian, so they are inert:
the loader skips fixup for any resource type not in its registry. The texture(s) in the bundle
are fully ported and loadable.

Usage:
  py tools/assets/bundles/convert_x360_bundle.py <in_x360.bundle> <out_plat4.bundle>
"""
import os, sys, subprocess, tempfile, shutil, glob

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
YAP = os.path.join(ROOT, 'build', 'tools', 'yap', 'YAP.exe')
VOL = os.path.join(ROOT, 'build', 'tools', 'volatility', 'Volatility.Cli.exe')


def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit(f"command failed ({r.returncode}): {args[0]}")
    return r.stdout


def convert(in_bundle, out_bundle):
    work = tempfile.mkdtemp(prefix='bndl_')
    ex = os.path.join(work, 'ex')
    run([YAP, 'e', in_bundle, ex])

    # port every Texture resource (yap names them <ID>_header.dat + <ID>_body.dat)
    texdir = os.path.join(ex, 'Texture')
    ported = 0
    for hdr in glob.glob(os.path.join(texdir, '*_header.dat')):
        rid = os.path.basename(hdr)[:-len('_header.dat')]
        body = os.path.join(texdir, rid + '_body.dat')
        stage = os.path.join(work, 'tex_' + rid)
        os.makedirs(stage, exist_ok=True)
        # volatility convention: <ID>.dat (header) + <ID>_texture.dat (body)
        shutil.copy(hdr, os.path.join(stage, rid + '.dat'))
        shutil.copy(body, os.path.join(stage, rid + '_texture.dat'))
        run([VOL, 'PortTexture', '--informat=x360', f'--inpath={os.path.join(stage, rid + ".dat")}',
             '--outformat=bprx64', f'--outpath={stage}'])
        # write the ported pair back into the extraction in yap naming
        shutil.copy(os.path.join(stage, rid + '.dat'), hdr)
        shutil.copy(os.path.join(stage, rid + '_texture.dat'), body)
        ported += 1

    meta = os.path.join(ex, '.meta.yaml')
    txt = open(meta).read().replace('platform: 2', 'platform: 4').replace('compressed: true', 'compressed: false')
    open(meta, 'w').write(txt)

    run([YAP, 'c', ex, out_bundle])
    shutil.rmtree(work, ignore_errors=True)
    print(f"{os.path.basename(in_bundle)}: ported {ported} texture(s) -> platform-4 {out_bundle}")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    convert(sys.argv[1], sys.argv[2])
