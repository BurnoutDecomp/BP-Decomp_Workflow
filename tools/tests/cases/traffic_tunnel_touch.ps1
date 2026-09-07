# traffic_tunnel_touch -- issue #14: "traffic: Cars simply disappear when we touch them with the
# player car" (Adriwin06), "seems to happen consistently when being in the tunnel of the highway".
#
# SCENARIO: the east I-88 tunnel. TRIGGERS.DAT carries it as the Tunnel generic regions 421647 /
# 605440 / 421642 / 421638 / 421636 (x 3013..3042, y ~ -8, z -1218..+274, two 11 m carriageways at
# x ~ 3013 and x ~ 3042). Teleport onto the west carriageway near the south portal, throttle pinned,
# and drive the tunnel end to end: the lane traffic ahead is what the player touches.
#
# WHAT IT WAS (2026-09-07, RED runs 20260907_112818 / _113833 / _114701): the cars are not removed.
# A traffic car promoted to a physics body inside the tunnel rose 10-11 m in ONE physics step, with
# no vertical velocity, onto the surface street above the tunnel, and stayed there -- re-lifted to
# the same plane every frame. The [T-ystep] stage probe (BRN_TRAFFIC_DIAG,
# BrnPhysicsModuleUpdateFunctions.cpp) put the step between "readbodies" and "postsim", i.e. in
# VehiclePhysics::UpdateSuspensionPostSimulation, which seats the body on its wheels' road
# contacts. Those contacts were STALE: PhysicalTrafficManager::ResetAboveGroundTestResults, the
# per-frame clear of every traffic wheel's RoadContact + down-ray latch, was a parked no-op, so a
# body created into a pooled slot inherited the previous occupant's contact plane (in the tunnel,
# the surface street where that car had lived). Fixed in b5-decomp by landing the reset.
#
# ORACLES. Two, independent of the fix:
#   * [traffic-track] (BRN_TRAFFIC_TRACK, traffic_track_lane.ps1): a vehicle's y must not move more
#     than 2 m between two 0.5 s samples in the same state (4 m across a state change), and no
#     removal may happen inside the console's 150 m clearup radius / 80 m in front of the player.
#   * [T-ystep] (BRN_TRAFFIC_DIAG): no physics stage may move a live traffic body more than 2 m in
#     one step. The slot-reuse snap at "postscene-end" (a create, not a move) is exempt.
# The traffic_track_lane "no vehicle > 4 m above the player" check is deliberately NOT carried:
# in a tunnel the traffic on the surface streets above IS 10 m above the player, legitimately.
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case traffic_tunnel_touch -ExpectFail -Label pre-fix
#
@{
  Name    = 'traffic_tunnel_touch'
  Area    = 'traffic'
  Bug     = 'issue #14 -- traffic cars disappear when touched, consistently in the highway tunnel'
  Frames  = $false
  Run     = @{
    Drive          = $true
    MaxSeconds     = 90
    SkipIntro     = $true      # the console -skipvideos latch (see the banner)
    AcceptGap     = 1.0        # harness pump latency, not a game gate
    Teleport       = '3013.0,-7.5,-1150.0,0'
    ThrottleScript = '0:accel'
  }
  DiagEnv = 'BRN_TRAFFIC_TRACK=1,BRN_TRAFFIC_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }

    @{ Kind = 'Script'; Name = 'the witness produced samples'; Script = {
        param($ctx)
        $n = ($ctx.LogLines | Where-Object { $_ -match '\[traffic-track\] SAMPLE ' }).Count
        $v = ($ctx.LogLines | Where-Object { $_ -match '\[traffic-track\] t=' }).Count
        return @{ Pass = ($n -ge 40 -and $v -ge 40)
                  Detail = "samples=$n vehicle-lines=$v (need >=40 of each; 0 means BRN_TRAFFIC_TRACK never reached the game)" }
      } }

    @{ Kind = 'Script'; Name = 'no physical/crashed vehicle y jumps > 2 m in 0.5 s'; Script = {
        param($ctx)
        $rx = '\[traffic-track\] t=(?<t>[-\d.eE+]+) id=(?<id>\d+) pos=\((?<x>[-\d.eE+]+), (?<y>[-\d.eE+]+), (?<z>[-\d.eE+]+)\) state=(?<st>\w+) vis=(?<vis>\d) dist=(?<d>[-\d.eE+]+) infront=(?<f>\d)'
        $last = @{}
        $worst = 0.0; $worstDetail = ''
        $hits = 0
        foreach ($l in $ctx.LogLines) {
          if ($l -notmatch $rx) { continue }
          $id = $Matches.id; $t = [double]$Matches.t; $y = [double]$Matches.y; $st = $Matches.st
          $xx = [double]$Matches.x; $zz = [double]$Matches.z
          if ($last.ContainsKey($id)) {
            $p = $last[$id]
            $dt = $t - $p.t
            # 2 m in 0.5 s while the state is unchanged is the lane-following teleport; a
            # 4 m step ACROSS a state change is the demotion/recycle hand-over snapping a car
            # to a param that outran it (the [T3-return] divergence of the T-wave round-3
            # list), which is the other half of "teleports above the road".
            $lim = if ($p.st -eq $st) { 2.0 } else { 4.0 }
            # TUNNEL-SPECIFIC: a LANE-FOLLOWING car (param/static in both samples) rides the authored
            # lane spline, and the south-portal ramps drop 2.4 m per 0.5 s at highway speed (measured
            # post-fix, run 20260907_115444: ids 40/218/276, all param->param on the ramps). The bug
            # is a PHYSICS-body effect, so only steps that involve a physical/crashed sample count.
            $lbLaneOnly = (($p.st -eq 'param' -or $p.st -eq 'static') -and ($st -eq 'param' -or $st -eq 'static'))
            if ($dt -gt 0 -and $dt -le 1.5 -and -not $lbLaneOnly) {
              $dy = [math]::Abs($y - $p.y)
              if ($dy -gt $lim) {
                $hits++
                if ($dy -gt $worst) {
                  $worst = $dy
                  $worstDetail = ("id={0} t={1:f1}->{2:f1} state={3} y {4:f2}->{5:f2} (dy={6:f2}m) xz ({7:f1},{8:f1})->({9:f1},{10:f1})" -f `
                                  $id, $p.t, $t, $st, $p.y, $y, $dy, $p.x, $p.z, $xx, $zz)
                }
              }
            }
          }
          $last[$id] = @{ t = $t; y = $y; st = $st; x = $xx; z = $zz }
        }
        if ($hits -eq 0) { return @{ Pass = $true; Detail = 'no y jump > 2 m (same state) / 4 m (across a state change) between consecutive samples' } }
        return @{ Pass = $false; Detail = "$hits y-jumps over the limit; worst $worstDetail" }
      } }

    @{ Kind = 'Script'; Name = 'removals obey the console radius'; Script = {
        param($ctx)
        # The console's ONLY distance-driven traffic removal is TryClearupOffscreenTraffic
        # @0x8273C4C8: it kills a physical car ONLY when the squared distance from
        # mCameraLastFrame exceeds unk_8300CC80 == 22500 (150 m), and never one the render pass
        # touched last frame. The showtime band (15 m behind the camera) is gated on
        # mbPlayingShowtimeMode, which this scenario never enters. The chase camera trails the
        # player by well under 15 m, so a removal reported at < 135 m from the PLAYER cannot be
        # the console's rule -- that is the reported "traffic disappears" symptom.
        $rx = '\[traffic-track\] id=(?<id>\d+) REMOVED reason=(?<r>\S+) state=(?<st>\w+) pos=\((?<x>[-\d.eE+]+), (?<y>[-\d.eE+]+), (?<z>[-\d.eE+]+)\) vis=(?<vis>\d) dist=(?<d>[-\d.eE+]+) infront=(?<f>\d)'
        $bad = @(); $all = 0
        foreach ($l in $ctx.LogLines) {
          if ($l -notmatch $rx) { continue }
          $all++
          $d = [double]$Matches.d
          $why = ''
          if ($Matches.r -eq 'clearup-offscreen' -and $d -lt 135.0) { $why = 'clearup inside the 150 m console radius' }
          elseif ($Matches.f -eq '1' -and $d -lt 80.0)              { $why = 'removed in front of the player within 80 m' }
          if ($why -ne '') {
            $bad += ("id={0} reason={1} state={2} dist={3:f1}m vis={4} infront={5} -- {6}" -f `
                     $Matches.id, $Matches.r, $Matches.st, $d, $Matches.vis, $Matches.f, $why)
          }
        }
        if ($bad.Count -eq 0) { return @{ Pass = $true; Detail = "removals=$all, all outside the console radius" } }
        return @{ Pass = $false; Detail = ("{0}/{1} removals break the console rule: {2}" -f $bad.Count, $all, (($bad | Select-Object -First 4) -join ' ; ')) }
      } }

    @{ Kind = 'Script'; Name = 'the traffic behaviour centre follows the player'; Script = {
        param($ctx)
        # THE ROOT-CAUSE CHECK. TrafficEntityModule::mCameraLastFrame is not a picture, it is
        # the module's BEHAVIOUR CENTRE: TryClearupOffscreenTraffic @0x8273C4C8 kills every
        # non-rendered physical car whose squared distance from it exceeds 22500 (150 m), and
        # SpawnNewTraffic / UpdateSympatheticCrashing / the junction FUP measure from the same
        # member. So a frame on which that point is not near the player is a frame that
        # deletes and stops spawning the traffic standing around him -- the reported
        # "traffic disappears ... and does other weird things".
        # The [T-anchor] probe (BRN_TRAFFIC_DIAG, BrnTrafficEntityModule_wT1_01.cpp) prints
        # both numbers on one line: the sim-box anchor the pass used (the player's car) and
        # mCameraLastFrame. Samples whose cam is EXACTLY the origin are the pre-handover boot
        # frames (the director has not published a camera yet) and are not the bug.
        $rx = '\[T-anchor\] d (?<d>\d+) divergent \d+ playerActive 1 idx -?\d+ anchor (?<ax>[-\d.eE+]+) (?<ay>[-\d.eE+]+) (?<az>[-\d.eE+]+) cam (?<cx>[-\d.eE+]+) (?<cy>[-\d.eE+]+) (?<cz>[-\d.eE+]+)'
        $n = 0; $bad = @(); $worst = 0.0
        foreach ($l in $ctx.LogLines) {
          if ($l -notmatch $rx) { continue }
          $cx = [double]$Matches.cx; $cy = [double]$Matches.cy; $cz = [double]$Matches.cz
          if ($cx -eq 0.0 -and $cy -eq 0.0 -and $cz -eq 0.0) { continue }   # pre-handover
          $n++
          $ax = [double]$Matches.ax; $ay = [double]$Matches.ay; $az = [double]$Matches.az
          $dd = [math]::Sqrt((($ax-$cx)*($ax-$cx)) + (($ay-$cy)*($ay-$cy)) + (($az-$cz)*($az-$cz)))
          if ($dd -gt $worst) { $worst = $dd }
          if ($dd -gt 150.0) {
            $bad += ("d={0} anchor=({1:f1},{2:f1},{3:f1}) cam=({4:f1},{5:f1},{6:f1}) apart={7:f0}m" -f `
                     $Matches.d, $ax, $ay, $az, $cx, $cy, $cz, $dd)
          }
        }
        if ($n -lt 20) { return @{ Pass = $false; Detail = "only $n usable [T-anchor] samples -- cannot evaluate (BRN_TRAFFIC_DIAG unset?)" } }
        if ($bad.Count -eq 0) { return @{ Pass = $true; Detail = ("{0} samples, behaviour centre never more than {1:f1} m from the player (limit 150 m = the clearup radius)" -f $n, $worst) }}
        return @{ Pass = $false; Detail = ("{0}/{1} samples put the behaviour centre outside the 150 m clearup radius (worst {2:f0} m): {3}" -f `
                  $bad.Count, $n, $worst, (($bad | Select-Object -First 4) -join ' ; ')) }
      } }

    @{ Kind = 'Script'; Name = 'no physics stage moves a traffic body more than 2 m in one step'; Script = {
        param($ctx)
        # THE ROOT-CAUSE CHECK. [T-ystep] (BRN_TRAFFIC_DIAG, BrnPhysicsModuleUpdateFunctions.cpp)
        # samples every live traffic body's Y at each stage of the physics frame and prints one line
        # when a slot moved > 0.25 m since the previous stage. A car on its wheels moves millimetres
        # per stage; the bug was an 11 m step at "postsim" (the post-simulation suspension seating
        # the body on a stale road contact). "postscene-end" is the slot-reuse snap of a freshly
        # created body from the pool seat's old transform to its spawn transform -- a create, not a
        # move -- and is exempt.
        $rx = '\[T-ystep\] stage=(?<st>[\w-]+) slot=(?<s>\d+) state=(?<ps>\d+) y (?<a>[-\d.eE+]+) -> (?<b>[-\d.eE+]+) dy=(?<d>[-\d.eE+]+)'
        $bad = @(); $n = 0
        foreach ($l in $ctx.LogLines) {
          if ($l -notmatch $rx) { continue }
          $n++
          if ($Matches.st -eq 'postscene-end') { continue }
          $d = [math]::Abs([double]$Matches.d)
          if ($d -gt 2.0) {
            $bad += ("stage={0} slot={1} state={2} y {3}->{4} (dy={5})" -f $Matches.st, $Matches.s, $Matches.ps, $Matches.a, $Matches.b, $Matches.d)
          }
        }
        if ($bad.Count -eq 0) { return @{ Pass = $true; Detail = "$n [T-ystep] events, none over 2 m outside slot creation" } }
        return @{ Pass = $false; Detail = ("{0}/{1} [T-ystep] steps over 2 m: {2}" -f $bad.Count, $n, (($bad | Select-Object -First 4) -join ' ; ')) }
      } }

    @{ Kind = 'Script'; Name = 'population does not collapse'; Script = {
        param($ctx)
        $rxS = '\[traffic-track\] SAMPLE t=(?<t>[-\d.eE+]+) alive=(?<a>\d+) near=(?<n>\d+)'
        $samples = @()
        foreach ($l in $ctx.LogLines) {
          if ($l -match $rxS) { $samples += @{ t = [double]$Matches.t; a = [int]$Matches.a; n = [int]$Matches.n } }
        }
        if ($samples.Count -lt 40) { return @{ Pass = $false; Detail = "only $($samples.Count) SAMPLE lines -- cannot evaluate" } }
        $tMax = 0.0
        foreach ($s0 in $samples) { if ($s0.t -gt $tMax) { $tMax = $s0.t } }
        $early = @($samples | Where-Object { $_.t -ge 20 -and $_.t -le 40 })
        $late  = @($samples | Where-Object { $_.t -ge ($tMax - 20) })
        if ($early.Count -eq 0 -or $late.Count -eq 0) { return @{ Pass = $false; Detail = "no early/late window (tMax=$tMax)" } }
        $eA = 0.0; $lA = 0.0; $eN = 0.0; $lN = 0.0
        foreach ($s0 in $early) { $eA += $s0.a; $eN += $s0.n }
        foreach ($s0 in $late)  { $lA += $s0.a; $lN += $s0.n }
        $eA = $eA / $early.Count; $eN = $eN / $early.Count
        $lA = $lA / $late.Count;  $lN = $lN / $late.Count
        $ok = ($eA -le 0) -or ($lA -ge 0.5 * $eA)
        return @{ Pass = $ok
                  Detail = ("alive {0:f1} (t 20-40s) -> {1:f1} (last 20 s, tMax={2:f0}s); near {3:f1} -> {4:f1}; need alive_late >= 50% of alive_early" -f $eA, $lA, $tMax, $eN, $lN) }
      } }
  )
}
