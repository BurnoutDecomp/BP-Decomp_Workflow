# vw_showtime_score -- upstream FxShowtime2Live (the Showtime per-car score chain) on a seat whose wreck reaches
# traffic (lane SHOWTIME, visual wave VW).
#
# Two harness defects keep the upstream case red on the 15:29 exe without any game fault:
#   1. its ShowtimeContacts seat often scores no traffic at all (playtest_showtime_cash\20261008_172757:
#      0 pushes, 0 pops), so every chain check is unevaluable;
#   2. "the GUI translator turned 140 into GuiHitVehicleEvent (394)" reads a witness that shares one
#      24-line budget with the per-frame action 142 score updates, which spend it in the first 0.4 s.
# This wrapper keeps every other check unchanged, moves the drive to vw_showtime_cash's seat, and reads the
# 394 hop where the GUI receives it instead (AboveCarRenderer, BRN_SHOWTIME_DIAG "[abovecar] bank add").
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case vw_showtime_score
$case = & (Join-Path $PSScriptRoot '..\..\..\b5-decomp\tests\FxShowtime2Live.ps1')
$case.Name = 'vw_showtime_score'
$case.Remove('FreshProfile')
$case.ProfileFixture = 'scratch\gameplay_wave\profile_backup\Profile.sav.pose250700'
$case.Run.Teleport = '2886.0,1.0,-2020.0,180'
$case.Run.ThrottleScript = '0:accel,16:none'
$case.Run.Showtime = '20:3'
$case.Run.Boost = '24'
$case.Run.MaxSeconds = 105
$case.DiagEnv += ',BRN_SHOWTIME_DIAG=1'
foreach ($check in $case.Checks) {
    if ($check.Name -ne 'the GUI translator turned 140 into GuiHitVehicleEvent (394)') { continue }
    $check.Clear()
    $check.Kind = 'Script'
    $check.Name = 'every scored hit (140) reached the GUI as GuiHitVehicleEvent (394) and banked'
    $check.Script = {
        param($ctx)
        $answers = @($ctx.LogLines | Where-Object { $_ -match '^\[showtime-score\] answer traffic car \d+ .* -> action 140' }).Count
        $added = 0
        foreach ($l in $ctx.LogLines) {
            if ($l -match '^\[abovecar\] bank add count=(\d+) \(was (\d+)\)') { $added += [int]$Matches[1] - [int]$Matches[2] }
        }
        @{ Pass = ($answers -ge 1 -and $added -eq $answers); Detail = "140 answers=$answers, 394 banked at the GUI=$added" }
    }
}
$case
