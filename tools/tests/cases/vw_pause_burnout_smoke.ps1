# vw_pause_burnout_smoke -- PAUSE WITH TYRE SMOKE IN THE AIR AND AN UNDAMAGED CAR: the pause camera is then the ICE
# pause-playlist camera framing the car (ArbStateCrashNav state 3, flyby 0), so the car, its tyre smoke and the road
# under it are all in view while that camera moves and the sim clock is held.
# Scenario: returning boot, no teleport (the car stays where it spawned), a standing burnout (accel+brake) from
# DRIVING+6 s, the Driver Details pause at DRIVING+12 s while the smoke hangs, back out at DRIVING+30 s.
# Witnesses:
#   BRN_CRASHCAM_DIAG      [pause-cam]  ICE eye samples (flyby 0 = the ICE camera; the eye must move)
#   BRN_PAUSED_TRAIL_DIAG  [paused-trail]  if the burnout laid marks: trail VS constants == world VP
#   BRN_POSTFX_SOURCE_DUMP frames\inputs\source_<present>.bmp  the scene under the pause menu, every 30 presents
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case vw_pause_burnout_smoke -Slot 4
@{
    Name = 'vw_pause_burnout_smoke'
    Area = 'vfx'
    Bug = 'Paused tyre smoke and the paused car must hold still in the world while the ICE pause camera moves.'
    Frames = $true
    ProfileFixture = 'rival_hunt_profile.sav'
    Run = @{
        Drive = $true
        DriveDelay = 6
        SkipIntro = $true
        AcceptGap = 1.0
        ThrottleScript = '0:accel+brake'
        PauseAt = '12'
        PauseTarget = 'driver'
        UnpauseAt = '30'
        MaxSeconds = 60
        FrameEvery = 30
    }
    DiagEnv = 'BRN_PAUSED_TRAIL_DIAG=1,BRN_CRASHCAM_DIAG=1,BRN_SCREEN_DIAG=1,BRN_FRAME_DUMP_MAX=200,BRN_POSTFX_SOURCE_DUMP=1,BRN_POSTFX_SOURCE_START=1500,BRN_POSTFX_SOURCE_EVERY=30,BRN_POSTFX_SOURCE_MAX=60'
    Checks = @(
        @{ Kind='Mark'; Name='reached DRIVING'; Phase='DRIVING' }
        @{ Kind='LogMatch'; Name='entered Driver Details'; Pattern="\[screen\] ENTER 'CN_D_DETAIL" }
        @{ Kind='Script'; Name='the pause camera is the moving ICE camera at the car (flyby 0, eye travels >= 1 m)'; Script={
            param($ctx)
            $laE = @()
            foreach ($line in $ctx.LogLines) {
                if ($line -match '\[pause-cam\] sample t (\S+) flyby 0 .* stateEye \(([^,]+), ([^,]+), ([^)]+)\) carDist (\S+)' -and [double]$Matches[1] -gt 0.0) {
                    $laE += ,@([double]$Matches[2], [double]$Matches[3], [double]$Matches[4], [double]$Matches[5]) }
            }
            if ($laE.Count -lt 5) { return @{ Pass=$false; Detail=("{0} ICE-camera samples (the car must be undamaged at the pause)" -f $laE.Count) } }
            $lfMax = 0.0
            foreach ($a in $laE) { $d = [Math]::Sqrt(($a[0]-$laE[0][0])*($a[0]-$laE[0][0]) + ($a[1]-$laE[0][1])*($a[1]-$laE[0][1]) + ($a[2]-$laE[0][2])*($a[2]-$laE[0][2])); if ($d -gt $lfMax) { $lfMax = $d } }
            $lfCar = ($laE | ForEach-Object { $_[3] } | Measure-Object -Maximum).Maximum
            @{ Pass=($lfMax -ge 1.0); Detail=("{0} samples, eye travelled up to {1:f2} m, at most {2:f1} m from the car" -f $laE.Count, $lfMax, $lfCar) }
        } }
        @{ Kind='Script'; Name='any paused tyre-mark draw uses the world camera'; Script={
            param($ctx)
            $liN = 0; $liBad = 0
            foreach ($line in $ctx.LogLines) {
                if ($line -match '^\[paused-trail\] record=\d+ present=\d+ status=(\S+) .* nativeSourceMaxError=(\S+) sourceWorldMaxError=(\S+)') {
                    ++$liN; if ($Matches[1] -ne 'observed' -or [double]$Matches[2] -gt 1e-5 -or [double]$Matches[3] -gt 1e-5) { ++$liBad } }
            }
            @{ Pass=($liBad -eq 0); Detail=("{0} records, {1} off" -f $liN, $liBad) }
        } }
        @{ Kind='LogMatch'; Name='scene sources written'; Pattern='\[postfx-source\] present=\d+ unit=0 .*written=1' }
        @{ Kind='LogCount'; Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }
        @{ Kind='NewAsserts'; Name='no new assertions' }
    )
}
