# frame_gate.ps1 -- THE CHECK THAT WOULD HAVE CAUGHT TASK 118.
#
# Assert counting, exe size, a clean link and a green lint all passed a destroyed world for a
# full day, across ~15 boot-verified commits, because nothing ever LOOKED AT A FRAME.
# This is the cheapest thing that does. Runtime: about 1 second on top of a boot run.
#
# ⛔⛔ AND THE CHECK THAT ITSELF FAILED, 2026-08-04 (task #139).
#   Until this revision the gate sorted the dump directory BY NAME and scored the last entry,
#   with no notion of when those pixels were produced.  `BRN_FRAME_DUMP=1` dumps NOTHING
#   silently (the game fopen()s "1\bb_000000.bmp" relative to build\game\ and gets NULL), so
#   the gate happily scored bitmaps left over from an earlier -- possibly days-old -- run and
#   reported PASS at corr 1.000.  EVERY "frame gate PASS" banked before this revision is
#   therefore unproven: not one of them verified the frames came from that run.
#   Provenance is now mandatory.  See frame_gate_common.ps1 for the full autopsy.
#
# Usage (after a flow_run.ps1 -Frames run):
#     frame_gate.ps1 -FrameDir <dir> -Marks <out>\marks.txt
#     frame_gate.ps1 -FrameDir <dir> -NotBefore 2026-08-04T18:22:31.4470000+02:00
#     frame_gate.ps1 -FrameDir <dir> -Marks ... -Golden golden_junkyard_handover.csv
#     frame_gate.ps1 -FrameDir <dir> -Marks ... -WriteGolden golden_junkyard_handover.csv
#
#   -Marks or -NotBefore is REQUIRED.  Without one the gate refuses to score rather than
#   emit an unprovenanced green.  flow_run.ps1 writes the RUNSTART line -Marks reads.
#
# ⛔ Goldens must be banked on a DEFAULT run -- never through BRN_WORLD_CAMFREE.  That flag
#   is how a day-long world-render regression hid: it was added by the very commit that broke
#   the world, so every shot taken through it looked fine while the default run was broken.
#
# RE-BANKED 2026-08-05 (the SEAT wave), old golden 123.2/89.5, old corr 0.654 -- THE CAR POSE
# CHANGED BY DESIGN and the frame was LOOKED AT before re-banking: the analytic rest seat
# (VehiclePhysics::SetTransformFromPositionOnRoad @0x825D1C00, run at the promote seam) +
# mCentreOfMassTransform from the shipped spec+1552 + the render publish's graphics-frame step
# put the car ON its wheels ON the ground (physics ground+1.4459 / model +0.7054 / body-draw
# -0.035 -- witness lines "[seat]" and "[seat-pose]" in BrnGame.log). The chase framing shifts
# because the visible car dropped ~0.74 m onto its wheels.
#
# Exit code 0 = PASS, 1 = FAIL. Intended to be the LAST line of the boot harness, so a wave
# cannot report "baseline held" without a frame that actually shows the world.
param(
  [Parameter(Mandatory=$true)][string]$FrameDir,
  [string]$Marks = "",
  [string]$NotBefore = "",
  [string]$Golden = "",
  [string]$WriteGolden = "",
  [double]$MinMean = 60.0,     # good junkyard frames measure 122-124; shard frames 33-39
  [double]$MinSd   = 40.0,     # good 89-90; shard 16-20
  [double]$MinCorr = 0.90,
  [double]$SkewSeconds = 2.0
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'frame_gate_common.ps1')
$TAG = 'frame-gate'

# --- provenance first: refuse bad input before any pixel is read -------------------------
Assert-FrameDirUsable -Tag $TAG -FrameDir $FrameDir
$launch = Resolve-NotBefore -Tag $TAG -NotBefore $NotBefore -Marks $Marks
$frames = Get-FreshFrames -Tag $TAG -FrameDir $FrameDir -NotBefore $launch -SkewSeconds $SkewSeconds

# The post-handover chase shot is the last frame of the run.  Sorted by name = by present
# count; every frame here is already proven to belong to this run.
$scored = ($frames | Sort-Object Name)[-1]

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
    if ($corr -lt $MinCorr) { $fail += ("golden correlation {0:f3} < {1}" -f $corr, $MinCorr) }
  }
}

Write-Provenance -Tag $TAG -FrameDir $FrameDir -Frames $frames -NotBefore $launch -Scored $scored
Write-Host ("[{0}] frame {1}  mean={2:f1} sd={3:f1} corr={4}" -f $TAG, $scored.Name, $mean, $sd, $corrTxt)
if ($fail.Count -gt 0) {
  Write-Host "[$TAG] *** FAIL *** the rendered world is not plausible:"
  $fail | ForEach-Object { Write-Host "    - $_" }
  Write-Host "    LOOK AT $($scored.FullName) BEFORE REPORTING THIS BUILD GREEN."
  exit 1
}
Write-Host "[$TAG] PASS"
exit 0
