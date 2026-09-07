# props_shot_s42_noclamp -- THE NEGATIVE CONTROL for props_shot_s42, and nothing else.
#
# ⛔ THIS CASE IS EXPECTED TO **FAIL**. Run it with -ExpectFail:
#     powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case props_shot_s42_noclamp -ExpectFail
#
# WHY IT EXISTS. props_shot_s42's whole claim is that a prop hit at 94 mph travels ~3.6 m in
# the two seconds after the strike because PropManager::ClampAcceleration @0x82627F00 is live
# and biting at exactly the console's KVF_MAX_LINEAR_ACCELERATION * dt == 30 * 1/60 == 0.500
# m/s per frame. A check nobody has seen FAIL is not a check, so this is the same scenario with
# the clamp switched off through the game's own opt-in experiment knob (BRN_PROP_NOCLAMP=1,
# PropManager_wQ2_01.cpp -- an early return at the top of ClampAcceleration, inert unless the
# variable is set).
#
# MEASURED 2026-09-07 -- SAME BINARY (exe mtime 18:25:16, sha256 70a6b836a98857bd), same shot,
# same prop 54683648, same 263 sampled frames:
#       clamp ON   d@2s =  3.60 m   clamp bit 25/263   max|dv| =  0.500 m/s
#       NOCLAMP    d@2s = 35.26 m   clamp bit  0/263   max|dv| = 27.000 m/s
# and two more props in the same boot went 29.20 m and 18.31 m against 3.63 m and 1.14 m.
# So the instrument separates the two regimes by ~10x, and 35 m IS what "sent flying way too
# much" looks like -- which is exactly what the console's clamp is preventing.
#
# ⚠️ The mMaxVelocity check still PASSES here (27.0 m/s is enforced in
# RigidBody::DynamicUpdate, not in ClampAcceleration) -- that is correct and is itself
# informative: the two ceilings are independent, and only the acceleration one is disabled.
#
@{
  Name    = 'props_shot_s42_noclamp'
  Area    = 'physics'
  Bug     = 'BurnoutDecomp/b5-decomp#2 -- NEGATIVE CONTROL for props_shot_s42 (expected to FAIL)'
  Frames  = $false
  Run     = @{
    Drive            = $true
    MotionProbe      = $true
    MaxSeconds       = 50
    SkipIntro        = $true
    AcceptGap        = 1.0
    CrashSweep       = '3052.7,-4.9,-2008.5'
    CrashSweepShots  = '3052.7/-4.9/-2008.5/180:42'
    CrashSweepSettle = 600
  }
  DiagEnv = 'BRN_PROP_DIAG=1 BRN_PROP_NOCLAMP=1'
  Checks  = @(
    @{ Kind = 'Mark';     Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'LogCount'; Name = 'the shot landed (props were updated by the sim)'; Pattern = '\[Q6-world\] whole prop'; Min = 1 }

    # The two checks props_shot_s42 makes, verbatim, so the control bites on the SAME
    # arithmetic the real case passes on.
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
        if ($n -eq 0) { return @{ Pass = $false; Detail = 'no [Q6-clamp] lines' } }
        return @{ Pass = ($worst -le 0.55); Detail = ("samples={0} max|dv|={1:f3} m/s limit=0.550" -f $n, $worst) }
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
