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
    @{ Kind = 'Script';   Name = 'the car moved';  Script = {
        param($ctx)
        # marks.txt: "DRIVE    <verdict>" -- "MOVED path=123.4m net=..." or UNKNOWN/n-a/STATIONARY
        $l = ($ctx.MarksText -split "`n") | Where-Object { $_ -match '^DRIVE\s+' } | Select-Object -First 1
        if (-not $l) { return @{ Pass = $false; Detail = 'no DRIVE line in marks.txt' } }
        $ok = ($l -match 'path=(?<p>[\d.,]+)m') -and ([double](($Matches.p) -replace ',', '.') -gt 20)
        return @{ Pass = $ok; Detail = $l.Trim() }
      } }
  )
}
