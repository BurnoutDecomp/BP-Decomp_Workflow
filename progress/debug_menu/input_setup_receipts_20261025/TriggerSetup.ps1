param(
  [Parameter(Mandatory=$true)][int]$ExpectedPid,
  [Parameter(Mandatory=$true)][string]$ExpectedStartUtc
)
$ErrorActionPreference='Stop'
[Diagnostics.Process]::GetCurrentProcess().PriorityClass=[Diagnostics.ProcessPriorityClass]::BelowNormal
$root=$PSScriptRoot;$slot=62079
$image=[IO.Path]::GetFullPath((Join-Path $root 'stage/slot/Burnout_PC.exe'))
$gameLog=Join-Path $root 'stage/slot/BrnGame.log'
$start=[DateTime]::Parse($ExpectedStartUtc).ToUniversalTime()
$deadline=[DateTime]::UtcNow.AddSeconds(65)
$events=@{};$receipts=[Collections.Generic.List[object]]::new()
function Assert-Owner {
  if([DateTime]::UtcNow -gt $deadline){throw 'Setup deadline reached; no more input.'}
  $games=@(Get-CimInstance Win32_Process -Filter "Name LIKE 'Burnout%.exe' OR Name='TUB_Burnout_PC_External.exe' OR Name='BrnGame.exe'")
  if($games.Count -ne 1 -or [int]$games[0].ProcessId -ne $ExpectedPid -or !$games[0].ExecutablePath -or
     [IO.Path]::GetFullPath($games[0].ExecutablePath) -ine $image){throw 'Foreign game or image identity changed.'}
  $owned=[Diagnostics.Process]::GetProcessById($ExpectedPid)
  if($owned.HasExited -or $owned.StartTime.ToUniversalTime().Ticks -ne $start.Ticks){throw 'PID/start identity changed.'}
}
function Lines {
  if(!(Test-Path -LiteralPath $gameLog)){return @()}
  if((Get-Item -LiteralPath $gameLog).LastWriteTimeUtc -lt $start){throw 'Stale game log.'}
  $stream=[IO.File]::Open($gameLog,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
  $reader=[IO.StreamReader]::new($stream,[Text.Encoding]::UTF8)
  try{$text=$reader.ReadToEnd()}finally{$reader.Dispose()}
  $last=$text.LastIndexOf([char]10);if($last -lt 0){return @()}
  return @($text.Substring(0,$last).Split([char]10)|ForEach-Object{$_.TrimEnd([char]13)})
}
function Key([int]$Code){
  if(!$events.ContainsKey($Code)){
    $name='Local\BurnoutPC_DebugKey_{0:X2}_{1}' -f $Code,$slot
    $events[$Code]=[Threading.EventWaitHandle]::new($false,[Threading.EventResetMode]::ManualReset,$name)
    if($events[$Code].SafeWaitHandle.IsInvalid){throw 'Invalid scoped key handle.'}
    $events[$Code].Reset()|Out-Null
  }
  return $events[$Code]
}
function Wait-Line([string]$Pattern,[int]$Cursor,[int]$Seconds){
  $until=[DateTime]::UtcNow.AddSeconds($Seconds)
  do{
    Assert-Owner;$lines=@(Lines)
    if($lines -match '\[ASSERT(?:\s+\d+)?\]|\[EXCEPTION\]'){throw 'Game assert or exception.'}
    for($i=$Cursor;$i -lt $lines.Count;$i++){if($lines[$i] -match $Pattern){return [pscustomobject]@{line=$i+1;text=$lines[$i]}}}
    Start-Sleep -Milliseconds 50
  }while([DateTime]::UtcNow -lt $until)
  throw ('Missing fresh receipt: '+$Pattern)
}
function Observed-Key([int]$Vk,[int]$Code){
  Assert-Owner;$cursor=@(Lines).Count;$key=Key $Vk;$key.Reset()|Out-Null
  try{
    if(!$key.Set()){throw 'Input event Set failed.'}
    $receipt=Wait-Line ('^\[debug-ui\] event=0 visible=1 .* key='+$Code+'$') $cursor 3
    $receipts.Add([ordered]@{vk=$Vk;key=$Code;line=$receipt.line;text=$receipt.text})
    return $receipt
  }finally{$key.Reset()|Out-Null}
}
function Observed-Codes([int]$Cursor){
  $out=[Collections.Generic.List[int]]::new();$lines=@(Lines)
  foreach($line in @($lines|Select-Object -Skip $Cursor)){
    $m=[regex]::Match($line,'^\[debug-ui\] event=0 visible=1 .* key=(\d+)$')
    if($m.Success -and [int]$m.Groups[1].Value -ne 0){$out.Add([int]$m.Groups[1].Value)}
  }
  return $out.ToArray()
}
try{
  Assert-Owner
  if((Get-FileHash -LiteralPath $image -Algorithm SHA256).Hash.ToLowerInvariant() -cne 'a87c43e38b2aeca43f532f7d9e9b8a5ef9a8b883aa27e640962e05641e8b8c43'){throw 'Unexpected executable.'}
  $cfg=Join-Path $root 'stage/data/b1.cfg';$sourceCfg=Join-Path $root 'b1.cfg'
  if((Get-FileHash -LiteralPath $cfg -Algorithm SHA256).Hash -cne (Get-FileHash -LiteralPath $sourceCfg -Algorithm SHA256).Hash){throw 'Private setup config changed.'}
  if(Test-Path -LiteralPath (Join-Path $root 'SETUP_RECEIPTS.json')){throw 'Setup attempt already exists.'}
  [void](Wait-Line '^\[ignition\] tick state=2\b.*\binCarSelect=0\b.*\bbrake=1\.0+\b' 0 35)
  $cursor=@(Lines).Count;$toggle=Key 192;$toggle.Reset()|Out-Null
  try{if(!$toggle.Set()){throw 'Console toggle failed.'};$opened=Wait-Line '^\[debug-ui\] event=9 visible=1 .* key=0$' $cursor 3}finally{$toggle.Reset()|Out-Null}
  $commandStart=@(Lines).Count
  $vks=@(69,88,69,67,32,66,49,190,67,70,71)
  $expected=@(101,120,101,99,32,98,49,46,99,102,103)
  for($i=0;$i -lt $vks.Count;$i++){[void](Observed-Key $vks[$i] $expected[$i])}
  $actual=@(Observed-Codes $commandStart)
  if(($actual -join ',') -cne ($expected -join ',')){throw 'Observed command is incomplete, duplicated or different; Enter not sent.'}
  [void](Observed-Key 13 10)
  $component=Wait-Line '^\[debug-component\] path="Gui/Gui Custom Renderer" request=menu controls=1$' $commandStart 8
  $alias=Wait-Line '^BOutR: /Gui/Gui Custom Renderer/Outer boost Red$' $commandStart 8
  $actual=@(Observed-Codes $commandStart)
  if(($actual -join ',') -cne (($expected+@(10)) -join ',')){throw 'Unexpected extra command keys or Enter.'}
  $window=@(Lines)|Select-Object -Skip $commandStart
  if($window -match 'Cannot open b1\.cfg|Unknown command|Component not found'){throw 'Setup command error.'}
  [ordered]@{status='setup_only_observed_pass';pid=$ExpectedPid;start_utc=$start.ToString('o');slot=$slot;command='exec b1.cfg';codes=$actual;receipts=@($receipts.ToArray());component=$component;alias=$alias;variable_writes=0;control_phases=0;captures=0}|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $root 'SETUP_RECEIPTS.json') -Encoding UTF8
  Write-Output 'SETUP ONLY PASS: full command, Enter, component and alias observed; no variable writes.'
}catch{
  [ordered]@{status='setup_only_fail_no_retry';error=$_.Exception.Message;pid=$ExpectedPid;slot=$slot;receipts=@($receipts.ToArray());control_phases=0;captures=0}|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $root 'SETUP_FAILURE.json') -Encoding UTF8
  throw
}finally{foreach($event in $events.Values){$event.Reset()|Out-Null;$event.Dispose()}}
