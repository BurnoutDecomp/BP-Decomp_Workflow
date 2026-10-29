param([string]$GameExe,[string]$RunDir)
$ErrorActionPreference='Stop'
$deadline=[DateTime]::UtcNow.AddSeconds(480);$owner=$null;$event=$null;$records=@();$exitSeen=$false
$gameLog=Join-Path (Split-Path $GameExe -Parent) 'BrnGame.log'
$out=Join-Path $RunDir 'CAPTURES.json'
function Save-Records { $records | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $out -Encoding UTF8 }
function Read-SharedLog {
 $stream=[IO.File]::Open($gameLog,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
 $reader=[IO.StreamReader]::new($stream)
 try{return $reader.ReadToEnd()}finally{$reader.Dispose();$stream.Dispose()}
}
try {
 while([DateTime]::UtcNow -lt $deadline){
  $games=@(Get-CimInstance Win32_Process -Filter "Name='Burnout_PC.exe'"|Where-Object{$_.ExecutablePath -and [IO.Path]::GetFullPath($_.ExecutablePath) -ieq [IO.Path]::GetFullPath($GameExe)})
  if($games.Count -gt 1){throw 'Multiple owned-image processes'}
  if($games.Count -eq 1){$owner=Get-Process -Id $games[0].ProcessId;$ownerStart=$owner.StartTime.ToUniversalTime().Ticks;$null=$owner.Handle;break}
  Start-Sleep -Milliseconds 80
 }
 if(!$owner){throw 'Owned game did not launch'}
 $ownerIdentity=@{pid=$owner.Id;image=$GameExe;start_utc_ticks=$ownerStart}
 $ownerIdentity|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $RunDir 'CAPTURE_OWNER.json')
 $event=[Threading.EventWaitHandle]::new($false,[Threading.EventResetMode]::ManualReset,('Local\BurnoutPC_FrameRequest_{0}_62173' -f $owner.Id))
 $exitAt=$null;$sequence=0;$taken=@{};$eaAt=$null;$criterionAt=$null;$introAt=$null
 $initialText=if(Test-Path -LiteralPath $gameLog){Read-SharedLog}else{''}
 foreach($old in [regex]::Matches($initialText,'(?m)^\[frame-request\] pid=(\d+) slot=(\d+) seq=(\d+) present=(\d+) file=(bb_\d{6}\.bmp)\r?$')){
  if([int]$old.Groups[1].Value -ne $owner.Id -or [int]$old.Groups[2].Value -ne 62173){throw 'Prior frame owner differs'}
  $sequence=[int]$old.Groups[3].Value
  $oldPath=Join-Path (Join-Path $RunDir 'frames') $old.Groups[5].Value
  $oldBytes=[IO.File]::ReadAllBytes($oldPath);$crypto=[Security.Cryptography.SHA256]::Create();try{$hash=[BitConverter]::ToString($crypto.ComputeHash($oldBytes)).Replace('-','').ToLowerInvariant()}finally{$crypto.Dispose()}
  $records+=@{label='car_select_recovery_capture';sequence=$sequence;ack=$old.Value;file=$oldPath;sha256=$hash;width=[BitConverter]::ToInt32($oldBytes,18);height=[math]::Abs([BitConverter]::ToInt32($oldBytes,22));owner=$ownerIdentity;note='First helper request acknowledged during car selection; helper failed while hashing; frame retained'}
 }
 if($sequence -gt 0){$taken.title_ready=$true;$taken.car_select=$true;Save-Records}
 while([DateTime]::UtcNow -lt $deadline){
  $owner.Refresh();if($owner.HasExited){$exitSeen=$true;break}
  $cim=Get-CimInstance Win32_Process -Filter "ProcessId=$($owner.Id)"
  if(!$cim -or [IO.Path]::GetFullPath($cim.ExecutablePath) -ine [IO.Path]::GetFullPath($GameExe) -or $owner.StartTime.ToUniversalTime().Ticks -ne $ownerStart){throw 'Capture owner changed'}
  $text=if(Test-Path -LiteralPath $gameLog){Read-SharedLog}else{''}
  if($null -eq $exitAt -and $text -match 'signalling StreamingFinished'){$exitAt=[DateTime]::UtcNow}
  if($null -eq $introAt -and $text -match '\[BootVideos\] play'){$introAt=[DateTime]::UtcNow}
  if($null -ne $introAt -and ([DateTime]::UtcNow-$introAt).TotalSeconds -gt 120 -and $text -notmatch '\[BootLegal\] stage -?\d+ -> 7'){throw 'BootVideos phase exceeded120s without legalstage7'}
  $label=$null
  if($null -eq $eaAt -and $text -match '\[Movie\] prepared [^\r\n]*EAFRANCHISE'){$eaAt=[DateTime]::UtcNow}
  if($null -eq $criterionAt -and $text -match '\[Movie\] prepared [^\r\n]*CRITERION'){$criterionAt=[DateTime]::UtcNow}
  if(!$taken.ea_logo -and $null -ne $eaAt -and ([DateTime]::UtcNow-$eaAt).TotalSeconds -ge 2){$label='ea_logo'}
  elseif(!$taken.ea_logo_late -and $null -ne $eaAt -and $null -eq $criterionAt -and ([DateTime]::UtcNow-$eaAt).TotalSeconds -ge 5){$label='ea_logo_late'}
  elseif(!$taken.criterion_logo -and $null -ne $criterionAt -and ([DateTime]::UtcNow-$criterionAt).TotalSeconds -ge 2){$label='criterion_logo'}
  elseif(!$taken.criterion_logo_late -and $null -ne $criterionAt -and ([DateTime]::UtcNow-$criterionAt).TotalSeconds -ge 5){$label='criterion_logo_late'}
  elseif(!$taken.title_ready -and $text -match '(?m)^\[BootLegal\] stage -?\d+ -> 7\r?$'){$label='title_ready'}
  elseif(!$taken.profile_ready -and $text -match '\[BootProfile\] stage 3 -> 4'){$label='profile_ready'}
  elseif(!$taken.car_select -and $text -match 'Entering Car Select'){$label='car_select'}
  elseif(!$taken.world_exit -and $null -ne $exitAt){$label='world_exit'}
  elseif(!$taken.drive_8s -and $null -ne $exitAt -and ([DateTime]::UtcNow-$exitAt).TotalSeconds -ge 8){$label='drive_8s'}
  elseif(!$taken.drive_15s -and $null -ne $exitAt -and ([DateTime]::UtcNow-$exitAt).TotalSeconds -ge 15){$label='drive_15s'}
  elseif(!$taken.drive_25s -and $null -ne $exitAt -and ([DateTime]::UtcNow-$exitAt).TotalSeconds -ge 25){$label='drive_25s'}
  elseif(!$taken.drive_35s -and $null -ne $exitAt -and ([DateTime]::UtcNow-$exitAt).TotalSeconds -ge 35){$label='drive_35s'}
  if($label){
   $taken[$label]=$true;$sequence++;$cursor=$text.Length;$requestUtc=[DateTime]::UtcNow.ToString('o');$event.Reset()|Out-Null;$event.Set()|Out-Null
   $ackDeadline=[DateTime]::UtcNow.AddSeconds(8);$match=$null
   while([DateTime]::UtcNow -lt $ackDeadline){
    $owner.Refresh();if($owner.HasExited){throw 'Owned game exited during capture'}
    $fresh=Read-SharedLog;$tail=if($fresh.Length -ge $cursor){$fresh.Substring($cursor)}else{throw 'Log truncated'}
    $m=[regex]::Match($tail,'(?m)^\[frame-request\] pid=(\d+) slot=(\d+) seq=(\d+) present=(\d+) file=(bb_\d{6}\.bmp)\r?$')
    if($m.Success){$match=$m;break};Start-Sleep -Milliseconds 50
   }
   if(!$match){throw ('No capture acknowledgement: '+$label)}
   if([int]$match.Groups[1].Value -ne $owner.Id -or [int]$match.Groups[2].Value -ne 62173 -or [int]$match.Groups[3].Value -ne $sequence){throw 'Capture acknowledgement ownership/sequence mismatch'}
   $path=Join-Path (Join-Path $RunDir 'frames') $match.Groups[5].Value
   $bytes=[IO.File]::ReadAllBytes($path);$width=[BitConverter]::ToInt32($bytes,18);$height=[math]::Abs([BitConverter]::ToInt32($bytes,22))
   if($width -ne 1280 -or $height -ne 720){throw "Capture dimensions $width x $height differ"}
   $crypto=[Security.Cryptography.SHA256]::Create();try{$hash=[BitConverter]::ToString($crypto.ComputeHash($bytes)).Replace('-','').ToLowerInvariant()}finally{$crypto.Dispose()}
   $records+=@{label=$label;sequence=$sequence;request_utc=$requestUtc;owner=$ownerIdentity;ack=$match.Value;file=$path;sha256=$hash;width=$width;height=$height;log_cursor_chars=$cursor;time_origin_note='Seconds after this passive helper observed StreamingFinished'}
   Save-Records;Write-Output ('CAPTURE '+$label+' '+$match.Value)
   if($records.Count -ge 10){
    foreach($required in @('ea_logo','criterion_logo','title_ready','profile_ready','car_select','world_exit','drive_8s','drive_15s')){if(!$taken[$required]){throw ('Required phase missing: '+$required)}}
    $owner.Refresh();if($owner.HasExited -or $owner.StartTime.ToUniversalTime().Ticks -ne $ownerStart -or [IO.Path]::GetFullPath($owner.MainModule.FileName) -ine [IO.Path]::GetFullPath($GameExe)){throw 'Phase completion owner changed'}
    $stopName='Local\BurnoutPC_HarnessPhaseDone_{0}_{1}_{2}' -f $owner.Id,62173,$ownerStart
    $stop=[Threading.EventWaitHandle]::OpenExisting($stopName)
    try{$stop.Set()|Out-Null}finally{$stop.Dispose()}
    @{owner=$ownerIdentity;event=$stopName;captures=$records.Count;reason='All required unbypassed logo/title/profile/world/driving phases captured';utc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $RunDir 'PHASE_STOP_REQUEST.json')
    break
   }
  }
  Start-Sleep -Milliseconds 80
 }
 Save-Records
}catch{ @{error=$_.Exception.Message;records=$records}|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $RunDir 'CAPTURE_ERROR.json'); if($owner){try{$owner.Refresh();if(!$owner.HasExited -and $owner.StartTime.ToUniversalTime().Ticks -eq $ownerStart -and [IO.Path]::GetFullPath($owner.MainModule.FileName) -ieq [IO.Path]::GetFullPath($GameExe)){$owner.Kill();$owner.WaitForExit(5000)|Out-Null}}catch{}};throw }
finally {if($event){$event.Reset()|Out-Null;$event.Dispose()}}
