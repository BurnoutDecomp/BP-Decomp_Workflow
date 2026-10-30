from pathlib import Path
import re
R=Path(__file__).resolve().parent
old=R.parent/'director15_independent_review_20261028/successor_v6/camera_native_driver.ps1'
t=old.read_text(encoding='utf-8-sig')
head=r'''param([string]$RunDir,[string]$ExpectedSlotExe,[string]$GameLog,[int]$Slot=62180)
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
'''
def function(name):
    start=re.search(r'function '+re.escape(name)+r'(?=[ (])',t).start()
    end=t.find('\nfunction ',start+1)
    return t[start:end]+'\n'
parts=[head]+[function(n) for n in ['Lines','Command-Codes','Own','Wait-Line','Key-Observed','Console','Type-Setup','Capture-Phase']]
parts[-1]=parts[-1].replace('function Capture-Phase(', 'function Capture-PhaseRaw(')
parts.append(r'''
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
''')
(R/'Driver.ps1').write_text(''.join(parts),encoding='utf-8')
print('Generated Driver.ps1 with unchanged reviewed raw reader, ownership, key ACK and frame ACK functions.')
