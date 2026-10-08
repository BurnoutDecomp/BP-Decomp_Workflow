# vw_showtime_crash_entry -- Showtime entered from a REAL crash (lane SHOWTIME, visual wave VW).
#
# Upstream's live Showtime cases (PlaytestShowtimeControlsLive / PlaytestShowtimeCameraControlsLive)
# press both bumpers at DRIVING+49, after the route's wall crash has reset, so every run takes the
# ground LAUNCH arm of RaceCarPhysics::SetPlayerVehicleInShowtime. This case reuses the camera-controls
# case unchanged (same seat, profile, boost pulses, four stick holds, basis/force checks) and presses
# both bumpers half a second after the route's wall crash opens (cue-gated on the [crash-info]
# hardstopVsWall line: the crash time moves by several seconds between boots, so a fixed -Showtime
# time missed it once), so the console's other arm runs: (mbHasAir || IsCrashing()) -> pushT 0.001,
# no relaunch.
# Checks on top of upstream's: the crash arm was taken with crashing=1, the car was really wrecked
# when the gesture landed, the Showtime crash camera/bounces/score ran, and the mode left cleanly
# (idle ladder -> results -> reset on the road).
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case vw_showtime_crash_entry
$case = & (Join-Path $PSScriptRoot '..\..\..\b5-decomp\tests\PlaytestShowtimeCameraControlsLive.ps1')
$case.Name = 'vw_showtime_crash_entry'
$case.Bug = 'Showtime started DURING a real wall crash must take the console crash arm (no relaunch) and play, score and exit like the launch entry.'
$case.Run.Remove('Showtime')
# Bounces are pressed by the script (one 0.3 s boost hold about every second, above the console's 0.7 s
# re-arm window) from the Showtime entry on; the drive's own fixed-time -Boost pulses are dropped.
$case.Run.Remove('Boost')
$case.Run.MenuScript = 'timeout:120; wait:hardstopVsWall 1 .*crash events 1; sleep:0.5; hold:ShoulderL:4; hold:ShoulderR:4; wait:\[showtime\] enter:; sleep:1; hold:Boost:0.3; sleep:1; hold:Boost:0.3; hold:SteerLeft:2; sleep:1; hold:Boost:0.3; sleep:1.2; hold:Boost:0.3; sleep:1; hold:Boost:0.3; hold:SteerRight:2; sleep:1; hold:Boost:0.3; sleep:1.2; hold:Boost:0.3; sleep:1; hold:Boost:0.3; hold:StickUp:2; sleep:1; hold:Boost:0.3; sleep:1.2; hold:Boost:0.3; sleep:1; hold:Boost:0.3; hold:StickDown:2; sleep:1; hold:Boost:0.3; sleep:1.2; hold:Boost:0.3; sleep:1; hold:Boost:0.3; sleep:1; hold:Boost:0.3; mark:controls_done'
$case.Run.MaxSeconds = 150
$case.Run.FrameEvery = 40
$case.DiagEnv = $case.DiagEnv -replace 'BRN_FRAME_DUMP_MAX=\d+', 'BRN_FRAME_DUMP_MAX=230'
foreach ($check in $case.Checks) {
    if ($check.Name -ne 'original valid Showtime entry arm') { continue }
    $check.Name = 'Showtime entered through the crash arm (crashing=1, no launch)'
    $check.Script = {
        param($ctx)
        $entry = @($ctx.LogLines | Where-Object { $_ -match '^\[showtime\] enter:' } | Select-Object -First 1)
        if ($entry.Count -eq 0) { return @{ Pass = $false; Detail = 'no Showtime entry recorded' } }
        $pop = @($ctx.LogLines | Where-Object { $_ -match '^\[showtime\] launch pop:' }).Count
        $crashArm = $entry[0] -match 'enter: airborne/crash arm \(hasAir=[01] crashing=1\) pushT=0\.001'
        @{ Pass = ($crashArm -and $pop -eq 0); Detail = "$($entry[0]); launch pops=$pop" }
    }
}
$case.Checks += @(
    @{ Kind = 'Script'; Name = 'the gesture landed inside the wall crash (wreck open before entry)'; Script = {
        param($ctx)
        $open = -1; $complete = -1; $entry = -1; $i = 0
        foreach ($l in $ctx.LogLines) {
            if ($entry -lt 0 -and $open -lt 0 -and $l -match 'hardstopVsWall 1 .*crash events 1') { $open = $i }
            if ($open -ge 0 -and $entry -lt 0 -and $complete -lt 0 -and $l -match '^\[crash-exit\] CRASH COMPLETE') { $complete = $i }
            if ($entry -lt 0 -and $l -match '^\[showtime\] enter:') { $entry = $i }
            $i++
        }
        $pass = ($open -ge 0) -and ($entry -gt $open) -and ($complete -lt 0 -or $complete -gt $entry)
        @{ Pass = $pass; Detail = "wall crash line=$open, showtime entry line=$entry, crash complete before entry line=$complete" }
    } }
    @{ Kind = 'LogMatch'; Name = 'Showtime physics entered'; Pattern = '\[showtime-watch\] mbPlayerCarInShowtime -> 1' }
    @{ Kind = 'LogCount'; Name = 'Showtime score updates reach the GUI (action 142 -> gui 396)'; Pattern = '\[showtime-score\] action 142 SHOWTIME_UPDATE -> gui 396'; Min = 10 }
    @{ Kind = 'LogMatch'; Name = 'Showtime ended through the console idle ladder'; Pattern = '\[crash-end\] ENDED via the IDLE LADDER' }
    @{ Kind = 'LogMatch'; Name = 'Showtime physics left'; Pattern = '\[showtime-watch\] mbPlayerCarInShowtime -> 0' }
    @{ Kind = 'LogMatch'; Name = 'Showtime results then the car reset onto the road'; Pattern = '\[showtime-switch\] ActiveRaceCar 0 mbIsInShowtime <- 0' }
    @{ Kind = 'Script'; Name = 'roaming camera back after the Showtime reset'; Script = {
        param($ctx)
        $left = -1; $roam = -1; $i = 0
        foreach ($l in $ctx.LogLines) {
            if ($left -lt 0 -and $l -match '^\[showtime-switch\] ActiveRaceCar 0 mbIsInShowtime <- 0') { $left = $i }
            if ($left -ge 0 -and $roam -lt 0 -and $l -match '^\[crashcam\] container current state -> 1 \(ArbStateRoaming\)') { $roam = $i }
            $i++
        }
        @{ Pass = ($left -ge 0 -and $roam -gt $left); Detail = "showtime left line=$left, roaming line=$roam" }
    } }
)
$case
