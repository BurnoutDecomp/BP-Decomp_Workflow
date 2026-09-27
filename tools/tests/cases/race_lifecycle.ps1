# race_lifecycle -- AN OFFLINE RACE, START TO RESULTS, WON THROUGH THE GAME'S OWN FINISH LINE.
#
# Race wave 2026-09-27, lane H. Junction 480852 (event 557182, data mode 0 RACE, one checkpoint:
# the finish, landmark region 4677, a 105.4 x 45.8 x 6.3 m box at (-3854.8, 372.6, -1650.9)),
# coordinates from scratch\stuntrace_scout\eventdata\all_junctions.csv.
#
# THE SCENARIO. Teleport to the junction grid, start the event, hold the throttle. Five seconds of
# IN_PROGRESS later -WinTeleport (BRN_WIN_TELEPORT, b5 GameSource/Game/BrnHarnessWinTeleport.cpp)
# places the player's car through the game's own ActiveRaceCar::RequestPlaceOnTrack:
#   hop 1 kind=stage   30 m outside the finish box, facing away from it, until the game's own live
#                      race position (ScoringSystem::GetCarRacePosition) reads 1 (why=leader) or
#                      10 s pass (why=wait-cap). The race's GUI finish type reads that LIVE
#                      position, and after a 3 km jump the player's AI route distance is stale
#                      until the route is re-found -- see the .cpp banner.
#   hop 2 kind=finish  into the box centre. The next frame the landmark test
#                      (TriggerQueryManager::PostWorldUpdateLandmarksBringUp) sees the car's segment
#                      inside the box -> ModeManager::RaceCarTriggersLandmark -> RaceCarFinishes.
# NOTHING IS FORCED: no finish position, score or checkpoint bit is written by the harness. The
# car did not DRIVE the route, and a result from this case must say it was teleported.
# NOTE: A WIN BANKS A MEDAL INTO THE SLOT'S Memcard PROFILE (OnEventFinishUpdateProfile's win block).
#
# WITNESSES (source of every pattern; the [evt-finish] pair needs BRN_MODEMGR_DIAG, set below):
#   [win-teleport] armed / hop / seat / done / FAIL    b5 GameSource/Game/BrnHarnessWinTeleport.cpp
#                                                      :289 / :451 / :481 / :530 / :276 and :543
#   [win-teleport] request N -> RequestPlaceOnTrack(   b5 GameSource/World/BrnPlaceOnTrackManager.cpp:935
#   [stunt] mode state -> E_GMS_...                    b5 GameSource/GameState/ModeManager/GameModes/BrnGameMode.cpp:610
#   [evt-finish] FinishCurrentMode ENTERED mode ..     b5 GameSource/GameState/ModeManager/BrnModeManager_Finish.cpp:678
#   [evt-finish] ShowModeResults mode ..               b5 GameSource/GameState/ModeManager/BrnModeManager_Finish.cpp:931
#   [evt-finish] ***** HARNESS DEBUG FINISH POSITION   b5 GameSource/GameState/ModeManager/BrnModeManager_WorldTick.cpp:392
# FinishCurrentMode's `debugFinishPos -1` is RaceCarFinishes' own store for the player
# (BrnModeManager.cpp:618): the finish came through the landmark chain, not the debug lever.
# Race finish type 0 == 1st (0..7 = 1st..8th); ShowModeResults' finishPosition is the finish ORDER
# (ScoringSystem::RegisterFinishForCar), 1 == WIN -> medal.
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case race_lifecycle -Slot 1
#
@{
  Name    = 'race_lifecycle'
  Area    = 'events/race'
  Bug     = 'race wave lane H -- no harness case had ever taken an offline race to RESULTS; the win teleport drives the real landmark finish'
  Frames  = $false
  Run     = @{
    Drive           = $true
    MotionProbe     = $true
    Teleport        = '762.2,0.7,-2235.5,259'
    StartEvent      = $true
    EventFsm        = $true
    SkipTrainingTip = $true
    SkipIntro       = $true      # the console -skipvideos latch
    AcceptGap       = 1.0        # harness pump latency, not a game gate
    ThrottleScript  = '0:accel'
    WinTeleport     = 5          # seconds of IN_PROGRESS before hop 1
    # IN_PROGRESS lands at ~30 s wall; +5 s delay, up to +11.5 s staged, then OUTRO/RESULTS.
    MaxSeconds      = 120
  }
  DiagEnv = 'BRN_MODEMGR_DIAG=1,BRN_EVENT_FINISH_DIAG=1,BRN_STARTGRID_DIAG=1,BRN_RACEFLOW_DIAG=1'
  Checks  = @(
    # race + rewards wave: the start-grid clear and the event-finish rewards (lanes G, W1).
    @{ Kind='LogMatch'; Name='start grid cleared of traffic (KillTrafficOnStartGridWholeSale)'; Pattern='\[startgrid\] wholesale kill fired #1 ' }
    @{ Kind='LogMatch'; Name='event-finish rewards ran for the win (completion computed)'; Pattern='\[eventfinish\] event=\d+ mode=0 pos=1 .*completion=' }
    @{ Kind='LogCount'; Name='no parked event-finish reward steps left'; Pattern='OnEventFinishUpdateProfile: '; Max=0 }
    @{ Kind='NewAsserts'; Name='no NEW assert families' }
    @{ Kind='LogCount';   Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }

    # ---- the harness armed and acted (a silent no-op must not pass) ---------------------------
    @{ Kind='LogMatch'; Name='win teleport armed';                  Pattern='\[win-teleport\] armed delay=' }
    @{ Kind='LogCount'; Name='win teleport issued hops';            Pattern='\[win-teleport\] hop \d+ landmark='; Min=2 }
    @{ Kind='LogCount'; Name='no win-teleport refusal or give-up';  Pattern='\[win-teleport\] FAIL'; Max=0 }
    @{ Kind='LogCount'; Name='World half handed each hop to RequestPlaceOnTrack'; Pattern='\[win-teleport\] request \d+ -> RequestPlaceOnTrack\('; Min=2 }
    @{ Kind='LogMatch'; Name='race staged outside the finish (hop kind=stage)';   Pattern='\[win-teleport\] hop \d+ landmark=0 region=\d+ id=\d+ -> .* kind=stage .* mode=0 ' }
    @{ Kind='LogMatch'; Name='finish hop waited for live race position 1';        Pattern='\[win-teleport\] hop \d+ landmark=0 region=\d+ id=\d+ -> .* kind=finish .* racePos=1 why=leader mode=0 ' }
    @{ Kind='LogMatch'; Name='the finish hop seated INSIDE the landmark box';     Pattern='\[win-teleport\] seat hop \d+ kind=finish landed .* inside=1' }
    @{ Kind='LogCount'; Name='the debug finish lever was NOT used';               Pattern='HARNESS DEBUG FINISH POSITION'; Max=0 }

    # ---- the lifecycle ladder ------------------------------------------------------------------
    @{ Kind='LogMatch'; Name='mode entered E_GMS_IN_PROGRESS'; Pattern='\[stunt\] mode state -> E_GMS_IN_PROGRESS' }
    @{ Kind='Mark';     Name='ladder cue e-inprog';            Cue='e-inprog' }
    @{ Kind='LogMatch'; Name='mode entered E_GMS_OUTRO';       Pattern='\[stunt\] mode state -> E_GMS_OUTRO' }
    @{ Kind='LogMatch'; Name='mode entered E_GMS_RESULTS';     Pattern='\[stunt\] mode state -> E_GMS_RESULTS' }
    @{ Kind='LogMatch'; Name='win teleport saw the mode leave IN_PROGRESS (OUTRO or RESULTS)'; Pattern='\[win-teleport\] done state=E_GMS_(OUTRO|RESULTS) mode=0 ' }

    # ---- the finish is the game's own, and it is a WIN ----------------------------------------
    @{ Kind='LogMatch'; Name='FinishCurrentMode: race, 1st, not timed out, via RaceCarFinishes';
       Pattern='\[evt-finish\] FinishCurrentMode ENTERED mode 0 finishType 0 .*attemptSucceeded 1 timedOut 0 .*debugFinishPos -1' }
    @{ Kind='LogMatch'; Name='ShowModeResults: finishPosition 1, hasPlayerWon 1';
       Pattern='\[evt-finish\] ShowModeResults mode 0 finishPosition 1 .*hasPlayerWon 1' }
  )
}
