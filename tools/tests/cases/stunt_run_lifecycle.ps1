# stunt_run_lifecycle -- THE STUNT RUN, END TO END.
#
# Lane `stunt` of the 2026-09-06 bug-test wave. Drive to stunt junction 480897, start event
# 558269 (STUNT RUN, target 10,000 in 2:00), run the whole lifecycle -- junction panel -> event
# start -> flyby -> countdown -> IN_PROGRESS -> mode timer -> RESULTS -- and measure that the
# SCORER ACTUALLY SCORES, per stunt TYPE.
#
# THE BUG THIS WAS WRITTEN AGAINST (b5 tree, pre-fix):
#   StuntOffencesManager::OutputStuntsInProgress @0x8263B278 -- the ONLY writer of
#   RaceCarState::mfInProgressDriftTime / mfInProgressHandbreakTurnAngle / the four sibling
#   in-progress stunt scalars -- was PARKED at its console call site
#   (VehicleManager::WriteOutVehicleStats @0x8263F460 leg 0x8263F764). So those six fields sat
#   at 0 for the whole run and StuntModeScoring::UpdateDriftStunts @0x8232CAE0 /
#   UpdateDrivingStunts @0x8232CD70 -- which gate on exactly those fields -- could never award
#   DRIFT or HANDBRAKE_TURN score. Air/boost/collectible stunts scored; the two ground-driving
#   feeds were dead.
#
# THE SCENARIO drives the two dead feeds ON PURPOSE:
#   throttle 0:accel (get up to speed) -> 26:accel+handbrake with full left lock (a handbrake
#   spin: the physics detector needs >90 deg accumulated, the scorer >=160 deg) -> back on the
#   power with the lock still on (a sustained drift: the scorer needs >1.0 s of drift time).
#   The steer/throttle time base is seconds since the first input after the DRIVING mark, and
#   the event is armed with -StartEvent, so the mode is running by then.
#
# WITNESSES (all [FLAG PC witness], first-N capped, opt-in behind BRN_STUNT_DIAG except the
# mode-state ladder rung, which honours flow_run's `e-inprog` CONTRACT cue):
#   [stunt] mode state ...      GameMode::SetCurrentState  (BrnGameMode.cpp)
#   [stunt] award type=..       StuntModeScoring::UpdateScore   (BrnStuntModeScoring_UpdatePass.cpp)
#   [stunt] combo banked ..     StuntModeScoring::EndCombo      (BrnStuntModeScoring_Combo.cpp)
#   [stunt] feed ..             VehicleManager::WriteOutVehicleStats (the publish leg itself)
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case stunt_run_lifecycle -ExpectFail -Label pre-fix
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case stunt_run_lifecycle -Label post-fix
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
#   ⛔ THIS ONE CANNOT BE 60 s AND THAT IS THE GAME, NOT THE HARNESS. The stunt run is a 120 s
#   game mode on the SIM clock and the case scores its whole lifecycle through to RESULTS; the
#   ThrottleScript/SteerScript below run to t+118. Only the boot saving comes off it.
#
@{
  Name    = 'stunt_run_lifecycle'
  Area    = 'events/stunt'
  Bug     = 'stunt lane -- the stunt-run scoring feed: drift + handbrake stunts never register (the parked StuntOffencesManager::OutputStuntsInProgress publish)'
  Frames  = $false
  Run     = @{
    Drive           = $true
    MotionProbe     = $true        # the DRIVE verdict -- so a run that scores nothing can be told
                                   # apart from a run whose car never moved
    Teleport        = '2641.5,1.3,-1723.8,169'
    StartEvent      = $true
    EventFsm        = $true
    SkipTrainingTip = $true
    # 265, not 235: the mode's 120 s runs on the SIM clock, and this schedule deliberately
    # spins the car (run 20260906_121838 covered 374 m of path for 23 m of net travel), which
    # costs enough frame time that a 235 s wall budget cut the run off still IN_PROGRESS.
    MaxSeconds      = 250
    SkipIntro      = $true      # the console -skipvideos latch (see the banner)
    AcceptGap      = 1.0        # harness pump latency, not a game gate
    # MANY attempts, not two. Measured 2026-09-06: the identical two-attempt schedule drifted
    # heavily in run 20260906_100601 (200 DRIFT awards) and not at all in 20260906_113310 -- the
    # car's trajectory after 30 s of open-road throttle is not reproducible frame-for-frame, so a
    # schedule with two chances is a coin toss. This pulses the handbrake every ~8 s and flips the
    # steering lock every ~15 s for the whole 120 s event, so a scoreable slide only has to happen
    # ONCE. Both feeds are exercised: the handbrake pulse (rear wheels locked -> GetTimeDrifting
    # climbs, and the heading change accumulates toward the 90 deg detector gate) and the sustained
    # full-lock carve between pulses.
    ThrottleScript  = '0:accel,26:accel+handbrake,32:accel,40:accel+handbrake,46:accel,54:accel+handbrake,60:accel,68:accel+handbrake,74:accel,82:accel+handbrake,88:accel,96:accel+handbrake,102:accel,110:accel+handbrake,116:accel'
    # The lock FLIPS every ~16 s, and that is a deliberate compromise rather than the obvious
    # choice. Holding one direction the whole event scores more handbrake turns --
    # StuntOffencesManager::CheckForHandBreakTurns @0x825E3A38 accumulates mfHandBreakAngleSoFar as
    # a SIGNED sum of heading deltas, so a flip cancels its own progress toward the 90 deg detector
    # gate -- but it also parks the car spinning on the spot (measured: 374 m of path for 23 m of
    # net travel), and the sim then runs slowly enough that the mode's own 120 s never elapses
    # inside the run budget: runs 20260906_121838 and _122723 both ended still IN_PROGRESS.
    # Alternating keeps the car covering ground, which is what lets the event actually FINISH.
    SteerScript     = '0:none,22:left,38:right,54:left,70:right,86:left,102:right,118:left'
  }
  DiagEnv = 'BRN_PROP_DIAG=1,BRN_STUNT_DIAG=1'
  Checks  = @(
    @{ Kind='NewAsserts'; Name='no NEW assert families' }
    @{ Kind='LogCount'; Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }

    # ---- the lifecycle ladder -------------------------------------------------------------
    @{ Kind='Mark';     Name='junction detected (action 201 -> gui 311)'; Cue='e-junc' }
    @{ Kind='Mark';     Name='event started (action 23 -> gui 93)';       Cue='e-start' }
    @{ Kind='Mark';     Name='mode reached E_GMS_IN_PROGRESS';            Cue='e-inprog' }
    # ⚠️ E_GMS_RESULTS IS NOT GATED, and it is not because it does not happen. The full lifecycle
    # INTRO -> COUNTDOWN -> IN_PROGRESS -> OUTRO -> RESULTS -> QUIT is in the log of runs
    # 20260906_100601, _113310, _115233 and _120858, printed by this file's own mode-state rung.
    # But reaching it is a race between the mode's 120 s SIM clock and the run's wall-clock budget,
    # and the sim's frame rate on this box is set by whatever ten other lanes' uncommitted code is
    # doing: the same case at MaxSeconds 265 reached RESULTS in _120858 and ran out still
    # IN_PROGRESS in _121838, _122723 and _123629. A check like that measures box load, not this
    # bug. IN_PROGRESS above is the deterministic end of the ladder and is gated; RESULTS stays in
    # the log as evidence. RESTORE-WHEN the harness can drive the mode clock (a -DebugFinishPos run
    # ends the event on demand, but a medal taken that way is not a scored win -- see flow_run).

    # ---- the scorer ran ---------------------------------------------------------------------
    # ⚠️ WHAT IS DELIBERATELY *NOT* GATED HERE, and why. The obvious checks -- "a DRIFT/
    # HANDBRAKE_TURN award appears" and "the banked combo total > 0" -- are the user-visible end of
    # this bug, and they DO fire on the fixed build: run 20260906_100601 logged 200
    # `[stunt] award type=3 DRIFT` lines and `combo banked score=1174`, run 20260906_115233 twelve
    # `award type=10 HANDBRAKE_TURN` and `combo banked score=200`. But they are not a property of
    # the FIX -- they are a property of the DRIVE. The console's own scoring gates are
    # KF_STUNT_ATTACK_MIN_DRIFT_TIME = 1.0 s and KF_HANDBRAKE_TURN_MIN_ANGLE = 160 deg, and whether
    # a 120 s throttle/steer schedule clears either depends on where in Paradise City the car
    # happens to be: three post-fix runs of this identical schedule scored 200 drifts, 12 handbrake
    # turns, and (20260906_120858) a 0.8 s drift that missed the 1.0 s gate. Gating on them makes
    # the case flap on the game's difficulty rather than on the bug.
    # So the case gates on the FEED instead -- the thing the park actually broke, which is
    # published every frame the car does anything and is therefore deterministic. The award and
    # combo lines stay in the log as evidence.

    # ---- the feed the park killed ----------------------------------------------------------
    # The six in-progress stunt scalars AS THE SCORER READS THEM. Pre-fix every sampled frame was
    # `drift=0 hb=0 mask=0` because nothing ever wrote them; post-fix the publish is live.
    # muStuntActionInProgress != 0 means SOME stunt bit reached the scorer at all.
    @{ Kind='LogValue'; Name='in-progress stunt mask reaches the scorer'; Pattern='\[stunt\] feed .*mask=(?<v>[-\d]+)'; Group='v'; Agg='max'; Min=1 }
    # The scorer's own gate reads the FLOAT lane, not the mask, so check that lane carries a real
    # value too. 0.05 s, not 1.0: the 1.0 s is the console's SCORING threshold (whether this
    # particular drive drifted long enough), while any non-zero at all is the publish working.
    @{ Kind='LogValue'; Name='RaceCarState drift time published non-zero'; Pattern='\[stunt\] feed .*drift=(?<v>[-\d.]+)'; Group='v'; Agg='max'; Min=0.05 }
  )
}
