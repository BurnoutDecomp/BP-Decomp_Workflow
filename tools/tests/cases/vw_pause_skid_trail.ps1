# vw_pause_skid_trail -- PAUSE WITH FRESH TYRE MARKS ON THE ROAD: do they stay glued to the road under the moving
# pause camera?
#
# Upstream's skid-hold scenario (PlaytestRenderSkidHoldLive: teleport, turn + handbrake lays a strip, the car rests),
# then the Driver Details pause while the strip is fresh and the tyre smoke still hangs in the air, held for ~19 s,
# then resumed.
# On the console the pause runs ArbStateCrashNav (state 3) with the ICE pause-playlist camera, which keeps moving while
# the sim clock is held; the trail renderer and the world must both draw with that one camera (a28161fa witness,
# f74fa5c1 / cede4e0c fix). Witnesses:
#   BRN_PAUSED_TRAIL_DIAG  [paused-trail]  original TrailRenderer matrix vs native VS constants vs world view-projection
#   BRN_CRASHCAM_DIAG      [pause-cam]     the arbitrator edges and the pause camera eye samples
#   BRN_SKID_PROBE         [skid]          the strip actually laid (SkidMarksEnabled per surface)
#   BRN_TRAIL_HEIGHT_DIAG  [trailquad]     the laid strip's quads at the trail draw
#   BRN_POSTFX_SOURCE_DUMP frames\inputs\source_<present>.bmp  the scene under the pause menu, every 30 presents
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case vw_pause_skid_trail -Slot 4
@{
    Name = 'vw_pause_skid_trail'
    Area = 'vfx'
    Bug = 'Paused tyre marks must keep their world place under the moving pause camera (trail matrix == world camera).'
    Frames = $true
    ProfileFixture = 'rival_hunt_profile.sav'
    Run = @{
        Drive = $true
        DriveDelay = 12
        MotionProbe = $true
        SkipIntro = $true
        AcceptGap = 1.0
        Teleport = '3040.7,-5.8,-1937.9,180'
        SteerScript = '0:none,4:right50,5.5:none'
        ThrottleScript = '0:accel,4:accel+handbrake,5.5:brake,8:handbrake'
        PauseAt = '17.5'
        PauseTarget = 'driver'
        UnpauseAt = '38'
        MaxSeconds = 70
        FrameEvery = 30
    }
    DiagEnv = 'BRN_PAUSED_TRAIL_DIAG=1,BRN_CRASHCAM_DIAG=1,BRN_SCREEN_DIAG=1,BRN_SKID_PROBE=1,BRN_TRAIL_HEIGHT_DIAG=1,BRN_FRAME_DUMP_MAX=200,BRN_POSTFX_SOURCE_DUMP=1,BRN_POSTFX_SOURCE_START=2100,BRN_POSTFX_SOURCE_EVERY=30,BRN_POSTFX_SOURCE_MAX=70'
    Checks = @(
        @{ Kind='Mark'; Name='reached DRIVING'; Phase='DRIVING' }
        @{ Kind='LogMatch'; Name='a skid strip was laid'; Pattern='\[trailquad\].*type=\d+ emitter=.*laid=[\d.]+ now=[\d.]+' }
        @{ Kind='LogMatch'; Name='entered Driver Details'; Pattern="\[screen\] ENTER 'CN_D_DETAIL" }
        @{ Kind='LogCount'; Name='the pause entered the crash-nav camera state'
           Pattern='\[pause-cam\] arbitrator NORMAL -> CRASH_NAV_ICE_CAMERAS \(crashNavShown 1'; Min=1 }
        @{ Kind='Script'; Name='the paused tyre-mark draw uses the world camera (trail VS constants == source == world VP on every record)'; Script={
            param($ctx)
            $laRec = @(); $lCams = @{}; $lsCur = $null; $lsWorld = ''
            foreach ($line in $ctx.LogLines) {
                if ($line -match '^\[paused-trail\] record=(\d+) present=\d+ status=(\S+) .* nativeSourceMaxError=(\S+) sourceWorldMaxError=(\S+)') {
                    $laRec += ,@($Matches[2], [double]$Matches[3], [double]$Matches[4])
                    if ($lsCur) { $lCams[$lsWorld] = 1 }
                    $lsCur = $Matches[1]; $lsWorld = ''
                } elseif ($line -match '^\[paused-trail\] record=(\d+) row=\d+ .* world=(\[[^\]]*\])') {
                    $lsWorld += $Matches[2]
                }
            }
            if ($lsCur) { $lCams[$lsWorld] = 1 }
            if ($laRec.Count -lt 3) { return @{ Pass=$false; Detail=("{0} [paused-trail] records (need >= 3: tyre marks drawn while paused)" -f $laRec.Count) } }
            $liBad = @($laRec | Where-Object { $_[0] -ne 'observed' -or $_[1] -gt 1e-5 -or $_[2] -gt 1e-5 }).Count
            $lfNS = ($laRec | ForEach-Object { $_[1] } | Measure-Object -Maximum).Maximum
            $lfSW = ($laRec | ForEach-Object { $_[2] } | Measure-Object -Maximum).Maximum
            @{ Pass=($liBad -eq 0 -and $lCams.Count -ge 2)
               Detail=("{0} records, {1} off; max native-source {2:g3}, source-world {3:g3}; {4} distinct paused cameras" -f $laRec.Count, $liBad, $lfNS, $lfSW, $lCams.Count) }
        } }
        @{ Kind='LogCount'; Name='the arbitrator came back to NORMAL after the unpause'
           Pattern='\[pause-cam\] arbitrator CRASH_NAV_ICE_CAMERAS -> NORMAL \(crashNavShown 0'; Min=1 }
        @{ Kind='LogCount'; Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }
        @{ Kind='NewAsserts'; Name='no new assertions' }
    )
}
