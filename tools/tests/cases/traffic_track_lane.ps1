# traffic_track_lane -- lane `traffic_weird`: "traffic disappear, teleport above and do other
# weird things".
#
# The bug is not an assert, so the oracle is the [traffic-track] witness (opt-in
# BRN_TRAFFIC_TRACK, added in BrnTrafficEntityModule_wT1_01.cpp / _wT5_01.cpp): every 0.5 s of
# sim time it prints one line per ALIVE traffic vehicle within 120 m of the player --
#   [traffic-track] t=<s> id=<n> pos=(x, y, z) state=<param|static|physical|crashed> vis=<0|1>
#                   dist=<m> infront=<0|1>
# plus a per-sample census
#   [traffic-track] SAMPLE t=<s> alive=<n> near=<n> printed=<n> player=(x, y, z)
# and one line per removal, from the module's single kill entry point
#   [traffic-track] id=<n> REMOVED reason=<caller> state=<..> pos=(..) vis=<0|1> dist=<m> infront=<0|1>
#
# The four behavioural checks below are the report's four symptoms, in the console's own terms:
#   * TELEPORT: a vehicle's y moves more than 2 m between two consecutive 0.5 s samples while
#     its state is unchanged (a car driving a lane cannot climb 4 m/s vertically), or more than
#     4 m across a state change (the demotion/recycle hand-over snapping a car onto a param that
#     outran it).
#   * DISAPPEAR IN VIEW: a vehicle is REMOVED while it is in front of the player and closer
#     than 80 m. The console's own removal rule permits none of that:
#     TryClearupOffscreenTraffic @0x8273C4C8 kills only beyond
#     KF_CLEARUP_FAR_FROM_CAMERA_DIST_SQ == 22500 (150 m) and never a car the render pass
#     touched last frame; the showtime band (not this scenario) starts at 15 m BEHIND.
#   * ABOVE THE ROAD: a vehicle sits more than 4 m above the player while within 40 m of him,
#     for two consecutive samples (>= 1 s). The player is on the road; the traffic beside him
#     is not on an overpass at this teleport spot.
#   * POPULATION COLLAPSE: the near-vehicle census late in the drive is at least half what it
#     was 30 s in (the "population collapse late in long drives" of the T-wave round-3 list).
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case traffic_track_lane -ExpectFail -Label pre-fix
@{
  Name    = 'traffic_track_lane'
  Area    = 'traffic'
  Bug     = 'field report -- traffic disappears, teleports above the road, and does other weird things'
  Frames  = $false
  Run     = @{
    Drive          = $true
    MaxSeconds     = 160
    Teleport       = '3323.9,-2.4,-1793.2,0'
    ThrottleScript = '0:accel,30:none,40:accel'
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

    @{ Kind = 'Script'; Name = 'no vehicle y jumps > 2 m in 0.5 s'; Script = {
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
            if ($dt -gt 0 -and $dt -le 1.5) {
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

    @{ Kind = 'Script'; Name = 'no vehicle > 4 m above the player for >= 1 s'; Script = {
        param($ctx)
        $rxS = '\[traffic-track\] SAMPLE t=(?<t>[-\d.eE+]+) alive=(?<a>\d+) near=(?<n>\d+) printed=(?<p>\d+) player=\((?<px>[-\d.eE+]+), (?<py>[-\d.eE+]+), (?<pz>[-\d.eE+]+)\)'
        $rxV = '\[traffic-track\] t=(?<t>[-\d.eE+]+) id=(?<id>\d+) pos=\((?<x>[-\d.eE+]+), (?<y>[-\d.eE+]+), (?<z>[-\d.eE+]+)\) state=(?<st>\w+) vis=(?<vis>\d) dist=(?<d>[-\d.eE+]+) infront=(?<f>\d)'
        # the SAMPLE line is emitted AFTER its own vehicle lines, so buffer per t
        $pend = @(); $streak = @{}; $bad = @(); $py = $null
        foreach ($l in $ctx.LogLines) {
          if ($l -match $rxV) {
            $pend += @{ t = [double]$Matches.t; id = $Matches.id; y = [double]$Matches.y; d = [double]$Matches.d; st = $Matches.st }
            continue
          }
          if ($l -match $rxS) {
            $py = [double]$Matches.py
            $t  = [double]$Matches.t
            $seen = @{}
            foreach ($v in $pend) {
              if ($v.d -lt 40.0 -and ($v.y - $py) -gt 4.0) {
                $seen[$v.id] = $true
                $c = 0; if ($streak.ContainsKey($v.id)) { $c = $streak[$v.id] }
                $c++
                $streak[$v.id] = $c
                if ($c -ge 2) {
                  $bad += ("id={0} t={1:f1} y={2:f2} playerY={3:f2} above={4:f2}m dist={5:f1} state={6} samples={7}" -f `
                           $v.id, $t, $v.y, $py, ($v.y - $py), $v.d, $v.st, $c)
                }
              }
            }
            foreach ($k in @($streak.Keys)) { if (-not $seen.ContainsKey($k)) { $streak[$k] = 0 } }
            $pend = @()
          }
        }
        if ($bad.Count -eq 0) { return @{ Pass = $true; Detail = 'no vehicle sat > 4 m above the player within 40 m for >= 1 s' } }
        return @{ Pass = $false; Detail = ("{0} airborne observations: {1}" -f $bad.Count, (($bad | Select-Object -First 4) -join ' ; ')) }
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
