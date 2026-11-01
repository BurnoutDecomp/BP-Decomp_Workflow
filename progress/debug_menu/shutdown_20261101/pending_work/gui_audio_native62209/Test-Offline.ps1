$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'CurrentSaveProgress.ps1');. (Join-Path $PSScriptRoot 'CaseHelpers.ps1')
. (Join-Path $PSScriptRoot 'Runtime.Helpers.ps1');. (Join-Path $PSScriptRoot 'CaptureAudit.ps1')
. (Join-Path $PSScriptRoot 'ConcurrentOwner.ps1');. (Join-Path $PSScriptRoot 'ConfigReadOnly.ps1')
$checks=[Collections.Generic.List[object]]::new()
function Check([bool]$Good,[string]$Name){$checks.Add(@{name=$Name;pass=$Good});if(!$Good){throw ('Offline check failed: '+$Name)}}
function Reject([string]$Name,[scriptblock]$Run){$bad=$false;try{&$Run|Out-Null}catch{$bad=$true};Check $bad $Name}
foreach($file in Get-ChildItem -LiteralPath $PSScriptRoot -File -Filter '*.ps1'){
 $t=$null;$e=$null;$null=[Management.Automation.Language.Parser]::ParseFile($file.FullName,[ref]$t,[ref]$e)
 Check ($e.Count -eq 0) ('parse '+$file.Name)
}
$run=New-BrnGuiAudioRunArguments
Check (!$run.ContainsKey('Audio') -and !$run.ContainsKey('SkipIntro')) 'actual Run omits Audio and SkipIntro'
Check ($run.PauseAt -ceq '22' -and $run.PauseTarget -ceq 'map' -and $run.MenuTapAt -ceq '30:Next,38:Prev' -and $run.UnpauseAt -ceq '46') 'actual scoped flow schedule'
$expected=Get-Content -Raw (Join-Path $PSScriptRoot 'CURRENT_SAVE_EXPECTED_PROGRESS.json')|ConvertFrom-Json
$raw=@('Signin state changed: signed-in','[profile-save] deserialised: isNewProfile=0 -> playIntroVideo=0')+@($expected.runtime_reference.raw_lines|ForEach-Object {$_.text})
$gate=Test-BrnPrivateFixtureProgress $raw $expected $expected.source_sha256
Check $gate.pass 'actual current-save helper accepts archived native load rows'
Check (!(Test-BrnPrivateFixtureProgress $raw $expected ('0'*64)).pass) 'actual current-save helper rejects wrong copied-save hash'
Check (!(Test-BrnPrivateFixtureProgress ($raw|ForEach-Object {$_ -replace 'isNewProfile gs=0','isNewProfile gs=1'}) $expected $expected.source_sha256).pass) 'actual current-save helper rejects new gameplay profile'
Check (Test-BrnGuiAudioPositiveMotion '[motion] n 1 pos 1 2 3 |v| 1.25 mph 2 gas 0.5 steer 0 ') 'actual movement predicate accepts positive gas/speed'
Check (!(Test-BrnGuiAudioPositiveMotion '[motion] n 1 pos 1 2 3 |v| 0.0 mph 0 gas 1.0 steer 0 ')) 'actual movement predicate rejects stationary gas'
Check (!(Test-BrnGuiAudioPositiveMotion '[motion] n 1 pos 1 2 3 |v| 1.0 mph 2 gas 0.0 steer 0 ')) 'actual movement predicate rejects no gas'
$token='[frame-request] pid=54460 slot=62209 seq=1 present=7 file=bb_000007.bmp'
$m=Get-NativeFrameAckMatch ('audio prefix '+$token) 54460 62209 1
Check ($m.Index -eq 13) 'actual frame ACK parser accepts attributed prefixed token'
Reject 'wrong frame PID' {Get-NativeFrameAckMatch $token 54461 62209 1}
Reject 'wrong frame slot' {Get-NativeFrameAckMatch $token 54460 62208 1}
Reject 'wrong frame sequence' {Get-NativeFrameAckMatch $token 54460 62209 2}
Reject 'wrong filename/present' {Get-NativeFrameAckMatch ($token.Replace('bb_000007','bb_000008')) 54460 62209 1}
Reject 'duplicate frame token' {Get-NativeFrameAckMatch ($token+$token) 54460 62209 1}
# Real owner predicate, with only external process enumeration supplied as an offline fixture.
function Get-BrnObservedGameProcesses {return @()}
$stage=@{allowed_concurrent_game=$null};$deadline=[DateTime]::UtcNow.AddMinutes(1)
$script:cleanupMode=$false;$script:logAccepted=$false;$script:nextCim=[DateTime]::UtcNow.AddMinutes(1)
$script:concurrentLedgerPath='';$script:maxConcurrentOtherCount=0;$script:concurrentObservationCount=0
$start=[DateTime]::UtcNow.AddMinutes(-1)
$owner=@{Pid=54460;Handle=1;Ticks=$start.Ticks;Path=(Join-Path $PSScriptRoot 'offline-owned.exe');Process=[pscustomobject]@{Id=54460;HasExited=$false;StartTime=$start}}
Own;Check ($script:concurrentObservationCount -eq 1) 'actual retained owner and independent empty concurrent set accepted'
$owner.Ticks++;Reject 'actual owner rejects start-time mismatch' {Own};$owner.Ticks--
$owner.Process.HasExited=$true;Reject 'actual owner rejects exited process' {Own};$owner.Process.HasExited=$false
# Execute the unchanged real frame capture function. Only process polling and arriving
# log/event data are mocked; BMP, SHA, CSV, cursor and sequence checks execute.
$temp=Join-Path $PSScriptRoot ('offline_fixture_'+[Guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($temp);$RunDir=$temp
$frames=Join-Path $temp 'frames';[void][IO.Directory]::CreateDirectory($frames)
$bmp=Join-Path $frames 'bb_000007.bmp';$csv=Join-Path $frames 'frames.csv';$ini=Join-Path $temp 'config.ini';$GameLog=Join-Path $temp 'prefix.log'
try{
 $script:gameLines=[Collections.Generic.List[string]]::new();$script:gameBytes=0L;$script:prefixHash=$null
 [IO.File]::WriteAllText($GameLog,"first`n",[Text.Encoding]::ASCII)
 $seen=Lines;Check ($seen.Count -eq 1 -and $seen[0] -ceq 'first') 'actual complete-line prefix reader accepts original bytes'
 [IO.File]::WriteAllText($GameLog,"other`n",[Text.Encoding]::ASCII)
 Reject 'actual complete-line prefix reader rejects same-length rewrite' {Lines}
 $bytes=[byte[]]::new(3686454);$bytes[0]=66;$bytes[1]=77
 [BitConverter]::GetBytes([int]1280).CopyTo($bytes,18);[BitConverter]::GetBytes([int]-720).CopyTo($bytes,22)
 [IO.File]::WriteAllBytes($bmp,$bytes);[IO.File]::WriteAllText($csv,"present,fixture`n7,synthetic`n")
 [IO.File]::WriteAllText($ini,"[Debug]`r`nSound Module/Sound/Console=2`r`n")
 Check (@(Get-Sound32DebugIniSoundKeys $ini).Count -eq 1) 'actual read-only Win32 INI guard rejects early Sound key'
 [IO.File]::WriteAllText($ini,"[Debug]`r`nGui Module/Test=1`r`n")
 Check (@(Get-Sound32DebugIniSoundKeys $ini).Count -eq 0) 'actual read-only Win32 INI guard permits no Sound key'
 function Own {}
 function Lines {return ,$script:fixtureLines}
 $script:fixtureLines=[Collections.Generic.List[string]]::new();$script:fixtureLines.Add('earlier line')
 $script:testAck='audio prefix '+$token;$script:sequence=0;$script:maxRawFrames=8
 $frameRows=[Collections.Generic.List[object]]::new();$owner=@{Pid=54460};$Slot=62209
 $frameEvent=[pscustomobject]@{}
 $frameEvent|Add-Member ScriptMethod Reset {}
 $frameEvent|Add-Member ScriptMethod Set {$script:fixtureLines.Add($script:testAck)}
 $frameEvent|Add-Member ScriptMethod WaitOne {param($ms) return $false}
 Capture-PhaseRaw @{name='offline_actual_capture'}
 Check ($frameRows.Count -eq 1 -and $frameRows[0].sequence -eq 1 -and $frameRows[0].ack_index -eq 1 -and $frameRows[0].request_cursor -eq 1 -and $frameRows[0].pid -eq 54460 -and $frameRows[0].slot -eq 62209) 'actual Capture-PhaseRaw BMP/CSV/SHA/owner/cursor pipeline'
 $audit=Complete-NativeBatchCaptureAudit -RunDir $temp -Rows $frameRows.ToArray() -Slot 62209 -MaxFrames 8
 Check $audit.pass 'actual capture audit accepts real fixture file/hash'
 $script:frameRows=[Collections.Generic.List[object]]::new();1..8|ForEach-Object {$script:frameRows.Add(@{})}
 Reject 'actual capture refuses ninth frame before event' {Capture-PhaseRaw @{name='ninth'}}
}finally{
 foreach($path in @($bmp,$csv,$ini,$GameLog,(Join-Path $temp 'CAPTURE_AUDIT.json'))){
  if(![IO.Path]::GetFullPath($path).StartsWith([IO.Path]::GetFullPath($temp)+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Unsafe offline cleanup target'}
  if(Test-Path -LiteralPath $path){Remove-Item -LiteralPath $path}
 }
 Remove-Item -LiteralPath $frames;Remove-Item -LiteralPath $temp
}
$inputs=@{}
foreach($name in @('Test-Offline.ps1','Runtime.Helpers.ps1','CaseHelpers.ps1','CurrentSaveProgress.ps1','CaptureAudit.ps1','ConcurrentOwner.ps1','ConfigReadOnly.ps1','Case.ps1','Driver.ps1')){$inputs[$name]=(Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $name) -Algorithm SHA256).Hash.ToLowerInvariant()}
@{pass=$true;count=$checks.Count;checks=$checks.ToArray();actual_helpers_executed=$true;input_sha256=$inputs;native_run=$false;temporary_fixtures_removed=(!(Test-Path $temp));normal_written=$false}|ConvertTo-Json -Depth 8|Set-Content (Join-Path $PSScriptRoot 'OFFLINE_TESTS.json') -Encoding utf8
Write-Output ('Offline GUI62209 helpers: '+$checks.Count+' checks passed; no stage/native run.')
