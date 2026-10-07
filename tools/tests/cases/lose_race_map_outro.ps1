# lose_race_map_outro -- LOSE A RACE WHILE A PAUSE (MAP) REQUEST LANDS WITH THE RESULTS (issue #32).
#
# GW4 lane LOSE. Junction 480852 (the race_lifecycle grid). The player starts the race, holds the
# throttle, and -DebugFinishPos 2 ends the race in 2nd place eight seconds into IN_PROGRESS
# (ModeManager::FinishCurrentModeNextUpdateWithFinishPosition, the console's own debug lever).
#
# THE LOSE PATH UNDER TEST, every hop witnessed:
#   FinishCurrentMode (finishType 1 == 2nd) -> OUTRO -> RESULTS -> ShowModeResults posts action 37
#   and hands the player car to the AI (action 7 selector 2 -> [ai-evt] PLAYER_TAKEN_OVER inControl 0)
#   -> GUI 291 -> InGame -> InstantResultsState (OnEnter .. OnLeave) -> TriggerExitResults posts
#   GUI 292 -> game event 26 -> ResultsAccept 4 -> 5 (QUIT) -> ExitCurrentMode TEARING DOWN ->
#   SendModeStopMessages action 7 -> [ai-evt] PLAYER_TAKEN_OVER inControl 1.
# THE ORACLE THAT THE PLAYER HAS THE CAR BACK is independent of every witness above: the harness
# releases the throttle at t+40 s (well after the event should be over) and the car must roll to a
# stop. While the AI owns the car (the #32 symptom) it keeps driving at speed with boost.
# THE #32 SUSPECT ON TOP: BRN_LOSE_PAUSE_WITH_291=map replays a Back press (the offline pause, the
# main map) that reaches InGame in the SAME update as GUI 291, through the console's own
# InGame::PauseGame. State::SendStateEvent keeps only the last event of an update, so before the
# fix the map replaced "TO_OFF_POST", the results screen never opened, no GUI 292 / game event 26
# was ever posted, and the AI kept the car. The harness closes the map 3 s later (Stop), as a
# player would. AFTER the fix InGame sees the cache still holding the un-dismissed results record
# of the running mode and re-sends "TO_OFF_POST" ([lose-diag] RECOVERED, FLAG PC fix).
# NOTE: A LOSS BANKS A LOSS INTO THE PROFILE; ProfileFixture restores the shared save.
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case lose_race_map_outro
#
@{
  Name    = 'lose_race_map_outro'
  Area    = 'events/lose'
  Bug     = 'issue #32 -- a pause request in the results update dropped GUI 291: no results, AI kept the car'
  Frames  = $false
  ProfileFixture = 'scratch\gameplay_wave\profile_backup\Profile.sav.pose250700'
  Run     = @{
    Drive           = $true
    MotionProbe     = $true
    Teleport        = '762.2,0.7,-2235.5,259'
    StartEvent      = $true
    EventFsm        = $true
    SkipTrainingTip = $true
    SkipIntro       = $true
    AcceptGap       = 1.0
    ThrottleScript  = '0:accel,40:none'
    DebugFinishPos  = 2
    DebugFinishAt   = 8
    MenuScript      = 'wait:HARNESS PAUSE WITH GUI 291;sleep:3;tap:Stop'
    MaxSeconds      = 90
  }
  DiagEnv = 'BRN_MODEMGR_DIAG=1,BRN_LOSE_DIAG=1,BRN_LOSE_PAUSE_WITH_291=map'
  Checks  = @(
    @{ Kind='NewAsserts'; Name='no NEW assert families' }
    @{ Kind='LogCount';   Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }

    @{ Kind='LogMatch'; Name='debug finish lever fired with position 2'; Pattern='HARNESS DEBUG FINISH POSITION \(BRN_DEBUG_FINISH_POS=2\)' }
    @{ Kind='LogMatch'; Name='FinishCurrentMode: race, 2nd (finishType 1)';
       Pattern='\[evt-finish\] FinishCurrentMode ENTERED mode 0 finishType 1 .*debugFinishPos 2' }
    @{ Kind='LogMatch'; Name='ShowModeResults: finishPosition 2, hasPlayerWon 0';
       Pattern='\[evt-finish\] ShowModeResults mode 0 finishPosition 2 .*hasPlayerWon 0' }
    @{ Kind='LogMatch'; Name='mode entered E_GMS_RESULTS'; Pattern='\[stunt\] mode state -> E_GMS_RESULTS' }
    @{ Kind='LogMatch'; Name='AI took the player car for the outro'; Pattern='\[ai-evt\] PLAYER_TAKEN_OVER inControl 0' }

    @{ Kind='LogMatch'; Name='the pause lever fired with GUI 291'; Pattern='\[lose-diag\] HARNESS PAUSE WITH GUI 291 \(map\)' }
    @{ Kind='LogMatch'; Name='results screen entered';  Pattern='INSTANT RESULTS DEBUG: OnEnter' }
    @{ Kind='LogMatch'; Name='results screen left';     Pattern='INSTANT RESULTS DEBUG: OnLeave' }
    @{ Kind='LogMatch'; Name='event 26 -> ResultsAccept RESULTS -> QUIT';
       Pattern='\[evt-finish\] event 26 -> ResultsAccept: mode state 4 -> 5' }
    @{ Kind='LogMatch'; Name='ExitCurrentMode tore the race down';
       Pattern='\[evt-finish\] ExitCurrentMode: TEARING DOWN mode type 0 ' }
    @{ Kind='LogMatch'; Name='control handed back to the player'; Pattern='\[ai-evt\] PLAYER_TAKEN_OVER inControl 1' }
    @{ Kind='LogCount'; Name='the map request DID replace the results transition (the #32 trigger happened)'; Pattern='\[lose-diag\] DROPPED GUI 291: "TO_OFF_POST" replaced in the same update by "MAP_MAIN"'; Min=1 }
    @{ Kind='LogCount'; Name='InGame recovered the dropped results screen (FLAG PC fix)'; Pattern='\[lose-diag\] RECOVERED: mode 0 results record pending'; Min=1; Max=1 }
    @{ Kind='LogCount'; Name='no RESULTS stall / load stall witness'; Pattern='\[lose-diag\] STALL'; Max=0 }

    @{ Kind='Script'; Name='after the throttle release the car rolls to a stop (player owns it)'; Script = {
        param($ctx)
        $d = $ctx.RunDir; while ($d -and -not (Test-Path (Join-Path $d 'tools\tests\tools'))) { $d = Split-Path $d }
        & (Join-Path $d 'tools\tests\tools\LOSE_control_back.ps1') -Lines $ctx.LogLines
      } }
  )
}
