# baseline_boot_drive -- the run every other case is a variation of: boot, junkyard, car
# select, exit, DRIVING, teleport onto a road and hold the throttle. No asserts, no exceptions,
# the car actually moves. If THIS is red, no other case's failure means anything yet.
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case baseline_boot_drive
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
  Name    = 'baseline_boot_drive'
  Area    = 'harness'
  Bug     = 'none -- the baseline'
  Frames  = $false
  # flow_run.ps1 parameters, splatted verbatim. OutDir/FrameDir/DiagEnv/LockTimeoutSec are the
  # runner's; everything else flow_run accepts goes here (see its param() block).
  Run     = @{
    Drive       = $true
    MotionProbe = $true            # the DRIVE verdict in marks.txt needs [motion] samples
    MaxSeconds  = 50
    SkipIntro  = $true      # the console -skipvideos latch (see the banner)
    AcceptGap  = 1.0        # harness pump latency, not a game gate
    Teleport    = '3040.7,-5.8,-1937.9,180'   # the road outside the junkyard exit
  }
  DiagEnv = ''
  Checks  = @(
    # Assert lines look like "[ASSERT 20] IsInWorld() (path\BrnRaceCar.cpp:492)"; exceptions
    # "[EXCEPTION] EXCEPTION_ACCESS_VIOLATION (0xC0000005) at ...". NewAsserts tolerates the
    # families in tools\tests\known_asserts.txt (another lane's noise) and names any NEW one.
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'assert lines (info: known noise counts too)'; Pattern = '\[ASSERT \d+\]'; Max = 200 }
    @{ Kind = 'LogCount';   Name = 'no exceptions';  Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';     Name = 'reached DRIVING'; Phase = 'DRIVING' }
    # The car moved: path from the teleport seat UP TO THE FIRST RESPAWN (Get-DriveSegment in
    # _checks.ps1). Until 2026-10-06 this read marks.txt's DRIVE path=, which was measured after
    # the LAST >20 m placement jump: a wreck + respawn late in the window scored 0..13 m for a
    # 300 m drive (5 false reds 09-08..09-23, each with a GAMEWRECKED right before the respawn).
    @{ Kind = 'Script';   Name = 'the car moved (teleport seat -> first respawn, > 20 m)';  Script = {
        param($ctx)
        $s = Get-DriveSegment $ctx.LogLines
        if (-not $s.Known) { return @{ Pass = $false; Detail = ("{0} [motion] sample(s): no car position in this log" -f $s.Samples) } }
        return @{ Pass = ($s.Path -gt 20.0); Detail = ("path={0:f1}m net={1:f1}m samples {2}..{3} teleported={4} later respawns={5}" -f `
                  $s.Path, $s.Net, $s.FromSample, $s.ToSample, $s.Teleported, $s.Respawns) }
      } }
    # A wreck is gameplay, not a red: reported on its own line so a red 'car moved' is never
    # confused with a respawn, and a wreck-heavy run is visible at a glance.
    @{ Kind = 'LogCount'; Name = 'info: GAMEWRECKED hud messages (gameplay, never fails)'; Pattern = 'STARTING MESSAGE NAMED "GAMEWRECKED' }
  )
}
