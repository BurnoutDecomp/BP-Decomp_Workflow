// Minimal bring-up shader for Burnout Paradise PC world rendering.
// Used by convert_shaders_bundle.py --fallback for techniques with no TUB
// HLSL source and no recovered/ source (today only
// CarStudio_DoNotShipWithThisInTheGame_Default; Godray_Additive_Doublesided_Default
// used to be the other one and is now recovered/Godray_Additive_Doublesided.fx),
// and by the MINIMAL_PATH.md single-shader bring-up option.
//
// Constant names deliberately reuse the game's global names so the engine's
// name/hash-keyed binding (ShaderConstantsExternal::FixUp(const ProgramBuffer*)
// / the constant hash table) finds whichever of them the owning technique
// dispatches.  A technique constant that is ABSENT from the compiled shader is
// not harmless:
//   * an EXTERNAL one makes ShaderConstantsExternal::FixUp log the console's
//     "Missing shader constant from table <name>";
//   * an INTERNAL (material) one makes CgsResource::MaterialResourceType::
//     PostFixUpShaderConstants ASSERT "Tyring to postfixup a constant not present
//     in the programbuffer" the moment a material using the technique streams in
//     (that is exactly what the Godray substitution did on TRK_UNIT83_GR before
//     `illuminance` was declared+consumed below and Godray got a real shader).
// So every global AND internal constant the substituted techniques list is
// declared AND consumed below (an unused declaration is optimised out of the
// constant table).  convert_shaders_bundle.py now checks this contract after
// compiling (`check` re-runs it on a staged bundle).
//
// MATRIX PACKING: compiled with /Zpr (row-major).  See compile_entry() in
// convert_shaders_bundle.py -- the engine uploads logical ROWS.
//
// Compile (see MINIMAL_PATH.md):
//   fxc /T vs_3_0 /E VS_Main /O2 /Zpr /Fo fallback_vs.fxo fallback_world.fx
//   fxc /T ps_3_0 /E PS_Main /O2 /Zpr /Fo fallback_ps.fxo fallback_world.fx

// ---- per-object (vertex) --------------------------------------------------
float4x4 world;

// ---- global (vertex) ------------------------------------------------------
float4x4 ViewProjectionModified;
float4x4 IrradianceQuadricA;
float4x4 IrradianceQuadricB;
float4x4 ShadowMap_WorldToLight[3];
float3   KeyLightDirection;
float3   ViewPosition;
float4   ScattCoeffs;

// ---- global (pixel) -------------------------------------------------------
float4   FogColourPlusWhiteLevel;
float3   KeyLightColour;
float3   KeyLightSpecularColour;
float3   KeyLightClampedColour;
float4   ShadowMap_Constants;
float4   ShadowMap_Constants2;

// ---- material (internal) --------------------------------------------------
float4 materialDiffuse = { 1.0f, 1.0f, 1.0f, 1.0f };
float  illuminance     = 1.0f;   // Godray_Additive_Doublesided's PS internal

sampler2D DiffuseTextureSampler : register(s0);

struct VSIn
{
    float3 position : POSITION;
    float2 uv       : TEXCOORD0;
};

struct VSOut
{
    float4 hPosition : POSITION;
    float2 uv        : TEXCOORD0;
    float4 shade     : TEXCOORD1;
};

VSOut VS_Main(VSIn IN)
{
    VSOut OUT;
    float4 objectPos = float4(IN.position, 1.0f);
    float3 worldPos  = mul(objectPos, world).xyz;
    float4 worldPos4 = float4(worldPos, 1.0f);

    // Same form as Include/Transform.fxh TransformWorldToProjection: the rows of
    // ViewProjectionModified are dotted with the world position, and row 3 carries
    // the {zScale, zBias, wScale, wBias} depth remap.
    float4 hpos;
    hpos.x  = dot(worldPos4, ViewProjectionModified[0]);
    hpos.y  = dot(worldPos4, ViewProjectionModified[1]);
    hpos.z  = dot(worldPos4, ViewProjectionModified[2]);
    hpos.zw = hpos.zz * ViewProjectionModified[3].xz + ViewProjectionModified[3].yw;
    OUT.hPosition = hpos;

    OUT.uv = IN.uv;

    // Touch every remaining vertex-stage global so it survives into the constant
    // table (see the header note); the contribution is scaled to ~zero.
    float4 ambient = IrradianceQuadricA[0] + IrradianceQuadricB[0]
                   + mul(worldPos4, ShadowMap_WorldToLight[0])
                   + ScattCoeffs
                   + float4(KeyLightDirection, 0.0f)
                   + float4(ViewPosition, 0.0f);
    OUT.shade = ambient * 1e-8f + float4(1.0f, 1.0f, 1.0f, 1.0f);
    return OUT;
}

float4 PS_Main(VSOut IN) : COLOR0
{
    float4 texel = tex2D(DiffuseTextureSampler, IN.uv) * materialDiffuse;

    // Same "declare and consume" rule for the pixel-stage globals.
    float4 lighting = FogColourPlusWhiteLevel
                    + float4(KeyLightColour, 0.0f)
                    + float4(KeyLightSpecularColour, 0.0f)
                    + float4(KeyLightClampedColour, 0.0f)
                    + ShadowMap_Constants + ShadowMap_Constants2;
    return texel * IN.shade + (lighting + illuminance) * 1e-8f;
}

technique Default
{
    pass p0
    {
        VertexShader = compile vs_3_0 VS_Main();
        PixelShader  = compile ps_3_0 PS_Main();
    }
}
