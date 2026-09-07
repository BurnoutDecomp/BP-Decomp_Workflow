# crash_sweep_batch.ps1 -- ONE CRASH PER BOOT, over a grid of impact angles and speeds.
#
# ⭐⭐ WHY ONE PER BOOT, AND WHY THAT IS NOT AN EFFICIENCY CHOICE.
#   BRN_CRASH_SWEEP can fire up to 48 shots in a single boot, and the first version of this
#   measurement did exactly that.  It is WRONG, and the log says so: PlaceCarOnTrack's reset
#   carries mbResetDeformation = IsWrecked() for a non-crashing car (RaceCarEntityModule::
#   ResetActiveRaceCar @0x822F4880, the console's own rule), so a re-placed car keeps every dent
#   the previous shot gave it.  Measured on run sw_probe, two shots with BYTE-IDENTICAL approach
#   (98.4 mph) and entry (123.7 mph) speeds:
#         shot 0, pristine car   rollDeg  21.6   171 impulse arrivals
#         shot 1, same car dented rollDeg 179.7  1329 impulse arrivals
#   and on run sw_fan shots 4/5/6 crashed with ZERO arrivals at all -- a car whose deformation
#   model had been deactivated is not running the experiment any more.  Shot k>0 is therefore a
#   different experiment from shot 0, and a frequency computed over all of them is meaningless.
#   So: one boot, one shot, a pristine car every time.  ~75 s a boot.
#
# ⭐ THE GRID AIMS EVERY SHOT AT THE SAME WALL.  Fanning the heading from a fixed launch point
#   changes WHICH object the car meets (measured: from one launch, heading 234 hit at
#   (3172.6,-2003.2), 250 hit something else 19 m away, 220 drove 112 m into open road).  So the
#   launch is computed per shot as  target - D * (sin h, 0, cos h),  which varies only the angle
#   of incidence.  ⚠️ The launch must land ON ROAD: place-on-track's drop query returns no
#   candidate off it and the car is seated at the requested Y instead (visible in the log as a
#   seat whose 'at' vector has y exactly 0.000000).  Such a shot is not a valid sample.
#
# Usage:
#   crash_sweep_batch.ps1 -Tag base -Headings 210,220,230,240 -Speeds 30,40,50,60
#   crash_sweep_batch.ps1 -Tag rep  -Headings 230 -Speeds 45 -Repeats 3   # determinism check
#
# Reports:  python tools/diagnostics/crash_sweep_report.py scratch/flow_run/<tag>_*/BrnGame.log
# ⛔⛔⛔ THE DEFAULT 42 m LAUNCH TAKES EVERY SHOT ON AN INVINCIBLE CAR (measured 2026-09-07).
#   Each shot is a RequestPlaceOnTrack, and PlaceCarOnTrack's ResetDeformation type-1 arm sets
#   mfNoDamageTimer = 1.5 s and meAbsorptionSet = E_ABSORPTIONSET_INVINCIBLE (@0x82639D60). The
#   timer only burns while the deformable object is UNFROZEN, and it un-freezes at place-on-track
#   -- so the window starts when the shot fires. 42 m at 50 m/s is 0.84 s of travel: the car meets
#   the wall with 0.65 s of invincibility left, and in set 4 the whole AbsorptionTable row is 0.0,
#   so lfAbsorbed == 0 and the car CANNOT DENT BY ARITHMETIC. Measured on the two boots ef38a2e8
#   published: A1's first contact frame reads noDamageTimer 0.650001 (== 1.5 - 51/60 exactly),
#   A2's 0.883317 (== 1.5 - 37/60). Both impacts produced ZERO [dent] rows, which reads exactly
#   like "the car barely deformed".
#   ⇒ -MinDamageableSeconds 1.6 raises the launch distance per shot to speed * 1.6, so the window
#     has closed before contact. It is NOT the default: changing the geometry silently would make
#     new runs incomparable with the whole banked corpus, and a longer run-up can put the launch
#     OFF ROAD (the [sweep] SEAT BAD check catches that at run time -- read it). The line this
#     script always prints tells you the travel time either way, and warns when it is short.
param(
  [string]$Tag        = "cs",
  [double[]]$Headings = @(210, 220, 230, 240),
  [double[]]$Speeds   = @(30, 40, 50, 60),
  [int]$Repeats       = 1,
  [double]$TargetX    = 3170.6,
  [double]$TargetY    = -3.7,
  [double]$TargetZ    = -2004.6,
  [double]$Distance   = 42.0,
  [double]$MinDamageableSeconds = 0.0,  # >0 raises Distance per shot to speed * this (1.6 clears 1.5 s)
  [int]$MaxSeconds    = 75,
  [switch]$Frames                       # dump frames (only ever for ONE shot -- see MinFreeGB)
)
$ErrorActionPreference = 'Stop'
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$inv  = [Globalization.CultureInfo]::InvariantCulture

$KF_CONSOLE_NO_DAMAGE_SECONDS = 1.5   # ResetDeformation @0x82639D60, flt_820945DC == 3FC00000

$runs = @()
foreach ($r in 1..$Repeats) {
  foreach ($h in $Headings) {
    foreach ($s in $Speeds) {
      # ⭐ the per-shot launch distance. Never SHORTENED by the switch, only raised.
      $d = $Distance
      if ($MinDamageableSeconds -gt 0.0 -and $s -gt 0.0) {
        $need = $s * $MinDamageableSeconds
        if ($need -gt $d) { $d = $need }
      }
      $travel = if ($s -gt 0.0) { $d / $s } else { [double]::PositiveInfinity }
      $rad = $h * [Math]::PI / 180.0
      $lx = $TargetX - $d * [Math]::Sin($rad)
      $lz = $TargetZ - $d * [Math]::Cos($rad)
      $name = "{0}_h{1:000}_s{2:00}_r{3}" -f $Tag, [int]$h, [int]$s, $r
      $runs += [pscustomobject]@{
        Name    = $name
        Launch  = ("{0},{1},{2}" -f $lx.ToString('0.###', $inv), $TargetY.ToString('0.###', $inv), $lz.ToString('0.###', $inv))
        Shot    = ("{0}:{1}" -f $h.ToString('0.###', $inv), $s.ToString('0.###', $inv))
        Dist    = $d
        Travel  = $travel
      }
    }
  }
}

# ⭐ THE INVINCIBILITY LINE PRINTS ON EVERY BATCH, CONTAMINATED OR NOT. A warning that only appears
# when it fires leaves the reader unable to tell a clean corpus from an un-instrumented one.
$short = @($runs | Where-Object { $_.Travel -lt $KF_CONSOLE_NO_DAMAGE_SECONDS })
$tmin = ($runs | Measure-Object -Property Travel -Minimum).Minimum
$tmax = ($runs | Measure-Object -Property Travel -Maximum).Maximum
Write-Host ("[batch] travel time launch->target: {0:F2} s .. {1:F2} s  (console no-damage window {2:F2} s)" -f $tmin, $tmax, $KF_CONSOLE_NO_DAMAGE_SECONDS)
if ($short.Count -gt 0) {
  Write-Host ("[batch] WARNING: {0} of {1} shot(s) reach the target INSIDE the post-place-on-track invincibility" -f $short.Count, $runs.Count)
  Write-Host  "[batch]          window, so the car is in E_ABSORPTIONSET_INVINCIBLE at impact and CANNOT DENT."
  Write-Host  "[batch]          crash_sweep_report.py will DISCARD those shots. Re-run with -MinDamageableSeconds 1.6"
  Write-Host  "[batch]          (raises the launch distance) if you want deformation or momentum numbers from them."
} else {
  Write-Host  "[batch] every shot clears the 1.5 s window before contact -- the car can dent at impact."
}

Write-Host ("[batch] {0} boots planned (one crash each), tag '{1}'" -f $runs.Count, $Tag)
$i = 0
foreach ($run in $runs) {
  $i++
  $out = Join-Path $root ("scratch\flow_run\" + $run.Name)
  Write-Host ("[batch] {0}/{1}  {2}  launch {3}  shot {4}  dist {5:F1} m  travel {6:F2} s{7}" -f `
              $i, $runs.Count, $run.Name, $run.Launch, $run.Shot, $run.Dist, $run.Travel,
              $(if ($run.Travel -lt $KF_CONSOLE_NO_DAMAGE_SECONDS) { "  <-- INSIDE the 1.5 s invincibility window" } else { "" }))
  # ⛔ A HASHTABLE, NOT AN ARRAY. PowerShell splats an ARRAY POSITIONALLY -- the leading
  # '-OutDir' string is passed as a VALUE, not read as a parameter name -- so flow_run.ps1
  # bound the out-dir path to its first positional parameter and the whole list shifted, which
  # surfaced as "cannot convert <path> to Int32" on -MaxSeconds. Only hashtable splatting binds
  # by name. (And $args is a PowerShell AUTOMATIC variable: never use it as a splat target.)
  $flowArgs = @{
    OutDir          = $out
    Drive           = $true
    CrashSweep      = $run.Launch
    CrashSweepShots = $run.Shot
    CrashSweepArm   = 4
    DiagEnv         = 'BRN_CRASH_RESPONSE_DIAG=1'
    MaxSeconds      = $MaxSeconds
  }
  if ($Frames) { $flowArgs['Frames'] = $true; $flowArgs['FrameEvery'] = 2 }
  # ⛔ THE REDIRECTION TARGET MUST BE A BARE PATH OR A VARIABLE. `*> (Join-Path ...)` does not
  # parse as a redirect; the parenthesised expression folds back into the argument list.
  $flowLog = Join-Path $root ("scratch\flow_run\" + $run.Name + "_flow.log")
  & (Join-Path $PSScriptRoot 'flow_run.ps1') @flowArgs *> $flowLog
  if (-not (Test-Path (Join-Path $out 'BrnGame.log'))) {
    Write-Host ("[batch]   WARN: no BrnGame.log for {0}" -f $run.Name)
  }
}
Write-Host "[batch] done. Score with:"
Write-Host ("  python tools/diagnostics/crash_sweep_report.py scratch/flow_run/{0}_*/BrnGame.log" -f $Tag)
