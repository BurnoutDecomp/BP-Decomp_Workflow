// =============================================================================
// brn_lionblend.fx -- the Lion particle blend program pairs (PC platform leaf).
//
// The X360 title embeds FOUR Xenos microcode packages in the executable and
// hands them to BrnGraphics::Im3dBlend::Construct @0x8229B260, which builds a
// two-program ImRenderer<BrnGraphics::LionBlendVertex>:
//
//   program 0  "LionBlended"       vertex unk_8200DD58 (0x1A4)  pixel unk_8200DF00 (0x10C)
//   program 1  "LionBlendedZFade"  vertex unk_8200E010 (0x220)  pixel unk_8200E230 (0x1F8)
//
// (The four blob addresses and their sizes are the literal immediates in
// Construct's own prologue: `addi r27, r10, unk_8200DD58-unk_8200E230` ..
// `li r10, 0x1F8` / `li r27, 0x1A4` / `li r27, 0x10C` / `li r27, 0x220`, stored
// into the four parallel stack arrays r5/r6/r7/r8 with r9 = 2 programs.)
//
// Each package was read out of the image with tools/re/x360rd.py, split at its
// header's +0x04 microcode offset / +0x08 size, disassembled with
// tools/assets/shaders/xenos.py and named with tools/assets/shaders/ctab.py.
// This file is that disassembly written back as HLSL. No visual oracle was used.
//
// CTAB (the console's own constant table -- these are the eight names
// Im3dBlend::Construct resolves with ProgramBuffer::GetVariableHandleByName):
//   program 0 vs : worldViewProj c0..c3 (matrix_rows), colourScale c4
//   program 0 ps : DiffuseSampler s0
//   program 1 vs : worldViewProj c0..c3, colourScale c4, gScale c5 (float3),
//                  gOffset c6 (float3)
//   program 1 ps : gDepthConversion c0, gDepthFadeConstants c1,
//                  DiffuseSampler s0, DepthSampler s1
//
// -----------------------------------------------------------------------------
// THE XENOS LISTINGS, verbatim (xenos.py; export62 == oPos, export0..2 are the
// three interpolators the pixel shader reads back as r0/r1/r2).
//
// program 0 vertex (0x9C bytes of stream, no literal block):
//    3 : vfetch r2.xyzw, r0.yxx, vf31          element 0  POSITION0 (float4)
//    4 : vfetch r1.xyzw, r0.yxx, vf31          element 1  COLOR0    (ubyte4n)
//    5 : vfetch r0.xyzw, r0.yxx, vf31          element 2  TEXCOORD0 (float4)
//    6 : mad   r3, r2.zzzz, c2, c3
//    7 : mad   r3, r2.yyyy, c1.xzyw, r3.xzyw
//    8 : mad   export62, r2.xxxx, c0, r3.xzyw  oPos = float4(pos.xyz,1) * worldViewProj
//    9 : max   export1.____, r0, r0            (vector half writes NOTHING)
//    9   maxs  export1.x___, r2.ww             oT1.x = position.w == the frame blend weight
//   10 : max   export0.xyzw, r0, r0            oT0   = the two packed uv pairs
//   11 : mul   export2.xyzw, r1, c4            oT2   = colour * colourScale
//
// program 0 pixel (0x54):
//    1 : tfetch r3, r0.zwz, tf0                NEXT frame  (uv.zw)
//    2 : tfetch r0, r0.xyx, tf0                CURRENT frame (uv.xy)
//    3 : add    r3, r3, -r0
//    4 : mad    r0, r3, r1.xxxx, r0            lerp(current, next, blend)
//    5 : mul    export0, r0, r2                * colour
//
// program 1 vertex (0xCC):
//    3 : vfetch r3.xyzw   POSITION0     4 : vfetch r1.xyzw  COLOR0
//    5 : vfetch r2.xyzw   TEXCOORD0
//    6 : mad   r0, r3.zzzz, c2, c3
//    7 : mad   r0, r3.yyyy, c1.xzyw, r0.xzyw
//    8 : mad   r0, r3.xxxx, c0.wxyz, r0.wxzy   (the .w lane rotates into r0.x)
//    9 : max   export62, r0.yzwx, r0.yzwx      oPos, un-rotated
//   10 : rcp   r0.x___, r0.x                   1 / clip.w
//   11 : max   export1.____, r0, r0
//   11   maxs  export1.___w, r3.ww             oT1.w = position.w == the blend weight
//   12 : max   export0.xyzw, r2, r2            oT0   = the two uv pairs
//   13 : mul   r0.xyz_, r0.yzww, r0.xxxx       ndc = clip.xyz / clip.w
//   14 : mul   export2.xyzw, r1, c4            oT2   = colour * colourScale
//   15 : mad   export1.xyz_, r0.xyzz, c5, c6   oT1.xyz = ndc * gScale + gOffset
//
// program 1 pixel (0xC0):
//    2 : tfetch r3.xy1w, r1.xyx, tf1           depth texel; the .z LANE IS A LITERAL 1.0
//    3 : tfetch r4, r0.zwz, tf0                NEXT frame
//    4 : tfetch r0, r0.xyx, tf0                CURRENT frame
//    5 : add    r4, r4, -r0
//    6 : dp4    r3._y__, r3.zywx, c0.wzxy      D = 1*gDC.w + d.y*gDC.z + d.w*gDC.x + d.x*gDC.y
//    7 : mul    r3.x___, r3.yyyy, r1.zzzz      D * vertexDepth
//    8 : mad    r0, r4, r1.wwww, r0            lerp(current, next, blend)
//    9 : mul    export0.xyz_, r0.xyzz, r2.xyzz rgb = texel.rgb * colour.rgb
//   10 : add    r1.x___, -r3.yyyy, r1.zzzz     vertexDepth - D
//   10   rcp    r2._y__, r3.x                  1 / (D * vertexDepth)
//   11 : mulsc0 r1._y__, c1.x * r2.y           gDepthFadeConstants.x / (D * vertexDepth)
//   12 : mul    r1.x___, r1.yyyy, r1.xxxx [clamp]
//   13 : mul    r2.x___, r1.xxxx, r2.wwww      * colour.a
//   14 : mul    export0.___w, r2.xxxx, r0.wwww * texel.a
//
// -----------------------------------------------------------------------------
// WHY THE Z-FADE ARITHMETIC IS A SOFT-PARTICLE FADE, derived, not guessed.
// Im3dBlend::BeginRendering @0x82282060 pushes
//     gOffset            = { halfTexelU + 0.5, halfTexelV + 0.5, zFar, 0 }
//     gScale             = { 0.5, -0.5, zNear - zFar, 0 }
//     gDepthConversion   = { R*255/256, R*255/65536, R*255/16777216, zFar }   R = zNear - zFar
//     gDepthFadeConstants= { (zNear * zFar) / depthRange, 0, 0, 0 }
// so oT1.xy is the standard D3D ndc->normalised-screen-uv map with the half
// texel bias, and both `D` (from the depth texel) and oT1.z (from ndc.z) are
// g(z) = zFar + (zNear - zFar) * z. Substituting the projection's own
// z = F/(F-N) * (1 - N/zview) makes the constant term vanish exactly, leaving
// g = F*N / zview. The pixel shader's (gDFC.x / (D*vz)) * (vz - D) is therefore
//     (N*F/depthRange) * (1/D - 1/vz) == (zScene - zParticle) / depthRange,
// saturated: a soft-particle depth fade over `depthRange` world units. That
// identity is what pins every constant above; nothing here is tuned.
//
// FLAG PC-platform leaf: the depth TEXEL packing (channels w / x / y as the
// 1, 1/256, 1/65536 bytes, with the literal 1.0 in the .z lane paying for the
// zFar term) is the Xenos depth-surface channel order. The dot product below
// reproduces the console's weave byte-for-byte; a PC scene-depth source that
// packs its bytes into different channels must be fixed where it is PRODUCED,
// not by re-weaving this dot.
//
// Build recipe (identical to pc/gcm/renderengine/SkidProgramsPC.cpp):
//   fxc /nologo /T vs_3_0 /E vs_main  /O2 /Zpr /Fo lionblend_vs.fxo    brn_lionblend.fx
//   fxc /nologo /T ps_3_0 /E ps_main  /O2 /Zpr /Fo lionblend_ps.fxo    brn_lionblend.fx
//   fxc /nologo /T vs_3_0 /E vs_zfade /O2 /Zpr /Fo lionblendz_vs.fxo   brn_lionblend.fx
//   fxc /nologo /T ps_3_0 /E ps_zfade /O2 /Zpr /Fo lionblendz_ps.fxo   brn_lionblend.fx
//   -> tools/assets/shaders/shader_transcode.py :: build_pc_program_buffer()
//   -> b5-decomp/src/pc/gcm/renderengine/LionBlendProgramsPC.cpp
// =============================================================================

// ---- vertex constants (both programs share c0..c4) --------------------------
float4x4 worldViewProj : register(c0);
float4   colourScale   : register(c4);
// ---- vertex constants, program 1 only ---------------------------------------
float3   gScale        : register(c5);
float3   gOffset       : register(c6);

// ---- pixel constants, program 1 only ----------------------------------------
float4   gDepthConversion    : register(c0);
float4   gDepthFadeConstants : register(c1);

sampler2D DiffuseSampler : register(s0);
sampler2D DepthSampler   : register(s1);

// The 36-byte BrnGraphics::LionBlendVertex, as the three vertex-descriptor
// elements ImRenderer<LionBlendVertex>::Construct @0x8228E890 declares:
//   element 0  in-stream +0   type 0x1A23A6 (float4)  element type 1 -> POSITION0
//   element 1  in-stream +16  type 0x014C86 (ubyte4n) element type 4 -> COLOR0
//   element 2  in-stream +20  type 0x1A23A6 (float4)  element type 6 -> TEXCOORD0
struct VS_IN
{
    float4 pos    : POSITION0;   // .xyz position, .w = the inter-frame blend weight
    float4 colour : COLOR0;      // packed RGBA8, overbright (the writer scales rgb by 511)
    float4 uv     : TEXCOORD0;   // (u,v) of the CURRENT frame, (u,v) of the NEXT frame
};

// Both interpolator sets carry the colour on a TEXCOORD, not a COLOR: the
// console's interpolators are full floats and colourScale is free to push the
// product past 1.0, which a D3D9 COLOR interpolator would clamp away.
struct VS_OUT
{
    float4 pos    : POSITION;
    float4 uv     : TEXCOORD0;   // export0
    float  blend  : TEXCOORD1;   // export1.x  (the vector half of slot 9 writes nothing)
    float4 colour : TEXCOORD2;   // export2
};

struct VS_OUT_ZFADE
{
    float4 pos    : POSITION;
    float4 uv     : TEXCOORD0;   // export0
    float4 fade   : TEXCOORD1;   // export1 : .xy screen uv, .z depth, .w blend weight
    float4 colour : TEXCOORD2;   // export2
};

// =============================================================================
// program 0 -- LionBlended
// =============================================================================
VS_OUT vs_main(VS_IN i)
{
    VS_OUT o;
    // slots 6-8: pos.x*c0 + pos.y*c1 + pos.z*c2 + c3 (the .xzyw swizzles cancel).
    o.pos    = mul(float4(i.pos.xyz, 1.0f), worldViewProj);
    // slot 10.
    o.uv     = i.uv;
    // slot 9, scalar half.
    o.blend  = i.pos.w;
    // slot 11.
    o.colour = i.colour * colourScale;
    return o;
}

float4 ps_main(VS_OUT i) : COLOR
{
    // slots 1-4: cross-fade the atlas cell against the next frame's cell.
    float4 lCurrent = tex2D(DiffuseSampler, i.uv.xy);
    float4 lNext    = tex2D(DiffuseSampler, i.uv.zw);
    // slot 5.
    return lerp(lCurrent, lNext, i.blend) * i.colour;
}

// =============================================================================
// program 1 -- LionBlendedZFade
// =============================================================================
VS_OUT_ZFADE vs_zfade(VS_IN i)
{
    VS_OUT_ZFADE o;
    // slots 6-9.
    float4 lClip = mul(float4(i.pos.xyz, 1.0f), worldViewProj);
    o.pos = lClip;

    // slots 10 / 13: the perspective divide, done in the vertex shader.
    float3 lNdc = lClip.xyz / lClip.w;

    // slot 15: ndc -> normalised screen uv (xy) and the linearisable depth (z).
    o.fade.xyz = lNdc * gScale + gOffset;
    // slot 11, scalar half.
    o.fade.w   = i.pos.w;
    // slot 12.
    o.uv       = i.uv;
    // slot 14.
    o.colour   = i.colour * colourScale;
    return o;
}

float4 ps_zfade(VS_OUT_ZFADE i) : COLOR
{
    // slot 2. The .z lane of the fetch is the literal 1.0 that pays for the
    // gDepthConversion.w (== zFar) term of the dot below.
    float4 lDepthTexel = tex2D(DepthSampler, i.fade.xy);

    // slots 3-5, 8.
    float4 lCurrent = tex2D(DiffuseSampler, i.uv.xy);
    float4 lNext    = tex2D(DiffuseSampler, i.uv.zw);
    float4 lTexel   = lerp(lCurrent, lNext, i.fade.w);

    // slot 6, lane for lane: (1, d.y, d.w, d.x) . (gDC.w, gDC.z, gDC.x, gDC.y).
    float lSceneDepth = dot(float4(1.0f, lDepthTexel.y, lDepthTexel.w, lDepthTexel.x),
                            float4(gDepthConversion.w, gDepthConversion.z,
                                   gDepthConversion.x, gDepthConversion.y));

    // slots 7 / 10-12: saturate( K * (particleDepth - sceneDepth) / (sceneDepth * particleDepth) ).
    float lFade = saturate((gDepthFadeConstants.x / (lSceneDepth * i.fade.z))
                           * (i.fade.z - lSceneDepth));

    // slots 9 / 13 / 14: the fade lands on ALPHA only.
    float4 o;
    o.rgb = lTexel.rgb * i.colour.rgb;
    o.a   = (lFade * i.colour.a) * lTexel.a;
    return o;
}
