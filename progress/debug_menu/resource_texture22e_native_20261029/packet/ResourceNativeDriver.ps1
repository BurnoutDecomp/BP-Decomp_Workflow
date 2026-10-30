param(
  [Parameter(Mandatory=$true)][ValidateSet('resource_windows','resource_stats_allocator')][string]$Suite,
  [Parameter(Mandatory=$true)][string]$GameLog,
  [Parameter(Mandatory=$true)][string]$GameDir,
  [Parameter(Mandatory=$true)][string]$DataDir,
  [Parameter(Mandatory=$true)][string]$RunDir,
  [Parameter(Mandatory=$true)][ValidateRange(1,65535)][int]$Slot,
  [int]$TimeoutSec = 220
)
$ErrorActionPreference = 'Stop'
$packetRoot = Split-Path -Parent $PSCommandPath
$driverPlan=Get-Content -LiteralPath (Join-Path $packetRoot 'CASE_PLAN.json') -Raw|ConvertFrom-Json
. (Join-Path $packetRoot 'TextureProviderReadiness.ps1')
$candidateScopeProperty=$driverPlan.candidate_execution_scope.suites.PSObject.Properties[$Suite]
if($null -eq $candidateScopeProperty){throw "CASE_PLAN has no candidate-specific execution scope for $Suite"}
$candidateScope=$candidateScopeProperty.Value
$privateDisplayPlan=$driverPlan.protected_config_source.private_display_config
if($null -eq $privateDisplayPlan -or [int]$privateDisplayPlan.private_values.Width -ne 1280 -or
   [int]$privateDisplayPlan.private_values.Height -ne 720 -or [int]$privateDisplayPlan.private_values.Fullscreen -ne 0 -or
   [long]$privateDisplayPlan.capture.frame_file_bytes -ne 3686454 -or
   [int]$privateDisplayPlan.capture.header_bytes -ne 54 -or [int]$privateDisplayPlan.capture.bytes_per_pixel -ne 4 -or
   [long]$privateDisplayPlan.capture.frame_file_bytes -ne ([long]$privateDisplayPlan.capture.header_bytes + [long]$privateDisplayPlan.private_values.Width*[long]$privateDisplayPlan.private_values.Height*[long]$privateDisplayPlan.capture.bytes_per_pixel) -or
   [long]$privateDisplayPlan.capture.reserve_bytes_per_frame -ne 8388608){throw 'Driver plan does not bind the reviewed 1280x720 windowed capture extent and frame reserve.'}
$script:expectedCaptureWidth=[int]$privateDisplayPlan.private_values.Width
$script:expectedCaptureHeight=[int]$privateDisplayPlan.private_values.Height
$script:expectedFrameFileBytes=[long]$privateDisplayPlan.capture.frame_file_bytes
$script:frameReserveBytes=[long]$privateDisplayPlan.capture.reserve_bytes_per_frame
$slotDir = [IO.Path]::GetFullPath($GameDir)
$dataDir = [IO.Path]::GetFullPath($DataDir)
$runDir = [IO.Path]::GetFullPath($RunDir)
$frameDir = Join-Path $runDir 'frames' # Setup context intentionally has no FrameDir member.
$evidenceDir = Join-Path $runDir 'resource_evidence'
New-Item -ItemType Directory -Force $frameDir,$evidenceDir | Out-Null
$token = ([IO.Path]::GetFileName($runDir) -replace '[^A-Za-z0-9]','')
if ($token.Length -gt 10) { $token = $token.Substring($token.Length - 10) }
if (!$token) { $token = [Guid]::NewGuid().ToString('N').Substring(0,10) }
$runPrefix = 'r' + $token.ToLowerInvariant()
$driverLog = Join-Path $runDir 'resource_driver.log'
$driverReceiptPath = Join-Path $runDir 'RESOURCE_DRIVER_RECEIPT.json'
$frameReceipts = [System.Collections.Generic.List[object]]::new()
$scriptReceipts = [System.Collections.Generic.List[object]]::new()
$inputReceipts = [System.Collections.Generic.List[object]]::new()
$readbackGroups = [System.Collections.Generic.List[object]]::new()
$baselineValues = @{}
$expectedCurrentValues = @{}
$script:latestMotionNumber = -1
$script:lastBoundKeyReleaseMotionNumber = -1
$processIdentity = $null
$stimulusProcessIdentity = $null
$stimulusProcess = $null
$script:stimulusProcessHandle = [IntPtr]::Zero
$gameProcess = $null
$script:gameProcessHandle = [IntPtr]::Zero
$frameEvent = $null
$dumpMutex = $null
$dumpMutexHeld = $false
$restoreReceipt = $null
$restoreMode = $false
$restoreDeadline = $null
$driverSuccessful = $false
$script:logTailByte = $null
$script:logTailLine = $null
$script:logTailCarry = ''
$keyEvents = @{}
$failure = $null
$startedAt = [DateTime]::UtcNow

function Write-Log([string]$Text) {
  Add-Content -LiteralPath $driverLog -Encoding UTF8 -Value ('{0:o} {1}' -f [DateTime]::UtcNow,$Text)
}
function Write-Json([string]$Path,[object]$Value) {
  [IO.File]::WriteAllText($Path,($Value | ConvertTo-Json -Depth 30)+"`n",[Text.UTF8Encoding]::new($false))
}
function Get-SharedText([string]$Path) {
  if (!(Test-Path -LiteralPath $Path -PathType Leaf)) { return '' }
  $fs=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete)
  try { $sr=[IO.StreamReader]::new($fs); try { return $sr.ReadToEnd() } finally { $sr.Dispose() } }
  finally { if ($fs) { $fs.Dispose() } }
}
function Get-CompleteLogSnapshot {
  $fs=[IO.File]::Open($GameLog,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete)
  try {
    $snapshotLength=[long]$fs.Length
    if($snapshotLength -gt [int]::MaxValue){throw 'The private game log exceeds the supported single-snapshot size.'}
    $bytes=[byte[]]::new([int]$snapshotLength)
    $offset=0
    while($offset -lt $bytes.Length){
      $read=$fs.Read($bytes,$offset,$bytes.Length-$offset)
      if($read -le 0){throw 'The private game log changed/truncated while taking one indexed snapshot.'}
      $offset+=$read
    }
  } finally { $fs.Dispose() }
  $raw=[Text.Encoding]::UTF8.GetString($bytes,0,$offset)
  if($raw.Length -gt 0 -and $raw[0] -eq [char]0xFEFF){$raw=$raw.Substring(1)}
  $lastNewline=$raw.LastIndexOf("`n")
  if($lastNewline -ge 0){$completeText=$raw.Substring(0,$lastNewline+1);$carry=$raw.Substring($lastNewline+1)}
  else{$completeText='';$carry=$raw}
  $lines=[System.Collections.Generic.List[string]]::new()
  if($completeText.Length -gt 0){
    $parts=[regex]::Split($completeText,"`r?`n")
    $count=$parts.Length
    if($completeText.EndsWith("`n")){$count--}
    for($i=0;$i -lt $count;$i++){$lines.Add([string]$parts[$i])}
  }
  return [pscustomobject]@{byte_count=[long]$snapshotLength;complete_line_count=[int]$lines.Count;lines=$lines.ToArray();trailing_partial=$carry;text=$raw}
}
function Get-LogLines {
  $snapshot=Get-CompleteLogSnapshot
  return ,$snapshot.lines
}
function Normalize-NativeValue([string]$Path,[string]$Value) {
  $v=$Value.Trim()
  if($Path -in @('Core/Resource/Bundle Window','Core/Resource/Show bundle loader queue','Core/Resource/Show Share Test','GameDataModule/Show HUD')){
    if($v -match '^(?i:true|1|yes)$'){return 'TRUE'}
    if($v -match '^(?i:false|0|no)$'){return 'FALSE'}
  }
  if($Path -eq 'Core/Resource/Max Partial Fixups' -or $Path -in @('GameDataModule/Slots Used','GameDataModule/Slots Free')){
    $n=0L
    if([long]::TryParse($v,[Globalization.NumberStyles]::Integer,[Globalization.CultureInfo]::InvariantCulture,[ref]$n)){return $n.ToString([Globalization.CultureInfo]::InvariantCulture)}
  }
  if($v.Length -ge 2 -and $v.StartsWith('"') -and $v.EndsWith('"')){$v=$v.Substring(1,$v.Length-2).Replace('\\','\').Replace('\"','"')}
  return $v
}
function Convert-BaselineToCommandValue([string]$Path,[string]$Value) {
  $normalized=Normalize-NativeValue $Path $Value
  if($Path -in @('Core/Resource/Bundle Window','Core/Resource/Show bundle loader queue','Core/Resource/Show Share Test','GameDataModule/Show HUD','Core/Resource/Max Partial Fixups')){return $normalized}
  if($Path -in @('GameDataModule/Slots Used','GameDataModule/Slots Free')){throw "Refusing to write read-only allocator value $Path."}
  if($normalized -match '[\r\n]'){throw "Unsafe multiline native baseline for $Path."}
  return '"'+$normalized.Replace('"','\"')+'"'
}
function Compare-NativeValue([string]$Path,[string]$A,[string]$B) {
  return ((Normalize-NativeValue $Path $A) -ceq (Normalize-NativeValue $Path $B))
}
function Find-ReadbackGroup([string]$Name) {
  return @($readbackGroups | Where-Object {$_.script -ceq ($Name+'.txt')} | Select-Object -Last 1)
}
function Wait-FlowDriving([int]$Seconds=120) {
  $path=Join-Path $runDir 'run_case.stdout.log'
  $deadline=[DateTime]::UtcNow.AddSeconds($Seconds)
  while([DateTime]::UtcNow -lt $deadline){
    Assert-OwnedProcess
    $text=Get-SharedText $path
    $m=[regex]::Match($text,'(?m)^\s*\|\s*\[flow\] (?:DRIVING via [^\r\n]+|input [^\r\n]+\(DRIVING\+[^)\r\n]*\))')
    if($m.Success){return [ordered]@{line=$m.Value.Trim();observed_utc=[DateTime]::UtcNow.ToString('o')}}
    Start-Sleep -Milliseconds 250
  }
  throw 'Flow did not report its actual DRIVING phase before resource action captures.'
}
function Get-MotionRows {
  $rx='(?m)^\[motion\] n (?<n>\d+) pos (?<x>[-+0-9.eE]+) (?<y>[-+0-9.eE]+) (?<z>[-+0-9.eE]+) at .*? \|v\| (?<speed>[-+0-9.eE]+) mph (?<mph>[-+0-9.eE]+) .* engine (?<engine>\d+)\r?$'
  $lines=Get-LogLines
  $rows=[System.Collections.Generic.List[object]]::new()
  for($i=0;$i -lt $lines.Count;$i++){
    $m=[regex]::Match($lines[$i],$rx)
    if($m.Success){$rows.Add([pscustomobject]@{n=[int]$m.Groups['n'].Value;x=[double]$m.Groups['x'].Value;y=[double]$m.Groups['y'].Value;z=[double]$m.Groups['z'].Value;speed=[double]$m.Groups['speed'].Value;engine=[int]$m.Groups['engine'].Value;line_index=$i;line=$lines[$i]})}
  }
  return ,$rows.ToArray()
}
function Wait-NewPlayerMotion([int]$AfterNumber,[int]$Seconds=12) {
  $deadline=[DateTime]::UtcNow.AddSeconds($Seconds)
  while([DateTime]::UtcNow -lt $deadline){
    Assert-OwnedProcess
    $rows=Get-MotionRows
    $fresh=@($rows|Where-Object {$_.n -gt $AfterNumber}|Sort-Object n)
    if($fresh.Count -gt 0){
      $row=$fresh[-1]
      if($row.engine -ne 2){throw "Fresh selected-player motion transitioned away from engine=2: $($row.line)"}
      if($row.n -le $script:latestMotionNumber){throw 'Selected-player motion sequence did not increase strictly.'}
      $script:latestMotionNumber=$row.n
      return $row
    }
    Start-Sleep -Milliseconds 250
  }
  throw "No fresh selected-player engine=2 motion row after n=$AfterNumber."
}
function Assert-PhaseReadbacks([object]$Phase) {
  $groupList=@(Find-ReadbackGroup ([string]$Phase.script_name))
  if($groupList.Count -ne 1){throw "Indexed raw value receipt is missing for phase $($Phase.name)."}
  $group=$groupList[0]
  $valueByPath=@{}
  for($i=0;$i -lt $group.receipts.Count;$i++){$valueByPath[[string]$group.receipts[$i].path]=[string]$group.value_receipts[$i].value}
  foreach($command in $Phase.commands){
    $m=[regex]::Match([string]$command,'^SET "([^"]+)" (.+)$')
    if(!$m.Success){continue}
    $path=$m.Groups[1].Value
    if(!$valueByPath.ContainsKey($path)){throw "Phase $($Phase.name) readback omitted its written variable $path."}
    $actual=$valueByPath[$path]
    $requested=$m.Groups[2].Value.Trim()
    if($path -in @('GameDataModule/Slots Used','GameDataModule/Slots Free')){continue}
    if(!(Compare-NativeValue $path $actual $requested)){throw "Phase $($Phase.name) requested $path=$requested but indexed native value was '$actual'."}
  }
  foreach($path in $valueByPath.Keys){$expectedCurrentValues[$path]=$valueByPath[$path]}
  $Phase | Add-Member -NotePropertyName validated_readback_group_index -NotePropertyValue ($readbackGroups.Count-1) -Force
}
function New-RestoreScript([string]$Name,[string[]]$Paths) {
  $pairs=@{
    'Core/Resource/Heap Window'='H';'Core/Resource/Histogram'='I';'Core/Resource/Type Stats'='T';'Core/Resource/Type Stats Mode'='M';
    'Core/Resource/Texture Window'='X';'Core/Resource/Sort By'='S';'Core/Resource/Draw'='D';'Core/Resource/Bundle Window'='B';
    'Core/Resource/Show bundle loader queue'='Q';'Core/Resource/Max Partial Fixups'='MP';'Core/Resource/ShareTest0'='S0';
    'Core/Resource/ShareTest1'='S1';'Core/Resource/Show Share Test'='SV';'GameDataModule/Show HUD'='HUD'
  }
  $lines=[System.Collections.Generic.List[string]]::new()
  foreach($path in $Paths){
    if(!$baselineValues.ContainsKey($path)){throw "Cannot restore $path without a same-run indexed baseline."}
    if(!$pairs.ContainsKey($path)){throw "No source-bound alias exists for restore path $path."}
    $alias=$pairs[$path]
    $setValue=Convert-BaselineToCommandValue $path ([string]$baselineValues[$path])
    $lines.Add(('SET "{0}" {1}' -f $path,$setValue))
    Add-VariableRead $lines $alias $path
  }
  return Write-StageScript $Name $lines.ToArray()
}
function Invoke-DumpStats([string]$ScriptName) {
  $globalPath='D:\cgsresourcedump_0.txt'
  $copyPath=Join-Path $evidenceDir 'cgsresourcedump_0.txt'
  $dumpMutex=[Threading.Mutex]::new($false,'Local\BurnoutPC_ResourceDumpStats_v1')
  $dumpMutexHeld=$false
  $hash=$null
  try{
    try{$dumpMutexHeld=$dumpMutex.WaitOne(30000)}catch [Threading.AbandonedMutexException]{$dumpMutexHeld=$true}
    if(!$dumpMutexHeld){throw 'Timed out waiting for the Resource Dump Stats named mutex.'}
    if(Test-Path -LiteralPath $globalPath){throw 'The serialized dump path is occupied while holding its action mutex; no existing file will be overwritten or removed.'}
    Run-ConsoleScript $ScriptName
    $null=Wait-StableFile $globalPath 90 'native Dump Stats pool table under mutex'
    Copy-Item -LiteralPath $globalPath -Destination $copyPath
    $hash=(Get-FileHash -LiteralPath $copyPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $actual=(Get-FileHash -LiteralPath $globalPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if($actual -cne $hash){throw 'The fixed dump path changed after the owned copy; preserving the file.'}
    Remove-Item -LiteralPath $globalPath -Force
    if(Test-Path -LiteralPath $globalPath){throw 'Owned Dump Stats file remained after hash-matched removal.'}
    $parsed=Parse-PoolDump $copyPath
    return [ordered]@{path=$globalPath;copy='resource_evidence/cgsresourcedump_0.txt';sha256=$hash;bytes=(Get-Item -LiteralPath $copyPath).Length;pool_count=$parsed.rows.Count;selected_pool=[string]$parsed.chosen.name;rows=$parsed.rows;cleanup='deleted_hash_match_under_mutex';mutex='Local\BurnoutPC_ResourceDumpStats_v1'}
  } finally {
    if($dumpMutexHeld){try{$dumpMutex.ReleaseMutex()}catch{}}
    if($null -ne $dumpMutex){$dumpMutex.Dispose()}
  }
}
function Write-StageScript([string]$Name,[string[]]$Lines) {
  if ($Name -notmatch '^[A-Za-z0-9.-]+$') { throw "Unsafe staged script name: $Name" }
  $Path=Join-Path $slotDir ($Name+'.txt')
  if (Test-Path -LiteralPath $Path) { throw "Refusing to overwrite staged script: $Path" }
  [IO.File]::WriteAllLines($Path,$Lines,[Text.Encoding]::ASCII)
  $evidencePath=Join-Path $evidenceDir ([IO.Path]::GetFileName($Path))
  Copy-Item -LiteralPath $Path -Destination $evidencePath
  $scriptReceipts.Add([pscustomobject]@{name=[IO.Path]::GetFileName($Path);path=$Path;evidence_path=$evidencePath;sha256=(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant();bytes=(Get-Item -LiteralPath $Path).Length;lines=$Lines})
  return $Path
}
function Add-VariableRead([System.Collections.Generic.List[string]]$Lines,[string]$Alias,[string]$Path) {
  # Original path ACK, then the variable alias as a bare typed value, then the same path ACK.
  $Lines.Add(('ALIAS {0} "{1}"' -f $Alias,$Path))
  $Lines.Add(('ALIAS {0}' -f $Alias))
  $Lines.Add($Alias)
  $Lines.Add(('ALIAS {0}' -f $Alias))
}
function Add-FunctionAlias([System.Collections.Generic.List[string]]$Lines,[string]$Alias,[string]$Path) {
  $Lines.Add(('ALIAS {0} "{1}"' -f $Alias,$Path))
  $Lines.Add(('ALIAS {0}' -f $Alias))
}
function Assert-OwnedProcess([bool]$ForCleanup=$false) {
  if ($null -eq $gameProcess -or $null -eq $processIdentity) { throw 'Owned game process identity was not set.' }
  $policyAbortPath=Join-Path $runDir 'RESOURCE_RUN_POLICY_ABORT.json'
  if(!$ForCleanup -and !$restoreMode -and (Test-Path -LiteralPath $policyAbortPath -PathType Leaf)){
    $abort=Get-Content -LiteralPath $policyAbortPath -Raw|ConvertFrom-Json
    throw ('Run policy violation requested input stop: '+[string]$abort.reason)
  }
  $gameProcess.Refresh()
  if ($gameProcess.HasExited) { throw "Owned game process $($gameProcess.Id) exited; no further input will be sent." }
  if($script:gameProcessHandle -eq [IntPtr]::Zero -or $gameProcess.Handle -ne $script:gameProcessHandle){throw 'Retained owned-process handle changed or was not forced at adoption.'}
  $now=[DateTime]::UtcNow
  $deadline=if($ForCleanup -and $restoreMode){$restoreDeadline}else{$script:overallDeadline}
  if ($null -ne $deadline -and $now -ge $deadline) { throw 'Owned process input deadline expired; no further key event will be sent.' }
  if ($now -ge $script:nextCimCheck) {
    $cim=Get-CimInstance Win32_Process -Filter "ProcessId=$($gameProcess.Id)" -ErrorAction Stop
    if ($null -eq $cim -or !$cim.ExecutablePath -or [IO.Path]::GetFullPath([string]$cim.ExecutablePath) -ine $processIdentity.image_path) {
      throw 'Periodic owner check failed: PID no longer names the exact staged executable.'
    }
    $gameProcess.Refresh()
    if ($gameProcess.HasExited -or $gameProcess.StartTime.ToUniversalTime().Ticks -ne [long]$processIdentity.start_ticks) {
      throw 'Periodic owner check failed: retained process handle/start time changed.'
    }
    $script:nextCimCheck=$now.AddSeconds(8)
  }
}
function Wait-OwnedMilliseconds([int]$Milliseconds,[bool]$ForCleanup=$false) {
  $left=$Milliseconds
  while($left -gt 0){
    Assert-OwnedProcess $ForCleanup
    $step=[Math]::Min(40,$left)
    Start-Sleep -Milliseconds $step
    $left-=$step
  }
}
function Read-NewCompleteLogLines([bool]$ForCleanup=$false) {
  if($null -eq $script:logTailByte -or $null -eq $script:logTailLine){throw 'Incremental key-trace reader was not initialized.'}
  Assert-OwnedProcess $ForCleanup
  $fs=[IO.File]::Open($GameLog,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete)
  try{
    if($fs.Length -lt [long]$script:logTailByte){throw 'Owned game log was truncated during incremental key acknowledgement.'}
    $null=$fs.Seek([long]$script:logTailByte,[IO.SeekOrigin]::Begin)
    $sr=[IO.StreamReader]::new($fs,[Text.Encoding]::UTF8,$false,4096,$true)
    try{$newText=$sr.ReadToEnd();$script:logTailByte=[long]$fs.Position}finally{$sr.Dispose()}
  }finally{$fs.Dispose()}
  $rows=[System.Collections.Generic.List[object]]::new()
  if($newText.Length -eq 0){return ,$rows.ToArray()}
  $combined=$script:logTailCarry+$newText
  $parts=[regex]::Split($combined,"`r?`n")
  $hasTrailingNewline=$combined.EndsWith("`n")
  $completeCount=$parts.Length-1
  if($hasTrailingNewline){$script:logTailCarry=''}else{$script:logTailCarry=[string]$parts[$parts.Length-1]}
  for($i=0;$i -lt $completeCount;$i++){$rows.Add([pscustomobject]@{line=[string]$parts[$i];line_index=[int]$script:logTailLine});$script:logTailLine++}
  return ,$rows.ToArray()
}
function Wait-LogTrace([string]$Pattern,[int]$Milliseconds=3000,[bool]$ForCleanup=$false,[string]$Description='native log receipt') {
  $startLine=[int]$script:logTailLine
  $deadline=[DateTime]::UtcNow.AddMilliseconds($Milliseconds)
  while([DateTime]::UtcNow -lt $deadline){
    $newLines=Read-NewCompleteLogLines $ForCleanup
    foreach($row in $newLines){if($row.line -match $Pattern){return [ordered]@{line=$row.line;line_index=$row.line_index}}}
    Wait-OwnedMilliseconds 40 $ForCleanup
  }
  throw "Native $Description was not observed after complete-line cursor $startLine."
}
function Wait-KeyTrace([int]$Ascii,[int]$Milliseconds=3000,[bool]$ForCleanup=$false) {
  return Wait-LogTrace ('^\[debug-ui\].*\bkey='+$Ascii+'(?:\s|$)') $Milliseconds $ForCleanup ('debug UI ASCII '+$Ascii)
}
function Tap-KeyUntilTrace([int]$Key,[string]$Pattern,[string]$Description,[int]$Milliseconds=3000,[bool]$ForCleanup=$false) {
  Assert-OwnedProcess $ForCleanup
  $null=Read-NewCompleteLogLines $ForCleanup
  try {
    Assert-OwnedProcess $ForCleanup
    $keyEvents[$Key].Set()|Out-Null
    return Wait-LogTrace $Pattern $Milliseconds $ForCleanup $Description
  } finally {
    try{$keyEvents[$Key].Reset()|Out-Null}catch{}
  }
}
function Toggle-ConsoleOpen {
  $ack=Tap-KeyUntilTrace 192 '^\[debug-ui\] event=9 visible=1 .* key=0$' 'debug console open transition' 3000 $restoreMode
  $inputReceipts.Add([pscustomobject]@{kind='debug_console_toggle_ack';transition='open';virtual_key=192;expected_event=9;expected_visible=1;line=$ack.line;line_index=$ack.line_index;slot=$Slot;utc=[DateTime]::UtcNow.ToString('o')})
  return $ack
}
function Tap-Key([int]$Key,[bool]$Shift=$false,[bool]$Control=$false,[int]$ExpectedAscii=-1) {
  Assert-OwnedProcess $restoreMode
  $null=Read-NewCompleteLogLines $restoreMode
  try {
    if ($Shift) { Assert-OwnedProcess $restoreMode; $keyEvents[16].Set() | Out-Null }
    if ($Control) { Assert-OwnedProcess $restoreMode; $keyEvents[17].Set() | Out-Null }
    Wait-OwnedMilliseconds 30 $restoreMode
    Assert-OwnedProcess $restoreMode; $keyEvents[$Key].Set() | Out-Null
    if($ExpectedAscii -ge 0){$keyAck=Wait-KeyTrace $ExpectedAscii 3000 $restoreMode}
    else{Wait-OwnedMilliseconds 90 $restoreMode;$keyAck=$null}
  } finally {
    try {$keyEvents[$Key].Reset()|Out-Null} catch {}
    try {$keyEvents[16].Reset()|Out-Null} catch {}
    try {$keyEvents[17].Reset()|Out-Null} catch {}
  }
  if($ExpectedAscii -lt 0){Wait-OwnedMilliseconds 90 $restoreMode}
  if($null -ne $keyAck){$inputReceipts.Add([pscustomobject]@{kind='debug_key_ack';virtual_key=$Key;ascii=$ExpectedAscii;line=$keyAck.line;line_index=$keyAck.line_index;slot=$Slot;utc=[DateTime]::UtcNow.ToString('o')})}
}
function Trigger-BoundScript([int]$Key,[string]$Name,[int]$Cursor,[int]$MotionBefore,[bool]$ForCleanup=$false) {
  Assert-OwnedProcess $ForCleanup
  $null=Read-NewCompleteLogLines $ForCleanup
  $group=$null
  try {
    Assert-OwnedProcess $ForCleanup
    $keyEvents[$Key].Set()|Out-Null
    $group=Collect-ReadbackGroup $Name $Cursor $ForCleanup
  } finally {
    try{$keyEvents[$Key].Reset()|Out-Null}catch{}
  }
  $motionRows=Get-MotionRows
  $lastMotion=if($motionRows.Count -gt 0){[int]$motionRows[-1].n}else{[int]$MotionBefore}
  $script:lastBoundKeyReleaseMotionNumber=[Math]::Max([int]$MotionBefore,$lastMotion)
  return $group
}
function Type-Text([string]$Text) {
  foreach ($c in $Text.ToCharArray()) {
    $n=[int]$c
    if ($n -ge 97 -and $n -le 122) { Tap-Key ($n-32) $false $false $n }
    elseif ($n -ge 65 -and $n -le 90) { Tap-Key $n $true $false $n }
    elseif ($n -ge 48 -and $n -le 57) { Tap-Key $n $false $false $n }
    else {
      switch ($c) {
        ' ' { Tap-Key 32 $false $false 32 }
        '/' { Tap-Key 191 $false $false 47 }
        '"' { Tap-Key 222 $true $false 34 }
        '.' { Tap-Key 190 $false $false 46 }
        '-' { Tap-Key 189 $false $false 45 }
        '_' { Tap-Key 189 $true $false 95 }
        default { throw "Unsupported console-command character U+$('{0:X4}' -f [int]$c)" }
      }
    }
  }
}
function Run-ConsoleScript([string]$Name) {
  Assert-OwnedProcess $restoreMode
  $cursor=(Get-LogLines).Count
  $openAck=Toggle-ConsoleOpen
  Wait-OwnedMilliseconds 400 $restoreMode
  Type-Text ('exec "../slot/{0}.txt"' -f $Name)
  Tap-Key 13 $false $false 10
  Wait-OwnedMilliseconds 700 $restoreMode
  $closeCursor=[int]$script:logTailLine
  Tap-Key 192
  Wait-OwnedMilliseconds 400 $restoreMode
  $closeRows=Read-NewCompleteLogLines $restoreMode
  $hiddenRows=@($closeRows|Where-Object {$_.line -match '^\[debug-ui\] event=0 visible=0 .* key=0$'})
  $closeAck=if($hiddenRows.Count -gt 0){$hiddenRows[-1]}else{$null}
  $closedPhase='console_closed_after_'+$Name
  $closedFrame=Capture-Frame $closedPhase 'console_absence_after_toggle'
  $inputReceipts.Add([pscustomobject]@{kind='debug_console_exec';script=$Name;input='DebugKey_192 open with event9/visible1/key0 ACK; typed exec ../slot file; DebugKey_13 submit ACK; DebugKey_192 close toggle; owner-bound frame proves console absence';open_ack_line=$openAck.line;open_ack_line_index=$openAck.line_index;close_requested=$true;close_cursor_line=$closeCursor;close_ack=$(if($closeAck){[ordered]@{line=$closeAck.line;line_index=$closeAck.line_index;meaning='optional event0 visible0 only'}}else{$null});close_frame_phase=$closedFrame.phase;close_frame_name=$closedFrame.name;close_frame_sha256=$closedFrame.sha256;utc=[DateTime]::UtcNow.ToString('o')})
  $null=Collect-ReadbackGroup $Name $cursor $restoreMode
}
function Collect-ReadbackGroup([string]$Name,[int]$Cursor,[bool]$ForCleanup=$false) {
  $scriptRec=@($scriptReceipts | Where-Object {$_.name -ceq ($Name+'.txt')} | Select-Object -Last 1)
  if($scriptRec.Count -ne 1){throw "Retained script receipt is missing for $Name."}
  $readTargets=@()
  for($i=0;$i -lt $scriptRec[0].lines.Count-3;$i++){
    $m=[regex]::Match([string]$scriptRec[0].lines[$i],'^ALIAS ([A-Za-z][A-Za-z0-9_]{0,8}) "([^"]+)"$')
    if($m.Success -and $scriptRec[0].lines[$i+1] -ceq ('ALIAS '+$m.Groups[1].Value) -and $scriptRec[0].lines[$i+2] -ceq $m.Groups[1].Value -and $scriptRec[0].lines[$i+3] -ceq ('ALIAS '+$m.Groups[1].Value)){
      $readTargets+=@([pscustomobject]@{alias=$m.Groups[1].Value;path=$m.Groups[2].Value})
    }
  }
  if($readTargets.Count -eq 0){return $null}
  $deadline=[DateTime]::UtcNow.AddSeconds(12);$lineSet=$null;$found=@()
  while([DateTime]::UtcNow -lt $deadline){
    Assert-OwnedProcess $ForCleanup
    $lineSet=Get-LogLines;$found=@();$searchFrom=$Cursor
    foreach($target in $readTargets){
      $expected=('{0}: /{1}' -f $target.alias,$target.path);$hit=-1
      for($j=$searchFrom;$j+2 -lt $lineSet.Count;$j++){if($lineSet[$j] -ceq $expected -and $lineSet[$j+2] -ceq $expected){$hit=$j;break}}
      if($hit -lt 0){$found=@();break}
      $found+=@([ordered]@{alias=$target.alias;path=$target.path;expected_line=$expected;open_line_index=$hit;value_line_index=($hit+1);close_line_index=($hit+2);value=([string]$lineSet[$hit+1])})
      $searchFrom=$hit+3
    }
    if($found.Count -eq $readTargets.Count){break}
    Wait-OwnedMilliseconds 150 $ForCleanup
  }
  if($found.Count -ne $readTargets.Count){throw "Raw indexed alias readback triples were incomplete for script $Name after cursor $Cursor."}
  $groupEnd=[int]$found[-1].close_line_index;$rawGroupLines=@()
  if($groupEnd -ge $Cursor){$rawGroupLines=@($lineSet[$Cursor..$groupEnd])}
  $group=[ordered]@{script=$Name+'.txt';script_path=$scriptRec[0].path;script_sha256=$scriptRec[0].sha256;script_bytes=$scriptRec[0].bytes;commands=@($scriptRec[0].lines);cursor=[int]$Cursor;index_base=0;log_lines_start_index=[int]$Cursor;final_line_index=$groupEnd;receipts=@($found|ForEach-Object{[ordered]@{alias=$_.alias;path=$_.path;expected_line=$_.expected_line;open_line_index=$_.open_line_index;close_line_index=$_.close_line_index}});value_receipts=@($found|ForEach-Object{[ordered]@{alias=$_.alias;kind='native_typed_raw_line';value=$_.value;line_index=$_.value_line_index;open_line_index=$_.open_line_index;close_line_index=$_.close_line_index}});snapshot=[ordered]@{values=@{};aliases=@{};components=@();readback_method='zero_parameter_alias_bracketed_by_repeated_path_ack'};log_lines=$rawGroupLines}
  foreach($rec in $found){$group.snapshot.values[$rec.path]=$rec.value;$group.snapshot.aliases[$rec.alias]=$rec.path}
  $readbackGroups.Add($group);$scriptRec[0] | Add-Member -NotePropertyName readback_group_index -NotePropertyValue ($readbackGroups.Count-1) -Force
  if($Name -ceq 'resourcebaseline' -or $Name -ceq 'resourceearlypartialbaseline'){
    foreach($rec in $found){if(!$baselineValues.ContainsKey($rec.path)){$baselineValues[$rec.path]=$rec.value}}
  }
  foreach($rec in $found){$expectedCurrentValues[$rec.path]=$rec.value}
  return $group
}
function Read-OwnerGameLog {
  Assert-OwnedProcess $restoreMode
  return Get-SharedText $GameLog
}
function Wait-Text([string]$Pattern,[int]$Seconds,[string]$What) {
  $deadline=[DateTime]::UtcNow.AddSeconds($Seconds)
  while ([DateTime]::UtcNow -lt $deadline) {
    $text=Read-OwnerGameLog
    if ($text -match $Pattern) { return @{text=$text;match=$Matches[0]} }
    Start-Sleep -Milliseconds 750
  }
  throw "Timed out waiting for $What. Pattern: $Pattern"
}
function Wait-StableFile([string]$Path,[int]$Seconds,[string]$What) {
  $deadline=[DateTime]::UtcNow.AddSeconds($Seconds); $last=-1L; $same=0
  while ([DateTime]::UtcNow -lt $deadline) {
    Assert-OwnedProcess $restoreMode
    if (Test-Path -LiteralPath $Path -PathType Leaf) {
      $len=(Get-Item -LiteralPath $Path).Length
      if ($len -gt 0 -and $len -eq $last) { $same++ } else { $same=0; $last=$len }
      if ($same -ge 3) { return Get-Item -LiteralPath $Path }
    }
    Wait-OwnedMilliseconds 400 $restoreMode
  }
  throw "Timed out waiting for stable $What at $Path"
}
function Capture-Frame([string]$Phase,[string]$Kind) {
  if ($null -eq $frameEvent) { throw 'Frame request event not initialized.' }
  Assert-OwnedProcess $restoreMode
  $before=Get-SharedText $GameLog
  $beforeAcks=[regex]::Matches($before,'(?m)^\[frame-request\] pid=\d+ slot=\d+ seq=\d+ present=\d+ file=bb_\d{6}\.bmp\r?$').Count
  $frameEvent.Set() | Out-Null
  $deadline=[DateTime]::UtcNow.AddSeconds(12); $ack=$null; $all=''
  while ([DateTime]::UtcNow -lt $deadline) {
    $all=Read-OwnerGameLog
    $acks=[regex]::Matches($all,'(?m)^\[frame-request\] pid=\d+ slot=\d+ seq=\d+ present=\d+ file=bb_\d{6}\.bmp\r?$')
    if ($acks.Count -gt $beforeAcks) { $ack=$acks[$acks.Count-1].Value.Trim(); break }
    Wait-OwnedMilliseconds 100 $restoreMode
  }
  if (!$ack) { throw "No owner-bound frame acknowledgement for $Phase/$Kind." }
  $m=[regex]::Match($ack,'^\[frame-request\] pid=(\d+) slot=(\d+) seq=(\d+) present=(\d+) file=(bb_\d{6}\.bmp)$')
  if (!$m.Success -or [int]$m.Groups[1].Value -ne [int]$processIdentity.pid -or [int]$m.Groups[2].Value -ne $Slot) {
    throw "Frame acknowledgement PID/slot does not match this run: $ack"
  }
  $expectedSeq=$frameReceipts.Count+1
  if ([int]$m.Groups[3].Value -ne $expectedSeq) { throw "Frame sequence expected $expectedSeq, received $($m.Groups[3].Value)." }
  $bmp=Join-Path $frameDir $m.Groups[5].Value
  $item=Wait-StableFile $bmp 8 "requested BMP $($m.Groups[5].Value)"
  $bytes=[IO.File]::ReadAllBytes($bmp)
  if([long]$bytes.Length -ne [long]$item.Length){throw 'Requested BMP changed length while the driver read its bytes.'}
  $dimensions=Get-BmpDimensions -Bytes $bytes -Path $bmp
  $width=[int]$dimensions.width; $height=[int]$dimensions.height
  if($width -ne $script:expectedCaptureWidth -or $height -ne $script:expectedCaptureHeight){throw "Requested BMP dimensions $width x $height differ from the private Display config $($script:expectedCaptureWidth) x $($script:expectedCaptureHeight)."}
  if([long]$item.Length -ne $script:expectedFrameFileBytes -or [long]$item.Length -gt $script:frameReserveBytes){throw "Requested BMP byte count $($item.Length) does not match the bound private frame extent/reserve."}
  $rec=[pscustomobject]@{phase=$Phase;kind=$Kind;sequence=[int]$m.Groups[3].Value;present=[int]$m.Groups[4].Value;name=$m.Groups[5].Value;ack_line=$ack;path=$bmp;sha256=(Get-FileHash -LiteralPath $bmp -Algorithm SHA256).Hash.ToLowerInvariant();bytes=[long]$bytes.Length;width=$width;height=$height;signed_height=$dimensions.signed_height;top_down=$dimensions.top_down}
  $frameReceipts.Add($rec)
  Write-Log ("FRAME {0}/{1} pid={2} slot={3} seq={4} present={5} file={6} sha256={7}" -f $Phase,$Kind,$processIdentity.pid,$Slot,$rec.sequence,$rec.present,$rec.name,$rec.sha256)
  return $rec
}
function Get-BmpDimensions([byte[]]$Bytes,[string]$Path){
  if($Bytes.Length -lt 54 -or [Text.Encoding]::ASCII.GetString($Bytes,0,2) -cne 'BM'){throw "Invalid BMP header: $Path"}
  $width=[BitConverter]::ToInt32($Bytes,18)
  $signedHeight=[BitConverter]::ToInt32($Bytes,22)
  if($width -le 0 -or $signedHeight -eq 0 -or $signedHeight -eq [int]::MinValue){throw "Invalid BMP dimensions: $width x $signedHeight"}
  $absoluteHeight=[Math]::Abs([long]$signedHeight)
  if($absoluteHeight -le 0 -or $absoluteHeight -gt [int]::MaxValue){throw "Unrepresentable BMP height: $signedHeight"}
  return [pscustomobject]@{width=$width;height=[int]$absoluteHeight;signed_height=$signedHeight;top_down=($signedHeight -lt 0)}
}
function Capture-Phase([object]$Phase) {
  Assert-OwnedProcess
  $cursor=(Get-LogLines).Count
  $VirtualKey=112;$n=1
  $motionBefore=[int]$script:latestMotionNumber
  $group=Trigger-BoundScript $VirtualKey ([string]$Phase.script_name) $cursor $motionBefore
  $motionReleaseBase=[int]$script:lastBoundKeyReleaseMotionNumber
  $boundReceipt=[pscustomobject]@{kind='bound_phase';phase=$Phase.name;script=$Phase.script_name;virtual_key=$VirtualKey;binding=('F'+$n);phase_sequence=[int]$Phase.phase_sequence;next_script=$Phase.next_script;slot=$Slot;log_cursor=$cursor;readback_final_line_index=$group.final_line_index;key_release_motion_number=$motionReleaseBase;console_state='closed_by_prior_owner_bound_toggle_frame';key_held_until='exact indexed raw path/value/path group';utc=[DateTime]::UtcNow.ToString('o')}
  $inputReceipts.Add($boundReceipt)
  Assert-PhaseReadbacks $Phase
  Wait-OwnedMilliseconds 250
  $motion=Wait-NewPlayerMotion $motionReleaseBase 12
  $motionWitness=[ordered]@{n=$motion.n;line=$motion.line;line_index=$motion.line_index;engine=$motion.engine;speed_mps=$motion.speed}
  $Phase | Add-Member -NotePropertyName fresh_motion -NotePropertyValue $motionWitness -Force
  $boundReceipt | Add-Member -NotePropertyName fresh_motion -NotePropertyValue $motionWitness -Force
  # A fresh selected-player motion row must follow each action before the consumer frame.
  Wait-OwnedMilliseconds 800
  $null=Capture-Frame $Phase.name 'raw_alias_readback_console_closed'
  Wait-OwnedMilliseconds 800
  $null=Capture-Frame $Phase.name 'resource_effect_or_restore_console_closed'
}
function Parse-PoolDump([string]$Path) {
  $lines=[IO.File]::ReadAllLines($Path)
  $rows=[System.Collections.Generic.List[object]]::new()
  for ($i=2;$i -lt $lines.Length;++$i) {
    if ([string]::IsNullOrWhiteSpace($lines[$i])) { continue }
    $parts=$lines[$i].Split("`t")
    if ($parts.Length -lt 7) { continue }
    $name=$parts[0].Trim(); $nums=@()
    $ok=$true
    for ($j=1;$j -le 6;++$j) { $v=0L; if (![long]::TryParse($parts[$j].Trim(),[Globalization.NumberStyles]::Integer,[Globalization.CultureInfo]::InvariantCulture,[ref]$v)) { $ok=$false; break }; $nums+=$v }
    if (!$ok -or !$name) { continue }
    $rows.Add([pscustomobject]@{name=$name;main_size=$nums[0];video_size=$nums[1];main_used=$nums[2];video_used=$nums[3];main_free=$nums[4];video_free=$nums[5]})
  }
  if ($rows.Count -eq 0) { throw 'The actual Dump Stats file has no parseable active pool rows.' }
  $safe=@($rows | Where-Object {$_.name -match '^[A-Za-z0-9 _.-]+$'})
  if ($safe.Count -eq 0) { throw 'No live pool name is safe for the original quoted StringList console command.' }
  $chosen=$safe | Sort-Object @{Expression={ [long]$_.video_used };Descending=$true},@{Expression={ [long]$_.main_used };Descending=$true} | Select-Object -First 1
  return @{rows=@($rows);chosen=$chosen}
}

try {
  $stimulusProcess=Get-Process -Id $PID -ErrorAction Stop
  $script:stimulusProcessHandle=[IntPtr]$stimulusProcess.Handle
  if($script:stimulusProcessHandle -eq [IntPtr]::Zero){throw 'Could not force a handle for the Resource Setup stimulus process.'}
  $stimulusCim=Get-CimInstance Win32_Process -Filter "ProcessId=$PID" -ErrorAction Stop
  if($null -eq $stimulusCim -or [string]::IsNullOrWhiteSpace([string]$stimulusCim.ExecutablePath) -or [string]::IsNullOrWhiteSpace([string]$stimulusCim.CommandLine)){throw 'Could not retain exact Resource Setup stimulus process image/parent/command identity.'}
  $stimulusStart=$stimulusProcess.StartTime.ToUniversalTime()
  $stimulusProcessIdentity=[ordered]@{pid=[int]$PID;image_path=[IO.Path]::GetFullPath([string]$stimulusCim.ExecutablePath);start_time_utc=$stimulusStart.ToString('o');start_ticks=[long]$stimulusStart.Ticks;parent_pid=[int]$stimulusCim.ParentProcessId;command_path=[IO.Path]::GetFullPath($PSCommandPath)}
  if (!(Test-Path -LiteralPath $slotDir -PathType Container) -or !(Test-Path -LiteralPath $dataDir -PathType Container)) { throw 'Private staged sibling slot/data directories are missing.' }
  for ($key=0;$key -lt 256;++$key) {
    $keyEvents[$key]=[Threading.EventWaitHandle]::new($false,[Threading.EventResetMode]::ManualReset,('Local\BurnoutPC_DebugKey_{0:X2}_{1}' -f $key,$Slot))
    $keyEvents[$key].Reset() | Out-Null
  }
  $launchDeadline=[DateTime]::UtcNow.AddSeconds(45)
  while ([DateTime]::UtcNow -lt $launchDeadline) {
    $cims=@(Get-CimInstance Win32_Process -Filter "Name='Burnout_PC.exe'" -ErrorAction Stop | Where-Object {$_.ExecutablePath -and [IO.Path]::GetFullPath($_.ExecutablePath) -ieq (Join-Path $slotDir 'Burnout_PC.exe')})
    if ($cims.Count -gt 1) { throw 'More than one process owns the private staged executable.' }
    if ($cims.Count -eq 1) {
      $gameProcess=Get-Process -Id ([int]$cims[0].ProcessId) -ErrorAction Stop
      $script:gameProcessHandle=[IntPtr]$gameProcess.Handle
      if($script:gameProcessHandle -eq [IntPtr]::Zero){throw 'Could not force and retain a nonzero handle for the exact staged game process.'}
      $processIdentity=[ordered]@{pid=[int]$cims[0].ProcessId;image_path=[IO.Path]::GetFullPath($cims[0].ExecutablePath);start_time_utc=$gameProcess.StartTime.ToUniversalTime().ToString('o');start_ticks=$gameProcess.StartTime.ToUniversalTime().Ticks;slot=$Slot;slot_tag=('_'+$Slot);stage_root=[IO.Path]::GetFullPath((Join-Path $slotDir '..'));runtime_workflow_commit=$driverPlan.runtime_harness.upstream_commit;runtime_workflow_tree=$driverPlan.runtime_harness.upstream_tree;runtime_root_path=$driverPlan.runtime_harness.runtime_root_path;runtime_overlay_manifest_sha256=$driverPlan.runtime_harness.overlay_manifest_sha256;runtime_overlay_seal_sha256=$driverPlan.runtime_harness.overlay_seal_sha256;phase_done_requester_sha256=$driverPlan.runtime_harness.requester_sha256}
      break
    }
    Start-Sleep -Milliseconds 250
  }
  if ($null -eq $gameProcess) { throw 'The exact private staged Burnout_PC.exe did not start within 45 seconds.' }
  $script:processIdentity=$processIdentity
  $script:overallDeadline=[DateTime]::UtcNow.AddSeconds($TimeoutSec)
  $script:nextCimCheck=[DateTime]::UtcNow.AddSeconds(8)
  $ownerFile=Join-Path $runDir 'RESOURCE_GAME_OWNER.json'
  $ownerRecord=[ordered]@{schema=2;suite=$Suite;slot=$Slot;run_name=[IO.Path]::GetFileName($runDir);pid=$processIdentity.pid;image_path=$processIdentity.image_path;start_time_utc=$processIdentity.start_time_utc;start_ticks=$processIdentity.start_ticks;stage_root=$processIdentity.stage_root;runtime_workflow_commit=$processIdentity.runtime_workflow_commit;runtime_workflow_tree=$processIdentity.runtime_workflow_tree;runtime_root_path=$processIdentity.runtime_root_path;runtime_overlay_manifest_sha256=$processIdentity.runtime_overlay_manifest_sha256;runtime_overlay_seal_sha256=$processIdentity.runtime_overlay_seal_sha256;phase_done_requester_sha256=$processIdentity.phase_done_requester_sha256;candidate_exe_sha256=(Get-FileHash -LiteralPath (Join-Path $slotDir 'Burnout_PC.exe') -Algorithm SHA256).Hash.ToLowerInvariant();owner_sidecar_sha256=(Get-FileHash -LiteralPath (Join-Path $processIdentity.stage_root 'RESOURCE_STAGE_OWNER.json') -Algorithm SHA256).Hash.ToLowerInvariant();created_utc=[DateTime]::UtcNow.ToString('o')}
  Write-Json $ownerFile $ownerRecord
  $gameLogReady=Wait-Text '(?m)^\[BootLegal\] stage ' 120 'the BootLegal stage machine before TitleStart'
  $startupLogSnapshot=Get-CompleteLogSnapshot
  $script:logTailLine=[int]$startupLogSnapshot.complete_line_count
  $script:logTailByte=[long]$startupLogSnapshot.byte_count
  $script:logTailCarry=[string]$startupLogSnapshot.trailing_partial
  $stageMatch=[regex]::Match([string]$gameLogReady.text,'(?m)^\[BootLegal\] stage (-?\d+) ->[^\r\n]*')
  $firstBootStage=if($stageMatch.Success){[int]$stageMatch.Groups[1].Value}else{-1}
  $maxPartialSetBeforeTitleStart=$false
  $partialFixupProof=$null
  $suffix='_'+$Slot
  $frameName=('Local\BurnoutPC_FrameRequest_{0}_{1}' -f $processIdentity.pid,$Slot)
  $frameEvent=[Threading.EventWaitHandle]::new($false,[Threading.EventResetMode]::AutoReset,$frameName)

  # EARLY_MAX_PARTIAL_FAILURE_SAFE_BEGIN
  if($Suite -eq 'resource_windows' -and $driverPlan.candidate_execution_scope.suites.resource_windows.enable_max_partial_fixups -eq $true){
    $mpPath='Core/Resource/Max Partial Fixups'
    $earlyBaselineName='resourceearlypartialbaseline'
    $earlyBaselineLines=[System.Collections.Generic.List[string]]::new()
    $earlyBaselineLines.Add('COMPONENT "Resource"')
    Add-VariableRead $earlyBaselineLines 'MP' $mpPath
    $null=Write-StageScript $earlyBaselineName $earlyBaselineLines.ToArray()
    Run-ConsoleScript $earlyBaselineName
    $earlyBaselineGroup=@(Find-ReadbackGroup $earlyBaselineName)
    if($earlyBaselineGroup.Count -ne 1 -or $earlyBaselineGroup[0].value_receipts.Count -ne 1 -or
       !(Compare-NativeValue $mpPath ([string]$earlyBaselineGroup[0].value_receipts[0].value) ([string]$earlyBaselineGroup[0].value_receipts[0].value)) -or
       !$baselineValues.ContainsKey($mpPath)){
      throw 'The read-only same-run Max Partial Fixups baseline probe did not complete before any SET.'
    }
    $mpBaseline=[string]$baselineValues[$mpPath]
    $earlyBaselineReceipt=[ordered]@{
      schema=1;status='captured_before_set';suite=$Suite;slot=$Slot;process=$processIdentity
      script=$earlyBaselineGroup[0].script;script_sha256=$earlyBaselineGroup[0].script_sha256
      path=$mpPath;value=$mpBaseline
      line_index=$earlyBaselineGroup[0].value_receipts[0].line_index
      open_line_index=$earlyBaselineGroup[0].value_receipts[0].open_line_index
      close_line_index=$earlyBaselineGroup[0].value_receipts[0].close_line_index
      baseline_group_sha256=(Get-FileHash -LiteralPath $earlyBaselineGroup[0].script_path -Algorithm SHA256).Hash.ToLowerInvariant()
      created_utc=[DateTime]::UtcNow.ToString('o')
    }
    Write-Json (Join-Path $runDir 'RESOURCE_EARLY_PARTIAL_BASELINE.json') $earlyBaselineReceipt

    # Prebuild and bind the one-control emergency restore before attempting the setter.
    $earlyRestoreName='resourceearlypartialrestore'
    $null=New-RestoreScript $earlyRestoreName @($mpPath)
    $earlyBindLines=[System.Collections.Generic.List[string]]::new()
    $earlyBindLines.Add(('BIND F2 exec "../slot/{0}.txt"' -f $earlyRestoreName))
    $null=Write-StageScript 'resourcebindearlyrestore' $earlyBindLines.ToArray()
    Run-ConsoleScript 'resourcebindearlyrestore'

    $earlySetName='resourceearlypartialset'
    $earlySetLines=[System.Collections.Generic.List[string]]::new()
    $earlySetLines.Add(('SET "{0}" 10' -f $mpPath))
    Add-VariableRead $earlySetLines 'MP' $mpPath
    $null=Write-StageScript $earlySetName $earlySetLines.ToArray()
    Run-ConsoleScript $earlySetName
    $earlySetGroup=@(Find-ReadbackGroup $earlySetName)
    if($earlySetGroup.Count -ne 1 -or $earlySetGroup[0].value_receipts.Count -ne 1 -or
       !(Compare-NativeValue $mpPath ([string]$earlySetGroup[0].value_receipts[0].value) '10')){
      throw 'The Max Partial Fixups=10 setter lacks one exact typed readback; early restore remains armed.'
    }
    $partialSetCloseIndex=[int]$earlySetGroup[0].value_receipts[0].close_line_index
    $freshLogLines=Get-LogLines
    $titleCueIndex=-1
    for($li=0;$li -lt $freshLogLines.Count;$li++){if($freshLogLines[$li] -match '^\[BootLegal\] stage -?\d+ -> 7(?:\D|$)'){$titleCueIndex=$li;break}}
    $maxPartialSetBeforeTitleStart=($titleCueIndex -ge 0 -and $partialSetCloseIndex -lt $titleCueIndex)
    $partialLine=$null
    for($li=$partialSetCloseIndex+1;$li -lt $freshLogLines.Count;$li++){
      if($freshLogLines[$li] -match 'SendPartialFixupRequest.*(?:requested|liAvailable|liCount).*(?:capped|liCount)'){$partialLine=$freshLogLines[$li];break}
    }
    if($partialLine){
      $pm=[regex]::Match($partialLine,'SendPartialFixupRequest.*requested(?:_count)?[=: ]+(?<requested>\d+).*capped(?:_count)?[=: ]+(?<capped>\d+)')
      if($pm.Success){$partialFixupProof=[ordered]@{call_line=$partialLine;requested_count=[int]$pm.Groups['requested'].Value;capped_count=[int]$pm.Groups['capped'].Value;log_line_index=$li;max_partial_close_line_index=$partialSetCloseIndex;title_start_cue_line_index=$titleCueIndex}}
    }
  }
  # EARLY_MAX_PARTIAL_FAILURE_SAFE_END
  $baselineLines=[System.Collections.Generic.List[string]]::new()
  $baselineLines.Add('COMPONENT "Resource"')
  if ($Suite -eq 'resource_stats_allocator') { $baselineLines.Add('COMPONENT "GameDataModule"') }
  foreach ($pair in @(@('X','Core/Resource/Texture Window'),@('S','Core/Resource/Sort By'),@('D','Core/Resource/Draw'))) { Add-VariableRead $baselineLines $pair[0] $pair[1] }
  if ($Suite -eq 'resource_stats_allocator') {
    foreach ($pair in @(@('S0','Core/Resource/ShareTest0'),@('S1','Core/Resource/ShareTest1'),@('SV','Core/Resource/Show Share Test'),@('HUD','GameDataModule/Show HUD'),@('USED','GameDataModule/Slots Used'),@('FREE','GameDataModule/Slots Free'))) { Add-VariableRead $baselineLines $pair[0] $pair[1] }
  }
  $null=Write-StageScript 'resourcebaseline' $baselineLines.ToArray()
  Run-ConsoleScript 'resourcebaseline'
  foreach($path in $baselineValues.Keys){$expectedCurrentValues[$path]=$baselineValues[$path]}
  $restorePaths=if($Suite -eq 'resource_windows'){@('Core/Resource/Texture Window','Core/Resource/Sort By','Core/Resource/Draw')}else{@('Core/Resource/ShareTest0','Core/Resource/ShareTest1','Core/Resource/Show Share Test','GameDataModule/Show HUD')}
  $restoreName=if($Suite -eq 'resource_windows'){'resourcewindowsrestore'}else{'resourcestatsrestore'}
  $null=New-RestoreScript $restoreName $restorePaths
  $dumpLines=[System.Collections.Generic.List[string]]::new();Add-FunctionAlias $dumpLines 'DS' 'Core/Resource/Dump Stats';$dumpLines.Add('CALL DS')
  $null=Write-StageScript 'resourcedumpstats' $dumpLines.ToArray()
  $phases=@()
  if ($Suite -eq 'resource_windows') {
    $phases=@(
      @{key=112;name='texture_bank_open';commands=@('SET "Core/Resource/Sort By" "Nothing"','SET "Core/Resource/Draw" "Stretched"','SET "Core/Resource/Texture Window" __POOL__');aliases=@([pscustomobject]@{alias='X';path='Core/Resource/Texture Window'},[pscustomobject]@{alias='S';path='Core/Resource/Sort By'},[pscustomobject]@{alias='D';path='Core/Resource/Draw'})},
      @{key=113;name='texture_next_callback';commands=@('CALL N');aliases=@([pscustomobject]@{alias='X';path='Core/Resource/Texture Window'});function_aliases=@([pscustomobject]@{alias='N';path='Core/Resource/Next Texture'})},
      @{key=114;name='texture_previous_callback';commands=@('CALL P');aliases=@([pscustomobject]@{alias='X';path='Core/Resource/Texture Window'});function_aliases=@([pscustomobject]@{alias='P';path='Core/Resource/Prev Texture'})},
      @{key=115;name='texture_sort_area';commands=@('SET "Core/Resource/Sort By" "Area"');aliases=@([pscustomobject]@{alias='S';path='Core/Resource/Sort By'})},
      @{key=116;name='texture_sort_width';commands=@('SET "Core/Resource/Sort By" "Width"');aliases=@([pscustomobject]@{alias='S';path='Core/Resource/Sort By'})},
      @{key=117;name='texture_draw_actual';commands=@('SET "Core/Resource/Draw" "Actual Size"');aliases=@([pscustomobject]@{alias='D';path='Core/Resource/Draw'})},
      @{key=118;name='texture_draw_stretched';commands=@('SET "Core/Resource/Draw" "Stretched"');aliases=@([pscustomobject]@{alias='D';path='Core/Resource/Draw'})},
      @{key=119;name='texture_page_mode_8x8';commands=@('SET "Core/Resource/Draw" "Thumbnails 8x8"');aliases=@([pscustomobject]@{alias='D';path='Core/Resource/Draw'},[pscustomobject]@{alias='X';path='Core/Resource/Texture Window'})},
      @{key=120;name='texture_next_page_callback';commands=@('CALL G');aliases=@([pscustomobject]@{alias='D';path='Core/Resource/Draw'},[pscustomobject]@{alias='X';path='Core/Resource/Texture Window'});function_aliases=@([pscustomobject]@{alias='G';path='Core/Resource/Next Texture Page'})},
      @{key=121;name='texture_previous_page_callback';commands=@('CALL R');aliases=@([pscustomobject]@{alias='D';path='Core/Resource/Draw'},[pscustomobject]@{alias='X';path='Core/Resource/Texture Window'});function_aliases=@([pscustomobject]@{alias='R';path='Core/Resource/Prev Texture Page'})},
      @{key=122;name='texture_window_off';commands=@('SET "Core/Resource/Texture Window" "<none>"');aliases=@([pscustomobject]@{alias='X';path='Core/Resource/Texture Window'})}
    )
  } else {
    $phases=@(
      @{key=112;name='share_self_match_on';commands=@('SET "Core/Resource/ShareTest0" __POOL__','SET "Core/Resource/ShareTest1" __POOL__','SET "Core/Resource/Show Share Test" TRUE');aliases=@([pscustomobject]@{alias='S0';path='Core/Resource/ShareTest0'},[pscustomobject]@{alias='S1';path='Core/Resource/ShareTest1'},[pscustomobject]@{alias='SV';path='Core/Resource/Show Share Test'})},
      @{key=113;name='share_test0_other_pool_counterfactual';commands=@('SET "Core/Resource/ShareTest0" __COUNTERPOOL__','SET "Core/Resource/Show Share Test" TRUE');aliases=@([pscustomobject]@{alias='S0';path='Core/Resource/ShareTest0'},[pscustomobject]@{alias='S1';path='Core/Resource/ShareTest1'},[pscustomobject]@{alias='SV';path='Core/Resource/Show Share Test'})},
      @{key=114;name='share_test1_other_pool_counterfactual';commands=@('SET "Core/Resource/ShareTest0" __POOL__','SET "Core/Resource/ShareTest1" __COUNTERPOOL__','SET "Core/Resource/Show Share Test" TRUE');aliases=@([pscustomobject]@{alias='S0';path='Core/Resource/ShareTest0'},[pscustomobject]@{alias='S1';path='Core/Resource/ShareTest1'},[pscustomobject]@{alias='SV';path='Core/Resource/Show Share Test'})},
      @{key=115;name='share_restore_off';commands=@('SET "Core/Resource/Show Share Test" FALSE','SET "Core/Resource/ShareTest0" "<none>"','SET "Core/Resource/ShareTest1" "<none>"');aliases=@([pscustomobject]@{alias='S0';path='Core/Resource/ShareTest0'},[pscustomobject]@{alias='S1';path='Core/Resource/ShareTest1'},[pscustomobject]@{alias='SV';path='Core/Resource/Show Share Test'})},
      @{key=116;name='allocator_hud_on';commands=@('SET "GameDataModule/Show HUD" TRUE');aliases=@([pscustomobject]@{alias='HUD';path='GameDataModule/Show HUD'},[pscustomobject]@{alias='USED';path='GameDataModule/Slots Used'},[pscustomobject]@{alias='FREE';path='GameDataModule/Slots Free'})},
      @{key=117;name='allocator_hud_off_readonly_attempt';commands=@('SET "GameDataModule/Show HUD" FALSE','SET "GameDataModule/Slots Used" 0','SET "GameDataModule/Slots Free" 0');aliases=@([pscustomobject]@{alias='HUD';path='GameDataModule/Show HUD'},[pscustomobject]@{alias='USED';path='GameDataModule/Slots Used'},[pscustomobject]@{alias='FREE';path='GameDataModule/Slots Free'})}
    )
  }
  for($phaseIndex=0;$phaseIndex -lt $phases.Count;$phaseIndex++){
    $phase=$phases[$phaseIndex]
    $scriptName=($Suite -replace '_','')+($phase.name -replace '_','')
    $phase | Add-Member -NotePropertyName phase_sequence -NotePropertyValue ($phaseIndex+1) -Force
    $scriptLines=[System.Collections.Generic.List[string]]::new()
    foreach ($aliasPair in $phase.function_aliases) { Add-FunctionAlias $scriptLines $aliasPair.alias $aliasPair.path }
    foreach ($command in $phase.commands) {
      $line=$command.Replace('__POOL__','"__POOL__"').Replace('__COUNTERPOOL__','"__COUNTERPOOL__"')
      $scriptLines.Add($line)
    }
    if($phaseIndex+1 -lt $phases.Count){
      $phase | Add-Member -NotePropertyName next_script -NotePropertyValue (($Suite -replace '_','')+($phases[$phaseIndex+1].name -replace '_','')) -Force
      $scriptLines.Add(('BIND F1 exec "../slot/{0}.txt"' -f $phase.next_script))
    }else{$phase | Add-Member -NotePropertyName next_script -NotePropertyValue $null -Force}
    foreach ($aliasPair in $phase.aliases) { Add-VariableRead $scriptLines $aliasPair.alias $aliasPair.path }

    $null=Write-StageScript $scriptName $scriptLines.ToArray()
    $phase | Add-Member -NotePropertyName script_name -NotePropertyValue $scriptName -Force
  }
  $bindLines=[System.Collections.Generic.List[string]]::new()
  $phaseTriggerKey=112;$restoreTriggerKey=113
  if($phases.Count -eq 0){throw 'Resource suite has no action scripts to bind.'}
  $bindLines.Add(('BIND F1 exec "../slot/{0}.txt"' -f $phases[0].script_name))
  $bindLines.Add(('BIND F2 exec "../slot/{0}.txt"' -f $restoreName))
  $null=Write-StageScript 'resourcebindphases' $bindLines.ToArray()
  Run-ConsoleScript 'resourcebindphases'

  $dump=Invoke-DumpStats 'resourcedumpstats'
  $dumpPath=$dump.path;$dumpCopy=Join-Path $runDir $dump.copy;$dumpHash=$dump.sha256;$poolName=[string]$dump.selected_pool
  $parsed=@{rows=$dump.rows;chosen=[pscustomobject]@{name=$poolName}}
  $counterPoolName=$null
  if($Suite -eq 'resource_stats_allocator'){
    $different=@($dump.rows|Where-Object {$_.name -cne $poolName -and $_.name -match '^[A-Za-z0-9 _.-]+$' -and ([long]$_.main_used -gt 0 -or [long]$_.video_used -gt 0)})
    $chosenCounter=$different|Sort-Object @{Expression={if($_.name -ceq 'Sound'){0}else{1}}},@{Expression={[long]$_.video_used}},@{Expression={[long]$_.main_used};Descending=$true}|Select-Object -First 1
    if(!$chosenCounter){throw 'No actual valid different live pool exists for an independent share counterfactual.'}
    $counterPoolName=[string]$chosenCounter.name
  }
  $poolJson=[ordered]@{schema=1;source='native CgsResource::DebugComponent::DumpStats';source_path=$dumpPath;copy_path=$dump.copy;sha256=$dumpHash;bytes=$dump.bytes;pool_count=$dump.pool_count;selected_pool=$poolName;selected_reason='highest VideoMemUsed then MainMemUsed among actual live active pool rows; no pool id/name was guessed';cleanup=$dump.cleanup;mutex=$dump.mutex;rows=$dump.rows}
  $poolJson.counterfactual_pool=$counterPoolName;$poolJson.counterfactual_selection_reason='different actual live pool, prefer Sound; zero totals remain an actual pixel requirement'
  Write-Json (Join-Path $evidenceDir 'POOL_CATALOG.json') $poolJson
  if ($Suite -eq 'resource_windows') {
    foreach ($rec in $scriptReceipts) {
      $scriptText=[IO.File]::ReadAllText($rec.path)
      $scriptText=$scriptText.Replace('"__POOL__"',('"'+$poolName+'"')).Replace('"__COUNTERPOOL__"',('"'+$counterPoolName+'"'))
      [IO.File]::WriteAllText($rec.path,$scriptText,[Text.Encoding]::ASCII)
      Copy-Item -LiteralPath $rec.path -Destination $rec.evidence_path -Force
      $rec.sha256=(Get-FileHash -LiteralPath $rec.path -Algorithm SHA256).Hash.ToLowerInvariant()
      $rec.bytes=(Get-Item -LiteralPath $rec.path).Length
      $rec.lines=[IO.File]::ReadAllLines($rec.path)
    }
  } else {
    foreach ($rec in $scriptReceipts) {
      $scriptText=[IO.File]::ReadAllText($rec.path)
      $scriptText=$scriptText.Replace('"__POOL__"',('"'+$poolName+'"')).Replace('"__COUNTERPOOL__"',('"'+$counterPoolName+'"'))
      [IO.File]::WriteAllText($rec.path,$scriptText,[Text.Encoding]::ASCII)
      Copy-Item -LiteralPath $rec.path -Destination $rec.evidence_path -Force
      $rec.sha256=(Get-FileHash -LiteralPath $rec.path -Algorithm SHA256).Hash.ToLowerInvariant()
      $rec.bytes=(Get-Item -LiteralPath $rec.path).Length
      $rec.lines=[IO.File]::ReadAllLines($rec.path)
    }
  }
  foreach($phase in $phases){
    for($ci=0;$ci -lt $phase.commands.Count;$ci++){$phase.commands[$ci]=([string]$phase.commands[$ci]).Replace('__POOL__','"'+$poolName+'"').Replace('__COUNTERPOOL__','"'+$counterPoolName+'"')}
  }
  $poolJson.selected_pool=$poolName
  Write-Json (Join-Path $evidenceDir 'POOL_CATALOG.json') $poolJson

  $flowDriving=Wait-FlowDriving 120
  $latest=Wait-NewPlayerMotion -1 20
  $stable=$false; $stationaryLines=@(); $stationaryDeadline=[DateTime]::UtcNow.AddSeconds(45)
  while(!$stable -and [DateTime]::UtcNow -lt $stationaryDeadline){
    $rows=Get-MotionRows
    $recent=@($rows|Where-Object {$_.n -gt ($latest.n-3)}|Sort-Object n|Select-Object -Last 3)
    if($recent.Count -eq 3){
      $ordered=$true
      for($ri=1;$ri -lt 3;$ri++){if($recent[$ri].n -le $recent[$ri-1].n -or $recent[$ri].line_index -le $recent[$ri-1].line_index){$ordered=$false}}
      $allGood=($ordered -and @($recent|Where-Object {$_.engine -eq 2 -and $_.speed -lt 0.25}).Count -eq 3)
      if($allGood){
        $xs=@($recent|ForEach-Object {$_.x});$ys=@($recent|ForEach-Object {$_.y});$zs=@($recent|ForEach-Object {$_.z})
        if(($xs|Measure-Object -Maximum).Maximum-($xs|Measure-Object -Minimum).Minimum -lt 0.25 -and ($ys|Measure-Object -Maximum).Maximum-($ys|Measure-Object -Minimum).Minimum -lt 0.25 -and ($zs|Measure-Object -Maximum).Maximum-($zs|Measure-Object -Minimum).Minimum -lt 0.25){$stable=$true;$stationaryLines=@($recent|ForEach-Object {$_.line});$script:latestMotionNumber=$recent[-1].n}
      }
    }
    if(!$stable){Start-Sleep -Milliseconds 300}
  }
  if(!$stable){throw 'The last three selected-player motion rows were not consecutive, engine=2, near-zero samples.'}
  Write-Log ('STATIONARY consecutive selected-player engine2 samples=' + $stationaryLines.Count + ' speed_bound_mps=0.25')
  $null=Capture-Frame 'stationary_natural_scene' 'pre_control_baseline_console_closed'

  $textureProviderReadiness=$null
  foreach ($phase in $phases) {
    Capture-Phase $phase
    if($phase.name -ceq 'texture_bank_open'){
      $probe=[ordered]@{schema=1;status='awaiting_actual_native_caption_and_pixels';suite=$Suite;slot=$Slot;selected_pool=$poolName;process=$processIdentity;frames=@($frameReceipts|Where-Object {$_.phase -ceq 'texture_bank_open'});raw_aliases=@{texture_window=$expectedCurrentValues['Core/Resource/Texture Window'];sort_by=$expectedCurrentValues['Core/Resource/Sort By'];draw=$expectedCurrentValues['Core/Resource/Draw']};minimum_visible_total=65;initial_zero_based_index=0;page_size=64;no_more_selected_inputs_before_gate=$true;created_utc=[DateTime]::UtcNow.ToString('o')}
      Write-Json (Join-Path $runDir 'TEXTURE_PROVIDER_PROBE.json') $probe
      Write-Log 'PROVIDER_GATE awaiting actual caption Texture0ofN>=65 plus texture pixels; no callbacks/pages before gate'
      $gatePath=Join-Path $runDir 'TEXTURE_PROVIDER_GATE.json'
      $gateDeadline=[DateTime]::UtcNow.AddSeconds([int]$driverPlan.texture_provider_readiness.gate_timeout_seconds)
      while(!(Test-Path -LiteralPath $gatePath -PathType Leaf)){
        Assert-OwnedProcess
        if([DateTime]::UtcNow -ge $gateDeadline){throw 'Actual texture-provider readiness was not witnessed within the bounded gate; restore without page/callback claims.'}
        Wait-OwnedMilliseconds 200
      }
      $gateItem=Get-Item -LiteralPath $gatePath -Force
      if($gateItem.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Texture readiness gate is a reparse point.'}
      $gate=Get-Content -LiteralPath $gatePath -Raw|ConvertFrom-Json
      $textureProviderReadiness=Assert-TextureProviderGate -Gate $gate -Probe $probe -Identity $processIdentity
      Write-Json (Join-Path $runDir 'TEXTURE_PROVIDER_GATE_VALIDATED.json') $textureProviderReadiness
      Write-Log ('PROVIDER_GATE validated actual total='+$textureProviderReadiness.visible_texture_total+'; continue bounded callbacks/pages')
    }
  }
  $restoreMode=$true; $restoreDeadline=[DateTime]::UtcNow.AddSeconds(18)
  $restoreCursor=(Get-LogLines).Count
  $restoreGroup=Trigger-BoundScript $restoreTriggerKey $restoreName $restoreCursor ([int]$script:latestMotionNumber) $restoreMode
  $inputReceipts.Add([pscustomobject]@{kind='bound_restore';script=$restoreName;virtual_key=$restoreTriggerKey;binding='F2';slot=$Slot;log_cursor=$restoreCursor;readback_final_line_index=$restoreGroup.final_line_index;console_state='closed_by_prior_owner_bound_toggle_frame';key_held_until='exact indexed raw path/value/path group';utc=[DateTime]::UtcNow.ToString('o')})
  $restoreComparisons=@();$restoreOk=$true
  for($ri=0;$ri -lt $restoreGroup.receipts.Count;$ri++){
    $path=[string]$restoreGroup.receipts[$ri].path;$actual=[string]$restoreGroup.value_receipts[$ri].value;$before=[string]$baselineValues[$path]
    $same=Compare-NativeValue $path $actual $before
    $restoreComparisons+=@([ordered]@{path=$path;baseline=$before;restored=$actual;matches=$same;line_index=$restoreGroup.value_receipts[$ri].line_index;open_line_index=$restoreGroup.value_receipts[$ri].open_line_index;close_line_index=$restoreGroup.value_receipts[$ri].close_line_index})
    if(!$same){$restoreOk=$false}
  }
  if(!$restoreOk){throw 'One or more modified controls did not return to the same-run indexed baseline.'}
  $restoreReceipt=[ordered]@{schema=1;status='restored';suite=$Suite;slot=$Slot;process=$processIdentity;baseline_script='resourcebaseline.txt';restore_script=$restoreName+'.txt';baseline_values=$baselineValues;comparisons=$restoreComparisons;validated_utc=[DateTime]::UtcNow.ToString('o')}
  Write-Json (Join-Path $runDir 'RESOURCE_RESTORE_RECEIPT.json') $restoreReceipt
  $restoreMode=$false
  Wait-OwnedMilliseconds 800
  $null=Capture-Frame 'restore_resource_controls' 'alias_path_value_restore_ack_console_closed'
  Wait-OwnedMilliseconds 800
  $null=Capture-Frame 'restore_resource_controls' 'effect_or_restore_console_closed'

  # The helper records the original fixed-path file but leaves its removal to Run.ps1, which
  # compares this copy's hash after run_case has performed its PID/profile cleanup.
  $ownerProof=[ordered]@{pid=[int]$processIdentity.pid;image_path=$processIdentity.image_path;start_time_utc=$processIdentity.start_time_utc;start_ticks=$processIdentity.start_ticks;stage_root=$processIdentity.stage_root;slot=$Slot;slot_tag=$processIdentity.slot_tag;runtime_workflow_commit=$processIdentity.runtime_workflow_commit;runtime_workflow_tree=$processIdentity.runtime_workflow_tree;runtime_root_path=$processIdentity.runtime_root_path;runtime_overlay_manifest_sha256=$processIdentity.runtime_overlay_manifest_sha256;runtime_overlay_seal_sha256=$processIdentity.runtime_overlay_seal_sha256;phase_done_requester_sha256=$processIdentity.phase_done_requester_sha256;frame_event=$frameName}
  $receipt=[ordered]@{schema=2;status='complete';suite=$Suite;slot=$Slot;created_utc=$startedAt.ToString('o');completed_utc=[DateTime]::UtcNow.ToString('o');process=$ownerProof;private_display_config=[ordered]@{source_sha256=$privateDisplayPlan.source_sha256;private_sha256=$privateDisplayPlan.derived_sha256;width=$script:expectedCaptureWidth;height=$script:expectedCaptureHeight;fullscreen=[int]$privateDisplayPlan.private_values.Fullscreen;capture_frame_file_bytes=$script:expectedFrameFileBytes;frame_reserve_bytes=$script:frameReserveBytes};frame_output_dir=$frameDir;dump_path=$dumpPath;dump_copy='resource_evidence/cgsresourcedump_0.txt';dump_sha256=$dumpHash;dump_cleanup=$dump.cleanup;pool_catalog='resource_evidence/POOL_CATALOG.json';selected_pool=$poolName;flow_driving=$flowDriving;first_boot_stage=$firstBootStage;max_partial_set_before_title_start=$maxPartialSetBeforeTitleStart;partial_fixup_proof=$partialFixupProof;early_partial_baseline_receipt=$(if($Suite -eq 'resource_windows' -and $driverPlan.candidate_execution_scope.suites.resource_windows.enable_max_partial_fixups -eq $true){'RESOURCE_EARLY_PARTIAL_BASELINE.json'}else{$null});candidate_scope_id=[string]$candidateScope.scope_id;candidate_excluded_site_ids=@($candidateScope.excluded_site_ids);phase_count=$phases.Count;phase_names=@($phases|ForEach-Object {$_.name});baseline_values=$baselineValues;readback_groups=@($readbackGroups);restore_receipt='RESOURCE_RESTORE_RECEIPT.json';restore_complete=($null -ne $restoreReceipt -and $restoreReceipt.status -ceq 'restored');source_script_receipts=@($scriptReceipts);frame_receipts=@($frameReceipts);input_receipts=@($inputReceipts);stationary_motion_lines=$stationaryLines;source_behavior='Only indexed raw alias path/value/path triples establish typed values; whole-state SAVE is never invoked.'}
  $receipt.stimulus_process=$stimulusProcessIdentity
  $receipt|Add-Member -NotePropertyName texture_provider_readiness -NotePropertyValue $textureProviderReadiness -Force
  Write-Json $driverReceiptPath $receipt
  Write-Log 'RESULT complete'
  $driverSuccessful=$true
}
catch {
  $failure=$_.Exception.Message
  Write-Log ("RESULT fail: " + $failure)
  if($null -eq $restoreReceipt -or $restoreReceipt.status -cne 'restored'){
    try{
      $emergencyRestoreName=$null
      if($restoreName -and @($scriptReceipts|Where-Object {$_.name -ceq ($restoreName+'.txt')}).Count -eq 1){$emergencyRestoreName=$restoreName}
      elseif($earlyRestoreName -and @($scriptReceipts|Where-Object {$_.name -ceq ($earlyRestoreName+'.txt')}).Count -eq 1){$emergencyRestoreName=$earlyRestoreName}
      if($baselineValues.Count -gt 0 -and $emergencyRestoreName){
        $restoreMode=$true;$restoreDeadline=[DateTime]::UtcNow.AddSeconds(20)
        Run-ConsoleScript $emergencyRestoreName
        $restoreScriptReceipts=@($scriptReceipts|Where-Object {$_.name -ceq ($emergencyRestoreName+'.txt')})
        if($restoreScriptReceipts.Count -ne 1){throw 'Emergency restore lacks exactly one retained script receipt.'}
        $expectedRestorePaths=[System.Collections.Generic.List[string]]::new()
        $expectedRestorePathSet=[System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        $expectedRestoreCommandValues=@{}
        foreach($commandLine in $restoreScriptReceipts[0].lines){
          $setMatch=[regex]::Match([string]$commandLine,'^SET "([^"]+)" (.+)$')
          if(!$setMatch.Success){continue}
          $path=[string]$setMatch.Groups[1].Value
          if(!$baselineValues.ContainsKey($path)){throw "Emergency restore script writes a path without a same-run baseline: $path"}
          if(!$expectedRestorePathSet.Add($path)){throw "Emergency restore script writes a duplicate path: $path"}
          $expectedCommandValue=Convert-BaselineToCommandValue $path ([string]$baselineValues[$path])
          if([string]$setMatch.Groups[2].Value -cne $expectedCommandValue){throw "Emergency restore script does not write the captured same-run baseline for $path."}
          $expectedRestorePaths.Add($path)
          $expectedRestoreCommandValues[$path]=$expectedCommandValue
        }
        if($expectedRestorePaths.Count -eq 0){throw 'Emergency restore script contains no typed SET targets.'}
        $emergencyGroups=@(Find-ReadbackGroup $emergencyRestoreName)
        if($emergencyGroups.Count -ne 1){throw 'Emergency restore lacks exactly one indexed readback group.'}
        $emergencyGroup=$emergencyGroups[0]
        $emergencyReceipts=@($emergencyGroup.receipts);$emergencyValueReceipts=@($emergencyGroup.value_receipts)
        if($emergencyReceipts.Count -ne $expectedRestorePaths.Count -or $emergencyValueReceipts.Count -ne $expectedRestorePaths.Count){throw "Emergency restore indexed readback group has $($emergencyReceipts.Count) path receipts and $($emergencyValueReceipts.Count) values; expected exactly $($expectedRestorePaths.Count)."}
        $emergencyComparisons=@();$emergencyOk=$true
        for($ri=0;$ri -lt $expectedRestorePaths.Count;$ri++){
          $path=[string]$expectedRestorePaths[$ri]
          $pathReceipt=$emergencyReceipts[$ri];$valueReceipt=$emergencyValueReceipts[$ri]
          if([string]$pathReceipt.path -cne $path){throw "Emergency restore returned an unexpected, duplicate, or out-of-order path at index ${ri}: $([string]$pathReceipt.path)"}
          if([string]$pathReceipt.alias -cne [string]$valueReceipt.alias -or
             [int]$pathReceipt.open_line_index -ne [int]$valueReceipt.open_line_index -or
             [int]$pathReceipt.close_line_index -ne [int]$valueReceipt.close_line_index -or
             [int]$valueReceipt.line_index -ne ([int]$valueReceipt.open_line_index+1) -or
             [int]$valueReceipt.close_line_index -ne ([int]$valueReceipt.open_line_index+2)){
            throw "Emergency restore path/value receipt pair is incomplete or misindexed for $path."
          }
          $actual=[string]$valueReceipt.value;$before=[string]$baselineValues[$path]
          $same=Compare-NativeValue $path $actual $before
          $emergencyComparisons+=@([ordered]@{path=$path;requested_command_value=$expectedRestoreCommandValues[$path];baseline=$before;restored=$actual;matches=$same;line_index=$valueReceipt.line_index;open_line_index=$valueReceipt.open_line_index;close_line_index=$valueReceipt.close_line_index})
          if(!$same){$emergencyOk=$false}
        }
        if($emergencyOk){
          $restoreReceipt=[ordered]@{schema=1;status='restored';emergency=$true;suite=$Suite;slot=$Slot;process=$processIdentity;baseline_script='resourcebaseline.txt';restore_script=$emergencyRestoreName+'.txt';expected_paths=@($expectedRestorePaths);baseline_values=$baselineValues;comparisons=$emergencyComparisons;validated_utc=[DateTime]::UtcNow.ToString('o');original_failure_preserved=$failure}
          Write-Json (Join-Path $runDir 'RESOURCE_RESTORE_RECEIPT.json') $restoreReceipt
        } else {$restoreReceipt=[ordered]@{schema=1;status='failed';emergency=$true;comparisons=$emergencyComparisons;original_failure_preserved=$failure}}
      }
    }catch{$restoreReceipt=[ordered]@{schema=1;status='failed';emergency=$true;error=$_.Exception.Message;original_failure_preserved=$failure}}
  }
  $receipt=[ordered]@{schema=2;status='fail';suite=$Suite;slot=$Slot;started_utc=$startedAt.ToString('o');failed_utc=[DateTime]::UtcNow.ToString('o');error=$failure;process=$processIdentity;private_display_config=[ordered]@{source_sha256=$privateDisplayPlan.source_sha256;private_sha256=$privateDisplayPlan.derived_sha256;width=$script:expectedCaptureWidth;height=$script:expectedCaptureHeight;fullscreen=[int]$privateDisplayPlan.private_values.Fullscreen;capture_frame_file_bytes=$script:expectedFrameFileBytes;frame_reserve_bytes=$script:frameReserveBytes};dump_cleanup=$(if($dump){$dump.cleanup}else{'not_completed'});restore_complete=($null -ne $restoreReceipt -and $restoreReceipt.status -ceq 'restored');restore_receipt='RESOURCE_RESTORE_RECEIPT.json';readback_groups=@($readbackGroups);early_partial_baseline_receipt=$(if($Suite -eq 'resource_windows' -and $driverPlan.candidate_execution_scope.suites.resource_windows.enable_max_partial_fixups -eq $true){'RESOURCE_EARLY_PARTIAL_BASELINE.json'}else{$null});candidate_scope_id=[string]$candidateScope.scope_id;candidate_excluded_site_ids=@($candidateScope.excluded_site_ids);phase_count=$phases.Count;phase_names=@($phases|ForEach-Object {$_.name});baseline_values=$baselineValues;frame_receipts=@($frameReceipts);input_receipts=@($inputReceipts);source_script_receipts=@($scriptReceipts)}
  $receipt.stimulus_process=$stimulusProcessIdentity
  try { Write-Json $driverReceiptPath $receipt } catch { }
}
finally {
  if ($null -ne $frameEvent) { try {$frameEvent.Dispose()} catch {} }
  foreach ($e in $keyEvents.Values) { try {$e.Reset()|Out-Null;$e.Dispose()} catch {} }
  if($null -ne $gameProcess){try{$gameProcess.Dispose()}catch{}}
}
if($null -ne $processIdentity -and $null -ne $restoreReceipt -and $restoreReceipt.status -ceq 'restored'){
  try{
    $restorePath=Join-Path $runDir 'RESOURCE_RESTORE_RECEIPT.json'
    $driverPath=Join-Path $runDir 'RESOURCE_DRIVER_RECEIPT.json'
    $witnessPath=Join-Path $runDir 'RESOURCE_PHASE_DONE_WITNESS.json'
    if(Test-Path -LiteralPath $witnessPath){throw 'Refusing to reuse an existing semantic/restoration witness.'}
    if($null -eq $stimulusProcess -or $script:stimulusProcessHandle -eq [IntPtr]::Zero){throw 'Setup stimulus process identity/handle is missing before witness write.'}
    $stimulusProcess.Refresh()
    if($stimulusProcess.HasExited -or $stimulusProcess.Handle -ne $script:stimulusProcessHandle){throw 'Setup stimulus process handle/start identity changed before witness write.'}
    $driverSha=(Get-FileHash -LiteralPath $driverPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $restoreSha=(Get-FileHash -LiteralPath $restorePath -Algorithm SHA256).Hash.ToLowerInvariant()
    $witness=[ordered]@{schema=2;status=$(if($driverSuccessful){'resource_actions_complete_and_restored'}else{'resource_actions_failed_but_restored'});suite=$Suite;slot=$Slot;process=$processIdentity;driver_process=$stimulusProcessIdentity;phase_actions_complete=[bool]$driverSuccessful;restoration_verified=$true;driver_receipt_sha256=$driverSha;restore_receipt_sha256=$restoreSha;readback_groups_count=$readbackGroups.Count;indexed_value_receipts_count=(@($readbackGroups|ForEach-Object {@($_.value_receipts).Count}|Measure-Object -Sum).Sum);frame_receipts_count=$frameReceipts.Count;dump_cleanup=$(if($dump){$dump.cleanup}else{'not_completed'});original_failure=$failure;created_utc=[DateTime]::UtcNow.ToString('o')}
    $witnessTemp=$witnessPath+'.tmp'
    Write-Json $witnessTemp $witness
    if(Test-Path -LiteralPath $witnessPath){throw 'Semantic/restoration witness appeared before the atomic publish.'}
    [IO.File]::Move($witnessTemp,$witnessPath)
  }catch{
    $witnessFailure=$_.Exception.Message
    if($driverSuccessful){
      $driverSuccessful=$false
      try{$finalDriver=Get-Content -LiteralPath (Join-Path $runDir 'RESOURCE_DRIVER_RECEIPT.json') -Raw|ConvertFrom-Json;$finalDriver.status='fail';$finalDriver.error='Semantic/restoration witness write failed: '+$witnessFailure;$finalDriver.witness_write_failed=$true;Write-Json (Join-Path $runDir 'RESOURCE_DRIVER_RECEIPT.json') $finalDriver}catch{}
    }
    Write-Log ('PHASE_DONE_WITNESS fail: '+$witnessFailure)
    try{Write-Json (Join-Path $runDir 'RESOURCE_PHASE_DONE_WITNESS_FAILURE.json') ([ordered]@{schema=1;status='failed';suite=$Suite;slot=$Slot;process=$processIdentity;driver_process=$stimulusProcessIdentity;error=$witnessFailure;restoration_still_verified=$true;created_utc=[DateTime]::UtcNow.ToString('o')})}catch{}
  }
}
if($null -ne $stimulusProcess){try{$stimulusProcess.Dispose()}catch{}}
if(!$driverSuccessful){exit 1}
