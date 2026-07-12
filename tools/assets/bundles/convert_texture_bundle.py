#!/usr/bin/env python3
"""Convert a stock X360 texture-only bundle (GUITEXTURES.BIN,
SMALL8X8WHITESQUARE.BUNDLE, ...) to the x64 PC port form the reconstructed
engine loads: platform-4, uncompressed, little-endian, with each Texture
resource's pixel data ported by Volatility (de-tile + endian + mip repack) and
its header transcoded to the serialised renderengine::Texture x64 object the
loader's FixUp path (renderengine::Texture::Create) actually reads -- see
tex_transcode.py for the two header layouts.

Usage:
  py tools/assets/bundles/convert_texture_bundle.py <in_x360_bundle> <out_plat4_bundle>

Verify with: py tools/assets/bundles/dump_texture_bundle.py <out_plat4_bundle>
"""
import os
import subprocess
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tex_transcode

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
YAP = os.path.join(ROOT, 'build', 'tools', 'yap', 'YAP.exe')


def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit('command failed (%d): %s' % (r.returncode, args[0]))
    return r.stdout


def convert(in_bundle, out_bundle):
    work = tempfile.mkdtemp(prefix='texbndl_')
    try:
        ex = os.path.join(work, 'ex')
        run([YAP, 'e', in_bundle, ex])
        ported = tex_transcode.port_textures(ex, work, verbose=True)

        meta = os.path.join(ex, '.meta.yaml')
        txt = open(meta).read().replace('platform: 2', 'platform: 4') \
                               .replace('compressed: true', 'compressed: false')
        open(meta, 'w').write(txt)
        run([YAP, 'c', ex, out_bundle])
        print('%s: ported %d texture(s) -> platform-4 %s'
              % (os.path.basename(in_bundle), ported, out_bundle))
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    convert(sys.argv[1], sys.argv[2])
