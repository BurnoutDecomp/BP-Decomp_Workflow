# marked_man_threat -- MARKED MAN (SurvivorMode): how many enemy cars chase the player, and how hard.
#
# Gameplay wave GW3, lane MARKED (issue #24: "Marked man AI is not aggressive enough, and barely
# any enemies are here"). Same scenario as marked_man_lifecycle (junction 480856, event 560148,
# data mode 3 SURVIVOR, game mode type 8), held longer so the threat ramp reaches its cap, with
# the opt-in BRN_MM_DIAG witnesses on.
#
# WITNESSES (all behind BRN_MM_DIAG=1 except the console's own debug prints):
#   [mm-start] MARKED MAN rankRatio R maxOpponents N ...   SurvivorMode::Start
#   [mm-pre] ... count C bcast B ...                        SurvivorMode::PreWorldUpdate
#   <AI> Allowed in Marked man :Yes,...                     SurvivorMode::UpdateOpponents (console print)
#   [mm-ai] car I ... aggr A ... aggState S ... dist D      AIAggression::Update, per car per second
#   [mm-ai] decide calls ...                                AIAggression::DecideToAttack exit tally
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case marked_man_threat
#
@{
  Name    = 'marked_man_threat'
  Area    = 'events/marked_man'
  Bug     = 'issue #24 -- Marked Man too passive, too few enemies'
  Frames  = $false
  Run     = @{
    Drive           = $true
    MotionProbe     = $true
    Teleport        = '1634.3,-1.9,-2284.1,292'
    StartEvent      = $true
    EventFsm        = $true
    SkipTrainingTip = $true
    SkipIntro       = $true
    AcceptGap       = 1.0
    # IN_PROGRESS lands at ~29 s wall; the ramp caps 5 s later. 75 s leaves ~40 s of chase.
    MaxSeconds      = 75
    ThrottleScript  = '0:accel'
  }
  DiagEnv = 'BRN_MM_DIAG=1'
  Checks  = @(
    @{ Kind='NewAsserts'; Name='no NEW assert families' }
    @{ Kind='LogCount';   Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }
    @{ Kind='LogMatch';   Name='mode entered E_GMS_IN_PROGRESS'; Pattern='\[stunt\] mode state -> E_GMS_IN_PROGRESS' }

    # ---- the enemy COUNT is the console's arithmetic on the per-mode rank ratio --------------
    # SurvivorMode::Start: maxOpponents = (s32)(3 * ratio + 2), capped at 4 (image words 2 and 4),
    # and it is also the grid's rival count. The ramp time is 5.0 at every rank (both image words
    # are 5.0). A fresh Marked Man record (ratio 0) gives 2 enemies; 4 needs ratio >= 2/3.
    @{ Kind='LogValue'; Name='maxOpponents is the console band [2,4]';
       Pattern='\[mm-start\] MARKED MAN rankRatio \S+ maxOpponents (?<n>\d+) '; Group='n'; Agg='all'; Min=2; Max=4 }
    @{ Kind='LogMatch'; Name='every allowed enemy is on the grid (numRivals == maxOpponents)';
       Pattern='\[mm-start\] MARKED MAN rankRatio \S+ maxOpponents (\d+) numRivals \1 ' }
    @{ Kind='LogValue'; Name='threat ramp time is 5 s';
       Pattern='\[mm-start\] .* maxRampTimer (?<t>[0-9.]+)'; Group='t'; Agg='all'; Min=5; Max=5 }

    # ---- the ramp runs and lets the whole pack in -------------------------------------------
    @{ Kind='LogValue'; Name='the ramp mode clock advances (dt > 0)';
       Pattern='\[mm-pre\] call \d+ state 2 dt (?<dt>[0-9.]+) '; Group='dt'; Agg='max'; Min=0.001 }
    @{ Kind='LogValue'; Name='the ramp broadcast reached 2 or more enemies';
       Pattern='\[mm-pre\] .* count (?<c>\d+) bcast'; Group='c'; Agg='max'; Min=2 }
    @{ Kind='LogMatch'; Name='UpdateOpponents allowed player + 2 enemies'; Pattern='<AI> Allowed in Marked man :Yes,Yes,Yes,' }

    # ---- the enemies are Marked Man hunters and they come for the player ----------------------
    # AICar::OnModeStart: MARKED_MAN aggression = 0.2 + 0.8 * ratio (image floats 0.2 / 1.0).
    @{ Kind='LogValue'; Name='hunter aggression is in the console band [0.2,1.0]';
       Pattern='\[mm-ai\] car \d+ style 6 .* aggr (?<a>[0-9.]+) '; Group='a'; Agg='all'; Min=0.2; Max=1.0 }
    @{ Kind='LogValue'; Name='a hunter closed to within 30 m of the player';
       Pattern='\[mm-ai\] car \d+ style 6 .* dist (?<d>[0-9.]+) spd'; Group='d'; Agg='min'; Max=30 }
    @{ Kind='LogValue'; Name='DecideToAttack ran';
       Pattern='\[mm-ai\] decide calls (?<n>\d+) '; Group='n'; Agg='max'; Min=1 }
    @{ Kind='LogMatch'; Name='a hunter entered a slam state (OVERTAKE_TO_SLAM / DROP_BACK_TO_SLAM / ATTACK_SLAM)';
       Pattern='\[mm-ai\] car \d+ style 6 .* aggState [123] ' }
  )
}
