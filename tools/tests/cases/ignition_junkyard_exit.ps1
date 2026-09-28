# ignition_junkyard_exit -- lane IGNITION, gameplay wave GW3 (b5-decomp issue #13).
#
# BUG: "vehicle's ignition is always on". On the console the car leaves the junkyard with its
# engine OFF (no tail lights, no HUD); holding the gas cranks it (STARTING, 1.2 s, RUNNING);
# standing still with no pedal for 15 s switches it off again (STOPPING, 0.5 s, OFF).
# ActiveRaceCar::UpdateEngineState is that state machine:
#   OFF --(gas|brake > 0.05)--> STARTING --(1.2 s held)--> RUNNING
#   RUNNING --(no pedal and |mph| <= 2 for 15 s)--> STOPPING --(0.5 s)--> OFF
# and its force-RUNNING early-out is taken only when the car is in a game mode (an event) or
# may not switch its engine off.
#
# WITNESSES (always on, no env var):
#   [ignition] attach slot 0 type=0 ... inCarSelect=0 ... -> carInGameMode=<0|1>
#       BrnRaceCarEntityModule.cpp, one line per attach; the junkyard-exit attach is the last
#       type=0 line with inCarSelect=0.
#   [ignition] tick state=<n> ... accel=<f> brake=<f>
#       BrnActiveRaceCar.cpp UpdateEngineState, printed on every state CHANGE of the player car
#       (0 OFF, 1 STARTING, 2 RUNNING, 3 STOPPING) with the pedal values that frame.
#   [hud-reveal] posting GUI 379 GuiPlayerEngineEvent engineOn=<0|1>
#       GameBridgeWorldToGui.cpp, the engine on/off GUI event the HUD reveal is slaved to.
#   [motion] ... engine <n>   (MotionProbe, every 30 frames)
#
# SCENARIO (t = DRIVING + DriveDelay): no pedal for 8 s (the engine must stay OFF), gas 8-11 s
# (crank + run), brake 11-13 s (still demand, stays RUNNING), then nothing for 27 s (the car
# rolls to a stop, 15 s idle, STOPPING, OFF), then gas again at 40 s (it must crank again).
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case ignition_junkyard_exit
#
@{
  Name    = 'ignition_junkyard_exit'
  Area    = 'world'
  Bug     = 'b5-decomp #13 -- ignition always on after the junkyard exit'
  Frames  = $false
  Run     = @{
    Drive          = $true
    MotionProbe    = $true
    MaxSeconds     = 85
    SkipIntro      = $true      # the console -skipvideos latch
    AcceptGap      = 1.0        # harness pump latency, not a game gate
    Teleport       = '3040.7,-5.8,-1937.9,180'   # the road outside the junkyard exit
    ThrottleScript = '0:none,8:accel,11:brake,13:none,40:accel'
  }
  DiagEnv = ''
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'LogMatch';   Name = 'the [ignition] witness ran'; Pattern = '\[ignition\] tick state=' }

    @{ Kind = 'Script'; Name = 'engine OFF at the exit, cranked by the gas, idled off, cranked again'; Script = {
        param($ctx)

        $lines = $ctx.LogLines
        # The junkyard-exit attach: the LAST player attach off the car-select podium.
        $exit = -1
        for ($i = 0; $i -lt $lines.Count; $i++) {
          if ($lines[$i] -match '\[ignition\] attach slot \d+ type=0 .*inCarSelect=0 ') { $exit = $i }
        }
        if ($exit -lt 0) { return @{ Pass = $false; Detail = 'no junkyard-exit attach line (type=0 inCarSelect=0)' } }

        $fail = @(); $note = @()
        if ($lines[$exit] -match 'carInGameMode=(?<g>\d)') {
          if ($Matches.g -ne '0') { $fail += 'exit attach says carInGameMode=1 (free burn has no game mode: the engine is forced RUNNING)' }
        }

        # Every player engine-state change after the exit, with its pedals, and the engine field
        # of every [motion] sample (to prove the OFF stretch before the first gas is real time).
        $ticks = @(); $offSamples = 0; $firstStart = -1
        for ($i = $exit + 1; $i -lt $lines.Count; $i++) {
          $l = $lines[$i]
          if ($l -match '\[ignition\] tick state=(?<s>\d+) .*accel=(?<a>[-\d.eE+]+) brake=(?<b>[-\d.eE+]+)') {
            $ticks += ,@{ S = [int]$Matches.s; A = [double]::Parse($Matches.a, [Globalization.CultureInfo]::InvariantCulture);
                          B = [double]::Parse($Matches.b, [Globalization.CultureInfo]::InvariantCulture); I = $i }
            if ($firstStart -lt 0 -and [int]$Matches.s -ne 0) { $firstStart = $i }
          } elseif ($firstStart -lt 0 -and $l -match '\[motion\] .* engine (?<e>\d+)\s*$') {
            if ($Matches.e -eq '0') { $offSamples++ }
          }
        }
        $seq = ($ticks | ForEach-Object { $_.S }) -join ','
        $note += ('states after exit: ' + $seq)
        $note += ('OFF motion samples before the first crank: ' + $offSamples)

        if ($ticks.Count -eq 0) { return @{ Pass = $false; Detail = 'no [ignition] tick after the exit -- the engine state never changed' } }
        if ($ticks[0].S -ne 1) { $fail += ('first state after the exit is ' + $ticks[0].S + ', not STARTING (1): the engine did not start from OFF') }
        elseif ($ticks[0].A -le 0.05 -and $ticks[0].B -le 0.05) { $fail += 'the engine cranked with no pedal pressed' }
        if ($offSamples -lt 8) { $fail += ('only ' + $offSamples + ' OFF [motion] samples before the first crank (want >= 8, i.e. OFF while the pedals are idle)') }

        # The full cycle, in order: 1 -> 2 -> 3 -> 0 -> 1.
        $want = @(1, 2, 3, 0, 1); $k = 0
        foreach ($t in $ticks) { if ($k -lt $want.Count -and $t.S -eq $want[$k]) { $k++ } }
        if ($k -lt $want.Count) { $fail += ('cycle STARTING,RUNNING,STOPPING,OFF,STARTING reached only ' + $k + ' of 5 steps') }
        foreach ($t in $ticks) {
          if ($t.S -eq 3 -and ($t.A -gt 0.05 -or $t.B -gt 0.05)) { $fail += 'STOPPING entered with a pedal pressed' }
        }

        # The HUD follows: an engineOn=0 GUI event after the idle switch-off.
        $hudOff = $false; $hudOn = $false
        for ($i = $exit + 1; $i -lt $lines.Count; $i++) {
          if ($lines[$i] -match '\[hud-reveal\] posting GUI 379 .*engineOn=1') { $hudOn = $true }
          if ($hudOn -and $lines[$i] -match '\[hud-reveal\] posting GUI 379 .*engineOn=0') { $hudOff = $true }
        }
        if (-not $hudOn)  { $fail += 'no GUI 379 engineOn=1 after the exit' }
        if (-not $hudOff) { $fail += 'no GUI 379 engineOn=0 after the engine came on (the idle switch-off never reached the HUD)' }

        $detail = ($note -join '; ')
        if ($fail.Count -gt 0) { $detail = ($fail -join ' | ') + '  [' + $detail + ']' }
        return @{ Pass = ($fail.Count -eq 0); Detail = $detail }
      } }
  )
}
