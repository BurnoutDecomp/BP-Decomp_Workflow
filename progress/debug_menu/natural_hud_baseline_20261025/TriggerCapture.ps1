param(
  [Parameter(Mandatory=$true)][int]$ExpectedPid,
  [Parameter(Mandatory=$true)][string]$ExpectedStartUtc
)
$ErrorActionPreference = 'Stop'
[Diagnostics.Process]::GetCurrentProcess().PriorityClass = [Diagnostics.ProcessPriorityClass]::BelowNormal
$root = $PSScriptRoot
$slot = 62076
$image = [IO.Path]::GetFullPath((Join-Path $root 'stage/slot/Burnout_PC.exe'))
$gameLog = Join-Path $root 'stage/slot/BrnGame.log'
$start = [DateTime]::Parse($ExpectedStartUtc).ToUniversalTime()
$deadline = [DateTime]::UtcNow.AddSeconds(35)
function Assert-Owner {
  $games = @(Get-CimInstance Win32_Process -Filter "Name LIKE 'Burnout%.exe' OR Name='TUB_Burnout_PC_External.exe' OR Name='BrnGame.exe'")
  if ($games.Count -ne 1 -or [int]$games[0].ProcessId -ne $ExpectedPid -or
      !$games[0].ExecutablePath -or [IO.Path]::GetFullPath($games[0].ExecutablePath) -ine $image) { throw 'Foreign game or image identity changed.' }
  $owned = [Diagnostics.Process]::GetProcessById($ExpectedPid)
  if ($owned.HasExited -or $owned.StartTime.ToUniversalTime().Ticks -ne $start.Ticks) { throw 'PID/start identity changed.' }
}
function Read-CompleteLines {
  $stream = [IO.File]::Open($gameLog,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
  $reader = [IO.StreamReader]::new($stream,[Text.Encoding]::UTF8)
  try { $text = $reader.ReadToEnd() } finally { $reader.Dispose() }
  $last = $text.LastIndexOf([char]10)
  if ($last -lt 0) { return @() }
  return @($text.Substring(0,$last).Split([char]10) | ForEach-Object { $_.TrimEnd([char]13) })
}
Assert-Owner
if ((Get-FileHash -LiteralPath $image -Algorithm SHA256).Hash.ToLowerInvariant() -cne 'a87c43e38b2aeca43f532f7d9e9b8a5ef9a8b883aa27e640962e05641e8b8c43') { throw 'Unexpected executable bytes.' }
if (Test-Path -LiteralPath (Join-Path $root 'CAPTURE_REQUEST.json')) { throw 'A capture was already attempted.' }
$engine = $null
do {
  Assert-Owner
  if (Test-Path -LiteralPath $gameLog) {
    if ((Get-Item -LiteralPath $gameLog).LastWriteTimeUtc -lt $start) { throw 'Game log is stale.' }
    $lines = @(Read-CompleteLines)
    if ($lines -match '\[ASSERT(?:\s+\d+)?\]|\[EXCEPTION\]') { throw 'Game asserted or raised an exception.' }
    $engine = $lines | Where-Object { $_ -match '^\[ignition\] tick state=' } | Select-Object -Last 1
    if ($engine -match '^\[ignition\] tick state=2\b.*\binCarSelect=0\b.*\bbrake=1\.0+\b') { break }
  }
  Start-Sleep -Milliseconds 250
} while ([DateTime]::UtcNow -lt $deadline)
if ($engine -notmatch '^\[ignition\] tick state=2\b.*\binCarSelect=0\b.*\bbrake=1\.0+\b') { throw 'No player engine/brake prerequisite observed.' }
$cursor = $lines.Count
$eventName = 'Local\BurnoutPC_FrameRequest_{0}_{1}' -f $ExpectedPid,$slot
$event = [Threading.EventWaitHandle]::new($false,[Threading.EventResetMode]::ManualReset,$eventName)
try {
  Assert-Owner
  $event.Reset() | Out-Null
  $record = [ordered]@{pid=$ExpectedPid;image=$image;start_utc=$start.ToString('o');slot=$slot;event_name=$eventName;game_log_prefix_lines=$cursor;engine_witness=$engine;request_utc=[DateTime]::UtcNow.ToString('o');debug_controls=0}
  $record | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $root 'CAPTURE_REQUEST.json') -Encoding UTF8
  if (!$event.Set()) { throw 'Frame request failed.' }
  $ack = $null
  $ackDeadline = [DateTime]::UtcNow.AddSeconds(10)
  do {
    Assert-Owner
    $after = @(Read-CompleteLines)
    $ack = $after | Select-Object -Skip $cursor | Where-Object { $_ -match ('^\[frame-request\] pid='+$ExpectedPid+' slot='+$slot+' seq=1 present=\d+ file=bb_\d{6}\.bmp$') } | Select-Object -First 1
    if ($ack) { break }
    Start-Sleep -Milliseconds 100
  } while ([DateTime]::UtcNow -lt $ackDeadline)
  if (!$ack -or $event.WaitOne(0)) { throw 'No owner-bound capture acknowledgement/reset.' }
  [ordered]@{pid=$ExpectedPid;slot=$slot;ack=$ack;event_reset=$true;debug_controls=0;pixel_review='pending'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $root 'CAPTURE_ACK.json') -Encoding UTF8
  Write-Output $ack
} finally { $event.Dispose() }
