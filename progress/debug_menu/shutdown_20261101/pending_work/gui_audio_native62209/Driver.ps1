param([string]$GameExe,[string]$RunDir)
$ErrorActionPreference='Stop';$Slot=62209
$stage=Get-Content -Raw (Join-Path $PSScriptRoot 'STAGING.json')|ConvertFrom-Json
$pins=Get-Content -Raw (Join-Path $PSScriptRoot 'SOURCE_PINS.json')|ConvertFrom-Json
. (Join-Path $PSScriptRoot 'CurrentSaveProgress.ps1');. (Join-Path $PSScriptRoot 'ConcurrentOwner.ps1')
. (Join-Path $PSScriptRoot 'CaptureAudit.ps1');. (Join-Path $PSScriptRoot 'CaseHelpers.ps1')
$GameLog=Join-Path (Split-Path $GameExe -Parent) 'BrnGame.log';$flowLog=Join-Path $RunDir 'flow_run.console.log'
$started=[DateTime]::UtcNow;$deadline=$started.AddSeconds(500);$owner=$null;$frameEvent=$null
$script:gameLines=[Collections.Generic.List[string]]::new();$script:gameBytes=0L;$script:prefixHash=$null
$script:nextCim=[DateTime]::MinValue;$script:assertCursor=0;$script:logAccepted=$false;$script:cleanupMode=$false
$script:concurrentLedgerPath=Join-Path $RunDir 'CONCURRENT_GAME_RUNTIME.jsonl';$script:maxConcurrentOtherCount=0;$script:concurrentObservationCount=0
$script:sequence=0;$script:maxRawFrames=8;$frameRows=[Collections.Generic.List[object]]::new();$cues=[ordered]@{}
. (Join-Path $PSScriptRoot 'Runtime.Helpers.ps1')
function Shared-Text([string]$Path){
 if(!(Test-Path -LiteralPath $Path)){return ''}
 $s=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete));$r=[IO.StreamReader]::new($s)
 try{return $r.ReadToEnd()}finally{$r.Dispose();$s.Dispose()}
}
function Wait-FlowCue([string]$Pattern){
 $until=[DateTime]::UtcNow.AddSeconds(80)
 do{Own;$text=Shared-Text $flowLog;$m=[regex]::Match($text,$Pattern,[Text.RegularExpressions.RegexOptions]::Multiline);if($m.Success){return @{line=$m.Value;index=$m.Index;source=$flowLog}};Start-Sleep -Milliseconds 50}while([DateTime]::UtcNow -lt $until)
 throw ('Missing actual flow input receipt: '+$Pattern)
}
function Wait-Motion([int]$Cursor){
 $until=[DateTime]::UtcNow.AddSeconds(50)
 do{Own;$all=Lines;for($i=$Cursor;$i -lt $all.Count;$i++){if(Test-BrnGuiAudioPositiveMotion $all[$i]){return @{line=$all[$i];index=$i}}};Start-Sleep -Milliseconds 50}while([DateTime]::UtcNow -lt $until)
 throw 'Missing fresh positive gas and movement in owned game'
}
function Capture([string]$Name){Capture-PhaseRaw @{name=$Name}}
try{
 if($stage.slot -ne $Slot -or [IO.Path]::GetFullPath($GameExe) -ine [IO.Path]::GetFullPath((Join-Path $stage.exe_dir 'Burnout_PC.exe')) -or (Get-FileHash $GameExe -Algorithm SHA256).Hash.ToLowerInvariant() -cne $pins.candidate.exe_sha256){throw 'Wrong GUI62209 executable binding'}
 @{status='ready';driver_pid=$PID;slot=$Slot;max_frames=8;scoped_game_inputs_created=0}|ConvertTo-Json|Set-Content (Join-Path $RunDir 'DRIVER_READY.json')
 while(!$owner -and [DateTime]::UtcNow -lt $deadline){
  foreach($p in @(Get-Process -Name Burnout_PC -ErrorAction SilentlyContinue)){
   try{if($p.StartTime.ToUniversalTime() -lt $started){continue};$c=Get-CimInstance Win32_Process -Filter ('ProcessId='+$p.Id)
    if($c.ExecutablePath -and [IO.Path]::GetFullPath($c.ExecutablePath) -ieq [IO.Path]::GetFullPath($GameExe)){
     $handle=$p.Handle;if(!$handle -or $p.HasExited){throw 'No retained owned process handle'}
     if($owner){throw 'Multiple candidate-image game processes'}
     $owner=@{Process=$p;Handle=$handle;Pid=$p.Id;Ticks=$p.StartTime.ToUniversalTime().Ticks;Path=[IO.Path]::GetFullPath($c.ExecutablePath)}
    }
   }catch{if($owner){throw}}
  };if(!$owner){Start-Sleep -Milliseconds 50}
 }
 if(!$owner){throw 'Owned GUI62209 game missing'};$script:logAccepted=$true;Own
 $owner|Select-Object Pid,Ticks,Path|ConvertTo-Json|Set-Content (Join-Path $RunDir 'CAPTURE_OWNER.json')
 $frameEvent=[Threading.EventWaitHandle]::new($false,[Threading.EventResetMode]::ManualReset,('Local\BurnoutPC_FrameRequest_{0}_{1}' -f $owner.Pid,$Slot))
 $cues.ea=Wait-Line "^\[BootVideos\] play 'EAFranchise'" 0 120;Start-Sleep -Milliseconds 750;Capture 'ea_boot'
 $cues.criterion=Wait-Line "^\[BootVideos\] play 'Criterion'" $cues.ea.index 90;Start-Sleep -Milliseconds 750;Capture 'criterion_boot'
 [void](Wait-Line '^\[one-profile\].* same=1 ' 0 150)
 $expected=Get-Content -Raw (Join-Path $PSScriptRoot 'CURRENT_SAVE_EXPECTED_PROGRESS.json')|ConvertFrom-Json
 $gate=Test-BrnPrivateFixtureProgress (Lines).ToArray() $expected $stage.profile_sha256
 $gate|ConvertTo-Json -Depth 12|Set-Content (Join-Path $RunDir 'CURRENT_SAVE_LOAD_GATE.json') -Encoding utf8
 if(!$gate.pass){throw ('Private current-save load mismatch: '+($gate.problems -join '; '))}
 $cues.exit=Wait-Line '^=== CarSelectManager: Exit state is finished\.$' 0 150
 $cues.before=Wait-Motion ($cues.exit.index+1);Capture 'driving_before_pause'
 $cursor=(Lines).Count;$cues.map=Wait-Line "^\[screen\] ENTER 'CN_MAP_MAIN'" $cursor 80
 $cues.paused=Wait-Line '^\[sim-pause\] action 86 -> PAUSED' $cursor 20
 Start-Sleep -Milliseconds 500;Capture 'map_open'
 $cues.next=Wait-FlowCue '^\[flow\] MENU tap #1 \(Next\) at DRIVING\+[^\r\n]+';Start-Sleep -Milliseconds 500;Capture 'map_after_next'
 $cues.prev=Wait-FlowCue '^\[flow\] MENU tap #2 \(Prev\) at DRIVING\+[^\r\n]+';Start-Sleep -Milliseconds 500;Capture 'map_after_prev'
 $cursor=(Lines).Count;$cues.unpause=Wait-FlowCue '^\[flow\] UNPAUSE tap #1[^\r\n]+'
 $cues.resumed=Wait-Line '^\[sim-pause\] action 87 -> RESUMED' $cursor 25
 $cues.after=Wait-Motion ($cues.resumed.index+1);Capture 'driving_resumed'
 $cursor=(Lines).Count;Start-Sleep -Seconds 2;$cues.continues=Wait-Motion $cursor;Capture 'driving_continues'
 Own;$null=Complete-NativeBatchCaptureAudit -RunDir $RunDir -Rows $frameRows.ToArray() -Slot $Slot -MaxFrames 8
 $result=Join-Path $RunDir 'driver-result.json'
 @{status='complete_awaiting_visual_review';slot=$Slot;process_id=$owner.Pid;image=$owner.Path;start_ticks=[string]$owner.Ticks;exe_sha256=$pins.candidate.exe_sha256;profile_pass=$gate.pass;frame_count=$frameRows.Count;frames=$frameRows.ToArray();cues=$cues;audible_proof=$false;native_sweep11_13_proof=$false;control_credit=0;normal_written=$false}|ConvertTo-Json -Depth 12|Set-Content $result -Encoding utf8
 & (Join-Path $PSScriptRoot 'Request-HarnessPhaseDone.ps1') -ProcessId $owner.Pid -Slot $Slot -ExpectedImagePath $owner.Path -ExpectedStartUtc $owner.Process.StartTime.ToUniversalTime().ToString('o') -WitnessPath $result -WitnessSha256 (Get-FileHash $result -Algorithm SHA256).Hash.ToLowerInvariant() -ReceiptPath (Join-Path $RunDir 'PHASE_DONE_REQUEST.json')
}catch{
 @{status='fail';error=$_.Exception.Message;slot=$Slot;frames=$frameRows.ToArray();cues=$cues;normal_written=$false}|ConvertTo-Json -Depth 12|Set-Content (Join-Path $RunDir 'DRIVER_ERROR.json') -Encoding utf8
 throw
}finally{if($frameEvent){$frameEvent.Reset()|Out-Null;$frameEvent.Dispose()}}
