# props_shot_s18 -- BurnoutDecomp/b5-decomp#2, ONE STRIKE at 18 m/s (40 mph).
#
# The LOW end of the props_shot_s42 speed ladder (that file's banner has the whole ladder, the
# recipe, the console constants and the negative control). This cell is kept as a case of its
# own because it is the one that CONTRADICTS the report: 40 mph is the worst launch of the six
# speeds measured, not the mildest.
#
#     impact      d@1s   d@2s   rise@2s   whole-run
#      22 mph     1.07   1.60    0.00     29.44 (bulldoze)
#      40 mph     4.21   6.63    0.00     27.15 (bulldoze)   <- THIS CELL
#      58 mph     3.90   4.63    1.06      4.91
#      76 mph     3.18   4.08    1.36      4.50
#      94 mph     2.79   3.60    1.26      3.60
#     112 mph     2.86   3.28    0.95      3.33
#
# 40 mph is also the type-53 lamppost's own mfMoveThreshold (read out of PROPPHYSICS.BUNDLE by
# tools/diagnostics/prop_gazetteer.py), i.e. the lean/promote boundary -- which is why the cell
# sits where it does. Below it the prop resolves on its joint; at and above it the prop is
# promoted to a free E_PHYSICAL body.
#
# ⚠️ THE 27 m "whole-run" NUMBER IS A BULLDOZE, NOT A LAUNCH. With the throttle held for ~25 s
# after the shot the car never clears the prop and shunts it down the road again and again
# (z -2033 -> -2041 -> -2053 -> -2061, four separate pushes with the prop at rest between each,
# its own speed never above 15 m/s). That is why the check below is a 2 s WINDOW from the
# moment the prop first moves, and why "max displacement over the run" is the wrong metric.
#
@{
  Name    = 'props_shot_s18'
  Area    = 'physics'
  Bug     = 'BurnoutDecomp/b5-decomp#2 -- props are sent flying way too much when hit at medium/high speed'
  Frames  = $false
  Run     = @{
    Drive            = $true
    MotionProbe      = $true
    MaxSeconds       = 50
    SkipIntro        = $true
    AcceptGap        = 1.0
    CrashSweep       = '3052.7,-4.9,-2008.5'
    CrashSweepShots  = '3052.7/-4.9/-2008.5/180:18'
    CrashSweepSettle = 600
  }
  DiagEnv = 'BRN_PROP_DIAG=1'
  Checks  = @(
    @{ Kind = 'Mark';     Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'LogCount'; Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'LogCount'; Name = 'the shot landed (props were updated by the sim)'; Pattern = '\[Q6-world\] whole prop'; Min = 1 }

    @{ Kind = 'Script'; Name = 'per-frame |dv| <= KVF_MAX_LINEAR_ACCELERATION*dt (0.500 m/s)'; Script = {
        param($ctx)
        $rx = [regex]'\[Q6-clamp\] prop (?<id>\d+).*?prev v=\((?<px>[-\d.eE+]+),(?<py>[-\d.eE+]+),(?<pz>[-\d.eE+]+)\) out v=\((?<ox>[-\d.eE+]+),(?<oy>[-\d.eE+]+),(?<oz>[-\d.eE+]+)\)'
        $worst = -1.0; $n = 0
        foreach ($l in $ctx.LogLines) {
          $m = $rx.Match($l); if (-not $m.Success) { continue }
          $n++
          $dv = [Math]::Sqrt(
            [Math]::Pow([double]$m.Groups['ox'].Value - [double]$m.Groups['px'].Value, 2) +
            [Math]::Pow([double]$m.Groups['oy'].Value - [double]$m.Groups['py'].Value, 2) +
            [Math]::Pow([double]$m.Groups['oz'].Value - [double]$m.Groups['pz'].Value, 2))
          if ($dv -gt $worst) { $worst = $dv }
        }
        if ($n -eq 0) { return @{ Pass = $false; Detail = 'no [Q6-clamp] lines -- the shot missed, or BRN_PROP_DIAG is off' } }
        return @{ Pass = ($worst -le 0.55); Detail = ("samples={0} max|dv|={1:f3} m/s limit=0.550" -f $n, $worst) }
      } }

    @{ Kind = 'Script'; Name = 'no prop exceeds mMaxVelocity (27.0 m/s)'; Script = {
        param($ctx)
        $rx = [regex]'\[Q6-world\] whole prop (?<id>\d+) pos \([^)]*\) \|linVel\|=(?<v>[-\d.eE+]+)'
        $worst = -1.0; $n = 0
        foreach ($l in $ctx.LogLines) {
          $m = $rx.Match($l); if (-not $m.Success) { continue }
          $n++; $v = [double]$m.Groups['v'].Value
          if ($v -gt $worst) { $worst = $v }
        }
        if ($n -eq 0) { return @{ Pass = $false; Detail = 'no [Q6-world] whole-prop lines' } }
        return @{ Pass = ($worst -le 27.05); Detail = ("samples={0} max|linVel|={1:f3} m/s ceiling=27.000" -f $n, $worst) }
      } }

    @{ Kind = 'Script'; Name = 'launch (horizontal displacement in the first 2 s) <= 12 m'; Script = {
        param($ctx)
        $rx = [regex]'\[Q6-world\] whole prop (?<id>\d+) pos \((?<x>[-\d.eE+]+), (?<y>[-\d.eE+]+), (?<z>[-\d.eE+]+)\) \|linVel\|=(?<v>[-\d.eE+]+)'
        $seq = @{}
        foreach ($l in $ctx.LogLines) {
          $m = $rx.Match($l); if (-not $m.Success) { continue }
          $id = $m.Groups['id'].Value
          if (-not $seq.ContainsKey($id)) { $seq[$id] = New-Object System.Collections.ArrayList }
          [void]$seq[$id].Add(@([double]$m.Groups['x'].Value, [double]$m.Groups['y'].Value,
                                [double]$m.Groups['z'].Value, [double]$m.Groups['v'].Value))
        }
        if ($seq.Count -eq 0) { return @{ Pass = $false; Detail = 'no [Q6-world] whole-prop lines' } }
        $worst = 0.0; $worstId = ''
        foreach ($id in $seq.Keys) {
          $s = $seq[$id]
          $i0 = -1
          for ($i = 0; $i -lt $s.Count; $i++) { if ($s[$i][3] -gt 0.05) { $i0 = $i; break } }
          if ($i0 -lt 0) { continue }
          $p0 = $s[$i0]
          $n = [Math]::Min($s.Count - 1, $i0 + 120)
          for ($j = $i0; $j -le $n; $j++) {
            $d = [Math]::Sqrt([Math]::Pow($s[$j][0]-$p0[0],2) + [Math]::Pow($s[$j][2]-$p0[2],2))
            if ($d -gt $worst) { $worst = $d; $worstId = $id }
          }
        }
        return @{ Pass = ($worst -le 12.0); Detail = ("props={0} max 2 s horizontal launch={1:f2} m (prop {2}) limit=12.00" -f $seq.Count, $worst, $worstId) }
      } }
  )
}
