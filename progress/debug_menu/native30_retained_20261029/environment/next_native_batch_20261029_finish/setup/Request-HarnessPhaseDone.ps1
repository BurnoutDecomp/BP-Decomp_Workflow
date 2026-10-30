[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][ValidateRange(1,2147483647)][int]$ProcessId,
  [Parameter(Mandatory=$true)][ValidateRange(1,2147483647)][int]$Slot,
  [Parameter(Mandatory=$true)][string]$ExpectedImagePath,
  [Parameter(Mandatory=$true)][string]$ExpectedStartUtc,
  [Parameter(Mandatory=$true)][string]$WitnessPath,
  [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-fA-F]{64}$')][string]$WitnessSha256,
  [Parameter(Mandatory=$true)][string]$ReceiptPath
)

$ErrorActionPreference = 'Stop'

function Get-ExactOwnedProcess([Diagnostics.Process]$Process, [Int64]$RetainedHandle, [string]$FullImagePath, [long]$StartTicks) {
  if ($null -eq $Process -or $RetainedHandle -eq 0) { throw 'No retained process handle was supplied.' }
  $Process.Refresh()
  if ($Process.HasExited) { throw 'Owned process has exited.' }
  if ($Process.StartTime.ToUniversalTime().Ticks -ne $StartTicks) { throw 'Owned process start time changed.' }
  $rows = @(Get-CimInstance Win32_Process -Filter "ProcessId=$($Process.Id)" -ErrorAction Stop)
  if ($rows.Count -ne 1 -or [string]::IsNullOrWhiteSpace([string]$rows[0].ExecutablePath)) {
    throw 'Owned process image path could not be pinned by PID.'
  }
  $actualPath = [IO.Path]::GetFullPath([string]$rows[0].ExecutablePath)
  if ($actualPath -ine $FullImagePath) { throw 'Owned process image path changed.' }
  $Process.Refresh()
  if ($Process.HasExited -or $Process.StartTime.ToUniversalTime().Ticks -ne $StartTicks) {
    throw 'Owned process exited or changed identity during validation.'
  }
  return $true
}

$expectedImage = [IO.Path]::GetFullPath($ExpectedImagePath)
$expectedStart = [DateTimeOffset]::Parse(
  $ExpectedStartUtc,
  [Globalization.CultureInfo]::InvariantCulture,
  [Globalization.DateTimeStyles]::RoundtripKind
).UtcDateTime
$witness = (Resolve-Path -LiteralPath $WitnessPath -ErrorAction Stop).Path
$witnessItem = Get-Item -LiteralPath $witness -Force
if ($witnessItem.PSIsContainer -or ($witnessItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
  throw 'Witness must be a regular, non-reparse file.'
}
$actualWitnessHash = (Get-FileHash -LiteralPath $witness -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualWitnessHash -cne $WitnessSha256.ToLowerInvariant()) { throw 'Witness SHA-256 does not match the caller-bound value.' }
$receipt = [IO.Path]::GetFullPath($ReceiptPath)
if (Test-Path -LiteralPath $receipt) { throw 'Receipt path already exists; refusing overwrite.' }
$receiptParent = Split-Path -Parent $receipt
if (-not (Test-Path -LiteralPath $receiptParent -PathType Container)) { throw 'Receipt parent directory must already exist.' }

$owned = $null
$phaseEvent = $null
$eventSet = $false
$pending = $receipt + '.pending.' + [Guid]::NewGuid().ToString('N')
try {
  $owned = [Diagnostics.Process]::GetProcessById($ProcessId)
  # Accessing Handle forces a retained native process handle; PID lookup alone is not identity.
  $retainedHandle = $owned.Handle.ToInt64()
  Get-ExactOwnedProcess $owned $retainedHandle $expectedImage $expectedStart.Ticks | Out-Null
  $eventName = 'Local\BurnoutPC_HarnessPhaseDone_{0}_{1}_{2}' -f $ProcessId,$Slot,$expectedStart.Ticks
  $phaseEvent = [Threading.EventWaitHandle]::OpenExisting($eventName)
  Get-ExactOwnedProcess $owned $retainedHandle $expectedImage $expectedStart.Ticks | Out-Null

  $record = [ordered]@{
    schema = 1
    status = 'exact_owned_phase_completion_stop_requested'
    process_id = $ProcessId
    image = $expectedImage
    start_utc = $expectedStart.ToString('o')
    slot = $Slot
    retained_process_handle = $true
    witness_path = $witness
    witness_sha256 = $actualWitnessHash
    event_name = $eventName
    event_set = $false
    utc = [DateTime]::UtcNow.ToString('o')
  }
  $json = $record | ConvertTo-Json -Depth 4
  [IO.File]::WriteAllText($pending, $json, [Text.UTF8Encoding]::new($false))
  if (-not $phaseEvent.Set()) { throw 'Phase-done event Set returned false.' }
  $eventSet = $true
  $record.event_set = $true
  $record.utc = [DateTime]::UtcNow.ToString('o')
  $json = $record | ConvertTo-Json -Depth 4
  [IO.File]::WriteAllText($pending, $json, [Text.UTF8Encoding]::new($false))
  [IO.File]::Move($pending, $receipt)
  Write-Output ("PHASE_DONE_REQUESTED pid={0} slot={1} start={2} witness_sha256={3} receipt={4}" -f `
    $ProcessId,$Slot,$expectedStart.ToString('o'),$actualWitnessHash,$receipt)
} catch {
  if ($eventSet) {
    Write-Error ("The exact phase event was set, but the success receipt could not be finalized; inspect {0}. Error: {1}" -f $pending,$_.Exception.Message)
  } else {
    if (Test-Path -LiteralPath $pending) { Remove-Item -LiteralPath $pending -Force -ErrorAction SilentlyContinue }
    throw
  }
} finally {
  if ($phaseEvent) { $phaseEvent.Dispose() }
  if ($owned) { $owned.Dispose() }
}
