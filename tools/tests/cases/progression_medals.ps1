# progression_medals -- THE LICENCE / RANK-UP CHAIN.
#
# Lane `medals` of the 2026-09-06 progression "not connected" wave. The species is issue #10's:
# the console CALLER is live on PC and the callee has no body, so a seat exists and nothing runs.
#
# WHAT IS NOT CONNECTED (b5 tree, pre-fix):
#   ProgressionManager::UpdatePlayerMedals @0x8239FE50 -- the ONLY producer of game action 200
#   (E_ACTION_UPDATE_PLAYER_MEDALS -> GuiEventMedalUpdate 307) and the ONLY console caller of
#   UnlockToProgressionRank -- had no body anywhere in b5-decomp/src. All THREE of its seats
#   were therefore parked:
#     * OnEventFinishUpdateProfile's P6 (after an event win),
#     * PreWorldUpdate's `mbPlayerMedalsUpdateRequired` arm (every in-game frame),
#     * and, transitively, ProgressionManager::Construct @0x8237A5F8's boot seed of that flag
#       (`stbx 1, this, 0x20973` @0x8237A7B0) -- Construct is not reconstructed either, so on
#       PC NOTHING EVER SET THE FLAG and the arm could not have run even if it had a body.
#   Consequences: the licence never advanced past the profile's -2 "rank not set" seed, the
#   rank-up car unlocks never fired, and the medal HUD never refreshed.
#   Its callees were absent too: CalculateRankFromMedalTotal @0x8237AB38,
#   ClearMedalsOnRankUp @0x823705D8 (UnlockToProgressionRank park Q4),
#   UnlockDefaultPlayerCars @0x8237BF98 (park Q1), FixGameModeRanks @0x82395CD8 (park P5 plus
#   the `[PARKED]` seat in GameStateModule_gSR_00.cpp @0x82396FC4).
#
# THE WITNESSES (both [FLAG PC witness], opt-in behind BRN_PROGRESSION_MEDALS=1, first-N capped;
# NEITHER is in the X360 binary):
#   [medals] total=<rankWins> rank=<managerRank> profileRank=<profileRank>
#            winsToNext=<n> action200=1 events=<profileEventCount>
#       -- ProgressionManager::UpdatePlayerMedals, once per call. On the pre-fix build this line
#          can never appear: the function does not exist.
#   [medals] fixranks rank=<profileRank> race=.. roadrage=.. stunt=.. markedman=..
#       -- ProgressionManager::FixGameModeRanks, once per call. Its reachable seat is
#          GameStateModule::StartModeAtLights @0x82396FC4, which -StartEvent drives.
#
# THE SCENARIO. Boot -> junkyard -> DRIVING is enough for the PreWorldUpdate arm (the console's
# Construct seed is stood in for at the Prepare2 seam, exactly where Profile::Construct already
# is). -StartEvent at the stunt junction 2641.5,1.3,-1723.8 additionally drives StartModeAtLights,
# which is FixGameModeRanks' live seat. -DebugFinishPos 1 is armed so the OnEventFinishUpdateProfile
# seats (P5 + P6) are exercised too when the run has time for them -- but NOTHING IS GATED ON IT:
# whether a 60 s wall budget reaches RESULTS is a property of this box's frame rate, not of this
# bug (the stunt lane's banner has the measurements), and a medal taken through -DebugFinishPos is
# a debug finish, not a scored win. The four checks below are all reachable from the boot + start.
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case progression_medals -ExpectFail -Label pre-fix
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case progression_medals -Label post-fix
#
@{
  Name    = 'progression_medals'
  Area    = 'progression'
  Bug     = 'progression wave lane medals -- UpdatePlayerMedals @0x8239FE50 and its callees have no body, so the licence rank, the rank-up unlocks and game action 200 never happen'
  Frames  = $false
  Run     = @{
    Drive           = $true
    MotionProbe     = $true
    Teleport        = '2641.5,1.3,-1723.8,169'   # the stunt junction the stunt lane proved reachable
    StartEvent      = $true                      # -> GameStateModule::StartModeAtLights (FixGameModeRanks' seat)
    EventFsm        = $true
    SkipTrainingTip = $true
    DebugFinishPos  = 1                          # arm the event-win seats; NOT gated on (see the banner)
    DebugFinishAt   = 8
    MaxSeconds      = 60
    SkipIntro       = $true                      # the console -skipvideos latch
    AcceptGap       = 1.0                        # harness pump latency, not a game gate
  }
  DiagEnv = 'BRN_PROGRESSION_MEDALS=1'
  Checks  = @(
    @{ Kind='NewAsserts'; Name='no NEW assert families' }
    @{ Kind='LogCount';   Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }
    @{ Kind='Mark';       Name='reached DRIVING'; Phase='DRIVING' }

    # ---- the bug itself ---------------------------------------------------------------------
    # UpdatePlayerMedals ran at all, and posted game action 200 on the way out. Pre-fix the
    # witness cannot exist, so this FAILS (a LogValue whose witness never fires fails, by design).
    @{ Kind='LogValue'; Name='UpdatePlayerMedals ran and posted action 200';
       Pattern='\[medals\] total=.*action200=(?<v>\d+)'; Group='v'; Agg='max'; Min=1 }

    # The licence rank left the profile's -2 "rank not set" seed. This is the user-visible half:
    # UnlockToProgressionRank's shared rank tail (park Q4) is what mirrors the manager's cached
    # rank onto Profile::mi8CurrentProgressionRank, and it was never landed.
    @{ Kind='LogValue'; Name='profile licence rank is set (left the -2 seed)';
       Pattern='\[medals\] total=.*profileRank=(?<v>-?\d+)'; Group='v'; Agg='last'; Min=0 }

    # FixGameModeRanks ran at its live seat (StartModeAtLights).
    @{ Kind='LogValue'; Name='FixGameModeRanks ran at StartModeAtLights';
       Pattern='\[medals\] fixranks rank=(?<v>-?\d+)'; Group='v'; Agg='any'; Min=-2 }

    # ---- the seam-retirement safety check ----------------------------------------------------
    # UnlockToProgressionRank(0)'s event-list population is what stops the `lpEvent` null crash in
    # OnEventFinishUpdateProfile. Pre-fix it was driven by a PC-invented Prepare2 seam; post-fix it
    # is driven from the console's own seat inside UpdatePlayerMedals. The RECORD COUNT MUST NOT
    # MOVE: 120 is what the PRE-FIX run measured (scratch\bugtest\runs\progression_medals\
    # 20260906_211020 -- "profile event list populated -- 120 records from 120 authored
    # junctions"), i.e. one record per authored junction that carries an OFFLINE event. Both
    # bounds are pinned so a count that moves in EITHER direction fails.
    # This check PASSES on both builds on purpose -- it is a regression guard, not the RED trigger.
    @{ Kind='LogValue'; Name='profile event list still populated to the same count';
       Pattern='profile event list populated -- (?<v>\d+) records'; Group='v'; Agg='max'; Min=120; Max=120 }
  )
}
