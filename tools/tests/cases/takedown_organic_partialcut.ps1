# takedown_organic_partialcut -- THE FIRST PARTIAL-LOCK VARIANT. Same chain, same teleport, same
# junction as takedown_organic; the only change is that the aim is a HALF-STICK lane change instead
# of a full lock, so the car crosses onto the rivals' line WITHOUT losing its speed.
#
# WHY (measured on takedown_organic/20260913_170821, the wave 7 re-run of the kept setting):
#   * The start-line clamp holds steer at exactly 0.000000 until the frame gas goes 0.0999 -> 1.0,
#     which on that run is motion sample n~1500, about t+6.9 on the schedule clock. Everything
#     before that is un-steerable, so slot 1's 6.57 m pass at t+4.9 cannot be closed by any script.
#   * From t+6.9 the full `left` lock did cross the lane (x 3044.6 -> 3033.4 in 2.3 s) and then
#     killed the car: 8.05 m/s -> 5.5 m/s, then parked at (3005, -2034) at 0.90 m/s from t+13 to
#     t+35. The pack is 7-30 m away for the whole of t+8.2..t+18 and the player is stationary for
#     it. Losing the speed is what loses the window, not missing the lane.
#   * The rivals' line through this stretch is x 3035-3038; the player's start lane is x 3044.6, so
#     the lane change needed is about -7 m, not -11 m.
# So: half stick from t+0 (which the clamp defers to its own release), straightened at t+9.5, then
# a dead-straight full-throttle run down the rivals' lane while the pack is still inside 30 m.
#
# Everything else -- teleport, event, diag env, the 13-check ladder -- is takedown_organic's, so the
# two runs differ in exactly one field and are directly comparable.
@{
  Name    = 'takedown_organic_partialcut'
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
    SteerScript     = '0:left50,9.5:none'
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
