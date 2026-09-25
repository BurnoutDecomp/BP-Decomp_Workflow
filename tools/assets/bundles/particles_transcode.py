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
  ParticleDescription (.lef)     PORTED (2026-09-03, boost-exhaust wave) by
                                 lef_transcode.py, which walks the LION effect graph and
                                 applies the game's OWN endian map -- the four
                                 cLionTokenTable instances at .rdata 0x82F36A34/38/3C/40
                                 plus the pointer words each Delocate twiddles by hand.
                                 It used to be a verbatim big-endian passthrough on the
                                 grounds that "cLionFX is not reconstructed"; that argument
                                 was wrong for one word in particular. The FIRST WORD of a
                                 .lef is the effect-name hash StartLionEffect @0x82289F50
                                 matches against, so big-endian bytes make every Lion
                                 effect start -- boost flame, exhaust smoke, boost recharge
                                 -- miss and take the console's "Couldn't locate lion effect
                                 description" exit. See lef_transcode.py's banner for the
                                 map, the two console quirks reproduced, and the checks.
  VFXMeshCollection              PORTED (2026-09-25, FX-CRASHVFX C3): the debris meshes.
                                 LoadFXBundle stages 5..8 acquire one collection per
                                 debris array and the texture it names, and
                                 BrnDebrisRenderer::RenderDebrisArray instances it 32 at a
                                 time. ENDIAN SWAP, no widening: the registered handler's
                                 FixUp (BrnVFXMeshCollectionResourceType::FixUp
                                 @0x82678490) rebases the header's offsets as u32 words in
                                 place (the low-4 GB convention) and adds the graphics
                                 lane to the two buffer base words. Header: every 32-bit
                                 word (version, 32 radii, the four u32 fields, the
                                 MeshHelper, the 9-word IndexBuffer and 10-word
                                 VertexBuffer headers) flipped, the texture name's bytes
                                 untouched. Body: the index data flipped by its width
                                 (IndexBuffer Common bit 31), the vertex data flipped as
                                 32-bit lanes (36-byte WorldTexturedVertex = 9 f32). See
                                 mesh_layout() for the model and its citations.

AN UNPORTED (BIG-ENDIAN) MESH COLLECTION IS REFUSED, NOT CRASHED ON. The exe registers
0x10019 as of FX-CRASHVFX C3, so its FixUp runs on whatever PARTICLES.BUNDLE a player has.
A bundle converted before this port still carries the three collections big-endian; the
handler's PC platform leaf recognises the byte-reversed version word, says so ONCE in the
log with the re-conversion command, and leaves the collection unbound -- the debris stays
undrawn, as before the port. Re-run this converter (or build_game_data.py --only
PARTICLES.BUNDLE) to get the debris meshes.

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
  5. the meshes   every VFXMeshCollection walks its model in BOTH byte orders (header
                  words, MeshHelper 1/1, IndexBuffer count == muNumIndices, VertexBuffer
                  bytes == fetch size == muNumVertices x 36, both data runs inside the
                  body, every other byte zero), swaps back to the input byte for byte,
                  and decodes little-endian as the console draws it: every index below
                  muNumVertices, a whole number of triangles, finite lanes, unit normals,
                  exactly the 32 instance ids 0.5 .. 31.5. Its +0x90 texture name must
                  resolve to a Texture of this bundle (stage 7's acquire), and the three
                  ids must be HashString of the three debris preset names (stage 5's).

Usage:
  py tools/assets/bundles/particles_transcode.py <in_x360.bundle> <out_plat4.bundle>
  py tools/assets/bundles/particles_transcode.py --verify <plat4.bundle>
"""
from __future__ import print_function

import binascii
import math
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
import lef_transcode          # noqa: E402
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

# The debris meshes. LoadFXBundle stage 5 (0x8229CEB4..0x8229CF2C) acquires one VFXMeshCollection per debris array
# by the name in its preset, _gaDebrisArrayParams @0x82CDB250 (stride 0x50, mpMeshCollectionName at +0):
# 0x82013FD4 "lowres_debris.rf3" (arrays 0..2), 0x82013FE8 "highres_debris_02.rf3" (3), 0x82014000
# "Glass_debris.rf3" (4). Their ids are HashString of those names.
DEBRIS_MESH_NAMES = ('lowres_debris.rf3', 'highres_debris_02.rf3', 'Glass_debris.rf3')


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


# ----------------------------------------------------------------------- VFXMeshCollection
# The serialised BrnParticle::BrnVFXMeshCollection, as BrnVFXMeshCollectionResourceType::FixUp @0x82678490 and its
# consumers read it. Every field is a 32-bit word:
#   +0x00 muVersion == 2                        (`cmplwi r11, 2` 0x826784AC)
#   +0x04 mafRadius[32]                         f32
#   +0x84 mpMeshHelper       offset, rebased    (0x826784D8 / 0x826784E8)
#   +0x88 muNumIndices                          the debris draw's index count (RenderDebrisArray)
#   +0x8C muNumVertices
#   +0x90 mMaterial.mpTextureName  offset, rebased (0x826784DC / 0x826784EC) -> a NUL-terminated name that
#                                  LoadFXBundle stage 7 acquires (`lwz r3, 0x90(r3)` 0x8229D060)
# MeshHelper at mpMeshHelper: numIndexBuffers == 1, numVertexBuffers == 1 (0x826784F0..0x82678504),
#   m_buffers[0] -> the IndexBuffer header, m_buffers[1] -> the VertexBuffer header (both offsets, rebased).
# IndexBuffer header, 9 words: the six D3DResource words (Common, ReferenceCount, Fence, ReadFence, Identifier,
#   BaseFlush), +0x18 Address (a BODY offset -- FixUp adds the graphics lane, 0x82678568..0x82678574),
#   +0x1C Size in bytes, +0x20 the index count. Common bit 31 selects 32-bit indices (the PC draw path's test).
# VertexBuffer header, 10 words: the six D3DResource words, +0x18 fetch-constant word 0 (the BODY offset, with
#   the fetch type 3 in its low two bits, which FixUp keeps: 0x82678540..0x82678554), +0x1C fetch word 1 (the
#   endian mode in bits 0..1 -- 2, 8-in-32 -- and the size in dwords in bits 2..25), +0x20 the size in bytes,
#   +0x24 one more word.
# Body: the index data at the IndexBuffer's Address, the vertex data at the fetch base: muNumVertices
#   WorldTexturedVertex records of MESH_VERTEX_STRIDE bytes, the declaration
#   ImRenderer<WorldTexturedVertex>::Construct builds (element words 0x1A23A6 FLOAT4 @0, 0x2A23B9 FLOAT3 @16,
#   0x2C23A5 FLOAT2 @28) -- nine f32 lanes: the position with the instance index in w, the normal, the uv.
#   Every mesh bakes MESH_INSTANCES copies of the piece (instance w = i + 0.5), which is why RenderDebrisArray
#   draws the whole index run once per batch of 32 transforms.
MESH_VERSION = 2
MESH_HEADER_WORDS = 37                 # the version, the 32 radii, the four fields
MESH_OFF_HELPER = 0x84
MESH_OFF_NUM_INDICES = 0x88
MESH_OFF_NUM_VERTICES = 0x8C
MESH_OFF_TEXTURE_NAME = 0x90
MESH_HELPER_WORDS = 4
MESH_IB_WORDS = 9
MESH_VB_WORDS = 10
MESH_VERTEX_STRIDE = 36                # sizeof(WorldTexturedVertex)
MESH_INSTANCES = 32                    # Im3dTexPlusLighting::KU_NUM_TRANSFORMS
MESH_FETCH_TYPE_VERTEX = 3
MESH_FETCH_ENDIAN_8IN32 = 2


def mesh_layout(header, body, be, label):
    """Walk one serialised collection in the given byte order and return its fields, the header words the
    port flips and the two body runs. Raises PortError on anything the model does not tile exactly."""
    E = '>' if be else '<'

    def word(off):
        return struct.unpack_from(E + 'I', header, off)[0]

    if len(header) < MESH_HEADER_WORDS * 4:
        raise PortError('%s: header is only %d bytes' % (label, len(header)))
    version = word(0)
    if version != MESH_VERSION:
        raise PortError('%s: muVersion %#x, expected %d (%s-endian read)' % (label, version, MESH_VERSION,
                                                                            'big' if be else 'little'))
    helper = word(MESH_OFF_HELPER)
    nidx = word(MESH_OFF_NUM_INDICES)
    nvtx = word(MESH_OFF_NUM_VERTICES)
    name_off = word(MESH_OFF_TEXTURE_NAME)
    if not (MESH_HEADER_WORDS * 4 <= name_off < len(header)):
        raise PortError('%s: texture name offset %#x outside the header' % (label, name_off))
    name_end = header.find(b'\0', name_off)
    if name_end < 0 or name_end == name_off:
        raise PortError('%s: texture name at %#x is empty or not NUL-terminated' % (label, name_off))
    name = header[name_off:name_end].decode('ascii')
    if helper % 4 or helper <= name_end or helper + 4 * MESH_HELPER_WORDS > len(header):
        raise PortError('%s: mesh helper at %#x does not follow the name (ends %#x) inside %d bytes'
                        % (label, helper, name_end, len(header)))
    n_ib, n_vb, ib, vb = (word(helper + 4 * k) for k in range(MESH_HELPER_WORDS))
    if (n_ib, n_vb) != (1, 1):
        raise PortError('%s: mesh helper counts %d/%d, expected 1/1' % (label, n_ib, n_vb))
    regions = sorted([(0, MESH_HEADER_WORDS * 4), (name_off, name_end + 1), (helper, helper + 4 * MESH_HELPER_WORDS),
                      (ib, ib + 4 * MESH_IB_WORDS), (vb, vb + 4 * MESH_VB_WORDS)])
    for (a0, a1), (b0, b1) in zip(regions, regions[1:]):
        if b0 < a1:
            raise PortError('%s: header regions overlap: [%#x,%#x) and [%#x,%#x)' % (label, a0, a1, b0, b1))
    if ib % 4 or vb % 4 or regions[-1][1] > len(header):
        raise PortError('%s: buffer headers at %#x / %#x misplaced in %d bytes' % (label, ib, vb, len(header)))

    ib_common, ib_addr, ib_size, ib_count = word(ib), word(ib + 0x18), word(ib + 0x1C), word(ib + 0x20)
    width = 4 if ib_common & 0x80000000 else 2
    fetch0, fetch1, vb_size = word(vb + 0x18), word(vb + 0x1C), word(vb + 0x20)
    vb_off = fetch0 & ~3
    if fetch0 & 3 != MESH_FETCH_TYPE_VERTEX:
        raise PortError('%s: vertex fetch type %d, expected %d' % (label, fetch0 & 3, MESH_FETCH_TYPE_VERTEX))
    if fetch1 & 3 != MESH_FETCH_ENDIAN_8IN32:
        raise PortError('%s: vertex fetch endian %d, expected %d (8in32)' % (label, fetch1 & 3, MESH_FETCH_ENDIAN_8IN32))
    if ((fetch1 >> 2) & 0xFFFFFF) * 4 != vb_size:
        raise PortError('%s: fetch size %d dwords != %d bytes' % (label, (fetch1 >> 2) & 0xFFFFFF, vb_size))
    if ib_count != nidx:
        raise PortError('%s: IndexBuffer count %d != muNumIndices %d' % (label, ib_count, nidx))
    if nidx == 0 or nidx * width > ib_size or ib_size % width:
        raise PortError('%s: %d indices of %d bytes do not fit %d bytes' % (label, nidx, width, ib_size))
    if nvtx == 0 or nvtx * MESH_VERTEX_STRIDE != vb_size:
        raise PortError('%s: %d vertices x %d != %d vertex bytes' % (label, nvtx, MESH_VERTEX_STRIDE, vb_size))
    runs = sorted([(ib_addr, ib_addr + ib_size), (vb_off, vb_off + vb_size)])
    if runs[0][1] > runs[1][0] or runs[1][1] > len(body):
        raise PortError('%s: index run [%#x,%#x) / vertex run [%#x,%#x) do not fit a %d-byte body'
                        % (label, ib_addr, ib_addr + ib_size, vb_off, vb_off + vb_size, len(body)))

    words = list(range(0, MESH_HEADER_WORDS * 4, 4))
    words += [helper + 4 * k for k in range(MESH_HELPER_WORDS)]
    words += [ib + 4 * k for k in range(MESH_IB_WORDS)]
    words += [vb + 4 * k for k in range(MESH_VB_WORDS)]
    covered = set()
    for off in words:
        covered.update(range(off, off + 4))
    covered.update(range(name_off, name_end + 1))
    stray = [off for off in range(len(header)) if off not in covered and header[off]]
    if stray:
        raise PortError('%s: header byte %#x (%#x) lies outside the model' % (label, stray[0], header[stray[0]]))
    in_runs = set(range(ib_addr, ib_addr + ib_size)) | set(range(vb_off, vb_off + vb_size))
    stray = [off for off in range(len(body)) if off not in in_runs and body[off]]
    if stray:
        raise PortError('%s: body byte %#x (%#x) lies outside the index / vertex runs' % (label, stray[0], body[stray[0]]))
    return {'name': name, 'nidx': nidx, 'nvtx': nvtx, 'width': width, 'words': words,
            'ib_addr': ib_addr, 'ib_size': ib_size, 'vb_off': vb_off, 'vb_size': vb_size,
            'helper': helper, 'ib': ib, 'vb': vb, 'name_off': name_off}


def swap_vfx_mesh_collection(header, body, be=True, label='VFXMeshCollection'):
    """Flip every header word of the model and both body runs by their lane width; nothing else moves."""
    m = mesh_layout(header, body, be, label)
    out_header = bytearray(header)
    for off in m['words']:
        out_header[off:off + 4] = out_header[off:off + 4][::-1]
    out_body = bytearray(body)
    width = m['width']
    for off in range(m['ib_addr'], m['ib_addr'] + m['ib_size'], width):
        out_body[off:off + width] = out_body[off:off + width][::-1]
    for off in range(m['vb_off'], m['vb_off'] + m['vb_size'], 4):
        out_body[off:off + 4] = out_body[off:off + 4][::-1]
    return bytes(out_header), bytes(out_body), m


def check_mesh_geometry(header, body, label):
    """The little-endian collection must decode as the console draws it (see the banner, validation 5)."""
    m = mesh_layout(header, body, False, label)
    code = 'H' if m['width'] == 2 else 'I'
    indices = struct.unpack_from('<%d%s' % (m['nidx'], code), body, m['ib_addr'])
    if max(indices) >= m['nvtx']:
        raise PortError('%s: index %d reaches past %d vertices' % (label, max(indices), m['nvtx']))
    if m['nidx'] % 3:
        raise PortError('%s: %d indices are not a whole number of triangles' % (label, m['nidx']))
    instances = set()
    for v in range(m['nvtx']):
        lanes = struct.unpack_from('<9f', body, m['vb_off'] + MESH_VERTEX_STRIDE * v)
        if not all(math.isfinite(x) for x in lanes):
            raise PortError('%s: vertex %d has a non-finite lane %r' % (label, v, lanes))
        normal = math.sqrt(lanes[4] * lanes[4] + lanes[5] * lanes[5] + lanes[6] * lanes[6])
        if abs(normal - 1.0) > 0.05:
            raise PortError('%s: vertex %d normal length %.4f' % (label, v, normal))
        instances.add(lanes[3])
    if instances != set(k + 0.5 for k in range(MESH_INSTANCES)):
        raise PortError('%s: instance ids %s, expected the %d ids 0.5 .. %.1f'
                        % (label, sorted(instances)[:6], MESH_INSTANCES, MESH_INSTANCES - 0.5))
    return m


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

        # -- ParticleDescription (.lef) -------------------------------------------
        # 2026-09-03: no longer a passthrough. lef_transcode walks the LION graph with the
        # game's own endian map (the four cLionTokenTable instances + the by-hand pointer
        # words each Delocate twiddles) and swaps every field it names. See its banner.
        lef_totals = {'descriptors': 0, 'behaviours': 0, 'materials': 0, 'waveforms': 0}
        nlef = 0
        for p in sorted(os.listdir(os.path.join(ex, 'ParticleDescription'))):
            if not p.endswith('.dat'):
                continue
            path = os.path.join(ex, 'ParticleDescription', p)
            raw = open(path, 'rb').read()
            label = os.path.splitext(p)[0]
            stats = lef_transcode.check(raw, be=True, label=label)
            ported = lef_transcode.swap(raw, be=True, label=label)
            if lef_transcode.swap(ported, be=False, label=label) != raw:
                raise PortError('%s: .lef swap is not an involution' % p)
            # The resource id IS the effect-name hash StartLionEffect matches on, so a
            # ported blob whose first word no longer equals its own bundle id would be
            # unreachable -- exactly the failure this port exists to remove.
            rid = int(label.split('_')[0], 16)
            if stats['hash'] != rid:
                raise PortError('%s: .lef name hash %08X != bundle id %08X'
                                % (p, stats['hash'], rid))
            open(path, 'wb').write(ported)
            nlef += 1
            for k in lef_totals:
                lef_totals[k] += stats[k]
            if verbose:
                print('  ParticleDescription %s %08X %r: %d descriptors, %d behaviours, '
                      '%d materials, %d waveforms'
                      % (p, stats['hash'], stats['name'], stats['descriptors'],
                         stats['behaviours'], stats['materials'], stats['waveforms']))
        counts['ParticleDescription'] = nlef
        if verbose:
            print('  ParticleDescription: %d .lef ported, %s'
                  % (nlef, ', '.join('%d %s' % (v, k) for k, v in sorted(lef_totals.items()))))

        # -- VFXMeshCollection (the debris meshes; see the banner and mesh_layout) --
        # A collection extracts as a header/body PAIR. Its texture name must resolve to a Texture of this bundle
        # (stage 7's acquire) and the set of ids must be HashString of the three debris preset names (stage 5's).
        mesh_dir = os.path.join(ex, 'VFXMeshCollection')
        texture_ids = set(e['id'] for e in src['entries'] if e['type'] == TYPE_TEXTURE)
        mesh_ids = []
        for p in sorted(os.listdir(mesh_dir)):
            if not p.endswith('_header.dat'):
                continue
            rid = int(p[:-len('_header.dat')], 16)
            label = '%08X' % rid
            header_path = os.path.join(mesh_dir, p)
            body_path = os.path.join(mesh_dir, label + '_body.dat')
            header, body = open(header_path, 'rb').read(), open(body_path, 'rb').read()
            ported_header, ported_body, m = swap_vfx_mesh_collection(header, body, be=True, label=label)
            back_header, back_body, _m = swap_vfx_mesh_collection(ported_header, ported_body, be=False, label=label)
            if back_header != header or back_body != body:
                raise PortError('%s: mesh collection swap is not an involution' % label)
            check_mesh_geometry(ported_header, ported_body, label)
            if resource_id(m['name']) not in texture_ids:
                raise PortError('%s: texture %r -> id %08X is not a Texture of this bundle'
                                % (label, m['name'], resource_id(m['name'])))
            open(header_path, 'wb').write(ported_header)
            open(body_path, 'wb').write(ported_body)
            mesh_ids.append(rid)
            if verbose:
                print('  VFXMeshCollection %s: texture %r (%08X), %d indices (%d-bit), %d vertices x %d, '
                      'header %d / body %d bytes ported'
                      % (label, m['name'], resource_id(m['name']), m['nidx'], 8 * m['width'], m['nvtx'],
                         MESH_VERTEX_STRIDE, len(header), len(body)))
        wanted = sorted(set(resource_id(n) for n in DEBRIS_MESH_NAMES))
        if sorted(mesh_ids) != wanted:
            raise PortError('mesh collections %s != HashString of the debris presets %s'
                            % (['%08X' % i for i in sorted(mesh_ids)], ['%08X' % i for i in wanted]))
        counts['VFXMeshCollection'] = len(mesh_ids)

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

    # Every .lef must walk LITTLE-endian, and its first word (the effect-name hash that
    # StartLionEffect matches on) must equal its own bundle id.
    lef_stats = {'descriptors': 0, 'behaviours': 0, 'materials': 0, 'waveforms': 0}
    for e in by_type.get(TYPE_PARTICLE_DESCRIPTION, []):
        st = lef_transcode.check(payload(b, e), be=False, label='%08X' % e['id'])
        if st['hash'] != e['id']:
            raise PortError('%s: .lef %08X carries name hash %08X' % (bundle_path, e['id'], st['hash']))
        for k in lef_stats:
            lef_stats[k] += st[k]

    vp = by_type.get(TYPE_VFX_PROP_COLLECTION, [])
    if len(vp) != 1:
        raise PortError('%s: %d VFXPropCollection resources, expected 1' % (bundle_path, len(vp)))
    vfxprops_transcode.check(payload(b, vp[0]), be=False, verbose=False)

    tex = by_type.get(TYPE_TEXTURE, [])
    # The debris meshes must walk LITTLE-endian and draw as the console does (validation 5).
    meshes = by_type.get(TYPE_VFX_MESH_COLLECTION, [])
    wanted = sorted(set(resource_id(n) for n in DEBRIS_MESH_NAMES))
    if sorted(e['id'] for e in meshes) != wanted:
        raise PortError('%s: mesh collections %s != the debris presets %s'
                        % (bundle_path, ['%08X' % e['id'] for e in meshes], ['%08X' % i for i in wanted]))
    texture_ids = set(e['id'] for e in tex)
    mesh_notes = []
    for e in meshes:
        m = check_mesh_geometry(payload(b, e, 0), payload(b, e, 1), '%08X' % e['id'])
        if resource_id(m['name']) not in texture_ids:
            raise PortError('%s: mesh %08X names texture %r (%08X), not in the bundle'
                            % (bundle_path, e['id'], m['name'], resource_id(m['name'])))
        mesh_notes.append('%08X %s %d/%d' % (e['id'], m['name'], m['nidx'], m['nvtx']))
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
        print('  verify %s: the .lef graph walks little-endian -- %s'
              % (os.path.basename(bundle_path),
                 ', '.join('%d %s' % (v, k) for k, v in sorted(lef_stats.items()))))
        print('  verify %s: the debris meshes walk little-endian (id texture indices/vertices) -- %s'
              % (os.path.basename(bundle_path), '; '.join(mesh_notes)))
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
