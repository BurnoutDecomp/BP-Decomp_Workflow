# VW_CAMPARAMS_testbed.ps1 -- the concurrent stimulus of tools\tests\cases\vw_camparams_testbed.ps1.
#
# Opens the director's "Camera" debug page in a running game through the debug console (the same
# named-event key harness as STUBS_ONACT_debugpage.ps1 and b5-decomp\tests\run_debug_menu.ps1),
# opens its "Testbed" submenu as a window and walks it with the Down key. The game runs with
# BRN_DEBUG_UI_TRACE=1, so every key press logs a [debug-ui] line naming the selected row; the
# distinct selections are the Testbed menu's rows. Once the car has been driving it types
#     COMPONENT "Camera"                       -> DebugComponent::OnActivate (registers the Testbed rows)
#     BIND F12 *WINDOW /Camera/Testbed 84 101  -> F12 opens the Testbed menu as a window
# closes the console, presses F12, snapshots the newest dumped frame, presses Down 60 times,
# snapshots again and writes the rows it saw to testbed_rows.txt (one per line, first-seen order)
# next to its own log (testbed_helper.log). The case's checks read both.
param(
  [Parameter(Mandatory = $true)][string]$GameLog,
  [Parameter(Mandatory = $true)][string]$OutDir,
  [int]$Slot = 0,
  [int]$TimeoutSec = 180,
  [double]$DriveSeconds = 10.0,
  [int]$Downs = 60
)
$ErrorActionPreference = 'Stop'
$helperLog = Join-Path $OutDir 'testbed_helper.log'
function Say([string]$s) { Add-Content -LiteralPath $helperLog -Value ("{0} {1}" -f (Get-Date).ToString('HH:mm:ss.fff'), $s) }

$suffix = if ($Slot -gt 0) { "_$Slot" } else { '' }
$keys = @{}
for ($key = 0; $key -lt 256; $key++) {
  $keys[$key] = [Threading.EventWaitHandle]::new($false, [Threading.EventResetMode]::ManualReset,
      ('Local\BurnoutPC_DebugKey_{0:X2}{1}' -f $key, $suffix))
  $keys[$key].Reset() | Out-Null
}
function Tap-Key([int]$Key, [bool]$Shift = $false) {
  if ($Shift) { $keys[16].Set() | Out-Null }
  Start-Sleep -Milliseconds 20
  $keys[$Key].Set() | Out-Null
  Start-Sleep -Milliseconds 60
  $keys[$Key].Reset() | Out-Null
  $keys[16].Reset() | Out-Null
  Start-Sleep -Milliseconds 60
}
function Type-Text([string]$Text) {
  foreach ($c in $Text.ToCharArray()) {
    $n = [int]$c
    if ($n -ge 97 -and $n -le 122) { Tap-Key ($n - 32) }
    elseif ($n -ge 65 -and $n -le 90) { Tap-Key $n $true }
    elseif ($n -ge 48 -and $n -le 57) { Tap-Key $n }
    else {
      switch ($c) {
        ' ' { Tap-Key 32 }
        '"' { Tap-Key 222 $true }
        '/' { Tap-Key 191 }
        '*' { Tap-Key 56 $true }
        '.' { Tap-Key 190 }
        '-' { Tap-Key 189 }
        '_' { Tap-Key 189 $true }
        default { throw "Unsupported character: $c" }
      }
    }
  }
}
function Read-Log {
  # The game holds its log open for writing: read it shared.
  $fs = [IO.File]::Open($GameLog, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete)
  try { return (New-Object IO.StreamReader($fs)).ReadToEnd() } finally { $fs.Dispose() }
}
function Command([string]$Text) {
  Type-Text $Text
  Tap-Key 13
  Start-Sleep -Milliseconds 400
  Say "typed: $Text"
}
function Snapshot([string]$Name) {
  Start-Sleep -Milliseconds 1500
  $frameDir = Join-Path $OutDir 'frames'
  $frame = Get-ChildItem -LiteralPath $frameDir -Filter '*.bmp' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1
  if ($frame) {
    Copy-Item -LiteralPath $frame.FullName -Destination (Join-Path $OutDir "$Name.bmp") -Force
    Say "snapshot $Name <- $($frame.Name)"
  } else { Say "snapshot ${Name}: no frame dumped yet" }
}

try {
  $t0 = Get-Date
  Say "waiting for a game started after $($t0.ToString('HH:mm:ss')) and its car-select exit"
  $ready = $false
  while (((Get-Date) - $t0).TotalSeconds -lt $TimeoutSec) {
    $proc = Get-Process -Name 'Burnout_PC' -ErrorAction SilentlyContinue | Where-Object { $_.StartTime -ge $t0 } | Select-Object -First 1
    if ($proc -and ((Get-Date) - $proc.StartTime).TotalSeconds -ge 5 -and (Test-Path -LiteralPath $GameLog)) {
      $text = (Read-Log)
      if ($text -match 'CarSelectManager: Exit state is finished') { $ready = $true; break }
    }
    Start-Sleep -Milliseconds 500
  }
  if (-not $ready) { Say 'RESULT FAIL: the game never left car select'; exit 1 }
  Say ("car-select exit seen; driving {0:f0}s before opening the page" -f $DriveSeconds)
  Start-Sleep -Milliseconds ([int]($DriveSeconds * 1000))

  $before = ([regex]::Matches((Read-Log), '\[ASSERT \d+\]')).Count
  Tap-Key 192
  Command 'component "Camera"'
  Command 'bind F12 *WINDOW /Camera/Testbed 84 101'
  Tap-Key 192
  $logStart = (Read-Log).Length
  Tap-Key 123
  Snapshot 'testbed_menu_top'
  for ($i = 0; $i -lt $Downs; ++$i) {
    Tap-Key 40
    Start-Sleep -Milliseconds 120
  }
  Snapshot 'testbed_menu_walked'
  Start-Sleep -Seconds 1
  $text = (Read-Log)
  $tail = if ($text.Length -gt $logStart) { $text.Substring($logStart) } else { '' }
  $rows = New-Object System.Collections.Generic.List[string]
  foreach ($m in [regex]::Matches($tail, '\[debug-ui\][^\r\n]*selection="([^"\r\n]*)"')) {
    $name = $m.Groups[1].Value
    if ($name -ne '' -and -not $rows.Contains($name)) { $rows.Add($name) }
  }
  Set-Content -LiteralPath (Join-Path $OutDir 'testbed_rows.txt') -Value $rows -Encoding UTF8
  Say ("[debug-ui] lines after F12: {0}; distinct selections: {1}" -f ([regex]::Matches($tail, '\[debug-ui\]')).Count, $rows.Count)
  Tap-Key 27
  Start-Sleep -Seconds 2
  $after = ([regex]::Matches((Read-Log), '\[ASSERT \d+\]')).Count
  Say ("assert lines in the game log: {0} before the page opened, {1} after" -f $before, $after)
  Say 'RESULT DONE'
  exit 0
}
catch {
  Say ("RESULT FAIL: {0}" -f $_.Exception.Message)
  exit 1
}
finally {
  foreach ($k in $keys.Values) { try { $k.Reset() | Out-Null; $k.Dispose() } catch { } }
}
