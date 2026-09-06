# run_all.ps1 -- run every case under tools\tests\cases\ (or a -Filter subset) and print a
# one-line-per-case table. Each case's own run dir + REPORT.md is where the detail is. Exit 1 if
# any case did not end as expected.
#
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_all.ps1 [-Filter 'traffic_*'] [-Label post-fix]
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_all.ps1 -Parallel 3
#
# ⭐⭐ -Parallel k -- k GAMES AT ONCE, ONE PER SLOT (2026-09-06, lane harness2).
#   Sequentially, sixteen cases at 60-130 s each is half an hour of box time and every other lane
#   waits behind all of it. With -Parallel k the cases are dealt round-robin onto slots 1..k, each
#   of which is a separate game instance out of build\game_slots\<n>\ with its own log, its own
#   harness input channels, its own box lock and its own Memcard_<n> profile (tools\tests\slots.ps1
#   and the -Slot banner in run_case.ps1 say how, and why nothing leaks between them).
#   ⛔ SLOT 0 IS NEVER USED BY -Parallel. It is build\game itself -- the default path every banked
#   run and golden was measured through, and the one a lone `run_case.ps1 -Case x` still takes --
#   so a parallel sweep can never disturb a solo measurement someone else is taking.
#   ⚠️ WHAT PARALLELISM COSTS, STATED UP FRONT: the slots share one GPU and one CPU, so each one
#   runs at a lower frame rate than it would alone. Every check in tools\tests\cases today is a log
#   line or a pixel, and neither moves with contention -- but a case whose check is ever a frame
#   rate, a wall-clock duration, or anything counted PER FRAME must be scored on a slot of its own.
#   Each run's own marks.txt carries its POLL line and its frame count, so the cost is measurable
#   after the fact rather than assumed.
#   ⚠️ A parallel sweep is NOT the place to discover that a build is broken: run
#   `run_case.ps1 -Case baseline_boot_drive` first. Sixteen simultaneous failures all blaming the
#   same missing exe is a slow way to learn one fact.
param(
  [string]$Filter = '*',
  [string]$Label = '',
  [int]$Parallel = 0,             # 0 = sequential on slot 0 (the historical behaviour, unchanged)
  [switch]$ExpectFail
)
$ErrorActionPreference = 'Continue'
$root  = Resolve-Path (Join-Path $PSScriptRoot "..\..")
# ⚠️ -like ON THE BASE NAME, not Get-ChildItem -Filter. The provider filter understands only `*`
# and `?`, so `-Filter '[bi]*'` matched NOTHING and said "no cases match" -- which reads exactly
# like a typo in the pattern. `-like` is a superset: every pattern that worked before still does,
# and character classes now work too, which is what lets a sweep be split into batches that each
# fit inside one foreground command.
$cases = Get-ChildItem (Join-Path $PSScriptRoot 'cases') -Filter '*.ps1' |
         Where-Object { $_.BaseName -like $Filter } | Sort-Object Name
if ($cases.Count -eq 0) { Write-Host "[all] no cases match '$Filter'"; exit 2 }

$runCase   = (Join-Path $PSScriptRoot 'run_case.ps1')
$slotsPs1  = (Join-Path $PSScriptRoot 'slots.ps1')
$latestFor = { param($name) Join-Path $root ("scratch\bugtest\runs\{0}\latest.json" -f $name) }

function Read-Latest([string]$name) {
  $l = & $latestFor $name
  $o = @{ verdict = '?'; phase = '?'; asserts = '?'; slot = '?' }
  if (Test-Path $l) {
    try {
      $j = Get-Content $l -Raw | ConvertFrom-Json
      $o.verdict = $j.verdict; $o.phase = $j.phase; $o.asserts = $j.asserts
      $o.slot = $(if ($null -ne $j.slot) { $j.slot } else { 0 })
    } catch { }
  }
  return $o
}

$rows = @()
$bad  = 0

if ($Parallel -le 0) {
  foreach ($c in $cases) {
    $name = $c.BaseName
    Write-Host ""
    Write-Host ("[all] ================ {0} ================" -f $name)
    & $runCase -Case $c.FullName -Label $Label -ExpectFail:$ExpectFail
    $rc = $LASTEXITCODE
    $j  = Read-Latest $name
    if ($rc -ne 0) { $bad++ }
    $rows += ("{0,-40} {1,-5} phase={2,-9} asserts={3,-5} slot={4,-2} rc={5}" -f $name, $j.verdict, $j.phase, $j.asserts, $j.slot, $rc)
  }
} else {
  # Stage the slots FIRST, in the foreground. A slot that could not be built is a case that would
  # otherwise fail for a reason that has nothing to do with the game.
  Write-Host ("[all] staging {0} slot(s) ..." -f $Parallel)
  & powershell -ExecutionPolicy Bypass -File $slotsPs1 -Make $Parallel
  if ($LASTEXITCODE -ne 0) { Write-Host "[all] FAIL: could not stage the slots -- see the [slots] lines above."; exit 2 }

  # ⭐ SOLO CASES ARE HELD BACK (2026-09-06, lane quiet). A case may declare `Solo = $true`, which
  #   means its measurement is not valid with other games on the box. It then runs AFTER the
  #   parallel batch, sequentially, on SLOT 0 -- the same path a plain `run_case.ps1` takes.
  #   ⛔ THE ONE THAT NEEDS IT, and why, so this is not an escape hatch for a flaky case:
  #   quiet_focus_input's stimulus is a process that must take the DESKTOP's foreground away from
  #   the game and hold real keys down. Under -Parallel that process is started from inside a
  #   Start-Job runspace, and measured on 2026-09-06 the two ends disagreed about what the
  #   foreground even was -- the injector logged 118/118 samples with no Burnout window in front
  #   while the game under test logged `focus=1` throughout and never saw a change. Neither the
  #   stimulus nor the gate can be trusted in that configuration, so the case is scored alone.
  #   A case whose checks are merely SLOWER in parallel does not qualify; a frame-rate or
  #   wall-clock check does (see the contention note in this file's banner).
  $soloCases = @()
  $parCases  = @()
  foreach ($c in $cases) {
    $isSolo = $false
    try { $h = & $c.FullName; if ($h -is [hashtable] -and $h.Solo) { $isSolo = $true } } catch { }
    if ($isSolo) { $soloCases += $c } else { $parCases += $c }
  }
  if ($soloCases.Count -gt 0) {
    Write-Host ("[all] {0} case(s) marked Solo -- held back and run alone on slot 0 after the batch: {1}" -f `
                $soloCases.Count, (($soloCases | ForEach-Object { $_.BaseName }) -join ', '))
  }
  $cases = $parCases

  # Deal the cases round-robin onto slots 1..k. Each job is one run_case.ps1 in its own runspace;
  # the slot's box lock serialises anything else that ever targets that slot, so two jobs can
  # never land on one instance.
  $jobs = @()
  $i = 0
  foreach ($c in $cases) {
    $slot = ($i % $Parallel) + 1
    $i++
    Write-Host ("[all] queue {0,-40} -> slot {1}" -f $c.BaseName, $slot)
    # ⚠️ THE SWITCH IS PASSED AS AN [int], not a [bool]. Start-Job hands -ArgumentList through the
    # remoting serialiser, and a $false arriving in an untyped param binds to -ExpectFail: as a
    # STRING -- "cannot convert System.String to SwitchParameter", which killed both jobs of the
    # first parallel sweep AFTER the games had already run. Typing the param and rebuilding the
    # switch inside the job is the fix; the failure mode is worth naming because the summary table
    # still showed each case's PREVIOUS latest.json verdict beside rc=2, i.e. it read like a
    # runner error on a passing case rather than a run that never happened.
    $jobs += (Start-Job -Name $c.BaseName -ScriptBlock {
      param([string]$lsRunCase, [string]$lsCase, [int]$liSlot, [string]$lsLabel, [int]$liExpectFail)
      $lArgs = @{ Case = $lsCase; Slot = $liSlot; Label = $lsLabel }
      if ($liExpectFail -ne 0) { $lArgs['ExpectFail'] = $true }
      & $lsRunCase @lArgs *>&1 | ForEach-Object { "$_" }
      "___RC___=$LASTEXITCODE"
    } -ArgumentList $runCase, $c.FullName, $slot, $Label, $(if ($ExpectFail) { 1 } else { 0 }))
  }

  Write-Host ("[all] {0} case(s) running on {1} slot(s). Waiting ..." -f $cases.Count, $Parallel)
  $null = Wait-Job -Job $jobs
  foreach ($j in $jobs) {
    $out = @(Receive-Job -Job $j)
    $rc  = 2
    foreach ($l in $out) { if ("$l" -match '^___RC___=(\d+)$') { $rc = [int]$Matches[1] } }
    $consoleFile = Join-Path $root ("scratch\bugtest\runs\{0}\_run_all_job.log" -f $j.Name)
    New-Item -ItemType Directory -Force (Split-Path $consoleFile) | Out-Null
    $out | Set-Content $consoleFile -Encoding UTF8
    $r = Read-Latest $j.Name
    if ($rc -ne 0) { $bad++ }
    $rows += ("{0,-40} {1,-5} phase={2,-9} asserts={3,-5} slot={4,-2} rc={5}" -f $j.Name, $r.verdict, $r.phase, $r.asserts, $r.slot, $rc)
    Remove-Job -Job $j -Force
  }
  Write-Host "[all] each job's console output -> scratch\bugtest\runs\<case>\_run_all_job.log"

  # The held-back Solo cases, one at a time, on slot 0 -- after every parallel job has finished,
  # so the box really is theirs.
  foreach ($c in $soloCases) {
    $name = $c.BaseName
    Write-Host ""
    Write-Host ("[all] ============ {0} (Solo -- alone on slot 0) ============" -f $name)
    & $runCase -Case $c.FullName -Label $Label -ExpectFail:$ExpectFail
    $rc = $LASTEXITCODE
    $j  = Read-Latest $name
    if ($rc -ne 0) { $bad++ }
    $rows += ("{0,-40} {1,-5} phase={2,-9} asserts={3,-5} slot={4,-2} rc={5}" -f $name, $j.verdict, $j.phase, $j.asserts, $j.slot, $rc)
  }
  $cases = $parCases + $soloCases
}

Write-Host ""
Write-Host "[all] ---- summary ----"
$rows | Sort-Object | ForEach-Object { Write-Host "  $_" }
Write-Host ("[all] {0} case(s), {1} not as expected" -f $cases.Count, $bad)
exit $(if ($bad -gt 0) { 1 } else { 0 })
