# lose_marked_man_wrecked -- LOSE A MARKED MAN BY GETTING TOTALLED AND GET THE CAR BACK (issue #32 family).
#
# GW4 lane LOSE. Junction 480856 (event 560148, Marked Man / SurvivorMode, game mode type 8), the
# marked_man_lifecycle grid. The player starts the event and holds the throttle; BRN_AI_MADNESS=1
# (the existing rival-aggression knob) lets the rivals wreck the car quickly. Each player wreck
# reaches ModeManager::UpdateCurrentMode arm 13 -> ScoringSystem::OnRoadRagePlayerCrashed; at the
# event's wreck limit the scorer marks the player totalled, and after the grace time
# PlayerFinishedMode(car destroyed) -> FinishCurrentMode -> RESULTS -> results screen -> GUI 292 ->
# game event 26 -> QUIT -> ExitCurrentMode. (Placing the car into walls or parked cars with
# -CrashSweep did not produce wrecks; the rivals do.)
# ORACLE: the throttle is released at t+200 s and the car must roll to a stop
# (or, -CoastWindow 20, be clearly coasting down when the run ends).
# NOTE: a loss is banked into the profile; ProfileFixture restores the shared save.
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case lose_marked_man_wrecked
#
@{
  Name    = 'lose_marked_man_wrecked'
  Area    = 'events/lose'
  Bug     = 'issue #32 family -- a Marked Man lost by being totalled must end and hand the car back'
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
    ThrottleScript  = '0:accel,200:none'
    Teleport        = '1634.3,-1.9,-2284.1,292'
    MaxSeconds      = 275
  }
  DiagEnv = 'BRN_MODEMGR_DIAG=1,BRN_LOSE_DIAG=1,BRN_AI_MADNESS=1'
  Checks  = @(
    @{ Kind='NewAsserts'; Name='no NEW assert families' }
    @{ Kind='LogCount';   Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }

    @{ Kind='LogMatch'; Name='SurvivorMode::Start ran'; Pattern='GetTrafficDensitySurvival\(\) :' }
    @{ Kind='LogCount'; Name='player wrecks reached the road-rage/marked-man crash arm'; Pattern='\[rr\] OnRoadRagePlayerCrashed: crashes '; Min=1 }
    @{ Kind='LogMatch'; Name='FinishCurrentMode: marked man, car destroyed';
       Pattern='\[evt-finish\] FinishCurrentMode ENTERED mode 8 .*carDestroyed 1 ' }
    @{ Kind='LogMatch'; Name='ShowModeResults: marked man finishPosition 2, hasPlayerWon 0';
       Pattern='\[evt-finish\] ShowModeResults mode 8 finishPosition 2 .*hasPlayerWon 0' }
    @{ Kind='LogMatch'; Name='mode entered E_GMS_RESULTS'; Pattern='\[stunt\] mode state -> E_GMS_RESULTS' }
    @{ Kind='LogMatch'; Name='AI took the player car for the outro'; Pattern='\[ai-evt\] PLAYER_TAKEN_OVER inControl 0' }

    @{ Kind='LogMatch'; Name='results screen entered';  Pattern='INSTANT RESULTS DEBUG: OnEnter' }
    @{ Kind='LogMatch'; Name='results screen left';     Pattern='INSTANT RESULTS DEBUG: OnLeave' }
    @{ Kind='LogMatch'; Name='event 26 -> ResultsAccept RESULTS -> QUIT';
       Pattern='\[evt-finish\] event 26 -> ResultsAccept: mode state 4 -> 5' }
    @{ Kind='LogMatch'; Name='ExitCurrentMode tore the race down';
       Pattern='\[evt-finish\] ExitCurrentMode: TEARING DOWN mode type 8 ' }
    @{ Kind='LogMatch'; Name='control handed back to the player'; Pattern='\[ai-evt\] PLAYER_TAKEN_OVER inControl 1' }
    @{ Kind='LogCount'; Name='no lose-diag stall / dropped / recovery witness'; Pattern='\[lose-diag\] (STALL|DROPPED|RECOVERED)'; Max=0 }

    @{ Kind='Script'; Name='after the throttle release the car rolls to a stop (player owns it)'; Script = {
        param($ctx)
        $d = $ctx.RunDir; while ($d -and -not (Test-Path (Join-Path $d 'tools\tests\tools'))) { $d = Split-Path $d }
        & (Join-Path $d 'tools\tests\tools\LOSE_control_back.ps1') -Lines $ctx.LogLines -CoastWindow 20
      } }
  )
}
