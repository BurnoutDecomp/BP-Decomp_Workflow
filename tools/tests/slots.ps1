# slots.ps1 -- N GAME INSTANCES ON ONE BOX. Build / refresh / list / clean the per-slot
# launch folders the parallel harness runs out of.
#
#   powershell -ExecutionPolicy Bypass -File tools\tests\slots.ps1 -Make 3     # slots 1..3
#   powershell -ExecutionPolicy Bypass -File tools\tests\slots.ps1 -Slot 2     # just slot 2
#   powershell -ExecutionPolicy Bypass -File tools\tests\slots.ps1 -List
#   powershell -ExecutionPolicy Bypass -File tools\tests\slots.ps1 -Clean      # remove all slots
#
# WHAT A SLOT IS, AND WHAT IT DELIBERATELY IS NOT.
#   A slot is a LAUNCH FOLDER, not a copy of the game. `build\game` is 5.9 GB and its data is
#   rewritten by `build data` and by the asset porters; duplicating it -- by copy, by junction,
#   or by hard link -- would mean every slot could silently run STALE DATA the moment a porter
#   rewrote a bundle, and a measurement taken against the wrong assets is the worst kind:
#   reproducible and not attributable (the exe-provenance banner in flow_run.ps1 is the same
#   lesson, one file down).
#   So a slot holds ONLY what a running instance LOCKS or WRITES:
#       Burnout_PC.exe            a running game holds an exclusive lock on its image, so the
#                                 link would fail while any slot ran -- hence a copy
#       Burnout_PC.cgsmap         the assert/crash symbol reader opens it NEXT TO THE EXE
#                                 (CgsAssertManager.cpp:30), so it must travel with the copy
#       Burnout_PC.exe.provenance.json  copied so `[flow] exe <sha> b5=<head>` still says which
#                                 build produced the numbers -- a slot run that could not say
#                                 that is a slot run nobody can cite
#       *.dll                     the loader searches the EXE's directory first, not the CWD
#       BrnGame.log / BrnCrash.png  the game writes both next to the exe (CgsLog.cpp:15,
#                                 CgsCrashHandlerPC.cpp:148), which is exactly why a per-slot
#                                 exe directory gives a per-slot log for free
#   and everything else is read from `build\game`, live, because THAT IS THE WORKING DIRECTORY
#   flow_run launches the slot with. CgsHardwareInitPC.cpp:320 seeds macFOPENPath from
#   GetCurrentDirectory(), so the data path is the CWD and one data set serves every slot.
#
#   THE ONE THING THE CWD ALSO RESOLVES IS THE PROFILE ("Memcard\Profile.sav"), and two
#   instances writing one save is a CORRUPTED save, not a contended one. That is why the game
#   suffixes the directory with BRN_HARNESS_SLOT (b5-decomp CgsSaveLoadPC.cpp -> CgsHarnessSlot.h):
#   slot n reads and writes build\game\Memcard_<n>\. This script seeds that directory from
#   build\game\Memcard\ so a slot boots the RETURNING-PLAYER path like slot 0 does -- a slot
#   that started fresh would take the ~80 s first-boot path and its timings would not be
#   comparable with anything.
#
# SLOT 0 IS build\game ITSELF and this script never touches it. Everything a slot suffixes --
#   the single-instance mutex, the harness input channels, the assert-release event, the Memcard
#   directory, the box lock -- is empty-suffixed at slot 0, so the default path stays byte-for-byte
#   what every banked run and golden was measured through.
#
# IT REFUSES TO REFRESH A SLOT WHOSE GAME IS RUNNING. Overwriting the exe under a live
#   instance is either an access-denied (best case) or a run measuring half of one build and half
#   of another. Detection is by IMAGE PATH (Win32_Process.ExecutablePath), not by process name --
#   that is the same rule flow_run's per-slot kill sweep uses, and the only one that can tell one
#   slot's game from another's.
param(
  [int]$Make  = 0,        # build/refresh slots 1..N
  [int]$Slot  = 0,        # build/refresh JUST this slot (overrides -Make)
  [switch]$List,
  [switch]$Clean,
  [switch]$Force,         # refresh even when the slot exe is already current
  [switch]$NoProfileSeed  # ⛔⛔ DO NOT CREATE A MISSING Memcard_<n>\Profile.sav. flow_run passes
                          #   this on every run, and the reason is a MEASURED defect: run_case's
                          #   `FreshProfile = $true` parks the slot's profile so the case boots
                          #   the first-boot path, then flow_run stages the slot -- and the seed
                          #   below PUT THE PROFILE BACK, so the game booted as a RETURNING player
                          #   with every gate already collected. camera_shake_smash went RED twice
                          #   that way (runs 20260906_135159 and _135614: five
                          #   `[UI-gate] OnPropHit` and zero `[cam] smash`, because
                          #   StuntManager::ProcessStuntElement returns early on an already-
                          #   collected element and only a FIRST completion posts game action 58).
                          #   Nothing in either report said the word "profile"; the case simply
                          #   looked like a regression in the game. Seeding is a SETUP act and
                          #   belongs to an explicit `slots.ps1 -Make`, never to a run.
)
$ErrorActionPreference = 'Stop'
$root     = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$gameDir  = Join-Path $root 'build\game'
$slotsDir = Join-Path $root 'build\game_slots'

# The files a slot needs beside its own exe. Everything else is read live out of build\game.
$KAS_SLOT_FILES = @('Burnout_PC.exe', 'Burnout_PC.cgsmap', 'Burnout_PC.exe.provenance.json')

function Get-SlotDir([int]$n) {
  if ($n -le 0) { return "$gameDir" }
  return (Join-Path $slotsDir "$n")
}

# BY IMAGE PATH, NOT BY NAME. `Get-Process Burnout_PC` cannot tell slot 1's game from slot 2's,
# and a sweep that cannot tell them apart is a sweep that kills the wrong measurement.
function Get-SlotProcesses([int]$n) {
  $lsDir = (Get-SlotDir $n)
  try {
    return @(Get-CimInstance Win32_Process -Filter "Name='Burnout_PC.exe'" -ErrorAction Stop |
             Where-Object { $_.ExecutablePath -and
                            ([IO.Path]::GetDirectoryName($_.ExecutablePath).TrimEnd('\')) -ieq $lsDir.TrimEnd('\') })
  } catch { return @() }
}

function Show-Slots {
  Write-Host "[slots] slot 0 = $gameDir (the default path; never a copy)"
  if (-not (Test-Path $slotsDir)) { Write-Host "[slots] no slot folders yet ($slotsDir)"; return }
  foreach ($d in (Get-ChildItem $slotsDir -Directory -ErrorAction SilentlyContinue | Sort-Object Name)) {
    $n = 0
    if (-not [int]::TryParse($d.Name, [ref]$n)) { continue }
    $lExe = Join-Path $d.FullName 'Burnout_PC.exe'
    $lSrc = Join-Path $gameDir 'Burnout_PC.exe'
    $lsState = 'MISSING EXE'
    if (Test-Path $lExe) {
      $lsState = if ((Get-Item $lExe).LastWriteTime -ge (Get-Item $lSrc).LastWriteTime) { 'current' } else { 'STALE' }
    }
    $lRunning = @(Get-SlotProcesses $n).Count
    $lMem = Join-Path $gameDir ("Memcard_" + $d.Name)
    Write-Host ("[slots] slot {0}  {1,-11} running={2}  {3}  profile={4}" -f `
                $d.Name, $lsState, $lRunning, $d.FullName,
                $(if (Test-Path (Join-Path $lMem 'Profile.sav')) { 'yes' } else { 'NONE (first boot takes the fresh path)' }))
  }
}

function Make-Slot([int]$n) {
  if ($n -le 0) { Write-Host "[slots] slot 0 is build\game itself -- nothing to make."; return $true }
  $lSrcExe = Join-Path $gameDir 'Burnout_PC.exe'
  if (-not (Test-Path $lSrcExe)) { Write-Host "[slots] FAIL: no exe at $lSrcExe -- build first."; return $false }

  $lDir = Get-SlotDir $n
  $lLive = @(Get-SlotProcesses $n)
  if ($lLive.Count -gt 0) {
    Write-Host "[slots] REFUSING to refresh slot $n -- $($lLive.Count) game process(es) are running out of $lDir."
    Write-Host "[slots]   Overwriting a live exe measures half of one build and half of another."
    return $false
  }
  New-Item -ItemType Directory -Force $lDir | Out-Null

  # THE STAGING LOCK. build_exe_locked.ps1 holds this for the whole link, so a slot can never
  #   copy a HALF-LINKED exe. It is a second, narrower mutex on purpose: the box lock serialises
  #   RUNS (one per slot now), this one serialises "the bytes of build\game\Burnout_PC.exe are
  #   being rewritten". Acquisition order is box-then-stage in both scripts, so there is no cycle.
  $lStage = New-Object System.Threading.Mutex($false, "Local\BurnoutPC_ExeStage")
  $lGot = $false
  try { $lGot = $lStage.WaitOne([TimeSpan]::FromSeconds(3600)) }
  catch [System.Threading.AbandonedMutexException] { $lGot = $true }
  if (-not $lGot) { Write-Host "[slots] FAIL: the exe staging lock stayed busy for an hour."; return $false }

  $lCopied = 0
  try {
    foreach ($f in $KAS_SLOT_FILES) {
      $lSrc = Join-Path $gameDir $f
      if (-not (Test-Path $lSrc)) { continue }
      $lDst = Join-Path $lDir $f
      if ($Force -or -not (Test-Path $lDst) -or
          (Get-Item $lSrc).LastWriteTime -gt (Get-Item $lDst).LastWriteTime) {
        Copy-Item $lSrc $lDst -Force
        $lCopied++
      }
    }
    # The DLLs the loader resolves out of the EXE's own directory.
    foreach ($f in (Get-ChildItem $gameDir -Filter *.dll -File)) {
      $lDst = Join-Path $lDir $f.Name
      if (-not (Test-Path $lDst) -or $f.LastWriteTime -gt (Get-Item $lDst).LastWriteTime) {
        Copy-Item $f.FullName $lDst -Force
        $lCopied++
      }
    }
  } finally { $lStage.ReleaseMutex(); $lStage.Close() }

  # The slot's PRIVATE profile directory, seeded from slot 0's so it boots the returning-player
  # path (see the banner). It lives under build\game because that is the working directory the
  # game resolves "Memcard_<n>" against.
  $lMemDst = Join-Path $gameDir ("Memcard_" + $n)
  New-Item -ItemType Directory -Force $lMemDst | Out-Null
  $lProfSrc = Join-Path $gameDir 'Memcard\Profile.sav'
  $lProfDst = Join-Path $lMemDst 'Profile.sav'
  if ($NoProfileSeed) {
    # See the -NoProfileSeed banner: an ABSENT profile here is a deliberate FreshProfile park,
    # and re-creating it silently turns a first-boot case into a returning-player one.
  } elseif ((Test-Path $lProfSrc) -and ($Force -or -not (Test-Path $lProfDst))) {
    Copy-Item $lProfSrc $lProfDst -Force
    Write-Host "[slots] slot $n profile seeded from build\game\Memcard\Profile.sav"
  }

  Write-Host ("[slots] slot {0} ready: {1} ({2} file(s) refreshed)" -f $n, $lDir, $lCopied)
  return $true
}

if ($Clean) {
  if (Test-Path $slotsDir) {
    foreach ($d in (Get-ChildItem $slotsDir -Directory)) {
      $n = 0
      if ([int]::TryParse($d.Name, [ref]$n) -and (Get-SlotProcesses $n).Count -gt 0) {
        Write-Host "[slots] REFUSING to clean slot $n -- its game is running."
        exit 1
      }
    }
    Remove-Item -Recurse -Force $slotsDir
    Write-Host "[slots] removed $slotsDir (the Memcard_<n> directories are LEFT ALONE -- they are save data)"
  }
  exit 0
}
if ($List) { Show-Slots; exit 0 }

$lTargets = @()
if ($Slot -gt 0)     { $lTargets = @($Slot) }
elseif ($Make -gt 0) { $lTargets = @(1..$Make) }
else                 { Show-Slots; exit 0 }

$lBad = 0
foreach ($n in $lTargets) { if (-not (Make-Slot $n)) { $lBad++ } }
Show-Slots
exit $(if ($lBad -gt 0) { 1 } else { 0 })
