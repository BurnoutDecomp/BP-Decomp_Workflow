# takedown_organic -- A PLAYER-ON-RIVAL TAKEDOWN THROUGH THE REAL CHAIN, WITH NO BRN_FORCE_TAKEDOWN.
#
# Run it:  powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case takedown_organic
#
# THE SETTING KEPT HERE (wave 7): a 0.45 s QUARTER-STICK pulse at t+2.6, on a plain held throttle.
# Everything else -- teleport, event, diag env -- is unchanged from every earlier variant, so the
# whole campaign is directly comparable field by field.
#
# ============================================================================================
# THE GEOMETRY, AND WHY THE MISS IS A LANE WIDTH AND NOTHING ELSE
# ============================================================================================
# The place-on-track snap pins the player to ONE lane, x 3044.61, to seven digits. That is not a
# choice this case makes: takedown_organic_headon asked for a teleport 4 m further across and the
# car landed on exactly the same 3044.61, so the teleport CANNOT move the player laterally and
# every variant in the campaign starts in the same place. The pack uses two lanes either side:
#     x 3047-3051   going DOWN the road  (the launch: slots 1/2/3 at 40-54 m/s)
#     x 3037-3038   coming back UP it    (slots 1/2 again later, and slot 5)
# So the player sits in the middle, and "closest approach" over eleven settings is a lane width:
# 6.47 / 6.57 / 6.69 / 6.72 / 7.04 / 7.04 / 7.18 m, with 3.37-4.00 m only on the settings that
# drove the car off the road entirely. Aggression, window length and timing do not close that gap;
# lateral position is the only thing that does.
#
# ============================================================================================
# THE TWO NUMBERS WAVE 7 CORRECTED -- both were steering the whole campaign, and both were wrong
# ============================================================================================
#   * A MID-DRIVE STEER TOKEN LANDS. takedown_organic_lanepulse/20260913_172355 records
#     `input accel/left25 run=28,5s t+7,02s` in marks.txt and the [motion] steer column goes
#     0.0000 -> 0.0255 -> 0.0000 exactly across it. Every earlier variant set its aim at t+0
#     because a later token was believed to be ignored. It is not; a schedule can now aim.
#   * THE CLAMP RELEASE IS AT ABOUT t+0.2, NOT t+7-8. Anchor the frame counter on that same token
#     (t+7.02 and t+8.83 are 1.81 s apart and their two steer edges are 180 frames apart, so 99
#     frames/s) and the first harness input is at motion sample n~1485 -- while gas goes
#     0.0999 -> 1.0 at n1500. The car is free about a fifth of a second after t+0. The wave 6
#     reading of "t+8.1" came from an unanchored frame count; a variant aiming for the release at
#     t+7 fires its pulse at 38 m/s instead of at 10 and lands in a field.
#
# ============================================================================================
# THE STEERING RESPONSE, MEASURED -- the number every earlier variant was missing
# ============================================================================================
# Held from t+0 and applied on the release frame:
#     `left`   (full)  3044.6 -> 3033.4 in 2.3 s AND 8.05 -> 5.5 m/s, then parked at 0.90 m/s
#     `left50` (half)  3044.6 -> 3028.9 in 1.5 s, off the road, 13.4 -> 2.7 m/s
# As a timed mid-drive pulse:
#     left25 for 1.32 s from t+2.6 (18-26 m/s)   3044.6 -> 3017.0   == -27 m
#     left25 for 1.81 s from t+7.0 (35-38 m/s)   3044.6 -> 3010.5   == -34 m, off the road
# So a quarter stick is worth roughly -20 m per second of hold at road speed, and the lane this
# case needs is -7 m. Hence the 0.45 s asked for here.
#
# !! AND THE POINT THAT KILLS THE PULSE IDEA, measured on this file's own run
# (takedown_organic/20260913_173252): a schedule cannot hold a stick for 0.45 s. The harness polls
# at about 0.25 s, so marks.txt records the hold as t+2.83 -> t+3.10 -- 0.27 s, one poll -- and the
# [motion] steer column shows exactly one non-zero sample (0.0482 at n1620). That single quarter-
# stick sample still moved the car 17 m: x 3044.6 at n1620, then 3043.7, 3042.7, 3041.6, 3040.4,
# 3039.0, 3037.6, 3036.1, 3034.5, 3032.8, 3031.1, 3029.3, 3027.4 -- a DEAD-STRAIGHT drift at about
# -1.3 m per 60 frames with the stick already centred for the whole of it.
# A PULSE DOES NOT CHANGE LANE, IT CHANGES HEADING, and nothing brings the heading back. That is
# why every variant in this campaign either misses by a lane or ends up in a field, and it is why
# the next setting to try is a COUNTER-STEER PAIR -- one poll of left25 then one poll of right25,
# about half a second apart -- and not a longer or shorter single hold. Unrun as of this file.
#
# ============================================================================================
# WHAT IS STILL RED, AND THE ONE MEASUREMENT THAT NAMES IT
# ============================================================================================
# Six wave 7 runs, zero [td-contact] entries, exactly as the wave 6 six. But two of them put the
# player closer than the whole campaign had managed and the chain still recorded nothing:
#   * lanepulse got 2.69 m, and from n2730 to n3450 -- SIX SECONDS -- slot 4 held dx 0.04-1.39 m
#     and dz 2.63-3.30 m off the player while both cars moved 30 m.
#   * abreast got 3.39 m, with slot 5 at dx 3.3-4.4 m and dz 0.3-2.6 m for four seconds.
#   * this file's own run got 5.46 m -- slot 2 dead abreast, dz -0.03 m, one lane over.
# Over those same runs the [storecontact] census reads, in every report period:
#       ownerA: 0=N 3=.. 6=M 7=K 11=..      droppedB: 3=.. 6=M 7=K
# HOW TO READ IT. Each surviving contact is stored twice, as-is and A/B-swapped, and only the copy
# whose A side is the world owner is dropped -- so a race-car-body-vs-WORLD contact contributes one
# to ownerA[6] and one to droppedB[6], while a race-car-body-vs-anything-else contact contributes
# two to ownerA[6] and nothing to droppedB[6]. The EXCESS of ownerA[6] over droppedB[6] is therefore
# the count of race-car-body contacts against something that is not scenery.
# THE READING, and it is the one number to check first on any future run:
#     leftcut (the wave 6 kept setting, 180 s)  A[6]=14423  droppedB[6]=14095  excess 328
#     partialcut / headon / lanepulse / abreast / this file    excess 0, exactly, in every report
# The five short runs put a race-car body against nothing but the world for their whole length --
# including the six seconds lanepulse spent with slot 4 at dx 0.04 m. The control that says the
# census is not simply blind is in the same line: this file's own run reads ownerA[7]=1515 against
# droppedB[7]=1498 and ownerA[3]=5410 against droppedB[3]=4558, so traffic bodies and props DO
# register non-world partners in the same reports.
# !! WHAT THE EXCESS DOES NOT PROVE. An unpaired owner-6 store says a race-car body touched a
# non-world entity; it does NOT say the partner was another car. leftcut also carries 4,081
# unpaired PROP stores, and a race-car body against a prop lands in exactly the same excess. The
# census narrows the question to one owner pair; it does not answer it. A B-side histogram on the
# NON-dropped arm would, and that is a source change, not a harness one.
# That is UPSTREAM of the ownerB gate this case was written to turn, and it is what a run should
# read first: the census check below prints both columns so the next reader does not re-derive it.
#
# ============================================================================================
# WITNESSES SCORED HERE
# ============================================================================================
#   [td-spies]     queue length + a 14-bucket ownerB histogram   ProcessContactSpies
#   [storecontact] ownerA / droppedB owner censuses              the physics contact store
#   [td-contact]   entry / verdict                               the race-car contact handler
#   [td-crash]     attacker -> victim (BOTH now named by owner), takedownType, slot
#   [mugshot] / [payback]  takedown consumed / registered
#   [td]           <n> takedown event(s) this frame
#   [ai-evt]       action 14 ON_PLAYER_TAKEDOWN
#   [crashcam]     container current state -> 3
#
# NOTE ON [td-crash], NEW THIS WAVE. Both ids now print their owner by name, and that retires the
# wave 6 reading that "the player is reaching rivals": not one record in six wave 7 runs has a
# race-car attacker. They are all `attacker world(0):0` (a rival hitting scenery) or
# `attacker traffic(2):<n>` (a rival hitting traffic). The player appears in none of them.
@{
  Name    = 'takedown_organic'
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
    SteerScript     = '0:none,2.6:left25,3.05:none'
    MaxSeconds      = 120
  }
  DiagEnv = 'BRN_AI_MADNESS=1,BRN_CRASHCAM_DIAG=1,BRN_TRAFFIC_DIAG=1,BRN_VFXFEED_PROBE=1,BRN_SHOWTIME_WATCH=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }

    # RUNG -1 -- WAS THE CAR-VS-CAR POTENTIAL-CONTACT QUEUE [7] EVER FED. Informational. The
    # [bridge-queues] accumulator prints a qN= column only for queues that were ever non-empty,
    # so no q7= column on a run with rivals means the two car hulls never overlapped at all.
    @{ Kind = 'LogCount';   Name = 'info: [bridge-queues] lines with a q7= (car/car) column'
       Pattern = '\[bridge-queues\][^\r\n]* q7=' }
    @{ Kind = 'LogCount';   Name = 'info: [Q7-carcar] first pair per queue id'
       Pattern = '\[Q7-carcar\]' }

    # RUNG 0 -- the contact-spy queue. Informational: it never fails, it only says whether the
    # race-car contact arm was fed at all this run.
    @{ Kind = 'LogCount';   Name = 'info: [td-spies] contact-spy census lines'
       Pattern = '\[td-spies\]' }

    # RUNG 0b -- DID ANY TWO CAR BODIES TOUCH AT ALL. Informational, and it is the rung that tells
    # a scenario miss apart from a chain miss. The store writes every surviving contact twice, as-is
    # and A/B-swapped, and drops only the copy whose A side is the world owner -- so a part-vs-WORLD
    # contact adds one to ownerA[6] and one to droppedB[6], while a part-vs-PART contact would add
    # two to ownerA[6] and NOTHING to droppedB[6]. Equal columns therefore mean zero car-body-vs-
    # car-body stores, whatever the [rival] trace says about separation.
    @{ Kind = 'Script'; Name = 'info: [storecontact] car-body-vs-car-body stores'
       Script = {
         param($ctx)
         $lsA = $null; $lsB = $null
         foreach ($lsLine in $ctx.LogLines) {
           if ($lsLine -match '\[storecontact\] ownerA: (.+?) \| distinct')   { $lsA = $Matches[1].Trim() }
           if ($lsLine -match '\[storecontact\] droppedB: (.+?) \| distinct') { $lsB = $Matches[1].Trim() }
         }
         if (-not $lsA) { return @{ Pass = $true; Detail = 'no [storecontact] census in this log -- the trace needs BRN_VFXFEED_PROBE' } }
         $lhA = @{}; $lhB = @{}
         foreach ($lsTok in ($lsA -split '\s+')) { if ($lsTok -match '^(\d+)=(\d+)$') { $lhA[$Matches[1]] = [int]$Matches[2] } }
         foreach ($lsTok in ($lsB -split '\s+')) { if ($lsTok -match '^(\d+)=(\d+)$') { $lhB[$Matches[1]] = [int]$Matches[2] } }
         $lasPairs = @()
         foreach ($lsOwner in @('6','7','9','10')) {
           $liA = 0; $liB = 0
           if ($lhA.ContainsKey($lsOwner)) { $liA = $lhA[$lsOwner] }
           if ($lhB.ContainsKey($lsOwner)) { $liB = $lhB[$lsOwner] }
           if ($liA -ne 0 -or $liB -ne 0) {
             $lsVerdict = 'NO part-vs-part store'
             if ($liA -ne $liB) { $lsVerdict = ("{0} UNPAIRED -- a car body touched something that is not the world" -f ($liA - $liB)) }
             $lasPairs += ("owner {0}: A={1} droppedB={2} -> {3}" -f $lsOwner, $liA, $liB, $lsVerdict)
           }
         }
         return @{ Pass = $true; Detail = ("final census  ownerA[{0}]  droppedB[{1}]  ||  {2}" -f $lsA, $lsB, ($lasPairs -join ' ; ')) }
       } }

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
         return @{ Pass = $true; Detail = ("closest rival approach {0:f2} m (campaign best 2.69 m over eleven settings, and not one produced a [td-contact] entry)" -f $lfMin) }
       } }

    @{ Kind = 'LogMatch';   Name = 'the AI module received ON_PLAYER_TAKEDOWN'
       Pattern = '\[ai-evt\] action 14 ON_PLAYER_TAKEDOWN'; Expect = $true }
    @{ Kind = 'LogMatch';   Name = 'arbitrator entered the takedown camera state (EState 3)'
       Pattern = '\[crashcam\] container current state -> 3\b'; Expect = $true }
  )
}
