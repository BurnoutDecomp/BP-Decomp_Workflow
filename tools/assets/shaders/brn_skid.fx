// =============================================================================
// brn_skid.fx -- the skid / tyre-mark decal program pair (PC platform leaf).
//
// The X360 title embeds this pair in the executable (guest .rdata unk_8200E9D0,
// 456 bytes, vertex; unk_8200EB98, 228 bytes, pixel) and hands it to
// BrnGraphics::Im3dSkidsRenderer::Construct @0x82295150. Both were disassembled
// with tools/assets/shaders/xenos.py (2026-09-02); this file is that
// disassembly written back as HLSL -- no visual oracle was used:
//
//   vertex (12 ALU slots):
//     3  vfetch r2.xyz, r0.y, vf31            position          (element type 1)
//     4  vfetch r1.xyzw, r0.y, vf31           uv / time / alpha (element type 6)
//     5  mad r0, r2.zzzz, c2, c3
//     6  mad r0, r2.yyyy, c1.xzyw, r0.xzyw
//     7  mad export62, r2.xxxx, c0, r0.xzyw   oPos = pos * gWorldViewProj (row vector, rows c0..c3)
//     8  add r0, c5, -c4
//     9  mad r0, r0, r1.zzzz, c4              colour = lerp(gStartColour, gEndColour, TIME)
//    10  mul export1.w, r0.w, r1.w            oColour.a = colour.a * ALPHA (skid strength)
//    11  max export0.xy, r1.xy, r1.xy         oTex0 = uv
//    12  max export1.xyz, r0.xyz, r0.xyz      oColour.rgb = colour.rgb
//   pixel (2 slots):
//     1  tfetch r0, r0.xy, tf0
//     2  mul export0, r0, r1                  tex2D(sampler0, uv) * colour
//
// Constant registers follow the console's (the descriptor table is rebuilt from
// this file's CTAB so the engine binds by NAME; the register pins are only for
// like-for-like reading against the Xenos listing). /Zpr at compile time keeps
// the matrix row-major like the console's four mad rows.
//
// Build (same recipe as pc/gcm/renderengine/SkyDomeProgramsPC.cpp):
//   fxc /nologo /T vs_3_0 /E vs_main /O2 /Zpr /Fo skid_vs.fxo brn_skid.fx
//   fxc /nologo /T ps_3_0 /E ps_main /O2 /Zpr /Fo skid_ps.fxo brn_skid.fx
//   -> tools/assets/shaders/shader_transcode.py :: build_pc_program_buffer()
//   -> b5-decomp/src/pc/gcm/renderengine/SkidProgramsPC.cpp
// =============================================================================

float4x4 gWorldViewProj : register(c0);
float4   gStartColour   : register(c4);
float4   gEndColour     : register(c5);

sampler2D gSkidSampler : register(s0);

struct VS_IN
{
    float3 pos         : POSITION0;   // SkidVertex::mv3Pos         (vertex element type 1 -> POSITION 0)
    float4 uvTimeAlpha : TEXCOORD0;   // SkidVertex::mv4UvTimeAlpha (vertex element type 6 -> TEXCOORD 0)
};

struct VS_OUT
{
    float4 pos    : POSITION;
    float2 uv     : TEXCOORD0;   // export0.xy
    float4 colour : COLOR0;      // export1
};

VS_OUT vs_main(VS_IN i)
{
    VS_OUT o;
    // slots 5-7: pos.x * c0 + pos.y * c1 + pos.z * c2 + c3 (the .xzyw swizzles on slot 6 are
    // undone by slot 7's; the net is the plain row-vector product).
    o.pos = mul(float4(i.pos, 1.0f), gWorldViewProj);
    // slots 8-9: colour = (end - start) * time + start.
    float4 colour = (gEndColour - gStartColour) * i.uvTimeAlpha.z + gStartColour;
    // slots 10 / 12: rgb through, alpha scaled by the skid strength.
    o.colour = float4(colour.xyz, colour.w * i.uvTimeAlpha.w);
    // slot 11.
    o.uv = i.uvTimeAlpha.xy;
    return o;
}

float4 ps_main(VS_OUT i) : COLOR0
{
    return tex2D(gSkidSampler, i.uv) * i.colour;
}
