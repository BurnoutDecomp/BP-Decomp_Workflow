# roll_batch.ps1 -- ONE CRASH PER BOOT, over the FOUR crash types a barrel roll can come from.
#
# ⭐⭐ WHY THIS EXISTS. Every "does the car barrel roll?" number this campaign has published was
#   taken on ONE kind of crash: a head-on wall hit from a standing placement, no player input
#   afterwards. That is the LEAST likely crash to roll a car, and it is the only kind that has
#   ever been sampled. crash_sweep_batch.ps1 fires that recipe and nothing else. This fires four:
#
#     wall      the banked recipe, re-run so the control is on the SAME EXE as everything else.
#               ⛔ It is re-run rather than re-used: the banked corpus was taken on exe
#                  91c526eb2374 and a frequency compared across two binaries is not a comparison.
#     jump      the -Jump ramp, ONE shot per boot (the -Jump preset fires ten, which is right for
#               an air-time ladder and wrong here -- see THE PRISTINE-CAR RULE below).
#     showtime  the both-bumpers gesture through the console's own gate stack, plus the boost
#               PULSE that drives the bounce. ⭐ The console's super-elastic 1.1 ground restitution
#               (GetVehicleWorldRestitution @0x825E0C78, `|n.y| >= 0.5 ? 1.1 : 0.0`) is
#               SHOWTIME-GATED, so it has never fired in any measurement this campaign has taken.
#     carcar   a long run-up along the sweep road so the car meets TRAFFIC before the wall. The
#               tangential mode scale is 20.0 car-car against 5.0 vs world -- four times larger.
#               ⚠️ Traffic is stochastic, so this recipe does not GUARANTEE a car-to-car crash; it
#               makes one likely and the [tanbank] witness says afterwards whether it happened
#               (owner 1 with impRow 20.0). Classify, do not assume.
#
# ⭐ THE PRISTINE-CAR RULE, and why every kind here is one shot per boot.
#   PlaceCarOnTrack's reset carries mbResetDeformation = IsWrecked() for a non-crashing car
#   (RaceCarEntityModule::ResetActiveRaceCar @0x822F4880), so a re-placed car that recovered
#   rather than wrecked KEEPS the previous shot's dents. Measured on run sw_probe: two shots with
#   byte-identical approach and entry speeds scored rollDeg 21.6 (pristine) and 179.7 (dented).
#   A dented car rolls MORE -- so folding later shots in would bias a roll frequency UPWARD, which
#   is exactly the direction that would make this measurement flatter itself. One shot, one boot.
#
# ⛔ NOTHING HERE TUNES ANYTHING. Every knob is a placement or an input; no physics constant is
#   touched. The question is a FREQUENCY, and the answer is allowed to be "wall hits rarely roll".
#
# Usage:
#   roll_batch.ps1 -Kind jump     -Tag rj -Headings 0        -Speeds 26,32,38,44,50,56,62
#   roll_batch.ps1 -Kind wall     -Tag rw -Headings 220,230,240 -Speeds 40,55,70
#   roll_batch.ps1 -Kind showtime -Tag rs -Ats 12,18,24,30,36,42
#   roll_batch.ps1 -Kind carcar   -Tag rc -Headings 230      -Speeds 55,65 -Distance 300
#
# Score with:  python tools/diagnostics/roll_frequency.py "scratch/flow_run/<tag>_*/BrnGame.log"
param(
  [ValidateSet('wall','jump','showtime','carcar')]
  [string]$Kind       = 'jump',
  [string]$Tag        = "rb",
  # ⛔⛔ STRINGS, NOT [double[]] -- AND THE REASON IS A MEASURED SILENT CORRUPTION. Called through
  #   `powershell -File`, a [double[]] parameter receives "12,20" as ONE string and PowerShell's
  #   own comma-decimal parse turns it into the single number 1220. The first draft of this script
  #   did exactly that and printed `Showtime=1220:90` -- a run that would have waited 20 minutes
  #   for a gesture and reported nothing, with no error anywhere. Parsed here with InvariantCulture
  #   so the same string means the same thing from every shell and every locale.
  [string]$Headings   = "0",
  [string]$Speeds     = "44",
  [string]$Ats        = "12",           # showtime only: seconds after the DRIVING mark
  [int]$Repeats       = 1,
  [double]$Distance   = 0,              # 0 = the kind's own default
  [int]$MaxSeconds    = 0,              # 0 = the kind's own default
  [int]$Settle        = 0,              # 0 = the kind's own default (sim frames between shots)
  [switch]$Frames,                      # ⛔ ONE boot only -- a dump can reach 16 GB
  [int]$FrameEvery    = 2,
  [string]$FrameDir   = "",
  [string]$RestoreExeFrom = "",         # ⚠️⚠️ TWO LANES SHARE ONE CHECKOUT AND ONE build\game.
                                        #   A FAILED LINK DELETES THE EXE -- measured twice on
                                        #   2026-09-06, once by each lane -- and the victim's next
                                        #   boot dies with "[flow] FAIL: no exe", which reads like a
                                        #   build regression and is not one. Point this at a KNOWN
                                        #   copy and the loop restores it between boots and SAYS SO,
                                        #   so a campaign is not silently cut in half. ⛔ It restores
                                        #   only when the exe is ABSENT: it never overwrites whatever
                                        #   the other lane has just linked, and the run's own
                                        #   `[flow] exe <sha>` line still attributes every boot.
  [switch]$WhatIf                       # print the plan and stop
)
$ErrorActionPreference = 'Stop'
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
# ⛔ A LOCALE BUG CORRUPTS DRIVE SCRIPTS. This box formats doubles with a COMMA decimal separator,
#   and every one of flow_run's list parameters is comma-separated -- so "44,0:26,0" is four
#   fields, not two, and the run is placed somewhere nobody asked for. InvariantCulture, always.
$inv = [Globalization.CultureInfo]::InvariantCulture
$f = { param($v) ([double]$v).ToString('0.###', $inv) }
function Parse-List {
  param([string]$Text, [string]$What)
  $out = @()
  foreach ($t in ($Text -split '[,;]')) {
    $t = $t.Trim()
    if ($t -eq "") { continue }
    $n = 0.0
    if (-not [double]::TryParse($t, [Globalization.NumberStyles]::Float, $inv, [ref]$n)) {
      Write-Host "[roll] FAIL: -$What '$Text' -- '$t' is not a number (use '.' for the decimal point)."
      exit 1
    }
    $out += $n
  }
  if ($out.Count -eq 0) { Write-Host "[roll] FAIL: -$What is empty."; exit 1 }
  return $out
}
$aHeadings = Parse-List $Headings 'Headings'
$aSpeeds   = Parse-List $Speeds   'Speeds'
$aAts      = Parse-List $Ats      'Ats'

# ---- the wall recipe's own geometry, verbatim from crash_sweep_batch.ps1 so the control on this
#      exe is the SAME EXPERIMENT as the banked corpus, not a near-miss.
$KWallTarget = @(3170.6, -3.7, -2004.6)
$KWallDist   = 42.0
# ---- the jump ramp, verbatim from flow_run.ps1's -Jump preset (read off vfxprod_C's [boostloc]).
$KJumpLaunch = @(3027.0, -9.2, -330.0)
$KJumpSettle = 420

$plan = @()
foreach ($r in 1..$Repeats) {
  if ($Kind -eq 'showtime') {
    foreach ($at in $aAts) {
      # ⭐ AFTERTOUCH IS NOT A SEPARATE RECIPE -- IT IS THIS ONE. RaceCarPhysics::Update latches
      #   mbUsingAftertouch = mbAftertouchIsForceAdditive && controls->GetAftertouchEnable() > 0
      #                       && IsPlayerVehicleActuallyInShowtime()
      #   and CrashPlayManager::GetAftertouchLevel() returns 1.0 inside showtime once
      #   mfAftertouchPower is up. So aftertouch can ONLY be live during showtime, and a "scripted
      #   aftertouch run" is a showtime run with the steering channel actually being moved. The
      #   alternating hold below is that: 3 s left, 3 s right, for the length of the session.
      $lSteer = @("0:none")
      for ($t = $at + 3.0; $t -lt $at + 84.0; $t += 6.0) {
        $lSteer += ("{0}:left"  -f (& $f $t))
        $lSteer += ("{0}:right" -f (& $f ($t + 3.0)))
      }
      $plan += [pscustomobject]@{
        Name = ("{0}_at{1:00}_r{2}" -f $Tag, [int]$at, $r)
        Args = @{ Showtime = ("{0}:90" -f (& $f $at)); ShowtimeIgnoreProgression = $true
                  Boost = ("{0}:1.0:0.4" -f (& $f ($at + 2.0)))
                  SteerScript = ($lSteer -join ',') }
      }
    }
    continue
  }
  foreach ($h in $aHeadings) {
    foreach ($s in $aSpeeds) {
      $name = "{0}_h{1:000}_s{2:00}_r{3}" -f $Tag, [int](($h + 360) % 360), [int]$s, $r
      if ($Kind -eq 'jump') {
        # The heading is applied AT the ramp approach point: 0 runs straight up the ramp, a few
        # degrees off makes the take-off ASYMMETRIC, which is the geometry that turns a jump into a
        # roll rather than a nose-over. Keep it small -- the ramp is ~90 m ahead and 8 deg is 12 m
        # of lateral drift, which can leave the road (the seat line in the log says if it did).
        $plan += [pscustomobject]@{
          Name = $name
          Args = @{ CrashSweep = (($KJumpLaunch | ForEach-Object { & $f $_ }) -join ',')
                    CrashSweepShots = ("{0}:{1}" -f (& $f $h), (& $f $s))
                    CrashSweepSettle = $(if ($Settle -gt 0) { $Settle } else { $KJumpSettle })
                    CrashSweepArm = 4 }
        }
      }
      else {
        # wall + carcar share the sweep geometry and differ ONLY in the run-up distance: 42 m is a
        # placement that is already at the wall, 300 m is a placement that has to drive there --
        # through whatever traffic the road is carrying.
        $d = if ($Distance -gt 0) { $Distance } elseif ($Kind -eq 'carcar') { 300.0 } else { $KWallDist }
        $rad = $h * [Math]::PI / 180.0
        $lx = $KWallTarget[0] - $d * [Math]::Sin($rad)
        $lz = $KWallTarget[2] - $d * [Math]::Cos($rad)
        $plan += [pscustomobject]@{
          Name = $name
          Args = @{ CrashSweep = ("{0},{1},{2}" -f (& $f $lx), (& $f $KWallTarget[1]), (& $f $lz))
                    CrashSweepShots = ("{0}:{1}" -f (& $f $h), (& $f $s))
                    CrashSweepArm = 4 }
        }
        if ($Settle -gt 0) { $plan[-1].Args['CrashSweepSettle'] = $Settle }
      }
    }
  }
}

$defSecs = @{ wall = 75; jump = 85; showtime = 190; carcar = 130 }
$secs = if ($MaxSeconds -gt 0) { $MaxSeconds } else { $defSecs[$Kind] }
Write-Host ("[roll] kind={0} boots={1} tag='{2}' maxSeconds={3}" -f $Kind, $plan.Count, $Tag, $secs)
foreach ($p in $plan) { Write-Host ("[roll]   {0}  {1}" -f $p.Name, (($p.Args.GetEnumerator() | Sort-Object Name | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join ' ')) }
if ($WhatIf) { Write-Host "[roll] -WhatIf: nothing run."; exit 0 }
if ($Frames -and $plan.Count -gt 1) {
  Write-Host "[roll] FAIL: -Frames with $($plan.Count) boots. A dump can reach 16 GB; film ONE shot."
  exit 1
}

$script:BootsLost = @()
$i = 0
foreach ($p in $plan) {
  $i++
  $out = Join-Path $root ("scratch\flow_run\" + $p.Name)
  $exe = Join-Path $root 'build\game\Burnout_PC.exe'
  if ($RestoreExeFrom -ne "" -and -not (Test-Path $exe)) {
    if (Test-Path $RestoreExeFrom) {
      Copy-Item $RestoreExeFrom $exe -Force
      $h = (Get-FileHash $exe -Algorithm SHA256).Hash.Substring(0, 12)
      Write-Host ("[roll] ⚠ build\game\Burnout_PC.exe WAS MISSING (another lane's link failed) --")
      Write-Host ("[roll]   restored {0} from {1}. Every boot still prints its own exe hash." -f $h, $RestoreExeFrom)
    }
    else { Write-Host "[roll] ⚠ exe missing and -RestoreExeFrom '$RestoreExeFrom' does not exist." }
  }
  Write-Host ("[roll] {0}/{1}  {2}" -f $i, $plan.Count, $p.Name)
  $flowArgs = @{
    OutDir     = $out
    Drive      = $true
    MaxSeconds = $secs
    # ⭐ BOTH probes, always. [crash-response] is the pose stream every banked figure is built on;
    #   BRN_ROLL_PROBE is the CONSOLE'S OWN barrel-roll accumulator plus the [restit] census of the
    #   showtime-gated 1.1. Running one without the other makes the run non-comparable with the rest
    #   of the corpus for no saving at all.
    DiagEnv    = 'BRN_CRASH_RESPONSE_DIAG=1 BRN_ROLL_PROBE=1'
  }
  foreach ($k in $p.Args.Keys) { $flowArgs[$k] = $p.Args[$k] }
  if ($Frames) {
    $flowArgs['Frames'] = $true
    $flowArgs['FrameEvery'] = $FrameEvery
    if ($FrameDir -ne "") { $flowArgs['FrameDir'] = $FrameDir }
  }
  # ⛔ A HASHTABLE, NOT AN ARRAY -- PowerShell splats an array POSITIONALLY and the whole parameter
  #   list shifts (see crash_sweep_batch.ps1's banner for the failure this caused).
  $flowLog = Join-Path $root ("scratch\flow_run\" + $p.Name + "_flow.log")
  # ⛔⛔ ONE BOOT MUST NOT KILL THE BATCH. $ErrorActionPreference is 'Stop' and flow_run.ps1's own
  #   `trap` ends with `break`, so a terminating error inside ONE boot propagated out and ended the
  #   whole campaign -- measured 2026-09-06: a 16-boot wall sweep stopped after 3 because a
  #   concurrent edit to flow_run.ps1 made one launch throw, and the batch reported nothing at all
  #   about the 13 boots it never ran. A campaign that silently loses most of its n is worse than
  #   one that fails: the surviving rows still look like a corpus. Continue, and SAY which boot died.
  $failed = $false
  try { & (Join-Path $PSScriptRoot 'flow_run.ps1') @flowArgs *> $flowLog }
  catch { $failed = $true; Write-Host ("[roll]   ERROR in boot {0}: {1}" -f $p.Name, $_.Exception.Message) }
  if (-not (Test-Path (Join-Path $out 'BrnGame.log'))) {
    $script:BootsLost += $p.Name
    Write-Host ("[roll]   WARN: no BrnGame.log for {0} -- read {1}" -f $p.Name, $flowLog)
  }
}
if ($script:BootsLost.Count -gt 0) {
  Write-Host ("[roll] ⚠ {0} of {1} boots produced NO LOG: {2}" -f $script:BootsLost.Count, $plan.Count, ($script:BootsLost -join ', '))
  Write-Host "[roll]   The frequency below is over the boots that RAN. Re-run the lost ones before quoting an n."
}
Write-Host "[roll] done. Score with:"
Write-Host ("  python tools/diagnostics/roll_frequency.py `"scratch/flow_run/{0}_*/BrnGame.log`"" -f $Tag)
