# massive_impression -- baseline_boot_drive with the BRN_MASSIVE_DIAG witness on: the world
# impression pass must look advert renderables up in the fixed-up MassiveTable without asserting.
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case massive_impression
#
@{
  Name    = 'massive_impression'
  Area    = 'massive'
  Bug     = 'issue #34 stub wave: the Massive impression pass reads the MassiveTable lookup table'
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
  DiagEnv = 'BRN_MASSIVE_DIAG=1'
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
    @{ Kind = 'LogCount'; Name = 'info: Massive lookups witnessed'; Pattern = '\[FLAG PC witness\] \[massive\]' }
  )
}
