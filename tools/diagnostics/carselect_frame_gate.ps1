# carselect_frame_gate.ps1 -- THE CHECK THAT WOULD HAVE CAUGHT TASK 127.
#
# frame_gate.ps1 samples exactly ONE moment: the post-handover chase camera. Every wave on
# 2026-08-03 reported "frame gate PASS" and every one of them was telling the truth -- while
# the JUNKYARD CAR-SELECT SCREEN, a different game state that the gate never looks at, had the
# camera sitting on the yard floor pointing at the car's underside. A gate that samples one
# state certifies one state.
#
# This gate samples the CAR-SELECT screen. It needs the mark file cs_run.ps1 writes, because
# frames are named by PRESENT COUNT, not by time, so "the frame at ~65 s" is only knowable by
# correlating against the log marks.
#
# Usage (after a `cs_run.ps1 -Frames` run):
#   carselect_frame_gate.ps1 -FrameDir D:\...\cs_frames -Marks <out>\marks.txt
#   carselect_frame_gate.ps1 -FrameDir ... -Marks ... -Golden golden_junkyard_carselect.csv
#   carselect_frame_gate.ps1 -FrameDir ... -Marks ... -WriteGolden golden_junkyard_carselect.csv
#
# ⚠️⚠️ WHAT THE BANKED GOLDEN IS. golden_junkyard_carselect.csv is the state as of 2026-08-04,
#   and its FRAMING IS STILL WRONG -- the orbit camera is on the junkyard floor (task #127 is
#   open; see the ⚠️⚠️ block in BrnPlaceOnTrackManager.cpp PlaceCarOnTrack). It is banked as a
#   CHANGE DETECTOR, not as a statement that this shot is correct: it makes any further
#   movement of the car-select camera visible immediately instead of 25 hours later. When the
#   framing is fixed, re-bank with -WriteGolden and delete this paragraph.
#
# Exit code 0 = PASS, 1 = FAIL.
param(
  [Parameter(Mandatory=$true)][string]$FrameDir,
  [Parameter(Mandatory=$true)][string]$Marks,
  [string]$Golden = "",
  [string]$WriteGolden = "",
  [int]$PresentsAfterEntry = 300,   # ~3 s past "Entering Car Select" at ~100 fps: the settled shot
  # MEASURED on the 2026-08-04 physics-tip run: mean 21.5, sd 27.8. The car-select screen is
  # far darker than the chase view (the car fills the frame and the junkyard is in shadow), so
  # frame_gate.ps1's 60/40 band is wrong here. These sit ~40% below the measurement: low enough
  # not to trip on normal variation, high enough to catch a black or flat frame.
  [double]$MinMean = 12.0,
  [double]$MinSd   = 17.0,
  [double]$MinCorr = 0.90
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

if (-not (Test-Path $Marks)) { Write-Host "[cs-gate] FAIL: no marks file at $Marks"; exit 1 }
$carselLine = (Get-Content $Marks) | Where-Object { $_ -match '^carsel' } | Select-Object -First 1
if (-not $carselLine) { Write-Host "[cs-gate] FAIL: the run never reached car select"; exit 1 }
if ($carselLine -notmatch 'frame=bb_(\d+)\.bmp') {
  Write-Host "[cs-gate] FAIL: car-select mark carries no frame -- was the run started with -Frames?"; exit 1
}
$entry  = [int]$Matches[1]
$target = $entry + $PresentsAfterEntry

$all = Get-ChildItem $FrameDir -Filter *.bmp -ErrorAction SilentlyContinue | Sort-Object Name
if ($all.Count -eq 0) { Write-Host "[cs-gate] FAIL: no frames dumped -- did BRN_FRAME_DUMP get set?"; exit 1 }

# The dumped frame at or just past the target present count.
$pick = $all | Where-Object { $_.Name -match 'bb_(\d+)\.bmp' -and [int]$Matches[1] -ge $target } | Select-Object -First 1
if (-not $pick) {
  Write-Host ("[cs-gate] FAIL: the run left car select before +{0} presents (entry bb_{1:d6}, last {2})" -f `
              $PresentsAfterEntry, $entry, $all[-1].Name)
  exit 1
}

$img = [System.Drawing.Image]::FromFile($pick.FullName)
$bm  = New-Object System.Drawing.Bitmap($img, 64, 36)
$img.Dispose()
$lum = New-Object System.Collections.Generic.List[double]
for ($y=0; $y -lt 36; $y++) { for ($x=0; $x -lt 64; $x++) {
  $c = $bm.GetPixel($x,$y); $lum.Add(0.299*$c.R + 0.587*$c.G + 0.114*$c.B) } }
$bm.Dispose()

$mean = ($lum | Measure-Object -Average).Average
$sd   = [math]::Sqrt((($lum | ForEach-Object { ($_-$mean)*($_-$mean) }) | Measure-Object -Average).Average)

# ⚠️ InvariantCulture on BOTH ends -- see the same note in frame_gate.ps1. On an fr-FR host a
#   plain ToString() writes "21,5" and the comma-joined golden parses as twice as many fields,
#   which silently disables the correlation.
$INV = [System.Globalization.CultureInfo]::InvariantCulture
if ($WriteGolden -ne "") {
  (($lum | ForEach-Object { $_.ToString($INV) }) -join ',') | Set-Content $WriteGolden
  Write-Host "[cs-gate] golden written -> $WriteGolden"
}

$fail = @()
if ($mean -lt $MinMean) { $fail += ("mean luminance {0:f1} < {1}" -f $mean, $MinMean) }
if ($sd   -lt $MinSd)   { $fail += ("luminance sd {0:f1} < {1} (a flat/shard frame)" -f $sd, $MinSd) }

$corrTxt = "n/a"
if ($Golden -ne "" -and (Test-Path $Golden)) {
  $g = (Get-Content $Golden) -split ',' | ForEach-Object { [double]::Parse($_, $INV) }
  if ($g.Count -ne $lum.Count) {
    $fail += ("golden has {0} values, the frame has {1} -- STALE OR LOCALE-CORRUPTED GOLDEN, re-bank it" -f $g.Count, $lum.Count)
  }
  else {
    $gm = ($g | Measure-Object -Average).Average
    $num=0.0; $da=0.0; $db=0.0
    for ($i=0; $i -lt $g.Count; $i++) { $a=$lum[$i]-$mean; $b=$g[$i]-$gm; $num+=$a*$b; $da+=$a*$a; $db+=$b*$b }
    $corr = if ($da -gt 0 -and $db -gt 0) { $num / [math]::Sqrt($da*$db) } else { 0 }
    $corrTxt = "{0:f3}" -f $corr
    if ($corr -lt $MinCorr) { $fail += ("golden correlation {0:f3} < {1} -- THE CAR-SELECT CAMERA MOVED" -f $corr, $MinCorr) }
  }
}

Write-Host ("[cs-gate] entry bb_{0:d6} -> sampled {1}  mean={2:f1} sd={3:f1} corr={4}" -f `
            $entry, $pick.Name, $mean, $sd, $corrTxt)
if ($fail.Count -gt 0) {
  Write-Host "[cs-gate] *** FAIL *** the car-select screen is not what was banked:"
  $fail | ForEach-Object { Write-Host "    - $_" }
  Write-Host "    LOOK AT $($pick.FullName) BEFORE REPORTING THIS BUILD GREEN."
  exit 1
}
Write-Host "[cs-gate] PASS"
exit 0
