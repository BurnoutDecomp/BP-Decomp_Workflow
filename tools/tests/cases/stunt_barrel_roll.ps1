# stunt_barrel_roll -- issue #23: in a Stunt Run a barrel roll stays "held" and never banks.
#
# THE SCENARIO. One boot, one Stunt Run (junction 480897, event 558269), then a ladder of ramp
# shots fired INSIDE the running event:
#   shot 0  places the car in the junction at rest, so -StartEvent/-EventFsm start the event there
#           (the same junction pose stunt_run_lifecycle teleports to).
#   shot 1+ place the car on the -Jump ramp approach (x~3027, the bridge crest at z -272..-208) at
#           44 m/s on the ramp axis. The crest is twisted: the car leaves it with |right.y| ~0.8 and
#           rolls ~230 degrees in the air, and at 44 m/s it comes down on its wheels without a crash
#           (measured 2026-09-28 on three separate shots: completedRollDeg 229 / 234 / 253, rolls=1,
#           crashing=0). Faster shots (50+ m/s) roll further and land on the roof, which is a crash
#           and loses the combo by design, so they are not in this ladder.
# -CrashSweep is used instead of -Teleport because it is the only placement that can fire more
# than once per boot; the shots are counted in sim frames (settle 720 = 12 s), which leaves room
# for the 0.5 s bank window plus the 5 s no-stunt combo timeout after each landing.
#
# WHAT THE SCORER DOES WITH A ROLL. StuntModeScoring::UpdateAirStunts reads the player car's
# in-air rotation accumulator (ActiveRaceCar::UpdateInAirRotations) EVERY frame and, while its
# roll lane is past the 180 gate, re-awards BARREL_ROLL. That keeps the category active, and
# ShouldBankScore refuses to bank while a bankable category is active. The accumulator is cleared
# on the first frame all four wheels are attached and gripping again, so after a clean landing
# the roll banks 0.5 s later and the combo closes 5 s after that with its multiplier. Before the
# 2026-09-15 landing-pass polarity fix the landing pass never ran, the roll was never rated and
# the combo was held open for the rest of the run -- the reported symptom.
#
# WITNESSES (all opt-in PC witnesses):
#   [stunt] award type=1 BARREL_ROLL ...   StuntModeScoring::UpdateScore (BRN_STUNT_DIAG)
#   [stunt] combo banked ...               StuntModeScoring::EndCombo    (BRN_STUNT_DIAG)
#   [stuntair] takeoff/rolling/land ...    StuntOffencesManager         (BRN_ROLL_PROBE)
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case stunt_barrel_roll
#
@{
  Name    = 'stunt_barrel_roll'
  Area    = 'events/stunt'
  Bug     = 'issue #23 -- a barrel roll in a Stunt Run stays in progress and never banks for the multiplier'
  Frames  = $false
  ProfileFixture = 'scratch\gameplay_wave\profile_backup\Profile.sav.pose250700'
  Run     = @{
    Drive           = $true
    MotionProbe     = $true
    StartEvent      = $true
    EventFsm        = $true
    SkipTrainingTip = $true
    SkipIntro       = $true
    AcceptGap       = 1.0
    MaxSeconds      = 100
    CrashSweep      = '2641.5,1.3,-1723.8'
    CrashSweepShots = '2641.5/1.3/-1723.8/169:0,3027/-9.2/-330/0:44,3027/-9.2/-330/0:44,3027/-9.2/-330/0:44'
    CrashSweepSettle = 720
    CrashSweepMax    = 1200
  }
  DiagEnv = 'BRN_PROP_DIAG=1,BRN_STUNT_DIAG=1,BRN_ROLL_PROBE=1,BRN_STUNT23_DIAG=1'
  Checks  = @(
    @{ Kind='NewAsserts'; Name='no NEW assert families' }
    @{ Kind='LogCount'; Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }
    @{ Kind='Mark';     Name='event started (action 23 -> gui 93)'; Cue='e-start' }
    @{ Kind='Mark';     Name='mode reached E_GMS_IN_PROGRESS';      Cue='e-inprog' }

    # The precondition: the ramp produced at least one completed barrel roll that landed clean.
    @{ Kind='LogCount'; Name='a completed barrel roll landed without a crash'
       Pattern='\[stuntair\] land .* rolls=[1-9]\d* complete=\S+ crashing=0'; Min=1 }
    # The scorer saw the roll (the landing pass rated it).
    @{ Kind='LogMatch'; Name='the scorer awarded BARREL_ROLL'; Pattern='\[stunt\] award type=1 BARREL_ROLL' }
    # The scorer's in-air rotation must clear after every touchdown (StuntModeScoring::Update rung).
    @{ Kind='LogCount'; Name='never HELD: no live roll rotation 90 frames after a touchdown'; Pattern='\[stunt23\] HELD'; Max=0 }

    # THE BUG: every clean roll landing must be followed, before the next shot re-places the car,
    # by the combo closing with a score -- i.e. the roll banked instead of being held open.
    @{ Kind='Script'; Name='every clean roll landing banks before the next shot'; Script = {
        param($ctx)
        $lines = $ctx.LogLines
        $landings = 0; $banked = 0; $held = @(); $cut = @()
        for ($i = 0; $i -lt $lines.Count; $i++) {
          if ($lines[$i] -notmatch '\[stuntair\] land n=(\d+) .* rolls=[1-9]\d* complete=\S+ crashing=0') { continue }
          $n = $Matches[1]; $landings++
          $ok = $false; $ended = $false
          for ($j = $i + 1; $j -lt $lines.Count; $j++) {
            if ($lines[$j] -match '\[sweep\] shot ') { break }
            if ($lines[$j] -match '\[stunt\] combo banked score=[1-9]\d* mult=(\d+)') { $ok = $true; break }
            # The event timer ran out inside the bank window: the landing is cut, not held.
            if ($lines[$j] -match '\[stunt\] mode state -> E_GMS_OUTRO') { $ended = $true; break }
          }
          if ($ok) { $banked++ } elseif ($ended) { $cut += "n=$n" } else { $held += "n=$n" }
        }
        if ($landings -eq 0) { return @{ Pass = $false; Detail = 'no clean barrel-roll landing in the log' } }
        if ($held.Count -gt 0) { return @{ Pass = $false; Detail = ("{0}/{1} clean roll landing(s) never banked (held): {2}" -f $held.Count, $landings, ($held -join ' ')) } }
        $cutText = if ($cut.Count -gt 0) { " ({0} cut by the event end: {1})" -f $cut.Count, ($cut -join ' ') } else { '' }
        return @{ Pass = $true; Detail = ("{0}/{1} clean roll landing(s) banked a scored combo before the next shot{2}" -f $banked, $landings, $cutText) }
    } }
    # A banked barrel roll raises the combo multiplier above its neutral 1.
    @{ Kind='LogValue'; Name='a banked combo carries a multiplier > 1'
       Pattern='\[stunt\] combo banked score=[1-9]\d* mult=(?<v>\d+)'; Group='v'; Agg='max'; Min=2 }
  )
}
