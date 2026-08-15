// ============================================================================
// brn_postfx_composite.fx -- BrnPostFxShader, ALL TWELVE PERMUTATIONS.
//
// AUTHORED, NOT CONVERTED.  The console pairs are Xenos microcode embedded in
// the X360 executable (twenty-four packages, byte-exact in
// scratch/postfx_wave1b_dossiers/DATA_DUMP.md PART 1), not SHADERS.BNDL
// entries, so there is no HLSL source to recompile.  Every program was
// disassembled from that microcode with tools/assets/shaders/xenos.py and
// re-expressed here; the per-slot instruction mapping is recorded in
// scratch/postfx_step5_wave/permutations/REPORT.md (permutation 0's mapping is
// the older scratch/postfx_step2_out/shader/REPORT.md, unchanged).
//
// ONE VERTEX PROGRAM FOR ALL TWELVE.  The twelve X360 vertex packages
// (0x8203F0B8, 0x8203F630, 0x8203FB40, 0x82040180, 0x82040778, 0x82040E48,
// 0x820414D8, 0x82041C50, 0x82042380, 0x82042A50, 0x820430E0, 0x82043858) are
// 596 bytes each and BYTE-IDENTICAL -- md5 a47e7e9943a3570c484e1724d6dff763 for
// all twelve.  mainVS below is therefore compiled ONCE and the same PC image is
// handed to all twelve Shader::Construct call sites.
//
// THE TWELVE PERMUTATIONS ARE THIS ONE SOURCE COMPILED TWELVE WAYS.  The
// permutation index is
//     leShader = 4 * (meQuality + 1)  (motion blur on)   -- 0, 4 or 8
//              | 2  (depth of field on)
//              | 1  (3D colour-cube tint on)
// so the three switches below reproduce the console's own axes.  Bloom, the 2D
// tint and the vignette are in EVERY permutation and are switched off by their
// CONSTANTS, never by a shader swap.
//
//     BRN_POSTFX_TINT3D   0 / 1     +1 to the index
//     BRN_POSTFX_DOF      0 / 1     +2 to the index
//     BRN_POSTFX_BLUR     0 / 1 / 2 +0 / +4 / +8  (1 = BLUR, 2 = BLURHQ)
//
// THE CONSTANT REGISTERS ARE PINNED TO THE CONSOLE'S OWN CTAB ASSIGNMENT,
// PER PERMUTATION.  A name's register is NOT stable across permutations --
// BloomColour is c1 without depth of field and c3 with it -- which is why
// BrnPostFxShader resolves every constant by NAME through
// renderengine::ProgramBuffer::GetVariableHandleByName.  The register() pins
// below make the PC variable table match the console's register for register
// anyway; the twelve decoded CTABs are in the report.
//
//   no DOF : c0 GlobalParams, c1 BloomColour, c2 VignetteInnerRgbPlusMul,
//            c3 VignetteOuterRgbPlusAdd, c4 Tint2dColour,
//            [c5 BlurMatrixX, c6 BlurMatrixY, c7 BlurMatrixW  when BLUR]
//   DOF    : c0 GlobalParams, c1 DofParamsA, c2 DofParamsB, c3 BloomColour,
//            c4 VignetteInnerRgbPlusMul, c5 VignetteOuterRgbPlusAdd,
//            c6 Tint2dColour,
//            [c7 BlurMatrixX, c8 BlurMatrixY, c9 BlurMatrixW  when BLUR]
//   samplers (identical in every permutation that declares them):
//            s0 SamplerSource, s1 SamplerBloom, s2 SamplerDof,
//            s3 Sampler3dTint, s4 SamplerDepth
//
// Build (see the report; /Zpr is load-bearing -- fxc defaults to column-major):
//   fxc /nologo /T vs_3_0 /E mainVS /O2 /Zpr /Fo composite_vs.fxo brn_postfx_composite.fx
//   fxc /nologo /T ps_3_0 /E mainPS /O2 /Zpr "/DBRN_POSTFX_DOF=1" ... /Fo ps_NN.fxo brn_postfx_composite.fx
// then wrapped by tools/assets/shaders/shader_transcode.py::build_pc_program_buffer.
// ============================================================================

#ifndef BRN_POSTFX_TINT3D
#define BRN_POSTFX_TINT3D 0
#endif
#ifndef BRN_POSTFX_DOF
#define BRN_POSTFX_DOF 0
#endif
#ifndef BRN_POSTFX_BLUR
#define BRN_POSTFX_BLUR 0
#endif

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

// ---- pixel: the constant surface, per permutation ---------------------------
#if BRN_POSTFX_DOF
float4 GlobalParams            : register(c0);   // .x = 1 / white level
float4 DofParamsA              : register(c1);   // the four projected focal planes
float4 DofParamsB              : register(c2);   // .x amount, .y 1/(A.y-A.x), .z 1/(A.w-A.z)
float4 BloomColour             : register(c3);
float4 VignetteInnerRgbPlusMul : register(c4);
float4 VignetteOuterRgbPlusAdd : register(c5);   // .w = the gradient's ADD term
float4 Tint2dColour            : register(c6);
#if BRN_POSTFX_BLUR
float4 BlurMatrixX             : register(c7);
float4 BlurMatrixY             : register(c8);
float4 BlurMatrixW             : register(c9);
#endif
#else
float4 GlobalParams            : register(c0);   // .x = 1 / white level
float4 BloomColour             : register(c1);
float4 VignetteInnerRgbPlusMul : register(c2);
float4 VignetteOuterRgbPlusAdd : register(c3);   // .w = the gradient's ADD term
float4 Tint2dColour            : register(c4);
#if BRN_POSTFX_BLUR
float4 BlurMatrixX             : register(c5);
float4 BlurMatrixY             : register(c6);
float4 BlurMatrixW             : register(c7);
#endif
#endif

sampler2D SamplerSource : register(s0);
sampler2D SamplerBloom  : register(s1);
#if BRN_POSTFX_DOF
sampler2D SamplerDof    : register(s2);
#endif
#if BRN_POSTFX_TINT3D
sampler3D Sampler3dTint : register(s3);
#endif
#if BRN_POSTFX_DOF || BRN_POSTFX_BLUR
sampler2D SamplerDepth  : register(s4);
#endif

#if BRN_POSTFX_BLUR
// ---------------------------------------------------------------------------
// THE MOTION-BLUR CONSTANTS -- every one of them a literal decoded out of the
// microcode's c252..c255 block, not a choice made here.
//
// The dither hash weights (X360 literals 0x3F1E377A / 0x3EC3910D, present in
// all eight blur permutations):
//     `mul r2.zw, |r1.xy|, c254.xy` / `mad r1.x, r2.w, |r1.y|, r2.z`
//     `frc r0.z, r1.x`
// i.e. frac(0.618034 * |px| + 0.381966 * |py| * |py|), the golden-ratio pair.
//
// The cross-axis gradient scale 1/256 (0x3B800000) and the dither centring 0.5
// (0x3F000000) are the other two lanes of the same literal block.
//
// THE ONE CONSTANT THAT SEPARATES BLUR FROM BLURHQ IS THE JITTER SCALE, and
// that is the ONLY difference between the two families.  Diffing the four
// pairs (4 vs 8, 5 vs 9, 6 vs 10, 7 vs 11) instruction by instruction leaves
// exactly one changed value: 0.25 (0x3E800000) becomes 0.0625 (0x3D800000).
// Both are 1/MaxAnisotropy for the sampler BrnPostFxShader::Construct builds
// for that quality -- 4x for E_QUALITY_CHEAP (slots 4..7) and 16x for
// E_QUALITY_EXPENSIVE (slots 8..11) -- and Render binds
// mapSamplerState_MotionBlur[meQuality] on unit 0 whenever blur is on.  The
// jitter is half a hardware tap wide; nothing else about the two families
// differs, and in particular NEITHER is a multi-tap loop.
// ---------------------------------------------------------------------------
#define KF_DITHER_WEIGHT_X      0.618034005f
#define KF_DITHER_WEIGHT_Y      0.381966025f
#define KF_DITHER_CENTRE        0.5f
#define KF_GRADIENT_CROSS_AXIS  0.00390625f     // 1/256
#if BRN_POSTFX_BLUR == 2
#define KF_JITTER_SCALE         0.0625f         // BLURHQ, 16x anisotropic
#else
#define KF_JITTER_SCALE         0.25f           // BLUR,    4x anisotropic
#endif

// [FLAG PC deviation: the console's per-pixel blur mask is the STENCIL byte]
// On the X360 the depth-stencil surface is sampled as an A8R8G8B8 texture, so
// one fetch returns all four bytes of the D24S8 word 0xDDDDDDSS: A = depth
// high, R = depth mid, G = depth low, B = STENCIL.  The blur programs decode
// the depth from A/R/G (see the banner on the depth read) and multiply the
// screen velocity by the B lane -- a per-pixel blur mask living in the stencil
// buffer (`mul r3.xy, r4.xy, r3.x` in permutation 4, `mul r4.xy, r3.xy, r2.w`
// in permutation 6, both reading the lane the depth decode does NOT use).
// A PC raw-depth texture (INTZ / DF24 / DF16, the depthtex group's ladder) has
// no sampleable stencil lane at all -- D3D9 gives a depth texture's .r and
// nothing else -- so the mask is 1.0 here, i.e. every pixel blurs.  DELETE
// WHEN a stencil-readable path exists; until then this is the only motion-blur
// behaviour a PC composite can have, and it is disclosed rather than hidden.
#define KF_MOTION_BLUR_STENCIL_MASK 1.0f
#endif  // BRN_POSTFX_BLUR

float4 mainPS(float4 lUv : TEXCOORD0
#if BRN_POSTFX_BLUR
            , float2 lScreenPosition : VPOS
#endif
             ) : COLOR0
{
#if BRN_POSTFX_DOF || BRN_POSTFX_BLUR
    // ---- the scene depth ---------------------------------------------------
    // [FLAG PC deviation: the depth ENCODING, not the depth semantics]
    // The console reads its depth out of three colour lanes of an A8R8G8B8
    // fetch of the depth-stencil surface:
    //     `dp3 r0.x, depth.<mid,lo,hi>, c.<255/2^24, 255/2^8, 255/2^16>`
    // whose three weights are exactly 255/16777215, 65280/16777215 and
    // 16711680/16777215 (X360 literals 0x377F0001 / 0x3F7F0001 / 0x3B7F0001,
    // byte-identical in all ten permutations that read depth) -- a 24-bit
    // fixed-point reconstruction of D24S8.  On PC the post-fx targets carry a
    // RAW-DEPTH texture (INTZ / DF24 / DF16), whose fetch already returns the
    // normalised depth VALUE in .r, so reproducing the console's three-lane
    // decode here would multiply garbage.  The recovered SEMANTIC -- "the
    // scene's normalised device depth in [0,1]" -- is identical; only the
    // encoding differs, and the difference belongs to the platform, not to
    // this shader.
    //
    // ⚠ THIS IS A HARD DEPENDENCY ON THE RAW-DEPTH LADDER.  Bound to a
    // D24X8 hardware-compare depth texture (what the shadow ladder creates)
    // this fetch returns a 0/1 COMPARISON RESULT, not a depth, and both depth
    // of field and motion blur silently read a binary mask.  See
    // scratch/postfx_step5_wave/BRIEF_depthtex.md.
    float lDepth = tex2D(SamplerDepth, lUv.xy).r;
#endif

    // ---- the source tap ----------------------------------------------------
#if BRN_POSTFX_BLUR
    // CAMERA REPROJECTION.  BlurMatrixX / Y / W are rows of the screen ->
    // previous-screen matrix BrnPostFxShader::Render builds in double
    // precision from the current and previous world-view-projections.  The X
    // and Y rows are four-term; the W row is THREE-term -- BlurMatrixW.w is
    // never read by ANY of the eight blur programs (permutation 4 slots 10/16,
    // permutation 6 slots 10/15: the W accumulator gets uv.x*W.x + uv.y*W.y +
    // W.z*depth and no constant add, while the X and Y accumulators each pick
    // up their .w one instruction later).  Reproduced as written.
    float3 lReprojected;
    lReprojected.x = dot(lUv.xy, BlurMatrixX.xy) + (BlurMatrixX.z * lDepth) + BlurMatrixX.w;
    lReprojected.y = dot(lUv.xy, BlurMatrixY.xy) + (BlurMatrixY.z * lDepth) + BlurMatrixY.w;
    lReprojected.z = dot(lUv.xy, BlurMatrixW.xy) + (BlurMatrixW.z * lDepth);

    // `mad r4.xy, -r3.yyyy, r0.xyyy, r1.xzzz` -- the perspective term is
    // MULTIPLIED THROUGH, not divided out: the console never issues a
    // reciprocal here, so the velocity carries the W factor and the CPU-side
    // matrix scale absorbs it.
    float2 lVelocity = (lReprojected.xy - (lReprojected.z * lUv.xy))
                     * KF_MOTION_BLUR_STENCIL_MASK;

    // The screen-space dither, centred: `subsc0 r0.z, 0.5, r0.z`.
    float lScreenHash = (KF_DITHER_WEIGHT_X * abs(lScreenPosition.x))
                      + (KF_DITHER_WEIGHT_Y * abs(lScreenPosition.y) * abs(lScreenPosition.y));
    float lDither = frac(lScreenHash) - KF_DITHER_CENTRE;

    // THE BLUR IS ONE ANISOTROPIC FETCH, NOT A TAP LOOP.  The console sets the
    // fetch unit's two gradient latches by hand and then issues a single
    // tfetch from SamplerSource:
    //     23: setGradientH <- (velocity.x, velocity.y)
    //     24: setGradientV <- (velocity.y, -velocity.x) * 1/256
    //     26: tfetch r1.xyz, <jittered uv>, tf0
    // The footprint those two gradients span is a sliver 256:1 along the
    // velocity, so the sampler's anisotropic filter integrates the streak in
    // hardware -- which is why Construct builds a 4x and a 16x ANISOTROPIC
    // sampler and Render binds one of them on unit 0 exactly when blur is on.
    // tex2Dgrad is the D3D9 spelling of the same three instructions (texldd).
    float2 lGradientH = lVelocity;
    float2 lGradientV = float2(lVelocity.y, -lVelocity.x) * KF_GRADIENT_CROSS_AXIS;
    float2 lBlurUv    = lUv.xy + (lVelocity * (lDither * KF_JITTER_SCALE));

    float3 lSource = tex2Dgrad(SamplerSource, lBlurUv, lGradientH, lGradientV).rgb;
#else
    // `tfetch r1.xyz_, r0.xy, tf0` -- rgb only.
    float3 lSource = tex2D(SamplerSource, lUv.xy).rgb;
#endif

#if BRN_POSTFX_DOF
    // ---- depth of field ----------------------------------------------------
    // Two ramps out of the four projected focal planes DofParamsA carries, the
    // larger of the two, clamped, scaled by the amount:
    //     `sub r4.x, DofParamsA.y, depth`      (near: blur below plane 1)
    //     `add r4.y, depth, -DofParamsA.z`     (far:  blur above plane 2)
    //     `mul r4.xy, r4.xy, DofParamsB.yz`    (the two 1/delta reciprocals)
    //     `max r0.w, r4.x, r4.y [clamp]`
    //     `mul r0.w, r0.w, DofParamsB.x`       (m_dofAmount)
    // The far ramp's sign is pinned twice: permutation 6 slot 30 writes it as a
    // VECTOR `add r4._y__, r1.xxxx, -c1.zzzz` == depth - DofParamsA.z, and
    // BrnPostFxShader::Render builds DofParamsB.z as 1/(A.w - A.z), which only
    // ramps with (depth - A.z).
    //
    // The blend runs on the SOURCE tap, BEFORE the white-level scale and
    // before bloom (`add r1.xyz, r2.xyz, r1.xzw` sits above the GlobalParams
    // multiply in every DoF permutation), and SamplerDof is fetched at the
    // UNJITTERED uv even when motion blur is on (permutation 6 slot 26 uses
    // r0.xy, the interpolant, while the source fetch uses the jittered pair).
    float3 lDofBlur    = tex2D(SamplerDof, lUv.xy).rgb;
    float  lNearRamp   = (DofParamsA.y - lDepth) * DofParamsB.y;
    float  lFarRamp    = (lDepth - DofParamsA.z) * DofParamsB.z;
    float  lDofBlend   = saturate(max(lNearRamp, lFarRamp)) * DofParamsB.x;

    lSource = lSource + (lDofBlend * (lDofBlur - lSource));
#endif

    lSource = lSource * GlobalParams.x;

    // `tfetch r2.xyz_, r0.xy, tf1` -- rgb only.
    float3 lBloom = tex2D(SamplerBloom, lUv.xy).rgb * BloomColour.rgb;

    // SCREEN BLEND, built as three instructions on the console:
    //   `mul r2.xyz, r1, r3 [clamp]`   -> saturate(source * bloom)
    //   `add r2.xyz, r3, -r2`          -> bloom - that
    //   `add r1.xyz, r2, r1`           -> + source
    float3 lComposite = (lBloom - saturate(lSource * lBloom)) + lSource;

#if BRN_POSTFX_TINT3D
    // ---- the 3D colour-cube tint -------------------------------------------
    // `tfetch r1.xyz_, r1.xyz, tf3` -- the composed colour is the volume
    // texture's COORDINATE and the fetch REPLACES it.  Its position in the
    // chain is pinned: after the screen blend (permutation 1 slot 9 reads the
    // register slot 8 wrote), before the vignette multiply and before the 2D
    // tint add (permutation 1 slot 17 / permutation 3 slot 23 both feed the
    // fetch result into the final mad).  Nothing is premultiplied and nothing
    // is normalised on the way in.
    lComposite = tex3D(Sampler3dTint, lComposite).rgb;
#endif

    // `dp2add r0.x, r0.zw, r0.zw, c(0)` then `sqrt r0.x`.
    float lRadius = sqrt(dot(lUv.zw, lUv.zw));

    // `addsc0 r0.x, VignetteOuterRgbPlusAdd.w, r0.x` with the scalar clamp bit
    // set (the disassembler prints [clamp] on that slot in all twelve).
    float lT = saturate(lRadius + VignetteOuterRgbPlusAdd.w);

    // `muls r1.w, r0.xx` (t*t), `mad r0.x, -r0.x, 2.0f, 3.0f`,
    // `muls_prev r0.x, r0.x` -- the smoothstep polynomial t*t*(3 - 2t).
    float lGradient = (lT * lT) * (3.0f - (2.0f * lT));

    // `mad r0.xyz, r0.xxx, r0.yzw, c.xyz` where r0.yzw == outer - inner.
    float3 lVignette = VignetteInnerRgbPlusMul.rgb
                     + (lGradient * (VignetteOuterRgbPlusAdd.rgb - VignetteInnerRgbPlusMul.rgb));

    // `mad export0.xyz, r1.xyz, r0.xyz, cTint2d.xyz`, and the scalar unit's
    // `retain_prev export0.w` writes the last scalar result.
    //
    // ALPHA IS A DISCLOSED DEVIATION FOR PERMUTATIONS 1..11.  The console never
    // computes the alpha channel: `retain_prev` simply exports whatever the
    // scalar unit last produced, which is the vignette gradient in permutation
    // 0, t*t in permutations 1/2/3, and a scaled velocity component in the
    // eight blur permutations.  Those three values are compiler residue, not
    // an authored output.  Every permutation here writes the gradient -- the
    // value permutation 0 already ships -- so the twelve programs behave
    // identically in a lane the composite's own blend state writes but nothing
    // in this tree reads back.  Reproducing three different kinds of residue
    // would be reproducing the register allocator, not the shader.
    float4 lResult;
    lResult.rgb = (lComposite * lVignette) + Tint2dColour.rgb;
    lResult.a   = lGradient;
    return lResult;
}
