# takedown_organic_abreast -- THE PULSE MOVED TO THE FRAME A RIVAL IS ACTUALLY ALONGSIDE.
#
# WHAT takedown_organic_lanepulse/20260913_172355 SETTLED, and it corrects two numbers the whole
# campaign had been steering by:
#   * A MID-DRIVE STEER TOKEN LANDS. marks.txt records `input accel/left25 run=28,5s t+7,02s` and
#     the [motion] steer column goes 0.0000 -> 0.0255 -> 0.0000 exactly across it. Every earlier
#     variant set its aim at t+0 because a later token was believed to be ignored; that is no
#     longer a constraint on a schedule.
#   * THE CLAMP RELEASE IS NOT AT t+7-8. Anchoring the frame counter on that token (t+7.02 and
#     t+8.83 are 1.81 s apart and their two steer edges are 180 frames apart, so 99 frames/s) puts
#     the first harness input at n~1485 -- and gas goes 0.0999 -> 1.0 at n1500. The car is free
#     about a fifth of a second after t+0, not seven seconds. Aiming for "the release" at t+7 fired
#     the pulse at 38 m/s instead of 10, threw the car 22 m sideways off the road, and is why that
#     run finished the scenario crawling through a field.
#   * IT STILL SET THE CAMPAIGN RECORD: closest approach 2.69 m, against 3.37 m for all seven
#     earlier settings. From n2730 to n3450 -- six seconds -- slot 4 held dx 0.04-1.39 m and
#     dz 2.63-3.30 m off the player while both cars moved 30 m. Whatever that is, it is not a
#     scenario that missed the pack.
#
# THE SHOT THIS VARIANT TAKES. In that same run slot 4 comes DEAD ABREAST at n1890 -- dz -0.01 m,
# dx -7.11 m, about t+4.1 -- with the player at 30 m/s and still on the road. Seven metres is one
# lane. So the pulse moves to t+2.6 and lasts 1.1 s, which at 24-30 m/s is roughly the -7 m the
# lane is wide, and it is over before the car reaches the speed at which a quarter stick throws it
# off the road.
@{
  Name    = 'takedown_organic_abreast'
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
    SteerScript     = '0:none,2.6:left25,3.7:none'
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
