# quiet_background_keys.ps1 -- LANE quiet: hold real keys down on the DESKTOP while the game is
# NOT the foreground window, and record, every 200 ms, which window actually had the foreground.
#
# WHY IT EXISTS. The report is "test runs read my keyboard system-wide -- I cannot scroll on
# another window without the test car going all over the place". GetAsyncKeyState reads GLOBAL
# key state, so the only way to measure that claim is to reproduce it: put a different window in
# front, press W/A for real, and then ask the game's own [motion] probe whether the car's
# throttle and steering moved. This script presses nothing in the game and opens no harness
# channel -- the harness input channels are named events and are untouched by it.
#
# IT INJECTS REAL KEYSTROKES ONTO THE DESKTOP. They land in whatever window is foreground --
# which is this script's own topmost form, on purpose, so nothing else on the box receives them.
# Every key is released in the finally block, so a key can never be left stuck down.
#
# It is deliberately NOT a check kind and NOT part of run_case: it has to run CONCURRENTLY with
# flow_run, and every check runs afterwards. The usage is
#     Start-Process powershell -ArgumentList '-File tools\tests\offline\quiet_background_keys.ps1 ...'
#     powershell -File tools\tests\run_case.ps1 -Case quiet_focus_input ...
# and the case's Script check reads the CSV this writes.
param(
  [string]$Keys       = 'W,A',          # VK names (or single characters) to HOLD down
  [double]$HoldSeconds = 20,            # how long to hold them once armed
  [double]$MaxWaitSeconds = 240,        # give up waiting for the arm cue
  [string]$ArmPattern = 'signalling StreamingFinished',   # flow_run's 'strfin' cue == DRIVING
  [double]$ArmDelay   = 8,              # seconds after the cue before pressing (flow_run's DriveDelay)
  [string]$LogPath    = '',             # default build\game\BrnGame.log
  [string]$OutCsv     = ''              # default scratch\bugtest\lanes\quiet_work\bgkeys_<stamp>.csv
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))   # tools\tests\offline -> repo root
if ($LogPath -eq '') { $LogPath = Join-Path $root 'build\game\BrnGame.log' }
if ($OutCsv  -eq '') {
  $d = Join-Path $root 'scratch\bugtest\lanes\quiet_work'
  if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d | Out-Null }
  $OutCsv = Join-Path $d ("bgkeys_" + (Get-Date -Format 'yyyyMMdd_HHmmss') + ".csv")
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class QuietWin32 {
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll", CharSet=CharSet.Ansi)] public static extern IntPtr FindWindowA(string c, string n);
  [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);
  [DllImport("user32.dll")] public static extern short GetAsyncKeyState(int vk);
}
"@

# ---- resolve the key list to virtual-key codes -------------------------------------------
$vkNames = @{ 'SPACE' = 0x20; 'RETURN' = 0x0D; 'ENTER' = 0x0D; 'ESCAPE' = 0x1B; 'UP' = 0x26;
              'DOWN' = 0x28; 'LEFT' = 0x25; 'RIGHT' = 0x27; 'PRIOR' = 0x21; 'NEXT' = 0x22 }
$vks = @()
foreach ($k in ($Keys -split '[,\s]+')) {
  $t = $k.Trim()
  if ($t -eq '') { continue }
  if ($vkNames.ContainsKey($t.ToUpper())) { $vks += [byte]$vkNames[$t.ToUpper()] }
  elseif ($t.Length -eq 1) { $vks += [byte][char]([string]$t).ToUpper() }
  else { Write-Host "[bgkeys] FAIL: unknown key '$t'"; exit 2 }
}
if ($vks.Count -eq 0) { Write-Host '[bgkeys] FAIL: no keys'; exit 2 }
# Belt and braces: release these keys before we ever press them. The hold below is always shorter
# than the run it sits inside, so the finally block is what normally releases them -- but a hard
# kill (run_case stops a Setup process that outlives its run) skips finally, and a key left down
# on the desktop would poison whatever ran next. Clearing at START makes that self-healing.
foreach ($vk in $vks) { [QuietWin32]::keybd_event($vk, 0, 2, [UIntPtr]::Zero) }
Write-Host ("[bgkeys] keys: " + (($vks | ForEach-Object { "0x{0:X2}" -f $_ }) -join ' '))
Write-Host "[bgkeys] waiting for '$ArmPattern' in $LogPath"

# ---- wait for the arm cue in the game's log ----------------------------------------------
$t0 = Get-Date
$armed = $false
while (((Get-Date) - $t0).TotalSeconds -lt $MaxWaitSeconds) {
  if (Test-Path $LogPath) {
    # ⛔ FileShare.ReadWrite IS THE WHOLE POINT. The game holds BrnGame.log open for writing, so
    # [IO.File]::ReadAllText (which asks for FileShare.Read) throws a sharing violation for the
    # entire run and only succeeds once the process has EXITED. Measured: the first version armed
    # at +75.2 s on a 70 s run -- i.e. after the run it was meant to inject into had finished, so
    # it pressed keys at an empty desktop and the case read "the injector never ran".
    try {
      $fs = New-Object System.IO.FileStream($LogPath, [System.IO.FileMode]::Open,
              [System.IO.FileAccess]::Read,
              ([System.IO.FileShare]::ReadWrite -bor [System.IO.FileShare]::Delete))
      try {
        $sr = New-Object System.IO.StreamReader($fs, [System.Text.Encoding]::GetEncoding(28591))
        $txt = $sr.ReadToEnd()
        $sr.Dispose()
      } finally { $fs.Dispose() }
      if ($txt -match $ArmPattern) { $armed = $true; break }
    } catch { }
  }
  Start-Sleep -Milliseconds 300
}
if (-not $armed) { Write-Host "[bgkeys] FAIL: arm cue never appeared in $LogPath"; exit 1 }
Write-Host ("[bgkeys] armed at +{0:f1}s; waiting {1}s for the drive delay" -f `
            ((Get-Date) - $t0).TotalSeconds, $ArmDelay)
Start-Sleep -Milliseconds ([int]($ArmDelay * 1000))

# ---- the focus thief: a topmost form that keeps the foreground away from the game ---------
$form = New-Object System.Windows.Forms.Form
$form.Text = 'quiet lane -- focus thief (the keys typed here are the test stimulus)'
$form.Width = 640; $form.Height = 200
$form.TopMost = $true
$form.StartPosition = 'Manual'
$form.Location = New-Object System.Drawing.Point(40, 40)
$box = New-Object System.Windows.Forms.TextBox
$box.Multiline = $true; $box.Dock = 'Fill'
$form.Controls.Add($box)
$form.Show(); $form.Activate(); $box.Focus() | Out-Null
[System.Windows.Forms.Application]::DoEvents()
[void][QuietWin32]::SetForegroundWindow($form.Handle)

$rows = New-Object System.Collections.Generic.List[string]
# ⚠️ EVERY FIELD IS AN INTEGER OR A HEX STRING, ON PURPOSE. The first version wrote the sample
# time with "{0:f2}", and this box's locale is de-DE, so it wrote `0,02` -- a decimal COMMA inside
# a comma-separated file. Every consumer's field index shifted by one and the run read as "no key
# was ever down" while the raw column said 2. Time is milliseconds, as an integer.
$rows.Add('t_ms,fg_hwnd,game_hwnd,form_hwnd,game_is_foreground,keys_down')
$down = $false
try {
  foreach ($vk in $vks) { [QuietWin32]::keybd_event($vk, 0, 0, [UIntPtr]::Zero) }
  $down = $true
  $tp = Get-Date
  while (((Get-Date) - $tp).TotalSeconds -lt $HoldSeconds) {
    [System.Windows.Forms.Application]::DoEvents()
    $form.TopMost = $true
    [void][QuietWin32]::SetForegroundWindow($form.Handle)
    # re-assert the held keys: a synthetic key-down can be cleared by a focus change
    foreach ($vk in $vks) { [QuietWin32]::keybd_event($vk, 0, 0, [UIntPtr]::Zero) }

    $fg   = [QuietWin32]::GetForegroundWindow()
    $game = [QuietWin32]::FindWindowA('BurnoutParadiseWindowClass', 'Burnout Paradise')
    $nDown = 0
    foreach ($vk in $vks) { if (([QuietWin32]::GetAsyncKeyState([int]$vk) -band 0x8000) -ne 0) { $nDown++ } }
    $isGameFg = 0
    if ($game -ne [IntPtr]::Zero -and $fg -eq $game) { $isGameFg = 1 }
    $rows.Add(("{0},0x{1:X},0x{2:X},0x{3:X},{4},{5}" -f `
      [int](((Get-Date) - $tp).TotalMilliseconds), [int64]$fg, [int64]$game, [int64]$form.Handle, $isGameFg, $nDown))
    Start-Sleep -Milliseconds 200
  }
} finally {
  if ($down) { foreach ($vk in $vks) { [QuietWin32]::keybd_event($vk, 0, 2, [UIntPtr]::Zero) } }  # KEYEVENTF_KEYUP
  try { $form.Close(); $form.Dispose() } catch { }
  [System.IO.File]::WriteAllLines($OutCsv, $rows)
  Write-Host "[bgkeys] wrote $OutCsv ($($rows.Count - 1) samples)"
}

$data   = $rows | Select-Object -Skip 1
$fgGame = @($data | Where-Object { ($_ -split ',')[4] -eq '1' }).Count
$held   = @($data | Where-Object { [int](($_ -split ',')[5]) -gt 0 }).Count
Write-Host ("[bgkeys] samples with the GAME foreground: {0} of {1}; samples with a key really down: {2}" -f `
            $fgGame, $data.Count, $held)
if ($held -eq 0) { Write-Host '[bgkeys] WARNING: no sample saw a key down -- the stimulus did not happen'; exit 1 }
if ($fgGame -gt 0) { Write-Host '[bgkeys] WARNING: the game held the foreground for some samples -- those are not a background measurement' }
exit 0
