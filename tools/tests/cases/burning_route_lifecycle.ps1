# burning_route_lifecycle -- A BURNING ROUTE, START TO RESULTS, WON THROUGH THE GAME'S OWN FINISH.
#
# Race wave 2026-09-27, lane H. Junction 480860 (event 558944, data mode 4 BURNING_ROUTE, game mode
# type 5, one checkpoint: the finish, landmark region 4675, a 131.9 x 29.6 x 13.4 m box at
# (3033.5, 13.1, 86.8)), coordinates from scratch\stuntrace_scout\eventdata\all_junctions.csv.
#
# THE SCENARIO. Teleport to the junction grid, start the event, hold the throttle. Five seconds of
# IN_PROGRESS later -WinTeleport (BRN_WIN_TELEPORT, b5 GameSource/Game/BrnHarnessWinTeleport.cpp)
# places the player's car INTO the finish box through the game's own
# ActiveRaceCar::RequestPlaceOnTrack (hop kind=finish why=direct: a Burning Route's finish type
# does not depend on a race position, so there is no staging hop). The next frame the landmark
# test sees the car inside the box -> ModeManager::RaceCarTriggersLandmark -> RaceCarFinishes.
# FinishCurrentMode's burning-route arm is 1st unless timed out; ShowModeResults' finishPosition is
# the medal target + 1 (SetMedalModeTimer seeds GOLD, and five seconds in the route is still on it).
# NOTHING IS FORCED by the harness. The car did not DRIVE the route; say it was teleported.
# NOTE: A WIN BANKS A MEDAL INTO THE SLOT'S Memcard PROFILE.
#
# WITNESSES (source of every pattern; the [evt-finish] pair needs BRN_MODEMGR_DIAG, set below):
#   [win-teleport] armed / hop / seat / done / FAIL    b5 GameSource/Game/BrnHarnessWinTeleport.cpp
#                                                      :289 / :451 / :481 / :530 / :276 and :543
#   [win-teleport] request N -> RequestPlaceOnTrack(   b5 GameSource/World/BrnPlaceOnTrackManager.cpp:935
#   [stunt] mode state -> E_GMS_...                    b5 GameSource/GameState/ModeManager/GameModes/BrnGameMode.cpp:610
#   [evt-finish] FinishCurrentMode ENTERED mode ..     b5 GameSource/GameState/ModeManager/BrnModeManager_Finish.cpp:678
#   [evt-finish] ShowModeResults mode ..               b5 GameSource/GameState/ModeManager/BrnModeManager_Finish.cpp:931
#   [evt-finish] ***** HARNESS DEBUG FINISH POSITION   b5 GameSource/GameState/ModeManager/BrnModeManager_WorldTick.cpp:392
# `debugFinishPos -1` is RaceCarFinishes' own store for the player (BrnModeManager.cpp:618).
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case burning_route_lifecycle -Slot 1
#
@{
  Name    = 'burning_route_lifecycle'
  Area    = 'events/burning_route'
  Bug     = 'race wave lane H -- no harness case had ever taken a Burning Route to RESULTS; the win teleport drives the real landmark finish'
  Frames  = $false
  Run     = @{
    Drive           = $true
    MotionProbe     = $true
    Teleport        = '2857.0,-4.5,-2160.1,90'
    StartEvent      = $true
    EventFsm        = $true
    SkipTrainingTip = $true
    SkipIntro       = $true      # the console -skipvideos latch
    AcceptGap       = 1.0        # harness pump latency, not a game gate
    ThrottleScript  = '0:accel'
    WinTeleport     = 5          # seconds of IN_PROGRESS before the finish hop
    # IN_PROGRESS lands at ~30 s wall; +5 s delay, then OUTRO/RESULTS within a few seconds.
    MaxSeconds      = 90
  }
  DiagEnv = 'BRN_MODEMGR_DIAG=1'
  Checks  = @(
    @{ Kind='NewAsserts'; Name='no NEW assert families' }
    @{ Kind='LogCount';   Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }

    # ---- the harness armed and acted (a silent no-op must not pass) ---------------------------
    @{ Kind='LogMatch'; Name='win teleport armed';                  Pattern='\[win-teleport\] armed delay=' }
    @{ Kind='LogCount'; Name='win teleport issued a hop';           Pattern='\[win-teleport\] hop \d+ landmark='; Min=1 }
    @{ Kind='LogCount'; Name='no win-teleport refusal or give-up';  Pattern='\[win-teleport\] FAIL'; Max=0 }
    @{ Kind='LogCount'; Name='World half handed the hop to RequestPlaceOnTrack'; Pattern='\[win-teleport\] request \d+ -> RequestPlaceOnTrack\('; Min=1 }
    @{ Kind='LogMatch'; Name='finish hop into the burning-route finish';         Pattern='\[win-teleport\] hop \d+ landmark=0 region=\d+ id=\d+ -> .* kind=finish .* why=direct mode=5 ' }
    @{ Kind='LogMatch'; Name='the finish hop seated INSIDE the landmark box';    Pattern='\[win-teleport\] seat hop \d+ kind=finish landed .* inside=1' }
    @{ Kind='LogCount'; Name='the debug finish lever was NOT used';              Pattern='HARNESS DEBUG FINISH POSITION'; Max=0 }

    # ---- the lifecycle ladder ------------------------------------------------------------------
    @{ Kind='LogMatch'; Name='mode entered E_GMS_IN_PROGRESS'; Pattern='\[stunt\] mode state -> E_GMS_IN_PROGRESS' }
    @{ Kind='Mark';     Name='ladder cue e-inprog';            Cue='e-inprog' }
    @{ Kind='LogMatch'; Name='mode entered E_GMS_OUTRO';       Pattern='\[stunt\] mode state -> E_GMS_OUTRO' }
    @{ Kind='LogMatch'; Name='mode entered E_GMS_RESULTS';     Pattern='\[stunt\] mode state -> E_GMS_RESULTS' }
    @{ Kind='LogMatch'; Name='win teleport saw the mode leave IN_PROGRESS (OUTRO or RESULTS)'; Pattern='\[win-teleport\] done state=E_GMS_(OUTRO|RESULTS) mode=5 ' }

    # ---- the finish is the game's own, and it is a WIN ----------------------------------------
    @{ Kind='LogMatch'; Name='FinishCurrentMode: burning route, 1st, not timed out, via RaceCarFinishes';
       Pattern='\[evt-finish\] FinishCurrentMode ENTERED mode 5 finishType 0 .*attemptSucceeded 1 timedOut 0 .*debugFinishPos -1' }
    @{ Kind='LogMatch'; Name='ShowModeResults: finishPosition 1, hasPlayerWon 1';
       Pattern='\[evt-finish\] ShowModeResults mode 5 finishPosition 1 .*hasPlayerWon 1' }
  )
}
