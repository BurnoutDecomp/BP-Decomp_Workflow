# STUBS_ONACT_debugpage.ps1 -- the concurrent stimulus of tools\tests\cases\onact_debug_page.ps1.
#
# Opens the director's "Camera" debug page in a running game through the debug console, the same
# named-event key harness b5-decomp\tests\run_debug_menu.ps1 drives (Local\BurnoutPC_DebugKey_XX;
# flow_run sets BRN_INPUT_ALLOW_BACKGROUND). Once the car has been driving for a while it types
#     COMPONENT "Camera"      -> DebugManager::ActivateComponent -> BrnDirector::DebugComponent::OnActivate
#     SAVE "<file>"           -> every writable registered variable as a SET line
# and copies the saved state into the run dir (onact_state.txt) next to its own log (onact_helper.log).
# The case's checks read both. Started by the case's Setup scriptblock; never run it by hand while
# another game is up.
param(
  [Parameter(Mandatory = $true)][string]$GameLog,
  [Parameter(Mandatory = $true)][string]$OutDir,
  [int]$Slot = 0,
  [int]$TimeoutSec = 180,
  [double]$DriveSeconds = 12.0
)
$ErrorActionPreference = 'Stop'
$helperLog = Join-Path $OutDir 'onact_helper.log'
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
  $stateName = 'onact-state-{0}.txt' -f [guid]::NewGuid().ToString('N').Substring(0, 8)
  $statePath = Join-Path (Split-Path $GameLog -Parent) $stateName
  Tap-Key 192
  Command 'component "Camera"'
  Command ('save "{0}"' -f $stateName)
  Tap-Key 192
  Start-Sleep -Seconds 4
  $after = ([regex]::Matches((Read-Log), '\[ASSERT \d+\]')).Count
  Say ("assert lines in the game log: {0} before the page opened, {1} after" -f $before, $after)
  if (-not (Test-Path -LiteralPath $statePath)) { Say "RESULT FAIL: SAVE wrote no $stateName"; exit 1 }
  Copy-Item -LiteralPath $statePath -Destination (Join-Path $OutDir 'onact_state.txt') -Force
  Remove-Item -LiteralPath $statePath -Force
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
