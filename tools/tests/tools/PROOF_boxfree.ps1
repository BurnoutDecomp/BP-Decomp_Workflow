# PROOF_boxfree.ps1 -- is the slot-0 box lock free right now? Prints FREE or BUSY and exits 0/1.
# Takes the mutex for zero time only (acquire + immediate release); touches nothing else.
$m = New-Object System.Threading.Mutex($false, "Local\BurnoutPC_FlowRun")
$got = $false
try { $got = $m.WaitOne([TimeSpan]::Zero) } catch [System.Threading.AbandonedMutexException] { $got = $true }
if ($got) { $m.ReleaseMutex(); Write-Host "FREE"; exit 0 }
Write-Host "BUSY"
$p = Get-CimInstance Win32_Process -Filter "Name='Burnout_PC.exe'" | Select-Object -ExpandProperty ExecutablePath
if ($p) { Write-Host ("game: " + ($p -join '; ')) }
exit 1
