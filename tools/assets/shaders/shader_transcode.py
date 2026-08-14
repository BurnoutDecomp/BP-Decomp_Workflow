#!/usr/bin/env python3
"""Per-resource transcoders for SHADERS.BNDL (X360 platform-2 -> PC platform-4).

Two resource families live here (everything else in SHADERS.BNDL is handled by
the established tools/assets/bundles/world_type_transcode.py flippers):

  ShaderTechnique (type 0x32, id 50)
      Full structural big->little endian flip.  The committed PC consumer
      (b5-decomp/src/GameShared/GameClasses/Graphics/Resources/
      CgsShaderTechniqueResourceType.cpp FixUp @0x827EEB30) keeps the console
      32-bit layout and reads native-endian u32 words at the console byte
      offsets, so the platform-4 form is the identical layout with every
      32-bit word byteswapped (strings and the sampler-count byte stay raw).
      Layout authority: the nushaders repo (NUSHADERS_TUB in build.config.toml),
      Reference/ShaderTechnique_Xbox360.mediawiki + the committed FixUp code.

  ShaderProgramBuffer (type 0x12)
      Primary = 0x14-byte ProgramBufferData header (renderengine
      programbuffer.h) + platform shader header/microcode + descriptor table +
      interned names.  Secondary = the Xenos physical/constant block.
      Two modes:
        flip_program_buffer()   -- structural LE flip only.  The Xenos
                                   microcode is kept verbatim: the result is
                                   layout-valid for the PC loader but NOT
                                   consumable by D3D9.  Diagnostic mode.
        build_pc_program_buffer() -- replace the Xenos payload with D3D9
                                   SM3 bytecode (compiled from the TUB HLSL
                                   sources with fxc) and rebuild the
                                   descriptor table from the bytecode's CTAB.
      Container authority: the nushaders repo, Source/NuShaders.Formats/
      Xbox360/Xbox360ShaderProgramBuffer.cs (byte-validated round-trip
      packer) + b5-decomp .../states/programbuffer.h ProgramBufferData.
"""
import os
import struct
import sys

_BUNDLES = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        '..', 'bundles'))
if _BUNDLES not in sys.path:
    sys.path.insert(0, _BUNDLES)

from world_type_transcode import Plan, PlanError, be32, be16  # noqa: E402


def _cstring_end(data, off, what):
    end = data.find(b'\0', off)
    if end < 0:
        raise PlanError('%s: unterminated string @0x%X' % (what, off))
    return end + 1


# ---------------------------------------------------------------------------
# ShaderTechnique (type 0x32)
# ---------------------------------------------------------------------------
# Fixed 0x98-byte header (byte offsets per the burnout.wiki X360 layout, all
# confirmed against the committed CgsShaderTechniqueResourceType::FixUp):
#   +0x00 u32 vertex ShaderProgramBuffer import slot (0 in file)
#   +0x04 u32 pixel  ShaderProgramBuffer import slot (0 in file)
#   +0x08 ShaderConstantsInternal mInternalVertexShaderConstants   (5 words)
#   +0x1C ShaderConstantsExternal mExternalObjectVertexShaderConstants (4 words)
#   +0x2C ShaderConstantsExternal mExternalGlobalVertexShaderConstants (4 words)
#   +0x3C ShaderConstantsInternal mInternalPixelShaderConstants    (5 words)
#   +0x50 ShaderConstantsExternal mExternalObjectPixelShaderConstants  (4 words)
#   +0x60 ShaderConstantsExternal mExternalGlobalPixelShaderConstants  (4 words)
#   +0x70 ShaderConstantsCPU mCPUShaderConstants                   (4 words)
#   +0x80 ShaderConstantHashTable {keys ptr, names ptr, count}     (3 words)
#   +0x8C u32 mpaSamplers
#   +0x90 s8  miNumSamplers + 3 pad bytes  (RAW: the LE u32 read of the
#             unswapped bytes "NN 00 00 00" equals the count, which is what
#             both the FixUp u32 read and the sizer s8 read expect)
#   +0x94 u32 mpacName
#
# ShaderConstantsInternal: {count, sizes*, data**, hashes*, handles*}
#   sizes:   count entries of 4 bytes each; MEASURED as byte-value + 3 zero
#            bytes ("01 00 00 00" for size 1), i.e. already correct under the
#            PC's native LE u32 read -- kept RAW, validated (trailing bytes
#            must be zero), exactly like the +0x90 sampler-count quad.
#   data:    count u32 file-relative offsets, each to sizes[i] float4s
#            (16*sizes[i] bytes) of big-endian f32 payload (e.g. the
#            materialDiffuse default {1,1,1,1}) -- offsets and payload flipped.
#   hashes:  count u32 JAMCRC values
#   handles: count 4-byte renderengine::ProgramVariableHandle (four u8 fields
#            -- endian-neutral; the file carries writer garbage 88 01 BC 00,
#            overwritten at runtime bind).  MEASURED stride 4, not the 8-byte
#            runtime view on burnout.wiki: adjacent arrays sit exactly
#            count*4 apart.
# ShaderConstantsExternal: {count, data*, names**, handles*}
#   data:    count u32 words (runtime per-instance slots; zeros in file)
#   names:   count u32 file offsets to NUL strings
#   handles: count 4-byte ProgramVariableHandle (raw, as above)
# HashTable: keys = n u32, names = n u32 offsets to NUL strings.
# Sampler entries: 8 bytes {u32 name offset, s16 channel, u16 pad}; the pad
# carries writer garbage and is kept raw.

TECHNIQUE_HEADER_SIZE = 0x98

_INTERNAL_OFFS = (0x08, 0x3C)
_EXTERNAL_OFFS = (0x1C, 0x2C, 0x50, 0x60)


def _plan_handles(plan, data, off, count, what):
    # 4-byte serialized handles, four u8 fields: endian-neutral, kept raw.
    plan.raw(off, 4 * count, what + ' handles')


def _plan_string(plan, data, off, what):
    end = _cstring_end(data, off, what)
    plan.raw(off, end - off, what)


def plan_shader_technique(data):
    if len(data) < TECHNIQUE_HEADER_SIZE:
        raise PlanError('technique blob too small: %d' % len(data))
    plan = Plan(len(data))

    # Fixed header: every word is a u32 except the sampler-count byte quad.
    for off in range(0, TECHNIQUE_HEADER_SIZE, 4):
        if off == 0x90:
            plan.raw(off, 4, 'technique sampler count byte+pad')
        else:
            plan.u32(off, 'technique header word @0x%X' % off)

    # Internal constant blocks.
    for base in _INTERNAL_OFFS:
        count = be32(data, base)
        tag = 'internal@0x%X' % base
        if count > 64:
            raise PlanError('%s count %d implausible' % (tag, count))
        if count == 0:
            continue
        sizes, dataptr, hashes, handles = (be32(data, base + 4), be32(data, base + 8),
                                           be32(data, base + 12), be32(data, base + 16))
        for i in range(count):
            # size entry: leading byte + 3 zero bytes, LE-correct as-is.
            if data[sizes + 4 * i + 1:sizes + 4 * i + 4] != b'\0\0\0':
                raise PlanError('%s size[%d] bytes %s not byte+pad'
                                % (tag, i, data[sizes + 4 * i:sizes + 4 * i + 4].hex()))
            plan.raw(sizes + 4 * i, 4, tag + ' size byte quad')
            plan.u32(hashes + 4 * i, tag + ' hash')
            elem = be32(data, dataptr + 4 * i)
            plan.u32(dataptr + 4 * i, tag + ' data ptr')
            nwords = 4 * data[sizes + 4 * i]
            for k in range(nwords):
                plan.u32(elem + 4 * k, tag + ' f32 payload')
        _plan_handles(plan, data, handles, count, tag)

    # External constant blocks.
    for base in _EXTERNAL_OFFS:
        count = be32(data, base)
        tag = 'external@0x%X' % base
        if count > 64:
            raise PlanError('%s count %d implausible' % (tag, count))
        if count == 0:
            continue
        dataptr, names, handles = (be32(data, base + 4), be32(data, base + 8),
                                   be32(data, base + 12))
        for i in range(count):
            plan.u32(dataptr + 4 * i, tag + ' data word')
            noff = be32(data, names + 4 * i)
            plan.u32(names + 4 * i, tag + ' name ptr')
            if noff:
                _plan_string(plan, data, noff, tag + ' name')
        _plan_handles(plan, data, handles, count, tag)

    # CPU block (+0x70) -- observed zero in every SHADERS.BNDL technique; the
    # header words are already flipped above.  A non-zero count would need a
    # payload walk nobody has attested, so refuse it.
    if be32(data, 0x70) != 0:
        raise PlanError('CPU constant block non-empty (count=%d) -- unattested'
                        % be32(data, 0x70))

    # Constant hash table.
    n = be32(data, 0x88)
    if n > 64:
        raise PlanError('hash table count %d implausible' % n)
    keys, names = be32(data, 0x80), be32(data, 0x84)
    for i in range(n):
        plan.u32(keys + 4 * i, 'hash key')
        noff = be32(data, names + 4 * i)
        plan.u32(names + 4 * i, 'hash name ptr')
        if noff:
            _plan_string(plan, data, noff, 'hash name')

    # Sampler table.
    scount = data[0x90]
    if scount > 16:
        raise PlanError('sampler count %d implausible' % scount)
    sarr = be32(data, 0x8C)
    for i in range(scount):
        e = sarr + 8 * i
        plan.u32(e, 'sampler name ptr')
        plan.u16(e + 4, 'sampler channel')
        plan.raw(e + 6, 2, 'sampler pad (writer garbage)')
        noff = be32(data, e)
        if noff:
            _plan_string(plan, data, noff, 'sampler name')

    # Technique name.
    _plan_string(plan, data, be32(data, 0x94), 'technique name')

    plan.validate()
    return plan


def transcode_shader_technique(data, imports_yaml_text=None):
    """X360 -> platform-4: structural LE flip, byte count preserved."""
    plan = plan_shader_technique(data)
    return plan.apply(data), imports_yaml_text


def technique_name(data):
    off = be32(data, 0x94)
    return data[off:data.index(b'\0', off)].decode('ascii')


def technique_sampler_names(data):
    scount = data[0x90]
    sarr = be32(data, 0x8C)
    out = []
    for i in range(scount):
        noff = be32(data, sarr + 8 * i)
        chan = struct.unpack_from('>h', data, sarr + 8 * i + 4)[0]
        out.append((data[noff:data.index(b'\0', noff)].decode('ascii'), chan))
    return out


# ---------------------------------------------------------------------------
# ShaderProgramBuffer (type 0x12)
# ---------------------------------------------------------------------------
# ProgramBufferData header (0x14 bytes, renderengine programbuffer.h):
#   +0x00 u32 muShaderType      (0 = vertex, 1 = pixel)
#   +0x04 u16 mu16NumVariables
#   +0x06 u16 mu16Pad6          (bytes 01 00 in every X360 primary; kept RAW so
#                                the LE u16 read is 1, mirroring the technique
#                                sampler-count convention)
#   +0x08 u32 muMicrocodeSize   (== bytes between +0x14 and the descriptor
#                                table: X360 = D3D shader header (40 PS /
#                                872 VS) + Xenos ucode)
#   +0x0C u32 muMicrocodePart3  (secondary/physical block size)
#   +0x10 u32 muPhysicalPart    (0 in file; relocated at load)
#   +0x14 payload, then mu16NumVariables * 8-byte ProgramVariableDescriptor
#         {u32 name file-offset, u8, u8, u8, u8}, then NUL name strings.

PB_HEADER_SIZE = 0x14


def plan_program_buffer_primary(data):
    if len(data) < PB_HEADER_SIZE:
        raise PlanError('program buffer primary too small: %d' % len(data))
    plan = Plan(len(data))
    plan.u32(0x00, 'pb shader type')
    plan.u16(0x04, 'pb num variables')
    plan.raw(0x06, 2, 'pb pad6 bytes')
    plan.u32(0x08, 'pb microcode size')
    plan.u32(0x0C, 'pb part3 size')
    plan.u32(0x10, 'pb physical ptr')
    shader_type = be32(data, 0x00)
    if shader_type not in (0, 1):
        raise PlanError('pb shader type %d invalid' % shader_type)
    nvars = be16(data, 0x04)
    ucode = be32(data, 0x08)
    desc = PB_HEADER_SIZE + ucode
    if desc + 8 * nvars > len(data):
        raise PlanError('pb descriptor table [0x%X+%d*8] beyond blob 0x%X'
                        % (desc, nvars, len(data)))
    # Payload (D3D header + Xenos microcode) stays raw.
    plan.raw(PB_HEADER_SIZE, ucode, 'pb platform payload')
    for i in range(nvars):
        e = desc + 8 * i
        plan.u32(e, 'pb descriptor name offset')
        plan.raw(e + 4, 4, 'pb descriptor bytes')
        noff = be32(data, e)
        if noff:
            _plan_string(plan, data, noff, 'pb variable name')
    plan.validate()
    return plan


def flip_program_buffer(primary, secondary):
    """Structural LE flip.  Keeps the Xenos payload -- NOT D3D9-consumable."""
    plan = plan_program_buffer_primary(primary)
    return plan.apply(primary), secondary


def program_buffer_variables(primary):
    """[(name, b4, b5, b6)] from an X360 (BE) primary's descriptor table."""
    nvars = be16(primary, 0x04)
    desc = PB_HEADER_SIZE + be32(primary, 0x08)
    out = []
    for i in range(nvars):
        e = desc + 8 * i
        noff = be32(primary, e)
        name = primary[noff:primary.index(b'\0', noff)].decode('ascii')
        out.append((name, primary[e + 4], primary[e + 5], primary[e + 6]))
    return out


# ---------------------------------------------------------------------------
# D3D9 bytecode CTAB -> PC ShaderProgramBuffer
# ---------------------------------------------------------------------------

def parse_ctab(bytecode):
    """Parse the CTAB comment of D3D9 SM2/SM3 bytecode.

    Returns [(name, register_set, register_index, register_count)] where
    register_set is the D3DXREGISTER_SET enum (0 BOOL, 1 INT4, 2 FLOAT4,
    3 SAMPLER)."""
    out = []
    i = 4
    while i + 4 <= len(bytecode):
        tok = struct.unpack_from('<I', bytecode, i)[0]
        if tok == 0x0000FFFF or tok == 0x0000FFFE:   # end token
            break
        if (tok & 0xFFFF) == 0xFFFE:                 # comment block
            length = (tok >> 16) & 0x7FFF
            block = bytecode[i + 4:i + 4 + length * 4]
            if block[:4] == b'CTAB':
                c = block[4:]
                (_size, _creator, _ver, nconst,
                 cinfo, _flags, _target) = struct.unpack_from('<7I', c, 0)
                for k in range(nconst):
                    (name_off, regset, regidx, regcnt, _rsvd,
                     _type_off, _def_off) = struct.unpack_from('<IHHHHII',
                                                               c, cinfo + 20 * k)
                    name = c[name_off:c.index(b'\0', name_off)].decode('ascii')
                    out.append((name, regset, regidx, regcnt))
            i += 4 + length * 4
        else:
            i += 4
    return sorted(out)


def build_pc_program_buffer(bytecode, shader_type):
    """Build a platform-4 (LE) ShaderProgramBuffer primary around D3D9 bytecode.

    Contract (see FORMAT_MAP.md section 5):
      muShaderType     = 0 vertex / 1 pixel
      muMicrocodeSize  = len(bytecode); the D3D9 blob sits directly at +0x14,
                         so the committed consumer's descriptor-table walk
                         (data + muMicrocodeSize + 0x14) and the PC
                         XGRegister*Shader shim (CreateVertexShader(data+0x14))
                         both work unchanged.
      muMicrocodePart3 = 0 (no Xenos physical block; slot2 of the serialised
                         descriptor sizes to zero)
      descriptor bytes = {+4 register index, +5 data type (0 bool, 2 float4,
                         3 sampler), +6 register count, +7 0}.  This is the
                         MEASURED X360 semantics (retail SHADERS.BNDL
                         descriptors decode this way; nushaders' byte-validated
                         PackGenerate writes the same) -- note the b5
                         ProgramVariableDescriptor field NAMES at +4/+5
                         (mu8RegisterSet/mu8RegisterIndex) are misleading;
                         see FORMAT_MAP.md section 4.
    Returns (primary, secondary) with a 16-byte zero secondary placeholder.
    """
    if shader_type not in (0, 1):
        raise ValueError('shader_type must be 0 (VS) or 1 (PS)')
    if len(bytecode) % 4 != 0:
        raise ValueError('D3D9 bytecode length not dword-aligned')
    variables = parse_ctab(bytecode)

    desc_off = PB_HEADER_SIZE + len(bytecode)
    names_off = desc_off + 8 * len(variables)
    names = bytearray()
    name_offsets = []
    for name, _rs, _ri, _rc in variables:
        name_offsets.append(names_off + len(names))
        names += name.encode('ascii') + b'\0'
    while len(names) % 16:
        names += b'\0'

    out = bytearray()
    out += struct.pack('<I', shader_type)
    out += struct.pack('<H', len(variables))
    out += b'\x01\x00'                       # pad6 bytes, LE u16 == 1
    out += struct.pack('<I', len(bytecode))  # muMicrocodeSize
    out += struct.pack('<I', 0)              # muMicrocodePart3: no secondary
    out += struct.pack('<I', 0)              # muPhysicalPart
    out += bytecode
    # CTAB D3DXREGISTER_SET -> container data-type byte: BOOL(0)->0,
    # INT4(1)->2 (dispatched as float4), FLOAT4(2)->2, SAMPLER(3)->3.
    type_map = {0: 0, 1: 2, 2: 2, 3: 3}
    for (name, regset, regidx, regcnt), noff in zip(variables, name_offsets):
        if regidx > 0xFF or regcnt > 0xFF:
            raise ValueError('constant %s registers out of u8 range '
                             '(set=%d idx=%d cnt=%d)' % (name, regset, regidx, regcnt))
        out += struct.pack('<IBBBB', noff, regidx, type_map[regset], regcnt, 0)
    out += names
    while len(out) % 16:
        out += b'\0'
    return bytes(out), b'\0' * 16
