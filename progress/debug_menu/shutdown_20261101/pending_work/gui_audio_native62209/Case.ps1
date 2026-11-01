$ErrorActionPreference='Stop'
if(!(Test-Path -LiteralPath (Join-Path $PSScriptRoot 'STAGING.json'))){throw 'Root must materialize reviewed STAGING.json before native execution.'}
$stage=Get-Content -Raw (Join-Path $PSScriptRoot 'STAGING.json')|ConvertFrom-Json
. (Join-Path $PSScriptRoot 'CaseHelpers.ps1')
@{
 Name='gui_audio_normal_navigation_62209';OwnerDir=$PSScriptRoot
 Area='gui-native-continuation';Bug='Current-save normal boot and pause-map navigation after original GUI audio callback restoration'
 Frames=$true;ProfileFixture=$stage.profile_fixture;ProfileFixtureSha256=$stage.profile_sha256
 Run=(New-BrnGuiAudioRunArguments)
 DiagEnv='BRN_SCREEN_DIAG=1,BRN_FRAME_DUMP_REQUEST=1,BRN_FRAME_DUMP_MAX=8'
 Setup={param($ctx)
  $package=$ctx.Case.OwnerDir;$stage=Get-Content -Raw (Join-Path $package 'STAGING.json')|ConvertFrom-Json
  $pins=Get-Content -Raw (Join-Path $package 'SOURCE_PINS.json')|ConvertFrom-Json
  if($env:NATIVE_SCENE_RUN_CASE_PATH -cne $pins.runner_binding.workflow_helpers.run_case.path -or $env:NATIVE_SCENE_FLOW_RUN_PATH -cne $pins.runner_binding.workflow_helpers.flow_run.path){throw 'Run only through the pinned retry03 helper pair'}
  if($ctx.Slot -ne 62209 -or !$ctx.UsesPrivateStage -or $ctx.GameDir -ine $stage.exe_dir -or $ctx.WorkingDirectory -ine $stage.cwd){throw 'Wrong GUI62209 private binding'}
  $null=& (Join-Path $package 'Preflight.ps1') -AtRun -RunDir $ctx.RunDir
  . (Join-Path $package 'PathGuards.ps1')
  $identity=Assert-BrnPrivateProfile $stage.profile 'private GUI62209 profile'
  if($identity.status -cne 'regular_single_link_private_file' -or $identity.sha256 -cne $stage.profile_sha256){throw 'Private profile not the current4e fixture'}
  $identity|ConvertTo-Json|Set-Content (Join-Path $ctx.RunDir 'PRIVATE_PROFILE_BINDING.json') -Encoding utf8
  if(Test-Path -LiteralPath $ctx.GameLog){throw 'Owned game log must be fresh'}
  $args=@('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+(Join-Path $package 'Driver.ps1')+'"'),'-GameExe',('"'+(Join-Path $ctx.GameDir 'Burnout_PC.exe')+'"'),'-RunDir',('"'+$ctx.RunDir+'"'))
  $proc=Start-Process pwsh -WindowStyle Hidden -PassThru -ArgumentList $args -RedirectStandardOutput (Join-Path $ctx.RunDir 'driver.console.log') -RedirectStandardError (Join-Path $ctx.RunDir 'driver.stderr.log')
  $until=[DateTime]::UtcNow.AddSeconds(12);$ready=Join-Path $ctx.RunDir 'DRIVER_READY.json'
  while(!(Test-Path -LiteralPath $ready)){if($proc.HasExited -or [DateTime]::UtcNow -gt $until){throw 'GUI62209 capture helper not ready'};Start-Sleep -Milliseconds 50}
  $r=Get-Content -Raw $ready|ConvertFrom-Json
  if($r.driver_pid -ne $proc.Id -or $r.slot -ne 62209 -or $r.max_frames -ne 8){throw 'Wrong driver readiness identity'}
  return $proc
 }
 Checks=@(
  @{Kind='NewAsserts';Name='no new assertions'}
  @{Kind='LogCount';Name='zero raw assertions/exceptions';Pattern='\[ASSERT(?:\s+\d+)?\]|\[EXCEPTION\]';Max=0}
  @{Kind='Mark';Name='reached DRIVING';Phase='DRIVING'}
  @{Kind='LogCount';Name='real EA branding entered';Pattern="\[BootVideos\] play 'EAFranchise'";Min=1;Max=1}
  @{Kind='LogCount';Name='real Criterion branding entered';Pattern="\[BootVideos\] play 'Criterion'";Min=1;Max=1}
  @{Kind='LogCount';Name='real map screen entered';Pattern="\[screen\] ENTER 'CN_MAP_MAIN'";Min=1}
  @{Kind='Script';Name='current save, bounded captures, owned return and completion';Script={param($ctx);. (Join-Path $ctx.Case.OwnerDir 'CaseHelpers.ps1');Test-BrnGuiAudioNativeReceipts $ctx.RunDir}}
 )
}
