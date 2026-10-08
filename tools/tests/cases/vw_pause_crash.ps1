# vw_pause_crash -- PAUSE AFTER A REAL CRASH: does everything stay put and agree with the paused camera?
#
# Upstream's PlaytestPauseDeformationLive (253ddee3) scenario -- a real wall impact, then the Driver Details pause --
# held longer and with every pause witness armed at once:
#   BRN_PAUSE_DAMAGE_DIAG  [pause-damage]  skin / detached-part hashes per paused frame (253ddee3)
#   BRN_POSTFX_SOURCE_DUMP frames\inputs\source_<present>.bmp  the scene the final composite reads, before the pause
#                                          menu, so the crushed car and its parts can be looked at under the pause camera
#   BRN_CRASHCAM_DIAG      [pause-cam]     the arbitrator's CRASH_NAV edges and the pause camera's eye samples
# The pause camera after a crash is the road-runner fly-by (ArbStateCrashNav state 3), so it MOVES while the sim is
# held; the crushed car and detached parts must not change while it does. Tyre marks: vw_pause_skid_trail.
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case vw_pause_crash -Slot 4
$case = & (Join-Path $PSScriptRoot '..\..\..\b5-decomp\tests\PlaytestPauseDeformationLive.ps1')
$case.Name = 'vw_pause_crash'
$case.Bug = 'After a crash, the paused world (crushed car, detached parts, tyre marks) must stay put and agree with the moving pause camera.'
$case.Run.UnpauseAt = '24'
$case.Run.MaxSeconds = 75
$case.DiagEnv = 'BRN_PAUSE_DAMAGE_DIAG=1,BRN_CRASHCAM_DIAG=1,BRN_SCREEN_DIAG=1,BRN_FRAME_DUMP_MAX=200,BRN_POSTFX_SOURCE_DUMP=1,BRN_POSTFX_SOURCE_START=1200,BRN_POSTFX_SOURCE_EVERY=60,BRN_POSTFX_SOURCE_MAX=40'
$case.Checks += @(
    @{ Kind='LogCount'; Name='the pause entered the crash-nav camera state'
       Pattern='\[pause-cam\] arbitrator NORMAL -> CRASH_NAV_ICE_CAMERAS \(crashNavShown 1'; Min=1 }
    @{ Kind='Script'; Name='the pause camera moves while the sim is held (pause-cam eye travels >= 1 m)'; Script={
        param($ctx)
        $laE = @()
        foreach ($line in $ctx.LogLines) {
            # t 0 is the Prepare frame (the fly-by produces its first camera on the next).
            if ($line -match '\[pause-cam\] sample t (\S+) .* stateEye \(([^,]+), ([^,]+), ([^)]+)\)' -and [double]$Matches[1] -gt 0.0) { $laE += ,@([double]$Matches[2], [double]$Matches[3], [double]$Matches[4]) }
        }
        if ($laE.Count -lt 3) { return @{ Pass=$false; Detail=("{0} pause-cam samples" -f $laE.Count) } }
        $lfMax = 0.0
        foreach ($a in $laE) { $d = [Math]::Sqrt(($a[0]-$laE[0][0])*($a[0]-$laE[0][0]) + ($a[1]-$laE[0][1])*($a[1]-$laE[0][1]) + ($a[2]-$laE[0][2])*($a[2]-$laE[0][2])); if ($d -gt $lfMax) { $lfMax = $d } }
        @{ Pass=($lfMax -ge 1.0); Detail=("{0} samples, eye travelled up to {1:f2} m" -f $laE.Count, $lfMax) }
    } }
)
$case
