#!/usr/bin/env python3
"""Convert a stock X360 Flapt HUD bundle (FLAPTHUD.BUNDLE / FLAPTHUDSD.BUNDLE:
33 Texture resources + 1 FlaptFile resource type 0x10020) to the x64 PC port
form (platform-4, uncompressed, little-endian):

  1. YAP e            -- decompress + split resources (+ per-resource imports.yaml).
  2. Volatility PortTexture x360 -> bprx64 for every Texture resource
     (deswizzle + endian) + header transcode to the engine's serialised
     renderengine::Texture x64 form (tex_transcode.py -- Volatility's own
     header output is the REMASTER layout, which the reconstructed loader
     does not read).
  3. flapt_widen      -- the FlaptFile payload: BE/32-bit -> LE/64-bit graph
     re-serialisation (see flapt_widen.py for the format authority notes).
  4. rebuild the FlaptFile import table: same texture resource ids, in the same
     import-slot order, at the NEW widened mpapTextures slot offsets (8-byte
     stride). Like the stock X360 bundle (image 0x106CF0 + 33*16 = mem0 size
     0x106F00), the 16-byte ImportEntry run {u64 id, u32 slotOffset, pad} is
     APPENDED to the payload, inside the resource's mem0 data.
  5. patch .meta.yaml platform 4 / uncompressed, YAP c repack.
  6. YAP's repack does not carry import metadata (its e/c round-trip zeroes
     muImportOffset/muImportCount -- the GUIAPT pipeline patched the container
     directly for the same reason, cf. apt_widen_4to8.py), so the two entry
     fields are patched into the output bundle afterwards.

Usage:
  py tools/assets/bundles/convert_flapt_bundle.py <in_x360.bundle> <out_plat4.bundle>

Verify with:
  py tools/assets/bundles/dump_flapt.py <in_x360.bundle>  > a
  py tools/assets/bundles/dump_flapt.py <out_plat4.bundle> > b
  diff a b        (must be empty)
"""
import os
import re
import struct
import subprocess
import sys
import tempfile
import shutil
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flapt_widen
import tex_transcode

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
YAP = os.path.join(ROOT, 'build', 'tools', 'yap', 'YAP.exe')


def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit('command failed (%d): %s' % (r.returncode, args[0]))
    return r.stdout


def widen_flapt(ex):
    fdir = os.path.join(ex, 'FlaptFile')
    dats = [p for p in glob.glob(os.path.join(fdir, '*.dat'))
            if not p.endswith('_imports.yaml')]
    assert len(dats) == 1, dats
    dat = dats[0]

    img = flapt_widen.FlaptImage(open(dat, 'rb').read())
    covered, gaps = img.coverage()
    out, slots = flapt_widen.widen(img)
    open(dat, 'wb').write(out)
    for w in img.warnings:
        print('  !! ' + w)
    print('  FlaptFile %s: %#x -> %#x bytes (coverage %.2f%%, %d import slots)'
          % (os.path.basename(dat), img.size, len(out),
             100.0 * covered / img.size, len(slots)))

    # rebuild the import table: same resource ids, same slot order, new slot
    # offsets -- appended to the payload as LE 16-byte ImportEntry records
    # {u64 resourceId, u32 slotOffset, u32 pad}, exactly where the stock X360
    # bundle keeps them (inside the resource's mem0 data, after the image).
    imp = dat + '_imports.yaml'
    entries = []
    for ln in open(imp).read().splitlines():
        m = re.match(r'\s*-\s*(0x[0-9a-fA-F]+)\s*:\s*(0x[0-9a-fA-F]+)\s*$', ln)
        if m:
            entries.append((int(m.group(1), 16), int(m.group(2), 16)))
    assert len(entries) == len(slots), \
        'import count mismatch: yaml %d vs widened slots %d' % (len(entries), len(slots))
    table = b''.join(struct.pack('<QII', rid, new_off, 0)
                     for (_old, rid), new_off in zip(entries, slots))
    assert len(out) % 16 == 0, 'widened image not 16-aligned'
    with open(dat, 'ab') as f:
        f.write(table)
    os.remove(imp)   # YAP c ignores it; the entry fields are patched post-repack
    print('  imports: %d entries rebuilt at payload +%#x '
          '(4-byte stride -> 8-byte stride slots)' % (len(entries), len(out)))
    return len(out), len(entries)


def patch_entry_imports(out_bundle, import_offset, import_count):
    """YAP c writes muImportOffset/muImportCount as 0; patch the FlaptFile
    (type 0x10020) entry fields in the finished platform-4 bundle."""
    d = bytearray(open(out_bundle, 'rb').read())
    assert d[:4] == b'bnd2'
    n_ent = struct.unpack_from('<I', d, 0x10)[0]
    ent_off = struct.unpack_from('<I', d, 0x14)[0]
    patched = 0
    for e in range(n_ent):
        b = ent_off + 0x40 * e
        if struct.unpack_from('<I', d, b + 0x38)[0] != 0x10020:
            continue
        struct.pack_into('<I', d, b + 0x34, import_offset)   # muImportOffset
        struct.pack_into('<H', d, b + 0x3C, import_count)    # muImportCount
        patched += 1
    assert patched == 1, 'expected exactly one FlaptFile entry, patched %d' % patched
    open(out_bundle, 'wb').write(d)


def convert(in_bundle, out_bundle):
    work = tempfile.mkdtemp(prefix='flapt_')
    try:
        ex = os.path.join(work, 'ex')
        run([YAP, 'e', in_bundle, ex])

        ported = tex_transcode.port_textures(ex, work)
        import_offset, import_count = widen_flapt(ex)

        meta = os.path.join(ex, '.meta.yaml')
        txt = open(meta).read().replace('platform: 2', 'platform: 4') \
                               .replace('compressed: true', 'compressed: false')
        open(meta, 'w').write(txt)
        run([YAP, 'c', ex, out_bundle])
        patch_entry_imports(out_bundle, import_offset, import_count)
        print('%s: %d texture(s) ported + FlaptFile widened (%d imports @+%#x) '
              '-> platform-4 %s' % (os.path.basename(in_bundle), ported,
                                    import_count, import_offset, out_bundle))
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    convert(sys.argv[1], sys.argv[2])
