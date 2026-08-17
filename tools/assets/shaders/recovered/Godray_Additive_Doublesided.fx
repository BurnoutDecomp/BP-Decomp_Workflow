// Godray_Additive_Doublesided.fx -- RECOVERED from the X360 SHADERS.BNDL microcode.
//
// The retail bundle's technique "Godray_Additive_Doublesided_Default" (ShaderTechnique
// 0x81F53722, gamedb://burnout5/Playground/Test_Shaders/Godray_Additive_Doublesided.fx)
// has NO source in the nushaders TUB HLSL tree, so convert_shaders_bundle.py used to
// substitute fallback_world.fx for it.  That substitution is what fired
//   "Tyring to postfixup a constant not present in the programbuffer"
//   (CgsMaterialResourceType::PostFixUpShaderConstants, TRK_UNIT83/379/381/388_GR.bndl,
//    material Godray01.Material?ID=667103):
// the technique's PIXEL-stage INTERNAL constant list is {illuminance, materialDiffuse}
// and the fallback shader never declared `illuminance`, so the fxc CTAB of the
// substituted pixel program had no such variable and GetVariableHandleByName failed.
//
// This file is the real shader, decoded instruction-for-instruction from the two X360
// ShaderProgramBuffer resources the technique imports (VS 0xDFF4FAE8, PS 0x45ADE07A)
// with tools/assets/shaders/xenos.py + ctab.py (the decoder validated against the
// SHADERS.BNDL / SHADERS_PC.BNDL oracle pair, see xenos.py).  Constant surface, from
// the X360 programs' own CTABs and the technique's constant lists:
//   VS  world (per-object)   ViewProjectionModified, ScattCoeffs, ViewPosition (global)
//   PS  FogColourPlusWhiteLevel (global)   materialDiffuse, illuminance (internal;
//       X360 CTAB defaults {1,1,1,1} and 1.0)   DiffuseTextureSampler (s0)
//
// X360 microcode, annotated (Xenos slot : op):
//   VS  4/5 vfetch position -> r2.xyz, texcoord -> r0.yz
//        7-9  r1.xyz = pos.z*world[2] + world[3] + pos.y*world[1] + pos.x*world[0]
//       10-13 hpos.x = dot(VPM[0], r1) ; .y = dot(VPM[1], r1) ; z' = dot(VPM[2], r1)
//             hpos.zw = z' * VPM[3].xz + VPM[3].yw
//       14-16 dist = length(ViewPosition - worldPos)
//       17-21 fog = pow(saturate(dist * ScattCoeffs.x - ScattCoeffs.y), ScattCoeffs.z)
//                   * ScattCoeffs.w
//       22    o0.xyz = (u, v, fog)
//   PS  2    tfetch r1.xz_y <- tex2D(s0, uv)      (r1 = tex.x, tex.z, -, tex.y)
//        3    r2.yzw = tex.rgb * materialDiffuse.rgb ; r2.x = WhiteLevel + WhiteLevel
//        4-6  r1.xyz = (tex.rgb * materialDiffuse.rgb) * illuminance * (2 * WhiteLevel)
//        6    ps = tex.g                                  (maxs r1.w, r1.w)
//        7    r2.xyz = FogColour.rgb - r1.rgb ; r0.x = fog * ps  (muls_prev, ps = fog*tex.g)
//        8    oC0.rgb = r1.rgb + r0.x * r2.rgb ; oC0.a = ps       (retain_prev)
//
// MATRIX PACKING: compiled with /Zpr (row-major) like every SHADERS.BNDL program -- see
// compile_entry() in convert_shaders_bundle.py; the engine uploads logical ROWS.
// Self-contained on purpose: it must compile without the TUB Include/ tree.

// ---- per-object (vertex) --------------------------------------------------
float4x4 world;

// ---- global (vertex) ------------------------------------------------------
float4x4 ViewProjectionModified;
float4   ScattCoeffs;
float3   ViewPosition;

// ---- global (pixel) -------------------------------------------------------
float4   FogColourPlusWhiteLevel;

// ---- material (internal) --------------------------------------------------
float4 materialDiffuse = { 1.0f, 1.0f, 1.0f, 1.0f };
float  illuminance     = 1.0f;

sampler2D DiffuseTextureSampler : register(s0);

struct VSIn
{
    float3 position : POSITION;
    float2 uv       : TEXCOORD0;
};

struct VSOut
{
    float4 hPosition : POSITION;
    float3 uvFog     : TEXCOORD0;   // xy = uv, z = fog factor
};

VSOut VS_Main(VSIn IN)
{
    VSOut OUT;
    float4 objectPos = float4(IN.position, 1.0f);
    float3 worldPos  = mul(objectPos, world).xyz;
    float4 worldPos4 = float4(worldPos, 1.0f);

    // TransformWorldToProjection form: rows of ViewProjectionModified dotted with the
    // world position; row 3 carries the {zScale, zBias, wScale, wBias} depth remap.
    float4 hpos;
    hpos.x  = dot(worldPos4, ViewProjectionModified[0]);
    hpos.y  = dot(worldPos4, ViewProjectionModified[1]);
    hpos.z  = dot(worldPos4, ViewProjectionModified[2]);
    hpos.zw = hpos.zz * ViewProjectionModified[3].xz + ViewProjectionModified[3].yw;
    OUT.hPosition = hpos;

    // Scattering fog, the same form the TUB world shaders compile to.
    float  dist = length(ViewPosition - worldPos);
    float  fog  = pow(saturate(dist * ScattCoeffs.x - ScattCoeffs.y), ScattCoeffs.z)
                * ScattCoeffs.w;

    OUT.uvFog = float3(IN.uv, fog);
    return OUT;
}

float4 PS_Main(VSOut IN) : COLOR0
{
    float4 tex = tex2D(DiffuseTextureSampler, IN.uvFog.xy);

    // tex.rgb * materialDiffuse.rgb * illuminance * (2 * whiteLevel)
    float3 lit = tex.rgb * materialDiffuse.rgb
               * (illuminance * (FogColourPlusWhiteLevel.w + FogColourPlusWhiteLevel.w));

    // The fog lerp is scaled by the texture's green channel, which is also the alpha.
    float fogAmount = IN.uvFog.z * tex.g;

    float4 OUT;
    OUT.rgb = lit + (FogColourPlusWhiteLevel.rgb - lit) * fogAmount;
    OUT.a   = fogAmount;
    return OUT;
}

technique Default
{
    pass p0
    {
        VertexShader = compile vs_3_0 VS_Main();
        PixelShader  = compile ps_3_0 PS_Main();
    }
}
