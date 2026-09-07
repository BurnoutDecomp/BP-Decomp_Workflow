# hd_ui_flag -- BurnoutDecomp/b5-decomp#11 "Most in-game events UI like Road Rage or Showtime
# seems to use the SD instead of the HD UI" (+ the reporter's clue: the "HD compatible" text on
# the title screen).
#
# THE BUG, stated as a line in the log. The console carries ONE high-definition flag for the
# whole GUI: BrnRendererModule::Construct @0x8240A778 reads the video mode (XGetVideoMode ->
# fIsHiDef, and the front buffer's height >= 720 for its own mbIsHD), BrnGameModule::Construct
# hands the bool to BrnGui::GuiModule::Construct @0x82518028 as its last argument, and that
# stores it into the GUI cache: `*(gm + 1024649) = a6` == GuiCache +0x4B49 (mbIsHighDef). Every
# HD/SD choice the GUI makes at run time reads that byte:
#   * BootLegal::Update @0x824778D8         -- CLEAR => the "HD compatible" composite transitions
#                                              IN on the title screen (an SD-only advert)
#   * MainMapComponent::Construct @0x8245E5D4 -- CLEAR => the standard-def zoom table
#   * CrashNavMapMain @0x824CCC74             -- CLEAR => the 12000 SD pull-back, not 9000
#   * CrashNavDriverDetails @0x824BFEB8       -- CLEAR => the SD licence position
#   * RoadSignIconManager::Update @0x82517014 -- CLEAR => the SD distance-fade pair
# This build never wrote the byte (its GuiModule::Construct took no such argument), so the
# cache read 0 == SD everywhere -- while the apt/flapt/font BUNDLES were already picked HD
# (GuiResourceModule was constructed with HighDef == true by hand).
#
# THE WITNESSES.
#   RED  = the title screen's HDCompAnimator_mc receives apt_Transition -> 'transin'
#          ([AptComm] GetComponentData ... is an existing, capped boot probe), and there is no
#          "[GuiModule] high-definition=1" line because nothing computes the flag.
#   GREEN = the HD-composite reveal never fires, the GuiModule line says high-definition=1 for
#          the 1280x720 front buffer, and the FLAPT HUD bundle is still the HD one.
#
# Scenario: boot only (the title screen is the whole point), console -skipvideos latch on.
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case hd_ui_flag -ExpectFail -Label pre-fix
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case hd_ui_flag -Label post-fix
@{
  Name    = 'hd_ui_flag'
  Area    = 'gui'
  Bug     = 'BurnoutDecomp/b5-decomp#11 -- the GUI runs its SD layout choices (HD flag never written)'
  Frames  = $true                # title-screen stills for the issue thread
  FreshProfile = $false
  Run     = @{
    MaxSeconds = 40              # boot only: title screen is reached ~8 s in with SkipIntro
    SkipIntro  = $true           # the console -skipvideos latch
    AcceptGap  = 1.0
    FrameEvery = 30
  }
  DiagEnv = ''
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }

    # The scenario really reached the title screen's fade-in stage (E_STAGE_FADE_IN ran: the
    # ESRB animator is given its transition there, right after the HD-composite decision).
    @{ Kind = 'LogMatch'; Name = 'title screen fade-in stage ran'
       Pattern = '\[BootLegal\] stage 2 -> 3' }
    @{ Kind = 'LogMatch'; Name = 'ESRB animator was transitioned (the fade-in stage evaluated the HD byte)'
       Pattern = "\('esrb_anim'\) key='apt_Transition'" }

    # THE BUG. The "HD compatible" composite is revealed ONLY when the cache byte is CLEAR (SD).
    @{ Kind = 'LogCount'; Name = 'the SD-only "HD compatible" composite is NOT revealed'
       Pattern = "\('HDCompAnimator_mc'\) key='apt_Transition' -> 'transin'"; Max = 0 }

    # THE FLAG. GuiModule::Construct prints what it stored into the cache (once, unconditional).
    @{ Kind = 'LogMatch'; Name = 'GuiModule stored high-definition=1 into the GUI cache'
       Pattern = '\[GuiModule\] high-definition=1 ' }

    # The bundle side of the report: the event HUD composes from the HD flapt bundle.
    @{ Kind = 'LogMatch'; Name = 'the HD flapt HUD bundle is the one loaded'
       Pattern = "persistent apt bundle 'FLAPTHUD\.BUNDLE' -> loaded" }
    @{ Kind = 'LogCount'; Name = 'the SD flapt HUD bundle is never loaded'
       Pattern = "FLAPTHUDSD\.BUNDLE"; Max = 0 }
  )
}
