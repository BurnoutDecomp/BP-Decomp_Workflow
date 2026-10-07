# STUBS_mount.ps1 -- add or remove ONE source line in tools\build\build_game_exe.bat, safely.
#
#   powershell -ExecutionPolicy Bypass -File tools\tests\tools\STUBS_mount.ps1 -Add    GameSource\Foo\Bar.cpp -Lane <LANE>
#   powershell -ExecutionPolicy Bypass -File tools\tests\tools\STUBS_mount.ps1 -Remove GameSource\Foo\Bar.cpp -Lane <LANE>
#
# Paths are relative to b5-decomp\src (backslashes). The edit runs under the box lock, so no build
# (which reads the bat incrementally) is running while the file changes. -Add inserts the line just
# before the closing "/Fo ... /Fe" echo; it refuses if the path is already mounted or the .cpp does
# not exist. -Remove deletes the matching echo line (exact path match). Every change is appended to
# scratch\stubs_wave\MOUNTS.log. CRLF is preserved.
param(
  [string]$Add = "",
  [string]$Remove = "",
  [string]$DropFilter = "",
  [string]$Lane = "?"
)
$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
. (Join-Path $root 'tools\diagnostics\_box_lock.ps1')

if ($DropFilter -ne "") {
  # Removes the 'findstr /v /c:"<substring>"' source-drop line (and the move line after it).
  $bat = Join-Path $root 'tools\build\build_game_exe.bat'
  Enter-BoxLock -Label "mount:$Lane"
  $ls = [System.Collections.Generic.List[string]]::new()
  foreach ($l in ([System.IO.File]::ReadAllText($bat) -split "`r`n")) { $ls.Add($l) }
  $k = -1
  for ($i = 0; $i -lt $ls.Count; $i++) { if ($ls[$i] -like 'findstr /v*' -and $ls[$i].Contains($DropFilter)) { $k = $i; break } }
  if ($k -lt 0) { Write-Host "[mount] no findstr filter for: $DropFilter"; exit 1 }
  if ($k + 1 -lt $ls.Count -and $ls[$k + 1] -like 'move /y "%RSP%.tmp"*') { $ls.RemoveAt($k + 1) }
  $ls.RemoveAt($k)
  [System.IO.File]::WriteAllText($bat, ($ls -join "`r`n"))
  $logDir = Join-Path $root 'scratch\stubs_wave'
  New-Item -ItemType Directory -Force $logDir | Out-Null
  Add-Content -Path (Join-Path $logDir 'MOUNTS.log') -Value ("{0} {1} DROPFILTER {2}" -f (Get-Date).ToString('HH:mm:ss'), $Lane, $DropFilter)
  Write-Host "[mount] dropped source filter: $DropFilter (its explanatory rem lines above are yours to delete via report)"
  exit 0
}
if (($Add -eq "") -eq ($Remove -eq "")) { Write-Host "[mount] give exactly one of -Add / -Remove / -DropFilter"; exit 2 }
$rel = if ($Add) { $Add } else { $Remove }
$rel = $rel.Replace('/', '\').TrimStart('\')
if ($rel -like 'src\*') { $rel = $rel.Substring(4) }
$bat = Join-Path $root 'tools\build\build_game_exe.bat'
$line = '  echo "%SRC%\' + $rel + '"'

Enter-BoxLock -Label "mount:$Lane"

$text = [System.IO.File]::ReadAllText($bat)
$lines = [System.Collections.Generic.List[string]]::new()
foreach ($l in ($text -split "`r`n")) { $lines.Add($l) }
$hits = @()
for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i].Trim() -ieq $line.Trim()) { $hits += $i } }

if ($Add) {
  if (-not (Test-Path (Join-Path $root ("b5-decomp\src\" + $rel)))) { Write-Host "[mount] no such file: src\$rel"; exit 1 }
  if ($hits.Count -gt 0) { Write-Host "[mount] already mounted (line $($hits[0] + 1)): $rel"; exit 0 }
  $anchor = -1
  for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -like '*echo /Fo"%OUT%*') { $anchor = $i; break } }
  if ($anchor -lt 0) { Write-Host "[mount] anchor line not found"; exit 1 }
  $lines.Insert($anchor, $line)
  $what = "ADD"
} else {
  if ($hits.Count -eq 0) { Write-Host "[mount] not mounted: $rel"; exit 1 }
  foreach ($i in ($hits | Sort-Object -Descending)) { $lines.RemoveAt($i) }
  $what = "REMOVE"
}
[System.IO.File]::WriteAllText($bat, ($lines -join "`r`n"))
$logDir = Join-Path $root 'scratch\stubs_wave'
New-Item -ItemType Directory -Force $logDir | Out-Null
Add-Content -Path (Join-Path $logDir 'MOUNTS.log') -Value ("{0} {1} {2} {3}" -f (Get-Date).ToString('HH:mm:ss'), $Lane, $what, $rel)
Write-Host "[mount] $what $rel"
exit 0
