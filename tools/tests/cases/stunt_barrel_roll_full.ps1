# stunt_barrel_roll_full -- issue #23: a barrel roll in a Stunt Run stays "held" and never completes
# for the multiplier. This case rolls the car a FULL turn in a running Stunt Run and follows the
# roll through every stage the console scores it in.
#
# THE SCENARIO. One boot, one Stunt Run (junction 480897), then ramp shots fired INSIDE the event:
#   shot 0  places the car in the junction at rest so -StartEvent/-EventFsm start the event there.
#   shot 1+ place the car on the -Jump ramp approach (x~3027) at 44 m/s on the ramp axis, the
#           same shots stunt_barrel_roll uses (they land on the wheels without a crash).
# The ramp alone rolls the car ~220 degrees at the take-off roll limit, which the scorer rates
# GOOD but not AWESOME, and only an AWESOME roll is counted into the multiplier. So this case
# arms the PC harness lever BRN_STUNT23_ROLL (StuntOffencesManager, physics side): on each
# take-off it holds the roll rate at 14 rad/s until the car has turned >= 330 degrees and is
# upright again, then removes the roll rate so the car lands on its wheels. Detection, scoring,
# banking and the HUD feed are the console's own code; the lever only writes angular velocity.
#
# WITNESSES (all opt-in PC witnesses):
#   [stunt23] lever takeoff/done/end ...   the lever (BRN_STUNT23_ROLL)
#   [stunt23] f=... / HELD ...             StuntModeScoring::Update, state changes (BRN_STUNT23_DIAG)
#   [stunt23] bank ...                     StuntModeScoring::UpdateBufferedScore commit (BRN_STUNT23_DIAG)
#   [stunt] award / combo banked ...       UpdateScore / EndCombo (BRN_STUNT_DIAG)
#   [stuntair] takeoff/land ...            StuntOffencesManager (BRN_ROLL_PROBE)
# The verdict is computed by tools\tests\tools\STUNT23_roll_report.py over the run's log; run it
# by hand on any log with `python tools\tests\tools\STUNT23_roll_report.py <BrnGame.log>`.
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case stunt_barrel_roll_full
#
@{
  Name    = 'stunt_barrel_roll_full'
  Area    = 'events/stunt'
  Bug     = 'issue #23 -- a barrel roll in a Stunt Run stays in progress and never completes for the multiplier'
  Frames  = $false
  ProfileFixture = 'scratch\gameplay_wave\profile_backup\Profile.sav.pose250700'
  Run     = @{
    Drive           = $true
    MotionProbe     = $true
    StartEvent      = $true
    EventFsm        = $true
    SkipTrainingTip = $true
    SkipIntro       = $true
    AcceptGap       = 1.0
    MaxSeconds      = 100
    CrashSweep      = '2641.5,1.3,-1723.8'
    CrashSweepShots = '2641.5/1.3/-1723.8/169:0,3027/-9.2/-330/0:44,3027/-9.2/-330/0:44,3027/-9.2/-330/0:44'
    CrashSweepSettle = 720
    CrashSweepMax    = 1200
  }
  DiagEnv = 'BRN_PROP_DIAG=1,BRN_STUNT_DIAG=1,BRN_ROLL_PROBE=1,BRN_STUNT23_DIAG=1,BRN_STUNT23_ROLL=14,BRN_STUNT23_ROLL_DEG=330'
  Checks  = @(
    @{ Kind='NewAsserts'; Name='no NEW assert families' }
    @{ Kind='LogCount'; Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }
    @{ Kind='Mark';     Name='event started (action 23 -> gui 93)'; Cue='e-start' }
    @{ Kind='Mark';     Name='mode reached E_GMS_IN_PROGRESS';      Cue='e-inprog' }
    @{ Kind='LogCount'; Name='the lever rolled the car a full turn and stopped it upright'
       Pattern='\[stunt23\] lever done jump=\d+ turnedDeg=(3[3-9]\d|[4-9]\d\d)'; Min=1 }
    @{ Kind='LogCount'; Name='never HELD: no live roll rotation 90 frames after a touchdown'
       Pattern='\[stunt23\] HELD'; Max=0 }
    @{ Kind='Script'; Name='STUNT23 report: roll detected -> banked AWESOME with rolls -> multiplier up -> combo ends scored -> next trick scored'; Script = {
        param($ctx)
        $py = 'C:\Python310\python.exe'
        $tool = Join-Path $ctx.RunDir '..\..\..\..\..\tools\tests\tools\STUNT23_roll_report.py'
        $tool = [System.IO.Path]::GetFullPath($tool)
        $env:PYTHONUTF8 = '1'
        $out = & $py $tool $ctx.Log --verdict 2>&1
        $verdict = ($out | Where-Object { $_ -match '^VERDICT ' } | Select-Object -Last 1)
        $detail = ($out | Where-Object { $_ -match '^SUMMARY ' } | Select-Object -Last 1)
        if (-not $verdict) { return @{ Pass = $false; Detail = ("report tool produced no verdict: {0}" -f (($out | Select-Object -Last 3) -join ' | ')) } }
        return @{ Pass = ($verdict -match '^VERDICT PASS'); Detail = ("{0} {1}" -f $verdict, $detail) }
    } }
  )
}
