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
param(
  [string]$Tag        = "cs",
  [double[]]$Headings = @(210, 220, 230, 240),
  [double[]]$Speeds   = @(30, 40, 50, 60),
  [int]$Repeats       = 1,
  [double]$TargetX    = 3170.6,
  [double]$TargetY    = -3.7,
  [double]$TargetZ    = -2004.6,
  [double]$Distance   = 42.0,
  [int]$MaxSeconds    = 75,
  [switch]$Frames                       # dump frames (only ever for ONE shot -- see MinFreeGB)
)
$ErrorActionPreference = 'Stop'
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$inv  = [Globalization.CultureInfo]::InvariantCulture

$runs = @()
foreach ($r in 1..$Repeats) {
  foreach ($h in $Headings) {
    foreach ($s in $Speeds) {
      $rad = $h * [Math]::PI / 180.0
      $lx = $TargetX - $Distance * [Math]::Sin($rad)
      $lz = $TargetZ - $Distance * [Math]::Cos($rad)
      $name = "{0}_h{1:000}_s{2:00}_r{3}" -f $Tag, [int]$h, [int]$s, $r
      $runs += [pscustomobject]@{
        Name    = $name
        Launch  = ("{0},{1},{2}" -f $lx.ToString('0.###', $inv), $TargetY.ToString('0.###', $inv), $lz.ToString('0.###', $inv))
        Shot    = ("{0}:{1}" -f $h.ToString('0.###', $inv), $s.ToString('0.###', $inv))
      }
    }
  }
}

Write-Host ("[batch] {0} boots planned (one crash each), tag '{1}'" -f $runs.Count, $Tag)
$i = 0
foreach ($run in $runs) {
  $i++
  $out = Join-Path $root ("scratch\flow_run\" + $run.Name)
  Write-Host ("[batch] {0}/{1}  {2}  launch {3}  shot {4}" -f $i, $runs.Count, $run.Name, $run.Launch, $run.Shot)
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
