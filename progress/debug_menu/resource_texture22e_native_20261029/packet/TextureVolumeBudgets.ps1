function Get-TextureVolumeRequirement([object]$Budget,[string]$Volume,[bool]$StagePending) {
  if($Volume -cnotin @('C','D')){throw 'Unknown Texture budget volume.'}
  $spec=$Budget.volumes.PSObject.Properties[$Volume].Value
  if($null -eq $spec -or [long]$spec.floor_bytes -ne 2147483648){throw 'Texture untouched volume floor is not2GiB.'}
  $fields=if($Volume -ceq 'D'){@('payload_bytes','metadata_bytes','profile_config_bytes','slot_log_bytes','stage_sidecar_bytes')}else{@('frame_bytes','run_log_sidecar_bytes','transient_bytes')}
  $expected=[long]$spec.floor_bytes
  foreach($name in $fields){
    if($null -eq $spec.PSObject.Properties[$name] -or [long]$spec.PSObject.Properties[$name].Value -lt 0){throw ('Invalid Texture budget component: '+$Volume+'/'+$name)}
    $expected+=[long]$spec.PSObject.Properties[$name].Value
  }
  if([long]$spec.initial_required_bytes -ne $expected){throw 'Texture volume reservation arithmetic differs from its sealed components.'}
  if($Volume -ceq 'C' -and [long]$spec.frame_bytes -ne ([long]$Budget.frame_caps.resource_windows*[long]$Budget.frame_bytes_each)){throw 'Texture C frame cap/reservation differs.'}
  if(!$StagePending -and $Volume -ceq 'D'){$expected-=[long]$spec.payload_bytes+[long]$spec.metadata_bytes}
  if($expected -lt [long]$spec.floor_bytes){throw 'Texture budget would consume the untouched floor.'}
  return $expected
}
function Assert-TextureVolumeBudgets([object]$Budget,[string]$StagePath,[string]$OutputPath,[bool]$StagePending,[string]$Phase) {
  $records=@()
  foreach($entry in @(@{name='D';path=$StagePath},@{name='C';path=$OutputPath})){
    $full=[IO.Path]::GetFullPath([string]$entry.path);$root=[IO.Path]::GetPathRoot($full)
    if($root.TrimEnd('\').TrimEnd(':') -ine $entry.name){throw 'Texture output/stage volume differs from sealed plan.'}
    $required=Get-TextureVolumeRequirement -Budget $Budget -Volume $entry.name -StagePending $StagePending
    $drive=[IO.DriveInfo]::new($root);$free=[long]$drive.AvailableFreeSpace
    if(!$drive.IsReady -or $free -lt $required){throw "Texture volume budget failed $Phase/$($entry.name): free=$free required=$required"}
    $records+=@{volume=$entry.name;path=$full;phase=$Phase;available_bytes=$free;required_bytes=$required;floor_bytes=2147483648;stage_pending=$StagePending;measured_utc=[DateTime]::UtcNow.ToString('o');pass=$true}
  }
  return [pscustomobject]@{status='both_volumes_pass';records=$records;phase=$Phase}
}
