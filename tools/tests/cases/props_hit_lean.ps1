# props_hit_lean -- BurnoutDecomp/b5-decomp#2, the MOVE-THRESHOLD half of the report.
#
# WHY A SECOND CASE. The sibling props_hit_speed hits type-6 and type-24 props, whose
# mfMoveThreshold is 0.0 -- they are free physical bodies at ANY speed, so they cannot show the
# "fine when slow, silly when fast" split the report describes, and on the 2026-09-06 build they
# do not fly (max displacement 3.6 m, and PropManager::ClampAcceleration saturates at exactly its
# console ceiling every frame). The props that CAN show the split are the ones with a real move
# threshold: below it the contact is resolved directly on their joint (E_LEANING, lean/tilt);
# above it the prop is promoted to a free E_PHYSICAL body.
#
# THE PROPS AND THE AIM, from the shipped data (scratch\bugtest\props\gazetteer.py, which joins
# PROPS\PROPPHYSICS.BUNDLE's PropTypeData table to every ported TRK_UNIT*_GR.BNDL PropZoneData
# instance record). A row of type-53 props -- mass 150, moveThreshold 40 mph, jointType 1 (LEAN),
# sceneUri 428364, which PropTypeData::IsLamppost @0x822A1A00 counts as a lamppost -- runs down
# the junkyard-exit road:
#     (3052.7,-4.9,-2033.5) (3051.6,-5.0,-2064.9) (3050.3,-5.0,-2087.7) (3046.0,-4.9,-2108.1)
#     (3027.0,-4.9,-2139.5)
# Driving the road with -Teleport misses them (they are at the kerb, and run 20260906_100518
# collected only mid-road type-6/24 props), so this case uses the CRASH SWEEP instead: each shot
# is one console RequestPlaceOnTrack(pos, dir, SPEED), so the impact POINT, ANGLE and SPEED are
# inputs rather than emergent, and the cadence is counted in sim frames. Shot 0 is deliberately
# below the 40 mph threshold (8 m/s == 17.9 mph -> the prop must LEAN); shots 1..4 are well above
# it (35 m/s == 78 mph -> the prop is promoted to a free body).
#
# CHECKS -- the same two numbers as the sibling, and the same console grounding:
#  (1) PropManager::ClampAcceleration @0x82627F00 rewrites a prop's new linear velocity whenever
#      the implied acceleration exceeds KVF_MAX_LINEAR_ACCELERATION (Splat(30.0f); dyn-init thunk
#      0x82C5E830 -> rodata flt_82004F5C == 0x41F00000) and re-posts the corrected body, so the
#      velocity stored back into a PropInstance can move by at most 30 m/s^2 * dt = 0.5 m/s per
#      physics frame (dt = 1/60, BrnPhysicsModule.cpp:370 mfTimeStep = 0.016666668f).
#      [Q6-clamp] prints `prev v=` and `out v=` on one line, so the invariant is direct.
#  (2) how far a whole prop travels from where it was first published, off [Q6-world]. The 10 m
#      bound is the measured one: with the clamp live the same chain moved a prop 3.4-3.6 m
#      (scratch\flow_run\propfix_frames, scratch\bugtest\runs\props_hit_speed\20260906_100518),
#      and with the clamp disabled (BRN_PROP_NOCLAMP=1, scratch\flow_run\propfix_noclamp) 30.0 m.
#
# ⚠️⚠️ THIS CASE IS NOT YET DETERMINISTIC -- 1 RED IN 3 RUNS, 2026-09-06. Measured:
#     20260906_101608 (exe 10:04:52)  FAIL  maxDisplacement 49.80 m  -- prop 54661120 launched
#                                            16 m into the air and 45 m sideways; the RED
#     20260906_104858 (exe 10:48:47)  PASS  maxDisplacement  6.06 m, 16 props
#     20260906_110453 (exe 10:48:47)  PASS  maxDisplacement  6.06 m,  5 props
#   The two PASS runs share an exe, so an exe difference is not excluded, but the more likely
#   cause is the SHOT itself: RequestPlaceOnTrack snaps the launch point to the road, so which
#   kerbside prop the car actually reaches -- and whether it comes to REST against one, which is
#   what sustains the ejection (see the mechanism note below) -- varies run to run. The 101608
#   run collected 6 props, 104858 collected 16 including props 200 m away at x~2819.
#   ⇒ BEFORE USING THIS AS A GREEN GATE, make the shot land: aim from a point whose snapped
#   position is known (read [sweep] in the run's log), or add shots until a hit is certain.
#
# WHAT THE RED RUN SHOWED, and it is NOT the velocity channel: ClampAcceleration's ceiling held
# at exactly 0.500 m/s on every one of the 4,261 samples, yet the prop still travelled 49.8 m.
# A prop's position is advanced by DynamicUpdate as `mVel*dt + lpAccum[0]`, where lpAccum[0] is
# the solver's DIRECT position correction; on run 20260906_104858 a part moved 0.43 m per frame
# (26 m/s) while its clamped mVel was 1-2 m/s, i.e. >95% of the displacement comes through the
# position channel, which the console's acceleration clamp neither sees nor limits.
#
# RED:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case props_hit_lean -ExpectFail -Label pre-fix
# GREEN: powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case props_hit_lean -Label post-fix
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
#   FLOOR: five CrashSweep shots at 300 sim frames (5 s) of settle each is 25 s of sweep after
#   the arm, on top of boot(16) + DriveDelay(6).
#
@{
  Name    = 'props_hit_lean'
  Area    = 'physics'
  Bug     = 'BurnoutDecomp/b5-decomp#2 -- props are sent flying way too much when hit at medium/high speed'
  Frames  = $false
  Run     = @{
    Drive            = $true
    MotionProbe      = $true
    MaxSeconds       = 60
    SkipIntro       = $true      # the console -skipvideos latch (see the banner)
    AcceptGap       = 1.0        # harness pump latency, not a game gate
    # base launch point (per-shot points override it below); heading 180 == down -Z
    CrashSweep       = '3052.7,-4.9,-2008.5'
    #        x /  y  /   z   /hdg:speed  -- 25 m of run-in to each prop, aimed straight at it
    CrashSweepShots  = '3052.7/-4.9/-2008.5/180:8,3052.7/-4.9/-2008.5/180:35,3051.6/-5.0/-2039.9/180:35,3050.3/-5.0/-2062.7/180:35,3046.0/-4.9/-2083.1/180:35'
    CrashSweepSettle = 300     # 5 s between shots: long enough to watch a hit prop's whole arc
  }
  DiagEnv = 'BRN_PROP_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'LogCount'; Name = 'props were actually updated by the sim'; Pattern = '\[Q6-world\] whole prop'; Min = 1 }

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
        if ($n -eq 0) { return @{ Pass = $false; Detail = 'no [Q6-clamp] lines -- no whole prop was updated (every shot missed, or BRN_PROP_DIAG off)' } }
        $limit = 0.55
        return @{ Pass = ($worst -le $limit); Detail = ("samples={0} max|dv|={1:f2} m/s limit={2:f2}  worst: {3}" -f $n, $worst, $limit, $worstLine) }
      } }

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
        return @{ Pass = ($worst -le 10.0); Detail = ("samples={0} props={1} maxDisplacement={2:f2} m (prop {3}) maxRaw|linVel|={4:f2} m/s" -f $n, $first.Count, $worst, $worstId, $maxV) }
      } }
  )
}
