# vw_showtime_cash -- Showtime cash labels and traffic-hit banking, live (lane SHOWTIME, visual wave VW).
#
# Upstream 1f6749c0 restored the AboveCar cash labels and the banked-score flight, but its live case
# (b5-decomp\tests\PlaytestShowtimeCashLive.ps1) "does not claim organic traffic-hit banking": on its
# seat the Showtime wreck often reaches no traffic (run 20261008_172757: 0 traffic crashes), and its
# per-hop witnesses share 24 lines with the per-frame score updates, so the 394 hop is never printed.
# This case uses showtime_popups' seat (2886,1,-2020 heading 180, where the wreck reaches traffic
# within a few seconds) and the opt-in AboveCar witness (BRN_SHOWTIME_DIAG, BrnAboveCarRenderer.cpp):
#   [abovecar] bank add count=N (was M) scoringTraffic=S      a GuiHitVehicleEvent (394) banked a score
#   [abovecar] bank start value=V world=(...) screen=(x,y)    its one projection through the GUI camera
#   [abovecar] bank arrive count=N (was M)                    a score reached the counter and was erased
#   [abovecar] frame mode=G trafficLabels=L banked=B           every 300th AboveCar frame
# and dense frames over the first ~35 s of Showtime, so the labels and the banked flight can be seen.
# Bounces are pulsed with the boost button so the wreck keeps moving through traffic.
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case vw_showtime_cash
@{
  Name    = 'vw_showtime_cash'
  Area    = 'gui/abovecar'
  Bug     = 'Organic Showtime traffic hits must bank their cash through AboveCarRenderer (394 -> project -> fly to the counter) while the traffic cash labels draw.'
  Frames  = $true
  ProfileFixture = 'scratch\gameplay_wave\profile_backup\Profile.sav.pose250700'
  Run     = @{
    Drive          = $true
    MotionProbe    = $true
    MaxSeconds     = 105
    SkipIntro      = $true
    AcceptGap      = 1.0
    Teleport       = '2886.0,1.0,-2020.0,180'
    ThrottleScript = '0:accel,16:none'
    Showtime       = '20:3'
    ShowtimeIgnoreProgression = $true
    Boost          = '24'
    FrameEvery     = 10
  }
  DiagEnv = 'BRN_SHOWTIME_DIAG=1,BRN_SHOWTIME_WATCH=1,BRN_DIRECTOR_ACTION_DIAG=1,BRN_FRAME_DUMP_START=2300,BRN_FRAME_DUMP_MAX=230'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'LogMatch';   Name = 'Showtime physics entered'; Pattern = '\[showtime-watch\] mbPlayerCarInShowtime -> 1' }
    @{ Kind = 'LogValue';   Name = 'traffic cash labels drawn during Showtime (mode 2)'
       Pattern = '\[abovecar\] frame mode=2 trafficLabels=(?<n>\d+)'; Group = 'n'; Agg = 'max'; Min = 1 }
    @{ Kind = 'Script';     Name = 'every scored traffic hit banked exactly one score'; Script = {
        param($ctx)
        $answers = @($ctx.LogLines | Where-Object { $_ -match '^\[showtime-score\] answer traffic car \d+ .* -> action 140' }).Count
        $director = @($ctx.LogLines | Where-Object { $_ -match '^\[director-action\] 140 VEHICLE_HIT' }).Count
        $added = 0
        foreach ($l in $ctx.LogLines) {
            if ($l -match '^\[abovecar\] bank add count=(\d+) \(was (\d+)\)') { $added += [int]$Matches[1] - [int]$Matches[2] }
        }
        @{ Pass = ($answers -ge 1 -and $added -ge 1 -and $added -le $answers);
           Detail = "scored hits (action 140 answers)=$answers, director 140s=$director, banked scores added=$added" }
    } }
    @{ Kind = 'Script';     Name = 'each banked value is a scored hit value (base + chain bonus)'; Script = {
        param($ctx)
        # The 394 record carries the answer's base score and its earned chain bonus (miComboBonusEarned,
        # printed as "chain"); the banked text is FormatCurrency(base + bonus).
        $expected = @{}; $values = @()
        foreach ($l in $ctx.LogLines) {
            if ($l -match '^\[showtime-score\] answer traffic car \d+ .* base (\d+) .* chain (-?\d+) -> action 140') { $expected[[int]$Matches[1] + [int]$Matches[2]] = $true }
            if ($l -match '^\[abovecar\] bank start value=(-?\d+) ') { $values += [int]$Matches[1] }
        }
        $bad = @($values | Where-Object { -not $expected.ContainsKey($_) })
        @{ Pass = ($values.Count -ge 1 -and $bad.Count -eq 0);
           Detail = "bank start values=[$($values -join ',')] answered base+bonus=[$(($expected.Keys | Sort-Object) -join ',')]" }
    } }
    @{ Kind = 'LogCount';   Name = 'a banked score flew to the counter and was erased'; Pattern = '^\[abovecar\] bank arrive count='; Min = 1 }
    @{ Kind = 'Script';     Name = 'on-screen hits start inside the screen, off-screen ones at the counter (0,140)'; Script = {
        param($ctx)
        $n = 0; $bad = 0; $on = 0
        foreach ($l in $ctx.LogLines) {
            if ($l -notmatch '^\[abovecar\] bank start value=\S+ world=\S+ screen=\((?<x>[-\d.e+]+),(?<y>[-\d.e+]+)\)') { continue }
            $n++
            $x = [double]::Parse($Matches.x, [cultureinfo]::InvariantCulture); $y = [double]::Parse($Matches.y, [cultureinfo]::InvariantCulture)
            # Console: x = ndc.x * 1280 (centred between x and 1280), y = (ndc.y + 1) / 2 * 720 - 10, then one
            # 5 % step toward the target; an off-screen projection starts at the target itself.
            if ([math]::Abs($x) -lt 0.01 -and [math]::Abs($y - 140) -lt 0.01) { continue }
            $on++
            if ($x -lt -1280 -or $x -gt 1280 -or $y -lt -10 -or $y -gt 720) { $bad++ }
        }
        @{ Pass = ($n -ge 1 -and $bad -eq 0); Detail = "bank starts=$n, projected on screen=$on, out of range=$bad" }
    } }
    @{ Kind = 'LogMatch';   Name = 'Showtime ended through the console idle ladder'; Pattern = '\[crash-end\] ENDED via the IDLE LADDER' }
    @{ Kind = 'LogMatch';   Name = 'Showtime physics left'; Pattern = '\[showtime-watch\] mbPlayerCarInShowtime -> 0' }
  )
}
