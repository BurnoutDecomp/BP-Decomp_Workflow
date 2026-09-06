# aptshadow_text -- Apt<->game bridge: text DROP SHADOWS are missing.
#
# The bug: Apt text objects that ask for a drop shadow (CgsAptString::Prepare sets
# mTextObject.mbDropShadow when the font name contains "drop" -- the shipped GUIAPT bundles
# use "B5EAConDisSDrop" and "MachineStd-BoldDrop" -- or when the effect is E_EFFECT_DROPSHADOW)
# render with no shadow at all: the console's second glyph submission
# (CgsGraphics::TextRenderer::RenderDropShadow @0x827FD968, offset +2/+3 px in
# mDropShadowColour, submitted BEFORE the main pass) was never ported into
# RenderStringInternal.
#
# The witness (opt-in BRN_FONT_DIAG=1, one line per DISTINCT string+flag, capped at 256):
#   [font] str="..." shadow=<0|1> quads=<n> shadowquads=<m> colour=<rgba> shadowcolour=<rgba> off=(x,y)
# RED  = shadow=1 strings exist but every shadowquads is 0 (the pass never runs).
# GREEN = shadowquads > 0 wherever shadow=1.
#
# Scenario: the baseline boot-drive. It walks the title screen, the junkyard car select
# (BRNCARSELECTMAIN carries both drop fonts) and the free-burn HUD, so a drop-shadow string
# is guaranteed to be submitted on at least one of them.
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case aptshadow_text -ExpectFail -Label pre-fix
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case aptshadow_text -Label post-fix
#
# ⭐⭐ SHORTENED 2026-09-06 (lane harness2). WHAT CHANGED AND WHAT DID NOT.
#   The Run block below now carries `SkipIntro` and `AcceptGap`, and a smaller `MaxSeconds`.
#   Nothing else about the scenario moved and NO CHECK was touched.
#     SkipIntro  passes the CONSOLE's own "-skipvideos" command-line latch (BrnMain.cpp:434 ->
#                BootVideos::Update's soft-reboot exit) so the EA-Franchise and Criterion VP6
#                logos are not played. It is not a harness bypass and it is not new game code.
#     AcceptGap  is HARNESS latency, not a game gate: the Accept pump used to press every 3.0 s
#                at car select, and the junkyard leg of a returning boot was measurably two
#                consecutive pump periods long (carsel 16.5s -> livery 19.9s -> accept 23.0s).
#   MEASURED, same build, same scenario: boot-to-DRIVING 23.0 s -> 16.2 s.
#   MaxSeconds is cut by that saving plus the slack this case's own schedule shows it never used.
#
@{
  Name    = 'aptshadow_text'
  Area    = 'gui/apt'
  Bug     = 'apt<>game bridge -- text drop shadows are missing (lane aptshadow, wave 2026-09-06)'
  Frames  = $true
  Run     = @{
    Drive      = $true
    MaxSeconds = 55
    SkipIntro = $true      # the console -skipvideos latch (see the banner)
    AcceptGap = 1.0        # harness pump latency, not a game gate
    FrameEvery = 60                          # ~120 frames; 30 dumped 835 MB per run
    Teleport   = '3040.7,-5.8,-1937.9,180'   # the road outside the junkyard exit (baseline)
  }
  DiagEnv = 'BRN_FONT_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }

    # The test must MEASURE something: at least one text object really asks for a shadow.
    @{ Kind = 'LogMatch'; Name = 'a drop-shadow text object was submitted'
       Pattern = '\[font\] .*shadow=1 ' }

    # ...and the shadow pass emitted quads for it. RED today: every shadowquads is 0.
    @{ Kind = 'LogValue'; Name = 'drop-shadow pass emits quads'
       Pattern = '\[font\] .*shadow=1 quads=\d+ shadowquads=(?<m>\d+)'
       Group = 'm'; Agg = 'max'; Min = 1 }

    # Every shadow=1 submission gets a shadow of the SAME quad count as the glyph run
    # (RenderDropShadow re-walks mapaVertices[leType] one-for-one).
    @{ Kind = 'LogValue'; Name = 'no shadow-1 string left without a shadow'
       Pattern = '\[font\] .*shadow=1 quads=\d+ shadowquads=(?<m>\d+)'
       Group = 'm'; Agg = 'min'; Min = 1 }

    # PIXELS. The free-burn HUD's "MILES DRIVEN : 0.0km" readout (a shadow=1 string, witness
    # quads=17) sits on an OPAQUE HUD strip, so this box is scene-independent: measured
    # dark_frac 0.093-0.098 across four frames of one run and two frames of another (two
    # different builds), sigma ~0.002. A black +2/+3 shadow under those white glyphs turns
    # mid-grey pixels pure black, so dark_frac must climb clear of that band.
    # Banked from the RED run 20260906_104006 (dark_frac 0.0977 on bb_007380).
    @{ Kind = 'Frame'; Name = 'MILES DRIVEN readout gains shadow pixels'
       At = 'last'; Region = '1015,624,1180,648'; Stat = 'dark_frac'; Min = 0.115 }
  )
}
