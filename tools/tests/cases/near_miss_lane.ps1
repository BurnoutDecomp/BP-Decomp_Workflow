# near_miss_lane -- does the near-miss chain actually carry?
#
# The chain (traffic proximity -> the pre-scene traffic->race-car interface -> the race-car
# module's post-scene drain -> NearMissManager -> game events 64/65/66 + boost credit) went live
# on 2026-09-11 and until now had NO log site anywhere, so no case could tell "it fires" from
# "it is a well-formed no-op". This case is the oracle for that, and nothing else.
#
# THE WITNESS, every line behind the existing BRN_TRAFFIC_DIAG gate:
#   [T9-nm] results q=99 n=<n> [DELETE-WHEN-STABLE]
#       TrafficEntityModule::ProcessNearbyTrafficSceneQueryResults, one-shot on the first
#       matching batch that carried anything. This is the TRANSPORT proof and it is what this
#       case fails on: the 70 m sphere query was posted, the scene manager answered it, the
#       world bridge carried the answer into the traffic module's post-physics input, and the
#       drain read it. It says nothing about whether anything was CLOSE enough to score.
#   [T9-nm] drain traffic=<n> racecar=<n> [DELETE-WHEN-STABLE]
#       RaceCarEntityModule::UpdateTrafficAndRaceCarNearMisses, budgeted to 24 lines, printed
#       only on a drain where at least one collection is non-empty. It proves the traffic
#       module's proximity records crossed the bridge into the consumer.
#   [T9-nm] EVENT 64 id=<n> category=<n> chain=<n> [DELETE-WHEN-STABLE]
#       NearMissManager::NearMissEvent, budgeted to 24. category is ENearMissType:
#       0 normal traffic, 1 normal other race car, 2 crash-escape traffic, 3 crash-escape other
#       race car (read the enum in BrnNearMissManager.h, not this comment, if it ever moves).
#       Plus one-shot EVENT 65 (chain alive) and EVENT 66 (chain timed out) lines.
#
# ⚠️ DO NOT read `[T4-hit] outcome=NEARMISS` as this feed. That line is the physics CONTACT
# outcome (SetFreakedOut on an actual touch) in the traffic crash-response path, and it prints
# under the same BRN_TRAFFIC_DIAG. This chain is proximity WITHOUT contact; scoring it off the
# [T4-hit] line would be a false green.
#
# Scenario is traffic_track_lane's, unchanged (same teleport, same throttle schedule, same 80 s):
# that drive is the predicate this chain wants -- traffic in lane beside the player above 30 mph,
# which is exactly the producer's own filter (player > 30 mph, traffic within 5 m / race car
# within 10 m). BRN_TRAFFIC_TRACK is NOT set here: this case does not read those lines and the
# per-vehicle track spam is 40+ lines a second of log it would have to be filtered out of.
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case near_miss_lane
#
# ⭐ WHICH CHECK IS HARD, AND WHY IT IS THE TRANSPORT ONE. There is no Soft/Info kind in
# _checks.ps1 (a check either passes or fails), so an informational check is written as a
# `Script` that ALWAYS returns Pass=$true and carries the real numbers in its Detail.
#
# ⚠ MEASURED 2026-09-11, two runs of THIS case against builds of the same chain: one drive
# produced sixteen non-empty drains and a scored near miss, the other produced none at all --
# same teleport, same throttle script, same 80 s. Nothing was broken in the second one. The
# producer's own filter is player > 30 mph AND a traffic car within 5 m (race car within 10 m)
# on the frame the sphere batch is drained, and whether an 80 s lane drive ever satisfies it
# depends on where the traffic happens to be spawned that run. So "a near miss fired" and even
# "a collection came back non-empty" are GAMEPLAY outcomes, not chain health, and neither is
# scored hard here -- a check that goes red on a legal drive is one people learn to ignore.
#
# What IS deterministic is the transport: the query is posted every non-paused running frame
# while the player car is active, and the 70 m sphere around the camera returns the cars in the
# lane whether or not any of them comes inside 5 m. That is the hard check. If it is red the
# chain is broken; if it is green and both INFO lines are zero, the drive simply never passed
# anything closely enough.
#
@{
  Name    = 'near_miss_lane'
  Area    = 'traffic'
  Bug     = 'the near-miss chain has no log site -- no case can prove a near miss ever fires'
  Frames  = $false
  Run     = @{
    Drive          = $true
    MaxSeconds     = 80
    SkipIntro      = $true      # the console -skipvideos latch
    AcceptGap      = 1.0        # harness pump latency, not a game gate
    Teleport       = '3323.9,-2.4,-1793.2,0'
    ThrottleScript = '0:accel,30:none,40:accel'
  }
  DiagEnv = 'BRN_TRAFFIC_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }

    @{ Kind = 'Script'; Name = 'the sphere-query results reached the traffic drain'; Script = {
        param($ctx)
        # THE HARD CHECK -- the whole transport, end to end, in one latched line.
        $rx = '\[T9-nm\] results q=(?<q>\d+) n=(?<n>\d+)'
        foreach ($l in $ctx.LogLines) {
          if ($l -match $rx) {
            return @{ Pass = $true
                      Detail = ("first matching batch: query id {0}, {1} entities returned (one-shot witness)" -f $Matches.q, $Matches.n) }
          }
        }
        return @{ Pass = $false
                  Detail = 'no [T9-nm] results line all run. The 70 m nearby-traffic sphere query never came back to the traffic module with a single entity: either it was never posted (the player car never went active on a running, non-paused frame), or the scene manager answered it empty, or the world bridge did not carry the answer into the post-physics input buffer -- or BRN_TRAFFIC_DIAG never reached the game (check for other [T...] lines in the log)' }
      } }

    @{ Kind = 'Script'; Name = 'INFO -- the near-miss drain saw a non-empty collection (never fails; see the banner)'; Script = {
        param($ctx)
        # INFORMATIONAL. The witness only prints when at least one length is non-zero, so any
        # line at all is a carrying bridge -- but parse the numbers anyway, so a future change
        # that starts printing zeroes is visible in the Detail.
        $rx = '\[T9-nm\] drain traffic=(?<t>\d+) racecar=(?<r>\d+)'
        $n = 0; $nz = 0; $maxT = 0; $maxR = 0
        foreach ($l in $ctx.LogLines) {
          if ($l -notmatch $rx) { continue }
          $n++
          $t = [int]$Matches.t; $r = [int]$Matches.r
          if ($t -gt 0 -or $r -gt 0) { $nz++ }
          if ($t -gt $maxT) { $maxT = $t }
          if ($r -gt $maxR) { $maxR = $r }
        }
        if ($n -eq 0) {
          return @{ Pass = $true
                    Detail = 'INFO: no [T9-nm] drain line all run -- nothing the sphere returned was ever inside 5 m (10 m for a race car) on a frame the player was above 30 mph. Legal on a lane drive; the hard check above says whether the chain itself carried.' }
        }
        return @{ Pass = $true
                  Detail = ("INFO: {0} drain lines, {1} with a non-zero length; max traffic={2} max racecar={3} (the witness is budgeted to 24 lines)" -f $n, $nz, $maxT, $maxR) }
      } }

    @{ Kind = 'Script'; Name = 'INFO -- near-miss events posted (never fails; see the banner)'; Script = {
        param($ctx)
        $rx64 = '\[T9-nm\] EVENT 64 id=(?<id>-?\d+) category=(?<c>-?\d+) chain=(?<n>-?\d+)'
        $rx65 = '\[T9-nm\] EVENT 65 chain=(?<n>-?\d+)'
        $rx66 = '\[T9-nm\] EVENT 66 chain=(?<n>-?\d+) succeeded=(?<s>\d)'
        $n64 = 0; $cats = @{}; $maxChain = 0; $first = ''
        $n65 = 0; $n66 = 0; $done = ''
        foreach ($l in $ctx.LogLines) {
          if ($l -match $rx64) {
            $n64++
            $c = $Matches.c
            if ($cats.ContainsKey($c)) { $cats[$c] = $cats[$c] + 1 } else { $cats[$c] = 1 }
            if ([int]$Matches.n -gt $maxChain) { $maxChain = [int]$Matches.n }
            if ($first -eq '') { $first = ("id={0} category={1}" -f $Matches.id, $c) }
            continue
          }
          if ($l -match $rx65) { $n65++; continue }
          if ($l -match $rx66) { $n66++; if ($done -eq '') { $done = ("chain={0} succeeded={1}" -f $Matches.n, $Matches.s) } }
        }
        if ($n64 -eq 0) {
          return @{ Pass = $true
                    Detail = 'INFO: no near miss fired this run. Legal on a lane drive -- the player may never have passed a car inside 5 m above 30 mph without touching it. If the transport check above is green, the chain carries and the drive simply had no qualifying pass.' }
        }
        $catText = (($cats.Keys | Sort-Object | ForEach-Object { 'cat' + "$_" + '=' + $cats[$_] }) -join ' ')
        return @{ Pass = $true
                  Detail = ("INFO: {0} near-miss events (64), categories {1}, longest chain {2}, first {3}; chain-alive lines (65) {4}, chain-complete (66) {5} {6}" -f `
                            $n64, $catText, $maxChain, $first, $n65, $n66, $done) }
      } }
  )
}
