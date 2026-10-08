# VW_DEFORM_debugkeys.ps1 -- drive the in-game debug UI of a running game through the named-event
# key channels (Local\BurnoutPC_DebugKey_XX[_slot], the same channels b5-decomp\tests\run_debug_menu.ps1
# and STUBS_ONACT_debugpage.ps1 use; flow_run sets BRN_INPUT_ALLOW_BACKGROUND). Started by a case's
# Setup scriptblock; never run it by hand while another game is up.
#
# -StepsFile names a text file with one step per line, run in order:
#   wait:<regex>     until the game log (read shared) matches <regex> after the previous wait's match
#   key:<vk>[+shift|+ctrl]  tap one virtual key (192 = console toggle, 13 = enter, 37..40 arrows)
#   cmd:<text>       type <text> into the open console and press enter
#   sleep:<sec>      wall-clock pause
#   note:<text>      a line in the helper log
# The helper log (<OutDir>\vw_deform_keys.log) records every step with the game-log line count at
# the time, so a check can attribute a game line to the step that preceded it.
param(
  [Parameter(Mandatory = $true)][string]$GameLog,
  [Parameter(Mandatory = $true)][string]$OutDir,
  [Parameter(Mandatory = $true)][string]$StepsFile,
  [int]$Slot = 0,
  [int]$TimeoutSec = 200
)
$ErrorActionPreference = 'Stop'
$helperLog = Join-Path $OutDir 'vw_deform_keys.log'
function Say([string]$s) { Add-Content -LiteralPath $helperLog -Value ("{0} {1}" -f (Get-Date).ToString('HH:mm:ss.fff'), $s) }

$suffix = if ($Slot -gt 0) { "_$Slot" } else { '' }
$keys = @{}
for ($key = 0; $key -lt 256; $key++) {
  $keys[$key] = [Threading.EventWaitHandle]::new($false, [Threading.EventResetMode]::ManualReset,
      ('Local\BurnoutPC_DebugKey_{0:X2}{1}' -f $key, $suffix))
  $keys[$key].Reset() | Out-Null
}
function Tap-Key([int]$Key, [bool]$Shift = $false, [bool]$Control = $false) {
  if ($Shift) { $keys[16].Set() | Out-Null }
  if ($Control) { $keys[17].Set() | Out-Null }
  Start-Sleep -Milliseconds 20
  $keys[$Key].Set() | Out-Null
  Start-Sleep -Milliseconds 60
  $keys[$Key].Reset() | Out-Null
  $keys[16].Reset() | Out-Null
  $keys[17].Reset() | Out-Null
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
        '/' { Tap-Key 191 }
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
  $fs = [IO.File]::Open($GameLog, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete)
  try { return (New-Object IO.StreamReader($fs)).ReadToEnd() } finally { $fs.Dispose() }
}
function Log-Lines { return ([regex]::Matches((Read-Log), "`n")).Count }

try {
  $t0 = Get-Date
  Say "waiting for a game started after $($t0.ToString('HH:mm:ss'))"
  while ($true) {
    if (((Get-Date) - $t0).TotalSeconds -gt $TimeoutSec) { Say 'RESULT FAIL: no game'; exit 1 }
    $proc = Get-Process -Name 'Burnout_PC' -ErrorAction SilentlyContinue | Where-Object { $_.StartTime -ge $t0 } | Select-Object -First 1
    if ($proc -and (Test-Path -LiteralPath $GameLog) -and (Get-Item $GameLog).LastWriteTime -ge $t0) { break }
    Start-Sleep -Milliseconds 500
  }
  $from = 0
  $i = 0
  foreach ($step in @(Get-Content -LiteralPath $StepsFile | Where-Object { $_ -ne '' })) {
    ++$i
    $kind, $arg = $step -split ':', 2
    switch ($kind) {
      'wait' {
        while ($true) {
          if (((Get-Date) - $t0).TotalSeconds -gt $TimeoutSec) { Say "RESULT FAIL: step $i timed out waiting for $arg"; exit 1 }
          $text = Read-Log
          $m = [regex]::new($arg, 'Multiline').Match($text, [math]::Min($from, $text.Length))
          if ($m.Success) { $from = $m.Index + $m.Length; break }
          Start-Sleep -Milliseconds 250
        }
      }
      'key' {
        $parts = $arg -split '\+'
        Tap-Key ([int]$parts[0]) ($parts -contains 'shift') ($parts -contains 'ctrl')
      }
      'cmd' { Type-Text $arg; Tap-Key 13; Start-Sleep -Milliseconds 300 }
      'sleep' { Start-Sleep -Milliseconds ([int]([double]$arg * 1000)) }
      'note' { }
      default { throw "Unknown step kind: $kind" }
    }
    Say ("step {0} {1} (log line {2})" -f $i, $step, (Log-Lines))
  }
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
