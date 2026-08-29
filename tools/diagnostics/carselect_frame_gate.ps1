# carselect_frame_gate.ps1 -- THE CHECK THAT WOULD HAVE CAUGHT TASK 127.
#
# frame_gate.ps1 samples exactly ONE moment: the post-handover chase camera. Every wave on
# 2026-08-03 reported "frame gate PASS" and every one of them was telling the truth -- while
# the JUNKYARD CAR-SELECT SCREEN, a different game state that the gate never looks at, had the
# camera sitting on the yard floor pointing at the car's underside. A gate that samples one
# state certifies one state.
#
# This gate samples the CAR-SELECT screen.
#
# ⛔⛔ PROVENANCE IS MANDATORY, 2026-08-04 (task #139).  Until this revision the gate picked a
#   frame by present count and never asked when it was written, so a `BRN_FRAME_DUMP=1` run
#   (which dumps NOTHING, silently) scored leftovers from an earlier run and PASSED.  See the
#   autopsy in frame_gate_common.ps1.  -Marks or -NotBefore is now required.
#
# ⭐ TWO WAYS TO FIND THE CAR-SELECT FRAME.  Both are provenance-checked identically.
#   1. -Marks <marks.txt>   FLOW STATE.  Anchors on the `carsel ... frame=bb_NNNNNN.bmp`
#      line flow_run.ps1 writes when the log prints "Entering Car Select", then samples
#      +$PresentsAfterEntry.  Preferred: tied to a transition, not to a frame index.
#   2. -BySignature         FRAME SIGNATURE.  Car select (mean ~27.6 / sd ~34.4) and the
#      chase view (mean ~123.2 / sd ~89.5) are unmistakable in a 64x36 grey downsample, so
#      the car-select stretch can be found in the dump with no marks at all.  This is the
#      fallback when a run's marks are missing, and it is how task #138 re-found the banked
#      27.6/34.4 at corr 1.000.
#   -Marks still supplies RUNSTART for the freshness check even in -BySignature mode; use
#   -NotBefore instead if you genuinely have no marks file.
#
# Usage:
#   carselect_frame_gate.ps1 -FrameDir <dir> -Marks <out>\marks.txt
#   carselect_frame_gate.ps1 -FrameDir <dir> -Marks ... -Golden golden_junkyard_carselect.csv
#   carselect_frame_gate.ps1 -FrameDir <dir> -Marks ... -WriteGolden golden_junkyard_carselect.csv
#   carselect_frame_gate.ps1 -FrameDir <dir> -NotBefore <iso> -BySignature -Golden ...
#
# ⚠️⚠️ WHAT THE BANKED GOLDEN IS. golden_junkyard_carselect.csv is the state as of 2026-08-04,
#   and its FRAMING IS STILL WRONG -- the orbit camera is on the junkyard floor (task #127 is
#   open; see the ⚠️⚠️ block in BrnPlaceOnTrackManager.cpp PlaceCarOnTrack). It is banked as a
#   CHANGE DETECTOR, not as a statement that this shot is correct: it makes any further
#   movement of the car-select camera visible immediately instead of 25 hours later. When the
#   framing is fixed, re-bank with -WriteGolden and delete this paragraph.
#
#   RE-BANKED 2026-08-04 (task #133), mean 21.5/sd 27.8 -> mean 27.6/sd 34.4, old corr 0.758.
#   The gate did its job and the change was LOOKED AT before re-banking: THE WHEELS NOW DRAW.
#   Because this camera sits BELOW the junkyard floor it is the one shot in the whole flow that
#   sees them -- from the chase camera they are 0.74 m underground (no suspension settle), so
#   frame_gate.ps1 correctly still reads corr 1.000. The four tyres are the pale grey of the
#   flagged fallback pair, which is expected: a console-instanced mesh cannot use its own
#   `*_Instanced` technique program on this build (see the banner in XenonD3D9Shims.cpp).
#   ⇒ EXPECT THIS GOLDEN TO GO RED AGAIN, correctly, when either the suspension settle or the
#   real instanced shader lands. Re-bank then, after looking.
#
#   RE-BANKED 2026-08-05 (the junkyard-reveal wave), mean 27.6/sd 34.4 -> mean 39.8/sd 52.9,
#   old corr 0.539. The gate did its job and the change was LOOKED AT before re-banking: the
#   AUTHORED GAME-INTRO REVEAL now really plays (the ~8 s ICE pan onto the junkyard exterior),
#   so 'Entering Car Select' fires ~5 s later and +300 presents lands while the car-select GUI
#   chrome (banner + stat labels) is still animating in over the SAME floor-level framing --
#   the camera and car did not move (the livery-mark frame is unchanged). Task #127's wrong
#   floor-level framing is still wrong; the paragraph above still applies.
#
#   RE-BANKED 2026-08-05 (the SEAT wave), old corr -0.101 -- THE POSE CHANGED BY DESIGN and was
#   LOOKED AT frame-by-frame before re-banking. Three coupled landings moved the whole car:
#     1. the ANALYTIC REST SEAT (VehiclePhysics::SetTransformFromPositionOnRoad @0x825D1C00,
#        run at the promote seam over the resident spec's own wheel radii/positions): the
#        seeded physics transform is now the handling frame at ground+1.4459, retail's own
#        value (user-measured retail rest ~1.481 = seat + the 0.035 tyre-compression settle);
#     2. mCentreOfMassTransform = the SHIPPED spec+1552 matrix (was identity), so the model
#        frame renders at ground+0.7054;
#     3. the graphics-frame step in the render publish (the GR part locators are authored one
#        more model->handling step down -- measured 1 mm fit on the wheel-arch locators).
#   RESULT: the car sits ON its four wheels ON the sand (wheels in the arches for the first
#   time), the body no longer clips the ground, and the ⚠️⚠️ WHAT-THE-BANKED-GOLDEN-IS
#   paragraph above is PARTLY retired: the car is no longer sunk, so the floor-level orbit
#   camera now sees the car from just below the beltline instead of seeing its underbody.
#   Whether that low orbit height itself is retail-correct (task #127) is still open.
#
# ⭐ NEGATIVE CONTROL: on the seat-wave golden this gate scores corr -0.233 on a post-handover
#   chase frame (re-proven 2026-08-05 after the re-bank; the handover golden scores the same
#   -0.233 against the car-select frame). Earlier goldens: -0.381 (08-05 reveal), -0.371 (08-04).
#   Historical wording kept below:
#   (this gate scored corr -0.381 (was -0.371 on the 08-04 golden) on a
#   post-handover chase frame. That is what proves it discriminates rather than merely
#   passing. Re-check it when re-banking.
#
# Exit code 0 = PASS, 1 = FAIL.
param(
  [Parameter(Mandatory=$true)][string]$FrameDir,
  [string]$Marks = "",
  [string]$NotBefore = "",
  [switch]$BySignature,
  [string]$Golden = "",
  [string]$WriteGolden = "",
  [int]$PresentsAfterEntry = 300,   # ~3 s past "Entering Car Select" at ~100 fps: the settled shot
  # MEASURED on the 2026-08-04 physics-tip run: mean 21.5, sd 27.8. The car-select screen is
  # far darker than the chase view (the car fills the frame and the junkyard is in shadow), so
  # frame_gate.ps1's 60/40 band is wrong here. These sit ~40% below the measurement: low enough
  # not to trip on normal variation, high enough to catch a black or flat frame.
  [double]$MinMean = 12.0,
  [double]$MinSd   = 17.0,
  [double]$MinCorr = 0.90,
  # -BySignature band. Used only when no -Golden is supplied; with a golden these are taken
  # FROM the golden. Measured car select: mean 24.7..27.5, sd 33.1..34.1 (see the block below).
  [double]$SignatureMean    = 27.6,
  [double]$SignatureSd      = 34.4,
  [double]$SignatureMeanTol = 8.0,
  [double]$SignatureSdTol   = 6.0,
  [int]$SignatureStep       = 3,    # profiling 1920x1080 bitmaps is the slow part
  [int]$SignatureMinRun     = 3,    # an isolated in-band frame is a fluke, not a state
  [double]$SkewSeconds = 2.0
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'frame_gate_common.ps1')
$TAG = 'cs-gate'

# --- provenance first: refuse bad input before any pixel is read -------------------------
Assert-FrameDirUsable -Tag $TAG -FrameDir $FrameDir
$launch = Resolve-NotBefore -Tag $TAG -NotBefore $NotBefore -Marks $Marks
$all    = Get-FreshFrames -Tag $TAG -FrameDir $FrameDir -NotBefore $launch -SkewSeconds $SkewSeconds
$byName = @($all | Sort-Object Name)

# --- locate the car-select frame ---------------------------------------------------------
$scored = $null
$how    = ""

if ($BySignature) {
  # ⚠️⚠️ "DARK" IS NOT A SIGNATURE -- measured 2026-08-04, task #139.
  #   The first cut of this block took the longest contiguous stretch with mean < 60 (the
  #   same test the old scratchpad profiler used).  On a real 708-frame dump it selected
  #   bb_001530 -- THIRTEEN SECONDS INTO THE BOOT -- because the loading screens are dark
  #   too.  It then scored corr 0.209 and reported the car-select screen as broken.
  #   MEASURED distribution of one full run:
  #       boot / loading   mean  0.4 .. 33.0   sd  4.7 .. 74.4   (wildly variable)
  #       flyby            mean 88.9 ..106.1   sd 53.3 .. 74.4
  #       CAR SELECT       mean 24.7 .. 27.5   sd 33.1 .. 34.1   (tight, stable)
  #       chase            mean       122.7    sd       89.8     (dead constant)
  #   Car select is separable on BOTH axes together and on NEITHER alone: bb_002400 sits at
  #   mean 31.9 (in band) with sd 25.5 (out), and bb_001200 at sd 44.5 (in-ish) with mean
  #   16.8 (out).  So the band below is two-dimensional.
  #
  # ⭐ AND IT CALIBRATES ITSELF FROM THE GOLDEN when one is supplied, rather than trusting
  #   constants that rot.  This does NOT make the gate circular: mean/sd are
  #   PERMUTATION-INVARIANT -- they locate a candidate frame but cannot certify it, because
  #   a camera that moved to a different spot in the same scene keeps its histogram and
  #   still fails the correlation test that follows.  Locating and certifying stay separate.
  if ($Golden -ne "" -and (Test-Path $Golden)) {
    $gs = Get-GoldenStats -Path $Golden
    $tgtMean = $gs.mean; $tgtSd = $gs.sd
    $calib = "golden"
  } else {
    $tgtMean = $SignatureMean; $tgtSd = $SignatureSd
    $calib = "defaults"
  }
  $loMean = $tgtMean - $SignatureMeanTol; $hiMean = $tgtMean + $SignatureMeanTol
  $loSd   = $tgtSd   - $SignatureSdTol;   $hiSd   = $tgtSd   + $SignatureSdTol
  Write-Host ("[{0}] signature band ({1}): mean {2:f1}+-{3:f1}  sd {4:f1}+-{5:f1}  (step {6})" -f `
              $TAG, $calib, $tgtMean, $SignatureMeanTol, $tgtSd, $SignatureSdTol, $SignatureStep)

  # Coarse scan: profiling 700+ 1920x1080 bitmaps is the slow part, so step through them.
  # ⚠️ But a step is only sound on a big dump. On a short one it can skip the entire state
  #   and report "never showed car select" about a run that did -- so collapse to every
  #   frame when there are few, and never let the step outrun the minimum run length.
  if ($byName.Count -lt 100) { $SignatureStep = 1 }
  $idx = @(0..($byName.Count - 1) | Where-Object { ($_ % $SignatureStep) -eq 0 })
  $hits = @()
  foreach ($i in $idx) {
    $s = Get-LumaStats -Lum (Get-FrameLuma -Path $byName[$i].FullName)
    if ($s.mean -ge $loMean -and $s.mean -le $hiMean -and $s.sd -ge $loSd -and $s.sd -le $hiSd) {
      $hits += [pscustomobject]@{ Index = $i; File = $byName[$i]; Mean = $s.mean; Sd = $s.sd }
    }
  }
  if ($hits.Count -lt $SignatureMinRun) {
    Write-Host ("[{0}] *** FAIL *** no car-select frame in the dump." -f $TAG)
    Write-Host ("    Scanned {0} of {1} fresh frames (step {2}); {3} fell in the band, need {4}." -f `
                $idx.Count, $byName.Count, $SignatureStep, $hits.Count, $SignatureMinRun)
    Write-Host ("    band: mean {0:f1}..{1:f1}  sd {2:f1}..{3:f1}" -f $loMean, $hiMean, $loSd, $hiSd)
    Write-Host  "    Either the run never showed car select, or the screen changed enough to"
    Write-Host  "    leave the band -- run tools\diagnostics\frame_profile.py on the dump and LOOK."
    Write-Host ("    dump dir {0}, launch {1}" -f $FrameDir, $launch.ToString('o', $INV))
    exit 1
  }
  # Middle of the longest contiguous in-band stretch: the settled shot, away from both fades.
  $bestStart = 0; $bestLen = 1; $curStart = 0; $curLen = 1
  for ($k = 1; $k -lt $hits.Count; $k++) {
    if (($hits[$k].Index - $hits[$k-1].Index) -eq $SignatureStep) { $curLen++ }
    else { $curStart = $k; $curLen = 1 }
    if ($curLen -gt $bestLen) { $bestLen = $curLen; $bestStart = $curStart }
  }
  if ($bestLen -lt $SignatureMinRun) {
    Write-Host ("[{0}] *** FAIL *** car-select-like frames are scattered, not a settled stretch." -f $TAG)
    Write-Host ("    longest contiguous run {0} frames, need {1}. Isolated hits are a fluke, not a state." -f `
                $bestLen, $SignatureMinRun)
    exit 1
  }
  $pickHit = $hits[$bestStart + [int]($bestLen / 2)]
  $scored  = $pickHit.File
  $how = ("signature: {0} in-band frames, longest run {1} from {2}, took the middle (mean {3:f1} sd {4:f1})" -f `
          $hits.Count, $bestLen, $hits[$bestStart].File.Name, $pickHit.Mean, $pickHit.Sd)
}
else {
  if ([string]::IsNullOrWhiteSpace($Marks)) {
    Write-Host "[$TAG] *** FAIL *** need -Marks (flow-state anchor) or -BySignature."
    Write-Host "    Frames are named by PRESENT COUNT, not by time, so 'the frame at ~65 s'"
    Write-Host "    is only knowable by correlating against the log marks."
    exit 1
  }
  if (-not (Test-Path $Marks)) { Write-Host "[$TAG] FAIL: no marks file at $Marks"; exit 1 }
  $carselLine = (Get-Content $Marks) | Where-Object { $_ -match '^carsel' } | Select-Object -First 1
  if (-not $carselLine) { Write-Host "[$TAG] FAIL: the run never reached car select"; exit 1 }
  if ($carselLine -notmatch 'frame=bb_(\d+)\.bmp') {
    Write-Host "[$TAG] FAIL: car-select mark carries no frame -- was the run started with -Frames?"; exit 1
  }
  $entry  = [int]$Matches[1]
  $target = $entry + $PresentsAfterEntry

  # The dumped frame at or just past the target present count.
  $scored = $byName | Where-Object { $_.Name -match 'bb_(\d+)\.bmp' -and [int]$Matches[1] -ge $target } | Select-Object -First 1
  if (-not $scored) {
    Write-Host ("[{0}] FAIL: the run left car select before +{1} presents (entry bb_{2:d6}, last {3})" -f `
                $TAG, $PresentsAfterEntry, $entry, $byName[-1].Name)
    exit 1
  }
  $how = ("flow state: 'Entering Car Select' at bb_{0:d6}, +{1} presents" -f $entry, $PresentsAfterEntry)
}

$lum = Get-FrameLuma -Path $scored.FullName
$st  = Get-LumaStats -Lum $lum
$mean = $st.mean; $sd = $st.sd

if ($WriteGolden -ne "") { Write-Golden -Lum $lum -Path $WriteGolden -Tag $TAG }

$fail = @()
if ($mean -lt $MinMean) { $fail += ("mean luminance {0:f1} < {1}" -f $mean, $MinMean) }
if ($sd   -lt $MinSd)   { $fail += ("luminance sd {0:f1} < {1} (a flat/shard frame)" -f $sd, $MinSd) }

$corrTxt = "n/a"
if ($Golden -ne "" -and (Test-Path $Golden)) {
  $corr = Get-GoldenCorr -Lum $lum -Mean $mean -Path $Golden -Fail ([ref]$fail)
  if ($null -ne $corr) {
    $corrTxt = "{0:f3}" -f $corr
    if ($corr -lt $MinCorr) { $fail += ("golden correlation {0:f3} < {1} -- THE CAR-SELECT CAMERA MOVED" -f $corr, $MinCorr) }
  }
}

Write-Provenance -Tag $TAG -FrameDir $FrameDir -Frames $all -NotBefore $launch -Scored $scored
Write-Host ("[{0}]   picked by    {1}" -f $TAG, $how)
Write-Host ("[{0}] sampled {1}  mean={2:f1} sd={3:f1} corr={4}" -f $TAG, $scored.Name, $mean, $sd, $corrTxt)
if ($fail.Count -gt 0) {
  Write-Host "[$TAG] *** FAIL *** the car-select screen is not what was banked:"
  $fail | ForEach-Object { Write-Host "    - $_" }
  Write-Host "    LOOK AT $($scored.FullName) BEFORE REPORTING THIS BUILD GREEN."
  exit 1
}
Write-Host "[$TAG] PASS"
exit 0
