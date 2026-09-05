// tools/assets/shaders/brn_im2dblit.fx
// ============================================================================
// brn_im2dblit.fx -- the FOUR BrnRendererMemory blit programs: the DEPTH-blit
// pair (BlitDepth @0x82406EA8) and the COMPOSITE-blit pair (BlitComposite
// @0x82406A68).
//
// AUTHORED, NOT CONVERTED.  None of the four is in SHADERS.BNDL: all four are
// Xenos microcode packages embedded in the X360 executable and handed straight
// to renderengine::ProgramBuffer::Initialize by BrnRendererMemory::Construct
// @0x823FCA38 --
//   depth     vertex  X360 0x8203DAA8  340 B  ucode +0x0DC  (  0, 120)
//   depth     pixel   X360 0x8203DC00  236 B  ucode +0x0B0  (  0,  60)
//   composite vertex  X360 0x8203DCF0  400 B  ucode +0x118  (  0, 120)
//   composite pixel   X360 0x8203DE80  508 B  ucode +0x12C  ( 64, 144)
// (the pair after each size is the (literal-block bytes, instruction-stream
// bytes) split; only the composite PIXEL program has a literal block, and its
// one live literal is c255 = {0.5, 0, 0, 0}.)  All four sizes are the console's
// own -- they are the four KU_*_BLIT_*_SIZE words already committed in
// b5-decomp GameSource/Graphics/BrnRendererMemory.cpp:207-210.
//
// All four were disassembled with tools/assets/shaders/xenos.py and every ALU
// line below carries the instruction number of its counterpart.
//
// THE CONSTANT SURFACE IS NOT GUESSED: it is the CTAB interned in each package
// (tools/assets/shaders/ctab.py):
//   depth     vertex : c0 gOffsetXYZ  c1 gRightUp
//   depth     pixel  : s0 DiffuseSampler (sampler2D)
//   composite vertex : c0 gOffsetXYZ  c1 gRightUp  c2 gUVOffsets  c3 gUVScales
//   composite pixel  : c0 gQuincunxOffsets   s0 BaseSampler  s1 OverlaySampler
// and "gUVOffsets" / "gUVScales" / "gQuincunxOffsets" are exactly the three
// strings BlitComposite resolves through
// renderengine::ProgramBuffer::GetVariableHandleByName.
//
// ============================================================================
// THE CONSOLE DISASSEMBLY, instruction for instruction
// ============================================================================
// DEPTH VERTEX (0x8203DAA8 +0x0DC)
//   3 : vfetch  r0._xy_, vf31           -- the Im2d vertex's screen x,y
//   4 : max     export62.___w, r0, r0   -- position.w = 1 (export overlap)
//   4   maxs    export62.__zw, c0.zz    -- position.z = gOffsetXYZ.z
//   5 : dp2add  export62.x___, r0.zyyy, c1.zxxx, c0.xxxx
//   6 : dp2add  export62._y__, r0.zyyy, c1.wyyy, c0.yyyy
//   7 : vfetch  r0.xy__, vf31           -- the same two words again
//   8 : max     export0.xy__, r0.xyyy, r0.xyyy   -- texcoord0 = the raw xy
//
// DEPTH PIXEL (0x8203DC00 +0x0B0)
//   1 : tfetch  r0.x___, r0.xy, tf0     -- DiffuseSampler, the SOURCE DEPTH
//   2 : sgts    export0.x___, -r0'.xx   -- colour  = (-depth > 0)
//   3 : maxs    export61.x___, r0.xx [clamp]  -- export61 IS oDepth on Xenos
//
// COMPOSITE VERTEX (0x8203DCF0 +0x118) -- identical to the depth vertex except
// for the last instruction:
//   8 : mad     export0.xyzw, r0.xyxy, c3.xyzw, c2.xyzw
//       i.e. texcoord0 = vertexXY.xyxy * gUVScales + gUVOffsets, so .xy is the
//       BaseSampler uv and .zw is the OverlaySampler uv.
//
// COMPOSITE PIXEL (0x8203DE80 +0x12C)
//   literal c255 = {0.5, 0, 0, 0}
//   2 : add     r1.xy__, r0.xyyy,  c0.xyyy    -- +gQuincunxOffsets
//   3 : add     r1.__zw, r0.xxxy, -c0.xxxy    -- -gQuincunxOffsets
//   4 : tfetch  r0.xyzw, r0.zwz, tf1          -- OverlaySampler (PARTICLES)
//   5 : tfetch  r2.xyz_, r1.zwz, tf0          -- BaseSampler tap A (SCENE)
//   6 : tfetch  r1.xyz_, r1.xyx, tf0          -- BaseSampler tap B (SCENE)
//   7 : add     r1.xyz_, r2.xyzz, r1.xyzz
//   8 : mul     r1.xyz_, r1.xyzz, c255.xxxx   -- (A+B) * 0.5, the AA average
//   9 : add     r0.xyz_, r1.xyzz, r0.xyzz
//  10 : mad     export0.xyzw, -r1.xyzz, r0.wwww, r0.xyzz
//       export0.w = 1.0 (export overlap)
//   ==> out.rgb = scene*(1 - particleAlpha) + particleRGB      (a premultiplied
//       OVER), out.a = 1.0.
//
// ============================================================================
// ⚠ TWO DELIBERATE PC DEVIATIONS IN THE COMPOSITE PIXEL PROGRAM.  Both are
// forced by Direct3D 9 rules the Xenos does not have, both are named at the
// call site in BrnRendererMemory::BlitComposite, and both are algebra, not
// taste.
//
// (1) THE SCENE IS NOT SAMPLED; THE BLEND UNIT SUPPLIES ITS TERM.
//     On the X360 the render target is an EDRAM tile and BaseSampler reads the
//     RESOLVED COPY of the same buffer in main memory -- two different pieces
//     of memory, so sampling the destination is legal and the trailing
//     RenderTarget::Resolve @0x823F9338 copies the result back over it.  On PC
//     the down-sample target's texture IS the surface being rendered into
//     (PostFxRenderTargetPCLeaf.cpp:1456-1466 creates one D3DUSAGE_RENDERTARGET
//     texture and binds its level-0 surface; Resolve() is a documented no-op),
//     and D3D9 gives an undefined result for a texture sampled while bound.
//     So the identity
//         out = scene*(1 - a) + particleRGB
//              == blend( src = particleRGB, srcFactor = ONE,
//                        dst = scene,       dstFactor = INVSRCALPHA )
//     is used instead: the pixel program returns the particle sample and the
//     ROP performs the same arithmetic on the destination it is already
//     reading.  The particle term is bit-identical; what is dropped is the
//     scene's own two-tap quincunx average (instructions 5-8 above), which is
//     the Xenos AA reconstruction filter -- on this backend ResolveMSAA has
//     already performed a real D3D9 multisample resolve, so re-applying a
//     +/-0.166-texel two-tap blur here would be a SECOND filter, not the
//     console's one.  gQuincunxOffsets is therefore unused on PC and is not
//     declared (an undeclared constant is the honest spelling: a declared-but-
//     dead one would leave a handle lookup that silently succeeds).
//
// (2) THE ALPHA LANE IS NOT WRITTEN.  The console's export0.w is a hard 1.0
//     and blend slot 0 writes all four channels, which costs it nothing
//     because its cars-vs-world motion-blur mask lives in the STENCIL buffer.
//     This backend has no way to sample a stencil plane, so
//     renderengine::PCStampMotionBlurMask carries that mask in the SCENE
//     TARGET'S ALPHA (BrnRendererModule.cpp:4714-4735) -- the very lane this
//     pass would overwrite.  BlitComposite therefore sets COLORWRITEENABLE to
//     RGB only.  Stated here because a silent alpha write would break motion
//     blur with nothing in any log.
// ============================================================================
//
// VERTEX INPUT.  The console draws both blits through
// CgsGraphics::Basic2dColouredTexturedVertex_::Render -- a 20-byte
// {float2 pos, u32 colour, float2 uv} vertex through the Im2d renderer, whose
// vertex program maps pos through gOffsetXYZ/gRightUp.  The PC Im2d
// (CgsIm2d.cpp:150-193) is the FIXED-FUNCTION 2D GUI path: it selects the
// fixed-function pipeline, rewrites every vertex from 1280x720 logical
// coordinates, and cannot carry a bound vertex/pixel program pair at all.  So
// the blits are drawn the way BrnSunCorona::GenerateOcclusionBuffer already
// draws its own full-screen quad on this backend -- D3DDevice_BeginVertices
// with an explicit descriptor -- and the quad arrives in NDC, which makes
// gOffsetXYZ/gRightUp (the Im2d transform) dead.  They are not declared.
// The declaration is the sun corona's, value for value:
//   element 0  stream 0  format 0x2A23B9 FLOAT3  elementType 1 -> POSITION0  offset  0
//   element 1  stream 0  format 0x2C23A5 FLOAT2  elementType 6 -> TEXCOORD0  offset 12
//                                                                  STRIDE = 20
//
// Build recipe (identical to convert_shaders_bundle.py::compile_entry):
//     fxc /nologo /T vs_3_0 /E mainIm2dDepthBlitVS     /O2 /Zpr ...
//     fxc /nologo /T ps_3_0 /E mainIm2dDepthBlitPS     /O2 /Zpr ...
//     fxc /nologo /T vs_3_0 /E mainIm2dCompositeBlitVS /O2 /Zpr ...
//     fxc /nologo /T ps_3_0 /E mainIm2dCompositeBlitPS /O2 /Zpr ...
// ============================================================================

// ---------------------------------------------------------------------------
// THE DEPTH BLIT
// ---------------------------------------------------------------------------

sampler2D DiffuseSampler : register(s0);   // the SOURCE target's depth texture

struct DepthBlitVSIn
{
    float3 mPosition : POSITION0;   // NDC (see the VERTEX INPUT note above)
    float2 mUv       : TEXCOORD0;
};

struct DepthBlitVSOut
{
    float4 mPosition : POSITION;
    float2 mUv       : TEXCOORD0;
};

// instructions 3-8: position from the vertex, texcoord0 = the raw vertex uv
// (`max export0.xy__, r0.xyyy, r0.xyyy` is a pure copy).
DepthBlitVSOut mainIm2dDepthBlitVS(DepthBlitVSIn lIn)
{
    DepthBlitVSOut lOut;
    lOut.mPosition = float4(lIn.mPosition, 1.0f);
    lOut.mUv       = lIn.mUv;
    return lOut;
}

struct DepthBlitPSOut
{
    float4 mColour : COLOR0;
    float  mDepth  : DEPTH;
};

// instructions 1-3.  export61 is the Xenos depth export, so the whole program
// is "write the sampled depth as this fragment's depth"; the colour export is
// `sgts export0.x, -depth`, which is 0 for every non-negative depth and is
// masked off anyway (BlitDepth binds blend slot 7,
// eFactoryBlendState_NoColourWrite_NoAlphaTest, COLORWRITEENABLE = 0).
DepthBlitPSOut mainIm2dDepthBlitPS(float2 lUv : TEXCOORD0)
{
    DepthBlitPSOut lOut;
    const float lfDepth = tex2D(DiffuseSampler, lUv).r;
    lOut.mDepth  = saturate(lfDepth);
    lOut.mColour = float4(0.0f, 0.0f, 0.0f, 0.0f);
    return lOut;
}

// ---------------------------------------------------------------------------
// THE COMPOSITE BLIT
// ---------------------------------------------------------------------------

float4 gUVOffsets : register(c2);   // (base u,v half-texel, overlay u,v half-texel)
float4 gUVScales  : register(c3);   // (base u,v scale,      overlay u,v scale)

sampler2D OverlaySampler : register(s1);   // the QUARTER-RES PARTICLE BUFFER

struct CompositeBlitVSIn
{
    float3 mPosition : POSITION0;
    float2 mUv       : TEXCOORD0;
};

struct CompositeBlitVSOut
{
    float4 mPosition : POSITION;
    float4 mUv       : TEXCOORD0;   // .xy base uv, .zw overlay uv
};

// instruction 8: `mad export0.xyzw, r0.xyxy, c3.xyzw, c2.xyzw`.
CompositeBlitVSOut mainIm2dCompositeBlitVS(CompositeBlitVSIn lIn)
{
    CompositeBlitVSOut lOut;
    lOut.mPosition = float4(lIn.mPosition, 1.0f);
    lOut.mUv       = lIn.mUv.xyxy * gUVScales + gUVOffsets;
    return lOut;
}

// instructions 4 and 10, with the scene term re-associated onto the ROP and the
// alpha lane left alone -- see the two deviation notes in the banner.
float4 mainIm2dCompositeBlitPS(float4 lUv : TEXCOORD0) : COLOR0
{
    return tex2D(OverlaySampler, lUv.zw);
}
