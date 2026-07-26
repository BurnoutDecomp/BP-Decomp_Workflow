#!/usr/bin/env python3
"""Renderable porting helper for the x64 PC port bundles.

Converts one X360 ARTIST serialised ::Renderable resource (big-endian,
32-bit serialised pointers = offsets from the resource start) into the
platform-4 x64 form the reconstructed engine loads (little-endian, natural
MSVC x64 relayout with 8-byte pointer slots), plus its GPU body payload.

Serialised graph (X360, 32-bit -- b5-decomp
src/GameShared/GameClasses/Graphics/Dispatch/Renderable.h /
renderablemesh.h, DebugValidate @0x828A7DE0, FixUpRenderableMesh
@0x828A8968, GetSerialisedResourceDescriptor @0x828A9AB0):

  Renderable            +0x00 Vector3Plus sphere, +0x10 u16 version,
                        +0x12 u16 numMeshes, +0x14 meshPtrArray,
                        +0x18 ObjectScopeTextureInfo*, +0x1C u16 flags
  RenderableMesh        +0x00 PackedOobb, +0x10 DrawIndexedParameters,
                        +0x20 MaterialAssembly* (IMPORT slot),
                        +0x24 u8 numVertexDescriptors, +0x25 u8 instanceCount,
                        +0x26 u8 numVertexBuffers, +0x27 u8 flags,
                        +0x28 IndexBufferHeader*, +0x2C VertexBufferHeader*[numVB],
                        then VertexDescriptor* [numVD] (IMPORT slots)
  IndexBufferHeader     36 bytes of u32 (pc/gcm/renderengine/IndexBuffer.h)
                        -- PC keeps the X360 byte layout: ENDIAN FLIP ONLY.
                        muCommon bit31 set (0xC0000000) = 32-bit indices.
                        muBaseAddress = offset into the body payload | low flags.
  VertexBufferHeader    40 bytes of u32 (pc/gcm/renderengine/VertexBuffer.h)
                        -- ENDIAN FLIP ONLY; muBaseAddress low 2 bits = flags.
  ObjectScopeTextureInfo{u16 num, u16 max, s16* purposeToIndex, Texture**
                        (IMPORT slots), char** names} + name string pool.

x64 emission layout (natural MSVC relayout, members by name):
  Renderable      0x30: sphere@0, ver@0x10, numMeshes@0x12, meshes@0x18,
                  osti@0x20, flags@0x28
  RenderableMesh  0x30 + 8*(1+numVB+numVD): oobb@0, dip@0x10, material@0x20,
                  u8 quad@0x28, IB@0x30, VBs@0x38.., then VDs
  OSTI            0x20: num@0, max@2, map@8, textures@0x10, names@0x18
  IB/VB headers   unchanged size, u32 lanes flipped.

Import slots (material assemblies, vertex descriptors, object-scope
textures) are zero in the blob and listed in the YAP `_imports.yaml`
(`- 0xOFFSET: 0xRESOURCEID` lines); widening moves them, so a rewritten
imports.yaml is emitted alongside the widened header.

Body payload: index data is endian-flipped (u16 or u32 per the IB Common
tag). Vertex data is flipped PER ATTRIBUTE from the mesh's VertexDescriptor
imports (16B header + 16B elements {u16 stream, u16 offset, u32 X360 GPU
type dword, u16 usage, ...} + per-element stride bytes); when the
descriptors are not supplied the vertex bytes are left big-endian and a
warning is printed.

Usage:
  py tools/assets/bundles/renderable_transcode.py <yap_extraction_dir> [--check]

converts <dir>/Renderable/*.{_header.dat,_body.dat,_imports.yaml} in place
(using <dir>/VertexDescriptor/*.dat for the vertex swaps).

API for convert_world_bundle.py:
  imports = parse_imports_yaml(text)
  info    = parse_renderable(header_bytes, imports)
  info.vd_lookup = {resource_id: vd_bytes}          # optional, for vertex swap
  new_header, new_yaml = transcode_renderable(header_bytes, text)
  new_body             = transcode_renderable_body(body_bytes, info)
"""
import os
import struct
import sys

# ---------------------------------------------------------------------------
# X360 (source) layout constants
# ---------------------------------------------------------------------------
X360_RENDERABLE_SIZE = 0x20
X360_MESH_FIXED_SIZE = 0x28          # through the IB pointer slot @0x28
X360_OSTI_SIZE = 0x10
IB_HEADER_SIZE = 36                  # 9 u32 -- same on PC (flip only)
VB_HEADER_SIZE = 40                  # 10 u32 -- same on PC (flip only)

# x64 (destination) layout constants (natural MSVC relayout, see docstring)
X64_RENDERABLE_SIZE = 0x30
X64_MESH_FIXED_SIZE = 0x30           # buffer table (8B slots) starts here
X64_OSTI_SIZE = 0x20

# X360 GPU vertex declaration type dwords (Xenon D3DDECLTYPE) -> component
# lane widths for the endian flip. 1-byte lanes need no flip but the packed
# dword formats (D3DCOLOR/UBYTE4/DEC3N) are fetched as one 32-bit word.
X360_DECLTYPE_LANES = {
    0x2C83A4: (4, 1),   # FLOAT1
    0x2C23A5: (4, 2),   # FLOAT2
    0x2A23B9: (4, 3),   # FLOAT3
    0x1A23A6: (4, 4),   # FLOAT4
    0x182886: (4, 1),   # D3DCOLOR   (packed dword)
    0x1A2286: (4, 1),   # UBYTE4     (packed dword on the Xenon fetch)
    0x1A2086: (4, 1),   # UBYTE4N
    0x2C2359: (2, 2),   # SHORT2
    0x1A235A: (2, 4),   # SHORT4
    0x2C2159: (2, 2),   # SHORT2N
    0x1A215A: (2, 4),   # SHORT4N
    0x2C2059: (2, 2),   # USHORT2N
    0x1A205A: (2, 4),   # USHORT4N
    0x2A2287: (4, 1),   # UDEC3      (packed dword)
    0x2A2187: (4, 1),   # DEC3N      (packed dword)
    0x2C235F: (2, 2),   # FLOAT16_2
    0x1A235F: (2, 4),   # FLOAT16_4
}


class TranscodeError(SystemExit):
    pass


# ---------------------------------------------------------------------------
# imports.yaml
# ---------------------------------------------------------------------------
def parse_imports_yaml(text):
    """YAP `- 0xOFFSET: 0xRESOURCEID` lines -> {offset: resource_id}."""
    imports = {}
    for line in (text or '').splitlines():
        line = line.strip()
        if not line.startswith('-'):
            continue
        key, _, value = line[1:].partition(':')
        imports[int(key.strip(), 16)] = int(value.strip(), 16)
    return imports


def emit_imports_yaml(imports):
    """{offset: resource_id} -> YAP imports.yaml text (same shape as YAP's:
    lowercase 8-digit hex, sorted by offset, no trailing newline)."""
    return '\n'.join('- 0x%08x: 0x%08x' % (off, rid)
                     for off, rid in sorted(imports.items()))


# ---------------------------------------------------------------------------
# parse (X360 big-endian source form)
# ---------------------------------------------------------------------------
class ParsedRenderable(object):
    """The parsed serialised graph. Every consumed byte range is recorded so
    the X360 re-emit can prove full coverage (round-trip identity)."""

    def __init__(self):
        self.sphere = None            # 4 u32 lanes
        self.version = 0
        self.flags = 0
        self.meshes_off = 0           # X360 offset of the mesh pointer table
        self.osti_off = 0             # X360 offset of the OSTI block (0 = none)
        self.meshes = []              # [dict per mesh]
        self.osti = None              # dict or None
        self.imports = {}             # {x360_offset: resource_id}
        self.size = 0                 # source blob size
        self.ranges = []              # [(start, end, what)] consumed ranges
        self.tail_off = 0             # end of the last parsed object
        self.tail = b''               # trailing 16-align pad (serialiser junk,
                                      # preserved verbatim for the round trip)
        self.vd_lookup = {}           # {resource_id: vd_bytes} -- caller-set,
                                      # drives the vertex payload swap

    def claim(self, start, size, what):
        end = start + size
        if end > self.size:
            raise TranscodeError('renderable: %s @0x%X runs past the blob end '
                                 '(0x%X > 0x%X)' % (what, start, end, self.size))
        for s, e, w in self.ranges:
            if start < e and s < end:
                raise TranscodeError('renderable: %s @0x%X overlaps %s @0x%X'
                                     % (what, start, w, s))
        self.ranges.append((start, end, what))


def _u32(data, off):
    return struct.unpack_from('>I', data, off)[0]


def _u16(data, off):
    return struct.unpack_from('>H', data, off)[0]


def parse_renderable(header_bytes, imports):
    """Parse one X360 serialised Renderable header blob.

    imports: {x360_offset: resource_id} from parse_imports_yaml. Every yaml
    offset must land on a known import slot (material / vertex-descriptor /
    object-scope texture) or the parse fails -- that guards the layout model.
    """
    data = header_bytes
    p = ParsedRenderable()
    p.size = len(data)
    p.imports = dict(imports)

    if len(data) < X360_RENDERABLE_SIZE:
        raise TranscodeError('renderable: blob too small (%d bytes)' % len(data))

    p.sphere = struct.unpack_from('>4I', data, 0x00)
    p.version = _u16(data, 0x10)
    num_meshes = _u16(data, 0x12)
    p.meshes_off = _u32(data, 0x14)
    p.osti_off = _u32(data, 0x18)
    p.flags = _u16(data, 0x1C)
    p.claim(0, X360_RENDERABLE_SIZE, 'Renderable')

    if p.version != 11:
        raise TranscodeError('renderable: version %d (expected 11) -- wrong '
                             'endianness or not an X360 renderable?' % p.version)
    if num_meshes == 0 or p.meshes_off == 0:
        raise TranscodeError('renderable: no meshes (count=%d table=0x%X)'
                             % (num_meshes, p.meshes_off))

    claimed_imports = set()

    def import_at(off, what):
        value = _u32(data, off)
        if value != 0:
            raise TranscodeError('renderable: %s import slot @0x%X is not '
                                 'serialised-null (0x%08X)' % (what, off, value))
        if off in p.imports:
            claimed_imports.add(off)
            return p.imports[off]
        return None

    # mesh pointer table
    p.claim(p.meshes_off, 4 * num_meshes, 'mesh table')
    for mi in range(num_meshes):
        mesh_off = _u32(data, p.meshes_off + 4 * mi)
        num_vd = data[mesh_off + 0x24]
        instance_count = data[mesh_off + 0x25]
        num_vb = data[mesh_off + 0x26]
        mesh_flags = data[mesh_off + 0x27]
        mesh = {
            'src_off': mesh_off,
            'oobb': struct.unpack_from('>4I', data, mesh_off),
            'dip': struct.unpack_from('>4I', data, mesh_off + 0x10),
            'material_import': import_at(mesh_off + 0x20, 'material assembly'),
            'num_vd': num_vd,
            'instance_count': instance_count,
            'num_vb': num_vb,
            'flags': mesh_flags,
            'ib_off': _u32(data, mesh_off + 0x28),
            'vb_offs': [],
            'vd_imports': [],
        }
        table_words = 1 + num_vb + num_vd
        p.claim(mesh_off, X360_MESH_FIXED_SIZE + 4 * (table_words - 1),
                'mesh[%d]' % mi)
        for vi in range(num_vb):
            mesh['vb_offs'].append(_u32(data, mesh_off + 0x2C + 4 * vi))
        for di in range(num_vd):
            slot = mesh_off + 0x2C + 4 * num_vb + 4 * di
            mesh['vd_imports'].append(
                import_at(slot, 'vertex descriptor'))

        # GPU buffer headers -- u32 lanes, flip only
        mesh['ib_header'] = struct.unpack_from('>9I', data, mesh['ib_off'])
        p.claim(mesh['ib_off'], IB_HEADER_SIZE, 'mesh[%d] IB header' % mi)
        mesh['vb_headers'] = []
        for vi, vb_off in enumerate(mesh['vb_offs']):
            mesh['vb_headers'].append(struct.unpack_from('>10I', data, vb_off))
            p.claim(vb_off, VB_HEADER_SIZE, 'mesh[%d] VB[%d] header' % (mi, vi))
        p.meshes.append(mesh)

    # object-scope texture info (not seen in the world track units yet; the
    # walk mirrors GetRenderableBasicResourceDescriptor @0x828A96F0)
    if p.osti_off:
        o = p.osti_off
        osti = {
            'src_off': o,
            'num': _u16(data, o),
            'max': _u16(data, o + 2),
            'map_off': _u32(data, o + 4),
            'textures_off': _u32(data, o + 8),
            'names_off': _u32(data, o + 0xC),
            'purpose_map': [],
            'texture_imports': [],
            'name_offs': [],
            'names': [],
        }
        p.claim(o, X360_OSTI_SIZE, 'ObjectScopeTextureInfo')
        if osti['map_off']:
            osti['purpose_map'] = list(struct.unpack_from(
                '>%dh' % osti['max'], data, osti['map_off']))
            p.claim(osti['map_off'], 2 * osti['max'], 'OSTI purpose map')
        if osti['textures_off']:
            p.claim(osti['textures_off'], 4 * osti['num'], 'OSTI textures')
            for ti in range(osti['num']):
                osti['texture_imports'].append(
                    import_at(osti['textures_off'] + 4 * ti, 'OSTI texture'))
        if osti['names_off']:
            p.claim(osti['names_off'], 4 * osti['num'], 'OSTI name table')
            for ti in range(osti['num']):
                name_off = _u32(data, osti['names_off'] + 4 * ti)
                end = data.index(b'\0', name_off)
                osti['name_offs'].append(name_off)
                osti['names'].append(data[name_off:end])
                p.claim(name_off, ((end - name_off) + 4) & ~3,
                        'OSTI name[%d]' % ti)
        p.osti = osti

    unclaimed = set(p.imports) - claimed_imports
    if unclaimed:
        raise TranscodeError('renderable: imports.yaml offsets not on any '
                             'known import slot: %s'
                             % ', '.join('0x%X' % x for x in sorted(unclaimed)))

    # every unconsumed byte BETWEEN objects must be padding (zero) -- proves
    # the parse covers the whole serialised graph. The tail past the last
    # object (the 16-align pad) may hold serialiser junk: attested on 128 of
    # the 255 TRK_UNIT285 renderables, always strictly after the last VB
    # header. It is kept verbatim for the round trip and dropped on x64.
    p.tail_off = max(end for _, end, _ in p.ranges)
    p.tail = bytes(data[p.tail_off:])
    if len(p.tail) >= 16:
        raise TranscodeError('renderable: %d tail bytes past the last object '
                             '-- more than an align pad, layout model '
                             'incomplete' % len(p.tail))
    covered = bytearray(p.size)
    for s, e, _ in p.ranges:
        for i in range(s, e):
            covered[i] = 1
    for i in range(p.tail_off):
        if not covered[i] and data[i] != 0:
            raise TranscodeError('renderable: unparsed non-zero byte 0x%02X '
                                 '@0x%X -- layout model incomplete' % (data[i], i))
    return p


# ---------------------------------------------------------------------------
# emit
# ---------------------------------------------------------------------------
def _align(value, alignment):
    return (value + alignment - 1) & ~(alignment - 1)


def _layout_x64(p):
    """Assign x64 offsets to every object, preserving the source ordering.
    Returns ({src_off: new_off}, total_size, {new_import_off: resource_id})."""
    objects = []   # (src_off, size, align)
    objects.append((0, X64_RENDERABLE_SIZE, 16))
    objects.append((p.meshes_off, 8 * len(p.meshes), 16))
    for mesh in p.meshes:
        table = 1 + mesh['num_vb'] + mesh['num_vd']
        objects.append((mesh['src_off'], X64_MESH_FIXED_SIZE + 8 * table, 16))
        objects.append((mesh['ib_off'], IB_HEADER_SIZE, 16))
        for vb_off in mesh['vb_offs']:
            objects.append((vb_off, VB_HEADER_SIZE, 16))
    if p.osti:
        o = p.osti
        objects.append((o['src_off'], X64_OSTI_SIZE, 16))
        if o['map_off']:
            objects.append((o['map_off'], 2 * o['max'], 8))
        if o['textures_off']:
            objects.append((o['textures_off'], 8 * o['num'], 8))
        if o['names_off']:
            objects.append((o['names_off'], 8 * o['num'], 8))
            for ti, name in enumerate(o['names']):
                objects.append((o['name_offs'][ti], len(name) + 1, 4))

    remap = {}
    cursor = 0
    for src_off, size, alignment in sorted(objects):
        cursor = _align(cursor, alignment)
        remap[src_off] = cursor
        cursor += size
    return remap, _align(cursor, 16)


def emit_x64(p):
    """Emit the little-endian widened blob + the rewritten imports map."""
    remap, total = _layout_x64(p)
    out = bytearray(total)
    new_imports = {}

    def put_u32s(off, values):
        struct.pack_into('<%dI' % len(values), out, off, *values)

    # Renderable
    put_u32s(0x00, p.sphere)
    struct.pack_into('<2H', out, 0x10, p.version, len(p.meshes))
    struct.pack_into('<2Q', out, 0x18, remap[p.meshes_off],
                     remap[p.osti_off] if p.osti_off else 0)
    struct.pack_into('<H', out, 0x28, p.flags)

    # mesh table
    struct.pack_into('<%dQ' % len(p.meshes), out, remap[p.meshes_off],
                     *[remap[m['src_off']] for m in p.meshes])

    for mesh in p.meshes:
        base = remap[mesh['src_off']]
        put_u32s(base, mesh['oobb'])
        put_u32s(base + 0x10, mesh['dip'])
        # material assembly import slot (stays 0 in the blob)
        if mesh['material_import'] is not None:
            new_imports[base + 0x20] = mesh['material_import']
        out[base + 0x28] = mesh['num_vd']
        out[base + 0x29] = mesh['instance_count']
        out[base + 0x2A] = mesh['num_vb']
        out[base + 0x2B] = mesh['flags']
        struct.pack_into('<Q', out, base + 0x30, remap[mesh['ib_off']])
        for vi, vb_off in enumerate(mesh['vb_offs']):
            struct.pack_into('<Q', out, base + 0x38 + 8 * vi, remap[vb_off])
        for di, rid in enumerate(mesh['vd_imports']):
            slot = base + 0x30 + 8 * (1 + mesh['num_vb']) + 8 * di
            if rid is not None:
                new_imports[slot] = rid

        put_u32s(remap[mesh['ib_off']], mesh['ib_header'])
        for vi, vb_off in enumerate(mesh['vb_offs']):
            put_u32s(remap[vb_off], mesh['vb_headers'][vi])

    if p.osti:
        o = p.osti
        base = remap[o['src_off']]
        struct.pack_into('<2H', out, base, o['num'], o['max'])
        struct.pack_into('<3Q', out, base + 8,
                         remap[o['map_off']] if o['map_off'] else 0,
                         remap[o['textures_off']] if o['textures_off'] else 0,
                         remap[o['names_off']] if o['names_off'] else 0)
        if o['map_off']:
            struct.pack_into('<%dh' % o['max'], out, remap[o['map_off']],
                             *o['purpose_map'])
        if o['textures_off']:
            for ti, rid in enumerate(o['texture_imports']):
                if rid is not None:
                    new_imports[remap[o['textures_off']] + 8 * ti] = rid
        if o['names_off']:
            for ti, name in enumerate(o['names']):
                struct.pack_into('<Q', out, remap[o['names_off']] + 8 * ti,
                                 remap[o['name_offs'][ti]])
                new_off = remap[o['name_offs'][ti]]
                out[new_off:new_off + len(name)] = name

    return bytes(out), new_imports


def emit_x360(p):
    """Re-emit the parsed graph in the original X360 form (round-trip proof:
    must byte-compare equal with the source blob)."""
    out = bytearray(p.size)

    def put_u32s(off, values):
        struct.pack_into('>%dI' % len(values), out, off, *values)

    put_u32s(0x00, p.sphere)
    struct.pack_into('>2H', out, 0x10, p.version, len(p.meshes))
    struct.pack_into('>2I', out, 0x14, p.meshes_off, p.osti_off)
    struct.pack_into('>H', out, 0x1C, p.flags)

    put_u32s(p.meshes_off, [m['src_off'] for m in p.meshes])
    for mesh in p.meshes:
        base = mesh['src_off']
        put_u32s(base, mesh['oobb'])
        put_u32s(base + 0x10, mesh['dip'])
        out[base + 0x24] = mesh['num_vd']
        out[base + 0x25] = mesh['instance_count']
        out[base + 0x26] = mesh['num_vb']
        out[base + 0x27] = mesh['flags']
        struct.pack_into('>I', out, base + 0x28, mesh['ib_off'])
        put_u32s(base + 0x2C, mesh['vb_offs'])
        put_u32s(mesh['ib_off'], mesh['ib_header'])
        for vi, vb_off in enumerate(mesh['vb_offs']):
            put_u32s(vb_off, mesh['vb_headers'][vi])
    if p.osti:
        o = p.osti
        struct.pack_into('>2H3I', out, o['src_off'], o['num'], o['max'],
                         o['map_off'], o['textures_off'], o['names_off'])
        if o['map_off']:
            struct.pack_into('>%dh' % o['max'], out, o['map_off'],
                             *o['purpose_map'])
        if o['names_off']:
            put_u32s(o['names_off'], o['name_offs'])
            for ti, name in enumerate(o['names']):
                out[o['name_offs'][ti]:o['name_offs'][ti] + len(name)] = name
    out[p.tail_off:] = p.tail
    return bytes(out)


# ---------------------------------------------------------------------------
# VertexDescriptor parse (drives the per-attribute vertex payload swap)
# ---------------------------------------------------------------------------
def parse_vertex_descriptor(vd_bytes):
    """X360 serialised VertexDescriptor -> (stride, [(offset, lane_width,
    lane_count)]). Layout (attested on the TRK_UNIT285 set): 16B header with
    u16 numElements @+0x08, then numElements x 16B elements {u16 stream,
    u16 offset, u32 X360 GPU type dword, u16 usage, u16 usageIndex/slot,
    u32 1}, then numElements stride bytes (one per element, = the stride of
    the element's stream)."""
    num_elements = struct.unpack_from('>H', vd_bytes, 0x08)[0]
    elements = []
    for ei in range(num_elements):
        base = 0x10 + 16 * ei
        stream, offset = struct.unpack_from('>2H', vd_bytes, base)
        decl_type = struct.unpack_from('>I', vd_bytes, base + 4)[0]
        if stream != 0:
            raise TranscodeError('vertex descriptor: element %d on stream %d '
                                 '(multi-stream swap not modelled)' % (ei, stream))
        if decl_type not in X360_DECLTYPE_LANES:
            raise TranscodeError('vertex descriptor: unknown X360 decl type '
                                 '0x%06X @element %d' % (decl_type, ei))
        width, count = X360_DECLTYPE_LANES[decl_type]
        elements.append((offset, width, count))
    stride = vd_bytes[0x10 + 16 * num_elements]
    return stride, elements


def _merge_vd_lanes(vd_list):
    """Merge the (possibly per-pass, overlapping-subset) descriptors of one
    mesh into a single consistent lane map: (stride, {offset: width}), where
    each entry is one lane of `width` bytes to flip."""
    stride = None
    lanes = {}
    for vd_bytes in vd_list:
        vd_stride, elements = parse_vertex_descriptor(vd_bytes)
        if stride is None:
            stride = vd_stride
        elif stride != vd_stride:
            raise TranscodeError('vertex descriptors of one mesh disagree on '
                                 'stride (%d vs %d)' % (stride, vd_stride))
        for offset, width, count in elements:
            for lane in range(count):
                lane_off = offset + width * lane
                if lanes.setdefault(lane_off, width) != width:
                    raise TranscodeError('vertex descriptors of one mesh '
                                         'disagree on the lane @+0x%X' % lane_off)
    return stride, lanes


def _swap_region(buf, offset, count, width):
    """Byte-swap `count` lanes of `width` bytes at buf[offset...]."""
    end = offset + count * width
    fmt_be = '>%d%s' % (count, 'H' if width == 2 else 'I')
    fmt_le = '<%d%s' % (count, 'H' if width == 2 else 'I')
    values = struct.unpack(fmt_be, bytes(buf[offset:end]))
    buf[offset:end] = struct.pack(fmt_le, *values)


# ---------------------------------------------------------------------------
# body transcode
# ---------------------------------------------------------------------------
def transcode_renderable_body(body_bytes, parsed_header_info):
    """Endian-flip the GPU payload of one renderable: index data always
    (u16/u32 per the IB Common tag), vertex data per-attribute when the
    mesh's VertexDescriptor blobs are available in
    parsed_header_info.vd_lookup ({resource_id: bytes}); otherwise the
    vertex bytes are left big-endian with a printed warning."""
    p = parsed_header_info
    out = bytearray(body_bytes)
    warned = False

    for mi, mesh in enumerate(p.meshes):
        ib = mesh['ib_header']
        is_32bit = bool(ib[0] & 0x80000000)     # muCommon bit31 = 32-bit tag
        ib_base = ib[6] & ~3                    # muBaseAddress minus low flags
        ib_count = ib[8]                        # muIndexCount
        _swap_region(out, ib_base, ib_count, 4 if is_32bit else 2)

        vd_list = []
        for rid in mesh['vd_imports']:
            if rid is not None and rid in p.vd_lookup:
                vd_list.append(p.vd_lookup[rid])
        for vi, vb in enumerate(mesh['vb_headers']):
            vb_base = vb[6] & ~3                # muBaseAddress minus low flags
            vb_size = vb[8]                     # muSize
            if not vd_list or len(vd_list) != len([r for r in mesh['vd_imports'] if r is not None]):
                if not warned:
                    print('WARNING: mesh[%d] VB[%d]: vertex descriptors not '
                          'supplied -- vertex data left BIG-ENDIAN (TODO: '
                          'populate parsed_header_info.vd_lookup)' % (mi, vi))
                    warned = True
                continue
            stride, lanes = _merge_vd_lanes(vd_list)
            if vb_size % stride:
                print('WARNING: mesh[%d] VB[%d]: size 0x%X not a multiple of '
                      'stride %d -- trailing bytes left as-is' % (mi, vi, vb_size, stride))
            covered = sum(w for w in lanes.values())
            if covered < stride:
                print('WARNING: mesh[%d] VB[%d]: descriptors cover %d of %d '
                      'stride bytes -- gaps left as-is' % (mi, vi, covered, stride))
            for vertex in range(vb_size // stride):
                base = vb_base + vertex * stride
                for lane_off, width in lanes.items():
                    _swap_region(out, base + lane_off, 1, width)
    return bytes(out)


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------
def transcode_renderable(header_bytes, imports_yaml_text):
    """X360 serialised Renderable header + its YAP imports.yaml text ->
    (x64 little-endian widened header bytes, rewritten imports.yaml text)."""
    imports = parse_imports_yaml(imports_yaml_text)
    p = parse_renderable(header_bytes, imports)

    # round-trip identity: the X360 re-emit must reproduce the input exactly,
    # proving the parse covered/understood every byte
    if emit_x360(p) != bytes(header_bytes):
        raise TranscodeError('renderable: X360 round-trip mismatch -- '
                             'parser does not fully model this blob')

    new_header, new_imports = emit_x64(p)
    return new_header, emit_imports_yaml(new_imports)


def load_vertex_descriptors(extraction_dir):
    """{resource_id: bytes} for every VertexDescriptor/*.dat in a YAP
    extraction dir."""
    vd_dir = os.path.join(extraction_dir, 'VertexDescriptor')
    lookup = {}
    if os.path.isdir(vd_dir):
        for fname in os.listdir(vd_dir):
            if fname.lower().endswith('.dat'):
                with open(os.path.join(vd_dir, fname), 'rb') as fh:
                    lookup[int(fname[:-4], 16)] = fh.read()
    return lookup


# ---------------------------------------------------------------------------
# CLI: convert a YAP extraction dir in place
# ---------------------------------------------------------------------------
def convert_dir(extraction_dir, check_only=False):
    ren_dir = os.path.join(extraction_dir, 'Renderable')
    if not os.path.isdir(ren_dir):
        raise TranscodeError('no Renderable/ folder under %s' % extraction_dir)
    vd_lookup = load_vertex_descriptors(extraction_dir)

    count = 0
    for fname in sorted(os.listdir(ren_dir)):
        if not fname.endswith('_header.dat'):
            continue
        rid = fname[:-len('_header.dat')]
        header_path = os.path.join(ren_dir, fname)
        body_path = os.path.join(ren_dir, rid + '_body.dat')
        yaml_path = header_path + '_imports.yaml'

        with open(header_path, 'rb') as fh:
            header = fh.read()
        yaml_text = ''
        if os.path.isfile(yaml_path):
            with open(yaml_path, 'r', encoding='utf-8') as fh:
                yaml_text = fh.read()

        # already-converted guard (in-place safety): the x64 form is LE
        if struct.unpack_from('<H', header, 0x10)[0] == 11:
            print('skip %s: already little-endian' % rid)
            continue

        imports = parse_imports_yaml(yaml_text)
        info = parse_renderable(header, imports)
        info.vd_lookup = vd_lookup
        new_header, new_yaml = transcode_renderable(header, yaml_text)

        new_body = None
        if os.path.isfile(body_path):
            with open(body_path, 'rb') as fh:
                new_body = transcode_renderable_body(fh.read(), info)

        count += 1
        if check_only:
            continue
        with open(header_path, 'wb') as fh:
            fh.write(new_header)
        with open(yaml_path, 'w', encoding='utf-8', newline='') as fh:
            fh.write(new_yaml)
        if new_body is not None:
            with open(body_path, 'wb') as fh:
                fh.write(new_body)
    return count


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 1:
        sys.stderr.write(__doc__)
        return 2
    check_only = '--check' in sys.argv
    count = convert_dir(args[0], check_only)
    print('%s %d renderables in %s'
          % ('validated' if check_only else 'converted', count, args[0]))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
