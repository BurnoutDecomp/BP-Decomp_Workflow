# vw_bloom_moving_1440 -- upstream's moving post-FX case (b5-decomp\tests\PlaytestPostFxMovingLive.ps1)
# at a 2560x1440 native scene, capture on. The scene size comes from config.ini beside the exe, so
# this case only runs on a PRIVATE slot (-Slot n, n > 0) whose config.ini it writes in Setup; slot 0's
# build\game\config.ini is shared by every lane and is never touched. StartPresent 2100 puts the
# capture window inside the straight at ~30 m/s on this box (VSync 60: upstream's 5000 is past the
# end of the 65 s run here).
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case vw_bloom_moving_1440 -Slot 7
param([int]$Width = 2560, [int]$Height = 1440, [int]$StartPresent = 2100)
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$case = & (Join-Path $root 'b5-decomp\tests\PlaytestPostFxMovingLive.ps1') -Width $Width -Height $Height -Capture -StartPresent $StartPresent
$case.Name = 'vw_bloom_moving_' + $Height
$case.Setup = {
    param($ctx)
    if ($ctx.Slot -le 0) { throw 'vw_bloom_moving_* writes the slot config.ini: run it with -Slot n (n > 0).' }
    $slotDir = Join-Path $ctx.Root ('build\game_slots\' + $ctx.Slot)
    New-Item -ItemType Directory -Force $slotDir | Out-Null
    $config = Join-Path $slotDir 'config.ini'
    $text = "[Display]`r`nWidth=$($ctx.Case.NativeWidth)`r`nHeight=$($ctx.Case.NativeHeight)`r`nAdapterIndex=0`r`nVSync=1`r`nDecoupleSimulation=1`r`nFullscreen=0`r`n" +
            "[Settings]`r`nAlphaToCoverage=1`r`nAntiAliasing=0`r`nEnvironmentMap=1`r`nEnvironmentMap30Hz=1`r`nCoronas=1`r`nSunCorona=1`r`n"
    [IO.File]::WriteAllText($config, $text, [Text.Encoding]::ASCII)
    [IO.File]::WriteAllText((Join-Path $ctx.RunDir 'config.ini'), $text, [Text.Encoding]::ASCII)
    $null
}
$case
