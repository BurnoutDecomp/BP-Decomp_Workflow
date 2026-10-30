$case = & (Join-Path $PSScriptRoot 'AuthoredCase.ps1')
$case.Name = 'private_replay_source22e6735_boot_profile_world_drive_62173'
$case.OwnerDir = $PSScriptRoot
$case.Frames = $true
$case.Run.SkipIntro = $false
$case.Run.FrameEvery = 1000000000
$case.Run.MinFreeGB = 1.5
$case.Run.MaxLogMB = 128
$case.Run.AllowConcurrentGames = $true
$case.Run.Audio = $false
$case.Checks += @(
 @{ Kind='LogCount'; Name='real main title movie reached legal title-ready state'; Pattern='\[BootLegal\] stage -?\d+ -> 7'; Min=1; Max=1 }
 @{ Kind='LogCount'; Name='real profile serialization returned before BootProfile running'; Pattern='\[BootProfile\] stage 3 -> 4'; Min=1; Max=1 }
)
$case.Checks += @(
 @{Kind='LogCount'; Name='EA actual decoder prepared'; Pattern='\[Movie\] prepared .*EAFRANCHISE'; Min=1; Max=1}
 @{Kind='LogCount'; Name='Criterion actual decoder prepared'; Pattern='\[Movie\] prepared .*CRITERION'; Min=1; Max=1}
 @{Kind='LogCount'; Name='video outer event reached movie manager'; Pattern='GUI_OUT_UNEXPECTED.*(508|509)'; Max=0}
)
$case.Checks += @(
 @{ Kind='Script'; Name='both ordinary logo510 completions precede the legal title'; Script={
  param($ctx)
  $all=[string]::Join("`n",$ctx.LogLines)
  $ea=[regex]::Match($all,'(?im)^\[Movie\] prepared [^\r\n]*EAFRANCHISE[^\r\n]*')
  $cr=[regex]::Match($all,'(?im)^\[Movie\] prepared [^\r\n]*CRITERION[^\r\n]*')
  $title=[regex]::Match($all,'(?m)^\[BootLegal\] stage -?\d+ -> 7')
  $finish=@([regex]::Matches($all,'\[GuiModule\] video finished -> menu stream cleared, fed 510 to the flow\.'))
  $first=@($finish|Where-Object {$_.Index -gt $ea.Index -and $_.Index -lt $cr.Index})
  $second=@($finish|Where-Object {$_.Index -gt $cr.Index -and $_.Index -lt $title.Index})
  return @{Pass=($ea.Success -and $cr.Success -and $title.Success -and $ea.Index -lt $cr.Index -and $cr.Index -lt $title.Index -and $first.Count -eq 1 -and $second.Count -ge 1); Detail=('EA='+$ea.Index+' Criterion='+$cr.Index+' title='+$title.Index+' 510between='+$first.Count+' 510afterCriterion='+$second.Count)}
 } }
)
$case.DiagEnv = 'BRN_FRAME_DUMP_REQUEST=1'
$case.Setup = {
 param($ctx)
 $helper=Join-Path $ctx.Case.OwnerDir 'Capture.ps1'
 $args=@('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$helper+'"'),'-GameExe',('"'+(Join-Path $ctx.GameDir 'Burnout_PC.exe')+'"'),'-RunDir',('"'+$ctx.RunDir+'"'))
 Start-Process pwsh -WindowStyle Hidden -PassThru -ArgumentList $args -RedirectStandardOutput (Join-Path $ctx.RunDir 'capture.console.log') -RedirectStandardError (Join-Path $ctx.RunDir 'capture.stderr.log')
}
$case
