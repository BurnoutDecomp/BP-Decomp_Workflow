# APTL_map_prompt_screens -- lane APTL copy of map_prompt_screens with MaxSeconds 75 so the RB leg (DRIVING+27s) runs.
# map_prompt_screens -- issue #33 follow-up (GW4 lane MAPPROMPT): the other pause screens that
# carry B5StaticHelpItem button prompts. START opens CN_D_DETAIL (driver details), then RB moves
# right to CN_SETTINGS ("UNDER THE HOOD"). (A second RB reaches OnlinePlay, which is still an
# un-reconstructed screen on PC and draws nothing -- not walked here.) The two Apt runtime fixes behind #33 (the
# seek path keeps a PLACE record's clipActions; the end-of-timeline wrap replays frame 0) apply
# to every Apt movie, so these screens must also draw no "undefined" and keep their prompts.
# Frames: bb_* in the run dir (one per second) show each screen's prompt bar.
#
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case map_prompt_screens
#
@{
  Name    = 'APTL_map_prompt_screens'
  Area    = 'gui/map'
  Bug     = 'issue #33 -- help-item prompts on the pause screens (driver details, settings, ...)'
  Frames  = $true
  ProfileFixture = 'C:\Users\Niaz\burnout-pr\BP-Decomp_Workflow\scratch\gameplay_wave\profile_backup\Profile.sav.pose250700'   # the pose save; run_case restores the box save
  Run     = @{
    Drive       = $true
    MaxSeconds  = 75
    SkipIntro   = $true
    AcceptGap   = 1.0
    FrameEvery  = 60
    Teleport    = '3040.7,-5.8,-1937.9,180'
    PauseAt     = '15'
    PauseTarget = 'driver'
    ShoulderAt  = '27:R:1.0'
  }
  DiagEnv = 'BRN_FONT_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'LogMatch';   Name = 'driver details drew its title'; Pattern = '\[font\] path=apt str="DRIVER DETAILS"' }
    @{ Kind = 'LogMatch';   Name = 'a pause screen drew its back prompt'; Pattern = '\[font\] path=apt str="RETURN TO GAME"' }
    @{ Kind = 'LogMatch';   Name = 'settings drew its A SELECT prompt'; Pattern = '\[font\] path=apt str="SELECT"' }
    @{ Kind = 'LogCount';   Name = 'no drawn string reads "undefined"';
       Pattern = '\[font\] path=\w+ str="[^"]*undefined'; Max = 0 }
  )
}
