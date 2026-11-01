param([switch]$Execute)
$ErrorActionPreference='Stop';$package=$PSScriptRoot
if(!$Execute){& (Join-Path $package 'Preflight.ps1')|ConvertTo-Json -Depth 8;exit 0}
$stage=Get-Content -Raw (Join-Path $package 'STAGING.json')|ConvertFrom-Json
$pins=Get-Content -Raw (Join-Path $package 'SOURCE_PINS.json')|ConvertFrom-Json
$runDir=Join-Path $package ('runs/gui62209_'+[DateTime]::UtcNow.ToString('yyyyMMdd_HHmmss')+'_'+[Guid]::NewGuid().ToString('N'))
$null=& (Join-Path $package 'Preflight.ps1') -AtRun -RunDir $runDir
$oldRun=$env:NATIVE_SCENE_RUN_CASE_PATH;$oldFlow=$env:NATIVE_SCENE_FLOW_RUN_PATH
try{
 $env:NATIVE_SCENE_RUN_CASE_PATH=$pins.runner_binding.workflow_helpers.run_case.path
 $env:NATIVE_SCENE_FLOW_RUN_PATH=$pins.runner_binding.workflow_helpers.flow_run.path
 & $pins.runner_binding.workflow_helpers.run_case.path -Case (Join-Path $package 'Case.ps1') -RunDir $runDir -RunsRoot (Join-Path $package 'runs') -GameDir $stage.exe_dir -WorkingDirectory $stage.cwd -Slot 62209 -LockTimeoutSec 1
 $code=$LASTEXITCODE
}finally{
 if($null -eq $oldRun){Remove-Item Env:NATIVE_SCENE_RUN_CASE_PATH -ErrorAction SilentlyContinue}else{$env:NATIVE_SCENE_RUN_CASE_PATH=$oldRun}
 if($null -eq $oldFlow){Remove-Item Env:NATIVE_SCENE_FLOW_RUN_PATH -ErrorAction SilentlyContinue}else{$env:NATIVE_SCENE_FLOW_RUN_PATH=$oldFlow}
}
exit $code
