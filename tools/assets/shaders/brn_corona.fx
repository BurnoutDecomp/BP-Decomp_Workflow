// tools/assets/shaders/brn_corona.fx
// ============================================================================
// brn_corona.fx -- the renderengine::CoronaRenderer vertex/pixel program pair
// (the head/tail-light FLARE sprites).
//
// AUTHORED, NOT CONVERTED.  Neither program is in SHADERS.BNDL: both are Xenos
// microcode packages embedded in the X360 executable and handed straight to
// renderengine::ProgramBuffer::Initialize by
// renderengine::CoronaRenderer::Initialize @0x822850F8 --
//   corona vertex  X360 0x8200F2A0  788 B  ucode +0x16C  (64, 360)
//   corona pixel   X360 0x8200F1B8  228 B  ucode +0x0B4  ( 0,  48)
// (the pair after each size is the (literal-block bytes, instruction-stream
// bytes) split the package header's +0x18 field points at; only the vertex
// program has a literal block, and its fourth literal row is c255.)  Both sizes
// are the console's own: Initialize stores 0x314 = 788 and 0xE4 = 228 into the
// ProgramBufferParameters at +0x08 (asm 0x822851B0 / 0x82285134).  The bytes are
// scratch/coronas_step1/DATA_DUMP.md, dumped from ARTIST_copy.i64.
//
// Both were disassembled with tools/assets/shaders/xenos.py -- the decoder
// proved against the X360-vs-PC SHADERS.BNDL pair -- and EVERY ALU line below
// has a numbered counterpart in that disassembly; the full annotated listing is
// scratch/coronas_step1/coronaprogs/work/DECODE.md section 3, and the
// instruction numbers in the comments refer to it.
//
// THE CONSTANT SURFACE IS NOT GUESSED: it is the CTAB interned in each package
// (tools/assets/shaders/ctab.py), and the three vertex names are exactly the
// three strings CoronaRenderer::Initialize resolves through
// renderengine::ProgramBuffer::GetVariableHandleByName (asm 0x82285250 /
// 0x82285268 / 0x82285280, all three against the VERTEX program):
//   vertex : c0 viewProjectionMatrix (float4x4, 4 regs, D3DXPC_MATRIX_ROWS)
//            c4 cameraPositionPlusBrightness (float4)   .xyz camera, .w white level
//            c5 viewXyScale                  (float4)   .xy only
//   pixel  : s0 coronaTexture  (sampler2D)   -- the corona atlas
//
// ".w is the WHITE LEVEL" is not read off the name: CoronaRenderer::Begin
// @0x823FF2C0 publishes those three constants straight out of its
// RenderParameters block -- +0x10 (16 bytes) -> cameraPositionPlusBrightness,
// +0x20 (64 bytes) -> viewProjectionMatrix, +0x60 -> viewXyScale -- and the
// DecFIGS DWARF for that block (rwgcoronarenderer.h) spells the +0x10 member
// `Vector4 m_cameraPositionPlusWhiteLevel`.  Shader name and C++ member name are
// the same field.
//
// /Zpr IS LOAD-BEARING AND PROVEN HERE, not inherited: the console CTAB declares
// viewProjectionMatrix as D3DXPC_MATRIX_ROWS, i.e. register c0 is ROW 0, and the
// microcode's three-mad transform chain (instructions 13-15) combines c0..c3 as
// rows.  fxc's column-major default would transpose it and put every corona
// somewhere else on screen.
//
// VERTEX INPUT.  CoronaRenderer::Initialize builds the declaration inline (asm
// 0x8228528C-0x822852E4): four elements, stream 0, all offsets left at the
// Parameters ctor's 0xFFFF auto-pack sentinel, so they pack in order --
//   element 0  format 0x1A23A6 FLOAT4  elementType 1 -> POSITION0  offset  0
//   element 1  format 0x2A23B9 FLOAT3  elementType 3 -> NORMAL0    offset 16
//   element 2  format 0x1A23A6 FLOAT4  elementType 6 -> TEXCOORD0  offset 28
//   element 3  format 0x014C86 (8_8_8_8 unsigned-normalised, reversed component
//                       order) elementType 4 -> COLOR0             offset 44
//                                                          STRIDE = 48
// -- and 48 is exactly the stride CoronaRenderer::Dispatch @0x82404F30 hands
// D3DDevice_BeginVertices(dev, 13 /*QUADLIST*/, 4*count, 48).  The package's own
// input-signature table (VS +0x148: usages 0/3/5/10 against vfetch slots 4/5/6/7)
// agrees element for element.  Three sources, one layout.
//
// WHAT THE VERTEX CARRIES (Dispatch packs it, per corona, four corners):
//   POSITION .xyz = the corona's world position, .w = its bias distance
//                   (record +0x30, splatted into lane w by vrlimi128)
//   NORMAL        = the corona's facing direction (record +0x10)
//   TEXCOORD .xy  = s_atlasUVs[textureID][corner], .zw = the SIGNED corner
//                   extents (+-record+0x20, +-record+0x24)
//   COLOR0        = the record's RGBA8 colour (record +0x34)
//
// PIXEL-SHADER INTERPOLATOR SEMANTICS -- ONE DELIBERATE PC DEVIATION.  The
// vertex program's two exports are carried as TEXCOORD0/TEXCOORD1 rather than
// TEXCOORD0/COLOR0.  Xenos interpolators are unclamped full-range floats;
// D3D9's COLOR interpolators are permitted to clamp to [0,1] and to drop to
// 8-bit precision.  export1.xyz is colour.rgb * cameraPositionPlusBrightness.w
// -- a WHITE LEVEL that routinely exceeds 1.0 in this engine's HDR chain (see
// the post-fx exposure round trip) -- so a COLOR interpolator would silently
// clip the bright core of every flare.  Both ends of this seam are in this file,
// so nothing outside it depends on the choice.
// ============================================================================


// ---------------------------------------------------------------------------
// VERTEX PROGRAM  (X360 0x8200F2A0)   fxc /T vs_3_0 /E mainCoronaVS /O2 /Zpr
// ---------------------------------------------------------------------------
float4x4 viewProjectionMatrix         : register(c0);   // rows in c0..c3
float4   cameraPositionPlusBrightness : register(c4);
float4   viewXyScale                  : register(c5);

struct CoronaVertexIn
{
    float4 mPositionAndBias : POSITION;    // .xyz world position, .w bias distance
    float3 mDirection       : NORMAL;      // the corona's facing direction
    float4 mUvAndSize       : TEXCOORD0;   // .xy atlas uv, .zw signed corner extents
    float4 mColour          : COLOR0;      // the record's RGBA8, [0,1]
};

struct CoronaVertexOut
{
    float4 mPosition : POSITION;
    float2 mUv       : TEXCOORD0;          // export0
    float4 mColour   : TEXCOORD1;          // export1 (see the interpolator note)
};

CoronaVertexOut mainCoronaVS(CoronaVertexIn lIn)
{
    CoronaVertexOut lOut;

    // [8-11] the unit vector from the corona to the camera.
    //   8 : add r4.xyz, -r2.xyz, c4.xyz     9 : dp3   10 : rsq   11 : mul
    float3 lToCamera =
        normalize(cameraPositionPlusBrightness.xyz - lIn.mPositionAndBias.xyz);

    // [12] mad r5.xyz, r4.xyz, r2.w, r2.xyz -- pull the flare toward the camera
    // by the record's bias distance so it does not z-fight the lamp geometry.
    float3 lWorld = lIn.mPositionAndBias.xyz + lToCamera * lIn.mPositionAndBias.w;

    // [13-15] the three-mad row-major transform (see DECODE.md 3.1: the console
    // keeps the result as r2 = clip.zxyw and reads it back rotated at 16/25).
    float4 lClip = mul(float4(lWorld, 1.0f), viewProjectionMatrix);

    // [17] mad r3.x, -r2.w, c255.x(-1.5), r2.z  ==  clip.y + 1.5*clip.w.
    // In NDC that is the offset from the point (0, -1.5), i.e. 1.5 units below
    // screen centre: the flare is oriented radially away from that point.
    float lRadialY = lClip.y + 1.5f * lClip.w;

    // [18 scalar, 19, 20 scalar] the 2D length and its reciprocal, [21,22] the
    // unit radial direction.  (The console computes rsqrt then two muls.)
    float  lInvLength = rsqrt(lClip.x * lClip.x + lRadialY * lRadialY);
    float2 lRadial    = float2(lClip.x, lRadialY) * lInvLength;   // (rx, ry)

    // [23,24] the corner offset in the flare's own frame: .z scales the radial
    // axis (rx,ry), .w scales its perpendicular (ry,-rx).
    float2 lOffset = float2(lRadial.y * lIn.mUvAndSize.w + lRadial.x * lIn.mUvAndSize.z,
                            lRadial.y * lIn.mUvAndSize.z - lRadial.x * lIn.mUvAndSize.w);

    // [25] mad export62.xy, offset, c5.xy, clip.xy   and   [16] export62.zw = clip.zw.
    // The offset is added in CLIP space, so it shrinks as 1/w with distance.
    lOut.mPosition = float4(lClip.xy + lOffset * viewXyScale.xy, lClip.z, lClip.w);

    // [18 vector] dp3 r3.z, r4.xyz, direction   [20 vector] mul_sat by c255.y.
    // A flare facing away from the camera fades to nothing.
    float lFade = saturate(dot(lToCamera, lIn.mDirection) * 1.154701f);

    // [27] export0 = the atlas uv.
    lOut.mUv = lIn.mUvAndSize.xy;

    // [28] export1.xyz = colour.rgb * white level;  [26] export1.w = colour.a * fade.
    lOut.mColour = float4(lIn.mColour.rgb * cameraPositionPlusBrightness.w,
                          lIn.mColour.a * lFade);

    return lOut;
}


// ---------------------------------------------------------------------------
// PIXEL PROGRAM  (X360 0x8200F1B8)   fxc /T ps_3_0 /E mainCoronaPS /O2 /Zpr
//
// The whole console program is two instructions:
//     1 : tfetch  r0.xyzw, r0.xy, tf0
//     2 : mul     export0.xyzw, r0.xyzw, r1.xyzw
// No alpha test, no kill, no clamp -- the pass is additive with the depth test
// on and depth writes off (BrnCoronaManager::Construct's three state captures).
// ---------------------------------------------------------------------------
sampler2D coronaTexture : register(s0);

float4 mainCoronaPS(float2 lUv     : TEXCOORD0,
                    float4 lColour : TEXCOORD1) : COLOR0
{
    return tex2D(coronaTexture, lUv) * lColour;
}
