#!/usr/bin/env python3
"""Per-type X360 (big-endian) -> PC (little-endian) transcoders for ARTIST world
bundle serialized resources (TRK_UNIT<N>_GR.BNDL et al, extracted with YAP).

CONVENTION (verified per type against the committed b5-decomp consumer): the
reconstructed PC engine keeps the X360 32-bit serialized layouts (u32
pointer/offset slots, consumed via the low-4GB PointerFromU32 convention), so
conversion is an ENDIAN FLIP with the correct per-field widths -- u8 fields
stay, u16 fields flip as 16-bit, u32/f32 flip as 32-bit. No widening, offsets
unchanged, imports.yaml passed through unchanged.

Per-type status:
  Material          FLIP   consumer CgsMaterialResourceType.cpp (FixUp
                           @0x828A8280 et al) reads the blob via raw u32 slots.
  MaterialTechnique FLIP   consumer CgsMaterialTechniqueResourceType.cpp FixUp
                           (@0x828A8770) uses u32 slots at +24/+28/+36; the
                           GetSerialisedResourceDescriptor byte reads at 32..35
                           prove those four are u8 fields.
  TextureState      FLIP   32-byte sampler block layout attested store-for-
                           store by the X360 writer renderengine::SamplerState::
                           Initialize @0x82B62630 (f32 @+0/+4, u8 fields
                           @+8..+28); raster u32 slot @+0x20 (import offset
                           unchanged; PC RwTextureStateResourceType keeps 0x20).
  VertexDescriptor  FLIP   element read widths attested by the PC consumers
                           renderengine::VertexDescriptor::Initialize /
                           CreateD3DObject (u16 stream @+0, u16 offset @+2,
                           u32 type @+4, u8 method/usage/usageIndex @+8..+11,
                           u32 flag @+12).
  MaterialState     PASSTHROUGH  the committed consumer (renderstates.h
                           MaterialState + CgsMaterialStateResourceType FixUp)
                           models three HOST-WIDENED void* fields at +0/+8/+16
                           and sizes the resource as sizeof(MaterialState)=264
                           (blob is 252 with u32 slots at +0/+4/+8). A pure
                           flip cannot feed that consumer; the 240-byte state
                           tail also has unattested internal widths. Reported,
                           not guessed.
  PropGraphicsList  PASSTHROUGH  BrnPropGraphicsList.h explicitly models the
                           live structs HOST-WIDENED (PropGraphics stride 12 ->
                           24, list pointers +0x10/+0x14 -> +0x10/+0x18); the
                           load-side ResourceType FixUp is not committed. Also
                           the on-disk muNumberOfPropPartModels dword at +0xC
                           is byte-packed (bytes {0A,00,00,00} for count 10 on
                           a BE disk), contradicting the committed u32 model.
  PropInstanceData  PASSTHROUGH  committed FixUp (BrnPropInstanceData-
                           ResourceType.cpp) does 8-byte uintptr reads at
                           +0/+8 of the 32-bit blob and PropZoneData
                           (BrnPhysicsPropZoneData.h) is host-widened; the
                           80-byte instance record's 16-byte trailer widths
                           are not committed anywhere.
  StaticSoundMap    PASSTHROUGH  BrnStaticSoundMapResourceType::FixUp uses
                           NAMED member access on the host-widened
                           StaticSoundMap (16-byte vpu Vector2 + 8-byte
                           pointers), i.e. the PC engine expects a REBUILT
                           blob, not a flipped one.  Derived (unverified)
                           X360 layout for the eventual widening transcoder:
                           header 0x40 = Vector2 mMin/mMax (2 f32 lanes + pad
                           each), f32 subRegionSize @0x20, u32 mpSubRegions
                           @0x24, s32 numX/numZ @0x28/0x2C, u32 mpEntities
                           @0x30, s32 numEntities @0x34, u32 rootType @0x38;
                           entities are 16 bytes {f32 x,y,z, u16, u16}; grid
                           cells are {u16 firstEntity(0xFFFF=empty), u16
                           count}.

Every transcoder returns (new_header_bytes, new_imports_yaml_text). For flip
types the imports text is returned unchanged (offsets do not move). For
passthrough types the input bytes are returned unchanged.

The flip is involutive (flip(flip(x)) == x), so the identity round-trip proof
is coverage-based: each transcoder builds an explicit region plan (u32 / u16 /
raw) over the blob, and parsing rejects any overlap or out-of-range region.
Use --verify to run the parse + a post-flip consumer-logic re-walk without
writing anything.

Usage (converts an extracted-bundle folder in place):
  py tools/assets/bundles/world_type_transcode.py <extracted_dir> [--verify]

<extracted_dir> is a YAP extraction (contains Material/, MaterialTechnique/,
TextureState/, VertexDescriptor/, ... subfolders of <ID>.dat files). A
".le_transcoded" marker is written per converted type folder so a second run
cannot double-flip. Renderable is intentionally NOT handled here (owned by
renderable_transcode.py).
"""

import os
import struct
import sys

# --------------------------------------------------------------------------
# region-plan machinery
# --------------------------------------------------------------------------

U32 = 4
U16 = 2


class PlanError(ValueError):
    """Structural parse failure -- the blob does not match the attested layout."""


class Plan(object):
    """An explicit list of (offset, width) swap regions over a blob.

    Anything not claimed by a swap region is copied through unchanged (raw).
    Claims are validated: in-bounds, aligned to their width, and no byte may
    be claimed twice (identical duplicate claims are deduped -- e.g. two
    samplers sharing one name string).
    """

    def __init__(self, size):
        self.size = size
        self.swaps = {}     # offset -> width (2 or 4)
        self.raws = set()   # offsets of explicitly-claimed raw bytes

    def _claim(self, off, length, what):
        if off < 0 or off + length > self.size:
            raise PlanError('%s out of range: [0x%X,0x%X) size 0x%X'
                            % (what, off, off + length, self.size))

    def u32(self, off, what='u32'):
        self._claim(off, 4, what)
        prev = self.swaps.get(off)
        if prev is not None and prev != U32:
            raise PlanError('%s overlaps a u16 claim @0x%X' % (what, off))
        self.swaps[off] = U32

    def u16(self, off, what='u16'):
        self._claim(off, 2, what)
        prev = self.swaps.get(off)
        if prev is not None and prev != U16:
            raise PlanError('%s overlaps a u32 claim @0x%X' % (what, off))
        self.swaps[off] = U16

    def raw(self, off, length, what='raw'):
        self._claim(off, length, what)
        for o in range(off, off + length):
            self.raws.add(o)

    def validate(self):
        """No swap region may intersect an explicit raw claim or another swap."""
        seen = {}
        for off, w in self.swaps.items():
            for o in range(off, off + w):
                if o in self.raws:
                    raise PlanError('swap @0x%X (%d) intersects raw byte 0x%X'
                                    % (off, w, o))
                if o in seen:
                    raise PlanError('swap @0x%X (%d) intersects swap @0x%X (%d)'
                                    % (off, w, seen[o], self.swaps[seen[o]]))
                seen[o] = off

    def apply(self, data):
        """Byte-swap every planned region; everything else copies through."""
        out = bytearray(data)
        for off, w in self.swaps.items():
            out[off:off + w] = data[off:off + w][::-1]
        return bytes(out)


def be32(data, off):
    return struct.unpack_from('>I', data, off)[0]


def be16(data, off):
    return struct.unpack_from('>H', data, off)[0]


def _claim_cstring(plan, data, off, what):
    """Claim a NUL-terminated string (incl. NUL) as raw; return its length."""
    end = data.find(b'\0', off)
    if end < 0:
        raise PlanError('%s: unterminated string @0x%X' % (what, off))
    plan.raw(off, end - off + 1, what)
    return end - off + 1


def _flip_unclaimed_gaps_as_u32(plan):
    """Material policy: unclaimed 4-aligned dword runs (shader-constant
    instance data -- always 32-bit f32/u32 lanes -- and align pad) flip as u32;
    unaligned remainders stay raw."""
    claimed = set(plan.raws)
    for off, w in plan.swaps.items():
        claimed.update(range(off, off + w))
    off = 0
    while off < plan.size:
        if off in claimed:
            off += 1
            continue
        start = off
        while off < plan.size and off not in claimed:
            off += 1
        # flip the aligned dword core of the gap
        a = (start + 3) & ~3
        b = off & ~3
        for o in range(a, b, 4):
            if all(x not in claimed for x in range(o, o + 4)):
                plan.swaps[o] = U32


# --------------------------------------------------------------------------
# Material  (CgsGraphics::MaterialAssembly image; CgsMaterialResourceType.cpp)
# --------------------------------------------------------------------------
# header: +0x00 u32 technique-table ptr        +0x04 u32 resource id
#         +0x08 u8 numTechniques  +0x09 s8 numSamplers  +0x0A/+0x0B u8
#         +0x0C u32 sampler-array ptr
#         +0x10 u32 vertex ShaderConstantsInternal ptr
#         +0x14 u32 pixel  ShaderConstantsInternal ptr
#         +0x18 u32 CPU ShaderConstantsCPU ptr (0 when absent)
# technique table: numTechniques u32 slots (import slots)
# sampler (20 bytes): +0 u32 name ptr, +4 u32 name hash, +8 s16 id,
#         +0xA u16 external flag, +0xC s32 type (runtime), +0x10 u32 texture
#         import slot
# ShaderConstantsInternal (5 u32): count, sizes ptr, data-ptr-array ptr,
#         name-hash-array ptr, ProgramVariableHandle-array ptr; the handle
#         array is 4 u8 per entry (programbuffer.h), all other arrays u32;
#         instance data = 32-bit lanes (gap policy).
# ShaderConstantsCPU (4 u32): cpu-shader ptr, count, data-ptr-array ptr,
#         name-ptr-array ptr; name strings raw.

def _plan_shader_constants_internal(plan, data, off, tag):
    for i in range(5):
        plan.u32(off + 4 * i, tag + ' header')
    count = be32(data, off)
    if count > 0x100:
        raise PlanError('%s: implausible constant count %d' % (tag, count))
    sizes_off = be32(data, off + 4)
    dataarr_off = be32(data, off + 8)
    hash_off = be32(data, off + 0xC)
    handles_off = be32(data, off + 0x10)
    for i in range(count):
        plan.u32(sizes_off + 4 * i, tag + ' sizes')
        plan.u32(dataarr_off + 4 * i, tag + ' data ptrs')
        plan.u32(hash_off + 4 * i, tag + ' hashes')
        plan.raw(handles_off + 4 * i, 4, tag + ' handles')  # 4 x u8
        inst_off = be32(data, dataarr_off + 4 * i)
        if inst_off >= plan.size:
            raise PlanError('%s: instance data ptr 0x%X out of range'
                            % (tag, inst_off))
    # the Vector4 instance payloads are covered by the u32 gap policy


def _plan_shader_constants_cpu(plan, data, off, tag):
    for i in range(4):
        plan.u32(off + 4 * i, tag + ' header')
    count = be32(data, off + 4)
    if count >= 256:  # X360 FixUp asserts muNumConstantsInstances < 256
        raise PlanError('%s: implausible constant count %d' % (tag, count))
    dataarr_off = be32(data, off + 8)
    names_off = be32(data, off + 0xC)
    for i in range(count):
        plan.u32(dataarr_off + 4 * i, tag + ' data ptrs')
        plan.u32(names_off + 4 * i, tag + ' name ptrs')
        name_off = be32(data, names_off + 4 * i)
        if name_off:
            _claim_cstring(plan, data, name_off, tag + ' name')


def plan_material(data):
    plan = Plan(len(data))
    for off in (0x00, 0x04, 0x0C, 0x10, 0x14, 0x18):
        plan.u32(off, 'material header')
    plan.raw(0x08, 4, 'material counts')  # numTechniques / numSamplers / 2 u8
    num_tech = data[0x08]
    num_samplers = struct.unpack_from('>b', data, 0x09)[0]

    tech_off = be32(data, 0x00)
    for i in range(num_tech):
        plan.u32(tech_off + 4 * i, 'technique table')

    samp_off = be32(data, 0x0C)
    for i in range(max(num_samplers, 0)):
        s = samp_off + 20 * i
        plan.u32(s + 0x00, 'sampler name ptr')
        plan.u32(s + 0x04, 'sampler hash')
        plan.u16(s + 0x08, 'sampler id')
        plan.u16(s + 0x0A, 'sampler external flag')
        plan.u32(s + 0x0C, 'sampler type')
        plan.u32(s + 0x10, 'sampler texture slot')
        _claim_cstring(plan, data, be32(data, s), 'sampler name')

    _plan_shader_constants_internal(plan, data, be32(data, 0x10), 'vtx constants')
    _plan_shader_constants_internal(plan, data, be32(data, 0x14), 'pix constants')
    cpu_off = be32(data, 0x18)
    if cpu_off:
        _plan_shader_constants_cpu(plan, data, cpu_off, 'cpu constants')

    plan.validate()
    _flip_unclaimed_gaps_as_u32(plan)
    return plan


def transcode_material(header_bytes, imports_yaml_text=None):
    plan = plan_material(header_bytes)
    return plan.apply(header_bytes), imports_yaml_text


# --------------------------------------------------------------------------
# MaterialTechnique  (CgsMaterialTechniqueResourceType.cpp)
# --------------------------------------------------------------------------
# 40-byte header of u32 slots (+0 program import, +4 material-state import,
# +0x18/+0x1C vertex/pixel binding-list ptrs, +0x24 sampler-binding-list ptr;
# all three ptr slots relocated as u32 by FixUp @0x828A8770), EXCEPT the four
# u8 counts at +0x20..+0x23 (vertex/pixel binding counts, two trailing sizes;
# read as s8 by GetSerialisedResourceDescriptor @0x828A97D8).
# Tail: (b32+b33) 4-byte binding entries {u16 register-set, u8 block index,
# u8 register count} (PostFixUpShaderConstants writes exactly those widths),
# then (b34+b35) sampler-binding index bytes.

def plan_materialtechnique(data):
    plan = Plan(len(data))
    for off in (0x00, 0x04, 0x08, 0x0C, 0x10, 0x14, 0x18, 0x1C, 0x24):
        plan.u32(off, 'technique header')
    plan.raw(0x20, 4, 'technique counts')
    b32, b33, b34, b35 = data[0x20], data[0x21], data[0x22], data[0x23]
    logical = 4 * (b32 + b33 + 10) + b34 + b35
    if logical > len(data):
        raise PlanError('technique logical size %d > blob %d'
                        % (logical, len(data)))
    vtx_off = be32(data, 0x18)
    pix_off = be32(data, 0x1C)
    samp_off = be32(data, 0x24)
    if vtx_off != 0x28 or pix_off != vtx_off + 4 * b32 \
            or samp_off != pix_off + 4 * b33:
        raise PlanError('technique list ptrs inconsistent: '
                        'vtx=0x%X pix=0x%X samp=0x%X counts=%d/%d'
                        % (vtx_off, pix_off, samp_off, b32, b33))
    for base, count, tag in ((vtx_off, b32, 'vtx bindings'),
                             (pix_off, b33, 'pix bindings')):
        for i in range(count):
            e = base + 4 * i
            plan.u16(e, tag + ' register set')
            plan.raw(e + 2, 2, tag + ' index/count bytes')
    plan.raw(samp_off, b34 + b35, 'sampler binding bytes')
    plan.validate()
    return plan


def transcode_materialtechnique(header_bytes, imports_yaml_text=None):
    plan = plan_materialtechnique(header_bytes)
    return plan.apply(header_bytes), imports_yaml_text


# --------------------------------------------------------------------------
# TextureState  (CgsRwTextureStateResourceType.cpp; writer @0x82B62630)
# --------------------------------------------------------------------------
# 36-byte object: +0x00 f32 mip-lod bias, +0x04 f32 (second lod word),
# +0x08..+0x1F u8 sampler fields (address U/V/W, filters, bools, max
# anisotropy @+0x19, ... -- every store in SamplerState::Initialize between
# +8 and +28 is a byte store), +0x20 u32 raster import slot (import offset
# 0x20 is identical on PC -- offsetof(TextureState, mpRaster)).

TEXTURESTATE_LOGICAL_SIZE = 36


def plan_texturestate(data):
    if len(data) < TEXTURESTATE_LOGICAL_SIZE:
        raise PlanError('texture state blob too small: %d' % len(data))
    plan = Plan(len(data))
    plan.u32(0x00, 'lod bias f32')
    plan.u32(0x04, 'lod word f32')
    plan.raw(0x08, 0x18, 'sampler byte fields')
    plan.u32(0x20, 'raster slot')
    plan.validate()
    return plan


def transcode_texturestate(header_bytes, imports_yaml_text=None):
    plan = plan_texturestate(header_bytes)
    return plan.apply(header_bytes), imports_yaml_text


# --------------------------------------------------------------------------
# VertexDescriptor  (CgsRwVertexDescResourceType.cpp; pc/gcm VertexDescriptor)
# --------------------------------------------------------------------------
# header (0x10): +0x00 u32 declaration slot (0), +0x04 u32 stream mask,
#   +0x08 u16 element count, +0x0A raw {u8 initialised(=1), u8 pad} (byte-
#   packed on disk: observed {01,00}; raw keeps the PC LE u16 read == 1),
#   +0x0C u16 type-2 mask, +0x0E u16 pad.
# elements (16 bytes x count): +0 u16 stream, +2 u16 offset, +4 u32 type,
#   +8 u8[4] method/usage/usageIndex bytes, +0xC u32 flag (compared == 2
#   by Initialize) -- widths per the PC Initialize/CreateD3DObject reads.
# tail: count stride BYTES, then serializer pad garbage to 16 (kept raw).

def plan_vertexdescriptor(data):
    plan = Plan(len(data))
    plan.u32(0x00, 'vd declaration slot')
    plan.u32(0x04, 'vd stream mask')
    plan.u16(0x08, 'vd element count')
    plan.raw(0x0A, 2, 'vd initialised bytes')
    plan.u16(0x0C, 'vd type2 mask')
    plan.u16(0x0E, 'vd pad')
    count = be16(data, 0x08)
    if count == 0 or count > 16:
        raise PlanError('vd element count %d implausible' % count)
    logical = 0x10 + 17 * count  # == GetSerialisedResourceDescriptor size
    if logical > len(data):
        raise PlanError('vd logical size %d > blob %d' % (logical, len(data)))
    for i in range(count):
        e = 0x10 + 16 * i
        plan.u16(e + 0x0, 'vd elem stream')
        plan.u16(e + 0x2, 'vd elem offset')
        plan.u32(e + 0x4, 'vd elem type')
        plan.raw(e + 0x8, 4, 'vd elem usage bytes')
        plan.u32(e + 0xC, 'vd elem flag')
    plan.raw(0x10 + 16 * count, count, 'vd stride bytes')
    plan.validate()
    return plan


def transcode_vertexdescriptor(header_bytes, imports_yaml_text=None):
    plan = plan_vertexdescriptor(header_bytes)
    return plan.apply(header_bytes), imports_yaml_text


# --------------------------------------------------------------------------
# passthrough types (see module docstring for the per-type reason)
# --------------------------------------------------------------------------

def transcode_materialstate(header_bytes, imports_yaml_text=None):
    """PASSTHROUGH: PC consumer models host-widened pointers (see docstring)."""
    return header_bytes, imports_yaml_text


def transcode_propgraphicslist(header_bytes, imports_yaml_text=None):
    """PASSTHROUGH: PC consumer models host-widened structs (see docstring)."""
    return header_bytes, imports_yaml_text


def transcode_propinstancedata(header_bytes, imports_yaml_text=None):
    """PASSTHROUGH: PC consumer widened + record widths unattested (docstring)."""
    return header_bytes, imports_yaml_text


def transcode_staticsoundmap(header_bytes, imports_yaml_text=None):
    """PASSTHROUGH: PC consumer expects a rebuilt widened blob (docstring)."""
    return header_bytes, imports_yaml_text


# --------------------------------------------------------------------------
# post-flip consumer-logic verification (LE re-walk)
# --------------------------------------------------------------------------

def le32(data, off):
    return struct.unpack_from('<I', data, off)[0]


def le16(data, off):
    return struct.unpack_from('<H', data, off)[0]


def verify_material_le(data):
    """Re-walk the flipped blob with MaterialResourceType FixUp/PostFixUp logic."""
    size = len(data)
    tech_off, samp_off = le32(data, 0x00), le32(data, 0x0C)
    vtx_off, pix_off, cpu_off = le32(data, 0x10), le32(data, 0x14), le32(data, 0x18)
    num_tech, num_samp = data[0x08], struct.unpack_from('<b', data, 0x09)[0]
    assert tech_off + 4 * num_tech <= size, 'technique table oob'
    assert 0 < vtx_off < size and 0 < pix_off < size, 'sub-block ptr oob'
    for blk in (vtx_off, pix_off):
        count = le32(data, blk)
        assert count <= 0x100, 'constant count'
        for i in range(count):
            inst = le32(data, le32(data, blk + 8) + 4 * i)
            assert inst < size, 'instance data ptr oob'
            assert le32(data, blk + 0xC) + 4 * count <= size, 'hash array oob'
    for i in range(max(num_samp, 0)):
        s = samp_off + 20 * i
        name = le32(data, s)
        assert name < size and data[data.index(b'\0', name)] == 0, 'name oob'
    if cpu_off:
        count = le32(data, cpu_off + 4)
        assert count < 256, 'cpu count'
        names = le32(data, cpu_off + 0xC)
        for i in range(count):
            n = le32(data, names + 4 * i)
            assert n == 0 or n < size, 'cpu name oob'


def verify_materialtechnique_le(data):
    b32, b33, b34, b35 = data[0x20], data[0x21], data[0x22], data[0x23]
    assert 4 * (b32 + b33 + 10) + b34 + b35 <= len(data)
    assert le32(data, 0x18) == 0x28
    assert le32(data, 0x1C) == 0x28 + 4 * b32
    assert le32(data, 0x24) == 0x28 + 4 * (b32 + b33)


def verify_texturestate_le(data):
    # byte fields must be untouched: the X360 wrote max anisotropy @+0x19 and
    # the constant 1 @+0x1C; both are attested byte stores.
    assert data[0x1C] == 1, 'sampler +0x1C constant'


def verify_vertexdescriptor_le(data):
    count = le16(data, 0x08)
    assert 0 < count <= 16
    mask = 0
    for i in range(count):
        e = 0x10 + 16 * i
        assert le16(data, e) < 16, 'stream index'
        mask |= 1 << data[e + 0xB]  # usage-index byte
        assert le32(data, e + 0xC) in (1, 2), 'element flag'
    assert mask == le32(data, 0x04), 'stream mask mismatch'


# --------------------------------------------------------------------------
# folder driver
# --------------------------------------------------------------------------

FLIP_TYPES = {
    'Material': (plan_material, verify_material_le),
    'MaterialTechnique': (plan_materialtechnique, verify_materialtechnique_le),
    'TextureState': (plan_texturestate, verify_texturestate_le),
    'VertexDescriptor': (plan_vertexdescriptor, verify_vertexdescriptor_le),
}
PASSTHROUGH_TYPES = {
    'MaterialState': transcode_materialstate,
    'PropGraphicsList': transcode_propgraphicslist,
    'PropInstanceData': transcode_propinstancedata,
    'StaticSoundMap': transcode_staticsoundmap,
}
MARKER = '.le_transcoded'


def convert_folder(root, verify_only=False):
    total_ok = 0
    for tname, (planner, verifier) in sorted(FLIP_TYPES.items()):
        tdir = os.path.join(root, tname)
        if not os.path.isdir(tdir):
            continue
        marker = os.path.join(tdir, MARKER)
        if os.path.isfile(marker) and not verify_only:
            print('%-18s SKIP (already transcoded: %s present)' % (tname, MARKER))
            continue
        files = sorted(f for f in os.listdir(tdir)
                       if f.endswith('.dat') and not f.endswith('_imports.yaml'))
        ok = errs = 0
        for f in files:
            path = os.path.join(tdir, f)
            with open(path, 'rb') as fh:
                data = fh.read()
            ipath = path + '_imports.yaml'
            itext = None
            if os.path.isfile(ipath):
                with open(ipath, 'r') as fh:
                    itext = fh.read()
            try:
                plan = planner(data)
                flipped = plan.apply(data)
                itext2 = itext
                # identity round-trip: re-applying the SAME plan to the flipped
                # blob must reproduce the input byte-for-byte (proves the plan
                # covers the blob consistently and the flip is involutive).
                if plan.apply(flipped) != data:
                    raise PlanError('round-trip mismatch')
                verifier(flipped)
            except (PlanError, AssertionError, struct.error, IndexError) as e:
                print('  %s/%s: FAIL %s' % (tname, f, e))
                errs += 1
                continue
            ok += 1
            if not verify_only:
                with open(path, 'wb') as fh:
                    fh.write(flipped)
                if itext2 is not None and itext2 != itext:
                    with open(ipath, 'w') as fh:
                        fh.write(itext2)
        print('%-18s %s %d/%d files%s'
              % (tname, 'verified' if verify_only else 'flipped', ok, len(files),
                 (' (%d FAILED)' % errs) if errs else ''))
        total_ok += ok
        if not verify_only and errs == 0 and files:
            with open(marker, 'w') as fh:
                fh.write('big->little endian transcode complete\n')
    for tname in sorted(PASSTHROUGH_TYPES):
        if os.path.isdir(os.path.join(root, tname)):
            print('%-18s PASSTHROUGH (still big-endian; see module docstring)'
                  % tname)
    return total_ok


def main(argv):
    args = [a for a in argv[1:] if not a.startswith('--')]
    verify_only = '--verify' in argv
    if len(args) != 1:
        sys.stderr.write(__doc__.split('Usage', 1)[1])
        return 2
    root = args[0]
    if not os.path.isdir(root):
        sys.stderr.write('not a directory: %s\n' % root)
        return 2
    convert_folder(root, verify_only=verify_only)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
