# PROOF_waitbox.ps1 -- wait (polling, 5 s) until the slot-0 box lock is free, up to -MaxSec.
# Prints FREE after <n>s and exits 0, or BUSY and exits 1. Touches nothing but the mutex probe.
param([int]$MaxSec = 540)
$t0 = Get-Date
while ($true) {
  $m = New-Object System.Threading.Mutex($false, "Local\BurnoutPC_FlowRun")
  $got = $false
  try { $got = $m.WaitOne([TimeSpan]::Zero) } catch [System.Threading.AbandonedMutexException] { $got = $true }
  if ($got) { $m.ReleaseMutex(); $m.Dispose(); Write-Host ("FREE after {0:f0}s" -f ((Get-Date) - $t0).TotalSeconds); exit 0 }
  $m.Dispose()
  if (((Get-Date) - $t0).TotalSeconds -ge $MaxSec) { Write-Host ("BUSY after {0:f0}s" -f $MaxSec); exit 1 }
  Start-Sleep -Seconds 5
}
