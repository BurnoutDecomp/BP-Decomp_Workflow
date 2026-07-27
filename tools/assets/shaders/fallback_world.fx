// Minimal bring-up shader for Burnout Paradise PC world rendering.
// Used by convert_shaders_bundle.py --fallback for techniques with no TUB
// HLSL source (the Vehicle_* set and other exe-resident techniques), and by
// the MINIMAL_PATH.md single-shader bring-up option.
//
// Constant names deliberately reuse the game's global names so the engine's
// name/hash-keyed binding (ShaderConstantsExternal / the constant hash table)
// finds whichever of them the owning technique actually dispatches:
//   world                  -- per-object 4x3 world transform (float4x3 rows)
//   ViewProjectionModified -- global view-projection (4 float4 rows)
//   materialDiffuse        -- material colour (hash-table bound)
//   DiffuseTextureSampler  -- sampler s0 (the technique sampler channel 0)
// Anything the technique tries to bind that is absent here resolves to a
// register-count-0 handle and is skipped -- absent constants are harmless.
//
// Compile (see MINIMAL_PATH.md):
//   fxc /T vs_3_0 /E VS_Main /O2 /Fo fallback_vs.fxo fallback_world.fx
//   fxc /T ps_3_0 /E PS_Main /O2 /Fo fallback_ps.fxo fallback_world.fx

float4x4 world;
float4x4 ViewProjectionModified;
float4 materialDiffuse = { 1.0f, 1.0f, 1.0f, 1.0f };

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
};

VSOut VS_Main(VSIn IN)
{
    VSOut OUT;
    float3 worldPos = mul(float4(IN.position, 1.0f), world).xyz;
    OUT.hPosition = mul(float4(worldPos, 1.0f), ViewProjectionModified);
    OUT.uv = IN.uv;
    return OUT;
}

float4 PS_Main(VSOut IN) : COLOR0
{
    return tex2D(DiffuseTextureSampler, IN.uv) * materialDiffuse;
}

technique Default
{
    pass p0
    {
        VertexShader = compile vs_3_0 VS_Main();
        PixelShader  = compile ps_3_0 PS_Main();
    }
}
