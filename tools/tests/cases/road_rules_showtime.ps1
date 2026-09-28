# road_rules_showtime -- SHOWTIME ON A ROAD STARTS THE CRASH ROAD RULE, AND ENDING IT SCORES IT.
#
# Gameplay wave GW, 2026-09-28, lane SHOW. RoadRulesManager::Update starts the crash rule the frame
# showtime becomes active on a road (the selection flips to OFFLINE_CRASH and OnShowtimeStart posts
# action 277 with score type 1), and scores it the first frame showtime is no longer active
# (OnEndRule(E_SCORE_TYPE_CRASH, true) -> action 278 type 1 valid 1, score = the showtime score
# GameStateModule::UpdateRoadRulesManager hands the manager every frame). Neither half had run on
# the PC: nothing ever ended a showtime session with a posted score until SendModeStopMessages'
# leaving 143 was bodied in this wave.
#
# THE SCENARIO. road_rules_time's spot: teleport north of road-limit region 388315 and accelerate
# north. The time rule is NOT toggled (no EventDetails tap), so the only rule that can start is the
# crash rule. RequestPlaceOnTrack seats the car at about (3008, -2.5, -1945), inside a chain of
# SHORTCUT AI sections (flags bit 0x01) that carry no street span, so the current road index is -1
# there, as it is on the console: the shipped AI-section data gives span -1 for every section from
# the seat to z ~ -1740 (checked against both the ported AI.DAT and the retail PC AI.DAT). The car
# reaches road 54 (Interstate section, street span 213) at z ~ -1722, about 11 s into the throttle,
# and road 52 after the 397701 / 397451 limits. Both bumpers therefore wait until DRIVING+20 s
# (14 s of throttle): RoadRulesManager::miLastRoadIndex then holds a valid road, which is the road
# OnShowtimeStart hands OnStartRule. A gesture inside the shortcut (DRIVING+14, the first version of
# this case) starts showtime with road -1 and no crash rule. The throttle is released two seconds
# after the gesture so CrashModeScoring::HasCrashModeEnded's idle ladder (car still 3 s, no event
# 3 s, boost settled) can end the session inside the budget.
#
# PRECONDITION: the slot's profile must have road rules available (four medals, or a ruled road),
# or ShouldStartShowtimeMode refuses the gesture. The main Memcard profile on this box has five.
# The 'showtime started' check names that failure.
#
# WITNESSES (all [FLAG PC witness], opt-in, capped):
#   [roadrules] player section S span P shortcut B road R   BRN_ROADRULES_DIAG, StreetManager::
#                                                     UpdateUpcomingStreets, on each section change
#   [showtime-switch] action 143 posted ... entering=1   UpdateCurrentMode (unconditional one-shot)
#   [roadrules] action N -> gui M type T score S valid V  BRN_ROADRULES_DIAG, the road-rule translator
#   [showtime] leaving: mode ... finalScore ...           BRN_SHOWTIME_DIAG, SendModeStopMessages
# The GUI bridge's own 143 -> 397 witness (BRN_SHOWTIME_SCORE_DIAG) shares a 24-line budget with
# the per-frame action 142 and is spent before the session ends, so it gates nothing here.
@{
  Name    = 'road_rules_showtime'
  Area    = 'freeroam/road_rules'
  Bug     = 'gameplay wave GW 2026-09-28 -- the showtime crash road rule had never started or ended'
  Frames  = $false
  Run     = @{
    Drive          = $true
    MotionProbe    = $true
    Teleport       = '2886.0,1.0,-2020.0,180'
    SkipIntro      = $true      # the console -skipvideos latch
    AcceptGap      = 1.0        # harness pump latency, not a game gate
    MaxSeconds     = 100        # boot ~16 + gesture at DRIVING+20 + ~55 s for the idle ladder
    ThrottleScript = '0:accel,16:none'   # schedule time 14 == DRIVING+20; release 2 s after the gesture
    Showtime       = '20:3'
  }
  DiagEnv = 'BRN_ROADRULES_DIAG=1,BRN_SHOWTIME_DIAG=1'
  Checks  = @(
    @{ Kind='NewAsserts'; Name='no NEW assert families' }
    @{ Kind='LogCount';   Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }
    @{ Kind='Mark';       Name='reached DRIVING'; Phase='DRIVING' }
    @{ Kind='LogMatch';   Name='RoadRulesManager::Update runs'; Pattern='\[roadrules\] update road' }
    # ---- the car reaches a road before the gesture (the seat is a shortcut, road -1) ----------
    @{ Kind='LogMatch';   Name='the road lookup resolves a road (54 or 52)'
       Pattern='\[roadrules\] update road (54|52) ' }
    @{ Kind='LogMatch';   Name='the seat is a shortcut section with no span (road -1)'
       Pattern='\[roadrules\] player section \d+ span -1 shortcut 1 road -1' }
    @{ Kind='LogMatch';   Name='a street section resolves road 54'
       Pattern='\[roadrules\] player section \d+ span 213 shortcut 0 road 54' }
    # ---- showtime starts, and with it the crash rule ------------------------------------------
    @{ Kind='LogMatch';   Name='showtime started (action 143 entering=1)'
       Pattern='\[showtime-switch\] action 143 posted: car \d+ entering=1' }
    @{ Kind='LogMatch';   Name='crash rule started (277 -> GUI 335 type 1)'
       Pattern='\[roadrules\] action 277 -> gui 335 type 1' }
    # ---- showtime ends: the leaving 143, then the scored crash rule ----------------------------
    @{ Kind='LogValue';   Name='leaving 143 posted with finalScore > 0'
       Pattern='\[showtime\] leaving: mode (2|16) .* finalScore (?<n>-?\d+)'
       Group='n'; Agg='max'; Min=1 }
    @{ Kind='LogMatch';   Name='crash rule ended as a scored attempt (278 type 1 valid 1)'
       Pattern='\[roadrules\] action 278 -> gui 336 type 1 score [\d.eE+-]+ valid 1' }
    @{ Kind='LogValue';   Name='the crash rule carried the showtime score (> 0)'
       Pattern='\[roadrules\] action 278 -> gui 336 type 1 score (?<s>[\d.eE+-]+) valid 1'
       Group='s'; Agg='max'; Min=1 }
  )
}
