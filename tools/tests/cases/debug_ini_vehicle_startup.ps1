# Start-crash regression: automatic Race Car page activation by vehicle LOD INI settings.
# Run only in an isolated slot; its config is copied explicitly because slot staging omits it.
$lCase = & (Join-Path $PSScriptRoot 'baseline_boot_drive.ps1')
$lCase.Name = 'debug_ini_vehicle_startup'
$lCase.Area = 'debug-menu'
$lCase.Bug = 'INI-activated Race Car diagnostics read velocity before player attachment'
$lCase.Run.MaxSeconds = 180
$lCase.DiagEnv = 'BRN_DEBUG_UI_TRACE=1'
$lCase.Setup = {
    param($ctx)
    if ($ctx.Slot -le 0) { throw 'This case requires an isolated slot.' }
    $lSlotDir = Join-Path $ctx.Root ("build/game_slots/" + $ctx.Slot)
    New-Item -ItemType Directory -Force $lSlotDir | Out-Null
    $lConfig = Join-Path $lSlotDir 'config.ini'
    if (Test-Path -LiteralPath $lConfig) {
        Copy-Item -LiteralPath $lConfig -Destination (Join-Path $ctx.RunDir 'slot_config.before.ini')
    }
    Copy-Item -LiteralPath (Join-Path $ctx.Root 'build/game/config.ini') -Destination $lConfig -Force
    Copy-Item -LiteralPath $lConfig -Destination (Join-Path $ctx.RunDir 'config.used.ini')
}
$lCase.Checks += @(
    @{ Kind='LogCount'; Name='Race Car page was activated by startup settings';
       Pattern='\[debug-component\] path="/?Race Car Entity" request=engine controls=1'; Min=1 }
    @{ Kind='LogCount'; Name='all five configured vehicle LODs were applied';
       Pattern='\[debug-ini\] applied graphics/vehicles\.\.\./lods\.\.\./quality lod [0-4]='; Min=5 }
    @{ Kind='LogCount'; Name='no invalid-player or unattached-car assertion';
       Pattern='\[ASSERT \d+\].*(leActiveRaceCarIndex|IsAttached\(\))'; Max=0 }
)
return $lCase
