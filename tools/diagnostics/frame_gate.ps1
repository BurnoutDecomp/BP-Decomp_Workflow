# frame_gate.ps1 -- THE CHECK THAT WOULD HAVE CAUGHT TASK 118.
#
# Assert counting, exe size, a clean link and a green lint all passed a destroyed world for a
# full day, across ~15 boot-verified commits, because nothing ever LOOKED AT A FRAME.
# This is the cheapest thing that does. Runtime: about 1 second on top of a boot run.
#
# Usage (after a BRN_FRAME_DUMP run):
#     frame_gate.ps1 -FrameDir D:\...\dh_frames                 # absolute tripwire only
#     frame_gate.ps1 -FrameDir ... -Golden sig_good.csv         # + golden correlation
#     frame_gate.ps1 -FrameDir ... -WriteGolden sig_good.csv    # bank a new golden
#
# Exit code 0 = PASS, 1 = FAIL. Intended to be the LAST line of the boot harness, so a wave
# cannot report "baseline held" without a frame that actually shows the world.
param(
  [Parameter(Mandatory=$true)][string]$FrameDir,
  [string]$Golden = "",
  [string]$WriteGolden = "",
  [double]$MinMean = 60.0,     # good junkyard frames measure 122-124; shard frames 33-39
  [double]$MinSd   = 40.0,     # good 89-90; shard 16-20
  [double]$MinCorr = 0.90
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$f = Get-ChildItem $FrameDir -Filter *.bmp -ErrorAction SilentlyContinue | Sort-Object Name
if ($f.Count -eq 0) { Write-Host "[frame-gate] FAIL: no frames dumped -- did BRN_FRAME_DUMP get set?"; exit 1 }

$img = [System.Drawing.Image]::FromFile($f[-1].FullName)
$bm  = New-Object System.Drawing.Bitmap($img, 64, 36)
$img.Dispose()
$lum = New-Object System.Collections.Generic.List[double]
for ($y=0; $y -lt 36; $y++) { for ($x=0; $x -lt 64; $x++) {
  $c = $bm.GetPixel($x,$y); $lum.Add(0.299*$c.R + 0.587*$c.G + 0.114*$c.B) } }
$bm.Dispose()

$mean = ($lum | Measure-Object -Average).Average
$sd   = [math]::Sqrt((($lum | ForEach-Object { ($_-$mean)*($_-$mean) }) | Measure-Object -Average).Average)

if ($WriteGolden -ne "") { ($lum -join ',') | Set-Content $WriteGolden; Write-Host "[frame-gate] golden written -> $WriteGolden" }

$fail = @()
if ($mean -lt $MinMean) { $fail += ("mean luminance {0:f1} < {1}" -f $mean, $MinMean) }
if ($sd   -lt $MinSd)   { $fail += ("luminance sd {0:f1} < {1} (a flat/shard frame)" -f $sd, $MinSd) }

$corrTxt = "n/a"
if ($Golden -ne "" -and (Test-Path $Golden)) {
  $g = (Get-Content $Golden) -split ',' | ForEach-Object { [double]$_ }
  if ($g.Count -eq $lum.Count) {
    $gm = ($g | Measure-Object -Average).Average
    $num=0.0; $da=0.0; $db=0.0
    for ($i=0; $i -lt $g.Count; $i++) { $a=$lum[$i]-$mean; $b=$g[$i]-$gm; $num+=$a*$b; $da+=$a*$a; $db+=$b*$b }
    $corr = if ($da -gt 0 -and $db -gt 0) { $num / [math]::Sqrt($da*$db) } else { 0 }
    $corrTxt = "{0:f3}" -f $corr
    if ($corr -lt $MinCorr) { $fail += ("golden correlation {0:f3} < {1}" -f $corr, $MinCorr) }
  }
}

Write-Host ("[frame-gate] frame {0}  mean={1:f1} sd={2:f1} corr={3}" -f $f[-1].Name, $mean, $sd, $corrTxt)
if ($fail.Count -gt 0) {
  Write-Host "[frame-gate] *** FAIL *** the rendered world is not plausible:"
  $fail | ForEach-Object { Write-Host "    - $_" }
  Write-Host "    LOOK AT $($f[-1].FullName) BEFORE REPORTING THIS BUILD GREEN."
  exit 1
}
Write-Host "[frame-gate] PASS"
exit 0
