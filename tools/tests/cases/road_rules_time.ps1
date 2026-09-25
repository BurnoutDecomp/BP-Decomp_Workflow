# road_rules_time -- A TIME ROAD RULE STARTS, RUNS AND ENDS IN FREE ROAM.
#
# Road-rules wave, 2026-09-25. Before the wave, 14 of the 20 RoadRulesManager functions had no body
# and the PC ran only a road-display extract: entering a road posted action 273, but no rule could
# ever start, time or end. The wave landed the whole manager (Construct/Update/OnRoadLimit/OnStartRule/
# OnEndRule/OnScoreCompleted/...), mounted the StreetManager score half, wired the console call sites
# (GameStateModule::UpdateRoadRulesManager, the trigger query's OnRoadLimit, the road-rule game-event
# arms) and translated the road-rule actions to the HUD.
#
# THE SCENARIO. Teleport onto the road north of road-limit region 388315, accelerate, and tap the
# pad's d-pad-up third action (58, GUI_EVENT_DETAILS; harness channel EventDetails) one second in:
# that is the console's road-rule toggle (ControllerInput::mbStartEventPressed ->
# RoadRulesManager::UpdateActiveRoadRule), NONE -> OFFLINE_TIME. RequestPlaceOnTrack snaps the car
# onto road 54 facing north; it crosses limit 397701 (exit) and then 397451 (entry) into road 52,
# which starts the time rule (action 277). The accelerator-only drive never reaches road 52's far
# limit, so the attempt ends UNSCORED: measured 2026-09-25, back out through 397451 after 59.7 s
# (278 valid 0), then a second attempt on road 54 ended by a road change after 14.3 s.
#
# PRECONDITION: the slot's profile must have road rules available
# (ProgressionManager::AreRoadRulesAvailable: four medals, or a ruled road). The main Memcard and
# Memcard_3 profiles on this box have five and six. A fresh profile keeps the rule at 0 and the
# 'rule toggled to OFFLINE_TIME' check below names that failure.
#
# WHAT IS NOT GATED: a SCORED finish (278 valid 1 -> StreetManager::ProcessNewRoadScore -> 281).
# It needs a steer script that follows one road from limit to limit; the accelerator-only drive
# cannot. RESTORE-WHEN such a script exists.
#
# WITNESSES (BRN_ROADRULES_DIAG, all [FLAG PC witness], capped):
#   [roadrules] action N -> gui M ...   the translator (GameBridgeGameStateToX_*GuiEvents.cpp)
#   [roadrules] limit ...               RoadRulesManager::OnRoadLimit entry
#   [roadrules] update road ... t ...   RoadRulesManager::Update, on change + every 300th update
@{
  Name    = 'road_rules_time'
  Area    = 'freeroam/road_rules'
  Bug     = 'road-rules wave 2026-09-25 -- the time road rule never started (RoadRulesManager was a display-only slice)'
  Frames  = $false
  Run     = @{
    Drive          = $true
    MotionProbe    = $true
    Teleport       = '2886.0,1.0,-2020.0,180'
    SkipIntro      = $true      # the console -skipvideos latch
    AcceptGap      = 1.0        # harness pump latency, not a game gate
    MaxSeconds     = 90
    ThrottleScript = '0:accel'
    MenuTapAt      = '1:EventDetails'
  }
  DiagEnv = 'BRN_ROADRULES_DIAG=1'
  Checks  = @(
    @{ Kind='NewAsserts'; Name='no NEW assert families' }
    @{ Kind='LogCount';   Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }
    # ---- the manager runs and the toggle reaches it -------------------------------------------
    @{ Kind='LogMatch'; Name='RoadRulesManager::Update runs';        Pattern='\[roadrules\] update road' }
    @{ Kind='LogMatch'; Name='rule toggled to OFFLINE_TIME (282)';   Pattern='\[roadrules\] action 282 -> gui 343 rule 1' }
    # ---- a road limit starts a time rule ------------------------------------------------------
    @{ Kind='LogMatch'; Name='OnRoadLimit reached with an entry';    Pattern='\[roadrules\] limit \d+ entry 1' }
    @{ Kind='LogMatch'; Name='time rule started (277 -> GUI 335)';   Pattern='\[roadrules\] action 277 -> gui 335 type 0' }
    @{ Kind='LogValue'; Name='the rule clock advances';              Pattern='\[roadrules\] update road .* t (?<v>[\d.]+) timeout'; Group='v'; Agg='max'; Min=5 }
    @{ Kind='LogMatch'; Name='HUD score update posted (279 -> 338)'; Pattern='\[roadrules\] action 279 -> gui 338 \(time ' }
  )
}
