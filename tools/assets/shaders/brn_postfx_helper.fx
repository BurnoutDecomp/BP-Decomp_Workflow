// ============================================================================
// brn_postfx_helper.fx -- the four rw::graphics::postfx::PfxHelper programs and
// the rw::graphics::postfx::DepthOfField pixel program.
//
// AUTHORED, NOT CONVERTED.  Like the composite pair and the six bloom programs,
// none of these five is in SHADERS.BNDL: each is a Xenos microcode package
// embedded in the X360 executable and handed straight to
// renderengine::ProgramBuffer::Initialize --
//   PfxHelper "uvOffset"   vertex  X360 0x82044240  288 B  ucode +0x0C0 (0,96)
//   PfxHelper 9-tap        pixel   X360 0x820444F8  688 B  ucode +0x148 (0,360)
//   PfxHelper 16-tap       pixel   X360 0x820447A8  948 B  ucode +0x150 (0,612)
//   PfxHelper 4-tap        pixel   X360 0x82044360  408 B  ucode +0x0E4 (0,180)
//   DepthOfField           pixel   X360 0x82043FB8  644 B  ucode +0x19C (64,168)
// (the pair after each size is the (literal-block bytes, instruction-stream
// bytes) split the package header's +0x18 field points at; only the DoF program
// has a literal block, and its four literal rows map to c252..c255).
// The bytes are scratch/postfx_step5_wave/PACKAGES_DUMP.md, dumped from
// ARTIST_copy.i64; every one of the five sizes matches the byte count the
// committed rwgpfxhelper.cpp / rwgpfxdof.cpp already record at their call sites.
// All five were disassembled with tools/assets/shaders/xenos.py -- the decoder
// proved against the X360-vs-PC SHADERS.BNDL pair -- and every line below has a
// named counterpart in that disassembly.
//
// THE CONSTANT SURFACE IS NOT GUESSED: it is the CTAB interned in each package
// (tools/assets/shaders/ctab.py), and it reproduces, name for name and register
// for register, exactly the names PfxHelper::PfxHelper @0x82408348 and
// DepthOfField::DepthOfField @0x82402CA8 already ask for through
// renderengine::ProgramBuffer::GetVariableHandleByName:
//   quad vertex : c0  uvOffset                      (vector float4)
//   9-tap pixel : c0  sampleOffsets4x4_1 (float4x4, 4 regs)
//                 c4  sampleOffsets4x4_2 (float4x4, 4 regs)
//                 c8  sampleOffsets4_1   (vector float4, 1 reg)
//                 s0  scene_texture
//   16-tap pixel: c0  sampleOffsets_1  c4 sampleOffsets_2
//                 c8  sampleOffsets_3  c12 sampleOffsets_4  (float4x4 each)
//                 s0  scene_texture
//   4-tap pixel : c0  sampleOffsets (float4x4, 4 regs), s0 scene_texture
//   DoF pixel   : c0  g_focalConstants1, c1 g_focalConstants2 (vector float4)
//                 s0  screen_texture, s1 low_texture, s2 depth_texture
//
// WHICH PROGRAM IS WHICH -- A FINDING.  The three helper PIXEL programs are 9,
// 16 and 4 taps respectively, counted from their tfetch instructions AND from
// their CTAB register counts (4+4+1 = 9, 4+4+4+4 = 16, 4).  That settles the
// question the committed rwgpfxhelper.cpp banner left open ("the DWARF's
// 9tap/16tap member names and the shader-variable names disagree about which
// slot is which"): they do NOT disagree.  m_9tapPixelProgram (+0x20, the one
// bound to sampleOffsets4x4_1/_2/sampleOffsets4_1) really is the 9-tap that
// Blur9 pushes 4+4+1 rows into; m_16tapPixelProgram (+0x30, sampleOffsets_1..4)
// really is the 16-tap DownSample(METHOD_16TAP) fills; m_4tapPixelProgram
// (+0x44, sampleOffsets) really is the 4-tap that METHOD_16TAP_WITH_BILINEAR
// uses (InitWeights_Blur16WithBilinear emits exactly 4 bilinear taps).  The
// DWARF member names are correct as committed.
//
// VERTEX INPUT.  PfxHelper::PfxHelper builds the quad's declaration with the
// same two elements the composite and the bloom pairs use (asm 0x82408370-A8):
// element 0 format 0x2A23B9 (FLOAT3) elementType 1 -> POSITION0, element 1
// format 0x2C23A5 (FLOAT2) elementType 6 -> TEXCOORD0.  The quad is already in
// clip space and the vertex program passes POSITION through with w forced to 1
// (`tfetch r1.xyz1` + `max export62, r1, r1`).  No transform.
//
// Build (identical recipe + flags to PostFxProgramsPC.cpp / PostFxBloom-
// ProgramsPC.cpp).  /Zpr matters here: the four sampleOffsets* matrices are
// declared float4x4 to reproduce the console CTAB's `matrix_rows float[4x4]`
// class exactly, and row-major packing is what puts tap i in register base+i.
//   fxc /nologo /T vs_3_0 /E mainQuadVS   /O2 /Zpr /Fo helper_quad_vs.fxo  brn_postfx_helper.fx
//   fxc /nologo /T ps_3_0 /E mainBlur9PS  /O2 /Zpr /Fo helper_blur9_ps.fxo brn_postfx_helper.fx
//   fxc /nologo /T ps_3_0 /E mainBlur16PS /O2 /Zpr /Fo helper_blur16_ps.fxo brn_postfx_helper.fx
//   fxc /nologo /T ps_3_0 /E mainBlur4PS  /O2 /Zpr /Fo helper_blur4_ps.fxo brn_postfx_helper.fx
//   fxc /nologo /T ps_3_0 /E mainDofPS    /O2 /Zpr /Fo postfx_dof_ps.fxo   brn_postfx_helper.fx
// then wrapped by tools/assets/shaders/shader_transcode.py::
// build_pc_program_buffer(bytecode, shader_type) and published as
// b5-decomp/src/pc/gcm/renderengine/PostFxHelperProgramsPC.cpp.
//
// ALPHA.  All four console pixel programs end their export with the scalar
// unit's `retain_prev export0.___w [= PS]`, and none of the four issues a
// scalar op that would define PS for the export -- so the exported alpha is the
// previous-scalar residual, i.e. INDETERMINATE on the console (the same finding
// the bloom decode recorded).  Written as 0 here so the PC result is
// deterministic; flagged rather than pretended to be recovered.
//
// THE .xzy PERMUTATIONS.  Every accumulate chain below alternates operands
// between identity and the .xzy swizzle, which is an involution, so the pairs
// cancel and the net channel order is identity.  Traced instruction by
// instruction for all three blur programs in the wave report (the final mad of
// the 16-tap reads r0.xyzz -- identity -- and the final mad of the 9-tap reads
// r0.xzyy -- one permutation outstanding from an odd chain -- which is exactly
// the parity the trace predicts; that self-consistency is itself evidence the
// swizzle decode is right).
// ============================================================================

// ---- shared vertex input ---------------------------------------------------
struct PfxHelperVertexIn
{
    float3 mPosition : POSITION;    // already clip space (the helper's quad)
    float2 mUv       : TEXCOORD0;
};

struct PfxHelperVertexOut
{
    float4 mPosition : POSITION;
    float2 mUv       : TEXCOORD0;
};

// ============================================================================
// THE SHARED QUAD VERTEX PROGRAM  (X360 0x82044240, m_quadVertexProgram)
//
// Microcode (4 slots):
//   3 : tfetch  r1.xyz1, r0.yxx, tf31        ; POSITION, w forced to 1
//   4 : max     export62.xyzw, r1, r1        ; -> oPos (the "mov" idiom)
//   5 : tfetch  r0.xy__, r0.yxx, tf31        ; TEXCOORD0
//   6 : add     export0.xy__, r0.xyyy, c0.xyyy ; oT0.xy = uv + uvOffset.xy
//
// uvOffset is the half-texel PfxHelper::Blur9 computes from the DESTINATION
// target (0.5/w, 0.5/h, 0, 0) and PfxHelper::RenderQuad writes through
// m_uvOffsetHandle; DownSample passes null, for which RenderQuad writes four
// zeros (asm 0x823FE608-20).  Only .xy is ever added -- .zw are carried by the
// constant row and never read, exactly as encoded.
// ============================================================================
float4 uvOffset : register(c0);

PfxHelperVertexOut mainQuadVS(PfxHelperVertexIn lIn)
{
    PfxHelperVertexOut lOut;
    lOut.mPosition = float4(lIn.mPosition, 1.0f);
    lOut.mUv       = lIn.mUv + uvOffset.xy;
    return lOut;
}

// ---- the shared source sampler of all three blur programs -------------------
// CTAB: `scene_texture`, sampler reg 0.  PfxHelper::Blur9 / ::DownSample bind
// it by UNIT (`li r4, 0` at every shadow::Device::SetState(TextureState*, unit)
// call site), never by name.
sampler2D scene_texture : register(s0);

// ============================================================================
// THE 9-TAP DIRECTIONAL BLUR  (X360 0x820444F8, m_9tapPixelProgram)
//
// Nine tfetch of tf0, nine weighted taps.  Each row of the three constants is
// (offsetX, offsetY, weight, *) -- exactly what
// PfxHelper::InitWeights_DirBlur9Quadratic fills (lanes 0/1/2; lane 3 is never
// written by the generator and never read here).  PfxHelper::Blur9 pushes rows
// 0..3 through sampleOffsets4x4_1, rows 4..7 through sampleOffsets4x4_2 and row
// 8 through sampleOffsets4_1 -- 4 + 4 + 1 = the 9 registers the CTAB declares.
//
// Microcode (28 slots): 3..10 build the nine offset UVs (two of them on the
// scalar unit as `maxs` PS-load + `adds_prev`, which is the same add), 11..19
// fetch, 20 multiplies tap8 by c8.z and 21..28 mad the rest down to tap0.
// ============================================================================
float4x4 sampleOffsets4x4_1 : register(c0);
float4x4 sampleOffsets4x4_2 : register(c4);
float4   sampleOffsets4_1   : register(c8);

float3 PfxHelperWeightedTap(float2 lUv, float4 lOffsetAndWeight)
{
    return tex2D(scene_texture, lUv + lOffsetAndWeight.xy).rgb * lOffsetAndWeight.z;
}

float4 mainBlur9PS(float2 lUv : TEXCOORD0) : COLOR0
{
    // Written in the console's own accumulation order (tap 8 first, tap 0 last).
    float3 lSum = PfxHelperWeightedTap(lUv, sampleOffsets4_1);
    lSum += PfxHelperWeightedTap(lUv, sampleOffsets4x4_2[3]);
    lSum += PfxHelperWeightedTap(lUv, sampleOffsets4x4_2[2]);
    lSum += PfxHelperWeightedTap(lUv, sampleOffsets4x4_2[1]);
    lSum += PfxHelperWeightedTap(lUv, sampleOffsets4x4_2[0]);
    lSum += PfxHelperWeightedTap(lUv, sampleOffsets4x4_1[3]);
    lSum += PfxHelperWeightedTap(lUv, sampleOffsets4x4_1[2]);
    lSum += PfxHelperWeightedTap(lUv, sampleOffsets4x4_1[1]);
    lSum += PfxHelperWeightedTap(lUv, sampleOffsets4x4_1[0]);
    return float4(lSum, 0.0f);
}

// ============================================================================
// THE 16-TAP BOX BLUR  (X360 0x820447A8, m_16tapPixelProgram)
//
// Sixteen tfetch of tf0, sixteen weighted taps, four float4x4 constants.
// PfxHelper::DownSample(METHOD_16TAP) fills them from
// PfxHelper::InitWeights_Blur16 (a 4x4 grid, weight lane normalised to sum 1)
// and pushes 4 rows through each of sampleOffsets_1..4.
//
// Microcode (49 slots): 5..17 build the sixteen offset UVs, 18..33 fetch,
// 34 multiplies tap15 by c15.z and 35..49 mad the rest down to tap0.
// ============================================================================
float4x4 sampleOffsets_1 : register(c0);
float4x4 sampleOffsets_2 : register(c4);
float4x4 sampleOffsets_3 : register(c8);
float4x4 sampleOffsets_4 : register(c12);

float4 mainBlur16PS(float2 lUv : TEXCOORD0) : COLOR0
{
    float3 lSum = PfxHelperWeightedTap(lUv, sampleOffsets_4[3]);
    lSum += PfxHelperWeightedTap(lUv, sampleOffsets_4[2]);
    lSum += PfxHelperWeightedTap(lUv, sampleOffsets_4[1]);
    lSum += PfxHelperWeightedTap(lUv, sampleOffsets_4[0]);
    lSum += PfxHelperWeightedTap(lUv, sampleOffsets_3[3]);
    lSum += PfxHelperWeightedTap(lUv, sampleOffsets_3[2]);
    lSum += PfxHelperWeightedTap(lUv, sampleOffsets_3[1]);
    lSum += PfxHelperWeightedTap(lUv, sampleOffsets_3[0]);
    lSum += PfxHelperWeightedTap(lUv, sampleOffsets_2[3]);
    lSum += PfxHelperWeightedTap(lUv, sampleOffsets_2[2]);
    lSum += PfxHelperWeightedTap(lUv, sampleOffsets_2[1]);
    lSum += PfxHelperWeightedTap(lUv, sampleOffsets_2[0]);
    lSum += PfxHelperWeightedTap(lUv, sampleOffsets_1[3]);
    lSum += PfxHelperWeightedTap(lUv, sampleOffsets_1[2]);
    lSum += PfxHelperWeightedTap(lUv, sampleOffsets_1[1]);
    lSum += PfxHelperWeightedTap(lUv, sampleOffsets_1[0]);
    return float4(lSum, 0.0f);
}

// ============================================================================
// THE 4-TAP BILINEAR DOWN-SAMPLE  (X360 0x82044360, m_4tapPixelProgram)
//
// Four tfetch of tf0, one float4x4 constant.  PfxHelper::DownSample
// (METHOD_16TAP_WITH_BILINEAR) fills it from
// PfxHelper::InitWeights_Blur16WithBilinear, which emits four rows of
// (offsetX, offsetY, 0.25, 1.0) -- a 4x4 box covered by four bilinear taps,
// which is why the "16 tap with bilinear" method drives a FOUR tap program.
//
// Microcode (13 slots): 2..5 build the four offset UVs, 6..9 fetch, 10
// multiplies tap3 by c3.z and 11..13 mad taps 2, 1, 0.
// ============================================================================
float4x4 sampleOffsets : register(c0);

float4 mainBlur4PS(float2 lUv : TEXCOORD0) : COLOR0
{
    float3 lSum = PfxHelperWeightedTap(lUv, sampleOffsets[3]);
    lSum += PfxHelperWeightedTap(lUv, sampleOffsets[2]);
    lSum += PfxHelperWeightedTap(lUv, sampleOffsets[1]);
    lSum += PfxHelperWeightedTap(lUv, sampleOffsets[0]);
    return float4(lSum, 0.0f);
}

// ============================================================================
// THE DEPTH-OF-FIELD COMPOSITE  (X360 0x82043FB8,
// DepthOfField::m_depthOfFieldProgram)
//
// Microcode (11 slots + a 64-byte literal block):
//   ; literal c254 = {5.96047e-08, 0.00390625, 1.52588e-05, 0.5}
//   ;               = { 2^-24,      2^-8,      2^-16,       0.5 }
//   ; literal c255 = {255, 0, 0, 0}
//    2 : tfetch  r2.xyz_, r0.xyx, tf1       ; low_texture   (the blurred half-res)
//    3 : tfetch  r1.xyz_, r0.xyx, tf0       ; screen_texture(the sharp scene)
//    4 : tfetch  r0.xyw_, r0.xyx, tf2       ; depth_texture (r0.xyz <- D.r,D.g,D.a)
//    5 : mad     r0.xyz_, r0.zxyy, c255.xxxx, c254.wwww   ; byte = c*255 + 0.5
//    6 : floor   r0.xyz_, r0.xyzz
//    7 : dp3     r0.x___, r0.zxyy, c254.xyzz              ; the 24-bit recombine
//    8 : add     r0.__z_, r0.xxxx, -c0.zzzz               ; depth - focal[2]
//    8   subsc0  r0._y__, c0.y                            ; focal[1] - depth
//    9 : mul     r0.xy__, r0.yzzz, c1.yzzz [clamp]        ; * scales, saturate
//   10   maxs    r0._y__, r0.xy                           ; max(near, far)
//   11 : add     r0.x_zw, r2.xyyz, -r1.xyyz               ; low - screen
//   11   mulsc0  r0._y__, c1.x                            ; * amount
//   12 : mad     export0.xyzw, r0.yyyy, r0.xzww, r1.xyzz  ; screen + t*(low-screen)
//   12   retain_prev export0.___w                         ; alpha = PS (banner)
//
// THE TWO SCALAR-CONSTANT OPS.  `subsc0` / `mulsc0` name only ONE operand in
// the disassembly (the constant, indexed by the src3 register field); the other
// is the scalar destination register's component (swz + 0) & 3 -- the reading
// the post-fx step-2 composite decode established and corroborated against
// SHADERS.BNDL resource CC3B3312, whose `subsc0 r2.x, c255.x` is the only
// reading that makes its bilinear weight set correct.  Applied here: slot 8's
// src3 swizzle 0x80 gives register component x (= the depth just written by the
// dp3) against c0.y, and slot 11's swizzle 0x41 gives register component y (=
// the max) against c1.x.  Both readings are forced by the surrounding chain --
// nothing else in r0 holds a depth at slot 8, and nothing else holds the blur
// factor at slot 11 -- and both produce the standard four-plane DoF the class's
// State (near-blur / focal-near / focal-far / far-blur) describes.
//
// ==> BLUR FACTOR:
//        near = saturate((focal[1] - depth) * g_focalConstants2.y)
//        far  = saturate((depth  - focal[2]) * g_focalConstants2.z)
//        t    = max(near, far) * g_focalConstants2.x
//        oC0.rgb = lerp(screen, low, t)
//     g_focalConstants1 is DepthOfField::m_state.m_focalPlanes[0..3] as SetState
//     resolved them (each plane linearised through the projection and clamped to
//     [0,1]); .x and .w -- the two OUTER planes -- are never read by this
//     program, which is a finding, not an omission (grep of the decode:
//     c0 appears only as c0.z and c0.y).
//
// [FLAG PC deviation: THE DEPTH DECODE]  Slots 4-7 above reconstruct a 24-bit
// depth out of three 8-bit channels of a depth surface sampled as ARGB8 --
// depth = (A*255)*2^-8 + (R*255)*2^-16 + (G*255)*2^-24, which is what the Xenos
// hands back when a D24 depth buffer is read through a colour sampler.  On the
// PC backend the post-fx targets' depth is bound as a RAW-DEPTH texture
// (INTZ / DF24 / DF16 -- the depthtex group of this same wave), and a raw-depth
// sampler returns the depth VALUE in .r at full precision.  The quantity is the
// same quantity; only the encoding of the source texture differs, so the three
// decode instructions are replaced by the single fetch below and the console
// form is kept on the page above.  This is the one place where this file is not
// an instruction-for-instruction re-expression of the console program.  If the
// depth texture ever comes back as an ARGB8 blit instead of a raw-depth format,
// THIS is the line to change (a wrong choice here reads as depth-of-field
// applied in bands / inverted, never as a crash).
// ============================================================================
float4 g_focalConstants1 : register(c0);   // resolved focal planes [0..3]
float4 g_focalConstants2 : register(c1);   // .x amount, .y near scale, .z far scale

sampler2D screen_texture : register(s0);
sampler2D low_texture    : register(s1);
sampler2D depth_texture  : register(s2);

float4 mainDofPS(float2 lUv : TEXCOORD0) : COLOR0
{
    const float3 lLow    = tex2D(low_texture,    lUv).rgb;   // tf1
    const float3 lScreen = tex2D(screen_texture, lUv).rgb;   // tf0
    const float  lDepth  = tex2D(depth_texture,  lUv).r;     // tf2 -- see the PC deviation

    const float lNear = saturate((g_focalConstants1.y - lDepth) * g_focalConstants2.y);
    const float lFar  = saturate((lDepth - g_focalConstants1.z) * g_focalConstants2.z);
    const float lBlur = max(lNear, lFar) * g_focalConstants2.x;

    return float4(lScreen + lBlur * (lLow - lScreen), 0.0f);
}
