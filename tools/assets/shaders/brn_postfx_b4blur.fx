// ============================================================================
// brn_postfx_b4blur.fx -- the EIGHT rw::graphics::postfx::B4Blur programs.
//
// AUTHORED, NOT CONVERTED.  Like the composite pair, the six bloom programs and
// the five helper/DoF programs, none of these is in SHADERS.BNDL: each is a
// Xenos microcode package embedded in the X360 executable and handed straight
// to renderengine::ProgramBuffer::Initialize by B4Blur::B4Blur @0x823FE9C8 --
//   quad         vertex  X360 0x82045148  348 B  ucode +0x0B4 (0, 168)
//   scatter      vertex  X360 0x82045600  324 B  ucode +0x0CC (0, 120)
//   scatter      pixel   X360 0x82045748  620 B  ucode +0x130 (64, 252)
//   radial       vertex  X360 0x82045AC0  324 B  ucode +0x0CC (0, 120)
//   radial       pixel   X360 0x82045C08  716 B  ucode +0x130 (64, 348)
//   texture      pixel   X360 0x820459B8  260 B  ucode +0x0D4 (0, 48)
//   down-sample  pixel   X360 0x820454E0  288 B  ucode +0x0E4 (0, 60)
//   blur         pixel   X360 0x820452A8  564 B  ucode +0x0E0 (64, 276)
// (the pair after each size is the (literal-block bytes, instruction-stream
// bytes) split the package header's +0x18 field points at; the four programs
// with a 64-byte literal block map it to c252..c255.)  The bytes are
// scratch/postfx_step6_producers/PACKAGES_DUMP_B4BLUR.md, dumped from
// ARTIST_copy.i64; every one of the eight sizes matches the byte count the
// committed rwgpfxb4blur.cpp already records at its CreateProgram call site.
// All eight were disassembled with tools/assets/shaders/xenos.py -- the decoder
// proved against the X360-vs-PC SHADERS.BNDL pair -- and every line below has a
// named counterpart in that disassembly.
//
// THE CONSTANT SURFACE IS NOT GUESSED: it is the CTAB interned in each package
// (tools/assets/shaders/ctab.py).  Register for register:
//   quad VS        : (no constants at all)
//   scatter VS     : c0 uvOffset
//   radial  VS     : c0 uvOffset            -- see FINDING 1
//   scatter PS     : c0 scatterScalars1, c1 scatterScalars2, s0 low_texture
//   radial  PS     : c0 scatterScalars1, c1 scatterScalars2, s0 low_texture
//   texture PS     : c0 blendFactor,     s0 tex
//   downsample PS  : c0 sampleOffsets (matrix_rows float[4x4], RegisterCount 1),
//                    s0 scene_texture
//   blur PS        : s0 low_texture  ONLY  -- see FINDING 2
//
// ---------------------------------------------------------------------------
// FINDING 1 -- THE TWO 'uvOffset' VERTEX PROGRAMS ARE BYTE-IDENTICAL.
// 0x82045600 (scatter) and 0x82045AC0 (radial) are the same 324 bytes,
// sha1 9db13387ba196d6f185017f5b3053bda4d2835c0 for both (checked byte-for-byte
// after extraction, not by eye).  The X360 image carries two copies because the
// two CreateProgram call sites take two different addresses; ONE HLSL entry
// point and ONE PC array therefore serve both, and rwgpfxb4blur.cpp hands the
// same array to both sites -- which still builds two ProgramBuffer objects,
// exactly as the console does.
//
// FINDING 2 -- THE BLUR PIXEL PROGRAM HAS NO 'controlScalars' CONSTANT.
// B4Blur::B4Blur asks for it by name (`aControlscalars` @0x823FEF0C-0x823FEF1C,
// `bl renderengine__ProgramBuffer__GetVariableHandleByName`), and the tree's
// committed bind is a correct transcription of that call -- but the compiled
// package's CTAB declares exactly ONE entry, the `low_texture` sampler.  The
// three blur weights the name refers to were folded into the program's LITERAL
// block by the shader compiler: c255 = {0.75, 0.5, 0.66, 0}.  So on the console
// GetVariableHandleByName MISSES and m_controlScalarsHandle is a zero-count
// ("not found") handle; anything pushed through it goes nowhere.  The PC image
// below reproduces that exactly -- the three weights are literals here too, and
// no `controlScalars` uniform is declared -- because declaring one would give
// the PC handle a register the console handle does not have and make a push
// that is a no-op on the console start moving pixels on PC.
//
// FINDING 3 -- THE BLUR TAP OFFSETS ARE PER-VERTEX, NOT CONSTANTS.
// The blur quad's vertex descriptor is FIVE elements (position + four FLOAT4
// streams at usage indices 6/7/8/9, rwgpfxb4blur.cpp's KI_VERTEX_FORMAT_EXTRA
// x4), the quad vertex program below is a pure pass-through of those four
// float4s into TEXCOORD0..3, and the blur pixel program fetches SEVEN of the
// eight uv pairs they carry.  The DWARF corroborates: B4Blur::RenderBlurQuad
// builds a `VertexIterator5<VertexTypeFloat3, VertexTypeFloat4, VertexTypeFloat4,
// VertexTypeFloat4, VertexTypeFloat4>` (dwarfdump .../rwgpfxb4blur.cpp:270).
// That is why the blur program needs no offset uniform at all.
//
// ---------------------------------------------------------------------------
// WHICH PASS BINDS WHICH PROGRAM -- WHAT CAN AND CANNOT BE CONFIRMED.
// The DWARF declares B4Blur::{CommitRenderTargetToBackBuffer, DownSample, Apply,
// RenderBlurQuad, RenderRadialQuad, RenderScatterQuad, CalculateDownSampleTaps}
// (dwarfdump .../include/postfx/rwgpfxb4blur.h:183-211), but NONE of them exists
// in the X360 build: the whole ARTIST export set contains exactly three B4Blur
// functions (State::State @0x823F52E0, State::SetBlendSharpness @0x823F53A8,
// B4Blur::B4Blur @0x823FE9C8) and the ledger agrees (grep pasted in the report).
// The class is CONSTRUCTED and never DRIVEN on X360.  So the pass order cannot
// be "confirmed from the tree" -- there is no Render in the tree and no body to
// recover.  What each program COMPUTES is recovered below from its own
// microcode; which pass calls it is stated only where the pairing is forced by
// the member the constructor stores it in.
//
// ALPHA.  Three of the five pixel programs export a determinate alpha (scatter:
// a computed value; texture: blendFactor.x; down-sample: the fetch's forced 1).
// The blur program ends with the scalar unit's `retain_prev export0.___w [= PS]`
// and never issues a scalar op, so its alpha is the previous-scalar residual --
// INDETERMINATE on the console, the same finding the bloom and helper decodes
// recorded; written as 0 here so the PC result is deterministic, and flagged
// rather than pretended to be recovered.  The radial program also ends with
// `retain_prev`, but there its PS *is* determinate -- see the note at that entry.
//
// Build (identical recipe + flags to PostFxHelperProgramsPC.cpp):
//   fxc /nologo /T vs_3_0 /E mainB4BlurQuadVS       /O2 /Zpr /Fo b4blur_quad_vs.fxo    brn_postfx_b4blur.fx
//   fxc /nologo /T vs_3_0 /E mainB4BlurScatterVS    /O2 /Zpr /Fo b4blur_scatter_vs.fxo brn_postfx_b4blur.fx
//   fxc /nologo /T ps_3_0 /E mainB4BlurScatterPS    /O2 /Zpr /Fo b4blur_scatter_ps.fxo brn_postfx_b4blur.fx
//   fxc /nologo /T ps_3_0 /E mainB4BlurRadialPS     /O2 /Zpr /Fo b4blur_radial_ps.fxo  brn_postfx_b4blur.fx
//   fxc /nologo /T ps_3_0 /E mainB4BlurTexturePS    /O2 /Zpr /Fo b4blur_texture_ps.fxo brn_postfx_b4blur.fx
//   fxc /nologo /T ps_3_0 /E mainB4BlurDownSamplePS /O2 /Zpr /Fo b4blur_ds_ps.fxo      brn_postfx_b4blur.fx
//   fxc /nologo /T ps_3_0 /E mainB4BlurBlurPS       /O2 /Zpr /Fo b4blur_blur_ps.fxo    brn_postfx_b4blur.fx
// then wrapped by tools/assets/shaders/shader_transcode.py::
// build_pc_program_buffer(bytecode, shader_type) and published as
// b5-decomp/src/pc/gcm/renderengine/PostFxB4BlurProgramsPC.cpp.
// ============================================================================

// ============================================================================
// 1. THE BLUR QUAD'S VERTEX PROGRAM  (X360 0x82045148, m_quadVertexProgram)
//
// Microcode (10 slots, no constants):
//    3 : tfetch  r1.xyz1, r0.yxx, tf31        ; POSITION, w forced to 1
//    4 : max     export62.xyzw, r1, r1        ; -> oPos (the "mov" idiom)
//    5 : tfetch  r3.xyzw, r0.yxx, tf31        ; stream 1 (usage index 6)
//    6 : tfetch  r2.xyzw, r0.yxx, tf31        ; stream 2 (usage index 7)
//    7 : tfetch  r1.xyzw, r0.yxx, tf31        ; stream 3 (usage index 8)
//    8 : tfetch  r0.xyzw, r0.yxx, tf31        ; stream 4 (usage index 9)
//    9 : max     export0.xyzw, r3, r3         ; -> TEXCOORD0
//   10 : max     export1.xyzw, r2, r2         ; -> TEXCOORD1
//   11 : max     export2.xyzw, r1, r1         ; -> TEXCOORD2
//   12 : max     export3.xyzw, r0, r0         ; -> TEXCOORD3
//
// Five elements, in the order rwgpfxb4blur.cpp's constructor declares them:
// element 0 format 0x2A23B9 (FLOAT3) elementType 1 -> POSITION0; elements 1..4
// format 0x1A23A6 (FLOAT4) elementTypes 6/7/8/9 -> TEXCOORD0..3.  The quad is
// already in clip space and the position passes through with w = 1; the four
// float4 streams carry the SEVEN blur tap UVs (FINDING 3) untouched.
// ============================================================================
struct B4BlurQuadVertexIn
{
    float3 mPosition : POSITION;    // element 0, elementType 1
    float4 mTaps01   : TEXCOORD0;   // element 1, elementType 6
    float4 mTaps23   : TEXCOORD1;   // element 2, elementType 7
    float4 mTaps45   : TEXCOORD2;   // element 3, elementType 8
    float4 mTaps67   : TEXCOORD3;   // element 4, elementType 9
};

struct B4BlurQuadVertexOut
{
    float4 mPosition : POSITION;
    float4 mTaps01   : TEXCOORD0;
    float4 mTaps23   : TEXCOORD1;
    float4 mTaps45   : TEXCOORD2;
    float4 mTaps67   : TEXCOORD3;
};

B4BlurQuadVertexOut mainB4BlurQuadVS(B4BlurQuadVertexIn lIn)
{
    B4BlurQuadVertexOut lOut;
    lOut.mPosition = float4(lIn.mPosition, 1.0f);
    lOut.mTaps01   = lIn.mTaps01;
    lOut.mTaps23   = lIn.mTaps23;
    lOut.mTaps45   = lIn.mTaps45;
    lOut.mTaps67   = lIn.mTaps67;
    return lOut;
}

// ============================================================================
// 2. THE SCATTER / RADIAL QUAD'S VERTEX PROGRAM
//    (X360 0x82045600 == 0x82045AC0 byte-for-byte; FINDING 1.
//     m_scatterVertexProgram and m_radialVertexProgram)
//
// Microcode (9 slots):
//    3 : tfetch  r1.xyz1, r0.yxx, tf31          ; POSITION, w forced to 1
//    4 : max     export62.xyzw, r1, r1          ; -> oPos
//    5 : tfetch  r1.xy__, r0.yxx, tf31          ; stream 1 (usage index 6, FLOAT2)
//    6 : tfetch  r0.xyzw, r0.yxx, tf31          ; stream 2 (usage index 7, FLOAT4)
//    7 : add     export0.xy__, r1.xyyy, c0.xyyy ; oT0.xy = uv + uvOffset.xy
//    8 : max     export1.xyzw, r0, r0           ; -> TEXCOORD1
//
// The scatter descriptor is the three elements rwgpfxb4blur.cpp's constructor
// declares: FLOAT3 elementType 1, FLOAT2 elementType 6, FLOAT4 elementType 7.
// uvOffset is the same half-texel constant PfxHelper's quad vertex program
// takes; only .xy is ever added, exactly as encoded.
// ============================================================================
float4 uvOffset : register(c0);

struct B4BlurScatterVertexIn
{
    float3 mPosition : POSITION;    // elementType 1
    float2 mUv       : TEXCOORD0;   // elementType 6
    float4 mParams   : TEXCOORD1;   // elementType 7 -- the per-vertex scatter vectors
};

struct B4BlurScatterVertexOut
{
    float4 mPosition : POSITION;
    float2 mUv       : TEXCOORD0;
    float4 mParams   : TEXCOORD1;
};

B4BlurScatterVertexOut mainB4BlurScatterVS(B4BlurScatterVertexIn lIn)
{
    B4BlurScatterVertexOut lOut;
    lOut.mPosition = float4(lIn.mPosition, 1.0f);
    lOut.mUv       = lIn.mUv + uvOffset.xy;
    lOut.mParams   = lIn.mParams;
    return lOut;
}

// ---- the source sampler the three "blur family" pixel programs share --------
// CTAB name `low_texture`, sampler register 0 -- the same name the DepthOfField
// program uses for the half-resolution blurred copy.
sampler2D low_texture : register(s0);

// ============================================================================
// 3. THE SCATTER PIXEL PROGRAM  (X360 0x82045748, m_scatterPixelProgram)
//
// ONE tap of low_texture, displaced radially away from a centre by a
// pseudo-random ("scattered") amount, with a computed alpha -- i.e. the noisy
// smear a stack of these quads makes through m_scatterBlendState
// (E_FACTORY_BLEND_STATE_TRANSPARENT_MODULATE_NO_ALPHA_TEST_DEST_RGBA).
//
// Microcode (18 slots + a 64-byte literal block):
//   ; literal c254 = {0.25, 4, 0, 0}
//   ; literal c255 = {3.20367098, 2.83257604, 0.5, 3}
//    2 : mul     r2.xy__, r0.xyyy, c254.yyyy          ; uv * 4
//    3 : mul     r1.xyzw, r1.xzyw, r1.xzyw            ; (a,b,c,d) -> (a2,c2,b2,d2)
//    4 : add     r0.__zw, r1.xxxy, r1.zzzw            ; z = a2+b2, w = c2+d2
//    5 : frc     r1.xy__, r2'.xyyy                    ; frac(|uv*4|)
//    5   sqrt      r0.__z_, r0'.z                     ; |params.xy|
//    6 : cndge   r1.xy__, r2.xyyy, r1.xyyy, -r1.xyyy  ; sign restored == fmod(x,1)
//    7 : mad     r1.xy__, r1.xyyy, c254.xxxx, c255.wwww   ; *0.25 + 3
//    8 : mul     r1.x_z_, r1.yxxx, c255.yxxx          ; x = seed.y*2.832576, z = seed.x*3.203671
//    8   sqrt      r0.___w, r0'.w                     ; |params.zw|
//    9 : mul     r0.__zw, r0.wwwz, c1.zzzx            ; z = |params.zw|*c1.z, w = |params.xy|*c1.x
//    9   exp       r2.__z_, r1.z                      ; exp2(seed.x*3.203671)
//   10 : add     r1.__z_, r0.wwww, c1.yyyy [clamp]    ; falloff = sat(|params.xy|*c1.x + c1.y)
//   10   exp       r2.___w, r1.x                      ; exp2(seed.y*2.832576)
//   11 : add     r2.xy__, r0.xyyy, -c0.xyyy           ; delta = uv - centre
//   11   addsc0  r1.w = c1.w + r0.z [clamp]           ; alpha = sat(c1.w + |params.zw|*c1.z)
//   12 : mul     r3.xyz_, r2.xyzz, r2.xyww            ; x/y = delta^2 ; z = exp2(A)*exp2(B)
//   13 : frc     r0.__z_, r3.zzzz                     ; the noise fraction
//   13   adds      r0.___w, r3.xy                     ; dot(delta,delta)
//   14 : add     r0.__z_, r0.zzzz, -c255.zzzz         ; noise - 0.5
//   14   rsq       r0.___w, r0'.w                     ; 1/|delta|
//   15 : mul     r1.xy__, r2.xyyy, r0.wwww            ; normalize(delta)
//   15   mulsc0  r0.z = c0.w * r0.z                   ; noise * scatterScalars1.w
//   16 : mul     r0.__z_, r0.zzzz, r1.zzzz            ; * falloff
//   17 : mad     r0.xy__, r1.xyyy, r0.zzzz, r0.xyyy   ; uv + dir * amount
//   18 : tfetch  r1.xyz_, r0.xyx, tf0                 ; low_texture
//   19 : max     export0.xyzw, r1.xyzw, r1.xyzw       ; rgb = tap, a = r1.w (slot 11)
//
// The two scalar-with-constant ops are resolved with the Xenia encoding the
// step-2 decode established (constant = c<src3_reg>.[((swz>>6)+3)&3];
// register = r[(swz&0x3C) | (src_is_temp<<1) | (opc&1)].[swz&3]); re-running that
// reader over the DepthOfField package reproduces its two published readings
// (`r0.y = c0.y - r0.x`, `r0.y = c1.x * r0.y`) unchanged, which is the check
// that it is the right reader.  Here both resolve to r0.z, and the surrounding
// chain forces both (nothing else in r0 holds the noise at slot 15, and nothing
// else holds |params.zw|*c1.z at slot 11).
//
// SEMANTICS OF THE CONSTANTS, as the microcode uses them (the names are the
// CTAB's; the lane meanings are read off the code, not guessed):
//   scatterScalars1.xy = the scatter CENTRE in uv space
//   scatterScalars1.w  = the scatter DISTANCE scale (noise -> uv displacement)
//   scatterScalars2.x/.y = the MUL/ADD that turn |params.xy| into the [0,1] falloff
//   scatterScalars2.z/.w = the MUL/ADD that turn |params.zw| into the [0,1] alpha
//   scatterScalars1.z is never read by this program (a finding, not an omission).
// ============================================================================
float4 scatterScalars1 : register(c0);
float4 scatterScalars2 : register(c1);

float4 mainB4BlurScatterPS(float2 lUv : TEXCOORD0, float4 lParams : TEXCOORD1) : COLOR0
{
    // slots 2, 5, 6: fmod (not frac) -- the console restores the sign with cndge,
    // which is trunc-toward-zero.  For the non-negative UVs a full-screen quad
    // produces the two agree; fmod is written because it is what the asm does.
    const float2 lCell = fmod(lUv * 4.0f, 1.0f);
    const float2 lSeed = lCell * 0.25f + 3.0f;                                  // slot 7

    // slots 8-14: the hash.  exp2 of two scaled seeds, multiplied, fractioned and
    // centred -- a plain value-noise generator with no texture lookup.
    const float lNoise = frac(exp2(lSeed.x * 3.20367098f)
                            * exp2(lSeed.y * 2.83257604f)) - 0.5f;

    const float lParamLenXy = length(lParams.xy);                               // slots 3, 4, 5
    const float lParamLenZw = length(lParams.zw);                               // slots 3, 4, 8

    const float lFalloff = saturate(lParamLenXy * scatterScalars2.x
                                  + scatterScalars2.y);                         // slots 9, 10
    const float lAlpha   = saturate(scatterScalars2.w
                                  + lParamLenZw * scatterScalars2.z);           // slots 9, 11

    const float2 lDelta  = lUv - scatterScalars1.xy;                            // slot 11
    const float2 lDir    = normalize(lDelta);                                   // slots 12-15
    const float  lAmount = (lNoise * scatterScalars1.w) * lFalloff;             // slots 15, 16

    return float4(tex2D(low_texture, lUv + lDir * lAmount).rgb, lAlpha);        // slots 17-19
}

// ============================================================================
// 4. THE RADIAL PIXEL PROGRAM  (X360 0x82045C08, m_radialPixelProgram)
//
// EIGHT taps of low_texture marched along the line from the pixel toward a
// centre -- the classic radial ("speed streak") blur -- averaged with 1/8.
//
// Microcode (25 slots + a 64-byte literal block):
//   ; literal c254 = {5, 6, 7, 1}   c255 = {0.125, 0, 0, 0}
//    3 : mad     r1._yzw, c1.yyyy, c254.xxzy, c1.xxxx  ; k5 = c1.x+5c1.y, k7, k6
//    4 : dp3     r0.___w, c1.yxyy, c254.wwww           ; k2 = c1.x+2c1.y
//    4   adds      r4.__z_, c1.xy                      ; k1 = c1.x+  c1.y
//    5 : add     r4.xy__, -r0.xyyy, c0.xyyy            ; centre - uv
//    5   maxs      (no write)  PS = c1.x
//    6 : dp4     r0.__z_, c1.yxyy, c254.wwww           ; k3 = c1.x+3c1.y
//    6   muls_prev r3.x___, c0.z                       ; c0.z * c1.x   (== k0 * scale)
//    7 : mul     r3._yz_, r4.xxyy, c0.zzzz             ; delta = (centre-uv) * c0.z
//    7   addsc0  r1.x = c1.y + r0.z                    ; k4 = c1.x+4c1.y
//    8 : mad     r5.xyzw, r3.yzyz, r0.wwzz, r0.xyxy    ; taps k2, k3
//    9 : mad     r2.xyzw, r3.yzyz, r1.yyww, r0.xyxy    ; taps k5, k6
//   10 : mad     r6.xyzw, r3.xxyz, r4.xyzz, r0.xyxy    ; taps k0, k1
//   11 : mad     r3.xyzw, r3.yzyz, r1.xxzz, r0.xyxy    ; taps k4, k7
//   12-19: eight tfetch of tf0
//   20-26: seven adds -- the eight taps summed
//   27 : mul     export0.xyzw, r0.xyzz, c255.xxxx      ; * 0.125
//   27   retain_prev export0.___w   [= PS]
//
// THE STEP LADDER IS COMPLETE AND FORCED.  The eight tap multipliers decode to
// c1.x + i*c1.y for i = 0..7: i = 5/6/7 from the mad against the {5,6,7}
// literals, i = 1/2/3 from the adds/dp3/dp4 against the literal 1 (the dp3 and
// dp4 of (c1.y, c1.x, c1.y[, c1.y]) with (1,1,1[,1]) ARE "c1.x + 2c1.y" and
// "c1.x + 3c1.y"), i = 0 from the muls_prev/mad pair at slots 6/10, and i = 4
// from the scalar-with-constant at slot 7 (`c1.y + r0.z` with r0.z the k3 the
// dp4 had just written one slot earlier).  That the ONE operand the plain
// disassembly does not name lands exactly on the ONE missing rung of an
// otherwise complete 0..7 ladder is the check on the scalar decode.
//
// ALPHA.  The export's w is `retain_prev`, i.e. PS, and the last scalar op to
// run before it is slot 7's addsc0 -- so on the console the alpha of this
// program is DETERMINATE and equals k4 = scatterScalars2.x + 4*scatterScalars2.y.
// That is a compiler residue, not an authored value (the source plainly returned
// only a colour), but it is what the hardware exports, and the scatter/radial
// passes draw through a blend state whose destination factor reads alpha, so it
// is reproduced rather than replaced with a tidier 0.
// [FLAG: RECOVERED-BUT-INCIDENTAL -- if a later reading of the PS register's
//  lifetime across `exec` blocks says otherwise, THIS is the line to change; a
//  wrong choice here can only change how strongly the radial quad composites,
//  never what it samples.]
// ============================================================================
float4 mainB4BlurRadialPS(float2 lUv : TEXCOORD0) : COLOR0
{
    // slots 5, 6, 7: the per-tap step vector.  scatterScalars1.xy is the centre,
    // scatterScalars1.z the length scale; scatterScalars2.x/.y the base and the
    // increment of the eight-step ladder.
    const float2 lDelta = (scatterScalars1.xy - lUv) * scatterScalars1.z;

    // Written out rather than looped: the console issues EIGHT tfetch instructions
    // (slots 12-19) and fxc turns a `for` here into a `rep i0` dynamic loop with a
    // single texld, which is a different program.  `[unroll]` would do it too; the
    // eight lines are written so the ladder k = c1.x + i*c1.y is on the page.
    float3 lSum = tex2D(low_texture, lUv + lDelta * (scatterScalars2.x)).rgb;
    lSum += tex2D(low_texture, lUv + lDelta * (scatterScalars2.x + 1.0f * scatterScalars2.y)).rgb;
    lSum += tex2D(low_texture, lUv + lDelta * (scatterScalars2.x + 2.0f * scatterScalars2.y)).rgb;
    lSum += tex2D(low_texture, lUv + lDelta * (scatterScalars2.x + 3.0f * scatterScalars2.y)).rgb;
    lSum += tex2D(low_texture, lUv + lDelta * (scatterScalars2.x + 4.0f * scatterScalars2.y)).rgb;
    lSum += tex2D(low_texture, lUv + lDelta * (scatterScalars2.x + 5.0f * scatterScalars2.y)).rgb;
    lSum += tex2D(low_texture, lUv + lDelta * (scatterScalars2.x + 6.0f * scatterScalars2.y)).rgb;
    lSum += tex2D(low_texture, lUv + lDelta * (scatterScalars2.x + 7.0f * scatterScalars2.y)).rgb;

    const float lResidualAlpha = scatterScalars2.x + 4.0f * scatterScalars2.y;  // PS, see banner
    return float4(lSum * 0.125f, lResidualAlpha);
}

// ============================================================================
// 5. THE TEXTURE / BLEND PIXEL PROGRAM  (X360 0x820459B8, m_textureProgram)
//
// A modulated copy: the pass B4Blur::CommitRenderTargetToBackBuffer needs.
//
// Microcode (2 slots, no literal block):
//    1 : tfetch  r0.xyz_, r0.xyx, tf0            ; tex
//    2 : mul     export0.xyz_, r0.xyzz, c0.xxxx  ; rgb *= blendFactor.x
//    2   maxs      export0.___w, c0.xx           ; a  =  max(c0.x, c0.x) == blendFactor.x
//
// ⚠ THE SAMPLER IS CALLED `tex` HERE, not `low_texture` / `scene_texture`.  That
// is the CTAB's own name and it is reproduced verbatim; the constructor binds
// samplers by UNIT, never by name, so the name only has to match the console's
// so the two descriptor tables compare equal.
// Only .x of blendFactor is read -- .yzw are carried by the row and never used.
// ============================================================================
float4 blendFactor : register(c0);
sampler2D tex : register(s0);

float4 mainB4BlurTexturePS(float2 lUv : TEXCOORD0) : COLOR0
{
    return float4(tex2D(tex, lUv).rgb * blendFactor.x, blendFactor.x);
}

// ============================================================================
// 6. THE DOWN-SAMPLE PIXEL PROGRAM  (X360 0x820454E0, m_downsampleProgram)
//
// Microcode (3 slots, no literal block):
//    1 : add     r0.xy__, r0.xyyy, c0.xyyy   ; uv += sampleOffsets[0].xy
//    2 : tfetch  r0.xyz1, r0.xyx, tf0        ; scene_texture, w forced to 1
//    3 : max     export0.xyzw, r0, r0
//
// ⚠ ONE TAP, NOT SIXTEEN -- AND THE CTAB SAYS SO.  `sampleOffsets` is declared
// `matrix_rows float[4x4]` but with RegisterCount 1: the X360 compile of this
// program reads ROW 0 ONLY, and the microcode confirms it (a single tfetch, a
// single add against c0.xy).  The DecFIGS PS3 side fills sixteen floats
// (`float[16] blur4SampleOffsets` in B4Blur::DownSample, dwarfdump
// .../rwgpfxb4blur.cpp:849, filled by CalculateDownSampleTaps) -- so the X360
// build's program is a NARROWER variant of the same source than the PS3 build's.
// The declaration is kept float4x4 so the PC CTAB reproduces the console's
// `matrix_rows float[4x4]` class; only row 0 is read, which is what gives the PC
// image the same RegisterCount 1 the console image has.
// ============================================================================
float4x4 sampleOffsets : register(c0);
sampler2D scene_texture : register(s0);

float4 mainB4BlurDownSamplePS(float2 lUv : TEXCOORD0) : COLOR0
{
    return float4(tex2D(scene_texture, lUv + sampleOffsets[0].xy).rgb, 1.0f);
}

// ============================================================================
// 7. THE BLUR PIXEL PROGRAM  (X360 0x820452A8, m_blurProgram)
//
// SEVEN taps of low_texture at per-vertex UVs (FINDING 3), combined by a chain
// of three weighted mixes whose weights are LITERALS (FINDING 2):
// c255 = {0.75, 0.5, 0.66, 0}.
//
// Microcode (19 slots + a 64-byte literal block); r0..r3 are TEXCOORD0..3:
//    3 : tfetch  r4 <- r3.zw    (G)      7 : tfetch  r6 <- r0.zw    (B)
//    4 : tfetch  r5 <- r2.zw    (E)      8 : tfetch  r3 <- r1.xy    (C)
//    5 : tfetch  r2 <- r3.xy    (F)      9 : tfetch  r1 <- r0.xy    (A)
//    6 : tfetch  r7 <- r1.zw    (D)          -- r2.xy is NEVER fetched: 7 of 8
//   10 : add     r3 = C - A            13 : mad  r1 = (C-A)*0.5 + A   == lerp(A,C,.5)
//   11 : add     r0 = D - B            12 : mad  r0 = (D-B)*0.5 + B   == lerp(B,D,.5)
//   14 : add     r1 = r1 - F
//   15 : add     r0 = r0 - E           16 : mad  r0 = (r0-E)*0.66 + E == lerp(E,r0,.66)
//   17 : add     r0 = r0 - G           18 : mad  r0 = (r0-G)*0.75 + G == lerp(G,r0,.75)
//   19 : add     r0 = r0 + F
//   20 : mad     r0 = r1*0.75 + r0
//   21 : mul     export0.xyzw = r0 * 0.5
//   21   retain_prev export0.___w  [= PS]      ; alpha INDETERMINATE -> 0 here
//
// The chain reads as a centre-plus-ring reconstruction: A/C are one opposed pair
// averaged, B/D another, and E, G, F are single taps folded in with 0.66 / 0.75
// weights before the whole thing is halved.  No pass in the X360 build drives it
// (see "WHICH PASS BINDS WHICH PROGRAM" above), so the geometric meaning of the
// seven offsets cannot be pinned any further than the microcode pins it.
// ============================================================================
float4 mainB4BlurBlurPS(float4 lTaps01 : TEXCOORD0, float4 lTaps23 : TEXCOORD1,
                        float4 lTaps45 : TEXCOORD2, float4 lTaps67 : TEXCOORD3) : COLOR0
{
    const float3 lTapA = tex2D(low_texture, lTaps01.xy).rgb;   // slot 9
    const float3 lTapB = tex2D(low_texture, lTaps01.zw).rgb;   // slot 7
    const float3 lTapC = tex2D(low_texture, lTaps23.xy).rgb;   // slot 8
    const float3 lTapD = tex2D(low_texture, lTaps23.zw).rgb;   // slot 6
    const float3 lTapE = tex2D(low_texture, lTaps45.zw).rgb;   // slot 4 (lTaps45.xy unused)
    const float3 lTapF = tex2D(low_texture, lTaps67.xy).rgb;   // slot 5
    const float3 lTapG = tex2D(low_texture, lTaps67.zw).rgb;   // slot 3

    const float3 lInner = lerp(lTapA, lTapC, 0.5f);            // slots 10, 13
    float3 lAccum       = lerp(lTapB, lTapD, 0.5f);            // slots 11, 12
    lAccum              = lerp(lTapE, lAccum, 0.66f);          // slots 15, 16
    lAccum              = lerp(lTapG, lAccum, 0.75f);          // slots 17, 18
    lAccum              = lAccum + lTapF;                      // slot 19
    lAccum              = (lInner - lTapF) * 0.75f + lAccum;   // slots 14, 20

    return float4(lAccum * 0.5f, 0.0f);                        // slot 21
}
