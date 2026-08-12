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
  MaterialState     WIDEN  252-byte X360 blob -> the 264-byte x64 blob the
                           committed consumer reads (renderstates.h
                           MaterialState: three host-widened pointers at
                           +0/+8/+16; CgsMaterialStateResourceType FixUp
                           rebases all three; GetSerialisedResourceDescriptor
                           sizes it as sizeof(MaterialState)=264).
                           X360 blob layout (uniform across every sampled
                           resource; ptr values always {0xC, 0x5C, 0xBC}):
                             +0x00 u32 mpBlendState        -> +0x0C
                             +0x04 u32 mpDepthStencilState -> +0x5C
                             +0x08 u32 mpRasterizerState   -> +0xBC
                             +0x0C  BlendState: 19 u32 (Initialize @0x82B627C8
                                    is stw-only; the last word +0x48 = the
                                    initialised flag) + 4 pad
                             +0x5C  DepthStencilState: 24 u32 (17 state words
                                    + 6 widened bool words + initialised word;
                                    GetResourceDescriptor @0x82B636F8 attests
                                    the 0x60 object size)
                             +0xBC  RasterizerState: 13 u32 (Initialize
                                    @0x82B62958 stw-only; +0x28 = the u32 the
                                    MaterialState FixDown @0x828A8A80 marks,
                                    +0x30 = initialised) + 12 pad
                           ANOMALY (ARTIST bake-tool): the three initialised
                           words are LITTLE-endian on the BE disk (bytes
                           {01,00,00,00}); the X360 only ever tests them
                           non-zero. They are kept RAW so the LE runtime reads
                           a true 1. x64 form: three u64 offset slots
                           {0x18, 0x68, 0xC8} + the same 240-byte state tail
                           (all-u32 flip).
  PropGraphicsList  WIDEN  BrnPropGraphicsList.h models the live structs
                           HOST-WIDENED: list header 0x18 -> 0x20 (table
                           pointers u64 @+0x10/+0x18), PropGraphics stride
                           12 -> 24 {u32 typeId, pad, Model* @+8,
                           PropPartGraphics* @+0x10}, PropPartGraphics stride
                           12 -> 16 {u32 typeId, u32 partId, Model* @+8}.
                           muSizeInBytes is recomputed; mpParts offsets are
                           remapped by part INDEX; the Model slots are
                           serialised null IMPORT slots (X360 GetImportPointer
                           @0x82677720: import i<numModels -> graphics elem
                           +4, else part (i-numModels) +8), so the
                           imports.yaml offsets are REWRITTEN (+8 slots at the
                           widened strides).
                           ANOMALY (ARTIST bake-tool): muNumberOfPropPartModels
                           @+0xC AND every PropPartGraphics record are
                           LITTLE-endian on the BE disk (the X360 import walk
                           is driven by the bundle's own import table, which
                           is consistent, so the console never notices). The
                           transcoder validates both readings and emits true
                           LE values.
  PropInstanceData  WIDEN  serialised PropZoneData: header 0x1C -> 0x28
                           (BrnPhysicsPropZoneData.h host order: maCells u64
                           @0, muNumCells u8 @8, maInstances u64 @0x10,
                           muSizeInBytes @0x18, muNumberOfInstances @0x1C,
                           muNumberOfProps @0x20, muZoneId u16 @0x24), the
                           instance array re-based to +0x30 (16-aligned for
                           the embedded Matrix44Affine). The 80-byte instance
                           record does NOT widen (pointer-free): 4x16 matrix
                           (u32/f32 lanes) + trailer {u32 typeFlags @+64
                           (LoadProp @0x822F2EF0 masks & 0x3FFFFFF), u32 id
                           @+68 (InitialiseFromData @0x822B80E8), u16 @+72,
                           u8 @+74 (the & 0xC0 animation bits, byte-attested),
                           u8 @+75, u32 @+76}. PropCellData stays 12 bytes
                           (6 u16). The reserved zero tail after the cell
                           array is preserved byte-for-byte; muSizeInBytes and
                           the two header offsets are recomputed.
  StaticSoundMap    WIDEN  header 0x40 -> 0x50 (BrnStaticSoundMap.h host
                           order over the 16-byte vpu Vector2: mMin @0, mMax
                           @0x10, mfSubRegionSize f32 @0x20, mpSubRegions u64
                           @0x28, miNumSubRegionsX/Z @0x30/0x34, mpEntities
                           u64 @0x38, miNumEntities @0x40, meRootType @0x44,
                           pad to 0x50). X360 header: subRegionSize @0x20,
                           mpSubRegions u32 @0x24, numX/numZ @0x28/0x2C,
                           mpEntities u32 @0x30, numEntities @0x34, rootType
                           @0x38 (FixUp @0x826775C8 / descriptor @0x8267AFC0
                           offsets). Entities 16 bytes {f32 x,y,z, u16, u16}
                           (GetEntity @0x82675578 16-stride); grid cells
                           {u16 firstEntity (0xFFFF=empty), u16 count}
                           (validated: cell ranges tile [0, numEntities)).

Every transcoder returns (new_header_bytes, new_imports_yaml_text). For flip
types the imports text is returned unchanged (offsets do not move); the
widening PropGraphicsList transcoder rewrites the import offsets.

The flip is involutive (flip(flip(x)) == x), so the identity round-trip proof
is coverage-based: each transcoder builds an explicit region plan (u32 / u16 /
raw) over the blob, and parsing rejects any overlap or out-of-range region.
The widening transcoders are NOT involutive; each has an explicit inverse
(narrow_*) and the round-trip proof is inverse(widen(x)) == x over the blob's
logical bytes (trailing 16-align serializer pad is dropped, renderable_
transcode precedent). Use --verify to run parse + round-trip + a post-
transcode LE consumer-logic re-walk without writing anything.

Usage (converts an extracted-bundle folder in place):
  py tools/assets/bundles/world_type_transcode.py <extracted_dir> [--verify]

<extracted_dir> is a YAP extraction (contains Material/, MaterialTechnique/,
TextureState/, VertexDescriptor/, ... subfolders of <ID>.dat files). A
".le_transcoded" marker is written per converted type folder so a second run
cannot double-flip. Renderable is intentionally NOT handled here (owned by
renderable_transcode.py).
"""

import os
import re
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
# widening transcoders (X360 32-bit blob -> the x64 blob the committed
# host-widened consumers read; see the module docstring per type). Each has
# an explicit narrow_* inverse; transcode_* proves inverse(widen(x)) == x
# over the logical bytes and re-walks the result with the PC consumer logic.
# --------------------------------------------------------------------------

def _u32_flip_range(out, data, start, end, delta=0):
    """Flip u32 lanes data[start:end] into out[start+delta : end+delta]."""
    for o in range(start, end, 4):
        out[o + delta:o + delta + 4] = data[o:o + 4][::-1]


# ---- MaterialState --------------------------------------------------------
# X360 blob geometry (uniform across every sampled resource -- asserted).
MS_X360_SIZE = 252
MS_X64_SIZE = 264
MS_X360_PTRS = (0x0C, 0x5C, 0xBC)            # blend / depth-stencil / rasterizer
MS_X64_PTRS = (0x18, 0x68, 0xC8)             # same blocks, +12 (3 ptrs widen 4->8)
# LE-baked (bake-tool anomaly) initialised words, kept RAW: blend +0x48,
# depth-stencil +0x5C, rasterizer +0x30.
MS_INIT_WORDS = (0x0C + 0x48, 0x5C + 0x5C, 0xBC + 0x30)
# serializer pad regions (junk-bearing, copied RAW): blend tail, rasterizer tail
MS_RAW_PADS = ((0x58, 0x5C), (0xF0, 0xFC))


def _materialstate_tail(out, data):
    """Transcode the 240-byte state tail (an involution: u32 lane flips with
    the init words + pads copied raw). `data` is indexed at X360 blob offsets
    0x0C..0xFC; `out` receives the tail at index 0."""
    for o in range(0x0C, MS_X360_SIZE, 4):
        src = data[o:o + 4]
        raw = (o in MS_INIT_WORDS) or any(a <= o < b for a, b in MS_RAW_PADS)
        out[o - 0x0C:o - 0x0C + 4] = src if raw else src[::-1]


def transcode_materialstate(header_bytes, imports_yaml_text=None):
    d = header_bytes
    if len(d) < MS_X360_SIZE:
        raise PlanError('MaterialState blob too small: %d' % len(d))
    ptrs = struct.unpack_from('>3I', d, 0)
    if ptrs != MS_X360_PTRS:
        raise PlanError('MaterialState ptrs %s != canonical %s'
                        % (tuple(hex(p) for p in ptrs),
                           tuple(hex(p) for p in MS_X360_PTRS)))
    for o in MS_INIT_WORDS:
        if d[o:o + 4] not in (b'\x01\x00\x00\x00', b'\x00\x00\x00\x01'):
            raise PlanError('MaterialState initialised word @0x%X = %s'
                            % (o, d[o:o + 4].hex()))
    out = bytearray(MS_X64_SIZE)
    struct.pack_into('<3Q', out, 0, *MS_X64_PTRS)
    tail = bytearray(MS_X360_SIZE - 0x0C)
    _materialstate_tail(tail, d)
    out[0x18:] = tail
    # round-trip: narrow back and compare against the logical bytes
    if narrow_materialstate(bytes(out)) != d[:MS_X360_SIZE]:
        raise PlanError('MaterialState round-trip mismatch')
    verify_materialstate_le(bytes(out))
    return bytes(out), imports_yaml_text


def narrow_materialstate(x64_bytes):
    d = x64_bytes
    ptrs = struct.unpack_from('<3Q', d, 0)
    if ptrs != MS_X64_PTRS:
        raise PlanError('narrow: x64 ptrs %s unexpected' % (ptrs,))
    out = bytearray(MS_X360_SIZE)
    struct.pack_into('>3I', out, 0, *MS_X360_PTRS)
    # re-run the (involutive) tail transform over a re-based view
    shifted = bytearray(MS_X360_SIZE)
    shifted[0x0C:] = d[0x18:0x18 + MS_X360_SIZE - 0x0C]
    tail = bytearray(MS_X360_SIZE - 0x0C)
    _materialstate_tail(tail, bytes(shifted))
    out[0x0C:] = tail
    return bytes(out)


def verify_materialstate_le(data):
    """Re-walk with the committed PC consumer logic (CgsMaterialStateResource-
    Type FixUp rebases 3 u64 slots; renderstates.h sub-object map)."""
    assert len(data) == MS_X64_SIZE
    blend, ds, rast = struct.unpack_from('<3Q', data, 0)
    assert (blend, ds, rast) == MS_X64_PTRS, 'sub-object offsets'
    # every initialised word must read non-zero on LE (the runtime only tests
    # non-zero; the kept-raw LE bake means they read exactly 1)
    for base, rel in ((blend, 0x48), (ds, 0x5C), (rast, 0x30)):
        assert le32(data, base + rel) == 1, 'initialised word'
    assert le32(data, ds + 0x00) < 16, 'depth-stencil function word'
    assert le32(data, rast + 0x28) == 1, 'FixDown-marked rasterizer word'


# ---- PropGraphicsList -----------------------------------------------------

def _parse_propgraphicslist(d):
    size, zone, num_models = struct.unpack_from('>3I', d, 0)
    num_parts = struct.unpack_from('<I', d, 0x0C)[0]     # LE-baked (docstring)
    g_off, p_off = struct.unpack_from('>2I', d, 0x10)
    if size > len(d) or g_off + 12 * num_models > size:
        raise PlanError('PropGraphicsList header out of range')
    if g_off == 0:
        # empty list (TRK_UNIT0 et al): both tables null, no elements
        if num_models or num_parts or p_off or any(b != 0 for b in d[0x18:size]):
            raise PlanError('null graphics table on a non-empty list')
        return zone, [], [], 0, 0, size
    g_end = g_off + 12 * num_models
    if p_off:
        # the bake serializer aligns the parts table after the graphics table;
        # the (zero) alignment gap is reproduced by the narrow inverse
        if not (g_end <= p_off < g_end + 16 and p_off % 4 == 0):
            raise PlanError('parts table misplaced: 0x%X vs graphics end 0x%X'
                            % (p_off, g_end))
        if any(b != 0 for b in d[g_end:p_off]):
            raise PlanError('non-zero bytes in the table alignment gap')
        content_end = p_off + 12 * num_parts
    else:
        if num_parts:
            raise PlanError('null parts table with %d parts' % num_parts)
        content_end = g_end
    if not (content_end <= size < content_end + 16) \
            or any(b != 0 for b in d[content_end:size]):
        # cross-validate the LE count read against the BE reading
        num_parts_be = struct.unpack_from('>I', d, 0x0C)[0]
        if p_off and p_off + 12 * num_parts_be == size:
            raise PlanError('part count is BE on this disk (%d) -- LE-bake '
                            'assumption violated' % num_parts_be)
        raise PlanError('part count %d inconsistent with size' % num_parts)
    graphics = []
    for i in range(num_models):
        t, model, parts = struct.unpack_from('>3I', d, g_off + 12 * i)
        if model != 0:
            raise PlanError('graphics %d: model slot not serialised-null' % i)
        if parts and not (p_off <= parts < size and (parts - p_off) % 12 == 0):
            raise PlanError('graphics %d: parts ptr 0x%X invalid' % (i, parts))
        graphics.append((t, parts))
    type_ids = set(t for t, _ in graphics)
    parts = []
    for i in range(num_parts):
        t, pid, model = struct.unpack_from('<3I', d, p_off + 12 * i)  # LE-baked
        if model != 0:
            raise PlanError('part %d: model slot not serialised-null' % i)
        if t not in type_ids or pid > 0xFF:
            raise PlanError('part %d: LE read {type 0x%X part %d} implausible '
                            '-- LE-bake assumption violated' % (i, t, pid))
        parts.append((t, pid))
    return zone, graphics, parts, g_off, p_off, size


def transcode_propgraphicslist(header_bytes, imports_yaml_text=None):
    d = header_bytes
    zone, graphics, parts, g_off, p_off, old_size = _parse_propgraphicslist(d)
    nm, np_ = len(graphics), len(parts)
    new_g_off = 0x20 if g_off else 0        # null tables stay null
    new_p_off = (new_g_off + 24 * nm) if p_off else 0
    new_size = 0x20 + 24 * nm + 16 * np_
    out = bytearray(new_size)
    struct.pack_into('<4I2Q', out, 0, new_size, zone, nm, np_,
                     new_g_off, new_p_off)
    for i, (t, pref) in enumerate(graphics):
        new_pref = new_p_off + 16 * ((pref - p_off) // 12) if pref else 0
        struct.pack_into('<I4xQQ', out, new_g_off + 24 * i, t, 0, new_pref)
    for i, (t, pid) in enumerate(parts):
        struct.pack_into('<IIQ', out, new_p_off + 16 * i, t, pid, 0)
    # imports: the serialised-null Model slots move to the widened +8 offsets
    new_imports = imports_yaml_text
    if imports_yaml_text is not None:
        remap = {}
        for i in range(nm):
            remap[g_off + 12 * i + 4] = new_g_off + 24 * i + 8
        for i in range(np_):
            remap[p_off + 12 * i + 8] = new_p_off + 16 * i + 8
        lines = []
        seen = 0
        for line in imports_yaml_text.splitlines():
            m = re.match(r'^(\s*-\s*)0x([0-9a-fA-F]+)(:\s*.*)$', line)
            if not m:
                if line.strip():
                    raise PlanError('unparsed imports line: %r' % line)
                continue
            old = int(m.group(2), 16)
            if old not in remap:
                raise PlanError('import offset 0x%X is not a model slot' % old)
            lines.append('%s0x%08x%s' % (m.group(1), remap[old], m.group(3)))
            seen += 1
        if seen != nm + np_:
            raise PlanError('import count %d != models+parts %d'
                            % (seen, nm + np_))
        new_imports = '\n'.join(lines) + '\n'
    if narrow_propgraphicslist(bytes(out), g_off, p_off, old_size) != d[:old_size]:
        raise PlanError('PropGraphicsList round-trip mismatch')
    verify_propgraphicslist_le(bytes(out))
    return bytes(out), new_imports


def narrow_propgraphicslist(x64_bytes, old_g_off, old_p_off, old_size):
    d = x64_bytes
    size, zone, nm, np_ = struct.unpack_from('<4I', d, 0)
    g_off, p_off = struct.unpack_from('<2Q', d, 0x10)
    out = bytearray(old_size)     # zero alignment gap / tail pad reproduced
    struct.pack_into('>2I', out, 0, old_size, zone)
    if old_g_off == 0:            # empty list: null-table header only
        return bytes(out)
    struct.pack_into('>I', out, 8, nm)
    struct.pack_into('<I', out, 0x0C, np_)               # LE-baked, reproduced
    struct.pack_into('>2I', out, 0x10, old_g_off, old_p_off)
    for i in range(nm):
        t = struct.unpack_from('<I', d, g_off + 24 * i)[0]
        pref = struct.unpack_from('<Q', d, g_off + 24 * i + 0x10)[0]
        old_pref = old_p_off + 12 * ((pref - p_off) // 16) if pref else 0
        struct.pack_into('>3I', out, old_g_off + 12 * i, t, 0, old_pref)
    for i in range(np_):
        t, pid = struct.unpack_from('<2I', d, p_off + 16 * i)
        struct.pack_into('<3I', out, old_p_off + 12 * i, t, pid, 0)  # LE-baked
    return bytes(out)


def verify_propgraphicslist_le(data):
    """Re-walk with the PC consumer logic: the PropGraphicsList::FixUp walk
    (rebase table ptrs + per-graphics mpParts, muSizeInBytes < 0x2800 assert)
    + the GetImportCount arithmetic."""
    size, zone, nm, np_ = struct.unpack_from('<4I', data, 0)
    g_off, p_off = struct.unpack_from('<2Q', data, 0x10)
    # the PC FixUp tripwire scales the X360 0x2800 bound by the worst-case
    # stride growth (24/12 = 2x) for the widened blob
    assert size == len(data) and size < 2 * 0x2800, 'muSizeInBytes (FixUp assert)'
    if g_off == 0:
        assert nm == 0 and np_ == 0 and p_off == 0, 'empty list'
        return
    if p_off:
        assert g_off + 24 * nm == p_off and p_off + 16 * np_ == size, 'tables'
    else:
        assert np_ == 0 and g_off + 24 * nm == size, 'graphics-only table'
    for i in range(nm):
        pref = struct.unpack_from('<Q', data, g_off + 24 * i + 0x10)[0]
        assert pref == 0 or (p_off <= pref < size and (pref - p_off) % 16 == 0), \
            'mpParts target'
    for i in range(np_):
        t, pid = struct.unpack_from('<2I', data, p_off + 16 * i)
        assert pid <= 0xFF, 'part id'


# ---- PropInstanceData (serialised PropZoneData) ---------------------------
PZD_X360_HEADER = 0x1C
PZD_X64_HEADER = 0x28
PZD_X360_INST_OFF = 0x20
PZD_X64_INST_OFF = 0x30          # 16-aligned (embedded Matrix44Affine rows)
PROP_INSTANCE_STRIDE = 80        # pointer-free record: does NOT widen
PROP_CELL_STRIDE = 12            # 6 u16 fields: does NOT widen


def _flip_prop_instance(out, d, src, dst):
    # Trailer widths are DWARF ground truth (BrnPhysicsPropInstanceData.h:160-170,
    # homed in b5-decomp as BrnPhysicsPropInstanceData.h) and agree with LoadProp
    # @0x822F2EF0's byte reads into PropEntityRotationParams:
    #   +0x40 u32 muTypeIdAndFlags   +0x44 u32 muInstanceID
    #   +0x48 u16 muAlternativeType  +0x4A i8 mn8RotSpeed
    #   +0x4B u8  mn8MaxAngle        +0x4C u8 mn8MinAngle   +0x4D u8[3] padding
    _u32_flip_range(out, d, src, src + 64, dst - src)          # 4x16 matrix
    out[dst + 64:dst + 68] = d[src + 64:src + 68][::-1]        # u32 muTypeIdAndFlags
    out[dst + 68:dst + 72] = d[src + 68:src + 72][::-1]        # u32 muInstanceID
    out[dst + 72:dst + 74] = d[src + 72:src + 74][::-1]        # u16 muAlternativeType
    out[dst + 74] = d[src + 74]                                # i8  mn8RotSpeed (anim bits)
    out[dst + 75] = d[src + 75]                                # u8  mn8MaxAngle
    # 0x4C..0x4F is NOT a u32.  It was flipped as one until 2026-08-12, which moved
    # mn8MinAngle to 0x4F and read a padding byte as the min angle.  Byte-granular,
    # so the flip stays involutive and both round-trip proofs still hold.  MEASURED
    # over all 396 shipped TRK_UNIT*_GR.BNDL (24,047 instances): mn8MinAngle,
    # mn8MaxAngle and the padding are zero in every retail record, so the old code
    # reversed four zero bytes and the emitted data was never actually wrong -- the
    # bug was latent, not live.  verify_propinstancedata_le now pins the padding.
    out[dst + 76] = d[src + 76]                                # u8  mn8MinAngle
    out[dst + 77:dst + 80] = d[src + 77:src + 80]              # u8[3] mau8Padding


def _parse_propzonedata_be(d):
    cells_off = be32(d, 0)
    num_cells = d[4]
    inst_off = be32(d, 8)
    size = be32(d, 0x0C)
    num_inst, num_props = be32(d, 0x10), be32(d, 0x14)
    zone = be16(d, 0x18)
    total = size + PZD_X360_HEADER
    if total > len(d):
        raise PlanError('PropZoneData header out of range')
    if inst_off == 0:
        # empty zone (TRK_UNIT0 et al): null tables, all-zero reserve
        if cells_off or num_cells or num_props or \
                any(b != 0 for b in d[PZD_X360_HEADER:total]):
            raise PlanError('null instance table on a non-empty zone')
        return 0, 0, num_inst, 0, zone, total, PZD_X360_HEADER
    if inst_off != PZD_X360_INST_OFF:
        raise PlanError('PropZoneData instance table @0x%X' % inst_off)
    if cells_off != inst_off + PROP_INSTANCE_STRIDE * num_props:
        raise PlanError('cell table 0x%X not after %d instance records'
                        % (cells_off, num_props))
    tail_off = cells_off + PROP_CELL_STRIDE * num_cells
    if tail_off > total:
        raise PlanError('cell table overruns the resource')
    if any(b != 0 for b in d[tail_off:total]):
        raise PlanError('reserved tail is not all-zero')
    count_sum = 0
    for i in range(num_cells):
        cx, cz, start, count, resp, dont = struct.unpack_from(
            '>6H', d, cells_off + PROP_CELL_STRIDE * i)
        if start != count_sum or resp + dont > count:
            raise PlanError('cell %d ranges inconsistent' % i)
        count_sum += count
    if count_sum != num_props:
        raise PlanError('cell counts %d != numProps %d' % (count_sum, num_props))
    return cells_off, num_cells, num_inst, num_props, zone, total, tail_off


def transcode_propinstancedata(header_bytes, imports_yaml_text=None):
    d = header_bytes
    (cells_off, num_cells, num_inst, num_props,
     zone, total, tail_off) = _parse_propzonedata_be(d)
    lb_empty = cells_off == 0                # null tables (empty zone)
    new_inst_off = 0 if lb_empty else PZD_X64_INST_OFF
    new_cells_off = 0 if lb_empty else \
        PZD_X64_INST_OFF + PROP_INSTANCE_STRIDE * num_props
    payload = (PZD_X64_INST_OFF if not lb_empty else PZD_X64_HEADER) \
        - PZD_X64_HEADER + PROP_INSTANCE_STRIDE * num_props \
        + PROP_CELL_STRIDE * num_cells + (total - tail_off)
    new_total = PZD_X64_HEADER + payload
    new_size = payload
    out = bytearray(new_total)
    struct.pack_into('<QB7xQ3IH', out, 0, new_cells_off, num_cells,
                     new_inst_off, new_size, num_inst, num_props, zone)
    for i in range(num_props):
        _flip_prop_instance(out, d,
                            PZD_X360_INST_OFF + PROP_INSTANCE_STRIDE * i,
                            PZD_X64_INST_OFF + PROP_INSTANCE_STRIDE * i)
    for o in range(0, PROP_CELL_STRIDE * num_cells, 2):
        out[new_cells_off + o:new_cells_off + o + 2] = \
            d[cells_off + o:cells_off + o + 2][::-1]
    if narrow_propinstancedata(bytes(out)) != d[:total]:
        raise PlanError('PropInstanceData round-trip mismatch')
    verify_propinstancedata_le(bytes(out))
    return bytes(out), imports_yaml_text


def narrow_propinstancedata(x64_bytes):
    d = x64_bytes
    cells_off, num_cells = struct.unpack_from('<QB', d, 0)
    inst_off, size, num_inst, num_props, zone = struct.unpack_from('<Q3IH', d, 0x10)
    if inst_off == 0:                 # empty zone: null tables, zero reserve
        old_total = PZD_X360_HEADER + size
        out = bytearray(old_total)
        struct.pack_into('>3I', out, 0x0C, size, num_inst, num_props)
        struct.pack_into('>H', out, 0x18, zone)
        return bytes(out)
    old_cells_off = PZD_X360_INST_OFF + PROP_INSTANCE_STRIDE * num_props
    tail_len = (size + PZD_X64_HEADER) - (cells_off + PROP_CELL_STRIDE * num_cells)
    old_total = old_cells_off + PROP_CELL_STRIDE * num_cells + tail_len
    out = bytearray(old_total)
    struct.pack_into('>I', out, 0, old_cells_off)
    out[4] = num_cells
    struct.pack_into('>2I', out, 8, PZD_X360_INST_OFF,
                     old_total - PZD_X360_HEADER)
    struct.pack_into('>2I', out, 0x10, num_inst, num_props)
    struct.pack_into('>H', out, 0x18, zone)
    for i in range(num_props):
        _flip_prop_instance(out, d,
                            PZD_X64_INST_OFF + PROP_INSTANCE_STRIDE * i,
                            PZD_X360_INST_OFF + PROP_INSTANCE_STRIDE * i)
    for o in range(0, PROP_CELL_STRIDE * num_cells, 2):
        out[old_cells_off + o:old_cells_off + o + 2] = \
            d[cells_off + o:cells_off + o + 2][::-1]
    return bytes(out)


def verify_propinstancedata_le(data):
    """Re-walk with the PC consumer logic (BrnPhysicsPropZoneData.h host
    layout + the LoadZone / LoadProp / GetRespawnTypeForProp reads)."""
    cells_off, num_cells = struct.unpack_from('<QB', data, 0)
    inst_off, size, num_inst, num_props, zone = struct.unpack_from('<Q3IH', data, 0x10)
    assert size + PZD_X64_HEADER == len(data)
    if inst_off == 0:
        assert cells_off == 0 and num_cells == 0 and num_props == 0, 'empty zone'
        return
    assert inst_off == PZD_X64_INST_OFF
    assert cells_off == inst_off + PROP_INSTANCE_STRIDE * num_props
    count_sum = 0
    for i in range(num_cells):
        cx, cz, start, count, resp, dont = struct.unpack_from(
            '<6H', data, cells_off + PROP_CELL_STRIDE * i)
        assert start == count_sum and resp + dont <= count, 'cell ranges'
        count_sum += count
    assert count_sum == num_props, 'cell counts'
    for i in range(num_props):
        rec = inst_off + PROP_INSTANCE_STRIDE * i
        assert struct.unpack_from('<f', data, rec + 60)[0] == 1.0, \
            'matrix W lane'    # rows are {x,y,z,pad}: translation w == 1.0
        type_id = le32(data, rec + 64) & 0x3FFFFFF
        assert type_id < 0x10000, 'prop type id'
        # mau8Padding @0x4D..0x4F must stay zero -- this is what a u32 flip over the
        # 0x4C..0x4F byte fields would break (it would park mn8MinAngle at 0x4F).
        assert data[rec + 77:rec + 80] == b'\0\0\0', 'mau8Padding must be zero'


# ---- StaticSoundMap -------------------------------------------------------
SSM_X360_HEADER = 0x40
SSM_X64_HEADER = 0x50
SSM_ENTITY_STRIDE = 16


def _flip_ssm_entity(out, d, src, dst):
    _u32_flip_range(out, d, src, src + 12, dst - src)          # f32 x, y, z
    out[dst + 12:dst + 14] = d[src + 12:src + 14][::-1]        # u16
    out[dst + 14:dst + 16] = d[src + 14:src + 16][::-1]        # u16


def _parse_staticsoundmap_be(d):
    sub_off = be32(d, 0x24)
    num_x, num_z = be32(d, 0x28), be32(d, 0x2C)
    ent_off = be32(d, 0x30)
    num_ent = be32(d, 0x34)
    root = be32(d, 0x38)
    if ent_off != SSM_X360_HEADER or sub_off != ent_off + SSM_ENTITY_STRIDE * num_ent:
        raise PlanError('StaticSoundMap layout: entities @0x%X grid @0x%X'
                        % (ent_off, sub_off))
    total = sub_off + 4 * num_x * num_z
    # degenerate maps exist (TRK_UNIT57: numZ == 0, one root entity, no grid)
    if total > len(d) or root > 1 or num_x < 0 or num_z < 0:
        raise PlanError('StaticSoundMap header out of range')
    count_sum = 0
    for i in range(num_x * num_z):
        first, count = struct.unpack_from('>2H', d, sub_off + 4 * i)
        if first == 0xFFFF:
            if count != 0:
                raise PlanError('empty cell %d has count %d' % (i, count))
        else:
            if first + count > num_ent:
                raise PlanError('cell %d range oob' % i)
            count_sum += count
    if num_x * num_z > 0 and count_sum != num_ent:
        raise PlanError('cell counts %d != numEntities %d' % (count_sum, num_ent))
    return sub_off, num_x, num_z, num_ent, root, total


def transcode_staticsoundmap(header_bytes, imports_yaml_text=None):
    d = header_bytes
    sub_off, num_x, num_z, num_ent, root, total = _parse_staticsoundmap_be(d)
    new_ent_off = SSM_X64_HEADER
    new_sub_off = new_ent_off + SSM_ENTITY_STRIDE * num_ent
    new_total = new_sub_off + 4 * num_x * num_z
    out = bytearray(new_total)
    _u32_flip_range(out, d, 0x00, 0x20)                  # mMin / mMax (4 lanes each)
    out[0x20:0x24] = d[0x20:0x24][::-1]                  # mfSubRegionSize
    struct.pack_into('<Q', out, 0x28, new_sub_off)       # mpSubRegions (u64)
    struct.pack_into('<2I', out, 0x30, num_x, num_z)
    struct.pack_into('<Q', out, 0x38, new_ent_off)       # mpEntities (u64)
    struct.pack_into('<2I', out, 0x40, num_ent, root)
    for i in range(num_ent):
        _flip_ssm_entity(out, d, SSM_X360_HEADER + SSM_ENTITY_STRIDE * i,
                         new_ent_off + SSM_ENTITY_STRIDE * i)
    for o in range(0, 4 * num_x * num_z, 2):
        out[new_sub_off + o:new_sub_off + o + 2] = \
            d[sub_off + o:sub_off + o + 2][::-1]
    if narrow_staticsoundmap(bytes(out)) != d[:total]:
        raise PlanError('StaticSoundMap round-trip mismatch')
    verify_staticsoundmap_le(bytes(out))
    return bytes(out), imports_yaml_text


def narrow_staticsoundmap(x64_bytes):
    d = x64_bytes
    sub_off = struct.unpack_from('<Q', d, 0x28)[0]
    num_x, num_z = struct.unpack_from('<2I', d, 0x30)
    num_ent, root = struct.unpack_from('<2I', d, 0x40)
    old_ent_off = SSM_X360_HEADER
    old_sub_off = old_ent_off + SSM_ENTITY_STRIDE * num_ent
    old_total = old_sub_off + 4 * num_x * num_z
    out = bytearray(old_total)
    _u32_flip_range(out, d, 0x00, 0x20)
    out[0x20:0x24] = d[0x20:0x24][::-1]
    struct.pack_into('>6I', out, 0x24, old_sub_off, num_x, num_z,
                     old_ent_off, num_ent, root)
    for i in range(num_ent):
        _flip_ssm_entity(out, d, SSM_X64_HEADER + SSM_ENTITY_STRIDE * i,
                         old_ent_off + SSM_ENTITY_STRIDE * i)
    for o in range(0, 4 * num_x * num_z, 2):
        out[old_sub_off + o:old_sub_off + o + 2] = \
            d[sub_off + o:sub_off + o + 2][::-1]
    return bytes(out)


def verify_staticsoundmap_le(data):
    """Re-walk with the committed PC consumer logic (StaticSoundMapResource-
    Type::FixUp relocation targets + the GetSubRegionDescrip grid maths)."""
    sub_off = struct.unpack_from('<Q', data, 0x28)[0]
    num_x, num_z = struct.unpack_from('<2i', data, 0x30)
    ent_off = struct.unpack_from('<Q', data, 0x38)[0]
    num_ent = struct.unpack_from('<i', data, 0x40)[0]
    assert ent_off == SSM_X64_HEADER, 'entity table offset'
    assert sub_off == ent_off + SSM_ENTITY_STRIDE * num_ent, 'grid offset'
    assert sub_off + 4 * num_x * num_z == len(data), 'grid extent'
    min_x = struct.unpack_from('<f', data, 0x00)[0]
    max_x = struct.unpack_from('<f', data, 0x10)[0]
    sub_size = struct.unpack_from('<f', data, 0x20)[0]
    assert sub_size > 0.0, 'sub-region size'
    # the grid must tile the [mMin, mMax) X extent (GetSubRegionDescrip maths);
    # degenerate grids (numZ == 0) have no cells to tile
    if num_x > 0 and num_z > 0:
        assert abs((max_x - min_x) - sub_size * num_x) < sub_size + 1e-3, \
            'grid does not tile the X extent'


# ---- PropPhysics (serialised PropPhysicsDataHeader) -----------------------
# PROPS/PROPPHYSICS.BUNDLE, resource 0xD75C5932, type 0x1000F.  ONE resource in
# the whole game: the prop TYPE table every prop spawn resolves through.
#
# Member set + declaration order are DWARF ground truth (DecFIGS
# SharedClasses/Physics/Props/BrnPropPhysicsDataHeader.h,
# BrnPhysicsPropTypeData.h, BrnPhysicsPropPartTypeData.h); the console offsets
# below are pinned by PropPhysicsDataHeader::FixUp @0x8267F570, whose three
# array bases are +0x10 / +0x7E0 / +0xC90 (which is what fixes the array bounds
# at 500 / 300 / 2048) and whose inner relocation slots are PropTypeData +0x3C,
# +0x40 and PropPartTypeData +0x24.  Verified against the shipped blob: every
# object tiles [arena, EOF) at exactly these strides.
PPH_MAX_PROP_TYPES = 500
PPH_MAX_PART_TYPES = 300
PPH_MAX_VOLUMES = 2048
#
# The x64 column is pinned on the C++ side by
# BrnPropPhysicsDataHeader.h::PropPhysicsDataHeader::_AssertLayout(): 0x10 + 500*8
# = 0xFB0, + 300*8 = 0x1910, + 2048*8 = 0x5910 (muTimeStamp), sizeof 0x5918.
PPH_X360_TYPES_AT, PPH_X64_TYPES_AT = 0x10, 0x10
PPH_X360_PARTS_AT, PPH_X64_PARTS_AT = 0x7E0, 0xFB0
PPH_X360_VOLS_AT, PPH_X64_VOLS_AT = 0xC90, 0x1910
# ...muTimeStamp is the last member, immediately after mapVolumeTypes.
PPH_X360_STAMP_AT, PPH_X64_STAMP_AT = 0x2C94 - 4, 0x5918 - 8
PPH_X360_HEADER, PPH_X64_HEADER = 0x2C94, 0x5918   # sizeof(PropPhysicsDataHeader)
PPH_ALIGN = 16                                     # the resource's bundle alignment
# PropTypeData: three alignas(16) Vector3, a u64 CgsResource::ID, then the two
# relocated pointers.  Widening mfMass's tail padding + the two pointers exactly
# consumes the console record's 15-byte tail pad, so the stride is unchanged.
PROP_TYPE_STRIDE = 112
PT_IN_VOLS, PT_OUT_VOLS = 0x3C, 0x40      # maCollisionVolumes  (FixUp slot 0)
PT_IN_PARTS, PT_OUT_PARTS = 0x40, 0x48    # maParts             (FixUp slot 1)
PT_IN_TAIL, PT_OUT_TAIL = 0x44, 0x50      # mfSphereRadius .. mu8ExtraTypeInfo
PT_TAIL_F32 = 5                           # sphereRadius, maxJointAngleCos,
#                                           leanThreshold, moveThreshold,
#                                           smashThreshold ... then muSceneUriId
PT_TAIL_U8 = 5                            # maxState, numParts, numVolumes,
#                                           jointType, extraTypeInfo
# PropPartTypeData: two alignas(16) Vector3, then mfMass + one relocated
# pointer.  48 -> 64 (the pointer widens and the record re-pads to 16).
PROP_PART_IN, PROP_PART_OUT = 48, 64
PP_IN_VOLS, PP_OUT_VOLS = 0x24, 0x28      # maCollisionVolumes  (FixUp slot)
# rw::collision::Volume: an opaque fixed 96-byte serialised record on BOTH
# platforms (b5-decomp models it as `u8 maPayload[96]` in volume.cpp,
# volume_debug_access.h and FixableVolume.h).  Every field is u32-granular --
# 4x4 transform lanes, the type slot, volumeData, radius, groupID, surfaceID,
# flags -- so it is a straight dword flip with no widening.  See the report note
# on FixableVolume::FixUp's 8-byte store at +0x40 if that ever changes.
PPH_VOLUME_STRIDE = 96
PPH_VOLUME_TYPE_AT = 0x40                 # on disk: the VOLUMETYPE enum (1..5)
PPH_VOLUME_FLAGS_AT = 0x5C                # rwcollision VOLUMEFLAG_ISENABLED


def _pph_align(value):
    return (value + PPH_ALIGN - 1) & ~(PPH_ALIGN - 1)


def _parse_propphysics_be(d):
    """Walk the X360 blob and prove it tiles exactly, returning the arena as an
    ordered ['T'|'P'|'V', console_offset] list plus the header scalars."""
    if len(d) < PPH_X360_HEADER:
        raise PlanError('PropPhysics blob is only %d bytes' % len(d))
    num_types, num_vols, num_parts = struct.unpack_from('>3I', d, 0)
    # muSizeInBytes is LITTLE-endian on the BE disk (ARTIST bake-tool anomaly,
    # the PropGraphicsList precedent).  Requiring it to equal the blob length is
    # what PROVES the LE reading rather than assuming it.
    size_le = struct.unpack_from('<I', d, 0x0C)[0]
    if size_le != len(d):
        size_be = struct.unpack_from('>I', d, 0x0C)[0]
        raise PlanError('muSizeInBytes LE %#x != blob %#x (BE reads %#x)'
                        % (size_le, len(d), size_be))
    stamp = be32(d, PPH_X360_STAMP_AT)
    if not (num_types <= PPH_MAX_PROP_TYPES and num_parts <= PPH_MAX_PART_TYPES
            and num_vols <= PPH_MAX_VOLUMES):
        raise PlanError('counts %d/%d/%d exceed the fixed array bounds'
                        % (num_types, num_vols, num_parts))
    tables = []
    for base, used, cap in ((PPH_X360_TYPES_AT, num_types, PPH_MAX_PROP_TYPES),
                            (PPH_X360_PARTS_AT, num_parts, PPH_MAX_PART_TYPES),
                            (PPH_X360_VOLS_AT, num_vols, PPH_MAX_VOLUMES)):
        slots = list(struct.unpack_from('>%dI' % cap, d, base))
        if any(slots[used:]):
            raise PlanError('unused slots in the table at %#x are not null' % base)
        tables.append(slots[:used])
    types, parts, vols = tables
    arena = _pph_align(PPH_X360_HEADER)
    if any(b != 0 for b in d[PPH_X360_HEADER:arena]):
        raise PlanError('header alignment pad is not zero')
    # every object must be inside the arena, distinct, and tile it exactly
    objects = []
    for kind, offs, stride in (('T', types, PROP_TYPE_STRIDE),
                               ('P', parts, PROP_PART_IN),
                               ('V', vols, PPH_VOLUME_STRIDE)):
        for off in offs:
            if not (arena <= off and off + stride <= len(d)) or off % PPH_ALIGN:
                raise PlanError('%s object at %#x is out of the arena' % (kind, off))
            objects.append((off, kind, stride))
    objects.sort()
    if len(set(o for o, _, _ in objects)) != len(objects):
        raise PlanError('two table slots point at the same object')
    cursor = arena
    for off, kind, stride in objects:
        if off != cursor:
            raise PlanError('arena gap: expected %s at %#x, found it at %#x'
                            % (kind, cursor, off))
        cursor += stride
    if cursor != len(d):
        raise PlanError('arena ends at %#x, blob is %#x' % (cursor, len(d)))
    # cross-validate the intra-record pointers against the object tables
    vol_set, part_set = set(vols), set(parts)
    for i, off in enumerate(types):
        cv, mp = struct.unpack_from('>2I', d, off + PT_IN_VOLS)
        n_parts, n_vols = d[off + 0x5D], d[off + 0x5E]
        _pph_check_run(vol_set, cv, n_vols, PPH_VOLUME_STRIDE,
                       'propType %d volumes' % i)
        if n_parts:
            _pph_check_run(part_set, mp, n_parts, PROP_PART_IN,
                           'propType %d parts' % i)
        elif mp in part_set:
            raise PlanError('propType %d has 0 parts but a live maParts' % i)
        if any(d[off + 0x61:off + PROP_TYPE_STRIDE]):
            raise PlanError('propType %d tail pad is not zero' % i)
    if sum(d[off + 0x5D] for off in types) != num_parts:
        raise PlanError('sum(muNumberOfParts) != muNumberOfPartTypes')
    for i, off in enumerate(parts):
        cv = be32(d, off + PP_IN_VOLS)
        _pph_check_run(vol_set, cv, d[off + 0x2C], PPH_VOLUME_STRIDE,
                       'partType %d volumes' % i)
        if any(d[off + 0x2D:off + PROP_PART_IN]):
            raise PlanError('partType %d tail pad is not zero' % i)
    for i, off in enumerate(vols):
        vtype = be32(d, off + PPH_VOLUME_TYPE_AT)
        if not 1 <= vtype <= 5:
            raise PlanError('volume %d type enum %d is outside FixableVolume\'s '
                            'supported 1..5' % (i, vtype))
    return num_types, num_vols, num_parts, stamp, types, parts, vols, objects


def _pph_check_run(known, base, count, stride, what):
    """The `count` records starting at `base` must all be table objects (the
    console consumers index a run off a single base pointer)."""
    if not count:
        return
    for k in range(count):
        if base + stride * k not in known:
            raise PlanError('%s: run of %d from %#x leaves the table at %d'
                            % (what, count, base, k))


def _pph_plan(objects):
    """old console offset -> (kind, new x64 offset), preserving arena ORDER."""
    out_strides = {'T': PROP_TYPE_STRIDE, 'P': PROP_PART_OUT,
                   'V': PPH_VOLUME_STRIDE}
    cursor = _pph_align(PPH_X64_HEADER)
    plan = {}
    for off, kind, _ in objects:
        plan[off] = (kind, cursor)
        cursor += out_strides[kind]
    return plan, cursor


def _pph_flip_volume(out, d, src, dst):
    """The 96-byte rwcollision record is entirely u32-granular."""
    _u32_flip_range(out, d, src, src + PPH_VOLUME_STRIDE, dst - src)


def transcode_propphysics(header_bytes, imports_yaml_text=None):
    d = header_bytes
    (num_types, num_vols, num_parts, stamp,
     types, parts, vols, objects) = _parse_propphysics_be(d)
    plan, new_total = _pph_plan(objects)
    out = bytearray(new_total)

    struct.pack_into('<4I', out, 0, num_types, num_vols, num_parts, new_total)
    struct.pack_into('<I', out, PPH_X64_STAMP_AT, stamp)
    for base, offs in ((PPH_X64_TYPES_AT, types), (PPH_X64_PARTS_AT, parts),
                       (PPH_X64_VOLS_AT, vols)):
        for i, off in enumerate(offs):
            struct.pack_into('<Q', out, base + 8 * i, plan[off][1])

    for off in types:
        dst = plan[off][1]
        _u32_flip_range(out, d, off, off + 0x30, dst - off)   # 3x Vector3 lanes
        struct.pack_into('<Q', out, dst + 0x30,
                         struct.unpack_from('>Q', d, off + 0x30)[0])  # ID (u64)
        out[dst + 0x38:dst + 0x3C] = d[off + 0x38:off + 0x3C][::-1]   # mfMass
        # maCollisionVolumes / maParts.  A prop type with muNumberOfParts == 0
        # carries the bake tool's uninitialised sentinel in maParts instead of a
        # table offset; FixUp rebases it unconditionally and nothing ever
        # dereferences it, so it is widened verbatim (zero-extended).
        cv, mp = struct.unpack_from('>2I', d, off + PT_IN_VOLS)
        struct.pack_into('<Q', out, dst + PT_OUT_VOLS, plan[cv][1])
        struct.pack_into('<Q', out, dst + PT_OUT_PARTS,
                         plan[mp][1] if mp in plan else mp)
        _u32_flip_range(out, d, off + PT_IN_TAIL,                     # 5 f32 +
                        off + PT_IN_TAIL + 4 * (PT_TAIL_F32 + 1),     # muSceneUriId
                        (dst - off) + (PT_OUT_TAIL - PT_IN_TAIL))
        out[dst + PT_OUT_TAIL + 4 * (PT_TAIL_F32 + 1):
            dst + PT_OUT_TAIL + 4 * (PT_TAIL_F32 + 1) + PT_TAIL_U8] = \
            d[off + 0x5C:off + 0x5C + PT_TAIL_U8]                     # 5 u8 fields

    for off in parts:
        dst = plan[off][1]
        _u32_flip_range(out, d, off, off + 0x24, dst - off)   # 2x Vector3 + mfMass
        struct.pack_into('<Q', out, dst + PP_OUT_VOLS,
                         plan[be32(d, off + PP_IN_VOLS)][1])
        out[dst + 0x30:dst + 0x34] = d[off + 0x28:off + 0x2C][::-1]   # mfSphereRadius
        out[dst + 0x34] = d[off + 0x2C]                               # muNumberOfVolumes

    for off in vols:
        _pph_flip_volume(out, d, off, plan[off][1])

    if narrow_propphysics(bytes(out)) != d:
        raise PlanError('PropPhysics round-trip mismatch')
    verify_propphysics_le(bytes(out))
    return bytes(out), imports_yaml_text


def narrow_propphysics(x64_bytes):
    """Inverse of transcode_propphysics (the round-trip proof).  The arena order
    is preserved by the widening, so the console offsets are recomputed by
    replaying the same walk at the console strides."""
    d = x64_bytes
    num_types, num_vols, num_parts = struct.unpack_from('<3I', d, 0)
    stamp = struct.unpack_from('<I', d, PPH_X64_STAMP_AT)[0]
    tables = []
    for base, used in ((PPH_X64_TYPES_AT, num_types),
                       (PPH_X64_PARTS_AT, num_parts),
                       (PPH_X64_VOLS_AT, num_vols)):
        tables.append(list(struct.unpack_from('<%dQ' % used, d, base)))
    types, parts, vols = tables
    kinds = {}
    for kind, offs in (('T', types), ('P', parts), ('V', vols)):
        for off in offs:
            kinds[off] = kind
    in_strides = {'T': PROP_TYPE_STRIDE, 'P': PROP_PART_IN,
                  'V': PPH_VOLUME_STRIDE}
    back, cursor = {}, _pph_align(PPH_X360_HEADER)
    for off in sorted(kinds):
        back[off] = cursor
        cursor += in_strides[kinds[off]]
    out = bytearray(cursor)
    struct.pack_into('>3I', out, 0, num_types, num_vols, num_parts)
    struct.pack_into('<I', out, 0x0C, cursor)          # LE-baked, reproduced
    struct.pack_into('>I', out, PPH_X360_STAMP_AT, stamp)
    for base, offs in ((PPH_X360_TYPES_AT, types), (PPH_X360_PARTS_AT, parts),
                       (PPH_X360_VOLS_AT, vols)):
        for i, off in enumerate(offs):
            struct.pack_into('>I', out, base + 4 * i, back[off])
    for off in types:
        dst = back[off]
        _u32_flip_range(out, d, off, off + 0x30, dst - off)
        struct.pack_into('>Q', out, dst + 0x30,
                         struct.unpack_from('<Q', d, off + 0x30)[0])
        out[dst + 0x38:dst + 0x3C] = d[off + 0x38:off + 0x3C][::-1]
        cv, mp = struct.unpack_from('<2Q', d, off + PT_OUT_VOLS)
        struct.pack_into('>I', out, dst + PT_IN_VOLS, back[cv])
        struct.pack_into('>I', out, dst + PT_IN_PARTS,
                         back[mp] if mp in back else mp)
        _u32_flip_range(out, d, off + PT_OUT_TAIL,
                        off + PT_OUT_TAIL + 4 * (PT_TAIL_F32 + 1),
                        (dst - off) + (PT_IN_TAIL - PT_OUT_TAIL))
        out[dst + 0x5C:dst + 0x5C + PT_TAIL_U8] = \
            d[off + PT_OUT_TAIL + 4 * (PT_TAIL_F32 + 1):
              off + PT_OUT_TAIL + 4 * (PT_TAIL_F32 + 1) + PT_TAIL_U8]
    for off in parts:
        dst = back[off]
        _u32_flip_range(out, d, off, off + 0x24, dst - off)
        struct.pack_into('>I', out, dst + PP_IN_VOLS,
                         back[struct.unpack_from('<Q', d, off + PP_OUT_VOLS)[0]])
        out[dst + 0x28:dst + 0x2C] = d[off + 0x30:off + 0x34][::-1]
        out[dst + 0x2C] = d[off + 0x34]
    for off in vols:
        _pph_flip_volume(out, d, off, back[off])
    return bytes(out)


def verify_propphysics_le(data):
    """Re-walk the widened blob with the committed PC consumer logic:
    PropPhysicsDataHeader::FixUp's three array walks + its inner relocation
    slots at the HOST offsets, GetType/GetPartType's bounds asserts, and
    FixableVolume::FixUp's 1..5 type-enum assert."""
    num_types, num_vols, num_parts, size = struct.unpack_from('<4I', data, 0)
    assert size == len(data), 'muSizeInBytes'
    assert num_types <= PPH_MAX_PROP_TYPES, 'GetType bound (KU_MAX_PROP_TYPES)'
    assert num_parts <= PPH_MAX_PART_TYPES, 'mapPropPartTypes bound'
    assert num_vols <= PPH_MAX_VOLUMES, 'KU_MAX_PROP_PHYSICS_VOLUMES bound'
    arena = _pph_align(PPH_X64_HEADER)
    types = list(struct.unpack_from('<%dQ' % num_types, data, PPH_X64_TYPES_AT))
    parts = list(struct.unpack_from('<%dQ' % num_parts, data, PPH_X64_PARTS_AT))
    vols = list(struct.unpack_from('<%dQ' % num_vols, data, PPH_X64_VOLS_AT))
    part_set, vol_set = set(parts), set(vols)
    for off in types + parts + vols:
        assert arena <= off < len(data) and off % PPH_ALIGN == 0, 'object oob'
    for i, off in enumerate(types):
        cv, mp = struct.unpack_from('<2Q', data, off + PT_OUT_VOLS)
        n_vols = data[off + 0x6A]
        n_parts = data[off + 0x69]
        for k in range(n_vols):
            assert cv + PPH_VOLUME_STRIDE * k in vol_set, 'type %d volume run' % i
        for k in range(n_parts):
            assert mp + PROP_PART_OUT * k in part_set, 'type %d part run' % i
        assert struct.unpack_from('<f', data, off + 0x50)[0] >= 0.0, 'sphere radius'
        assert -1.0009 <= struct.unpack_from('<f', data, off + 0x54)[0] <= 1.0009, \
            'mfMaxJointAngleCos is not a cosine'
    for i, off in enumerate(parts):
        cv = struct.unpack_from('<Q', data, off + PP_OUT_VOLS)[0]
        for k in range(data[off + 0x34]):
            assert cv + PPH_VOLUME_STRIDE * k in vol_set, 'part %d volume run' % i
    for i, off in enumerate(vols):
        vtype = struct.unpack_from('<I', data, off + PPH_VOLUME_TYPE_AT)[0]
        assert 1 <= vtype <= 5, 'volume %d FixableVolume type enum' % i
        assert struct.unpack_from('<I', data, off + PPH_VOLUME_FLAGS_AT)[0] == 1, \
            'volume %d VOLUMEFLAG_ISENABLED' % i


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
# widening rebuilds: transcode_* embeds its own round-trip proof + LE re-walk
WIDEN_TYPES = {
    'MaterialState': transcode_materialstate,
    'PropGraphicsList': transcode_propgraphicslist,
    'PropInstanceData': transcode_propinstancedata,
    'PropPhysics': transcode_propphysics,
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
    for tname, fn in sorted(WIDEN_TYPES.items()):
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
                # transcode_* runs the narrow_* round-trip proof + LE re-walk
                out, itext2 = fn(data, itext)
            except (PlanError, AssertionError, struct.error, IndexError) as e:
                print('  %s/%s: FAIL %s' % (tname, f, e))
                errs += 1
                continue
            ok += 1
            if not verify_only:
                with open(path, 'wb') as fh:
                    fh.write(out)
                if itext2 is not None and itext2 != itext:
                    with open(ipath, 'w') as fh:
                        fh.write(itext2)
        print('%-18s %s %d/%d files%s'
              % (tname, 'verified' if verify_only else 'widened', ok, len(files),
                 (' (%d FAILED)' % errs) if errs else ''))
        total_ok += ok
        if not verify_only and errs == 0 and files:
            with open(marker, 'w') as fh:
                fh.write('x360 -> x64 widening transcode complete\n')
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
