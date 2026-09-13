# takedown_organic_lanepulse -- A QUARTER-STICK PULSE TIMED ON THE CLAMP RELEASE, NOT ON t+0.
#
# THE GEOMETRY, and it is the same in all four wave 7 runs so far. The place-on-track snap pins the
# player to ONE lane, x 3044.61, to seven digits -- takedown_organic_headon asked for a teleport
# 4 m further across and landed on exactly the same 3044.61, so the teleport CANNOT move the car
# laterally and every variant starts in the same place. The pack uses two lanes either side of it:
#   x 3047-3051  going DOWN the road (the launch, slots 1/2/3 at 40-54 m/s)
#   x 3037-3038  coming back UP it (slots 1/2 again later, and slot 5)
# So the player sits in the middle and the closest approach is a LANE WIDTH: 6.47 / 6.57 / 6.69 /
# 6.72 m in four runs, and 3.37-7.18 m across the wave 6 six. Nothing about timing or aggression
# closes that; only lateral position does.
#
# WHY A PULSE, AND WHY IT STARTS AT 7.0 AND NOT AT 0. Steering is dead until the clamp lifts, which
# is motion sample n~1500 == about t+6.9 in every run measured, and a token held from t+0 is
# therefore applied at full strength on the release frame. Measured that way:
#   `left`   (full)      3044.6 -> 3033.4 in 2.3 s AND 8.05 -> 5.5 m/s, then parked at 0.90 m/s
#   `left50` (half)      3044.6 -> 3028.9 in 1.5 s, off the road, 13.4 -> 2.7 m/s
# Both overshoot the -6.7 m the up-road lane needs, and both cost the speed that keeps the player
# in the window at all. So this variant holds NOTHING at t+0, presses a quarter stick at t+7.0 --
# on the release, as a mid-drive token, which the wave 7 harness lane says now lands -- and lets go
# at t+8.8. Half the deflection for a little over half the time.
#
# WHAT A RED RUN STILL MEASURES. The [motion] steer column says whether a mid-drive token landed at
# all (a burst at t+7.0, zero before it), and the x column says how far a 1.8 s quarter stick moves
# the car -- which is the number the next variant needs and no run has yet produced.
@{
  Name    = 'takedown_organic_lanepulse'
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
    SteerScript     = '0:none,7.0:left25,8.8:none'
    MaxSeconds      = 120
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

    # THE SCENARIO METRIC. Informational and unbounded -- it never fails; it exists so the next
    # variant can be compared against the campaign above instead of re-deriving it. 3.37 m is the
    # closest any of the seven settings got, and no setting has ever produced a contact.
    @{ Kind = 'Script'; Name = 'info: closest rival approach this run'
       Script = {
         param($ctx)
         $lfMin = [double]::PositiveInfinity
         foreach ($lsLine in $ctx.LogLines) {
           if ($lsLine -match '\[rival\].* dist ([0-9.]+)') {
             $lfD = [double]$Matches[1]
             if ($lfD -lt $lfMin) { $lfMin = $lfD }
           }
         }
         if ([double]::IsInfinity($lfMin)) {
           return @{ Pass = $true; Detail = 'no [rival] samples in this log -- the trace needs BRN_TRAFFIC_DIAG' }
         }
         return @{ Pass = $true; Detail = ("closest rival approach {0:f2} m (campaign range 3.37-7.18 m over seven settings, and not one produced a [td-contact] entry)" -f $lfMin) }
       } }

    @{ Kind = 'LogMatch';   Name = 'the AI module received ON_PLAYER_TAKEDOWN'
       Pattern = '\[ai-evt\] action 14 ON_PLAYER_TAKEDOWN'; Expect = $true }
    @{ Kind = 'LogMatch';   Name = 'arbitrator entered the takedown camera state (EState 3)'
       Pattern = '\[crashcam\] container current state -> 3\b'; Expect = $true }
  )
}
