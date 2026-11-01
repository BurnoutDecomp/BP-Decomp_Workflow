function Lines {
 if(!(Test-Path -LiteralPath $GameLog)){if($script:gameBytes -gt 0){throw 'owned game log disappeared; absolute proof indexes are invalid'};return ,$script:gameLines}
 $fs=[IO.File]::Open($GameLog,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete));$hash=[Security.Cryptography.SHA256]::Create()
 try{
  if($fs.Length -lt $script:gameBytes){throw 'owned game log truncated; absolute proof indexes are invalid'}
  $buffer=[byte[]]::new([int]$fs.Length);$read=0
  while($read -lt $buffer.Length){$part=$fs.Read($buffer,$read,$buffer.Length-$read);if($part -eq 0){break};$read+=$part}
  if($read -lt $script:gameBytes){throw 'owned game log truncated during read; absolute proof indexes are invalid'}
  # Verify every already-published byte, not just length/file identity: same-file rewrites and
  # equal-or-larger replacements must never retain stale rows or hide an earlier assertion.
  if($script:gameBytes -gt 0){
   $actual=[BitConverter]::ToString($hash.ComputeHash($buffer,0,[int]$script:gameBytes))
   if($actual -cne $script:prefixHash){throw 'owned game log prefix changed; absolute proof indexes are invalid'}
  }
  if($read -gt $script:gameBytes){
   $last=-1;for($i=$read-1;$i -ge $script:gameBytes;$i--){if($buffer[$i] -eq 10){$last=$i;break}}
   if($last -ge $script:gameBytes){
    $text=[Text.UTF8Encoding]::new($false,$false).GetString($buffer,[int]$script:gameBytes,[int]($last-$script:gameBytes))
    if($script:gameBytes -eq 0 -and $text.StartsWith([string][char]0xFEFF,[StringComparison]::Ordinal)){$text=$text.Substring(1)}
    $complete=[regex]::Replace($text,"`r+(?=`n)",'').TrimEnd([char]13)
    foreach($line in $complete.Split([char]10)){$script:gameLines.Add($line)}
    $script:gameBytes=$last+1;$script:prefixHash=[BitConverter]::ToString($hash.ComputeHash($buffer,0,[int]$script:gameBytes))
   }
  }
  return ,$script:gameLines
 }finally{$hash.Dispose();$fs.Dispose()}
}

function Own {
 $activeDeadline=if($script:cleanupMode){$script:cleanupDeadline}else{$deadline}
 if([DateTime]::UtcNow -gt $activeDeadline){throw 'bounded Director driver deadline'}
 if(!$owner -or !$owner.Process -or !$owner.Handle -or $owner.Process.Id -ne $owner.Pid -or $owner.Process.HasExited -or $owner.Process.StartTime.ToUniversalTime().Ticks -ne $owner.Ticks){throw 'exact retained Director owner exited or changed'}
 if([DateTime]::UtcNow -ge $script:nextCim){$c=Get-CimInstance Win32_Process -Filter ('ProcessId='+$owner.Pid) -ErrorAction Stop;if(!$c.ExecutablePath -or [IO.Path]::GetFullPath($c.ExecutablePath) -ine $owner.Path){throw 'owned image changed'};$script:nextCim=[DateTime]::UtcNow.AddSeconds(2)}
 if(!$script:cleanupMode -and $script:logAccepted){$all=Lines;for($i=$script:assertCursor;$i -lt $all.Count;$i++){if($all[$i] -match '\[ASSERT(?:\s+\d+)?\]|\[EXCEPTION\]|Alias not found|Variable not found|Component not found|Unknown command'){throw 'raw assert/exception/native command failure'}};$script:assertCursor=$all.Count}
if($owner){$obs=Assert-BrnConcurrentOwnerSet -Stage $stage -OwnedPid $owner.Pid -Phase "runtime" -AppendPath $script:concurrentLedgerPath;$script:maxConcurrentOtherCount=[Math]::Max($script:maxConcurrentOtherCount,[int]$obs.observed_other_game_count);$script:lastConcurrentObservation=$obs;$script:concurrentObservationCount++}
}

function Wait-Line([string]$Pattern,[int]$Cursor,[int]$Seconds=12){
 $until=[DateTime]::UtcNow.AddSeconds($Seconds)
 do{Own;$all=Lines;for($i=$Cursor;$i -lt $all.Count;$i++){if($all[$i] -match $Pattern){return [pscustomobject]@{line=$all[$i];index=$i}}};Start-Sleep -Milliseconds 50}while([DateTime]::UtcNow -lt $until)
 throw ('missing fresh native receipt: '+$Pattern)
}

function Get-NativeFrameAckMatch([string]$Line,[int]$OwnerPid,[int]$OwnerSlot,[int]$ExpectedSequence){
 # Sound's original LogOutput appends fragments; another native thread may place
 # a complete frame ACK after an audio prefix on the same physical log line.
 # Preserve that raw line, require one complete final token and the exact owner.
 if([regex]::Matches($Line,'\[frame-request\]').Count -ne 1){throw 'frame ACK token count is not one'}
 $m=[regex]::Match($Line,'\[frame-request\] pid=(\d+) slot=(\d+) seq=(\d+) present=(\d+) file=(bb_\d{6}\.bmp)$')
 if(!$m.Success -or [int]$m.Groups[1].Value -ne $OwnerPid -or [int]$m.Groups[2].Value -ne $OwnerSlot -or [int]$m.Groups[3].Value -ne $ExpectedSequence -or $ExpectedSequence -lt 1 -or [int]$m.Groups[4].Value -lt 1){throw 'frame ACK token owner/slot/sequence mismatch'}
 if([int]$m.Groups[5].Value.Substring(3,6) -ne [int]$m.Groups[4].Value){throw 'frame ACK filename/present mismatch'}
 return $m
}

function Capture-PhaseRaw([object]$Phase){
 $maxFrames=if($script:maxRawFrames){[int]$script:maxRawFrames}else{52}
 if($frameRows.Count -ge $maxFrames){throw ('raw frame cap exceeded before terminal capture: '+$frameRows.Count+' >= '+$maxFrames)}
 Own;$cursor=(Lines).Count;$frameEvent.Reset()|Out-Null;$frameEvent.Set()|Out-Null
 $ack=Wait-Line '\[frame-request\] pid=(\d+) slot=(\d+) seq=(\d+) present=(\d+) file=(bb_\d{6}\.bmp)$' $cursor 15
 $m=Get-NativeFrameAckMatch $ack.line $owner.Pid $Slot ($script:sequence+1)
 if([int]$m.Groups[1].Value -ne $owner.Pid -or [int]$m.Groups[2].Value -ne $Slot -or [int]$m.Groups[3].Value -ne ($script:sequence+1)){throw 'frame ACK owner/slot/sequence mismatch'}
 $name=$m.Groups[5].Value;$path=Join-Path $RunDir ('frames/'+$name);$until=[DateTime]::UtcNow.AddSeconds(5)
 while(!(Test-Path -LiteralPath $path)){Own;if([DateTime]::UtcNow -gt $until){throw 'ACK BMP missing'};Start-Sleep -Milliseconds 50}
 $bytes=[IO.File]::ReadAllBytes($path);$width=[BitConverter]::ToInt32($bytes,18);$height=[Math]::Abs([BitConverter]::ToInt32($bytes,22));if($bytes.Length -le 54 -or $bytes[0] -ne 66 -or $bytes[1] -ne 77 -or $width -ne 1280 -or $height -ne 720 -or $bytes.Length -gt 3686454){throw 'invalid 1280x720 BMP or unexpected capture budget'}
 if($frameEvent.WaitOne(0)){throw 'game did not consume frame event'}
 $present=[int]$m.Groups[4].Value;$csvPath=Join-Path $RunDir 'frames/frames.csv';$csvRows=@();$csvUntil=[DateTime]::UtcNow.AddSeconds(5)
 do{
  Own;$csvStream=$null;$csvReader=$null
  try{
   $csvStream=[IO.File]::Open($csvPath,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete));$csvReader=[IO.StreamReader]::new($csvStream);$csvText=$csvReader.ReadToEnd();$csvLines=$csvText.Split([char]10)
   $csvRows=@();for($j=0;$j -lt $csvLines.Length-1;$j++){if($csvLines[$j] -match ('^'+$present+',')){$csvRows+=([string]$csvLines[$j]).TrimEnd([char]13)}}
  }catch [IO.IOException]{}finally{if($csvReader){$csvReader.Dispose()}elseif($csvStream){$csvStream.Dispose()}}
  if($csvRows.Count -gt 1){throw 'duplicate CSV present row'}
  if($csvRows.Count -eq 1){break};Start-Sleep -Milliseconds 50
 }while([DateTime]::UtcNow -lt $csvUntil)
 if($csvRows.Count -ne 1){throw 'frame CSV did not finish its exact ACK present row inside the bound'}
 $script:sequence++;$row=[ordered]@{phase=$Phase.name;path=$path;name=$name;bytes=$bytes.Length;max_bytes=3686454;width=$width;height=$height;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant();pid=$owner.Pid;slot=$Slot;sequence=$script:sequence;present=$present;ack=$ack.line;ack_token=$m.Value;ack_column=$m.Index;ack_index=$ack.index;request_cursor=$cursor;csv_path=$csvPath;csv_row=[string]$csvRows[0]};$frameRows.Add($row)
}
