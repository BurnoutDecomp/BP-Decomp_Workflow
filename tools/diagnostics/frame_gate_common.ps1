# frame_gate_common.ps1 -- PROVENANCE + SAMPLING shared by frame_gate.ps1 and
# carselect_frame_gate.ps1.  Dot-source it: . (Join-Path $PSScriptRoot 'frame_gate_common.ps1')
#
# ⛔⛔ WHY THIS FILE EXISTS -- READ BEFORE CHANGING A LINE OF IT.
#
#   `BRN_FRAME_DUMP` takes a DIRECTORY.  Set to `1` the game builds the path "1\bb_000000.bmp",
#   fopen()s it relative to build\game\, gets NULL because build\game\1 does not exist, and
#   RETURNS WITHOUT WRITING OR LOGGING ANYTHING.  (device.cpp, DumpBackBufferIfRequested.)
#   Both gates then scored whatever bitmaps happened to already be sitting in the dump
#   directory -- and PASSED, at corr 1.000, on frames from a run that could be days old.
#   That undermined every "frame gate PASS" reported up to 2026-08-04.
#
#   This is the same disease as the fr-FR locale bug that silently skipped the whole
#   correlation block for a day, and the same disease as the destroyed world that survived
#   ~15 boot-verified commits: A CHECK THAT RETURNS A PLAUSIBLE GREEN BECAUSE IT IS NOT
#   LOOKING.  A gate that cannot tell a stale frame from a fresh one is not a gate.
#
# ⭐ THE RULE THIS FILE ENFORCES: a gate must know WHICH RUN produced the pixels it scored,
#   and must say so out loud in every PASS and every FAIL.  No timestamp, no score.

Add-Type -AssemblyName System.Drawing

$INV = [System.Globalization.CultureInfo]::InvariantCulture

# ---------------------------------------------------------------------------------------
# Assert-FrameDirUsable -- catch the `BRN_FRAME_DUMP=1` class of mistake at the gate.
#
# A bare "1", "true", "on", or any relative token is exactly what a caller types when they
# think the variable is a boolean.  The game silently produces nothing from it; the gate
# must not then quietly score someone else's leftovers.
function Assert-FrameDirUsable {
  param([string]$Tag, [string]$FrameDir)

  if ([string]::IsNullOrWhiteSpace($FrameDir)) {
    Write-Host "[$Tag] *** FAIL *** -FrameDir is empty."
    Write-Host "    BRN_FRAME_DUMP takes a DIRECTORY PATH, not a flag."
    exit 1
  }
  # A boolean-looking token is never a directory; name the real mistake instead of
  # letting it fall through to a generic 'not found'.
  if ($FrameDir -match '^\s*(1|0|true|false|on|off|yes|no)\s*$') {
    Write-Host "[$Tag] *** FAIL *** -FrameDir is '$FrameDir' -- that is a FLAG, not a directory."
    Write-Host "    BRN_FRAME_DUMP=1 makes the game fopen '1\bb_000000.bmp' relative to"
    Write-Host "    build\game\, which fails silently and dumps NOTHING.  Pass a real path."
    exit 1
  }
  if (-not [System.IO.Path]::IsPathRooted($FrameDir)) {
    Write-Host "[$Tag] *** FAIL *** -FrameDir '$FrameDir' is a RELATIVE path."
    Write-Host "    The game resolves BRN_FRAME_DUMP against its own working directory"
    Write-Host "    (build\game\), not yours, so a relative value dumps somewhere you are"
    Write-Host "    not looking -- or nowhere at all.  Pass an absolute path."
    exit 1
  }
  if (-not (Test-Path -LiteralPath $FrameDir -PathType Container)) {
    Write-Host "[$Tag] *** FAIL *** -FrameDir '$FrameDir' is not an existing directory."
    Write-Host "    Nothing was dumped there.  Did the run set BRN_FRAME_DUMP to this path?"
    exit 1
  }
}

# ---------------------------------------------------------------------------------------
# Resolve-NotBefore -- the launch instant the frames must postdate.
#
# Supplied explicitly with -NotBefore, or read from the `RUNSTART <ISO8601>` line that
# flow_run.ps1 writes at the top of marks.txt.  If NEITHER is available the gate refuses to
# score at all: an unprovenanced PASS is precisely the failure this file exists to prevent.
function Resolve-NotBefore {
  param([string]$Tag, [string]$NotBefore, [string]$Marks)

  if (-not [string]::IsNullOrWhiteSpace($NotBefore)) {
    try { return [datetime]::Parse($NotBefore, $INV, [System.Globalization.DateTimeStyles]::RoundtripKind) }
    catch {
      Write-Host "[$Tag] *** FAIL *** -NotBefore '$NotBefore' is not a parseable timestamp."
      Write-Host "    Use a round-trip ISO 8601 stamp, e.g. 2026-08-04T18:22:31.4470000+02:00"
      exit 1
    }
  }
  if (-not [string]::IsNullOrWhiteSpace($Marks) -and (Test-Path -LiteralPath $Marks)) {
    $line = (Get-Content -LiteralPath $Marks) | Where-Object { $_ -match '^RUNSTART\s+(\S+)' } | Select-Object -First 1
    if ($line -match '^RUNSTART\s+(\S+)') {
      try { return [datetime]::Parse($Matches[1], $INV, [System.Globalization.DateTimeStyles]::RoundtripKind) } catch { }
    }
  }
  Write-Host "[$Tag] *** FAIL *** no launch timestamp -- REFUSING TO SCORE."
  Write-Host "    This gate will not certify frames whose run it cannot identify.  Setting"
  Write-Host "    BRN_FRAME_DUMP=1 dumps nothing silently, and without a timestamp the gate"
  Write-Host "    would then score stale bitmaps and PASS at corr 1.000.  That happened."
  Write-Host "    Pass -NotBefore <ISO8601>, or -Marks <marks.txt> containing a RUNSTART line"
  Write-Host "    (tools\diagnostics\flow_run.ps1 writes one automatically)."
  exit 1
}

# ---------------------------------------------------------------------------------------
# Get-FreshFrames -- every .bmp in the dump dir, proven to belong to THIS run.
#
# Fails on an empty dir, and fails if ANY bitmap predates the launch.  The strict form
# matters: a dump directory that was not cleaned holds frames from two runs, and "newest by
# present count" can then be a STALE frame with a high counter.  Mixed provenance is
# unscoreable, so it is a hard failure rather than a filter.
function Get-FreshFrames {
  param([string]$Tag, [string]$FrameDir, [datetime]$NotBefore, [double]$SkewSeconds = 2.0)

  $all = @(Get-ChildItem -LiteralPath $FrameDir -Filter *.bmp -ErrorAction SilentlyContinue)
  if ($all.Count -eq 0) {
    Write-Host "[$Tag] *** FAIL *** no frames in $FrameDir"
    Write-Host "    The run dumped nothing.  BRN_FRAME_DUMP must be an ABSOLUTE DIRECTORY;"
    Write-Host "    set to a flag like '1' the game writes nothing and says nothing."
    exit 1
  }

  # Clock granularity between Get-Date and NTFS mtime can be a few ms; a real frame lands
  # many seconds into a boot, so a couple of seconds of slack cannot mask a stale dump.
  $cut   = $NotBefore.AddSeconds(-$SkewSeconds)
  $stale = @($all | Where-Object { $_.LastWriteTime -lt $cut })
  $newest = ($all | Sort-Object LastWriteTime)[-1]

  if ($stale.Count -gt 0) {
    $oldest = ($stale | Sort-Object LastWriteTime)[0]
    Write-Host "[$Tag] *** FAIL *** STALE FRAMES -- REFUSING TO SCORE."
    Write-Host ("    dump dir      : {0}" -f $FrameDir)
    Write-Host ("    launch (run)  : {0}" -f $NotBefore.ToString('o', $INV))
    Write-Host ("    stale frames  : {0} of {1} predate the launch" -f $stale.Count, $all.Count)
    Write-Host ("    oldest stale  : {0}  mtime {1}" -f $oldest.Name, $oldest.LastWriteTime.ToString('o', $INV))
    Write-Host ("    newest frame  : {0}  mtime {1}" -f $newest.Name, $newest.LastWriteTime.ToString('o', $INV))
    if ($newest.LastWriteTime -lt $cut) {
      Write-Host "    ⇒ EVERY frame here is older than the launch.  This run dumped NOTHING."
      Write-Host "      Almost always: BRN_FRAME_DUMP was set to a flag instead of a path."
    } else {
      Write-Host "    ⇒ MIXED PROVENANCE: the dump directory was not cleaned before the run."
      Write-Host "      Frames are named by present count, so a stale frame can outrank a"
      Write-Host "      fresh one by name.  Delete the directory and re-run."
    }
    exit 1
  }
  return ,$all
}

# ---------------------------------------------------------------------------------------
# Get-FrameLuma -- 64x36 grey downsample, 2304 samples.
# Kept bit-identical to the original inline code so the banked goldens stay valid.
function Get-FrameLuma {
  param([string]$Path)
  $img = [System.Drawing.Image]::FromFile($Path)
  $bm  = New-Object System.Drawing.Bitmap($img, 64, 36)
  $img.Dispose()
  $lum = New-Object System.Collections.Generic.List[double]
  for ($y=0; $y -lt 36; $y++) { for ($x=0; $x -lt 64; $x++) {
    $c = $bm.GetPixel($x,$y); $lum.Add(0.299*$c.R + 0.587*$c.G + 0.114*$c.B) } }
  $bm.Dispose()
  return $lum
}

function Get-LumaStats {
  param($Lum)
  $mean = ($Lum | Measure-Object -Average).Average
  $sd   = [math]::Sqrt((($Lum | ForEach-Object { ($_-$mean)*($_-$mean) }) | Measure-Object -Average).Average)
  return @{ mean = $mean; sd = $sd }
}

# ⚠️ InvariantCulture on BOTH ends.  On this fr-FR host a plain ToString() writes "79,444",
#   so a comma-joined golden parses as 4608 fields instead of 2304, the count test fails and
#   the correlation is SKIPPED -- the gate then prints "corr=n/a  PASS".  The banked
#   handover golden sat in that state from the day it was written (task #127).  A length
#   mismatch is a LOUD FAILURE here, never a silent skip.
function Write-Golden {
  param($Lum, [string]$Path, [string]$Tag)
  (($Lum | ForEach-Object { $_.ToString($INV) }) -join ',') | Set-Content $Path
  Write-Host "[$Tag] golden written -> $Path"
}

# Get-GoldenStats -- the mean/sd a banked golden itself measures.
# Lets -BySignature calibrate itself from the golden instead of hard-coded constants.
function Get-GoldenStats {
  param([string]$Path)
  $g = (Get-Content $Path) -split ',' | ForEach-Object { [double]::Parse($_, $INV) }
  return Get-LumaStats -Lum $g
}

function Get-GoldenCorr {
  param($Lum, [double]$Mean, [string]$Path, [ref]$Fail)
  $g = (Get-Content $Path) -split ',' | ForEach-Object { [double]::Parse($_, $INV) }
  if ($g.Count -ne $Lum.Count) {
    $Fail.Value += ("golden has {0} values, the frame has {1} -- STALE OR LOCALE-CORRUPTED GOLDEN, re-bank it" -f $g.Count, $Lum.Count)
    return $null
  }
  $gm = ($g | Measure-Object -Average).Average
  $num=0.0; $da=0.0; $db=0.0
  for ($i=0; $i -lt $g.Count; $i++) { $a=$Lum[$i]-$Mean; $b=$g[$i]-$gm; $num+=$a*$b; $da+=$a*$a; $db+=$b*$b }
  if ($da -gt 0 -and $db -gt 0) { return $num / [math]::Sqrt($da*$db) }
  return 0.0
}

# ---------------------------------------------------------------------------------------
# Write-Provenance -- printed in EVERY pass and EVERY fail, no exceptions.
# If a future wave reports a green gate, this block is what makes the claim checkable.
function Write-Provenance {
  param([string]$Tag, [string]$FrameDir, $Frames, [datetime]$NotBefore, $Scored)
  $newest = ($Frames | Sort-Object LastWriteTime)[-1]
  Write-Host ("[{0}] run provenance:" -f $Tag)
  Write-Host ("[{0}]   dump dir     {1}" -f $Tag, $FrameDir)
  Write-Host ("[{0}]   launch       {1}" -f $Tag, $NotBefore.ToString('o', $INV))
  Write-Host ("[{0}]   frames       {1}, newest {2} @ {3}" -f `
              $Tag, $Frames.Count, $newest.Name, $newest.LastWriteTime.ToString('o', $INV))
  Write-Host ("[{0}]   SCORED       {1} @ {2}" -f `
              $Tag, $Scored.Name, $Scored.LastWriteTime.ToString('o', $INV))
}
