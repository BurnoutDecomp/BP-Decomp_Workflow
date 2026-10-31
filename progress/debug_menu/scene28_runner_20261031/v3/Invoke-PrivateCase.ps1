[CmdletBinding()]
param([switch]$Execute)

$ErrorActionPreference = 'Stop'
$package = $PSScriptRoot
$stagePath = Join-Path $package 'STAGING.json'
$pins = Get-Content -Raw -LiteralPath (Join-Path $package 'SOURCE_PINS.json') | ConvertFrom-Json

if (-not $Execute) {
    $preflight = & (Join-Path $package 'Preflight.ps1')
    $preflight | ConvertTo-Json -Depth 8
    if ($preflight.pass) { exit 0 } else { exit 1 }
}

if (-not (Test-Path -LiteralPath $stagePath -PathType Leaf)) {
    throw 'Execution requires a Root-created private STAGING.json; this package contains only the reviewed template.'
}
$stage = Get-Content -Raw -LiteralPath $stagePath | ConvertFrom-Json
$stamp = [DateTime]::UtcNow.ToString('yyyyMMdd_HHmmss') + '_' + [Guid]::NewGuid().ToString('N')
$runsRoot = Join-Path $package 'runs'
$runDir = Join-Path $runsRoot ('native_scene_batch_62190_' + $stamp)
if (Test-Path -LiteralPath $runDir) { throw 'Refusing to reuse an existing run directory.' }

$preflight = & (Join-Path $package 'Preflight.ps1') -AtRun -RunDir $runDir -StagePath $stagePath
$preflight | ConvertTo-Json -Depth 8
if (-not $preflight.pass) { throw ('prelaunch static preflight failed: ' + ($preflight.problems -join '; ')) }

$oldRunCase = $env:NATIVE_SCENE_RUN_CASE_PATH
$oldFlowRun = $env:NATIVE_SCENE_FLOW_RUN_PATH
try {
    $env:NATIVE_SCENE_RUN_CASE_PATH = [string]$pins.runner_binding.workflow_helpers.run_case.path
    $env:NATIVE_SCENE_FLOW_RUN_PATH = [string]$pins.runner_binding.workflow_helpers.flow_run.path
    $runCase = [string]$pins.runner_binding.workflow_helpers.run_case.path
    & $runCase -Case (Join-Path $package 'Case.ps1') `
        -RunDir $runDir `
        -RunsRoot $runsRoot `
        -GameDir ([string]$stage.exe_dir) `
        -WorkingDirectory ([string]$stage.cwd) `
        -Slot 62190
    $exitCode = $LASTEXITCODE
} finally {
    if ($null -eq $oldRunCase) { Remove-Item Env:NATIVE_SCENE_RUN_CASE_PATH -ErrorAction SilentlyContinue } else { $env:NATIVE_SCENE_RUN_CASE_PATH = $oldRunCase }
    if ($null -eq $oldFlowRun) { Remove-Item Env:NATIVE_SCENE_FLOW_RUN_PATH -ErrorAction SilentlyContinue } else { $env:NATIVE_SCENE_FLOW_RUN_PATH = $oldFlowRun }
}
exit $exitCode
