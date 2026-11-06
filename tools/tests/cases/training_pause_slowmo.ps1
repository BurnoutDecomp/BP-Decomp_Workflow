# training_pause_slowmo -- the director's slow-down into a training pause.
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case training_pause_slowmo -Slot 12
#
# WHAT IS BEING MEASURED. Arbitrator::Update @0x8226ADA0 (0x8226B130..0x8226B24C): while
# GameState +0x1C2 mbTrainingPause is set (director action 150, posted by TrainingManager when a
# pausing tip starts), mfSlomoFactor eases 1 -> 0 at 0.05 a frame into the camera's sim time
# scale and depth-of-field blur, and under 0.05 the director sets its output pause request
# (DirectorOutputInterface +0x0E/+0x0F), which GameModule turns into game event 43 and
# RequestPause(E_PAUSE_GAME_TRAINING). When the tip goes (action 151) it eases back up and drops
# the latch past 0.95. A fresh profile shows the first junkyard tips, which pause.
#
# WITNESS (opt-in, [diag] not in the X360 binary): BRN_TRAINING_SLOMO_DIAG prints
#   [training-slomo] start | pause request (slomo f) | released
# and BRN_DIRECTOR_ACTION_DIAG the 150 / 151 arms.
#
# RED (before): no [training-slomo] line; the training pause comes from TrainingManager alone.
# GREEN: start, then the pause request, after a 150; released after a 151.
@{
  Name    = 'training_pause_slowmo'
  Area    = 'director'
  Bug     = 'Arbitrator::Update training slow-down (Jump_Effect, mbTrainingPause) was gated off'
  Frames  = $false
  FreshProfile = $true
  Run     = @{
    TitleStart  = $true
    Drive       = $true
    MaxSeconds  = 140
    SkipIntro   = $true
    AcceptGap   = 1.0
    Teleport    = '3040.7,-5.8,-1937.9,180'   # the road outside the junkyard exit (baseline's)
  }
  DiagEnv = 'BRN_TRAINING_SLOMO_DIAG=1,BRN_DIRECTOR_ACTION_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions';   Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }

    @{ Kind = 'LogMatch';   Name = 'a pausing training tip set mbTrainingPause (action 150)'
       Pattern = '\[director-action\] 150 GAME_TRAINING_PAUSE -> mbTrainingPause 1' }

    @{ Kind = 'Script'; Name = 'slow-down starts after 150 and ends in the pause request'; Script = {
        param($ctx)
        $lines = $ctx.LogLines
        $a150 = -1; $start = -1; $req = -1
        for ($i = 0; $i -lt $lines.Count; $i++) {
          if ($a150 -lt 0 -and $lines[$i] -match '\[director-action\] 150 ') { $a150 = $i; continue }
          if ($a150 -ge 0 -and $start -lt 0 -and $lines[$i] -match '\[training-slomo\] start') { $start = $i; continue }
          if ($start -ge 0 -and $lines[$i] -match '\[training-slomo\] pause request') { $req = $i; break }
        }
        if ($a150 -lt 0) { return @{ Pass = $false; Detail = 'no action 150' } }
        if ($start -lt 0) { return @{ Pass = $false; Detail = "action 150 at line $a150, no [training-slomo] start after it" } }
        if ($req -lt 0) { return @{ Pass = $false; Detail = "start at line $start, no pause request after it" } }
        return @{ Pass = $true; Detail = "150 @$a150, start @$start, pause request @$req" }
    } }

    @{ Kind = 'Script'; Name = 'the slow-down releases after 151'; Script = {
        param($ctx)
        $lines = $ctx.LogLines
        $a151 = -1; $rel = -1
        for ($i = 0; $i -lt $lines.Count; $i++) {
          if ($a151 -lt 0 -and $lines[$i] -match '\[director-action\] 151 ') { $a151 = $i; continue }
          if ($a151 -ge 0 -and $lines[$i] -match '\[training-slomo\] released') { $rel = $i; break }
        }
        if ($a151 -lt 0) { return @{ Pass = $false; Detail = 'no action 151' } }
        if ($rel -lt 0) { return @{ Pass = $false; Detail = "action 151 at line $a151, no release after it" } }
        return @{ Pass = $true; Detail = "151 @$a151, released @$rel" }
    } }
  )
}
