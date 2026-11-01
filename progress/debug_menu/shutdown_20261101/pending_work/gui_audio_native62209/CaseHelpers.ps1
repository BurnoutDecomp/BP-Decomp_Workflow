function New-BrnGuiAudioRunArguments {
 return @{
  Drive=$true;MotionProbe=$true;TitleStart=$true;AcceptGap=1.0
  MaxSeconds=480;MinFreeGB=2;MaxLogMB=48;NoAssertRelease=$true
  StrictGameOwnership=$true;AllowConcurrentGames=$true
  Teleport='3040.7,-5.8,-1937.9,180';DriveDelay=6.0;DriveSeconds=100.0
  ThrottleScript='0:accel,12:brake+handbrake,15:none,42:accel,50:brake+handbrake,53:none'
  PauseAt='22';PauseTarget='map';MenuTapAt='30:Next,38:Prev';UnpauseAt='46'
  FrameEvery=1000000000
 }
}
function Test-BrnGuiAudioPositiveMotion([string]$Line) {
 $m=[regex]::Match($Line,'^\[motion\].*\|v\| (?<speed>[-0-9.]+).* gas (?<gas>[-0-9.]+) ')
 if(!$m.Success){return $false}
 $inv=[cultureinfo]::InvariantCulture
 return ([double]::Parse($m.Groups['speed'].Value,$inv) -gt 0.1 -and [double]::Parse($m.Groups['gas'].Value,$inv) -gt 0.01)
}
function Test-BrnGuiAudioNativeReceipts([string]$RunDir) {
 foreach($name in @('driver-result.json','CAPTURE_AUDIT.json','CURRENT_SAVE_LOAD_GATE.json','PHASE_DONE_REQUEST.json','flow-terminal.json')){
  if(!(Test-Path -LiteralPath (Join-Path $RunDir $name))){return @{Pass=$false;Detail=('missing '+$name)}}
 }
 $r=Get-Content -Raw (Join-Path $RunDir 'driver-result.json')|ConvertFrom-Json
 $a=Get-Content -Raw (Join-Path $RunDir 'CAPTURE_AUDIT.json')|ConvertFrom-Json
 $g=Get-Content -Raw (Join-Path $RunDir 'CURRENT_SAVE_LOAD_GATE.json')|ConvertFrom-Json
 $p=Get-Content -Raw (Join-Path $RunDir 'PHASE_DONE_REQUEST.json')|ConvertFrom-Json
 $f=Get-Content -Raw (Join-Path $RunDir 'flow-terminal.json')|ConvertFrom-Json
 $phases='ea_boot|criterion_boot|driving_before_pause|map_open|map_after_next|map_after_prev|driving_resumed|driving_continues'
 $ok=($r.status -ceq 'complete_awaiting_visual_review' -and $r.slot -eq 62209 -and $r.profile_pass -eq $true -and $r.process_id -gt 0 -and $r.frame_count -eq 8 -and $a.pass -eq $true -and $a.frame_count -eq 8 -and $g.pass -eq $true -and $g.private_fixture_sha256 -ceq '4e4526ed40c8fa57f1100503351c68285f9eba69421e4bdab1bb8ce63ec3a23c' -and $p.event_set -eq $true -and $p.slot -eq 62209 -and $p.process_id -eq $r.process_id -and [IO.Path]::GetFullPath($p.image) -ieq [IO.Path]::GetFullPath($r.image) -and ([DateTimeOffset]::Parse($p.start_utc).UtcDateTime.Ticks.ToString()) -ceq [string]$r.start_ticks -and $p.witness_sha256 -ceq (Get-FileHash (Join-Path $RunDir 'driver-result.json') -Algorithm SHA256).Hash.ToLowerInvariant() -and ($r.frames.phase -join '|') -ceq $phases -and @($r.frames|Where-Object {$_.pid -ne $r.process_id -or $_.slot -ne 62209}).Count -eq 0 -and $f.success -eq $true -and $f.flow_status.phase_collection_stop_requested -eq $true -and $f.flow_status.owned_cleanup_complete -eq $true -and $f.flow_status.owned_pid -eq $r.process_id -and [IO.Path]::GetFullPath($f.flow_status.owned_image) -ieq [IO.Path]::GetFullPath($r.image) -and ([DateTimeOffset]::Parse($f.flow_status.owned_start_utc).UtcDateTime.Ticks.ToString()) -ceq [string]$r.start_ticks)
 return @{Pass=$ok;Detail='current-save + exact owner + eight bounded frames + PhaseDone/cleanup; pixels require separate review; audible/sweep/control credit=0'}
}
