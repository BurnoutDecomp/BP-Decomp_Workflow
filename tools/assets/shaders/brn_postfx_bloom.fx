// ============================================================================
// brn_postfx_bloom.fx -- the six BrnPostFxBloom programs (three vertex/pixel
// pairs: down-sample, "new" one-pass blur, "old" two-pass separable blur).
//
// AUTHORED, NOT CONVERTED.  The console six are Xenos microcode embedded in the
// X360 executable, not SHADERS.BNDL entries, so there is no HLSL to recompile:
//   gacBloomDSVertexProgram      X360 0x8203E6F8  348 B  ucode +0x0F0  (0,108)
//   gacBloomDSPixelProgram       X360 0x8203E858  516 B  ucode +0x114  (0,240)
//   gacBloomBlurVertexProgram    X360 0x8203EA60  368 B  ucode +0x0F8  (0,120)
//   gacBloomBlurPixelProgram     X360 0x8203EBD0  420 B  ucode +0x0E0  (64,132)
//   gacBloomBlurOldVertexProgram X360 0x8203ED78  404 B  ucode +0x11C  (0,120)
//   gacBloomBlurOldPixelProgram  X360 0x8203EF10  424 B  ucode +0x10C  (0,156)
// (the pair after each size is the (literal-block bytes, instruction-stream
// bytes) split the package header's +0x18 field points at).  All six were
// disassembled with tools/assets/shaders/xenos.py -- the decoder proved against
// the X360-vs-PC SHADERS.BNDL pair -- and every line below has a named
// counterpart in that disassembly (work/dis_all.txt of the step-4 shader wave).
//
// The constant surface is NOT guessed: it is the CTAB interned in each package
// (tools/assets/shaders/ctab.py), and it reproduces, name for name, exactly the
// names BrnPostFxBloom::Construct already asks for through
// renderengine::ProgramBuffer::GetVariableHandleByName:
//     DS vertex      : c0 kUvOffset_00_01, c1 kUvOffset_02_03
//     DS pixel       : c0 kDotWithWhiteLevel (float3), c1 kThresholdAndScale
//                      (float3), s0 SamplerSource
//     blur vertex    : c0 kUvOffset_00_01, c1 kUvOffset_02_03
//     blur pixel     : s0 SamplerSource   (no float constants at all)
//     blurOld vertex : c0 kUvOffset_00_01, c1 kUvOffset_02_03, c2 kUvOffset_04_05
//     blurOld pixel  : c0 kTapWeights0_3, c1 kTapWeights4, s0 SamplerSource
// Each is pinned with register() to the console's own assignment so the PC
// program's variable table matches register for register (the engine still
// resolves by NAME, so this is a convenience, not a requirement).
//
// VERTEX INPUT is the same declaration all three pairs share, built by
// BrnPostFxBloom::Construct: element 0 format 0x2A23B9 (FLOAT3) elementType 1
// (-> POSITION0), element 1 format 0x2C23A5 (FLOAT2) elementType 6 (->
// TEXCOORD0) -- the identical two-element Parameters block
// BrnPostFxShader::Construct builds for the composite, whose PC pair draws
// today.  The quad is ALREADY IN CLIP SPACE (DrawFullScreenQuad writes +-1 xy,
// z 0), and every console vertex program passes POSITION straight through with
// w forced to 1 (`tfetch r1.xyz1` + `max export62, r1, r1`).  No transform.
//
// Build (identical recipe + flags to PostFxProgramsPC.cpp / the composite;
// /Zpr is carried so the recipe stays the same as every other converted PC
// program -- none of these six has a matrix constant, so it changes nothing):
//   fxc /nologo /T vs_3_0 /E mainDSVS      /O2 /Zpr /Fo bloom_ds_vs.fxo      brn_postfx_bloom.fx
//   fxc /nologo /T ps_3_0 /E mainDSPS      /O2 /Zpr /Fo bloom_ds_ps.fxo      brn_postfx_bloom.fx
//   fxc /nologo /T vs_3_0 /E mainBlurVS    /O2 /Zpr /Fo bloom_blur_vs.fxo    brn_postfx_bloom.fx
//   fxc /nologo /T ps_3_0 /E mainBlurPS    /O2 /Zpr /Fo bloom_blur_ps.fxo    brn_postfx_bloom.fx
//   fxc /nologo /T vs_3_0 /E mainBlurOldVS /O2 /Zpr /Fo bloom_blurold_vs.fxo brn_postfx_bloom.fx
//   fxc /nologo /T ps_3_0 /E mainBlurOldPS /O2 /Zpr /Fo bloom_blurold_ps.fxo brn_postfx_bloom.fx
// then wrapped by tools/assets/shaders/shader_transcode.py::
// build_pc_program_buffer(bytecode, shader_type) and published as
// b5-decomp/src/pc/gcm/renderengine/PostFxBloomProgramsPC.cpp.
//
// ALPHA.  All three console pixel programs end their export with the scalar
// unit's `retain_prev export0.___w [= PS]`, and NONE of the three ever issues a
// scalar op -- so the alpha channel is the previous-scalar register's residual
// value, i.e. INDETERMINATE on the console.  It is never read: every consumer of
// the bloom / work targets fetches rgb only (`tfetch r?.xyz_` in all three blur
// programs and in the composite's `SamplerBloom` fetch).  Written as 0 here so
// the PC result is deterministic; flagged rather than pretended to be recovered.
// ============================================================================

// ---- shared vertex input ---------------------------------------------------
struct BloomVertexIn
{
    float3 mPosition : POSITION;    // already clip space (DrawFullScreenQuad)
    float2 mUv       : TEXCOORD0;   // source UV, half-texel offset already applied
};

// ============================================================================
// PASS 1 -- DOWN-SAMPLE / BRIGHT-PASS  (X360 vs 0x8203E6F8, ps 0x8203E858)
// ============================================================================
float4 kUvOffset_00_01 : register(c0);
float4 kUvOffset_02_03 : register(c1);

struct BloomDsVertexOut
{
    float4 mPosition : POSITION;
    float4 mUv_00_01 : TEXCOORD0;   // .xy tap0, .zw tap1
    float4 mUv_02_03 : TEXCOORD1;   // .xy tap2, .zw tap3
};

// Microcode (9 slots):
//   3 : tfetch  r1.xyz1, r0.yxx, tf31          ; POSITION, w forced to 1
//   4 : max     export62.xyzw, r1, r1          ; -> oPos (the "mov" idiom)
//   5 : tfetch  r0.xy__, r0.yxx, tf31          ; TEXCOORD0
//   6 : add     export0.xyzw, r0.xyxy, c0.xyzw ; TEXCOORD0 = uv.xyxy + kUvOffset_00_01
//   7 : add     export1.xyzw, r0.xyxy, c1.xyzw ; TEXCOORD1 = uv.xyxy + kUvOffset_02_03
BloomDsVertexOut mainDSVS(BloomVertexIn lIn)
{
    BloomDsVertexOut lOut;
    lOut.mPosition = float4(lIn.mPosition, 1.0f);
    lOut.mUv_00_01 = lIn.mUv.xyxy + kUvOffset_00_01;
    lOut.mUv_02_03 = lIn.mUv.xyxy + kUvOffset_02_03;
    return lOut;
}

// The CTAB declares both of these as float3 (`vector float[1x3]`), not float4 --
// which is exactly what BrnPostFxBloom::PrepareDownSampleBuffer writes:
// kDotWithWhiteLevel = (k/white, k/white, k/white, 0) and kThresholdAndScale =
// (threshold, 0.25/(1-threshold), 0, 0), the fourth lane being padding on a
// 16-byte constant row.
float3 kDotWithWhiteLevel : register(c0);
float3 kThresholdAndScale : register(c1);

sampler2D SamplerSource : register(s0);

// One 2x2 box tap, bright-passed.  Microcode:
//   dp3 rN, tap.zxyy, c0.zxyy      ; both operands share the .zxy permutation, so
//                                    the dot is dot(tap.rgb, kDotWithWhiteLevel)
//   add r3, rN, -c1.xxxx           ; luminance - kThresholdAndScale.x
//   mul rM.xyz, r3.<lane>, tap [clamp]  ; saturate((lum - threshold) * tap.rgb)
float3 BloomDsBrightTap(float2 lUv)
{
    float3 lTap = tex2D(SamplerSource, lUv).rgb;
    float  lLuminance = dot(lTap, kDotWithWhiteLevel);
    return saturate((lLuminance - kThresholdAndScale.x) * lTap);
}

// Microcode (20 slots):
//   2..5  : four tfetch of tf0 at TEXCOORD0.xy / TEXCOORD0.zw / TEXCOORD1.xy /
//           TEXCOORD1.zw   (r4 / r2 / r5 / r1 respectively)
//   6..9  : dp3 each tap against c0  -> r0.x=tap0 r0.w=tap1 r0.z=tap2 r0.y=tap3
//   10    : add r3, r0, -c1.xxxx                 ; all four minus the threshold
//   11..14: mul rM.xyz, r3.<lane>, tap [clamp]   ; the saturate on each tap
//   15..17: three adds; every operand carries the .xzy permutation, which is an
//           involution and cancels exactly across the chain (traced in the wave
//           report) -- the net is the plain sum of the four bright taps
//   18    : mul export0.xyzw, r0.xzyy, c1.yyyy   ; * kThresholdAndScale.y
//   18    : retain_prev export0.___w             ; alpha = PS (see banner)
float4 mainDSPS(float4 lUv_00_01 : TEXCOORD0,
                float4 lUv_02_03 : TEXCOORD1) : COLOR0
{
    float3 lBright = BloomDsBrightTap(lUv_00_01.xy)
                   + BloomDsBrightTap(lUv_00_01.zw)
                   + BloomDsBrightTap(lUv_02_03.xy)
                   + BloomDsBrightTap(lUv_02_03.zw);
    return float4(lBright * kThresholdAndScale.y, 0.0f);
}

// ============================================================================
// PASS 2 -- THE "NEW" ONE-PASS BLUR  (X360 vs 0x8203EA60, ps 0x8203EBD0)
// Reached only on the mbUseNewBloom arm, which Construct clears -- so it is
// dead on the shipping path.  Reconstructed anyway, exactly as the console has
// it, because the slot must not be left empty while the other five are filled.
// ============================================================================
struct BloomBlurVertexOut
{
    float4 mPosition : POSITION;
    float4 mUv_00_01 : TEXCOORD0;   // .xy tap0, .zw tap1
    float4 mUv_02_03 : TEXCOORD1;   // .xy tap2, .zw tap3
    float4 mUvRaw    : TEXCOORD2;   // the un-offset uv, duplicated -- see below
};

// Microcode (10 slots): identical to the down-sample vertex program plus ONE
// extra export --
//   6 : max export2.xyzw, r0.xyxy, r0.xyxy   ; TEXCOORD2 = (u, v, u, v)
// FINDING: the "new" blur PIXEL program never reads TEXCOORD2 (it fetches only
// r0 and r1, i.e. TEXCOORD0/1).  The export is dead on the console too.  It is
// reproduced because dropping it would change the vertex program's interpolator
// allocation, and because the console's own encoding is the authority here.
BloomBlurVertexOut mainBlurVS(BloomVertexIn lIn)
{
    BloomBlurVertexOut lOut;
    lOut.mPosition = float4(lIn.mPosition, 1.0f);
    lOut.mUvRaw    = lIn.mUv.xyxy;
    lOut.mUv_00_01 = lIn.mUv.xyxy + kUvOffset_00_01;
    lOut.mUv_02_03 = lIn.mUv.xyxy + kUvOffset_02_03;
    return lOut;
}

// The tap scale is a LITERAL in the microcode's 64-byte constant block, not a
// uniform: `; literal c255 = {0.25, 0, 0, 0}` read by slot 9 as c255.xxxx.  That
// is why this program's CTAB carries no float constants at all and why
// BrnPostFxBloom::Generate1PassBlurredBloomBuffer pushes no pixel constant.
static const float KF_BLUR_TAP_SCALE = 0.25f;

// Microcode (11 slots):
//   2..5 : four tfetch of tf0 at TEXCOORD1.zw / TEXCOORD1.xy / TEXCOORD0.xy /
//          TEXCOORD0.zw
//   6..8 : three plain adds (no permutation on any operand)
//   9    : mul export0.xyzw, r0.xyzz, c255.xxxx   ; * 0.25
//   9    : retain_prev export0.___w               ; alpha = PS (see banner)
float4 mainBlurPS(float4 lUv_00_01 : TEXCOORD0,
                  float4 lUv_02_03 : TEXCOORD1) : COLOR0
{
    float3 lSum = tex2D(SamplerSource, lUv_00_01.xy).rgb
                + tex2D(SamplerSource, lUv_00_01.zw).rgb
                + tex2D(SamplerSource, lUv_02_03.xy).rgb
                + tex2D(SamplerSource, lUv_02_03.zw).rgb;
    return float4(lSum * KF_BLUR_TAP_SCALE, 0.0f);
}

// ============================================================================
// PASS 3 -- THE "OLD" SEPARABLE FIVE-TAP GAUSSIAN  (X360 vs 0x8203ED78,
// ps 0x8203EF10).  THIS is the blur the shipping build runs
// (Generate2PassBlurredBloomBuffer, the !mbUseNewBloom arm).
// ============================================================================
float4 kUvOffset_04_05 : register(c2);

struct BloomBlurOldVertexOut
{
    float4 mPosition : POSITION;
    float4 mUv_00_01 : TEXCOORD0;   // .xy tap0, .zw tap1
    float4 mUv_02_03 : TEXCOORD1;   // .xy tap2, .zw tap3
    float4 mUv_04_05 : TEXCOORD2;   // .xy tap4, .zw unused (the 6th slot)
};

// Microcode (10 slots): the down-sample vertex program with a third offset pair.
//   6 : add export0.xyzw, r0.xyxy, c0.xyzw
//   7 : add export1.xyzw, r0.xyxy, c1.xyzw
//   8 : add export2.xyzw, r0.xyxy, c2.xyzw
// Generate2PassBlurredBloomBuffer writes only five of the six lanes
// (kUvOffset_04_05 = (offset4, 0, 0, 0) horizontally / (0, offset4, 0, 0)
// vertically), so the sixth tap coincides with the centre and is never fetched.
BloomBlurOldVertexOut mainBlurOldVS(BloomVertexIn lIn)
{
    BloomBlurOldVertexOut lOut;
    lOut.mPosition = float4(lIn.mPosition, 1.0f);
    lOut.mUv_00_01 = lIn.mUv.xyxy + kUvOffset_00_01;
    lOut.mUv_02_03 = lIn.mUv.xyxy + kUvOffset_02_03;
    lOut.mUv_04_05 = lIn.mUv.xyxy + kUvOffset_04_05;
    return lOut;
}

float4 kTapWeights0_3 : register(c0);
float4 kTapWeights4   : register(c1);

// Microcode (13 slots):
//   2..6 : five tfetch of tf0 at TEXCOORD0.xy, TEXCOORD0.zw, TEXCOORD1.xy,
//          TEXCOORD1.zw, TEXCOORD2.xy   (r3, r4, r5, r1, r0)
//   7    : mul r0.xyz, r0.xzyy, c1.xxxx                  ; tap4 * kTapWeights4.x
//   8    : mad r0.xyz, r1.xzyy, c0.wwww, r0.xyzz         ; + tap3 * w3
//   9    : mad r0.xyz, r5.xyzz, c0.zzzz, r0.xzyy         ; + tap2 * w2
//  10    : mad r0.xyz, r4.xzyy, c0.yyyy, r0.xzyy         ; + tap1 * w1
//  11    : mad export0.xyzw, r3.xyzz, c0.xxxx, r0.xzyy   ; + tap0 * w0
//  11    : retain_prev export0.___w                      ; alpha = PS (banner)
// Every .xzy permutation in that chain cancels (it is an involution and the
// accumulator alternates), so the net is the plain weighted sum below -- traced
// slot by slot in the wave report.
float4 mainBlurOldPS(float4 lUv_00_01 : TEXCOORD0,
                     float4 lUv_02_03 : TEXCOORD1,
                     float4 lUv_04_05 : TEXCOORD2) : COLOR0
{
    float3 lSum = tex2D(SamplerSource, lUv_00_01.xy).rgb * kTapWeights0_3.x
                + tex2D(SamplerSource, lUv_00_01.zw).rgb * kTapWeights0_3.y
                + tex2D(SamplerSource, lUv_02_03.xy).rgb * kTapWeights0_3.z
                + tex2D(SamplerSource, lUv_02_03.zw).rgb * kTapWeights0_3.w
                + tex2D(SamplerSource, lUv_04_05.xy).rgb * kTapWeights4.x;
    return float4(lSum, 0.0f);
}
