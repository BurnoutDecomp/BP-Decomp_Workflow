# vw_bloom_moving_long_1440 -- the moving post-FX scenario of vw_bloom_moving_1440 with a LONGER pixel
# window: 48 consecutive final frames and 24 aligned scene/bloom source pairs (every 2nd present),
# starting on the straight at speed and running into the first steer. Same private-slot config.ini
# rule as vw_bloom_moving_1440 (run with -Slot n, n > 0).
#
# The pixel verdict is VW_BLOOM_chain_check.py over the dumped pairs: every dumped bloom buffer is
# recomputed from its own dumped scene source with the console's bloom arithmetic (2x2 bilinear
# box taps at +-1 source texel, half-texel offset by the sampled target, (x - t) * x bright pass
# with the 0.25/(1-t) rescale, five-tap separable blur) and compared, and the temporal flicker of
# the bloom buffer is scored against the flicker of its own source.
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case vw_bloom_moving_long_1440 -Slot 7
param([int]$Width = 2560, [int]$Height = 1440, [int]$StartPresent = 2050)
$case = & (Join-Path $PSScriptRoot 'vw_bloom_moving_1440.ps1') -Width $Width -Height $Height -StartPresent $StartPresent
$case.Name = 'vw_bloom_moving_long_' + $Height
$case.DiagEnv = "BRN_CAMERA_TRACE=1,BRN_FRAME_DUMP_ARM=0,BRN_FRAME_DUMP_START=$StartPresent,BRN_FRAME_DUMP_MAX=48," +
                "BRN_POSTFX_SOURCE_DUMP=1,BRN_POSTFX_SOURCE_START=$StartPresent,BRN_POSTFX_SOURCE_EVERY=2,BRN_POSTFX_SOURCE_MAX=24"
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$case.ChainChecker = Join-Path $root 'tools\tests\tools\VW_BLOOM_chain_check.py'
$keep = @($case.Checks | Where-Object { $_.Name -in @('no new assertions','no exceptions','reached driving',
    'requested native scene target is live','ordinary driving moved the car') })
$case.Checks = $keep + @(
    @{Kind='LogCount';Name='24 aligned bloom pairs';Pattern='^\[postfx-source\] present=\d+ unit=1 .*written=1 ';Min=24;Max=24}
    @{Kind='Script';Name='bloom buffer == console bloom arithmetic over its own scene, every pair';Script={
        param($ctx)
        $py = 'C:\Python310\python.exe'
        $env:PYTHONUTF8 = '1'; $env:PYTHONIOENCODING = 'utf-8'
        $out = & $py -I $ctx.Case.ChainChecker $ctx.FrameDir 2>&1 | Out-String
        [IO.File]::WriteAllText((Join-Path $ctx.RunDir 'chain_check.txt'), $out)
        $pass = $out -match '(?m)^VERDICT PASS'
        @{Pass=$pass;Detail=(($out -split "`n" | Where-Object { $_ -match '^(VERDICT|SUMMARY)' }) -join ' | ').Trim()}
    }}
)
$case
