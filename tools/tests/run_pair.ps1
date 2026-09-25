# run_pair.ps1 -- run ONE PAIR case: two game instances at once, each on its own slot, each half
# an ordinary run_case.ps1 run, then one verdict for the pair.
#
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_pair.ps1 -Case net_lan_pair
#   ... -SlotA 3 -SlotB 4          # other slots (default 1 and 2 -- never slot 0)
#   ... -ExpectFail                # RED mode: exit 0 only if the PAIR fails
#   ... -NoRun -RunDir <pair dir>  # re-evaluate both halves of a pair run already on disk
#
# WHAT A PAIR CASE IS. A .ps1 under tools\tests\cases\ that takes `param([string]$Role)`:
#   * called with no -Role it returns the DESCRIPTOR: @{ Name; Pair = @{ Roles = @('A','B') } }
#     (no Checks -- run_case.ps1 refuses it, so it can never be run as a lone half by mistake);
#   * called with -Role <r> it returns an ordinary run_case hashtable for that half: its own Run,
#     DiagEnv, Setup (the place to set non-BRN_* environment such as BP_LAN) and Checks.
#   See cases\net_lan_pair.ps1.
#   The descriptor may also carry PAIR-LEVEL checks, which see BOTH halves at once (a half's own
#   Checks only ever see its own log):
#     Pair = @{ Roles = @('Host','Guest'); Checks = @( @{ Name = '...'; Script = { param($p) ... } } ) }
#   $p.Halves.<role> = @{ LogLines; Log; RunDir; MarksText; Verdict; Slot }, $p.RunDir = the pair dir.
#   The Script returns @{ Pass; Detail }, exactly like a half's Script check; a check that throws
#   or returns nothing FAILS. The pair verdict is PASS only if both halves AND every pair check pass.
#
# CROSS-HALF ENVIRONMENT (for flow_run -MenuScript waitpeer / waitfile / signal). Each half's
# process inherits, set here just before it is started (none is a BRN_* name, so flow_run's wipe
# leaves them alone and they reach flow_run by inheritance):
#   BP_PAIR_DIR        the pair run dir; the halves' signal files live in <dir>\signals (emptied here)
#   BP_PAIR_ROLE       this half's role;   BP_PAIR_PEER_ROLE  the other half's
#   BP_PAIR_PEER_LOG   the other half's LIVE log, build\game_slots\<its slot>\BrnGame.log
#   BP_PAIR_T0         the pair start (FILETIME UTC): a peer log last written before it is stale
#
# HOW IT RUNS -- REUSE, NOT A FORK. Each half is `run_case.ps1 -Case <wrapper> -Slot <n>
# -RunDir <pair dir>\<role>` in its own powershell process, started together. The wrapper is a
# one-line .ps1 in the pair dir that calls the case with -Role. So each half gets exactly what
# every other case gets: flow_run's boot, per-slot box lock, per-slot exe staging and kill sweep,
# BRN_* wipe + DiagEnv, provenance, result.json and REPORT.md. Slots isolate everything two
# instances would fight over (tools\tests\slots.ps1); the two halves never share a box lock.
#
# Everything lands under ONE directory:
#   scratch\bugtest\runs\<case>\<timestamp>\
#       <role>\...               the half's run_case run dir (flow\BrnGame.log, REPORT.md, ...)
#       <role>.case.ps1          the wrapper that half ran
#       <role>.console.log       everything that half's run_case printed
#       result.json / REPORT.md  the pair verdict
#   scratch\bugtest\runs\<case>\latest.json   -> the newest pair result
#
# Exit code: 0 = pair verdict matches expectation; 1 otherwise; 2 = the runner could not run it.
param(
  [Parameter(Mandatory=$true)][string]$Case,
  [int]$SlotA           = 1,
  [int]$SlotB           = 2,
  [string]$RunDir       = "",
  [string]$RunsRoot     = "",
  [switch]$ExpectFail,
  [switch]$NoRun,
  [int]$LockTimeoutSec  = 7200,
  [int]$WaitSeconds     = 0,      # 0 = the lock timeout + 30 minutes
  [string]$Label        = ""
)
$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$runCase = Join-Path $PSScriptRoot 'run_case.ps1'

# --- resolve + load the descriptor ------------------------------------------------------------
$casePath = $Case
if (-not (Test-Path $casePath)) { $casePath = Join-Path $PSScriptRoot ("cases\" + $Case + ".ps1") }
if (-not (Test-Path $casePath)) { Write-Host "[pair] FAIL: no case '$Case' (tried $casePath)"; exit 2 }
$casePath = (Resolve-Path $casePath).Path
$lDesc = & $casePath
if ($lDesc -isnot [hashtable] -or -not $lDesc.Pair -or -not $lDesc.Pair.Roles -or @($lDesc.Pair.Roles).Count -ne 2) {
  Write-Host "[pair] FAIL: $casePath is not a pair case (no -Role must return @{ Pair = @{ Roles = @('A','B') } })"; exit 2
}
if (-not $lDesc.Name) { $lDesc.Name = [IO.Path]::GetFileNameWithoutExtension($casePath) }
$laRoles = @($lDesc.Pair.Roles)
if ($SlotA -le 0 -or $SlotB -le 0 -or $SlotA -eq $SlotB) {
  Write-Host "[pair] FAIL: two different slots > 0 are needed (got $SlotA and $SlotB); slot 0 is never used by a pair"; exit 2
}
$laSlots = @($SlotA, $SlotB)

$lsRunsRootArg = $RunsRoot      # handed to both halves only when given (their latest.json goes there too)
if ($RunsRoot -eq "") { $RunsRoot = Join-Path $root "scratch\bugtest\runs" }
$caseRoot = Join-Path $RunsRoot $lDesc.Name
if ($NoRun) {
  if ($RunDir -eq "" -or -not (Test-Path $RunDir)) { Write-Host "[pair] FAIL: -NoRun needs an existing -RunDir"; exit 2 }
} elseif ($RunDir -eq "") {
  $RunDir = Join-Path $caseRoot (Get-Date).ToString('yyyyMMdd_HHmmss')
}
New-Item -ItemType Directory -Force $RunDir | Out-Null
$RunDir = (Resolve-Path $RunDir).Path

Write-Host ("[pair] {0}  ({1})" -f $lDesc.Name, $casePath)
if ($lDesc.Bug) { Write-Host ("[pair] bug:  {0}" -f $lDesc.Bug) }
Write-Host ("[pair] run dir: {0}" -f $RunDir)

# --- one wrapper per half ------------------------------------------------------------------------
$laHalves = @()
for ($i = 0; $i -lt 2; $i++) {
  $lsRole = "$($laRoles[$i])"
  $lsWrapper = Join-Path $RunDir ($lsRole + '.case.ps1')
  ("& '{0}' -Role '{1}'" -f ($casePath -replace "'", "''"), ($lsRole -replace "'", "''")) |
    Set-Content -Path $lsWrapper -Encoding UTF8
  $laHalves += @{ Role = $lsRole; Slot = $laSlots[$i]; Wrapper = $lsWrapper
                  Dir = (Join-Path $RunDir $lsRole); Console = (Join-Path $RunDir ($lsRole + '.console.log')) }
}

# --- run both halves at once -----------------------------------------------------------------------
function Start-Half($h, [bool]$lbNoRun) {
  $laArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$runCase`"",
              '-Case', "`"$($h.Wrapper)`"", '-RunDir', "`"$($h.Dir)`"", '-Slot', "$($h.Slot)",
              '-LockTimeoutSec', "$LockTimeoutSec")
  if ($Label -ne "") { $laArgs += @('-Label', "`"$Label`"") }
  if ($script:lsRunsRootArg -ne "") { $laArgs += @('-RunsRoot', "`"$script:lsRunsRootArg`"") }
  if ($lbNoRun) { $laArgs += '-NoRun' }
  return Start-Process powershell -ArgumentList $laArgs -PassThru -NoNewWindow `
           -RedirectStandardOutput $h.Console -RedirectStandardError ($h.Console + '.err')
}

# A slot with no Memcard_<n>\Profile.sav boots the ~64 s first-boot path (flow_run stages with
# -NoProfileSeed on purpose), so seed missing profiles here, once, like `slots.ps1 -Make` does.
# It never overwrites an existing profile and refuses a slot whose game is running.
if (-not $NoRun) {
  foreach ($h in $laHalves) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'slots.ps1') -Slot $h.Slot 2>&1 |
      Where-Object { $_ -match 'seeded|REFUSING|FAIL' } | ForEach-Object { Write-Host "[pair]   $_" }
  }
}

$t0 = Get-Date
$lsSignalDir = Join-Path $RunDir 'signals'
if (-not $NoRun) {
  if (Test-Path $lsSignalDir) { Remove-Item -Recurse -Force $lsSignalDir }
  New-Item -ItemType Directory -Force $lsSignalDir | Out-Null
}
$lProcs = @()
for ($i = 0; $i -lt 2; $i++) {
  $h = $laHalves[$i]
  $hPeer = $laHalves[1 - $i]
  if (-not $NoRun) { New-Item -ItemType Directory -Force $h.Dir | Out-Null }
  # the cross-half environment (see the banner); Start-Process copies it into this half's process
  $env:BP_PAIR_DIR       = $RunDir
  $env:BP_PAIR_ROLE      = $h.Role
  $env:BP_PAIR_PEER_ROLE = $hPeer.Role
  $env:BP_PAIR_PEER_LOG  = Join-Path $root ("build\game_slots\{0}\BrnGame.log" -f $hPeer.Slot)
  $env:BP_PAIR_T0        = "$($t0.ToFileTimeUtc())"
  $p = Start-Half $h ([bool]$NoRun)
  Write-Host ("[pair] {0} -> slot {1}, run_case pid {2}, console {3}" -f $h.Role, $h.Slot, $p.Id, $h.Console)
  $lProcs += $p
}
foreach ($lsVar in @('BP_PAIR_DIR','BP_PAIR_ROLE','BP_PAIR_PEER_ROLE','BP_PAIR_PEER_LOG','BP_PAIR_T0')) { Remove-Item "Env:\$lsVar" -ErrorAction SilentlyContinue }
$liWait = if ($WaitSeconds -gt 0) { $WaitSeconds } else { $LockTimeoutSec + 1800 }
$lbTimedOut = $false
foreach ($p in $lProcs) {
  $liLeft = [Math]::Max(1, $liWait - [int]((Get-Date) - $t0).TotalSeconds)
  if (-not $p.WaitForExit($liLeft * 1000)) { $lbTimedOut = $true }
}
if ($lbTimedOut) {
  Write-Host "[pair] a half outlived $liWait s -- stopping it (its flow_run releases its own box lock on exit)"
  foreach ($p in $lProcs) { if (-not $p.HasExited) { try { & taskkill /PID $p.Id /F /T *>$null } catch { } } }
}
Write-Host ("[pair] both halves returned after {0:f0}s" -f ((Get-Date) - $t0).TotalSeconds)

# --- the pair verdict ----------------------------------------------------------------------------------
$laRows = @()
$lbAllPass = -not $lbTimedOut
foreach ($h in $laHalves) {
  $lsResult = Join-Path $h.Dir 'result.json'
  $lRow = @{ role = $h.Role; slot = $h.Slot; verdict = 'NO RESULT'; phase = '?'; failed = @(); run_dir = $h.Dir }
  if (Test-Path $lsResult) {
    try {
      $j = Get-Content $lsResult -Raw | ConvertFrom-Json
      $lRow.verdict = "$($j.verdict)"; $lRow.phase = "$($j.phase)"
      $lRow.failed = @($j.checks | Where-Object { -not $_.pass } | ForEach-Object { "$($_.name): $($_.detail)" })
      $lRow.checks = @($j.checks)
    } catch { $lRow.verdict = 'UNREADABLE' }
  }
  if ($lRow.verdict -ne 'PASS') { $lbAllPass = $false }
  $laRows += $lRow
  Write-Host ("[pair] {0,-8} slot {1}  {2,-9} phase={3}" -f $lRow.role, $lRow.slot, $lRow.verdict, $lRow.phase)
  foreach ($f in $lRow.failed) { Write-Host ("[pair]            FAIL {0}" -f $f) }
  if ($lRow.verdict -eq 'NO RESULT') { Write-Host ("[pair]            see {0}" -f $h.Console) }
}

# --- the pair-level checks (see the banner) -------------------------------------------------------
$laPairRows = @()
if ($lDesc.Pair.Checks) {
  $lPairCtx = @{ RunDir = $RunDir; Halves = @{} }
  foreach ($h in $laHalves) {
    $lsLog = Join-Path $h.Dir 'flow\BrnGame.log'
    $lsMarks = Join-Path $h.Dir 'flow\marks.txt'
    $lRowH = @($laRows | Where-Object { $_.role -eq $h.Role })[0]
    $lPairCtx.Halves[$h.Role] = @{
      Log = $lsLog; RunDir = $h.Dir; Slot = $h.Slot; Verdict = $lRowH.verdict
      LogLines  = $(if (Test-Path $lsLog) { [IO.File]::ReadAllLines($lsLog) } else { @() })
      MarksText = $(if (Test-Path $lsMarks) { Get-Content $lsMarks -Raw } else { '' })
    }
  }
  foreach ($lChk in @($lDesc.Pair.Checks)) {
    $lsName = if ($lChk.Name) { "$($lChk.Name)" } else { 'pair check' }
    $lR = $null
    try { $lR = & $lChk.Script $lPairCtx } catch { $lR = @{ Pass = $false; Detail = "threw: $($_.Exception.Message)" } }
    if ($lR -is [array]) { $lR = @($lR | Where-Object { $_ -is [hashtable] }) | Select-Object -Last 1 }
    if ($null -eq $lR -or $lR -isnot [hashtable]) { $lR = @{ Pass = $false; Detail = 'the check returned nothing' } }
    $laPairRows += @{ name = $lsName; pass = [bool]$lR.Pass; detail = "$($lR.Detail)" }
    if (-not $lR.Pass) { $lbAllPass = $false }
    Write-Host ("[pair] PAIR     [{0}] {1} -- {2}" -f $(if ($lR.Pass) { 'PASS' } else { 'FAIL' }), $lsName, $lR.Detail)
  }
}

$verdict = if ($lbAllPass) { 'PASS' } else { 'FAIL' }
$expected = if ($ExpectFail) { 'FAIL' } else { 'PASS' }
$asExpected = ($verdict -eq $expected)
if ($ExpectFail) {
  if ($asExpected) { Write-Host "[pair] RED confirmed: '$($lDesc.Name)' FAILS on this build." }
  else             { Write-Host "[pair] *** NOT RED: '$($lDesc.Name)' PASSES on this build. ***" }
} else {
  if ($asExpected) { Write-Host "[pair] GREEN: '$($lDesc.Name)' PASSES." }
  else             { Write-Host "[pair] *** FAIL: '$($lDesc.Name)' ***" }
}

$result = @{
  case = $lDesc.Name; case_path = $casePath; bug = "$($lDesc.Bug)"; label = $Label
  when = (Get-Date).ToString('o'); run_dir = $RunDir; slots = $laSlots; timed_out = $lbTimedOut
  verdict = $verdict; expected = $expected; as_expected = $asExpected
  halves = @($laRows | ForEach-Object { @{ role = $_.role; slot = $_.slot; verdict = $_.verdict; phase = $_.phase; failed = $_.failed; run_dir = $_.run_dir } })
  pair_checks = @($laPairRows)
}
$result | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $RunDir 'result.json') -Encoding UTF8
New-Item -ItemType Directory -Force $caseRoot | Out-Null
$result | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $caseRoot 'latest.json') -Encoding UTF8

$md = @()
$md += "# $($lDesc.Name) -- $verdict" + $(if ($Label) { " ($Label)" } else { "" })
$md += ""
if ($lDesc.Bug) { $md += "Bug: $($lDesc.Bug)"; $md += "" }
$md += "Pair run: ``$RunDir``  slots $($laSlots -join ' + ')  expected=$expected  as_expected=$asExpected" + $(if ($lbTimedOut) { "  (TIMED OUT)" } else { "" })
$md += ""
$md += "| half | slot | verdict | phase | report |"
$md += "|---|---|---|---|---|"
foreach ($r in $laRows) { $md += ("| {0} | {1} | {2} | {3} | ``{4}`` |" -f $r.role, $r.slot, $(if ($r.verdict -eq 'PASS') { 'PASS' } else { "**$($r.verdict)**" }), $r.phase, (Join-Path $r.run_dir 'REPORT.md')) }
if ($laPairRows.Count -gt 0) {
  $md += ""
  $md += "## pair checks (both halves)"
  $md += ""
  $md += "| verdict | check | detail |"
  $md += "|---|---|---|"
  foreach ($c in $laPairRows) { $md += ("| {0} | {1} | {2} |" -f $(if ($c.pass) { 'PASS' } else { '**FAIL**' }), $c.name, ("$($c.detail)" -replace '\|', '\|')) }
}
foreach ($r in $laRows) {
  $md += ""
  $md += "## $($r.role)"
  $md += ""
  $md += "| verdict | check | detail |"
  $md += "|---|---|---|"
  foreach ($c in @($r.checks)) { if ($c) { $md += ("| {0} | {1} | {2} |" -f $(if ($c.pass) { 'PASS' } else { '**FAIL**' }), $c.name, ("$($c.detail)" -replace '\|', '\|')) } }
}
$md -join "`n" | Set-Content (Join-Path $RunDir 'REPORT.md') -Encoding UTF8
Write-Host "[pair] report -> $(Join-Path $RunDir 'REPORT.md')"

if ($asExpected) { exit 0 } else { exit 1 }
