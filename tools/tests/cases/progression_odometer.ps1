# progression_odometer -- BurnoutDecomp/b5-decomp#10: "miles driven not recorded when driving".
# The HUD odometer stayed at 0.0 km however far the player drove.
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case progression_odometer
#
# THE CHAIN (console): ProgressionManager::PreWorldUpdate @0x823A4F68 integrates the player's
# RaceCarState::mfSpeedMPH * 0.44704 * simStep every frame through AddDistanceDriven @0x823668F0
# into Profile::mfDistanceDrivenOffline/Online, the per-car-type tally and the current
# LiveryData::mfDistanceDriven; GameStateModule::CopyScoringDataToOutput publishes the livery float
# as ScoringOutputInterface::mfDistanceDrivenInCurrentCar; the GUI bridge carries it in
# GuiEventCurrentStatus (492) to GuiCache::mfDistanceDriven; OdometerComponent::Update formats it.
#
# WITNESSES (both opt-in via BRN_ODOMETER_DIAG, both bounded):
#   [odometer] hud=<m>                       OdometerComponent::Update -- the formatted number
#   [odometer] car=<m> offline=<m> online=<m> incar=<s> real=<s>
#                                            ProgressionManager::PreWorldUpdate -- the producer
#
# RED (before the fix): hud=0 for the whole drive.  GREEN: hud climbs with the distance actually
# driven (the harness' own [motion] samples, integrated as a polyline, are the yardstick).
@{
  Name    = 'progression_odometer'
  Area    = 'progression'
  Bug     = 'BurnoutDecomp/b5-decomp#10 -- miles driven not recorded when driving'
  Frames  = $false
  Run     = @{
    Drive       = $true
    MotionProbe = $true            # marks.txt DRIVE line carries path=<m> -- the yardstick
    MaxSeconds  = 55
    SkipIntro   = $true
    AcceptGap   = 1.0
    Teleport    = '3040.7,-5.8,-1937.9,180'   # the road outside the junkyard exit (baseline's)
  }
  DiagEnv = 'BRN_ODOMETER_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions';  Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }
    # THE BUG: the HUD number must move. A car that drove > 20 m (the baseline's own bar) with the
    # readout still at 0 is exactly issue #10.
    @{ Kind = 'LogValue';   Name = 'HUD odometer moved (last hud= >= 50 m)'
       Pattern = '\[odometer\] hud=(?<m>[\d.]+)'; Group = 'm'; Agg = 'last'; Min = 50 }
    # The producer side: the livery's distance and the profile's offline tally both climb.
    @{ Kind = 'LogValue';   Name = 'livery distance climbs (last car= >= 50 m)'
       Pattern = '\[odometer\] car=(?<m>[\d.]+)'; Group = 'm'; Agg = 'last'; Min = 50 }
    @{ Kind = 'LogValue';   Name = 'profile offline distance climbs (last offline= >= 50 m)'
       Pattern = '\[odometer\] car=[\d.]+ offline=(?<m>[\d.]+)'; Group = 'm'; Agg = 'last'; Min = 50 }
    # THE YARDSTICK: integrate the harness' own [motion] samples (10 Hz positions) into a polyline,
    # skipping any >20 m step (a reset-on-track / teleport placement, not driving), and compare with
    # the odometer. NOT marks.txt's DRIVE path= -- that figure is measured only AFTER the last
    # placement jump (a post-crash reset truncated it to 175 m of a 586 m drive on the first GREEN
    # run, ratio 3.4, while the whole-run polyline agreed with the odometer to 0.3%).
    # mfSpeedMPH * 0.44704 * simStep against a 10 Hz position polyline: 0.8x..1.25x.
    @{ Kind = 'Script';     Name = 'distance booked THIS RUN agrees with the whole-run motion polyline (0.8x..1.25x)'; Script = {
        param($ctx)
        $path = 0.0; $n = 0; $jumps = 0; $px = $null
        foreach ($line in $ctx.LogLines) {
          if ($line -match '\[motion\] n \d+ pos (?<x>-?[\d.]+) (?<y>-?[\d.]+) (?<z>-?[\d.]+) ') {
            $x = [double]$Matches.x; $y = [double]$Matches.y; $z = [double]$Matches.z
            if ($null -ne $px) {
              $d = [math]::Sqrt(($x-$px)*($x-$px) + ($y-$py)*($y-$py) + ($z-$pz)*($z-$pz))
              if ($d -lt 20) { $path += $d } else { $jumps++ }
            }
            $px = $x; $py = $y; $pz = $z; $n++
          }
        }
        # THE RUN'S DELTA, not the absolute: LiveryData::mfDistanceDriven PERSISTS in the save, so a
        # returning profile starts this run at last session's total (107 m on the run that first
        # tripped this check: hud 536 m vs a 405 m polyline; the per-second increments matched the
        # probe integral to 1 m). first car= .. last car= is what THIS run booked.
        $first = $null; $last = $null
        foreach ($line in $ctx.LogLines) {
          if ($line -match '\[odometer\] car=(?<m>[\d.]+)') { $v = [double]$Matches.m; if ($null -eq $first) { $first = $v }; $last = $v }
        }
        if ($null -eq $last) { return @{ Pass = $false; Detail = 'no [odometer] car= line' } }
        $booked = $last - $first
        if ($n -lt 2 -or $path -lt 20) { return @{ Pass = $false; Detail = ("car barely moved: polyline={0:N1}m over {1} samples" -f $path, $n) } }
        $ratio = $booked / $path
        return @{ Pass = ($ratio -ge 0.8 -and $ratio -le 1.25)
                  Detail = ("booked={0:N1}m (car {1:N1} -> {2:N1}) polyline={3:N1}m over {4} samples ({5} placement jumps skipped) ratio={6:N3}" -f $booked, $first, $last, $path, $n, $jumps, $ratio) }
      } }
  )
}
