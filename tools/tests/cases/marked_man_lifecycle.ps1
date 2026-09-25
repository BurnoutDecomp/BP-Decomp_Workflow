# marked_man_lifecycle -- MARKED MAN (SurvivorMode) from the start injection to IN_PROGRESS.
#
# Lane MM of the 2026-09-25 road-rules wave. Junction 480856 (event 560148, data mode 3 SURVIVOR),
# coordinates from scratch\stuntrace_scout\eventdata\all_junctions.csv.
#
# WHY THIS CASE EXISTS: the 2026-09-25 mode census reported "Marked Man stalls at COUNTDOWN". It
# does not. The census log itself (and every rerun) prints `[stunt] mode state -> E_GMS_IN_PROGRESS`
# about 5 s after COUNTDOWN, then the Survivor threat ramp (`<AI> Allowed in Marked man :...`) and,
# if the run is long enough, OUTRO -> RESULTS when the player is totalled. The misleading part was
# the `[start] event 25 -> FinishOfflineModeIntro (...)` line, whose text names
# StuntAttackMode::mbPlayerPointingInStartDirection for EVERY mode. Only StuntAttackMode overrides
# GameMode vtable slot 11 (ShouldCountdownEnd); SurvivorMode keeps the base leaf that returns true, so its
# countdown ends on CountdownState::Update's own timer (<= 0.0f, then SendEvent(E_GME_NEXT)).
# This case pins that ladder so a real regression cannot hide behind the same misreading.
#
# WITNESSES (no diag variable needed):
#   [stunt] mode state -> ...                     GameMode::SetCurrentState rung (ungated, capped)
#   lpProgressionRankData->GetTrafficDensitySurvival()   SurvivorMode::Start's own debug print
#   <AI> Allowed in Marked man :...               SurvivorMode::UpdateOpponents' own debug print
#                                                 (only fires once the ramp runs, i.e. IN_PROGRESS)
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case marked_man_lifecycle -Slot 1
#
@{
  Name    = 'marked_man_lifecycle'
  Area    = 'events/marked_man'
  Bug     = 'lane MM -- "Marked Man stalls at COUNTDOWN" (census 2026-09-25; not reproduced: the mode reaches IN_PROGRESS)'
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
    # IN_PROGRESS lands at ~29 s wall on this box (boot ~17 s, then the fly-by and the countdown).
    MaxSeconds      = 60
    ThrottleScript  = '0:accel'
  }
  DiagEnv = ''
  Checks  = @(
    @{ Kind='NewAsserts'; Name='no NEW assert families' }
    @{ Kind='LogCount';   Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }

    # ---- it is Marked Man ----------------------------------------------------------------
    @{ Kind='LogMatch'; Name='SurvivorMode::Start ran'; Pattern='GetTrafficDensitySurvival\(\) :' }

    # ---- the lifecycle ladder ------------------------------------------------------------
    @{ Kind='LogMatch'; Name='mode entered E_GMS_INTRO';       Pattern='\[stunt\] mode state -> E_GMS_INTRO' }
    @{ Kind='LogMatch'; Name='mode entered E_GMS_COUNTDOWN';   Pattern='\[stunt\] mode state -> E_GMS_COUNTDOWN' }
    @{ Kind='LogMatch'; Name='mode entered E_GMS_IN_PROGRESS'; Pattern='\[stunt\] mode state -> E_GMS_IN_PROGRESS' }
    @{ Kind='Mark';     Name='ladder cue e-inprog';            Cue='e-inprog' }

    # ---- the in-progress mode actually runs ------------------------------------------------
    @{ Kind='LogMatch'; Name='Survivor threat ramp broadcast (UpdateOpponents)'; Pattern='<AI> Allowed in Marked man :' }
  )
}
