#!/usr/bin/env python3
"""X360 (big-endian, platform-2) -> PC x64 (little-endian, platform-4) porter for
PARTICLES.BUNDLE -- the effects module's one FX bundle (LoadFXBundle @0x8229C950 loads
it as bundle 13 "particles.bundle" and resolves every effect texture / LION effect /
VFX prop table out of it).

WHAT IS IN IT (measured on the shipped file: 98 resources, 1,059,840 bytes)
    51  Texture (type 0)                      the effect rasters, fxskid / fxsmoke / fxspark ...
     1  TextureNameMap (0x1000B, 65547)       48 { FNV-1a(lion name), gdb texture name } pairs
     1  VFXPropCollection (0x1001B, 65563)    the prop VFX tables (vfxprops_transcode.py)
     1  ParticleDescriptionCollection (0x10008, 65544)
                                              a 41-entry import table of the LEFs below
    41  ParticleDescription (0x1001D, 65565)  the LION .lef effect binaries
     3  VFXMeshCollection (0x10019, 65561)    debris meshes (header + VB/IB body)

HOW EACH ONE IS PORTED -- and why (the deciding fact is always the committed consumer)
  Texture                        x360_tex / tex_transcode: the real Xenos layout -> tight
                                 linear mips + the serialised renderengine::Texture x64
                                 header. Same path GUITEXTURES / WORLDTEX take.
  TextureNameMap                 ENDIAN SWAP ONLY. The committed handler
                                 (SharedClasses/Graphics/TextureNameMapResourceType.cpp)
                                 keeps the console's 32-bit slots: FixUp rebases
                                 `mpEntries` and each entry's `mpGDBTextureName` as
                                 u32 words in place (the project's low-4 GB convention),
                                 so the layout does not widen. Header {u32 entries,
                                 u32 count} @0, Entry {u32 hash, u32 nameOffset} x count
                                 @16, then the NUL-terminated names (bytes, untouched).
  VFXPropCollection              ENDIAN SWAP ONLY -- vfxprops_transcode.py, same reason
                                 (its FixUp rebases 32-bit words in place).
  ParticleDescriptionCollection  ENDIAN SWAP of every u32: {u32 table, u32 count} then
                                 `count` import-slot words. The committed handler
                                 (ParticleDescriptionResourceType.cpp) reads the table
                                 pointer and each slot as u32 and GetImportPointer patches
                                 slot i at byte 4*(i+2) -- 32-bit slots on the host too.
  ParticleDescription (.lef)     PASSTHROUGH, VERBATIM, BIG-ENDIAN. The LION runtime that
                                 reads a .lef (cLionFX::BinLoad @0x82915xxx, the
                                 ~6,650-line sim/render core) is NOT reconstructed, and
                                 ParticleDescriptionResourceType::DeSerialise's BinLoad is
                                 a __debugbreak stub. The type is therefore left
                                 UNREGISTERED on the PC (CgsResourceTypeRegistration.cpp):
                                 the bundle loader creates the resource with its raw bytes
                                 and skips FixUp/DeSerialise, which is exactly what keeps
                                 the boot alive. FLAG PC: DELETE-WHEN cLionFX lands -- then
                                 this needs a real .lef porter (the LION format is
                                 self-describing big-endian; see the Lion SDK headers).
  VFXMeshCollection              PASSTHROUGH, VERBATIM, BIG-ENDIAN. Its consumer is the
                                 debris renderer (BrnDebrisRenderer::RenderDebrisArray
                                 @0x8228B078, absent) and its FixUp wants an x64-ported
                                 renderengine VertexBuffer/IndexBuffer pair that the
                                 world's renderable porter models for Renderables, not for
                                 this MeshHelper container. Left UNREGISTERED on the PC for
                                 the same reason as the .lef. FLAG PC: DELETE-WHEN the
                                 debris renderer lands -- port the header (u32 version +
                                 32 f32 + 4 u32) and the VB/IB with renderable_transcode's
                                 vertex-descriptor machinery.

WHY THE TWO PASSTHROUGHS ARE SAFE FOR THE TYRE MARK. LoadFXBundle @0x8229C950 acquires
the collection, the name map, the five mesh collections and every name-map texture; an
acquire of an unregistered-type resource still RESOLVES (the pool has the raw bytes) --
only FixUp is skipped, and nothing on the skid path dereferences a mesh or a .lef.
TrailSystem::Render reads the fxskid Texture through the name map, both of which are
fully ported here.

VALIDATION (always on -- a real proof, not a smoke test)
  1. structural   every swapped payload's own model must tile it exactly: the name map's
                  entry table at +16, every name offset inside the payload and
                  NUL-terminated; the collection's table at +8 and count == its import
                  count.
  2. identity     swapping each emitted little-endian payload BACK reproduces the input
                  byte for byte (the field map covers every byte it claims).
  3. the picture  the fxskid raster (id CRC32("<gdb name>".lower()) == 0x55AF0DBF) must
                  port to a NON-ZERO mip chain of the modelled size -- the 2026-08-28
                  boostbarmask lesson (a fully-packed texture ported as all zeros).
  4. the output   re-read as bnd2: platform 4, the same 98 ids, and every Texture /
                  TextureNameMap / VFXPropCollection / collection payload decodes in
                  little-endian with the counts above.

Usage:
  py tools/assets/bundles/particles_transcode.py <in_x360.bundle> <out_plat4.bundle>
  py tools/assets/bundles/particles_transcode.py --verify <plat4.bundle>
"""
from __future__ import print_function

import binascii
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
YAP = os.path.join(ROOT, 'build', 'tools', 'yap', 'YAP.exe')

sys.path.insert(0, HERE)
import tex_transcode          # noqa: E402
import vfxprops_transcode     # noqa: E402
import x360_tex               # noqa: E402

TYPE_TEXTURE = 0x0
TYPE_PARTICLE_DESCRIPTION_COLLECTION = 0x10008
TYPE_TEXTURE_NAME_MAP = 0x1000B
TYPE_VFX_MESH_COLLECTION = 0x10019
TYPE_VFX_PROP_COLLECTION = 0x1001B
TYPE_PARTICLE_DESCRIPTION = 0x1001D

# The one raster the tyre mark needs: LoadFXBundle resolves it through the name map by
# TextureNameMap::Entry::HashString("fxskid") (off_82CDAE74) and hands its handle to
# TrailSystem (mTrailTexture / mbIsReady). Its bundle id is CgsResource::ID::HashString
# of the gdb name == CRC32 of the lowercased name (bnd2 carries no names).
FXSKID_GDB_NAME = 'gamedb://burnout5/Burnout/Effects/Textures/fxskid.TextureConfig2d?ID=226049'
FXSKID_ID = 0x55AF0DBF


class PortError(RuntimeError):
    pass


def run(argv):
    r = subprocess.run(argv, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise PortError('command failed (%d): %s' % (r.returncode, argv[0]))
    return r.stdout


def resource_id(gdb_name):
    return binascii.crc32(gdb_name.lower().encode('ascii')) & 0xFFFFFFFF


# ----------------------------------------------------------------------------- name map
def _u32(buf, off, be):
    return struct.unpack_from('>I' if be else '<I', buf, off)[0]


def check_texture_name_map(buf, be, label):
    """Structural model of a serialised BrnParticle::TextureNameMap (the committed
    SerialisedTextureNameMap in TextureNameMapResourceType.cpp): {entries, count} then
    the entry table at align16(8) == 16, then the strings. Returns (entries, count)."""
    if len(buf) < 16:
        raise PortError('%s: name map is only %d bytes' % (label, len(buf)))
    entries, count = _u32(buf, 0, be), _u32(buf, 4, be)
    if entries != 16:
        raise PortError('%s: entry table at %#x, expected 16' % (label, entries))
    if count == 0 or 16 + 8 * count > len(buf):
        raise PortError('%s: count %d does not fit %d bytes' % (label, count, len(buf)))
    for i in range(count):
        name_off = _u32(buf, 16 + 8 * i + 4, be)
        if not (16 + 8 * count <= name_off < len(buf)):
            raise PortError('%s: entry %d name offset %#x outside the payload' % (label, i, name_off))
        if buf.find(b'\0', name_off) < 0:
            raise PortError('%s: entry %d name is not NUL-terminated' % (label, i))
    return entries, count


def swap_texture_name_map(buf, be=True):
    """Byte-swap the two header words and every entry's two words; strings untouched."""
    _entries, count = check_texture_name_map(buf, be, 'TextureNameMap')
    out = bytearray(buf)

    def sw(off):
        out[off:off + 4] = out[off:off + 4][::-1]

    sw(0)
    sw(4)
    for i in range(count):
        sw(16 + 8 * i)
        sw(16 + 8 * i + 4)
    return bytes(out)


def name_map_entries(buf, be):
    _entries, count = check_texture_name_map(buf, be, 'TextureNameMap')
    out = []
    for i in range(count):
        h = _u32(buf, 16 + 8 * i, be)
        o = _u32(buf, 16 + 8 * i + 4, be)
        out.append((h, buf[o:buf.index(b'\0', o)].decode('ascii')))
    return out


# --------------------------------------------------------- particle description collection
def check_particle_description_collection(buf, be, label, import_count=None):
    """{u32 table, u32 count} then `count` u32 import-slot words at +8 (table == 8)."""
    if len(buf) < 8 or len(buf) % 4:
        raise PortError('%s: collection is %d bytes (not a whole word count)' % (label, len(buf)))
    table, count = _u32(buf, 0, be), _u32(buf, 4, be)
    if table != 8:
        raise PortError('%s: table at %#x, expected 8' % (label, table))
    if 8 + 4 * count > len(buf):
        raise PortError('%s: count %d does not fit %d bytes' % (label, count, len(buf)))
    if import_count is not None and count != import_count:
        raise PortError('%s: count %d != %d imports in the sidecar' % (label, count, import_count))
    return table, count


def swap_particle_description_collection(buf, be=True, import_count=None):
    check_particle_description_collection(buf, be, 'ParticleDescriptionCollection', import_count)
    out = bytearray(buf)
    for off in range(0, len(buf), 4):
        out[off:off + 4] = out[off:off + 4][::-1]
    return bytes(out)


def count_imports(sidecar_path):
    if not os.path.isfile(sidecar_path):
        return 0
    n = 0
    for line in open(sidecar_path, 'r', encoding='utf-8'):
        if re.match(r'^\s*-\s*0x[0-9a-fA-F]+\s*:\s*0x[0-9a-fA-F]+\s*$', line):
            n += 1
    return n


# ----------------------------------------------------------------------------- helpers
def rewrite_meta(path):
    txt = open(path, 'r', encoding='utf-8').read()
    new = re.sub(r'(?m)^(\s*platform:\s*)2\s*$', r'\g<1>4', txt)
    new = re.sub(r'(?m)^(\s*compressed:\s*)true\s*$', r'\g<1>false', new)
    new = re.sub(r'(?m)^(\s*(?:mainMemOptimised|graphicsMemOptimised):\s*)true\s*$',
                 r'\g<1>false', new)
    if new == txt:
        raise PortError('%s: meta rewrite matched nothing' % path)
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(new)


def fix_import_sidecars(root):
    """YAP extract writes '<file>.dat_imports.yaml'; YAP create reads '<ID>_imports.yaml'.
    Without the rename every import is silently dropped (vehicle_transcode precedent)."""
    for lroot, _dirs, files in os.walk(root):
        for f in files:
            if f.endswith('.dat_imports.yaml'):
                base = f[:-len('.dat_imports.yaml')]
                if base.endswith('_header'):
                    base = base[:-len('_header')]
                os.replace(os.path.join(lroot, f), os.path.join(lroot, base + '_imports.yaml'))


def read_bnd2(path):
    d = open(path, 'rb').read()
    if d[:4] != b'bnd2':
        raise PortError('%s: not a bnd2 bundle' % path)
    plat_le = struct.unpack_from('<I', d, 8)[0]
    E = '<' if 1 <= plat_le <= 8 else '>'
    ver, plat, dbg, count, eoff = struct.unpack_from(E + '5I', d, 4)
    d0 = struct.unpack_from(E + 'I', d, 0x18)[0]
    entries = []
    for i in range(count):
        o = eoff + i * 0x40
        rid = struct.unpack_from(E + 'Q', d, o)[0]
        usz = [w & 0x0FFFFFFF for w in struct.unpack_from(E + '3I', d, o + 0x10)]
        csz = struct.unpack_from(E + '3I', d, o + 0x1C)
        doff = struct.unpack_from(E + '3I', d, o + 0x28)
        tid = struct.unpack_from(E + 'I', d, o + 0x38)[0]
        nimp = struct.unpack_from(E + 'H', d, o + 0x3C)[0]
        entries.append({'id': rid, 'type': tid, 'imports': nimp, 'usz': usz,
                        'csz': csz, 'doff': doff})
    return {'endian': E, 'platform': plat, 'count': count, 'entries': entries,
            'data0': d0, 'bytes': d}


def payload(bundle, entry, mem=0):
    b = bundle['bytes']
    # the data offsets for memory type N are relative to the Nth data section base
    base = struct.unpack_from(bundle['endian'] + 'I', b, 0x18 + 4 * mem)[0]
    usz, csz, doff = entry['usz'][mem], entry['csz'][mem], entry['doff'][mem]
    raw = b[base + doff: base + doff + csz]
    return zlib.decompress(raw) if (csz != usz and usz != 0) else raw


# ------------------------------------------------------------------------------ convert
def convert(in_bundle, out_bundle, verbose=True):
    if not os.path.isfile(YAP):
        raise PortError('YAP is not built: %s' % YAP)
    src = read_bnd2(in_bundle)
    if src['platform'] != 2:
        raise PortError('%s: platform %d, expected 2' % (in_bundle, src['platform']))
    src_ids = sorted(e['id'] for e in src['entries'])

    work = tempfile.mkdtemp(prefix='particles_')
    try:
        ex = os.path.join(work, 'ex')
        run([YAP, 'e', os.path.abspath(in_bundle), ex])
        fix_import_sidecars(ex)

        counts = {}
        skid_name_hash = None

        # -- TextureNameMap -------------------------------------------------------
        for p in sorted(os.listdir(os.path.join(ex, 'TextureNameMap'))):
            if not p.endswith('.dat'):
                continue
            path = os.path.join(ex, 'TextureNameMap', p)
            raw = open(path, 'rb').read()
            ported = swap_texture_name_map(raw, be=True)
            if swap_texture_name_map(ported, be=False) != raw:
                raise PortError('%s: name map swap is not an involution' % p)
            names = name_map_entries(ported, be=False)
            for h, n in names:
                if n == FXSKID_GDB_NAME:
                    skid_name_hash = h
                if resource_id(n) not in src_ids:
                    raise PortError('%s: name-map entry %r resolves to id %08X which is not in the bundle'
                                    % (p, n, resource_id(n)))
            if skid_name_hash is None:
                raise PortError('%s: the fxskid entry is missing from the name map' % p)
            open(path, 'wb').write(ported)
            counts['TextureNameMap'] = counts.get('TextureNameMap', 0) + 1
            if verbose:
                print('  TextureNameMap %s: %d entries, fxskid hash %08X -> id %08X'
                      % (p, len(names), skid_name_hash, FXSKID_ID))

        # -- VFXPropCollection ----------------------------------------------------
        for p in sorted(os.listdir(os.path.join(ex, 'VFXPropCollection'))):
            if not p.endswith('.dat'):
                continue
            path = os.path.join(ex, 'VFXPropCollection', p)
            raw = open(path, 'rb').read()
            vfxprops_transcode.check(raw, be=True, verbose=False)
            ported = vfxprops_transcode.swap(raw, be=True)
            vfxprops_transcode.check(ported, be=False, verbose=False)
            if vfxprops_transcode.swap(ported, be=False) != raw:
                raise PortError('%s: vfxprops swap is not an involution' % p)
            open(path, 'wb').write(ported)
            counts['VFXPropCollection'] = counts.get('VFXPropCollection', 0) + 1
            if verbose:
                print('  VFXPropCollection %s: %d bytes swapped + verified' % (p, len(raw)))

        # -- ParticleDescriptionCollection ---------------------------------------
        for p in sorted(os.listdir(os.path.join(ex, 'ParticleDescriptionCollection'))):
            if not p.endswith('.dat'):
                continue
            path = os.path.join(ex, 'ParticleDescriptionCollection', p)
            raw = open(path, 'rb').read()
            nimp = count_imports(path[:-4] + '_imports.yaml')
            ported = swap_particle_description_collection(raw, be=True, import_count=nimp)
            if swap_particle_description_collection(ported, be=False, import_count=nimp) != raw:
                raise PortError('%s: collection swap is not an involution' % p)
            open(path, 'wb').write(ported)
            counts['ParticleDescriptionCollection'] = counts.get('ParticleDescriptionCollection', 0) + 1
            if verbose:
                print('  ParticleDescriptionCollection %s: %d import slots swapped' % (p, nimp))

        # -- the two PASSTHROUGH families (see the banner) ------------------------
        for folder in ('ParticleDescription', 'VFXMeshCollection'):
            d = os.path.join(ex, folder)
            # a mesh collection extracts as a header/body PAIR; count resources, not files
            n = len([f for f in os.listdir(d)
                     if f.endswith('.dat') and not f.endswith('_body.dat')]) if os.path.isdir(d) else 0
            counts[folder + ' (passthrough BE)'] = n
            if verbose:
                print('  %s: %d payload(s) passed through VERBATIM (big-endian; type unregistered on PC)'
                      % (folder, n))

        # -- Texture --------------------------------------------------------------
        skid_hdr = os.path.join(ex, 'Texture', '%08X_header.dat' % FXSKID_ID)
        skid_body = os.path.join(ex, 'Texture', '%08X_body.dat' % FXSKID_ID)
        if not (os.path.isfile(skid_hdr) and os.path.isfile(skid_body)):
            raise PortError('fxskid raster %08X is not in the extraction' % FXSKID_ID)
        x_hdr, x_body = open(skid_hdr, 'rb').read(), open(skid_body, 'rb').read()
        ntex = tex_transcode.port_textures(ex, work, verbose=verbose)
        counts['Texture'] = ntex
        # validation 3 -- the picture: modelled size, and NOT all zeros
        fetch = x360_tex.parse_fetch_constant(x_hdr)
        pixels = open(skid_body, 'rb').read()
        modelled = x360_tex.tight_pixel_size(fetch) if hasattr(x360_tex, 'tight_pixel_size') else len(pixels)
        if len(pixels) != modelled:
            raise PortError('fxskid: ported %d bytes, modelled %d' % (len(pixels), modelled))
        if not any(pixels):
            raise PortError('fxskid: the ported mip chain is ALL ZEROS (the boostbarmask failure mode)')
        if verbose:
            nz = sum(1 for x in pixels if x)
            print('  fxskid %08X: %dx%d mips=%d GPUFMT %d -> %d bytes, %d non-zero (x360 body %d)'
                  % (FXSKID_ID, fetch['width'], fetch['height'], fetch['mips'], fetch['data_format'],
                     len(pixels), nz, len(x_body)))

        rewrite_meta(os.path.join(ex, '.meta.yaml'))
        out_bundle = os.path.abspath(out_bundle)
        os.makedirs(os.path.dirname(out_bundle), exist_ok=True)
        run([YAP, 'c', ex, out_bundle])
    finally:
        shutil.rmtree(work, ignore_errors=True)

    verify(out_bundle, expect_ids=src_ids, verbose=verbose)
    print('%s: ported %s -> %s' % (os.path.basename(in_bundle),
                                   ', '.join('%d %s' % (v, k) for k, v in sorted(counts.items())),
                                   out_bundle))


# ------------------------------------------------------------------------------- verify
def verify(bundle_path, expect_ids=None, verbose=True):
    b = read_bnd2(bundle_path)
    if b['platform'] != 4:
        raise PortError('%s: platform %d, expected 4' % (bundle_path, b['platform']))
    ids = sorted(e['id'] for e in b['entries'])
    if expect_ids is not None and ids != expect_ids:
        raise PortError('%s: resource id set changed (%d vs %d)' % (bundle_path, len(ids), len(expect_ids)))
    by_type = {}
    for e in b['entries']:
        by_type.setdefault(e['type'], []).append(e)

    nm = by_type.get(TYPE_TEXTURE_NAME_MAP, [])
    if len(nm) != 1:
        raise PortError('%s: %d TextureNameMap resources, expected 1' % (bundle_path, len(nm)))
    names = name_map_entries(payload(b, nm[0]), be=False)
    skid = [h for h, n in names if n == FXSKID_GDB_NAME]
    if not skid:
        raise PortError('%s: fxskid missing from the little-endian name map' % bundle_path)
    for _h, n in names:
        if resource_id(n) not in ids:
            raise PortError('%s: name-map entry %r -> %08X not in bundle' % (bundle_path, n, resource_id(n)))

    pc = by_type.get(TYPE_PARTICLE_DESCRIPTION_COLLECTION, [])
    if len(pc) != 1:
        raise PortError('%s: %d ParticleDescriptionCollection resources, expected 1' % (bundle_path, len(pc)))
    check_particle_description_collection(payload(b, pc[0]), False, 'PDC', import_count=pc[0]['imports'])
    if pc[0]['imports'] != len(by_type.get(TYPE_PARTICLE_DESCRIPTION, [])):
        raise PortError('%s: collection imports %d != %d .lef resources'
                        % (bundle_path, pc[0]['imports'], len(by_type.get(TYPE_PARTICLE_DESCRIPTION, []))))

    vp = by_type.get(TYPE_VFX_PROP_COLLECTION, [])
    if len(vp) != 1:
        raise PortError('%s: %d VFXPropCollection resources, expected 1' % (bundle_path, len(vp)))
    vfxprops_transcode.check(payload(b, vp[0]), be=False, verbose=False)

    tex = by_type.get(TYPE_TEXTURE, [])
    skid_tex = [e for e in tex if e['id'] == FXSKID_ID]
    if not skid_tex:
        raise PortError('%s: fxskid raster %08X missing' % (bundle_path, FXSKID_ID))
    hdr = payload(b, skid_tex[0], 0)
    fmt, w, h = struct.unpack_from('<i', hdr, 0x1C)[0], struct.unpack_from('<H', hdr, 0x20)[0], \
        struct.unpack_from('<H', hdr, 0x22)[0]
    mips = hdr[0x25]
    body = payload(b, skid_tex[0], 1)
    if not any(body):
        raise PortError('%s: fxskid body is all zeros' % bundle_path)
    if verbose:
        print('  verify %s: platform 4, %d resources: %d Texture, %d .lef, %d mesh; name map %d entries '
              '(fxskid hash %08X); fxskid header D3DFMT %#x %dx%d mips=%d, body %d bytes'
              % (os.path.basename(bundle_path), len(ids), len(tex),
                 len(by_type.get(TYPE_PARTICLE_DESCRIPTION, [])),
                 len(by_type.get(TYPE_VFX_MESH_COLLECTION, [])), len(names), skid[0],
                 fmt & 0xFFFFFFFF, w, h, mips, len(body)))
    return True


def main(argv):
    if len(argv) == 3 and argv[1] == '--verify':
        verify(argv[2])
        return 0
    if len(argv) != 3:
        raise SystemExit(__doc__)
    convert(argv[1], argv[2])
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
