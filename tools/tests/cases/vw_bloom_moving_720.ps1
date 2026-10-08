# vw_bloom_moving_720 -- the 1280x720 control for vw_bloom_moving_1440 (same scenario, same capture
# window, same private-slot config.ini rule).
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case vw_bloom_moving_720 -Slot 7
& (Join-Path $PSScriptRoot 'vw_bloom_moving_1440.ps1') -Width 1280 -Height 720
