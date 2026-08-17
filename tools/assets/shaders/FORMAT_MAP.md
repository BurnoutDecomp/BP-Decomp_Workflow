# SHADERS.BNDL format map: X360 (platform 2) -> PC platform 4

Slice deliverable for the world-render campaign shader data path (2026-07-27).
Everything below is measured against `build/game/SHADERS.BNDL` (bnd2 platform 2
big-endian, 344 resources), the committed b5 consumers, and the nushaders
toolchain (a separate repo; `NUSHADERS_TUB` in build.config.toml points at its
TUB tree), which is the authority on the container formats.

Companion files:

- `shader_transcode.py` -- per-resource transcoders (validated, round-trip-proven)
- `convert_shaders_bundle.py` -- whole-bundle driver (`inventory` / `convert`)
- `fallback_world.fx` -- minimal bring-up shader (see `MINIMAL_PATH.md`)
- `recovered/*.fx` -- shaders decoded from the X360 microcode for techniques the
  TUB tree lacks (Godray); always searched before the TUB tree
- `xenos.py` -- Xenos microcode disassembler, ground-truth-validated (see
  section 8)
- `ctab.py` -- big-endian CTAB reader (register-pinned uniform names for the
  shader `xenos.py` disassembles)
- converted output: `tools/assets/shaders/out/SHADERS_PC.BNDL` (do NOT stage
  into `build/game/` from this slice; hand over to the build owner)

## 1. Bundle inventory (X360 SHADERS.BNDL)

| type id | YAP folder          | count | notes                                                   |
|---------|---------------------|-------|---------------------------------------------------------|
| 0x32    | ShaderTechnique     | 110   | one per (fx file x technique); imports VS+PS 0x12       |
| 0x12    | ShaderProgramBuffer | 220   | 110 VS + 110 PS; split primary(`_header`)/secondary(`_body`), secondaryMemoryType 1 |
| 0x1     | Material            | 2     | default materials                                       |
| 0xf     | MaterialState       | 3     |                                                         |
| 0xd     | MaterialTechnique   | 5     |                                                         |
| 0x0     | Texture             | 2     | split header/body                                       |
| 0xe     | TextureState        | 2     |                                                         |

Technique names = `<fx base name>_<fx technique>` (e.g.
`Diffuse_Opaque_Singlesided_Default`) plus standalone shared Z-prepass
techniques (`ZOnlyOpaqueSingleSided`, ...). Full name list:
`py convert_shaders_bundle.py inventory build/game/SHADERS.BNDL`.

## 2. What the committed PC engine expects (real vs stub)

The b5 engine's shader path is the **console twin-type** (ShaderTechnique id 50
+ ShaderProgramBuffer), NOT the retail-TUB `Shader` resource type. Status of
each consumer:

- `b5-decomp/src/GameShared/GameClasses/Graphics/Resources/CgsShaderTechniqueResourceType.{h,cpp}`
  -- **REAL** (reconstructed from X360 ARTIST). `GetTypeID`(=50),
  `GetImportPointer` (VS import @ +0, PS import @ +4), `FixUp` @0x827EEB30
  (relocates the six constant sub-blocks at +8/+28/+44/+60/+80/+96, hash table
  @ +128, sampler table via +140/+144, name @ +148),
  `GetSerialisedResourceDescriptor` @0x827F7A68 and the two sub-sizers.
  **`PostFixUp` @0x827EEBF0 is DECLARED-ONLY (deferred)**: the shader-profile
  strstr classification against un-recovered rodata tables plus 4 calls to
  unidentified `sub_827ED8D0`. Note: the FixUp comment calls +148 the
  "sampler-state-block pointer", but +148 is the technique **name** pointer
  (`mpacName` on burnout.wiki; `GetSerialisedResourceDescriptor` strlens it).
- `b5-decomp/src/GameShared/GameClasses/Graphics/CgsShaderConstants.{h,cpp}` --
  **REAL**. `ShaderConstantsExternal::FixUp(u8*)` rebases data/names/handles
  pointers + each name; `Internal::FixUp(u8*)` rebases 4 pointers + each data
  element; `CgsShaderConstantHashTable.cpp FixUp` @0x827E9B20 rebases
  keys/names + each name.
- `b5-decomp/src/GameShared/GameClasses/RenderWare/x360/materialstates/CgsRwShaderProgramBufferResourceTypeX360.cpp`
  -- **REAL** (`GetSerialisedResourceDescriptor` @0x828A9910, `ReBase`
  @0x828A8E90). ReBase calls `XGRegisterVertexShader`/`XGRegisterPixelShader`
  which are **declared-not-defined externs on PC** (programbuffer.h) -- the
  engine agent must supply PC shims (section 6).
- `b5-decomp/src/SDKs/RenderEngineClub/MAIN/components/src/states/programbuffer.{h,cpp}`
  -- **REAL** X360 layout (`ProgramBufferData`, `ProgramVariableDescriptor`,
  `GetVariableHandleByName`); `Initialize` copies XG microcode parts (X360
  path; PC shims needed).
- `b5-decomp/src/pc/gcm/renderengine/VertexProgramState.{h,cpp}` -- **REAL but
  minimal**: `GetD3DVertexShader` returns `&mpVertexProgram->mauD3DVertexShader`
  = **ProgramBufferData + 0x14** (the payload!), and
  `shadowingdevice.cpp:279` passes that straight to
  `D3DDevice_SetVertexShader` (extern, no PC definition yet). This fixes the
  payload contract: whatever sits at +0x14 is what the PC set-shader shim
  receives.

### The x64 seam (engine-side open item)

`CgsShaderTechniqueResourceType::FixUp` reads the blob with **raw 32-bit
offsets/u32 slots** (console layout), but then placement-casts
`blob+8/28/...` to `ShaderConstantsInternal*/External*` whose x64 member
layout has 8-byte pointers (External is 32 bytes on x64 vs 16 on disk). The
two views cannot both be right on x64. The platform-4 data (this slice)
keeps the **32-bit console layout, byteswapped** -- same convention as every
other converted world type (InstanceList/Material/MaterialTechnique/... in
`tools/assets/bundles/world_type_transcode.py` all keep u32 slots). The
engine agent must make the sub-block FixUps read u32 slots at the console
offsets (as the resource-type FixUp already does), not widen the data.

## 3. ShaderTechnique blob (type 0x32) -- layout and per-field mapping

32-bit console layout (authority: the nushaders repo's
`Reference\ShaderTechnique_Xbox360.mediawiki`, byte-for-
byte confirmed against the committed FixUp and against the retail blobs).
Fixed 0x98-byte header:

| offset | field                                      | X360 -> PC transform |
|--------|--------------------------------------------|----------------------|
| 0x00   | vertex ShaderProgramBuffer import slot     | u32 flip (0 in file; loader writes id via imports sidecar offset 0x0) |
| 0x04   | pixel ShaderProgramBuffer import slot      | u32 flip (imports sidecar offset 0x4) |
| 0x08   | ShaderConstantsInternal (vertex), 5 words  | u32 flip each        |
| 0x1C   | ShaderConstantsExternal (object VS), 4 wds | u32 flip each        |
| 0x2C   | ShaderConstantsExternal (global VS)        | u32 flip each        |
| 0x3C   | ShaderConstantsInternal (pixel)            | u32 flip each        |
| 0x50   | ShaderConstantsExternal (object PS)        | u32 flip each        |
| 0x60   | ShaderConstantsExternal (global PS)        | u32 flip each        |
| 0x70   | ShaderConstantsCPU, 4 words                | u32 flip (count 0 in every retail blob; non-zero refused) |
| 0x80   | hash table {keys*, names*, count}          | u32 flip each        |
| 0x8C   | sampler array pointer                      | u32 flip             |
| 0x90   | s8 sampler count + 3 pad bytes             | **RAW** (`NN 00 00 00`; LE u32 read == count already) |
| 0x94   | technique name char*                       | u32 flip             |

Tail regions (all pointers are file-relative offsets, turned absolute by the
committed FixUps at load):

- **Internal block** `{count, sizes*, data**, hashes*, handles*}`:
  - sizes: count x 4 bytes, **measured as byte + 3 zero bytes** (`01 00 00 00`
    for one float4) -> **RAW** (LE-correct as-is). NB the committed
    `GetSerialisedResourceDescriptor` reads these as u32 -- correct under LE,
    nonsensical under BE, i.e. this quad was byte+pad all along.
  - data: count u32 offsets -> flip; each points to `sizes[i]` float4s of BE
    f32 payload (e.g. materialDiffuse default {1,1,1,1}) -> flip each u32 lane.
  - hashes: count u32 JAMCRC -> flip.
  - handles: count x **4-byte** `renderengine::ProgramVariableHandle` (four u8
    fields, endian-neutral, writer garbage `88 01 BC 00` / `04 02 BC 04` in
    file, rebound at runtime) -> RAW. **Measured stride 4**, not the 8-byte
    runtime view on burnout.wiki (adjacent arrays sit exactly count*4 apart).
- **External block** `{count, data*, names**, handles*}`: data = count u32
  runtime slots (zeros) -> flip; names = count u32 offsets -> flip, strings
  RAW; handles as above.
- **Hash table**: keys n x u32 -> flip; names n x u32 offsets -> flip;
  strings RAW.
- **Samplers**: 8-byte entries `{u32 name offset -> flip, s16 channel -> flip,
  u16 pad (writer garbage) -> RAW}`. Channels are D3D sampler registers
  (measured: DiffuseTextureSampler=0, shadowMapSamplerHighDetail=15 ==
  the compiled shaders' s0/s15).
- **Strings**: RAW.

`shader_transcode.transcode_shader_technique()` implements exactly this walk
with full-coverage validation; **all 110 retail techniques flip and round-trip
byte-exactly**.

## 4. ShaderProgramBuffer (type 0x12) -- X360 layout

Authority: the nushaders repo's `Source\NuShaders.Formats\Xbox360\
Xbox360ShaderProgramBuffer.cs` (byte-validated packer) +
`programbuffer.h ProgramBufferData`. Primary (`_header.dat`):

| offset | field              | meaning (X360)                                     |
|--------|--------------------|-----------------------------------------------------|
| 0x00   | u32 muShaderType   | 0 = vertex, 1 = pixel                               |
| 0x04   | u16 numVariables   | descriptor-table entry count                        |
| 0x06   | bytes `01 00`      | pad6 (LE u16 read == 1); RAW                        |
| 0x08   | u32 muMicrocodeSize| bytes between +0x14 and the descriptor table = D3D shader header (40 PS / 872 VS) + Xenos ucode |
| 0x0C   | u32 muMicrocodePart3 | secondary (physical/const) block size             |
| 0x10   | u32 muPhysicalPart | 0 in file, relocated at load                        |
| 0x14   | payload            | XGSet*ShaderHeader block + Xenos microcode          |
| +0x14+ucodeSize | descriptor table | numVariables x 8: `{u32 name file-offset, u8 register index, u8 data type (0 bool / 2 float4 / 3 sampler), u8 register count, u8 0}` |
| after  | NUL name strings, 16-padded                                             |

Secondary (`_body.dat`) = the Xenos physical/constant tail (GPU memory,
`secondaryMemoryType 1`).

**Descriptor byte semantics warning**: the retail data decodes as
+4 = register INDEX, +5 = data TYPE (measured: `DiffuseTextureSampler
reg 0 type 3`, `KeyLightColour reg 5 type 2`; nushaders' validated packer
writes the same). The b5 `ProgramVariableDescriptor` names these
`mu8RegisterSet` (+4) / `mu8RegisterIndex` (+5) -- the NAMES are misleading;
the bytes at +4 are what `SetVertexShaderConstantF` needs as the register
number. `GetVariableHandleByName` copies +4 -> handle+0, +5 -> handle+1,
shaderType -> handle+2, +6 -> handle+3 regardless, so data and code stay
consistent as long as dispatch treats handle+0 as the register index.

## 5. PC platform-4 target

**ShaderTechnique**: identical layout, LE (section 3). No widening.

**ShaderProgramBuffer**: same 0x14 header + descriptor-table shape, LE, with
the payload replaced:

| field            | PC value                                              |
|------------------|-------------------------------------------------------|
| muShaderType     | 0 VS / 1 PS (unchanged)                               |
| numVariables     | rebuilt from the D3D9 bytecode CTAB                   |
| muMicrocodeSize  | **len(D3D9 bytecode)** -- the SM3 blob sits directly at +0x14 with no console D3D header, so the committed descriptor-table walk (`data + muMicrocodeSize + 0x14`) and `VertexProgramState::GetD3DVertexShader` (`data + 0x14`) both work unchanged |
| muMicrocodePart3 | 0 -- no Xenos physical block (serialised-descriptor slot2 sizes to zero); `_body.dat` written as 16 zero bytes to keep the bundle shape |
| descriptor bytes | `{name file-offset, register index, type (CTAB D3DXRS: BOOL->0, INT4->2, FLOAT4->2, SAMPLER->3), register count, 0}` |

Bytecode source: the TUB HLSL (`{NUSHADERS_TUB}\Shaders\*.fx` + `..\Include\`,
where `NUSHADERS_TUB` = the nushaders repo's
`Reference\TUB\Bundle\gamedb\burnout5`), compiled with the plain
Windows-SDK `fxc.exe` as raw `vs_3_0`/`ps_3_0` (NOT the fx_2_0 effect profile
-- the engine wants bare shader blobs). **Verified equivalence**: compiling
`Diffuse_Opaque_Singlesided.fx` `VS_Main`/`PS_Main` yields a CTAB whose
constants match the X360 technique's constant blocks name-for-name (world;
IrradianceQuadricA/B, KeyLightDirection, ScattCoeffs, ShadowMap_WorldToLight,
ViewPosition, ViewProjectionModified; FogColourPlusWhiteLevel, KeyLightColour,
ShadowMap_Constants/2; hash-keyed materialDiffuse; samplers s0/s15 == the
technique's sampler channels). One benign delta: the recompiled VS also
declares `ShadowMap_Constants2`, which the technique never dispatches.

Technique -> HLSL mapping (in `convert_shaders_bundle.py`):

- `<FxBase>_<Technique>` -> `<FxBase>.fx`, that technique's
  `compile vs_3_0 <entry>` / `ps_3_0 <entry>` entries;
- standalone `ZOnly*` -> any fx defining that technique (identical bodies);
- `ZOnly*Instanced` -> the `*_Instanced.fx` files (their ZOnly techniques keep
  the un-suffixed name but use instanced vertex fetch);
- coverage: **108/110** from the TUB tree; `Godray_Additive_Doublesided_Default`
  has no TUB source and is now served by `recovered/Godray_Additive_Doublesided.fx`
  (decoded from the X360 microcode, see section 9); only
  `CarStudio_DoNotShipWithThisInTheGame_Default` (dev-only) still needs
  `--fallback` -> `fallback_world.fx`.  `recovered/` is always searched first.
- constant contract: after compiling, every technique's INTERNAL and EXTERNAL
  constant names are checked against the CTAB of the program it imports
  (`check_constant_contract`; `check <x360> <pc>` re-runs it on a staged bundle).
  An internal miss is a hard error -- it is the runtime assert
  `PostFixUpShaderConstants: "Tyring to postfixup a constant not present in the
  programbuffer"`; an external miss is a warning (the runtime "Missing shader
  constant from table" log line, today the 19 `*_Instanced` techniques'
  `InstancingIndexArray`/`InstancingMatrixArray`, a TUB instanced-source gap).

Other types: `Material`/`MaterialState`/`MaterialTechnique`/`TextureState` via
the boot-proven `world_type_transcode` flippers; `Texture` via the Volatility
PortTexture flow (both reused from `convert_world_bundle.py`). Bundle meta:
platform 2 -> 4, `compressed: false`, plus the YAP `_imports.yaml` sidecar
rename fix (without it `YAP c` silently drops every import).

## 6. Engine-side contract (for the engine agent)

The converted data assumes these PC shims (none exist yet -- the XG*/
D3DDevice_* symbols are honest externs today):

1. `XGRegisterVertexShader(pShader, physical)` / `XGRegisterPixelShader` (called
   from `CgsRwShaderProgramBufferResourceType::ReBase` with
   `pShader = ProgramBufferData + 0x14`): create the D3D9 shader from the
   SM3 bytecode at that address (`IDirect3DDevice9::CreateVertexShader/
   CreatePixelShader((const DWORD*)pShader)`) and remember the created object
   for that buffer; `physical` is meaningless on PC (muPhysicalPart == 0).
2. `D3DDevice_SetVertexShader` / `D3DDevice_SetPixelShader`
   (shadowingdevice.cpp): bind the object created in (1). Note the flush
   passes `GetD3DVertexShader()` == `ProgramBufferData + 0x14`, so the shim
   needs the payload-address -> shader-object mapping from (1) (or lazy
   creation at first bind).
3. Constant dispatch (`ShaderConstantsExternal/Internal::Dispatch*`): handle
   byte 0 = register index, byte 1 = data type (0/2/3), byte 3 = register
   count; float4 -> `Set*ShaderConstantF`, sampler -> the sampler stage,
   bool -> `Set*ShaderConstantB`.
4. `ProgramBuffer::Initialize`/`GetResourceDescriptor` X360 microcode paths
   (XGGetMicrocodeShaderParts etc.) are only used for runtime-created
   programs (post-fx); the streamed SHADERS.BNDL path goes through
   FixUp/ReBase and does not need them for world bring-up.
5. `ShaderTechniqueResourceType::PostFixUp` is deferred; if the world path
   turns out to require the profile code written into the name head, a
   minimal PC version can classify by technique-name substring
   (`Vehicle`/`World`/...) -- flag it when hit, don't guess silently.

## 7. Open questions

- **PVH descriptor naming** (section 4): b5 field names vs measured byte
  semantics -- needs a one-line comment fix engine-side, or an X360
  dispatch-asm recheck (`work show` the Dispatch*ShaderConstants TUs).
- **x64 sub-block FixUp seam** (section 2): External/Internal/HashTable FixUp
  bodies use x64-width member layouts over 32-bit blob data; must be
  raw-u32-slot rewrites to actually run.
- **Secondary body for PC**: written as 16 zero bytes with muMicrocodePart3=0.
  If the PC loader path objects to a graphics-memory body entry, drop
  `secondaryMemoryType` from the meta instead (untested either way -- needs
  the first boot-test with a world drive).
- **VS variant defines**: compiled with no defines ("base"). The X360 blobs
  may correspond to a defined variant (D_MRT etc. -- see the 5 variants in
  nushaders `compile_pc_tub.ps1`). Base matched the sampled technique's
  constant set exactly; revisit per-technique if a shader binds constants the
  technique lacks.
- **materialDiffuse et al. defaults**: internal-block instance data (the BE
  float payloads) are flipped and preserved; the runtime handle-binding path
  (technique -> program buffer `GetVariableHandleByName`) is engine-side and
  untested.
- **Godray**: RECOVERED (2026-08-17) -- `recovered/Godray_Additive_Doublesided.fx`,
  decoded from the bundle's own X360 programs (VS 0xDFF4FAE8 / PS 0x45ADE07A) with
  `xenos.py`; the fxc CTAB now matches the X360 CTAB name-for-name (even register
  for register).  The fallback substitute had been asserting at TRK_UNIT83/379/
  381/388_GR stream-in because it lacked the technique's internal PS constant
  `illuminance`.  **CarStudio**: no TUB HLSL; still fallback-substituted (its only
  internal constant, `materialDiffuse`, is in the fallback).

## 8. Xenos disassembler + the bundle-pair ground-truth oracle (2026-08-14)

`xenos.py` disassembles X360 (Xenos) shader microcode -- the
`[64-byte literal float4 block][instruction stream]` region of a shader
package, split per the two dwords at the package header's `+0x18` pointer.
`ctab.py` reads the same package's big-endian CTAB, giving byte-pinned
uniform names and register indices for whatever `xenos.py` decodes.

**Validation, and the reusable oracle.** `SHADERS.BNDL` (X360) and
`out/SHADERS_PC.BNDL` carry the SAME shaders under IDENTICAL resource ids --
one side Xenos microcode, the other fxc-compiled D3D9 bytecode. Extract both
sides of any shared resource with `build/tools/yap/YAP.exe`, disassemble the
X360 side with `xenos.py` and the PC side with `fxc /dumpbin`, and compare
instruction for instruction. Resource `CC3B3312` was used to prove the
decoder (including the relative ALU swizzle rule, the scalar-unit src3
selection, and the literal block mapping to c252..c255 -- details in the
`xenos.py` docstring). The same procedure decides ANY future Xenos decode
question in this project: pick a resource present in both bundles and the PC
bytecode is the answer key. Worked example (the post-fx composite, all 12
permutations): `scratch/postfx_step2_out/shader/REPORT.md`.
