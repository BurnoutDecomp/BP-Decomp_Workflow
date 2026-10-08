# vw_crashcam_bars -- the signature-jump camera draws the 0.15 letterbox and removes it (lane CRASHCAM).
#
# Wraps upstream's b5-decomp\tests\PlaytestCinematicBarsLive.ps1. That case teleports to
# 3013.2,-9.0,-839.3 and drives north under throttle, trusting the car to find the superjump ramp
# 545 m later; on exe 15:29 the car passed z=-294 seven metres west of the ramp (x 3019.6) and
# never jumped (20261008_172748: no OnJumpStart, no bars). Its first-time variant fixes the
# approach with the staged sweep (far placement, then the measured shot onto the ramp), but its
# profile fixture scratch\PLAYTEST_1005\first-time-jump-profile.sav is not on this box.
# This wrapper keeps the upstream checks and uses the first-time variant's staged approach with
# the fixture that is here (rival_hunt_profile.sav). Nothing in the game changes.
#
# The frame check runs tools\tests\tools\VW_CRASHCAM_bars.py instead of upstream's
# playtest_cinematic_bars_frames.py: upstream's bottom-band window sits on the PC debug text crawl
# (rows ~632..684 of 720), so a frame with an exact 108-row letterbox scored 0 bar frames
# (20261008_173009: upstream script 0, this script 78 frames, both bands exactly 108 rows).
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case vw_crashcam_bars
$root = Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$laCase = & (Join-Path $root 'b5-decomp\tests\PlaytestCinematicBarsLive.ps1')
$laCase.Name = 'vw_crashcam_bars'
$laCase.BarFrameScript = Join-Path $root 'tools\tests\tools\VW_CRASHCAM_bars.py'
$laCase.Run.Remove('Teleport')
$laCase.Run.CrashSweep = '3013.2,-9.0,-839.3'
$laCase.Run.CrashSweepShots = '1.7:0,3026.55/-8.9/-294.9/1.45:55.8'
$laCase.Run.CrashSweepSettle = 900
$laCase.Run.ThrottleScript = '0:accel'
$laCase.Run.MaxSeconds = 110
$laCase.DiagEnv = $laCase.DiagEnv + ',BRN_CAMPOOL_DIAG=1'
$laCase.Checks += @(
    @{Kind='LogCount'; Name='staged signature-jump approach actually fired'; Pattern='\[sweep\] shot 1/2'; Min=1}
    @{Kind='LogCount'; Name='jump approach seat remains valid'; Pattern='SEAT BAD shot 1'; Max=0}
    @{Kind='LogMatch'; Name='actual jump approach is seated on the road'; Pattern='\[sweep\] seat ok shot 1'}
    @{Kind='LogCount'; Name='no camera pool ran out'; Pattern='Ran out of slots'; Max=0}
    @{Kind='Script'; Name='both letterbox bands are exactly 0.15 of the frame (108 rows at 720)'; Script={
        param($ctx)
        $laOut = & py -3 $ctx.Case.BarFrameScript (Join-Path $ctx.RunDir 'frames') 2>&1
        try { $lrResult = ("$laOut" | ConvertFrom-Json) }
        catch { return @{Pass=$false; Detail="frame measurement failed: $laOut"} }
        $lsTop = @($lrResult.top_band_rows) -join ','
        $lsBottom = @($lrResult.bottom_band_rows) -join ','
        @{Pass=($lrResult.bar_frames -ge 2 -and $lsTop -eq '108' -and $lsBottom -eq '108'); Detail="top band rows {$lsTop}, bottom band rows {$lsBottom} over $($lrResult.bar_frames) bar frames"}
    }}
)
$laCase
