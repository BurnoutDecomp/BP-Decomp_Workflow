// ============================================================================
// brn_postfx_composite.fx -- BrnPostFxShader permutation 0 (the base composite).
//
// AUTHORED, NOT CONVERTED.  The console pair is Xenos microcode embedded in the
// X360 executable (vertex unk_0x8203F630, 596 B; pixel unk_0x8203F888, 696 B),
// not a SHADERS.BNDL entry, so there is no HLSL source to recompile.  Both
// programs were disassembled from that microcode and re-expressed here; every
// line below has a named counterpart in the disassembly recorded in
// scratch/postfx_step2_out/shader/REPORT.md.
//
// Constant registers are pinned with register() to the console's own CTAB
// assignment so the PC program's variable table matches the X360 one register
// for register (the engine resolves by NAME through
// renderengine::ProgramBuffer::GetVariableHandleByName, so this is a
// convenience, not a requirement).
//
//   vertex : c0 VignetteCentreXyScaleXy, c1 VignetteAngle
//   pixel  : c0 GlobalParams, c1 BloomColour, c2 VignetteInnerRgbPlusMul,
//            c3 VignetteOuterRgbPlusAdd, c4 Tint2dColour,
//            s0 SamplerSource, s1 SamplerBloom
//
// Build (see REPORT.md; /Zpr is load-bearing -- fxc defaults to column-major):
//   fxc /nologo /T vs_3_0 /E main /O2 /Zpr /Fo composite_vs.fxo brn_postfx_composite.fx
//   fxc /nologo /T ps_3_0 /E main /O2 /Zpr /Fo composite_ps.fxo brn_postfx_composite.fx
// then wrapped by tools/assets/shaders/shader_transcode.py::build_pc_program_buffer.
// ============================================================================

// ---- vertex ----------------------------------------------------------------
float4 VignetteCentreXyScaleXy : register(c0);
float4 VignetteAngle           : register(c1);

struct VertexIn
{
    float3 mPosition : POSITION;     // already in clip space (BrnPostFxShader::Render)
    float2 mUv       : TEXCOORD0;    // source UV, half-texel offset already applied
};

struct VertexOut
{
    float4 mPosition : POSITION;
    float4 mUv       : TEXCOORD0;    // .xy source UV, .zw vignette-space coordinate
};

VertexOut mainVS(VertexIn lIn)
{
    VertexOut lOut;

    // The quad is pre-transformed: the console vertex program fetches POSITION
    // and exports it unchanged (tfetch -> `max export62, r1, r1`).
    lOut.mPosition = float4(lIn.mPosition, 1.0f);

    // Screen coordinate is derived from the UV, not from the position:
    //   `add r1.xy, r0.xyyy, r0.xyyy` then `add r1.xyz, r1.xyzz, c255.xxyy`
    // with c255.x == -1.0f.
    float2 lScreen = (lIn.mUv + lIn.mUv) - 1.0f;

    // sincos of VignetteAngle.x.  The console shows the compiler's own range
    // reduction (mul by 1/2pi, +0.5, frac, *2pi, -pi) around a sin/cos pair;
    // fxc emits the identical reduction for this expression.
    float lSin;
    float lCos;
    sincos(VignetteAngle.x, lSin, lCos);

    // `mul r1.xyzw, r1.xyyx, r0.zwzw` then `add r0.w, r1.z, -r1.w` /
    // `adds r0.z, r1.xy`  ==  (x*cos + y*sin, y*cos - x*sin).
    float2 lRotated;
    lRotated.x = (lScreen.x * lCos) + (lScreen.y * lSin);
    lRotated.y = (lScreen.y * lCos) - (lScreen.x * lSin);

    // `mad r0.zw, c0.xxxy, c254.zzzz, r0.zzzw` (c254.z == -2.0f), then
    // `add r0.zw, r0.zzzw, c254.xxxx` (c254.x == 1.0f), then `mul r0.zw, c0.zw`.
    lOut.mUv.xy = lIn.mUv;
    lOut.mUv.zw = (lRotated - ((VignetteCentreXyScaleXy.xy + VignetteCentreXyScaleXy.xy) - 1.0f))
                  * VignetteCentreXyScaleXy.zw;
    return lOut;
}

// ---- pixel -----------------------------------------------------------------
float4 GlobalParams            : register(c0);   // .x = 1 / white level
float4 BloomColour             : register(c1);
float4 VignetteInnerRgbPlusMul : register(c2);
float4 VignetteOuterRgbPlusAdd : register(c3);   // .w = the gradient's ADD term
float4 Tint2dColour            : register(c4);

sampler2D SamplerSource : register(s0);
sampler2D SamplerBloom  : register(s1);

float4 mainPS(float4 lUv : TEXCOORD0) : COLOR0
{
    // `tfetch r1.xyz_, r0.xy, tf0` / `tfetch r2.xyz_, r0.xy, tf1` -- rgb only.
    float3 lSource = tex2D(SamplerSource, lUv.xy).rgb * GlobalParams.x;
    float3 lBloom  = tex2D(SamplerBloom,  lUv.xy).rgb * BloomColour.rgb;

    // SCREEN BLEND, built as three instructions on the console:
    //   `mul r2.xyz, r1, r3 [clamp]`   -> saturate(source * bloom)
    //   `add r2.xyz, r3, -r2`          -> bloom - that
    //   `add r1.xyz, r2, r1`           -> + source
    float3 lComposite = (lBloom - saturate(lSource * lBloom)) + lSource;

    // `dp2add r0.x, r0.zw, r0.zw, c255.y(0)` then `sqrt r0.x`.
    float lRadius = sqrt(dot(lUv.zw, lUv.zw));

    // `addsc0 r0.x, VignetteOuterRgbPlusAdd.w` with the scalar clamp bit set.
    float lT = saturate(lRadius + VignetteOuterRgbPlusAdd.w);

    // `muls r1.w, r0.xx` (t*t), `mad r0.x, -r0.x, 2.0f, 3.0f`,
    // `muls_prev r0.x, r0.x` -- the smoothstep polynomial t*t*(3 - 2t).
    float lGradient = (lT * lT) * (3.0f - (2.0f * lT));

    // `mad r0.xyz, r0.xxx, r0.yzw, c2.xyz` where r0.yzw == outer - inner.
    float3 lVignette = VignetteInnerRgbPlusMul.rgb
                     + (lGradient * (VignetteOuterRgbPlusAdd.rgb - VignetteInnerRgbPlusMul.rgb));

    // `mad export0.xyz, r1.xyz, r0.xyz, c4.xyz`, and the scalar unit's
    // `retain_prev export0.w` writes the last scalar result (the gradient).
    float4 lResult;
    lResult.rgb = (lComposite * lVignette) + Tint2dColour.rgb;
    lResult.a   = lGradient;
    return lResult;
}
