# props_hit_speed -- BurnoutDecomp/b5-decomp#2 "props are sent flying way too much when hit at
# medium/high speed".
#
# THE SCENARIO. Teleport onto the straight at (2995, 1.5, -1750) facing +Z and hold the throttle.
# 200 m of run-up puts the car at ~35-40 m/s when it reaches the physical prop cluster around
# (2988..3002, 1.4, -1548.6) -- the same head-on shot the 2026-09-02 props-at-speed session used,
# recorded in memory\project_bp_props_at_speed_fix.md.
#
# WHAT IS CHECKED, AND WHY THOSE NUMBERS ARE THE CONSOLE'S.
#  (1) THE PER-FRAME VELOCITY-CHANGE CEILING. PropManager::ClampAcceleration @0x82627F00 rewrites
#      a prop's new linear velocity whenever the implied acceleration exceeds
#      KVF_MAX_LINEAR_ACCELERATION (Splat(30.0f); dyn-init thunk 0x82C5E830, rodata flt_82004F5C)
#      and re-posts the corrected body to the simulation. So the velocity the console stores back
#      into a PropInstance can move by at most  30 m/s^2 * dt  in one physics frame -- 0.5 m/s at
#      the sim's 1/60 s step (BrnPhysicsModule.cpp:370 mfTimeStep = 0.016666668f). The witness
#      [Q6-clamp] prints `prev v=` (the stored value) and `out v=` (what is stored after the
#      clamp) on the same line, so the invariant is directly measurable. Bound = 30*dt + 10%.
#  (2) WHAT THE REPORTER SEES: how far a whole prop travels from where it was first published.
#      [Q6-world] prints the prop's world position every frame it is updated. THE 10 m BOUND IS
#      MEASURED, not picked: the 2026-09-02 props-at-speed session drove this exact shot with the
#      clamp live and the furthest whole prop moved 3.4 m
#      (scratch\flow_run\propfix_frames\BrnGame.log, prop 52923392: 2991.7,1.40,-1548.7 ->
#      2995.0,1.04,-1548.0, then it settles); the same shot with the clamp DISABLED
#      (BRN_PROP_NOCLAMP=1, scratch\flow_run\propfix_noclamp\BrnGame.log) moved a prop 30.0 m.
#      10 m is 3x the clamped baseline and a third of the unclamped one, so it separates the two
#      regimes with a wide margin either side.
#  (3) the usual: no NEW assert family, no exceptions, the run actually reached DRIVING.
#
# Both witnesses are opt-in behind BRN_PROP_DIAG and are first-N budgeted in the game code
# (PropManager_wQ2_01.cpp / PropEntityModule_wQ_06.cpp) -- no unbounded per-frame logging.
#
# RED:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case props_hit_speed -ExpectFail -Label pre-fix
# GREEN: powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case props_hit_speed -Label post-fix
#
# ⭐⭐ SHORTENED 2026-09-06 (lane harness2). WHAT CHANGED AND WHAT DID NOT.
#   The Run block below now carries `SkipIntro` and `AcceptGap`, and a smaller `MaxSeconds`.
#   Nothing else about the scenario moved and NO CHECK was touched.
#     SkipIntro  passes the CONSOLE's own "-skipvideos" command-line latch (BrnMain.cpp:434 ->
#                BootVideos::Update's soft-reboot exit) so the EA-Franchise and Criterion VP6
#                logos are not played. It is not a harness bypass and it is not new game code.
#     AcceptGap  is HARNESS latency, not a game gate: the Accept pump used to press every 3.0 s
#                at car select, and the junkyard leg of a returning boot was measurably two
#                consecutive pump periods long (carsel 16.5s -> livery 19.9s -> accept 23.0s).
#   MEASURED, same build, same scenario: boot-to-DRIVING 23.0 s -> 16.2 s.
#   MaxSeconds is cut by that saving plus the slack this case's own schedule shows it never used.
#
@{
  Name    = 'props_hit_speed'
  Area    = 'physics'
  Bug     = 'BurnoutDecomp/b5-decomp#2 -- props are sent flying way too much when hit at medium/high speed'
  Frames  = $false
  Run     = @{
    Drive          = $true
    MotionProbe    = $true
    MaxSeconds     = 60
    SkipIntro     = $true      # the console -skipvideos latch (see the banner)
    AcceptGap     = 1.0        # harness pump latency, not a game gate
    Teleport       = '2995,1.5,-1750,0'    # 200 m of run-up, facing the type-24 prop cluster
    ThrottleScript = '0:accel'
  }
  DiagEnv = 'BRN_PROP_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }

    # (0) the case is worthless if the shot missed: at least one whole-prop update must exist.
    @{ Kind = 'LogCount'; Name = 'props were actually updated by the sim'; Pattern = '\[Q6-world\] whole prop'; Min = 1 }

    # (1) the console's own per-frame ceiling on a stored prop velocity.
    @{ Kind = 'Script'; Name = 'per-frame |dv| <= KVF_MAX_LINEAR_ACCELERATION*dt'; Script = {
        param($ctx)
        $rx = [regex]'\[Q6-clamp\] prop (?<id>\d+).*?prev v=\((?<px>[-\d.eE+]+),(?<py>[-\d.eE+]+),(?<pz>[-\d.eE+]+)\) out v=\((?<ox>[-\d.eE+]+),(?<oy>[-\d.eE+]+),(?<oz>[-\d.eE+]+)\) dt=(?<dt>[-\d.eE+]+)'
        $worst = -1.0; $worstLine = ''; $n = 0
        foreach ($l in $ctx.LogLines) {
          $m = $rx.Match($l)
          if (-not $m.Success) { continue }
          $n++
          $dv = [Math]::Sqrt(
            [Math]::Pow([double]$m.Groups['ox'].Value - [double]$m.Groups['px'].Value, 2) +
            [Math]::Pow([double]$m.Groups['oy'].Value - [double]$m.Groups['py'].Value, 2) +
            [Math]::Pow([double]$m.Groups['oz'].Value - [double]$m.Groups['pz'].Value, 2))
          if ($dv -gt $worst) { $worst = $dv; $worstLine = $l.Trim() }
        }
        if ($n -eq 0) { return @{ Pass = $false; Detail = 'no [Q6-clamp] lines -- no whole prop was updated (shot missed, or BRN_PROP_DIAG off)' } }
        # 30 m/s^2 * (1/60) s = 0.5 m/s; +10% for the float round trip through the log.
        $limit = 0.55
        $ok = ($worst -le $limit)
        return @{ Pass = $ok; Detail = ("samples={0} max|dv|={1:f2} m/s limit={2:f2}  worst: {3}" -f $n, $worst, $limit, $worstLine) }
      } }

    # (2) how far a whole prop actually travels once it has been hit.
    @{ Kind = 'Script'; Name = 'prop displacement from first published pose <= 10 m'; Script = {
        param($ctx)
        $rx = [regex]'\[Q6-world\] whole prop (?<id>\d+) pos \((?<x>[-\d.eE+]+), (?<y>[-\d.eE+]+), (?<z>[-\d.eE+]+)\) \|linVel\|=(?<v>[-\d.eE+]+)'
        $first = @{}; $worst = -1.0; $worstId = ''; $maxV = -1.0; $n = 0
        foreach ($l in $ctx.LogLines) {
          $m = $rx.Match($l)
          if (-not $m.Success) { continue }
          $n++
          $id = $m.Groups['id'].Value
          $p = @([double]$m.Groups['x'].Value, [double]$m.Groups['y'].Value, [double]$m.Groups['z'].Value)
          $v = [double]$m.Groups['v'].Value
          if ($v -gt $maxV) { $maxV = $v }
          if (-not $first.ContainsKey($id)) { $first[$id] = $p; continue }
          $f = $first[$id]
          $d = [Math]::Sqrt([Math]::Pow($p[0]-$f[0],2) + [Math]::Pow($p[1]-$f[1],2) + [Math]::Pow($p[2]-$f[2],2))
          if ($d -gt $worst) { $worst = $d; $worstId = $id }
        }
        if ($n -eq 0) { return @{ Pass = $false; Detail = 'no [Q6-world] whole-prop lines' } }
        $ok = ($worst -le 10.0)
        return @{ Pass = $ok; Detail = ("samples={0} props={1} maxDisplacement={2:f2} m (prop {3}) maxRaw|linVel|={4:f2} m/s" -f $n, $first.Count, $worst, $worstId, $maxV) }
      } }
  )
}
