// =============================================================================
// brn_im3d.fx -- CgsGraphics::Im3d's program 0, the TEXTURED immediate-mode 3D
// pair (PC platform leaf).
//
// The X360 title embeds four programs in the executable and hands them to
// CgsGraphics::Im3d::Construct @0x827FC748 as two {vertex, pixel} pairs:
//     program 0   vertex unk_820D4090 (352 B)   pixel unk_820D41F0 (228 B)
//     program 1   vertex unk_820D44B8 (384 B)   pixel unk_820D4638 (1112 B)
// Program 1 is the STENCIL-MASK variant (Construct looks up "gvMaskUseFlags" on
// its buffers; Im3d::PushMask @0x827DCF78 binds mi8CurrentProgram + 1). Only
// program 0 is re-authored here -- it is the one every ordinary Im3d draw uses,
// including BrnParticle::Native::SparkRenderer::Dispatch @0x8228BBC8.
//
// Both halves were disassembled with tools/assets/shaders/xenos.py and the
// constant names read out of their CTABs with tools/assets/shaders/ctab.py;
// no visual oracle was used.
//
//   vertex (5 ALU slots after three vfetches):
//      3  vfetch r3.xyz_, r0.yxx, vf31        position   (element type 1)
//      4  vfetch r1.xyzw, r0.yxx, vf31        colour     (element type 4)
//      5  vfetch r0.xy__, r0.yxx, vf31        uv         (element type 6)
//      6  mad r2, r3.zzzz, c2, c3
//      7  mad r2, r3.yyyy, c1.xzyw, r2.xzyw
//      8  mad export62, r3.xxxx, c0, r2.xzyw  oPos = pos * worldViewProj
//      9  max export0.xy, r0.xyyy, r0.xyyy    oTex0   = uv
//     10  max export1, r1.xyzw, r1.xyzw       oColour = colour
//   pixel (2 slots):
//      1  tfetch r0.xyzw, r0.xyx, tf0
//      2  mul export0, r0.xyzw, r1.xyzw       tex2D(DiffuseSampler, uv) * colour
//
//   CTAB (vertex): worldViewProj  float4 reg 0 x4  matrix_rows float[4x4]
//   CTAB (pixel):  DiffuseSampler sampler reg 0 x1 sampler2D
//
// The two `max r, x, x` slots are the Xenos idiom for a MOV (the vector unit has
// no mov); they are pass-throughs and are written as such.
//
// The vertex stream is CgsGraphics::BasicColouredTexturedVertex -- FLOAT3
// position at +0, packed RGBA8 colour at +12, FLOAT2 UV at +16, stride 24 --
// and ImRenderer<BasicColouredTexturedVertex>::Construct declares its three
// elements with usage POSITION0 / COLOR0 / TEXCOORD0 (the +0x9 usage lane reads
// 0 / 10 / 5), which is what the semantics below must match.
//
// Build (identical recipe to brn_skid.fx; /Zpr is load-bearing -- it keeps the
// matrix row-major so the four mad rows stay c0..c3 in order):
//   fxc /nologo /T vs_3_0 /E vs_main /O2 /Zpr /Fo im3d_vs.fxo brn_im3d.fx
//   fxc /nologo /T ps_3_0 /E ps_main /O2 /Zpr /Fo im3d_ps.fxo brn_im3d.fx
//   -> tools/assets/shaders/shader_transcode.py :: build_pc_program_buffer()
//   -> b5-decomp/src/pc/gcm/renderengine/Im3dProgramsPC.cpp
// =============================================================================

float4x4 worldViewProj : register(c0);

sampler2D DiffuseSampler : register(s0);

struct VS_IN
{
    float3 pos    : POSITION0;    // BasicColouredTexturedVertex::mv3Pos    +0x00
    float4 colour : COLOR0;       // BasicColouredTexturedVertex::mv4Colour +0x0C (RGBA8)
    float2 uv     : TEXCOORD0;    // BasicColouredTexturedVertex::mv2Tex0UV +0x10
};

struct VS_OUT
{
    float4 pos    : POSITION;
    float2 uv     : TEXCOORD0;    // export0.xy
    float4 colour : COLOR0;       // export1
};

VS_OUT vs_main(VS_IN i)
{
    VS_OUT o;
    // slots 6-8: pos.x * c0 + pos.y * c1 + pos.z * c2 + c3. (The .xzyw swizzles
    // on slot 7 are undone by slot 8's; the net is the plain row-vector product.)
    o.pos    = mul(float4(i.pos, 1.0f), worldViewProj);
    o.uv     = i.uv;        // slot 9
    o.colour = i.colour;    // slot 10
    return o;
}

float4 ps_main(VS_OUT i) : COLOR0
{
    return tex2D(DiffuseSampler, i.uv) * i.colour;
}
