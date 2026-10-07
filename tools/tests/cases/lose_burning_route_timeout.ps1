# lose_burning_route_timeout -- LOSE A BURNING ROUTE ON TIME AND GET THE CAR BACK (issue #32 family).
#
# GW4 lane LOSE. Junction 480860 (event 558944, Burning Route, game mode type 5), the
# burning_route_lifecycle grid. The player starts the event and drives away from the finish;
# BRN_LOSE_TIME_LIMIT=5 (FLAG PC harness lever in BrnModeManager_UpdateMode.cpp) sets the three
# medal times to 5 s at the timer start (ScoringSystem::SetMedalModeTimer keeps its own bronze + 10 s
# outer bound), so the run reaches the console's own time-up FAILURE: E_ACTION_MODE_TIME_UP with
# succeeded 0 -> the time-up outro -> PlayerFinishedMode(timedOut) -> FinishCurrentMode -> RESULTS
# -> results screen -> GUI 292 -> game event 26 -> QUIT -> ExitCurrentMode.
# ORACLE: the throttle is released at t+50 s and the car must roll to a stop.
# NOTE: a loss is banked into the profile; ProfileFixture restores the shared save.
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case lose_burning_route_timeout
#
@{
  Name    = 'lose_burning_route_timeout'
  Area    = 'events/lose'
  Bug     = 'issue #32 family -- a Burning Route lost on time must end and hand the car back'
  Frames  = $false
  ProfileFixture = 'scratch\gameplay_wave\profile_backup\Profile.sav.pose250700'
  Run     = @{
    Drive           = $true
    MotionProbe     = $true
    Teleport        = '2857.0,-4.5,-2160.1,90'
    StartEvent      = $true
    EventFsm        = $true
    SkipTrainingTip = $true
    SkipIntro       = $true
    AcceptGap       = 1.0
    ThrottleScript  = '0:accel,50:none'
    MaxSeconds      = 100
  }
  DiagEnv = 'BRN_MODEMGR_DIAG=1,BRN_LOSE_DIAG=1,BRN_LOSE_TIME_LIMIT=5'
  Checks  = @(
    @{ Kind='NewAsserts'; Name='no NEW assert families' }
    @{ Kind='LogCount';   Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }

    @{ Kind='LogMatch'; Name='harness time limit armed for Burning Route'; Pattern='\[lose-diag\] HARNESS TIME LIMIT \(BRN_LOSE_TIME_LIMIT=5[.0]*\) mode type 5 ' }
    @{ Kind='LogMatch'; Name='FinishCurrentMode: burning route, timed out, attempt failed';
       Pattern='\[evt-finish\] FinishCurrentMode ENTERED mode 5 .*attemptSucceeded 0 timedOut 1 ' }
    # The record's finish position is the medal target + 1 and nothing in the console image moves
    # the target off GOLD on time (only SetTimeLimitSeconds / SetMedalModeTimer /
    # CheckRoadRageMedalAwarded / SetupGameMode store it), so a timed-out route reports
    # finishPosition 1 / hasPlayerWon 1 here exactly as the console arithmetic does; the loss is
    # carried by the timed-out byte (FinishCurrentMode above, record +0xE1).
    @{ Kind='LogMatch'; Name='ShowModeResults ran for the burning route';
       Pattern='\[evt-finish\] ShowModeResults mode 5 ' }
    @{ Kind='LogMatch'; Name='mode entered E_GMS_RESULTS'; Pattern='\[stunt\] mode state -> E_GMS_RESULTS' }
    @{ Kind='LogMatch'; Name='AI took the player car for the outro'; Pattern='\[ai-evt\] PLAYER_TAKEN_OVER inControl 0' }

    @{ Kind='LogMatch'; Name='results screen entered';  Pattern='INSTANT RESULTS DEBUG: OnEnter' }
    @{ Kind='LogMatch'; Name='results screen left';     Pattern='INSTANT RESULTS DEBUG: OnLeave' }
    @{ Kind='LogMatch'; Name='event 26 -> ResultsAccept RESULTS -> QUIT';
       Pattern='\[evt-finish\] event 26 -> ResultsAccept: mode state 4 -> 5' }
    @{ Kind='LogMatch'; Name='ExitCurrentMode tore the race down';
       Pattern='\[evt-finish\] ExitCurrentMode: TEARING DOWN mode type 5 ' }
    @{ Kind='LogMatch'; Name='control handed back to the player'; Pattern='\[ai-evt\] PLAYER_TAKEN_OVER inControl 1' }
    @{ Kind='LogCount'; Name='no lose-diag stall / dropped / recovery witness'; Pattern='\[lose-diag\] (STALL|DROPPED|RECOVERED)'; Max=0 }

    @{ Kind='Script'; Name='after the throttle release the car rolls to a stop (player owns it)'; Script = {
        param($ctx)
        $d = $ctx.RunDir; while ($d -and -not (Test-Path (Join-Path $d 'tools\tests\tools'))) { $d = Split-Path $d }
        & (Join-Path $d 'tools\tests\tools\LOSE_control_back.ps1') -Lines $ctx.LogLines
      } }
  )
}
