$owner=$PSScriptRoot
$stage=Get-Content -Raw (Join-Path $owner 'STAGING.json')|ConvertFrom-Json
@{
 Name='environment24_cloud_layers_irradiance_channels_62181'
 OwnerDir=$owner
 Area='debug-menu'
 Bug='Twenty-four pending original cloud and irradiance controls need separate native consumer positive/negative/restore witnesses.'
 Frames=$true
 ProfileFixture=(Join-Path $owner 'Profile.seed.sav')
 ProfileFixtureSha256=$stage.profile_seed_sha256
 Run=@{
  Drive=$true;MotionProbe=$true;TitleStart=$true;SkipIntro=$true;AcceptGap=1.0
  MaxSeconds=240;MinFreeGB=1.25;MaxLogMB=64;NoAssertRelease=$true
  StrictGameOwnership=$true;AllowConcurrentGames=$true;Audio=$false
  DriveDelay=2.0;ThrottleScript='0:accel,6:brake+handbrake';FrameEvery=1000000000
 }
 DiagEnv='BRN_DEBUG_UI_TRACE=1,BRN_FRAME_DUMP_REQUEST=1,BRN_FRAME_DUMP_MAX=43'
 Setup={
  param($ctx)
  $scope=Get-Content -Raw (Join-Path $ctx.Case.OwnerDir 'SCOPE.json')|ConvertFrom-Json
  $stage=Get-Content -Raw (Join-Path $ctx.Case.OwnerDir 'STAGING.json')|ConvertFrom-Json
  if($ctx.Slot -ne 62181 -or !$ctx.UsesPrivateStage -or $ctx.GameDir -ine $stage.exe_dir -or $ctx.WorkingDirectory -ine $stage.cwd){throw 'Exact private Environment21 stage required'}
  if(Test-Path $ctx.GameLog){throw 'Fresh private game log required'}
  $commands=@('component "Environment"')
  foreach($c in @($scope.controls)+@($scope.context_aliases)){$commands+=('alias '+$c.alias+' "'+$c.lookup_path+'"')}
  foreach($c in @($scope.controls)+@($scope.context_aliases)){$commands+=('alias '+$c.alias);$commands+=$c.alias;$commands+=('alias '+$c.alias)}
  $commands+='bind F2 exec b2.cfg'
  [IO.File]::WriteAllLines((Join-Path $ctx.WorkingDirectory 'b1.cfg'),$commands,[Text.Encoding]::ASCII)
  $driver=Join-Path $ctx.Case.OwnerDir 'Driver.ps1'
  $args=@('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$driver+'"'),'-RunDir',('"'+$ctx.RunDir+'"'),'-ExpectedSlotExe',('"'+(Join-Path $ctx.GameDir 'Burnout_PC.exe')+'"'),'-GameLog',('"'+$ctx.GameLog+'"'),'-Slot','62181')
  $process=Start-Process pwsh -WindowStyle Hidden -PassThru -ArgumentList $args -RedirectStandardOutput (Join-Path $ctx.RunDir 'driver.console.log') -RedirectStandardError (Join-Path $ctx.RunDir 'driver.stderr.log')
  $until=[DateTime]::UtcNow.AddSeconds(12)
  while(!(Test-Path (Join-Path $ctx.RunDir 'DRIVER_READY.json'))){if($process.HasExited -or [DateTime]::UtcNow -gt $until){throw 'Driver did not establish scoped prelaunch events'};Start-Sleep -Milliseconds 50}
  $ready=Get-Content -Raw (Join-Path $ctx.RunDir 'DRIVER_READY.json')|ConvertFrom-Json
  if($ready.status -cne 'ready' -or $ready.slot -ne 62181 -or $ready.driver_pid -ne $process.Id -or $ready.event_count -ne 256){throw 'Wrong scoped event owner'}
  return $process
 }
 Checks=@(
  @{Kind='NewAsserts';Name='no new assertions'}
  @{Kind='LogCount';Name='no exceptions';Pattern='\[EXCEPTION\]';Max=0}
  @{Kind='Mark';Name='normal title route reached DRIVING';Phase='DRIVING'}
  @{Kind='Script';Name='exact selected restorable controls native P/N/R and cleanup complete; pixels require independent review';Script={
   param($ctx)
   $p=Join-Path $ctx.RunDir 'driver-result.json'
   if(!(Test-Path $p)){return @{Pass=$false;Detail='No driver result'}}
   $r=Get-Content -Raw $p|ConvertFrom-Json
   return @{Pass=($r.status -ceq 'machine_complete_awaiting_independent_pixels' -and $r.eligible_control_count -eq 13 -and $r.frames.Count -eq (3*$r.eligible_control_count+4) -and $r.phases.Count -eq (3*$r.eligible_control_count+3) -and $r.terminal_restore_verified -eq $true -and $r.exe_sha256 -ceq '474ba5bb1a72efe0f06ccf71aae98b1b332ca7399715af83da2fa4c4d2666a44');Detail=('status='+$r.status+' frames='+$r.frames.Count+' phases='+$r.phases.Count+' site_credit=0')}
  }}
 )
}
