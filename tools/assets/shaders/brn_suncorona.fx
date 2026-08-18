// tools/assets/shaders/brn_suncorona.fx
// ============================================================================
// brn_suncorona.fx -- the FOUR BrnSunCorona programs: the sun-occlusion
// measurement pair and the sun-flare pair.
//
// AUTHORED, NOT CONVERTED.  None of the four is in SHADERS.BNDL: all four are
// Xenos microcode packages embedded in the X360 executable and handed straight
// to renderengine::ProgramBuffer::Initialize by BrnSunCorona::Construct
// @0x824009B0 --
//   occlusion vertex  X360 0x8203E118  204 B  ucode +0x084  (  0,  72)
//   occlusion pixel   X360 0x8203E208  524 B  ucode +0x118  ( 64, 180)
//   flare     vertex  X360 0x8203E438  240 B  ucode +0x090  (  0,  96)
//   flare     pixel   X360 0x8203E528  464 B  ucode +0x10C  ( 64, 132)
// (the pair after each size is the (literal-block bytes, instruction-stream
// bytes) split the package header's +0x18 field points at; only the two PIXEL
// programs have a literal block, mapping to c252..c255.)  All four sizes are the
// console's own: Construct stores 0xCC / 0x20C / 0xF0 / 0x1D0 into the
// ProgramBufferParameters at +0x08 (asm 0x82400AD8 / 0x82400B64 / 0x82400BF8 /
// 0x82400C5C).  The bytes are scratch/coronas_step2/DATA_DUMP.md, dumped from
// ARTIST_copy.i64, and each package is SELF-PROVING: const+stream == the +0x08
// size AND ucode_off+ucode_len == the dumped length, for all four
// (scratch/coronas_step2/suncorona/work/extract_blobs.log).
//
// All four were disassembled with tools/assets/shaders/xenos.py -- the decoder
// proved against the X360-vs-PC SHADERS.BNDL pair -- and EVERY ALU line below
// has a numbered counterpart in that disassembly (work/xenos_all.txt, annotated
// in work/DECODE.md).
//
// THE CONSTANT SURFACE IS NOT GUESSED: it is the CTAB interned in each package
// (tools/assets/shaders/ctab.py, work/ctab.txt):
//   occlusion vertex : (no constants at all)
//   occlusion pixel  : c0 kUvStartAndOffset (float4)   s0 SamplerSource  (sampler2D)
//   flare     vertex : (no constants at all)
//   flare     pixel  : c0 kColourAndPower   (float4)   s0 OcclusionSource(sampler2D)
// and the two pixel names are exactly the two strings BrnSunCorona::Construct
// resolves through renderengine::ProgramBuffer::GetVariableHandleByName
// (asm 0x82400BD4 "kUvStartAndOffset" against mpOcclusionPixelProgram, and
// 0x82400CEC "kColourAndPower" against mpFlarePixelProgram).
//
// /Zpr IS HARMLESS HERE AND KEPT FOR CONSISTENCY with every other converted PC
// program: neither vertex program declares a matrix (neither declares ANY
// constant), so row-vs-column packing cannot change a byte.  It is passed so
// this file goes through the identical fxc line as brn_corona.fx.
//
// VERTEX INPUT.  BrnSunCorona::Construct builds ONE declaration, shared by both
// vertex programs (asm 0x82400A18-0x82400A4C, read through the ground-truth
// Parameters lane table in pc/gcm/renderengine/VertexDescriptor.h:44-58):
//   element 0  stream 0  format 0x2A23B9 FLOAT3  elementType 1 -> POSITION0  offset  0
//   element 1  stream 0  format 0x2C23A5 FLOAT2  elementType 6 -> TEXCOORD0  offset 12
//                                                                  STRIDE = 20
// -- 20 is exactly the stride BOTH GenerateOcclusionBuffer @0x82400E98 and
// RenderOccludedFlare @0x8240130C hand D3DDevice_BeginVertices(dev, 6
// /*TRIANGLESTRIP*/, 4, 20), and exactly the DWARF's
// `typedef VertexIterator2<VertexTypeFloat3, VertexTypeFloat2>
//  BrnSunCoronaVertexIterator` (DecFIGS BrnSunCorona.cpp:29).  Three witnesses,
// one layout.  (Both format words are ALREADY in both PC mapping tables --
// ImmediateModePCLeaf.cpp:182/183 and XenonD3D9Shims.cpp:323/324 -- so unlike
// the corona pair's 0x014C86 there is no missing case to add.)
//
// ⚠ THE SPACE THE POSITION IS IN.  Both vertex programs are PURE PASS-THROUGHS:
// `oPos = float4(vIn.position.xyz, 1)`, with no matrix anywhere.  The CPU feeds
// NDC directly -- GenerateOcclusionBuffer writes the corners (-1,-1,0) (1,-1,0)
// (-1,1,0) (1,1,0), and RenderOccludedFlare writes the flare quad already
// converted to NDC by `x*2-1`.  There is nothing to transpose and no camera to
// get wrong.
// ============================================================================


// ===========================================================================
// SHARED VERTEX INPUT (the one declaration both vertex programs are drawn with)
// ===========================================================================
struct SunCoronaVertexIn
{
    float3 mPosition : POSITION;    // ALREADY IN NDC (see the banner)
    float2 mUv       : TEXCOORD0;
};


// ---------------------------------------------------------------------------
// OCCLUSION VERTEX PROGRAM  (X360 0x8203E118)
//     fxc /T vs_3_0 /E mainSunOcclusionVS /O2 /Zpr
//
// The whole console program is two instructions:
//     3 : tfetch  r0.xyz1, r0.yxx, tf31      -- fetch POSITION, w := 1
//     4 : max     export62.xyzw, r0, r0      -- oPos = that float4
// The TEXCOORD element of the declaration is present but NEVER FETCHED by this
// program (the occlusion pass writes uv = (0,0) into all four vertices anyway --
// GenerateOcclusionBuffer's four `std r10, 0(...)` pairs), and the pixel program
// builds its own uv out of kUvStartAndOffset.  Declaring the input and not using
// it is the faithful shape: fxc simply omits it from the input signature, which
// D3D9 permits (a declaration may feed more elements than a shader reads).
// ---------------------------------------------------------------------------
struct SunOcclusionVertexOut
{
    float4 mPosition : POSITION;
};

SunOcclusionVertexOut mainSunOcclusionVS(SunCoronaVertexIn lIn)
{
    SunOcclusionVertexOut lOut;

    // [3,4] oPos = float4(position.xyz, 1) -- no transform of any kind.
    lOut.mPosition = float4(lIn.mPosition, 1.0f);

    return lOut;
}


// ---------------------------------------------------------------------------
// OCCLUSION PIXEL PROGRAM  (X360 0x8203E208)
//     fxc /T ps_3_0 /E mainSunOcclusionPS /O2 /Zpr
//
// WHAT IT MEASURES.  It renders ONE PIXEL (the sun-corona buffer is 1x1 --
// BrnRendererMemory::CreateSunCoronaBuffer @0x823F73C8 loads a single `li r10,1`
// and stores it to width, height AND mip count) whose value is the FRACTION OF A
// 7x7 GRID OF DEPTH TAPS, laid out around the sun's screen position, that reads
// the FAR PLANE -- i.e. the fraction of the sun disc that nothing occludes.
// RenderOccludedFlare then multiplies the flare by that fraction.
//
// THE CONSOLE LISTING, instruction for instruction (work/xenos_all.txt):
//     literals  c254 = {1, 0.0204082, 0, 0}     0.0204082 == 1/49 == 1/(7*7)
//               c255 = {1.51992e-05, 0.996094, 0.00389099, 3}
//      5 : sgts   r0.z, -r0'.x, -r0'.x            -- the "set to 0" idiom: accumulator = 0
//      6 : mad    r0.y, -c0.w, c255.w(3), c0.y    -- v     = start.y - 3*offset.y
//        loop  (outer, 7)
//      7 :   maxs r0.x, c0.x, c0.x                -- u     = start.x        (NOT -3*offset.x)
//          loop  (inner, 7)
//      8 :     tfetch r1.xyz, r0.xy, tf0          -- sample SamplerSource
//      9 :     dp3    r0.w, r1.<y,z,x>, c255.xyz  -- decode a 24-bit depth from 3 lanes
//     10 :     sge    r0.w, r0.w, c254.x(1.0)     -- 1 if this tap is at the far plane
//     11 :     add    r0.z, r0.w, r0.z           \  accumulate
//     11 :     addsc0 r0.x, c0.z, r0.x           /  u += offset.x
//          end
//     12 :   addsc0 r0.y, c0.w, r0.y              -- v += offset.y
//        end
//     13 : mul    export0.xyzw, r0.z, c254.y      -- oC0 = count * (1/49)
//
// ⚠ THE LOOP COUNTS ARE NOT IN THE MICROCODE.  Xenos loop_start/loop_end read
// their trip count from a LOOP CONSTANT register that lives outside the
// instruction stream (the package's ucode region is exactly the 64-byte literal
// block + the 180-byte stream, which the header's own +0x18 split proves), so
// 7x7 is INFERRED -- from c254.y being exactly 1/49 and c255.w being exactly 3
// (a centred 7-tap kernel runs -3..+3).  No other pair of counts multiplies to
// 49.  Recorded as inferred, not claimed as read.
//
// ⚠ AND THE X SCAN IS NOT CENTRED -- THIS IS THE CONSOLE'S OWN ASYMMETRY, NOT A
// TRANSCRIPTION SLIP.  Instruction 6 subtracts 3 offsets from the START V;
// instruction 7 assigns the START U verbatim (its encoding is
// `14100000 0000006C C2000000`: scalar opcode 5 = maxs, scalar mask .x, src3 =
// CONSTANT index 0 with 2-component swizzle 0x6C -> c0.x,c0.x, i.e. max(c0.x,
// c0.x) -- the compiler's "mov"), and the CPU passes the sun's CENTRE in both
// lanes (`stfs f30 -> +0` = mfXPos, `stfs f29 -> +4` = mfYPos,
// GenerateOcclusionBuffer @0x82400E60/E64).  So the kernel spans
// [x, x+6*dx] x [y-3*dy, y+3*dy].  It is reproduced verbatim: "fixing" it would
// move the measurement half a kernel and is not a decompilation.
// (The DWARF names those two constant lanes lfStartU / lfStartV -- DecFIGS
// BrnSunCorona.cpp:278/279 -- which is consistent with either reading, so the
// asm arbitrates.)
//
// ⚠ ONE DELIBERATE PC DEVIATION: THE DEPTH *ENCODING*, NOT THE DEPTH SEMANTICS.
// Instruction 9 decodes a 24-bit depth out of three 8-bit colour lanes of an
// A8R8G8B8 fetch of the X360 depth-stencil surface -- the weights
// {255/2^24, 255/2^8, 255/2^16} = {1.51992e-05, 0.996094, 0.00389099} are the
// same three the post-fx blur programs use (see the identical banner at
// tools/assets/shaders/brn_postfx_composite.fx:233-252).  On D3D9 the scene
// depth is an INTZ texture, whose fetch returns the normalised device depth
// directly in .r, so the three-lane decode is REPLACED by a single .r read.  The
// VALUE is identical; only the encoding differs.
// ---------------------------------------------------------------------------
sampler2D SamplerSource : register(s0);   // the DOWN-SAMPLE buffer's depth texture

// .xy = the sun's screen position (mfXPos, mfYPos), .zw = one tap step
// (mfOcclusionSize / sourceWidth, mfOcclusionSize / sourceHeight).
float4 kUvStartAndOffset : register(c0);

// The two literal rows the console interns, spelled out so the recompiled
// bytecode carries the same numbers.
static const float KF_SUN_OCCLUSION_TAP_BIAS  = 3.0f;         // c255.w
static const int   KI_SUN_OCCLUSION_TAPS      = 7;            // 7 x 7 (see the note above)
static const float KF_SUN_OCCLUSION_TAP_SCALE = 1.0f / 49.0f; // c254.y = 0.0204082
static const float KF_FAR_PLANE_DEPTH         = 1.0f;         // c254.x

float4 mainSunOcclusionPS() : COLOR0
{
    // [5] the accumulator.
    float lfVisibleTaps = 0.0f;

    // [6] the START V is pulled back by three steps; the START U is NOT (see the
    // asymmetry note).
    float lfV = kUvStartAndOffset.y - KF_SUN_OCCLUSION_TAP_BIAS * kUvStartAndOffset.w;

    for (int liRow = 0; liRow < KI_SUN_OCCLUSION_TAPS; ++liRow)
    {
        // [7] u restarts at the START U on every row.
        float lfU = kUvStartAndOffset.x;

        for (int liTap = 0; liTap < KI_SUN_OCCLUSION_TAPS; ++liTap)
        {
            // [8,9] the tap.  On D3D9 the INTZ fetch IS the normalised depth.
            float lfDepth = tex2D(SamplerSource, float2(lfU, lfV)).r;

            // [10] 1 when nothing was drawn at this tap (the far plane / sky).
            // [11 vector] accumulate.
            lfVisibleTaps += step(KF_FAR_PLANE_DEPTH, lfDepth);

            // [11 scalar] u += offset.x
            lfU += kUvStartAndOffset.z;
        }

        // [12] v += offset.y
        lfV += kUvStartAndOffset.w;
    }

    // [13] the fraction, broadcast to all four lanes.  (The console's scalar unit
    // then overwrites .w with its previous scalar result -- the last v -- which
    // nothing ever reads: the flare pixel program samples this buffer's .x.  Not
    // reproduced; writing the fraction to .w is the strictly cleaner form of a
    // don't-care lane.)
    return lfVisibleTaps * KF_SUN_OCCLUSION_TAP_SCALE;
}


// ---------------------------------------------------------------------------
// FLARE VERTEX PROGRAM  (X360 0x8203E438)
//     fxc /T vs_3_0 /E mainSunFlareVS /O2 /Zpr
//
// Four instructions, and again no transform of any kind:
//     3 : tfetch  r1.xyz1, r0.yxx, tf31     -- POSITION, w := 1
//     4 : max     export62.xyzw, r1, r1     -- oPos
//     5 : tfetch  r0.xy, r0.yxx, tf31       -- TEXCOORD0
//     6 : max     export0.xy, r0.xy, r0.xy  -- oTex0
// RenderOccludedFlare writes the quad's positions ALREADY IN NDC and its uvs as
// the corners of the [-1,1] square: (-1,1) (1,1) (-1,-1) (1,-1) in the
// TRIANGLESTRIP order (asm 0x824013B0-0x82401518).
// ---------------------------------------------------------------------------
struct SunFlareVertexOut
{
    float4 mPosition : POSITION;
    float2 mUv       : TEXCOORD0;   // export0 -- the [-1,1] unit-disc coordinate
};

SunFlareVertexOut mainSunFlareVS(SunCoronaVertexIn lIn)
{
    SunFlareVertexOut lOut;

    // [3,4]
    lOut.mPosition = float4(lIn.mPosition, 1.0f);
    // [5,6]
    lOut.mUv       = lIn.mUv;

    return lOut;
}


// ---------------------------------------------------------------------------
// FLARE PIXEL PROGRAM  (X360 0x8203E528)
//     fxc /T ps_3_0 /E mainSunFlarePS /O2 /Zpr
//
// THE CONSOLE LISTING (literals: c255 = {1, 0, 0, 0}):
//      2 : sgts    r0.z, -r0'.x, -r0'.x           -- the "set to 0" idiom: r0.z = 0
//      3 : tfetch  r1.w, r0.zzz, tf0              -- sample OcclusionSource AT (0,0)
//      4 : dp2add  r0.y, r0.xy, r0.xy, c255.y(0)  -- dot(uv,uv)
//      5 : subsc0  r0.y, c255.x(1), r0.y          -- 1 - dot(uv,uv)
//      6 : mulsc0  r0.x, c0.x, r0.y               -- colour.r * that
//      7 : mul     r1.x, r0.x, r0.y              \ colour.r * that^2
//      7 : muls    r0.x, r0.y, r0.y              / that^2
//      8 : mul     r1.yz, r0.x, c0.yz             -- colour.gb * that^2
//      9 : max     export0.xyzw, r1, r1           -- oC0 = float4(colour.rgb*f2, occlusion)
//
// so:  RGB = kColourAndPower.rgb * (1 - dot(uv,uv))^2
//      A   = the occlusion buffer's single texel
//
// THREE THINGS WORTH SAYING OUT LOUD, all read rather than assumed:
//
//  * THE ALPHA IS THE OCCLUSION, AND THE BLEND CONSUMES IT.  The pass runs with
//    CgsBlendStateFactory saBlendStates[5]
//    (E_FACTORY_BLEND_STATE_TRANSPARENT_ADDITIVE_RGB_NO_ALPHA_TEST_DEST_RGB,
//    X360 dword_83010F84, factor word 0x01000106 -- CgsBlendStateFactory.cpp:240),
//    which the RB_BLENDCONTROL split in XenonD3D9Shims.cpp:4121 decodes as
//    COLOUR src = SRCALPHA, dst = ONE, op = ADD.  So the frame gets
//    `dst + flareRGB * occlusion`: the visibility fraction is applied by the
//    BLEND UNIT, not in the shader.  (ALPHA src = ZERO / dst = ONE -- the
//    destination alpha is left alone, which is what "DestRGB" names.)
//
//  * kColourAndPower.w (mfSunFlarePow, seeded 2.0f by Construct @0x82400A08) is
//    PUBLISHED BY THE CPU AND NEVER READ BY THE SHADER: the exponent is compiled
//    in as the two multiplies at instructions 7/8.  Writing `pow(f, 2)` here
//    would emit log/mul/exp; the square is what the console executes and what is
//    written.  The constant is still published, because the CPU publishes it.
//
//  * THERE IS NO SATURATE.  None of instructions 5-9 carries the [clamp] flag, so
//    outside the unit disc `1 - dot(uv,uv)` goes NEGATIVE and the square brings
//    it back up: at the quad's four corners (uv = (+-1,+-1), dot = 2) the factor
//    is 1 again, so the sprite is a bright disc with four bright corners -- a
//    four-pointed star.  That is the console's picture and it is reproduced
//    verbatim; a saturate() here would be a silent art change.
// ---------------------------------------------------------------------------
sampler2D OcclusionSource : register(s0);   // the 1x1 sun-corona buffer's colour texture

// .rgb = the sun colour * white level * brightness, .w = mfSunFlarePow (unread).
float4 kColourAndPower : register(c0);

float4 mainSunFlarePS(float2 lUv : TEXCOORD0) : COLOR0
{
    // [3] the whole 1x1 occlusion buffer, sampled at its origin.
    float lfOcclusion = tex2D(OcclusionSource, float2(0.0f, 0.0f)).x;

    // [4,5] the radial falloff -- 1 at the centre, 0 on the unit circle,
    // NEGATIVE outside it (no saturate; see the note).
    float lfFalloff = 1.0f - dot(lUv, lUv);

    // [6,7,8] colour * falloff^2  (the exponent is compiled in, not pow()).
    float3 lColour = kColourAndPower.rgb * (lfFalloff * lfFalloff);

    // [9] the occlusion rides out in ALPHA and the blend unit applies it.
    return float4(lColour, lfOcclusion);
}
