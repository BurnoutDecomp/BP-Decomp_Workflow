# Minimal shader bring-up path (world geometry on screen with one shader pair)

The full conversion (`convert_shaders_bundle.py`, see `FORMAT_MAP.md`) already
produces a complete platform-4 SHADERS.BNDL with real per-technique D3D9
bytecode, so the minimal path is only needed if the engine agent wants to
de-risk the first world draw with a single known-good VS/PS pair before
trusting 216 compiled shaders and the constant-dispatch plumbing.

## Option A (recommended): fallback-only bundle

Build a variant of the converted bundle in which EVERY technique's program
buffers are the fallback pair (positions + one texture, vs_3_0/ps_3_0):

    py tools/assets/shaders/convert_shaders_bundle.py convert ^
        build/game/SHADERS.BNDL tools/assets/shaders/out/SHADERS_PC_FALLBACK.BNDL ^
        --fallback --fxdir tools/assets/shaders/does_not_exist_dir --allow-contract-errors

(`--allow-contract-errors` is REQUIRED for this bundle since 2026-08-17: the
converter now hard-fails when a technique's INTERNAL constant is missing from
its compiled program, because CgsResource::MaterialResourceType::
PostFixUpShaderConstants ASSERTS "Tyring to postfixup a constant not present in
the programbuffer" for exactly that -- measured against the retail bundle, the
all-fallback variant carries 192 such misses, i.e. it asserts on nearly every
material at stream-in.  It stays a bring-up diagnostic, not a runnable bundle.
Note also that tools/assets/shaders/recovered/ is always searched first, so
even this "all-fallback" bundle gets the real Godray shader.)

(pointing --fxdir at an empty/nonexistent dir forces zero TUB matches, so with
--fallback every technique maps to `fallback_world.fx`; techniques keep their
real names, imports, constant blocks and sampler tables -- only the bytecode
and descriptor tables are the fallback's.)

Contract with the engine:

- Engine asks for any technique (e.g. `Diffuse_Opaque_Singlesided_Default`,
  id 51D4924A) exactly as on X360: the technique blob is byte-layout-identical
  (LE), its imports resolve to two ShaderProgramBuffer resources.
- Each program buffer is `ProgramBufferData` (LE) with D3D9 SM3 bytecode at
  +0x14; `muShaderType` 0/1 tells VS from PS.
- The fallback pair binds only: `world` (float4x4), `ViewProjectionModified`
  (float4x4), `materialDiffuse` (float4, hash-bound), `DiffuseTextureSampler`
  (s0). All of these exist in every world technique's constant blocks, so the
  engine's name/hash binding succeeds; any technique constant absent from the
  fallback CTAB yields a register-count-0 handle and must be skipped by the
  dispatch shim (count 0 == "not found" is the committed
  GetVariableHandleByName convention).
- Result: every world mesh draws textured with s0 and correct transforms; no
  lighting/fog/shadow.

## Option B: hand-packed single pair (no converter, smallest moving parts)

1. Compile (any Windows SDK fxc, resolved like nushaders
   `Build/Resolve-PC-FXC.ps1`):

       fxc /T vs_3_0 /E VS_Main /O2 /Fo fallback_vs.fxo tools/assets/shaders/fallback_world.fx
       fxc /T ps_3_0 /E PS_Main /O2 /Fo fallback_ps.fxo tools/assets/shaders/fallback_world.fx

2. Wrap each blob:

       py -c "import sys; sys.path.insert(0,'tools/assets/shaders'); import shader_transcode as st; open('vs_pb.bin','wb').write(st.build_pc_program_buffer(open('fallback_vs.fxo','rb').read(),0)[0])"

   (`build_pc_program_buffer(bytecode, 0|1)` returns the LE primary with the
   CTAB-derived descriptor table; see FORMAT_MAP.md section 5.)

3. Either splice the two blobs over an existing technique's program buffers in
   a YAP-extracted tree and `YAP c` it back (platform 4 meta), or hand the raw
   primaries to an engine-side test harness that skips the bundle loader and
   feeds `ProgramBufferData*` straight to the shims.

## Engine-side shim needs (identical for A and B)

Minimum three touch points (details in FORMAT_MAP.md section 6):

1. Create: `XGRegisterVertexShader/PixelShader(pShader=data+0x14, _)` ->
   `CreateVertexShader/CreatePixelShader((DWORD*)pShader)`, remember object.
2. Bind: `D3DDevice_SetVertexShader/SetPixelShader` -> map the payload address
   back to the created object and `IDirect3DDevice9::SetVertexShader/...`.
3. Dispatch: handle bytes {reg index, type 0|2|3, shaderType, reg count};
   float4 -> SetConstantF, sampler -> texture stage binding, count 0 -> skip.

Vertex declarations come from the world bundles' VertexDescriptor resources
(already ported by the world flow) -- the fallback VS consumes POSITION +
TEXCOORD0 and ignores extra streams, so any world declaration binds.

## What was verified in this slice

- fxc vs_3_0/ps_3_0 compiles of the TUB sources succeed on this machine
  (fxc @ `C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\fxc.exe`).
- The compiled CTAB constant/sampler sets match the X360 technique blocks
  name-for-name and register-for-register (s0/s15) on the sampled technique.
- The full converted bundle (`out/SHADERS_PC.BNDL`) re-extracts under YAP as
  platform 4 with imports intact, LE technique blobs, and 0xFFFE0300/0xFFFF0300
  SM3 version tokens at +0x14 of every program buffer.

NOT verified (needs the engine agent / a boot test): the loader accepting the
16-byte zero secondary, the shims above, and the first actual draw.
