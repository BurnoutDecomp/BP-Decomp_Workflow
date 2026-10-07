# lose_road_rage_timeout -- LOSE A ROAD RAGE ON TIME AND GET THE CAR BACK (issue #32 family).
#
# GW4 lane LOSE. Junction 480861 (event 550480, Road Rage, game mode type 3). The player starts
# the event and drives without taking anyone down; BRN_LOSE_TIME_LIMIT=12 (FLAG PC harness lever in
# BrnModeManager_UpdateMode.cpp) replaces the authored time limit at the timer start so the run
# reaches the console's own time-up loss: ScoringSystem::HasModeTimeExpired -> E_ACTION_MODE_TIME_UP
# -> the time-up outro -> PlayerFinishedMode(timedOut) -> FinishCurrentMode (attempt failed) ->
# RESULTS -> results screen -> GUI 292 -> game event 26 -> QUIT -> ExitCurrentMode.
# ORACLE: the throttle is released at t+45 s and the car must roll to a stop (the AI no longer
# owns it). NOTE: a loss is banked into the profile; ProfileFixture restores the shared save.
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case lose_road_rage_timeout
#
@{
  Name    = 'lose_road_rage_timeout'
  Area    = 'events/lose'
  Bug     = 'issue #32 family -- a Road Rage lost on time must end and hand the car back'
  Frames  = $false
  ProfileFixture = 'scratch\gameplay_wave\profile_backup\Profile.sav.pose250700'
  Run     = @{
    Drive           = $true
    MotionProbe     = $true
    Teleport        = '3040.7,-5.8,-1937.9,180'
    StartEvent      = $true
    EventFsm        = $true
    SkipTrainingTip = $true
    SkipIntro       = $true
    AcceptGap       = 1.0
    ThrottleScript  = '0:accel,45:none'
    MaxSeconds      = 100
  }
  DiagEnv = 'BRN_MODEMGR_DIAG=1,BRN_LOSE_DIAG=1,BRN_LOSE_TIME_LIMIT=12'
  Checks  = @(
    @{ Kind='NewAsserts'; Name='no NEW assert families' }
    @{ Kind='LogCount';   Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }

    @{ Kind='LogMatch'; Name='harness time limit armed for Road Rage'; Pattern='\[lose-diag\] HARNESS TIME LIMIT \(BRN_LOSE_TIME_LIMIT=12[.0]*\) mode type 3 ' }
    @{ Kind='LogMatch'; Name='FinishCurrentMode: road rage, timed out, attempt failed';
       Pattern='\[evt-finish\] FinishCurrentMode ENTERED mode 3 .*attemptSucceeded 0 timedOut 1 ' }
    @{ Kind='LogMatch'; Name='ShowModeResults: road rage, hasPlayerWon 0';
       Pattern='\[evt-finish\] ShowModeResults mode 3 .*hasPlayerWon 0' }
    @{ Kind='LogMatch'; Name='mode entered E_GMS_RESULTS'; Pattern='\[stunt\] mode state -> E_GMS_RESULTS' }
    @{ Kind='LogMatch'; Name='AI took the player car for the outro'; Pattern='\[ai-evt\] PLAYER_TAKEN_OVER inControl 0' }

    @{ Kind='LogMatch'; Name='results screen entered';  Pattern='INSTANT RESULTS DEBUG: OnEnter' }
    @{ Kind='LogMatch'; Name='results screen left';     Pattern='INSTANT RESULTS DEBUG: OnLeave' }
    @{ Kind='LogMatch'; Name='event 26 -> ResultsAccept RESULTS -> QUIT';
       Pattern='\[evt-finish\] event 26 -> ResultsAccept: mode state 4 -> 5' }
    @{ Kind='LogMatch'; Name='ExitCurrentMode tore the race down';
       Pattern='\[evt-finish\] ExitCurrentMode: TEARING DOWN mode type 3 ' }
    @{ Kind='LogMatch'; Name='control handed back to the player'; Pattern='\[ai-evt\] PLAYER_TAKEN_OVER inControl 1' }
    @{ Kind='LogCount'; Name='no lose-diag stall / dropped / recovery witness'; Pattern='\[lose-diag\] (STALL|DROPPED|RECOVERED)'; Max=0 }

    @{ Kind='Script'; Name='after the throttle release the car rolls to a stop (player owns it)'; Script = {
        param($ctx)
        $d = $ctx.RunDir; while ($d -and -not (Test-Path (Join-Path $d 'tools\tests\tools'))) { $d = Split-Path $d }
        & (Join-Path $d 'tools\tests\tools\LOSE_control_back.ps1') -Lines $ctx.LogLines
      } }
  )
}
