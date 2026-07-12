#!/usr/bin/env python3
"""Convert the stock X360 GUI data banks (POPUPS.PUP / HUDMESSAGES.HM /
HUDMESSAGESEQUENCES.HMSC) to the x64 PC port form (platform-4, uncompressed,
little-endian, 64-bit serialised pointers) that the reconstructed BundleLoader +
the CgsGui resource structs read.

Format authorities (data must match the loader, NEVER bend the loader):
  0x1F GuiPopup                  b5-decomp/src/GameShared/GameClasses/Gui/Model/Resources/CgsGuiPopupResource.{h,cpp}
                                 + DecFIGS DWARF CgsGuiPopupResource.h:97 (GuiPopup record, pointer-free, stride 0xC0)
  0x2C HudMessage                b5-decomp/.../CgsGuiHudMessage.{h,cpp}: x64 GuiHudMessageResource
                                 {GuiHudMessageData** @0, s32 size @8, s32 count @0xC}; GuiHudMessageData is
                                 pointer-free, stride 0x170, layout-identical 32/64-bit (verified: record CgsID ==
                                 CgsIDCompress(macMessageId) on the stock data).
  0x2E HudMessageSequence        NO committed PC reader yet. Layout inferred from the stock data and verified via
                                 the CgsID codec (leading u64 == CgsIDCompress(the char[13] name that follows)):
                                 {CgsID @0, char[13]+pad @8, u32 @0x18, u32 usedSize @0x1C, u32[9] zeros @0x20,
                                  s32 numEntries @0x44, Entry[(size-0x48)/0x30] @0x48} with
                                 Entry = {CgsID messageId @0, f32 @8, u32[9] @0xC} (stride 0x30).
                                 POINTER-FREE -> the 64-bit form is byte-layout-identical; this is a pure endian swap.
                                 RE-VERIFY when the HudMessageSequence reader TU lands.
  0x2F HudMessageSequenceDictionary  NO committed PC reader yet. The stock payload is exactly the
                                 GuiHudMessageListResource shape (CgsGuiHudMessageList.cpp):
                                 {s32 size @0, s32 count @4, char** table @8} + u32 name offsets + char[13] names.
                                 Widened the same way as its committed sibling (table pointer/slots -> u64).

Serialised-pointer convention (the project x64 discipline, cf. CgsAptDataHeader.cpp):
pointer slots are 64-bit little-endian FILE-RELATIVE OFFSETS from the resource base.
A no-op FixUp + consumer-side (realBase64 + offset) transcode works, and so does a
future in-place `slot += base` relocate (the slots are wide enough for a full address).

Every output byte derives from the input: names/pads are copied verbatim, numeric
fields are byte-swapped, and the only synthesised values are the re-laid-out table
offsets / size fields that the widening itself forces.

Usage:
  py tools/assets/bundles/convert_gui_banks.py <in_x360_bundle> <out_plat4_bundle>

Verify with: py tools/assets/bundles/dump_gui_banks.py <bundle>   (both forms)
"""
import os
import struct
import subprocess
import sys
import tempfile
import shutil
import glob

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
YAP = os.path.join(ROOT, 'build', 'tools', 'yap', 'YAP.exe')


def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit('command failed (%d): %s' % (r.returncode, args[0]))
    return r.stdout


def align(v, a):
    return (v + a - 1) & ~(a - 1)


def swap_fields(src, out, offset, fmt):
    """Byte-swap the struct.fmt fields at offset from BE src into LE out."""
    vals = struct.unpack_from('>' + fmt, src, offset)
    struct.pack_into('<' + fmt, out, offset, *vals)


# ---------------------------------------------------------------------------
# 0x1F GuiPopup: {u32 tableOff, s16 count, s16 size} + u32 offs[] + GuiPopup[count]
# -> {u64 tableOff, s16 count, s16 size, pad} + u64 offs[] + GuiPopup[count]
# GuiPopup record (0xC0, pointer-free, identical 32/64) swap map:
#   +0x00 CgsID(u64)  +0x18 meStyle  +0x1C meIcon  +0x60/0x64 maeMessageParams
#   +0x68 miMessageParamsUsed  +0x8C meButton1Param  +0xB4 meButton2Param
# ---------------------------------------------------------------------------
def conv_guipopup(src):
    table, count, size = struct.unpack_from('>IhH', src, 0)
    assert size == len(src) or size <= len(src), (size, len(src))
    offs = struct.unpack_from('>%dI' % count, src, table)
    stride = 0xC0
    new_table = max(0x40, 0x10)               # keep the stock 0x40 table home
    rec_base = align(new_table + 8 * count, 0x10)
    new_size = rec_base + stride * count

    out = bytearray(align(new_size, 0x10))
    struct.pack_into('<QhH', out, 0, new_table, count, new_size)
    for i, off in enumerate(offs):
        rec = bytearray(src[off:off + stride])
        for foff, ffmt in ((0x00, 'Q'), (0x18, 'I'), (0x1C, 'I'), (0x60, '2I'),
                           (0x68, 'I'), (0x8C, 'I'), (0xB4, 'I')):
            swap_fields(src[off:off + stride], rec, foff, ffmt)
        new_off = rec_base + stride * i
        struct.pack_into('<Q', out, new_table + 8 * i, new_off)
        out[new_off:new_off + stride] = rec
    return bytes(out)


# ---------------------------------------------------------------------------
# 0x2C HudMessage: {u32 tableOff, s32 size, s32 count} + u32 offs[] + Data[count]
# -> {u64 tableOff, s32 size, s32 count} + u64 offs[] + Data[count]
# GuiHudMessageData (0x170, pointer-free, identical 32/64) swap map:
#   +0x110 CgsID  +0x118 avail  +0x11C dur  +0x120 wait  +0x124 prio
#   +0x128 thresh +0x12C group  +0x130 s32[3] +0x13C u32[12]
# ---------------------------------------------------------------------------
def conv_hudmessage(src):
    table, size, count = struct.unpack_from('>Iii', src, 0)
    offs = struct.unpack_from('>%dI' % count, src, table)
    stride = 0x170
    new_table = table                          # 0x80: already 8-aligned, keep
    rec_base = align(new_table + 8 * count, 0x10)
    new_size = rec_base + stride * count

    out = bytearray(align(new_size, 0x10))
    struct.pack_into('<Qii', out, 0, new_table, new_size, count)
    for i, off in enumerate(offs):
        rec = bytearray(src[off:off + stride])
        for foff, ffmt in ((0x110, 'Q'), (0x118, 'I'), (0x11C, 'I'), (0x120, 'I'),
                           (0x124, 'i'), (0x128, 'i'), (0x12C, 'I'),
                           (0x130, '3i'), (0x13C, '12I')):
            swap_fields(src[off:off + stride], rec, foff, ffmt)
        new_off = rec_base + stride * i
        struct.pack_into('<Q', out, new_table + 8 * i, new_off)
        out[new_off:new_off + stride] = rec
    return bytes(out)


# ---------------------------------------------------------------------------
# 0x2E HudMessageSequence: pointer-free, layout-identical -> pure endian swap.
# ---------------------------------------------------------------------------
def conv_hudmessagesequence(src):
    out = bytearray(src)
    swap_fields(src, out, 0x00, 'Q')          # CgsID sequence id
    # +0x08..0x17 char[13] name + pad: verbatim
    swap_fields(src, out, 0x18, 'I')
    swap_fields(src, out, 0x1C, 'I')          # used-size word (0x1C8 on stock data)
    swap_fields(src, out, 0x20, '9I')         # zeros on stock data
    swap_fields(src, out, 0x44, 'i')          # numEntries
    n = (len(src) - 0x48) // 0x30
    for i in range(n):
        e = 0x48 + 0x30 * i
        swap_fields(src, out, e, 'Q')         # CgsID message id
        swap_fields(src, out, e + 8, '10I')   # f32 + 9 words (swap-safe as u32s)
    return bytes(out)


# ---------------------------------------------------------------------------
# 0x2F HudMessageSequenceDictionary: {s32 size, s32 count, u32 table @8}
#   + u32 nameOffs[] + char[13] names
# -> {s32 size, s32 count, u64 table @8} + u64 nameOffs[] + names (block-copied)
# ---------------------------------------------------------------------------
def conv_hudmessagesequencedict(src):
    size, count, table = struct.unpack_from('>iiI', src, 0)
    offs = struct.unpack_from('>%dI' % count, src, table)
    str_lo = min(offs)
    str_hi = size                              # names run to the used-size mark
    new_table = 0x10
    new_str_lo = align(new_table + 8 * count, 0x10)
    delta = new_str_lo - str_lo
    new_size = new_str_lo + (str_hi - str_lo)

    out = bytearray(align(new_size, 0x10))
    struct.pack_into('<iiQ', out, 0, new_size, count, new_table)
    for i, off in enumerate(offs):
        struct.pack_into('<Q', out, new_table + 8 * i, off + delta)
    out[new_str_lo:new_str_lo + (str_hi - str_lo)] = src[str_lo:str_hi]
    return bytes(out)


CONVERTERS = {
    'GuiPopup': conv_guipopup,
    'HudMessage': conv_hudmessage,
    'HudMessageSequence': conv_hudmessagesequence,
    'HudMessageSequenceDictionary': conv_hudmessagesequencedict,
}


def convert(in_bundle, out_bundle):
    work = tempfile.mkdtemp(prefix='guibank_')
    try:
        ex = os.path.join(work, 'ex')
        run([YAP, 'e', in_bundle, ex])

        converted = 0
        for type_name, fn in CONVERTERS.items():
            tdir = os.path.join(ex, type_name)
            if not os.path.isdir(tdir):
                continue
            for dat in glob.glob(os.path.join(tdir, '*.dat')):
                src = open(dat, 'rb').read()
                open(dat, 'wb').write(fn(src))
                converted += 1
                print('  %s/%s: %#x -> %#x bytes' % (
                    type_name, os.path.basename(dat), len(src),
                    os.path.getsize(dat)))

        # any other type in the bundle would pass through un-converted (inert
        # big-endian) - report it so nothing slips by silently.
        for entry in sorted(os.listdir(ex)):
            p = os.path.join(ex, entry)
            if os.path.isdir(p) and entry not in CONVERTERS:
                print('  !! unhandled resource type dir: %s (passed through '
                      'big-endian, will NOT load)' % entry)

        meta = os.path.join(ex, '.meta.yaml')
        txt = open(meta).read().replace('platform: 2', 'platform: 4') \
                               .replace('compressed: true', 'compressed: false')
        open(meta, 'w').write(txt)
        run([YAP, 'c', ex, out_bundle])
        print('%s: converted %d resource(s) -> platform-4 %s'
              % (os.path.basename(in_bundle), converted, out_bundle))
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    convert(sys.argv[1], sys.argv[2])
