param([string]$RunDir,[string]$ExpectedSlotExe,[string]$GameLog,[int]$Slot=62180)
$ErrorActionPreference='Stop'
$PackageRoot=$PSScriptRoot
$plan=Get-Content -Raw (Join-Path $PackageRoot 'SCOPE.json')|ConvertFrom-Json
$ExpectedSha256=$plan.candidate.exe_sha256
$stage=Get-Content -Raw (Join-Path $PackageRoot 'STAGING.json')|ConvertFrom-Json
$controls=@($plan.controls)+@($plan.context_aliases)
$logPath=Join-Path $RunDir 'driver.log';$keys=@{};$owner=$null;$frameEvent=$null;$doneEvent=$null;$script:sequence=0
$started=[DateTime]::UtcNow;$deadline=$started.AddSeconds(235);$nextCim=[DateTime]::MinValue
$script:consoleVisible=$null;$script:logAccepted=$false;$script:writesStarted=$false;$script:cleanupMode=$false;$script:terminalRestoreVerified=$false
$frameRows=[Collections.Generic.List[object]]::new();$phaseRows=[Collections.Generic.List[object]]::new()
$script:gameLines=[Collections.Generic.List[string]]::new();$script:gameBytes=0L;$script:assertCursor=0;$script:prefixHash=$null
function Say([string]$s){Add-Content -LiteralPath $logPath -Encoding UTF8 -Value ((Get-Date).ToString('HH:mm:ss.fff')+' '+$s)}
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

function Command-Codes([int]$Cursor){
 $all=Lines;$codes=[Collections.Generic.List[int]]::new()
 for($i=$Cursor;$i -lt $all.Count;$i++){if($all[$i] -match '^\[debug-ui\].*visible=1 .*key=(\d+)$' -and [int]$Matches[1] -ne 0){$codes.Add([int]$Matches[1])}}
 return ,$codes
}

function Own {
 $activeDeadline=if($script:cleanupMode){$script:cleanupDeadline}else{$deadline}
 if([DateTime]::UtcNow -gt $activeDeadline){throw 'bounded Director driver deadline'}
 if(!$owner -or !$owner.Process -or !$owner.Handle -or $owner.Process.Id -ne $owner.Pid -or $owner.Process.HasExited -or $owner.Process.StartTime.ToUniversalTime().Ticks -ne $owner.Ticks){throw 'exact retained Director owner exited or changed'}
 if([DateTime]::UtcNow -ge $script:nextCim){$c=Get-CimInstance Win32_Process -Filter ('ProcessId='+$owner.Pid) -ErrorAction Stop;if(!$c.ExecutablePath -or [IO.Path]::GetFullPath($c.ExecutablePath) -ine $owner.Path){throw 'owned image changed'};$script:nextCim=[DateTime]::UtcNow.AddSeconds(2)}
 if(!$script:cleanupMode -and $script:logAccepted){$all=Lines;for($i=$script:assertCursor;$i -lt $all.Count;$i++){if($all[$i] -match '\[ASSERT(?:\s+\d+)?\]|\[EXCEPTION\]|Alias not found|Variable not found|Component not found|Unknown command'){throw 'raw assert/exception/native command failure'}};$script:assertCursor=$all.Count}
}
function Wait-Line([string]$Pattern,[int]$Cursor,[int]$Seconds=12){
 $until=[DateTime]::UtcNow.AddSeconds($Seconds)
 do{Own;$all=Lines;for($i=$Cursor;$i -lt $all.Count;$i++){if($all[$i] -match $Pattern){return [pscustomobject]@{line=$all[$i];index=$i}}};Start-Sleep -Milliseconds 50}while([DateTime]::UtcNow -lt $until)
 throw ('missing fresh native receipt: '+$Pattern)
}
function Key-Observed([int]$Code,[string]$Pattern,[bool]$Shift=$false){
 Own;$cursor=(Lines).Count
 try{if($Shift){$keys[16].Set()|Out-Null};$keys[$Code].Set()|Out-Null;return Wait-Line $Pattern $cursor 6}finally{$keys[$Code].Reset()|Out-Null;$keys[16].Reset()|Out-Null}
}
function Console([bool]$Visible){if($null -ne $script:consoleVisible -and $script:consoleVisible -eq $Visible){return};$v=if($Visible){1}else{0};$ev=if($Visible){9}else{0};[void](Key-Observed 192 ('^\[debug-ui\] event='+$ev+' visible='+$v+' .* key=0$'));$script:consoleVisible=$Visible}
function Type-Setup {
 $commandCursor=(Lines).Count;$expectedCodes=@(101,120,101,99,32,98,49,46,99,102,103)
 foreach($ch in 'exec b1.cfg'.ToCharArray()){
  $ascii=[int]$ch;$vk=if($ascii -ge 97 -and $ascii -le 122){$ascii-32}elseif($ascii -eq 46){190}else{$ascii}
  [void](Key-Observed $vk ('^\[debug-ui\] event=0 visible=1 .* key='+$ascii+'$'))
 }
 $actualCodes=Command-Codes $commandCursor
 if(($actualCodes -join ',') -cne ($expectedCodes -join ',')){throw 'exact pre-Enter command sequence differs; no Enter sent'}
 [void](Key-Observed 13 '^\[debug-ui\] event=0 visible=1 .* key=10$')
 $actualCodes=Command-Codes $commandCursor
 if(($actualCodes -join ',') -cne ((@($expectedCodes)+@(10)) -join ',')){throw 'exact command-plus-Enter sequence differs'}
}
function Capture-PhaseRaw([object]$Phase){
 Own;$cursor=(Lines).Count;$frameEvent.Reset()|Out-Null;$frameEvent.Set()|Out-Null
 $ack=Wait-Line '^\[frame-request\] pid=(\d+) slot=(\d+) seq=(\d+) present=(\d+) file=(bb_\d{6}\.bmp)$' $cursor 15
 $m=[regex]::Match($ack.line,'pid=(\d+) slot=(\d+) seq=(\d+) present=(\d+) file=(bb_\d{6}\.bmp)')
 if([int]$m.Groups[1].Value -ne $owner.Pid -or [int]$m.Groups[2].Value -ne $Slot -or [int]$m.Groups[3].Value -ne ($script:sequence+1)){throw 'frame ACK owner/slot/sequence mismatch'}
 $name=$m.Groups[5].Value;$path=Join-Path $RunDir ('frames/'+$name);$until=[DateTime]::UtcNow.AddSeconds(5)
 while(!(Test-Path -LiteralPath $path)){Own;if([DateTime]::UtcNow -gt $until){throw 'ACK BMP missing'};Start-Sleep -Milliseconds 50}
 $bytes=[IO.File]::ReadAllBytes($path);if($bytes.Length -le 54 -or $bytes[0] -ne 66 -or $bytes[1] -ne 77){throw 'invalid or incomplete ACK BMP'}
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
 $script:sequence++;$row=[ordered]@{phase=$Phase.name;path=$path;name=$name;bytes=$bytes.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant();pid=$owner.Pid;slot=$Slot;sequence=$script:sequence;present=$present;ack=$ack.line;ack_index=$ack.index;request_cursor=$cursor;csv_path=$csvPath;csv_row=[string]$csvRows[0]};$frameRows.Add($row)
}

function Capture-Phase([object]$Phase){
 $cursor=(Lines).Count
 $motion=Wait-Line '^\[motion\] n \d+ pos .* mph -?0(?:\.[0-4]\d*)? gear .* engine 2$' $cursor 8
 Capture-PhaseRaw $Phase
 $frame=$frameRows[$frameRows.Count-1]
 $fields=$frame.csv_row.Split(',')
 if($fields.Count -ne 24){throw 'Unexpected actual frame CSV shape'}
 $pose=@([double]$fields[20],[double]$fields[21],[double]$fields[22])
 if(!$script:baselinePose){$script:baselinePose=$pose}
 $distance=[Math]::Sqrt([Math]::Pow($pose[0]-$script:baselinePose[0],2)+[Math]::Pow($pose[1]-$script:baselinePose[1],2)+[Math]::Pow($pose[2]-$script:baselinePose[2],2))
 if($distance -gt 2){throw 'Stationary consumer scene moved over2metres'}
 $frame.car_engine_state=2;$frame.boost_effect_mask=[uint32]$fields[23];$frame.motion_line=$motion.line;$frame.motion_index=$motion.index;$frame.pose=$pose;$frame.displacement_from_baseline=$distance
 $bmp=[IO.File]::ReadAllBytes($frame.path)
 if([BitConverter]::ToInt32($bmp,18) -ne 640 -or [Math]::Abs([BitConverter]::ToInt32($bmp,22)) -ne 360 -or $bmp.Length -gt 1MB){throw 'Capture violated640x360 storage contract'}
}
function Read-Values([int]$Cursor,[object[]]$Selected=$controls){
 $until=[DateTime]::UtcNow.AddSeconds(8)
 do{
  Own
  # One complete immutable raw-byte snapshot per poll. Lines still revalidates the
  # entire previously accepted prefix SHA before exposing any rows, unchanged.
  $all=Lines;$proof=@();$values=@{};$at=$Cursor;$complete=$true
  foreach($control in $Selected){
   $ack=$control.alias+': /'+$control.lookup_path;$found=-1
   for($i=$at;$i -lt $all.Count-2;$i++){if($all[$i] -ceq $ack -and $all[$i+2] -ceq $ack){$found=$i;break}}
   if($found -lt 0){$complete=$false;break}
   $value=$all[$found+1].Trim();$number=0.0
   if($control.type -eq 'f32'){
    if(![double]::TryParse($value,[Globalization.NumberStyles]::Float,[cultureinfo]::InvariantCulture,[ref]$number) -or [double]::IsNaN($number) -or [double]::IsInfinity($number)){throw 'Nonfinite native value'}
   }elseif($value -cnotin @('TRUE','FALSE')){throw 'Native bool type mismatch'}
   $values[$control.alias]=$value;$proof+=@{alias=$control.alias;path=$control.lookup_path;value=$value;ack_before=$found;value_line=$found+1;ack_after=$found+2};$at=$found+3
  }
  if($complete){return @{values=$values;proofs=$proof;snapshot_bytes=$script:gameBytes;snapshot_hash=$script:prefixHash}}
  Start-Sleep -Milliseconds 30
 }while([DateTime]::UtcNow -lt $until)
 throw 'Incomplete fresh native alias triplets inside8seconds'
}
function Queries([object[]]$Selected=$controls){$commands=@();foreach($control in $Selected){$commands+=('alias '+$control.alias);$commands+=$control.alias;$commands+=('alias '+$control.alias)};return $commands}
function Execute([string]$Name,[string[]]$Commands,[hashtable]$Expected,[bool]$Capture=$true,[object[]]$Selected=$controls){
 Own
 $file=Join-Path $stage.cwd 'b2.cfg'
 $emitted=$Commands+@(Queries $Selected)
 [IO.File]::WriteAllLines($file,$emitted,[Text.Encoding]::ASCII)
 $retained=Join-Path $RunDir ('phase_'+$Name+'.cfg')
 if(Test-Path $retained){throw 'Refusing phase command receipt overwrite'}
 [IO.File]::WriteAllBytes($retained,[IO.File]::ReadAllBytes($file))
 $scriptHash=(Get-FileHash -LiteralPath $retained -Algorithm SHA256).Hash.ToLowerInvariant()
 $cursor=(Lines).Count
 try{$keys[113].Set()|Out-Null;$read=Read-Values $cursor $Selected}finally{$keys[113].Reset()|Out-Null}
 foreach($key in $Expected.Keys){
  if(!$read.values.ContainsKey($key)){throw 'Missing expected value'}
  $want=[string]$Expected[$key];$actual=[string]$read.values[$key]
  if($want -in @('TRUE','FALSE')){if($actual -cne $want){throw "Value mismatch $Name $key $actual != $want"}}
  elseif([Math]::Abs([double]::Parse($want,[cultureinfo]::InvariantCulture)-[double]::Parse($actual,[cultureinfo]::InvariantCulture)) -gt 0.00051){throw "Value mismatch $Name $key $actual != $want"}
 }
 $phaseRows.Add(@{phase=$Name;cursor=$cursor;commands=$Commands;command_file=$retained;command_sha256=$scriptHash;expected=$Expected;proofs=$read.proofs;snapshot_bytes=$read.snapshot_bytes;snapshot_hash=$read.snapshot_hash})
 if($Capture){Start-Sleep -Milliseconds 400;Capture-Phase @{name=$Name}}
 return $read.values
}
function Commands-For([hashtable]$Values){$lines=@();foreach($control in $controls){if($Values.ContainsKey($control.alias)){$lines+=('set '+$control.alias+' '+$Values[$control.alias])}};return $lines}
function Save-Result([string]$Status,[string]$ErrorText=''){
 [ordered]@{status=$Status;error=$ErrorText;slot=$Slot;process_id=$owner.Pid;process_path=$owner.Path;process_start_ticks=[string]$owner.Ticks;exe_sha256=$ExpectedSha256;frames=@($frameRows.ToArray());phases=@($phaseRows.ToArray());terminal_restore_verified=$script:terminalRestoreVerified;selected_controls=24;eligible_control_count=$script:eligibleControls.Count;skipped_controls=$script:skippedControls;site_credit=0}|ConvertTo-Json -Depth 12|Set-Content (Join-Path $RunDir 'driver-result.json') -Encoding UTF8
}
try{
 if($Slot -ne 62180 -or $plan.control_count -ne 24 -or $controls.Count -ne 28){throw 'Wrong exact batch'}
 if((Get-FileHash $ExpectedSlotExe -Algorithm SHA256).Hash.ToLowerInvariant() -cne $ExpectedSha256){throw 'Wrong source32 executable'}
 for($i=0;$i -lt 256;$i++){$keys[$i]=[Threading.EventWaitHandle]::new($false,[Threading.EventResetMode]::ManualReset,('Local\BurnoutPC_DebugKey_{0:X2}_{1}' -f $i,$Slot));$keys[$i].Reset()|Out-Null}
 @{status='ready';slot=$Slot;driver_pid=$PID;event_count=256}|ConvertTo-Json|Set-Content (Join-Path $RunDir 'DRIVER_READY.json')
 while([DateTime]::UtcNow -lt $deadline -and !$owner){
  foreach($p in @(Get-Process -Name Burnout_PC -ErrorAction SilentlyContinue)){try{
   if($p.StartTime.ToUniversalTime() -lt $started){continue}
   $c=Get-CimInstance Win32_Process -Filter ('ProcessId='+$p.Id)
   if($c.ExecutablePath -and [IO.Path]::GetFullPath($c.ExecutablePath) -ieq [IO.Path]::GetFullPath($ExpectedSlotExe)){
    $handle=$p.Handle;if(!$handle -or $p.HasExited){throw 'No retained process handle'}
    $owner=@{Process=$p;Handle=$handle;Pid=$p.Id;Ticks=$p.StartTime.ToUniversalTime().Ticks;Path=[IO.Path]::GetFullPath($c.ExecutablePath)};break
   }
  }catch{if($owner){throw}}};if(!$owner){Start-Sleep -Milliseconds 100}
 }
 if(!$owner){throw 'No new exact private process'}
 $script:logAccepted=$true
 $frameEvent=[Threading.EventWaitHandle]::new($false,[Threading.EventResetMode]::ManualReset,('Local\BurnoutPC_FrameRequest_{0}_{1}' -f $owner.Pid,$Slot))
 [void](Wait-Line '^\[motion\] n \d+ pos .* mph (?:[1-9]\d|[1-9]\d{2,})(?:\.\d+)? gear ' 0 100)
 Start-Sleep -Seconds 12
 Own
 Console $true;Type-Setup;Console $false
 $natural=Read-Values 0
 if($natural.values.CTOOL -cne 'FALSE'){throw 'Tool TRUE would overwrite native setters; requires separate scenario'}
 Capture-Phase @{name='natural_baseline'}
 $contexts=@{};foreach($c in $plan.context_aliases){$contexts[$c.alias]=$natural.values[$c.alias]}
 $script:writesStarted=$true
 $frozen=Execute 'frozen_baseline' @('set CSIM FALSE','set CRIG FALSE','set CCLOUD 0') @{CSIM='FALSE';CTOOL='FALSE';CRIG='FALSE';CCLOUD='0'}
 $baseline=@{};foreach($c in $controls){$baseline[$c.alias]=$frozen[$c.alias]}
 $script:eligibleControls=[Collections.Generic.List[object]]::new();$script:skippedAliases=@();$script:skippedControls=@()
 foreach($control in $plan.controls){
  $value=[double]::Parse($baseline[$control.alias],[cultureinfo]::InvariantCulture)
  if($control.id -in @($plan.retained_complete_ids)){$script:skippedAliases+=$control.alias;$script:skippedControls+=@{id=$control.id;alias=$control.alias;baseline=$baseline[$control.alias];reason='complete PNR retained from predecessor; read-only refresh, no duplicate target or cleanup SET';state='retained_completed_phases'}}elseif($value -lt [double]$control.range_min -or $value -gt [double]$control.range_max){$script:skippedAliases+=$control.alias;$script:skippedControls+=@{id=$control.id;alias=$control.alias;baseline=$baseline[$control.alias];reason='captured value outside original setter range; no target or cleanup SET permitted';state='pending'}}else{$script:eligibleControls.Add($control)}
 }
 if($script:eligibleControls.Count -ne 3){throw 'Exactly3 unfinished restorable controls required; no target writes'}
 $baselineFrame=$frameRows[$frameRows.Count-1]
 @{status='awaiting_scene_review';frame=$baselineFrame;owner_pid=$owner.Pid;slot=$Slot;selected_controls=24;eligible_controls=$script:eligibleControls.Count;skipped_controls=$script:skippedControls;deadline_utc=$deadline.ToString('o')}|ConvertTo-Json -Depth 8|Set-Content (Join-Path $RunDir 'BASELINE_READY.json')
 $sceneDeadline=[DateTime]::UtcNow.AddSeconds(60)
 do{Own;if(Test-Path (Join-Path $RunDir 'BASELINE_APPROVAL.json')){break};Start-Sleep -Milliseconds 100}while([DateTime]::UtcNow -lt $sceneDeadline)
 if(!(Test-Path (Join-Path $RunDir 'BASELINE_APPROVAL.json'))){throw 'No baseline consumer scene approval'}
 $scene=Get-Content -Raw (Join-Path $RunDir 'BASELINE_APPROVAL.json')|ConvertFrom-Json
 if($scene.status -cne 'approved' -or $scene.frame_sha256 -cne $baselineFrame.sha256 -or $scene.owner_pid -ne $owner.Pid -or $scene.slot -ne $Slot -or !$scene.sky_visible -or !$scene.lit_world_visible -or !$scene.stationary){throw 'Actual baseline scene is unsuitable'}
 foreach($control in $script:eligibleControls){
  foreach($state in @('positive','negative','restore')){
   $value=if($state -eq 'restore'){$baseline[$control.alias]}else{([double]$control.$state).ToString('0.###',[cultureinfo]::InvariantCulture)}
   $expected=@{};foreach($k in $baseline.Keys){$expected[$k]=$baseline[$k]};$expected[$control.alias]=$value
   $commands=@();$companion=$null
   if($control.id -match '#005[24]$'){$companion='E56'}elseif($control.id -match '#0056$'){$companion='E52'}
   if($companion){
    if($companion -in $script:skippedAliases){throw 'Companion original baseline is not setter-restorable'}
    $companionValue=if($state -eq 'restore'){$baseline[$companion]}else{'0.5'}
    $commands+=('set '+$companion+' '+$companionValue);$expected[$companion]=$companionValue
   }
   $commands+=('set '+$control.alias+' '+$value)
   [void](Execute (($control.id -replace '^.*#','')+'_'+$state) $commands $expected)
  }
 }
 $restore=@{};foreach($k in $baseline.Keys){if($k -notin $script:skippedAliases){$restore[$k]=$baseline[$k]}};$restore.CRIG=$contexts.CRIG;$restore.CCLOUD=$contexts.CCLOUD
 [void](Execute 'controls_and_companions_restore' (Commands-For $restore) $restore)
 [void](Execute 'context_restore' (Commands-For $contexts) $contexts $true @($plan.context_aliases))
 $script:terminalRestoreVerified=$true
 if($frameRows.Count -ne (3*$script:eligibleControls.Count+4) -or $phaseRows.Count -ne (3*$script:eligibleControls.Count+3)){throw 'Incomplete exact21 P/N/R or restore collection'}
 Save-Result 'machine_complete_awaiting_independent_pixels'
 $helper=Join-Path $PackageRoot 'Request-HarnessPhaseDone.ps1'
 $witness=Join-Path $RunDir 'driver-result.json'
 & $helper -ProcessId $owner.Pid -Slot $Slot -ExpectedImagePath $owner.Path -ExpectedStartUtc $owner.Process.StartTime.ToUniversalTime().ToString('o') -WitnessPath $witness -WitnessSha256 (Get-FileHash $witness -Algorithm SHA256).Hash.ToLowerInvariant() -ReceiptPath (Join-Path $RunDir 'PHASE_DONE_REQUEST.json')
 Say 'RESULT DONE'
}catch{
 $reason=$_.Exception.Message
 $script:cleanupMode=$true;$script:cleanupDeadline=[DateTime]::UtcNow.AddSeconds(20)
 if($owner -and $script:writesStarted -and !$script:terminalRestoreVerified){try{
  $cleanup=@{};if($baseline){foreach($k in $baseline.Keys){if($k -notin $script:skippedAliases){$cleanup[$k]=$baseline[$k]}}}
  if($contexts){foreach($k in $contexts.Keys){$cleanup[$k]=$contexts[$k]}}
  [void](Execute 'emergency_restore' (Commands-For $cleanup) @{} $false)
 }catch{Say ('Emergency restore failed: '+$_.Exception.Message)}}
 Save-Result 'fail' $reason;Say ('RESULT FAIL '+$reason);exit 1
}finally{foreach($k in $keys.Values){try{$k.Reset()|Out-Null;$k.Dispose()}catch{}};if($frameEvent){$frameEvent.Reset()|Out-Null;$frameEvent.Dispose()}}
