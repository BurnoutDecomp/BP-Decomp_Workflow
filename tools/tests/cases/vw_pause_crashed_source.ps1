# vw_pause_crashed_source -- upstream's crashed-car pause (MenusPauseCameraCrashedLive: drive, crash, Driver Details
# pause at DRIVING+30 s, back out at +50 s), plus the two things needed to LOOK at the paused car under the moving
# road-runner pause camera:
#   BRN_POSTFX_SOURCE_DUMP  frames\inputs\source_<present>.bmp  the scene the final composite reads (no pause menu over
#                           it), every 60 presents from present 2700
#   BRN_PAUSE_DAMAGE_DIAG   [pause-damage]  the skin / detached-part hashes must not change while paused
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case vw_pause_crashed_source -Slot 4
$case = & (Join-Path $PSScriptRoot '..\..\..\b5-decomp\tests\MenusPauseCameraCrashedLive.ps1')
$case.Name = 'vw_pause_crashed_source'
$case.DiagEnv += ',BRN_PAUSE_DAMAGE_DIAG=1,BRN_FRAME_DUMP_MAX=200,BRN_POSTFX_SOURCE_DUMP=1,BRN_POSTFX_SOURCE_START=2700,BRN_POSTFX_SOURCE_EVERY=60,BRN_POSTFX_SOURCE_MAX=45'
$case.CasePathForFrames = (Join-Path $PSScriptRoot '..\..\..\b5-decomp\tests\MenusPauseCameraCrashedLive.ps1')
$case.Checks += @(
    @{ Kind='Script'; Name='the paused damage state does not change while the pause camera flies'; Script={
        param($ctx)
        $laSig = @()
        foreach ($line in $ctx.LogLines) {
            if ($line -match '^\[pause-damage\] paused 1 parts (\d+) detached (\d+) wheels (\d+) skin (\d+) poses (\d+)') { $laSig += "$($Matches[1]):$($Matches[2]):$($Matches[3]):$($Matches[4]):$($Matches[5])" }
        }
        $liDistinct = @($laSig | Select-Object -Unique).Count
        @{ Pass=($laSig.Count -ge 3 -and $liDistinct -eq 1); Detail=("{0} paused samples, {1} distinct damage states ({2})" -f $laSig.Count, $liDistinct, ($laSig | Select-Object -First 1)) }
    } }
    @{ Kind='LogMatch'; Name='scene sources written while paused'; Pattern='\[postfx-source\] present=\d+ unit=0 .*written=1' }
)
$case
