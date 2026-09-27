# marked_man_win -- MARKED MAN (SurvivorMode), START TO RESULTS, WON THROUGH THE GAME'S OWN FINISH.
#
# Race wave 2026-09-27, lane H. The marked_man_lifecycle scenario (junction 480856, event 560148,
# data mode 3 SURVIVOR, game mode type 8) plus -WinTeleport. One checkpoint: the finish, landmark
# region 4673, a 40.0 x 61.8 x 6.6 m box at (-3293.4, 486.0, -3520.2), about 5.3 km from the grid.
#
# THE SCENARIO. Teleport to the junction grid, start the event, hold the throttle. Five seconds of
# IN_PROGRESS later -WinTeleport (BRN_WIN_TELEPORT, b5 GameSource/Game/BrnHarnessWinTeleport.cpp)
# places the player's car INTO the finish box through the game's own
# ActiveRaceCar::RequestPlaceOnTrack (hop kind=finish why=direct: Marked Man passes unless the car
# was totalled, so there is no staging hop). The next frame the landmark test sees the car inside
# the box -> ModeManager::RaceCarTriggersLandmark -> RaceCarFinishes. FinishCurrentMode's marked-man
# arm is PASSED (finish type 9) unless timed out or totalled; ShowModeResults' finishPosition is
# `mbPlayerFinishedCarDestroyed ? 2 : 1`. NOTHING IS FORCED by the harness; say it was teleported.
# The delay is short on purpose: the rivals' threat ramp could total the car if it waited.
# NOTE: A WIN BANKS A MEDAL INTO THE SLOT'S Memcard PROFILE.
#
# WITNESSES (source of every pattern; the [evt-finish] pair needs BRN_MODEMGR_DIAG, set below):
#   [win-teleport] armed / hop / seat / done / FAIL    b5 GameSource/Game/BrnHarnessWinTeleport.cpp
#                                                      :289 / :451 / :481 / :530 / :276 and :543
#   [win-teleport] request N -> RequestPlaceOnTrack(   b5 GameSource/World/BrnPlaceOnTrackManager.cpp:935
#   [stunt] mode state -> E_GMS_...                    b5 GameSource/GameState/ModeManager/GameModes/BrnGameMode.cpp:610
#   lpProgressionRankData->GetTrafficDensitySurvival() SurvivorMode::Start's own debug print (see marked_man_lifecycle)
#   [evt-finish] FinishCurrentMode ENTERED mode ..     b5 GameSource/GameState/ModeManager/BrnModeManager_Finish.cpp:678
#   [evt-finish] ShowModeResults mode ..               b5 GameSource/GameState/ModeManager/BrnModeManager_Finish.cpp:931
#   [evt-finish] ***** HARNESS DEBUG FINISH POSITION   b5 GameSource/GameState/ModeManager/BrnModeManager_WorldTick.cpp:392
# `debugFinishPos -1` is RaceCarFinishes' own store for the player (BrnModeManager.cpp:618).
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case marked_man_win -Slot 1
#
@{
  Name    = 'marked_man_win'
  Area    = 'events/marked_man'
  Bug     = 'race wave lane H -- no harness case had ever WON a Marked Man; the win teleport drives the real landmark finish'
  Frames  = $false
  Run     = @{
    Drive           = $true
    MotionProbe     = $true
    Teleport        = '1634.3,-1.9,-2284.1,292'
    StartEvent      = $true
    EventFsm        = $true
    SkipTrainingTip = $true
    SkipIntro       = $true      # the console -skipvideos latch
    AcceptGap       = 1.0        # harness pump latency, not a game gate
    ThrottleScript  = '0:accel'
    WinTeleport     = 5          # seconds of IN_PROGRESS before the finish hop
    # IN_PROGRESS lands at ~29 s wall (marked_man_lifecycle); +5 s delay, then OUTRO/RESULTS.
    MaxSeconds      = 90
  }
  DiagEnv = 'BRN_MODEMGR_DIAG=1'
  Checks  = @(
    @{ Kind='NewAsserts'; Name='no NEW assert families' }
    @{ Kind='LogCount';   Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }

    # ---- it is Marked Man ------------------------------------------------------------------------
    @{ Kind='LogMatch'; Name='SurvivorMode::Start ran'; Pattern='GetTrafficDensitySurvival\(\) :' }

    # ---- the harness armed and acted (a silent no-op must not pass) ---------------------------
    @{ Kind='LogMatch'; Name='win teleport armed';                  Pattern='\[win-teleport\] armed delay=' }
    @{ Kind='LogCount'; Name='win teleport issued a hop';           Pattern='\[win-teleport\] hop \d+ landmark='; Min=1 }
    @{ Kind='LogCount'; Name='no win-teleport refusal or give-up';  Pattern='\[win-teleport\] FAIL'; Max=0 }
    @{ Kind='LogCount'; Name='World half handed the hop to RequestPlaceOnTrack'; Pattern='\[win-teleport\] request \d+ -> RequestPlaceOnTrack\('; Min=1 }
    @{ Kind='LogMatch'; Name='finish hop into the marked-man finish';            Pattern='\[win-teleport\] hop \d+ landmark=0 region=\d+ id=\d+ -> .* kind=finish .* why=direct mode=8 ' }
    @{ Kind='LogMatch'; Name='the finish hop seated INSIDE the landmark box';    Pattern='\[win-teleport\] seat hop \d+ kind=finish landed .* inside=1' }
    @{ Kind='LogCount'; Name='the debug finish lever was NOT used';              Pattern='HARNESS DEBUG FINISH POSITION'; Max=0 }

    # ---- the lifecycle ladder ------------------------------------------------------------------
    @{ Kind='LogMatch'; Name='mode entered E_GMS_IN_PROGRESS'; Pattern='\[stunt\] mode state -> E_GMS_IN_PROGRESS' }
    @{ Kind='Mark';     Name='ladder cue e-inprog';            Cue='e-inprog' }
    @{ Kind='LogMatch'; Name='mode entered E_GMS_OUTRO';       Pattern='\[stunt\] mode state -> E_GMS_OUTRO' }
    @{ Kind='LogMatch'; Name='mode entered E_GMS_RESULTS';     Pattern='\[stunt\] mode state -> E_GMS_RESULTS' }
    @{ Kind='LogMatch'; Name='win teleport saw the mode leave IN_PROGRESS (OUTRO or RESULTS)'; Pattern='\[win-teleport\] done state=E_GMS_(OUTRO|RESULTS) mode=8 ' }

    # ---- the finish is the game's own, and it is a WIN ----------------------------------------
    @{ Kind='LogMatch'; Name='FinishCurrentMode: marked man PASSED, not timed out, not destroyed';
       Pattern='\[evt-finish\] FinishCurrentMode ENTERED mode 8 finishType 9 .*attemptSucceeded 1 timedOut 0 carDestroyed 0 .*debugFinishPos -1' }
    @{ Kind='LogMatch'; Name='ShowModeResults: finishPosition 1, hasPlayerWon 1';
       Pattern='\[evt-finish\] ShowModeResults mode 8 finishPosition 1 .*hasPlayerWon 1' }
  )
}
