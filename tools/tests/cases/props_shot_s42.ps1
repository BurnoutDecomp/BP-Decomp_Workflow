# props_shot_s42 -- BurnoutDecomp/b5-decomp#2, ONE STRIKE at 42 m/s (94 mph).
#
# ⭐ THIS IS THE "MEDIUM/HIGH SPEED" CELL THE REPORT NAMES, and it is one of six that make up a
# speed ladder. The other five are this file with the speed in CrashSweepShots (and the case
# Name) changed:
#     props_shot_s10  ...180:10    22 mph
#     props_shot_s18  ...180:18    40 mph   (just under the type-53 lamppost's 40 mph
#                                            mfMoveThreshold -- the lean/promote boundary)
#     props_shot_s26  ...180:26    58 mph
#     props_shot_s34  ...180:34    76 mph
#     props_shot_s42  ...180:42    94 mph   (this file)
#     props_shot_s50  ...180:50   112 mph
# Read them all with:  python tools/diagnostics/prop_strike_report.py --ladder
#
# ⛔⛔ ONE SHOT PER BOOT, AND THAT IS NOT AN EFFICIENCY CHOICE -- it is the same rule
# crash_sweep_batch.ps1 records for the CAR, for the same reason. Measured 2026-09-07 on the
# four-shot props_speed_ladder_A/B: props hit by shot k are still moving -- or falling out of
# the world at the 27 m/s clamp -- during shot k+1's window, so a per-shot segmentation of the
# log attributes their motion to the later shot. Boot B's 10 m/s cell scored a 33 m "flight"
# that belonged to a prop shot 0 had already launched.
#
# THE TARGET is the type-53 lamppost at (3052.7,-4.9,-2033.5) on the junkyard-exit road --
# mass 150 kg, mfMoveThreshold 40 mph, mu8JointType 1 (LEAN), muSceneUriId 428364, which is
# both an IsLamppost id and one of the two HACKShouldMoveComOffset ids (so GetPropInertia
# @0x82612640 substitutes K_LAMPOST_INERTIA_BOX == (2,1,2) for its volume box). Every field
# here is out of the shipped PROPPHYSICS.BUNDLE -- dump it with
# `python tools/diagnostics/prop_gazetteer.py`, which also diffs the ported table against the
# X360 original (0 differences across 219 types x 14 fields, measured 2026-09-07).
#
# The launch point is 25 m up-road, heading 180. RequestPlaceOnTrack seats the car AT the
# commanded speed, so the impact speed is an INPUT and not an emergent quantity, and the
# -CrashSweep recipe is bit-deterministic: every one of these six boots seated from the same
# `from (3007.971924, -2.540364, -1945.166992)`, so a REPEAT of a cell carries no information.
#
# WHAT THE LADDER MEASURED (2026-09-07, all six cells plus the control on ONE binary --
# exe mtime 18:25:16, sha256 70a6b836a98857bd; the exe hash was re-read before and after and
# did not move):
#     impact      d@1s   d@2s   rise@2s   whole-run   |vh|max
#     22 mph      1.07   1.60    0.00     29.44 *     13.66
#     40 mph      4.21   6.63    0.00     27.15 *     15.34
#     58 mph      3.90   4.63    1.06      4.91       21.81
#     76 mph      3.18   4.08    1.36      4.50       24.47
#     94 mph      2.79   3.60    1.26      3.60       27.00
#    112 mph      2.86   3.28    0.95      3.33       27.00
#   * the two long "whole-run" numbers are a BULLDOZE, not a launch: below ~58 mph the car does
#     not clear the prop and shunts it again and again down the road while the throttle is held
#     (18 m/s: z -2033 -> -2041 -> -2053 -> -2061 in four pushes, at rest between each, the
#     prop's own speed never above 15 m/s). Hence d@1s/d@2s.
#   ⇒ the launch DECREASES with impact speed from 58 mph up. The reported symptom -- worse at
#     medium/high speed -- is not reproduced on this build.
#
# THE CHECKS ARE THE CONSOLE'S OWN CONSTANTS, not thresholds picked to pass:
#   * 27.000 m/s is Inertia::mMaxVelocity. AddPropToSim @0x826274D8 stores flt_82F2A390 ==
#     KF_PROP_MAX_ANGULAR_VEL == 27.0 into the LINEAR clamp slot (record+0x88) and
#     flt_82F2A394 == 30.0 into the ANGULAR one -- the console's own cross-wiring, transcribed
#     not corrected (PropManager_wQ2_05.cpp). RigidBody::DynamicUpdate @0x82BC2B78 enforces it.
#   * 0.500 m/s is KVF_MAX_LINEAR_ACCELERATION (Splat(30.0f); dyn-init thunk 0x82C5E830) times
#     the sim's 1/60 s step. PropManager::ClampAcceleration @0x82627F00 rewrites any prop
#     velocity whose implied acceleration exceeds it. [Q6-clamp] prints prev v and out v on one
#     line, so the invariant is direct.
#
# NEGATIVE CONTROL -- props_shot_s42_noclamp.ps1 is this file with BRN_PROP_NOCLAMP=1 added.
# Same binary, same shot, same prop, same 263 sampled frames:
#       clamp ON   d@2s =  3.60 m   clamp bit 25/263   max|dv| =  0.500
#       NOCLAMP    d@2s = 35.26 m   clamp bit  0/263   max|dv| = 27.000
# Run it whenever you doubt a green here: a check nobody has seen FAIL is not a check.
#
@{
  Name    = 'props_shot_s42'
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
    CrashSweepShots  = '3052.7/-4.9/-2008.5/180:42'
    CrashSweepSettle = 600
  }
  DiagEnv = 'BRN_PROP_DIAG=1'
  Checks  = @(
    @{ Kind = 'Mark';     Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'LogCount'; Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'LogCount'; Name = 'the shot landed (props were updated by the sim)'; Pattern = '\[Q6-world\] whole prop'; Min = 1 }

    # (1) the console's per-frame ceiling on a STORED prop velocity: 30 m/s^2 * 1/60 s.
    @{ Kind = 'Script'; Name = 'per-frame |dv| <= KVF_MAX_LINEAR_ACCELERATION*dt (0.500 m/s)'; Script = {
        param($ctx)
        $rx = [regex]'\[Q6-clamp\] prop (?<id>\d+).*?prev v=\((?<px>[-\d.eE+]+),(?<py>[-\d.eE+]+),(?<pz>[-\d.eE+]+)\) out v=\((?<ox>[-\d.eE+]+),(?<oy>[-\d.eE+]+),(?<oz>[-\d.eE+]+)\)'
        $worst = -1.0; $n = 0; $worstLine = ''
        foreach ($l in $ctx.LogLines) {
          $m = $rx.Match($l); if (-not $m.Success) { continue }
          $n++
          $dv = [Math]::Sqrt(
            [Math]::Pow([double]$m.Groups['ox'].Value - [double]$m.Groups['px'].Value, 2) +
            [Math]::Pow([double]$m.Groups['oy'].Value - [double]$m.Groups['py'].Value, 2) +
            [Math]::Pow([double]$m.Groups['oz'].Value - [double]$m.Groups['pz'].Value, 2))
          if ($dv -gt $worst) { $worst = $dv; $worstLine = $l.Trim() }
        }
        if ($n -eq 0) { return @{ Pass = $false; Detail = 'no [Q6-clamp] lines -- the shot missed, or BRN_PROP_DIAG is off' } }
        # 0.500 exactly, +10% for the float round trip through the log.
        return @{ Pass = ($worst -le 0.55); Detail = ("samples={0} max|dv|={1:f3} m/s limit=0.550  worst: {2}" -f $n, $worst, $worstLine) }
      } }

    # (2) no prop may exceed Inertia::mMaxVelocity. This is a CEILING the console enforces, so
    #     exceeding it is a defect in the integrator, not a tuning question.
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

    # (3) THE REPORT ITSELF, measured in a WINDOW so a bulldoze is not counted as a launch:
    #     how far the struck prop travels HORIZONTALLY in the 2 s after it first moves.
    #     Bound 12 m: measured 3.60 m here and 35.26 m with the clamp disabled, so it
    #     separates the two regimes with a wide margin either side.
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
          $n = [Math]::Min($s.Count - 1, $i0 + 120)   # 2 s at the sim's 60 Hz
          for ($j = $i0; $j -le $n; $j++) {
            $d = [Math]::Sqrt([Math]::Pow($s[$j][0]-$p0[0],2) + [Math]::Pow($s[$j][2]-$p0[2],2))
            if ($d -gt $worst) { $worst = $d; $worstId = $id }
          }
        }
        return @{ Pass = ($worst -le 12.0); Detail = ("props={0} max 2 s horizontal launch={1:f2} m (prop {2}) limit=12.00" -f $seq.Count, $worst, $worstId) }
      } }
  )
}
