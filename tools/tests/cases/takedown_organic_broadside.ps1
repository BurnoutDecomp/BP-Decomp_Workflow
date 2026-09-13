# takedown_organic_broadside -- SAME CHAIN AS takedown_organic, BUT THE PLAYER IS AIMED AT THE PACK.
#
# Run it:  powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case takedown_organic_broadside
#
# WHY THIS VARIANT EXISTS. takedown_organic is RED for a scenario reason, not a chain reason: it
# holds a dead-straight throttle and the closest a rival ever gets is 6.69 m, so [td-contact] stays
# 0 and every leg below it is unjudgeable. The geometry that makes the straight-line run fail is
# fully readable in its own traces (run 20260913_152538, [rival] + [motion]):
#
#   * The teleport lands the player at (3044.6, -1907.6) and the event's start-line clamp pins the
#     throttle at ~0.10 and the speed at exactly 8.05 m/s for ~6 s. Lateral position is untouched
#     (x is constant to seven digits) only because the steer input was zero -- the clamp is on the
#     throttle, not on the steering.
#   * The five rivals spawn BEHIND, 46-125 m back, then launch to 40-54 m/s and sweep past the
#     crawling player. Measured passes, in schedule seconds (t = first harness input):
#         t+6   slot 1 at 6.69 m, x 3047.7 -- passes on the RIGHT
#         t+8   slot 5 at 10.2 m
#         t+10  slot 3 at 15.1 m, x 3037.8 -- passes on the LEFT
#         t+11  slot 4 at 8.05 m, x 3036.8, z -2032.9 == the player's own z -- dead ABREAST, LEFT
#     After t+12 the pack is 60-160 m up the road at 40+ m/s and the player, topping out near
#     38 m/s, never sees them again. The whole opportunity is a ~7 s window.
#   * Every rival sample carries `victim 0`: they are hunting traffic, never the player. So the
#     contact has to be made BY the player -- which is also the takedown this wave is for.
#
# THE FIVE RUNS BEFORE THIS ONE, AND WHAT EACH ONE RULED OUT.
#
#   takedown_organic          20260913_152538  straight throttle hold                 min 6.69 m
#   takedown_organic_weave    20260913_160142  five left/right pulses over t+5..t+13  min 7.18 m
#   takedown_organic_cutin    20260913_160627  `right` pressed at t+9.8 and t+12.9    min 7.04 m
#   takedown_organic_rightlock 20260913_161001 `right` held from t+0                  min 3.37 m
#   takedown_organic_leftcut  20260913_161444  `left`  held from t+0                  min 4.00 m
#   takedown_organic_roadblock 20260913_161941 `brake` held from t+0                  min 3.55 m
#
# Not one of them logged a single [td-contact] entry. Four mechanics came out of the [motion]
# steer/x columns and the [rival] trace:
#   * The start-line clamp pins the STEERING as well as the throttle -- steer reads exactly
#     0.000000 for the whole clamp and snaps to the pi/8 limit on the one frame gas goes
#     0.0999 -> 1.0 (n=1470, about t+8.1). A token pressed after that mostly never lands, so only
#     the token held at t+0 is reliable, on either channel.
#   * The signs are real and opposite: `right` takes the car to +x, `left` to -x, the pack's side.
#   * FULL LOCK UNDER THROTTLE IS A SPIN, NOT A LANE CHANGE. leftcut fell from 11.9 m/s to
#     0.84 m/s inside 2 s and parked 4 m wide of the racing line and 20-55 m up-road of the passes.
#   * `brake` from t+0 DOES stop the car cleanly on the clamp release (8.06 -> 0.24 m/s over
#     n=1440..1500) and then reverses it back up the road at up to 14 m/s -- straight at the
#     oncoming pack -- but it holds the start lane at x 3044.6, and the rivals' line through this
#     stretch is x 3035-3038.
#
# THE APPROACH. Use both channels at t+0, which is the one combination left: `brake` to kill the
# run-away and keep the car slow, and `left` to walk it off the start lane onto the rivals' line
# while it is too slow for the lock to spin it. What that should leave is a slow, broadside car
# parked in the racing line for the rest of a 180 s window, with five rivals at aggression 14
# looping back through this stretch at 13-53 m/s. This is the fallback the brief allows -- a
# rival-on-player contact rather than a player-on-rival ram -- aimed at the one leg that has never
# fired: [td-contact], and with it an ownerB reading on a pair that is actually two race cars.
#
# WITNESSES SCORED HERE (all present on this exe; the first four are new since takedown_organic):
#   [td-spies]   queue length + a 14-bucket ownerB histogram    BrnVehicleManager_ProcessContactSpies.cpp
#   [td-contact] entry / verdict                                BrnVehicleManager.cpp
#   [td-crash]   attacker -> victim, takedownType, slot          BrnVehicleManager.cpp SetRaceCarCrashing
#   [mugshot] / [payback] takedown consumed / registered         BrnMugshotManager / BrnPaybackManager
#   [td]         <n> takedown event(s) this frame                GameStateModule_gTD_00.cpp
#   [ai-evt]     action 14 ON_PLAYER_TAKEDOWN                    BrnAIModule_Events.cpp
#   [crashcam]   container current state -> 3                    ArbitratorStateContainer::SetCurrentState
#
# BRN_GLASSFX_DIAG is now default-OFF, so the per-frame trace that drove the 128 MB log abort at
# ~150 s is gone and the window is no longer log-capped. It is still kept short on purpose: the
# scenario's whole decision is over by run second ~40.
@{
  Name    = 'takedown_organic_broadside'
  Area    = 'takedown'
  Bug     = 'takedown: a player ramming a RIVAL must produce a takedown through the real detection chain -- contact -> classifier -> crash queue -> TakedownManager -> scoring/AI/camera -- with no BRN_FORCE_TAKEDOWN'
  Frames  = $false
  Run     = @{
    Drive           = $true
    MotionProbe     = $true
    SkipIntro       = $true
    AcceptGap       = 1.0
    Teleport        = '3040.7,-5.8,-1937.9,180'   # unchanged: Road Rage junction 480861
    StartEvent      = $true
    EventFsm        = $true
    SkipTrainingTip = $true
    # The sweep. Times are seconds since the FIRST harness input, which is the same clock the
    # measured pass times above are quoted on.
    ThrottleScript  = '0:brake'
    SteerScript     = '0:left'
    MaxSeconds      = 180
  }
  DiagEnv = 'BRN_AI_MADNESS=1,BRN_CRASHCAM_DIAG=1,BRN_TRAFFIC_DIAG=1,BRN_VFXFEED_PROBE=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }

    # RUNG 0 -- the contact-spy queue. Informational: it never fails, it only says whether the
    # race-car contact arm was fed at all this run.
    @{ Kind = 'LogCount';   Name = 'info: [td-spies] contact-spy census lines'
       Pattern = '\[td-spies\]' }

    # RUNG 1 -- THE LEG THIS VARIANT EXISTS TO TURN. takedown_organic scores 0 here on four
    # separate runs; a single line is new evidence, so this check is RED on the old runs by
    # construction and can only go GREEN off a real player-on-rival contact.
    @{ Kind = 'LogMatch';   Name = 'a race-car vs race-car contact reached HandleRaceCarRaceCarContact'
       Pattern = '\[td-contact\] entry race car'; Expect = $true }

    # RUNG 2 -- the classifier actually ruled on it. Informational: an entry with no verdict means
    # a pre-classifier gate returned, which is a different seam from "no contact".
    @{ Kind = 'LogCount';   Name = 'info: [td-contact] classifier verdicts'
       Pattern = '\[td-contact\] verdict' }

    # RUNG 3 -- the crash-commit sink allocated a record and named a takedown type.
    @{ Kind = 'LogCount';   Name = 'info: [td-crash] crash records committed'
       Pattern = '\[td-crash\] attacker' }

    # RUNG 4 -- THE CASE. A takedown reached ProcessTakedownEvents, and it was not the harness's.
    @{ Kind = 'Script'; Name = 'an ORGANIC takedown was detected and counted (no harness line)'
       Script = {
         param($ctx)
         $laLines   = $ctx.LogLines
         $laTd      = @($laLines | Where-Object { $_ -match '\[td\]' })
         $laHarness = @($laTd    | Where-Object { $_ -match '\[td\] HARNESS force-takedown' })
         $laEvents  = @($laTd    | Where-Object { $_ -match '\[td\] (\d+) takedown event\(s\) this frame' })
         $laEntry   = @($laLines | Where-Object { $_ -match '\[td-contact\] entry race car' })
         $laVerdict = @($laLines | Where-Object { $_ -match '\[td-contact\] verdict' })
         $laCrash   = @($laLines | Where-Object { $_ -match '\[td-crash\] attacker' })
         $laExc     = @($laLines | Where-Object { $_ -match '\[EXCEPTION\]' })
         if ($laHarness.Count -gt 0) {
           return @{ Pass = $false; Detail = ("BRN_FORCE_TAKEDOWN LEAKED into this run ({0} harness line(s)) -- the run measures nothing; first: {1}" -f $laHarness.Count, "$($laHarness[0])".Trim()) }
         }
         if ($laEvents.Count -gt 0) {
           return @{ Pass = $true; Detail = ("{0} organic takedown frame(s); {1} contact entr(ies), {2} verdict(s), {3} crash record(s); first: {4}" -f $laEvents.Count, $laEntry.Count, $laVerdict.Count, $laCrash.Count, "$($laEvents[0])".Trim()) }
         }
         # Name the DEEPEST rung that fired, so a RED run points at one seam instead of the chain.
         $lsWhy = if ($laExc.Count -gt 0) {
           'but the run DIED first: ' + "$($laExc[0])".Trim() + ' -- fix the crash before reading this leg'
         } elseif ($laEntry.Count -eq 0) {
           'and no race-car vs race-car contact reached HandleRaceCarRaceCarContact at all ([td-contact] entry count 0) -- the sweep still missed the pack, or the contact never became a race-car pair; that is upstream of the classifier'
         } elseif ($laVerdict.Count -eq 0) {
           ("but {0} contact(s) DID enter HandleRaceCarRaceCarContact and NONE reached a verdict -- a pre-classifier gate returns before CheckForAllTypesOfImpacts; first entry: {1}" -f $laEntry.Count, "$($laEntry[0])".Trim())
         } elseif ($laCrash.Count -eq 0) {
           ("but {0} contact(s) were CLASSIFIED and none committed a crash record -- the seam is between the classifier verdict and SetRaceCarCrashing; first verdict: {1}" -f $laVerdict.Count, "$($laVerdict[0])".Trim())
         } else {
           ("but {0} crash record(s) WERE committed and no takedown was counted -- the seam is downstream of SetRaceCarCrashing (crash queue -> world bridge -> TakedownManager::Update); first record: {1}" -f $laCrash.Count, "$($laCrash[0])".Trim())
         }
         return @{ Pass = $false; Detail = ("no organic takedown was counted; {0}" -f $lsWhy) }
       } }

    # RUNG 5 -- the consumers wave 5 landed and never exercised.
    @{ Kind = 'LogCount';   Name = 'info: [mugshot] takedowns consumed'
       Pattern = '\[mugshot\] takedown consumed' }
    @{ Kind = 'LogCount';   Name = 'info: [payback] takedowns registered'
       Pattern = '\[payback\] takedown registered' }

    @{ Kind = 'LogMatch';   Name = 'the AI module received ON_PLAYER_TAKEDOWN'
       Pattern = '\[ai-evt\] action 14 ON_PLAYER_TAKEDOWN'; Expect = $true }
    @{ Kind = 'LogMatch';   Name = 'arbitrator entered the takedown camera state (EState 3)'
       Pattern = '\[crashcam\] container current state -> 3\b'; Expect = $true }
  )
}
