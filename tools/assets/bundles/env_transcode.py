#!/usr/bin/env python3
"""Convert the stock X360 (platform-2) ENVIRONMENTSETTINGS bundles to the x64 PC port form
(platform-4, uncompressed, little-endian) that the reconstructed BundleLoader can read.

WHY THIS EXISTS
    build/game/ENVIRONMENTSETTINGS/*.BUNDLE shipped byte-identical to the X360 originals --
    platform 2, big-endian -- and the loader hard-requires platform 4, so the environment
    keyframes were never loadable. That is the data half of "the sky is black": the sky
    colours, scattering and cloud parameters all live in these keyframes.

    The generic convert_x360_bundle.py handles the CONTAINER (YAP decompress -> meta
    platform 4 -> repack) but passes resource payloads through verbatim, which leaves the
    env records big-endian and therefore inert. This adds the missing payload porter.

WHAT THE PAYLOAD PORT IS
    The three env resource types are fixed-size, POINTER-FREE records of 4-byte fields, so
    the port is a pure 4-byte endian swap -- no relayout, no widening:

      65554 (0x10012) Keyframe   0x240 bytes, align 16   (KeyframeResourceType::
                                 GetSerialisedResourceDescriptor @0x8267D220)
      65555 (0x10013) TimeLine
      65556 (0x10014) Dictionary

    The Keyframe interior is asm-attested in the committed headers -- ScatteringData @0x090
    (size 0xA8), LightingData @0x140 (0x84), CloudsData @0x1D0 (0x6C) -- and every field in
    them is a f32 or a 4-byte scalar (colours are 3-float vectors on 16-byte strides with
    4-byte pads). That is what makes a uniform 32-bit swap correct here; do NOT copy this
    approach to a record with u16/u8 fields without checking.

VALIDATION (run with --verify, on by default)
    The port is round-tripped: the ported little-endian payload is re-read and every 4-byte
    lane compared against the big-endian source read as big-endian. Any mismatch aborts. The
    keyframe version word (+0) is additionally asserted == 8 (the X360 `*a2 == 8` check in
    KeyframeResourceType::FixUp) BOTH before and after, which catches a swap applied to the
    wrong region.

Usage:
  py tools/assets/bundles/env_transcode.py <in_x360.bundle> <out_plat4.bundle>
  py tools/assets/bundles/env_transcode.py --all        # convert the whole ENVIRONMENTSETTINGS tree in place
"""

import os
import shutil
import struct
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
YAP = os.path.join(ROOT, 'build', 'tools', 'yap', 'YAP.exe')
ENVDIR = os.path.join(ROOT, 'build', 'game', 'ENVIRONMENTSETTINGS')

# resource type ids -> friendly name. All three are fixed-size pointer-free 4-byte-field records.
ENV_TYPES = {65554: 'Keyframe', 65555: 'TimeLine', 65556: 'Dictionary'}
KEYFRAME_TYPE = 65554
KEYFRAME_VERSION = 8


def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit('FAILED: %s\n%s\n%s' % (' '.join(args), r.stdout, r.stderr))
    return r


def swap32(buf):
    """Byte-swap every complete 4-byte lane; a ragged tail is left alone (there is none in
    practice -- every env record size is a multiple of 4)."""
    b = bytearray(buf)
    n = len(b) - (len(b) % 4)
    for i in range(0, n, 4):
        b[i:i + 4] = b[i:i + 4][::-1]
    return bytes(b)


def port_payload(data, type_id, label):
    """BE -> LE for one env resource, with the round-trip check."""
    out = swap32(data)

    # every 4-byte lane must read the same value BE-from-source as LE-from-output
    n = len(data) - (len(data) % 4)
    for off in range(0, n, 4):
        be = struct.unpack_from('>I', data, off)[0]
        le = struct.unpack_from('<I', out, off)[0]
        if be != le:
            raise SystemExit('%s: lane %#x mismatch after swap (%08X vs %08X)' % (label, off, be, le))

    if type_id == KEYFRAME_TYPE and len(out) >= 4:
        src_ver = struct.unpack_from('>i', data, 0)[0]
        dst_ver = struct.unpack_from('<i', out, 0)[0]
        if src_ver != KEYFRAME_VERSION or dst_ver != KEYFRAME_VERSION:
            raise SystemExit('%s: keyframe version %d/%d, expected %d -- wrong region swapped?'
                             % (label, src_ver, dst_ver, KEYFRAME_VERSION))
    return out


def read_meta_types(meta_text):
    """Map resource id (UPPER hex, no 0x) -> type id from YAP's .meta.yaml, whose shape is

        resources:
          0x4c48fd46:
            type: 0x10013
            alignment:
              - 0x10
    """
    types = {}
    cur = None
    for line in meta_text.splitlines():
        t = line.strip()
        if t.startswith('0x') and t.endswith(':'):
            cur = t[2:-1].upper()
        elif t.startswith('type:') and cur is not None:
            try:
                types[cur] = int(t.split(':', 1)[1].strip(), 0)
            except ValueError:
                pass
            cur = None
    return types


def convert(in_bundle, out_bundle):
    if not os.path.exists(YAP):
        raise SystemExit('YAP not built: %s' % YAP)

    ex = tempfile.mkdtemp(prefix='envtx_')
    try:
        run([YAP, 'e', in_bundle, ex])

        meta = os.path.join(ex, '.meta.yaml')
        txt = open(meta).read()
        types = read_meta_types(txt)

        # YAP lays the payloads out as <TypeName>/<ID>.dat (plus <ID>.dat_imports.yaml
        # beside them), NOT as flat .dat files in the extraction root.
        ported = 0
        skipped = []
        for dirpath, _dirs, files in os.walk(ex):
            for name in sorted(files):
                if not name.endswith('.dat'):
                    continue
                rid = os.path.splitext(name)[0].upper()
                tid = types.get(rid)
                if tid is None:
                    skipped.append(name)
                    continue
                if tid not in ENV_TYPES:
                    skipped.append('%s (type %#x)' % (name, tid))
                    continue
                fp = os.path.join(dirpath, name)
                data = open(fp, 'rb').read()
                open(fp, 'wb').write(port_payload(data, tid, '%s[%s]' % (ENV_TYPES[tid], rid)))
                ported += 1
                print('    ported %-10s %-14s %4d bytes' % (ENV_TYPES[tid], name, len(data)))

        if skipped:
            print('    passed through verbatim: %s' % ', '.join(skipped))
        if ported == 0:
            raise SystemExit('    NO env resources ported -- the meta parse or the payload '
                             'walk is wrong. Refusing to emit a half-converted bundle.')

        # The import sidecars stay exactly where YAP wrote them: this tool round-trips the
        # same layout YAP produced, so no rename is needed (and renaming would lose them).

        txt = txt.replace('platform: 2', 'platform: 4').replace('compressed: true', 'compressed: false')
        open(meta, 'w').write(txt)

        run([YAP, 'c', ex, out_bundle])
    finally:
        shutil.rmtree(ex, ignore_errors=True)

    d = open(out_bundle, 'rb').read(16)
    plat = struct.unpack_from('<I', d, 8)[0]
    if plat != 4:
        raise SystemExit('%s: output platform is %d, expected 4' % (out_bundle, plat))
    print('  -> %s  (platform 4, %d bytes)' % (os.path.basename(out_bundle), os.path.getsize(out_bundle)))


def main():
    args = sys.argv[1:]
    if args == ['--all']:
        targets = []
        for dirpath, _dirs, files in os.walk(ENVDIR):
            for f in files:
                if f.upper().endswith('.BUNDLE'):
                    targets.append(os.path.join(dirpath, f))
        if not targets:
            raise SystemExit('no bundles under %s' % ENVDIR)
        for t in targets:
            d = open(t, 'rb').read(16)
            plat_be = struct.unpack_from('>I', d, 8)[0]
            plat_le = struct.unpack_from('<I', d, 8)[0]
            if plat_le == 4:
                print('%s: already platform 4, skipping' % os.path.relpath(t, ENVDIR))
                continue
            if plat_be != 2:
                print('%s: platform %d (not X360), skipping' % (os.path.relpath(t, ENVDIR), plat_be))
                continue
            print('%s:' % os.path.relpath(t, ENVDIR))
            bak = t + '.x360'
            if not os.path.exists(bak):
                shutil.copy2(t, bak)      # keep the console original beside it
            convert(bak, t)
        return
    if len(args) != 2:
        raise SystemExit(__doc__)
    convert(args[0], args[1])


if __name__ == '__main__':
    main()
