# takedown_organic_headon -- REVERSE UP THE LAUNCH LANE AND MEET THE PACK HEAD-ON.
#
# WHY (measured, two runs on the wave 7 exe plus the kept roadblock trace):
#   * takedown_organic_roadblock/20260913_161941 is the only setting that ever puts the player in
#     the rivals' own lane at speed: `brake` held from t+0 is ignored for the whole start-line
#     clamp (the car still runs the clamp's 8.05 m/s to n1440, x constant to seven digits), bites
#     the instant the clamp lifts, and then drives the car BACKWARDS up the road -- z -1964 -> -1776
#     at 40 m/s with x pinned at 3044.6 the whole way. No steering token is involved, so there is
#     no spin and nothing to lose speed to.
#   * The pack launches DOWN that same road in the x 3047-3051 lane (slots 1, 2 and 3 all read
#     rx 3047.6-3051.6 through their whole launch). Reversing at 40 m/s into cars doing 40-54 m/s
#     is an 80-94 m/s closing speed in one lane -- and roadblock's own closest approach, 3.55 m, is
#     a LATERAL miss of about 3-6 m in x, not a timing miss.
#   * So the one thing to change is x, and steering cannot change it: the clamp holds steer at
#     exactly 0.000000 until the frame gas goes 0.0999 -> 1.0, which is the same frame the reverse
#     starts. THE TELEPORT CAN. 3040.7 lands the car at 3044.61 (the game's place-on-track snaps
#     it), so this variant asks for 3044.7 and expects to land about 4 m further into the launch
#     lane, with everything else -- heading, z, event, diag env, checks -- byte-identical to
#     roadblock.
#
# WHAT A RED RUN STILL MEASURES. If the pack passes clean at 3-6 m again, the landing x in the
# first [motion] samples after the teleport says whether the shift happened at all; if the car
# lands where roadblock's did, the road snap ate the offset and the next move is a different z,
# not a bigger x.
@{
  Name    = 'takedown_organic_headon'
  Area    = 'takedown'
  Bug     = 'takedown: a player ramming a RIVAL must produce a takedown through the real detection chain -- contact -> classifier -> crash queue -> TakedownManager -> scoring/AI/camera -- with no BRN_FORCE_TAKEDOWN'
  Frames  = $false
  Run     = @{
    Drive           = $true
    MotionProbe     = $true
    SkipIntro       = $true
    AcceptGap       = 1.0
    Teleport        = '3044.7,-5.8,-1937.9,180'   # +4 m in x vs every other variant: the launch lane
    StartEvent      = $true
    EventFsm        = $true
    SkipTrainingTip = $true
    # The sweep. Times are seconds since the FIRST harness input, which is the same clock the
    # measured pass times above are quoted on.
    ThrottleScript  = '0:brake'
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
