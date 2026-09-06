# _checks.ps1 -- the check library run_case.ps1 evaluates a case's `Checks` list with.
#
# Every check is a hashtable with a `Kind` and a `Name`; the rest is per kind. Every check
# returns @{ Pass = $bool; Detail = 'one line the report prints' }. A check that cannot be
# evaluated (missing frame, bad regex) FAILS with the reason in Detail -- it never passes by
# default, so an evidence gap reads as a failure, not a green.
#
# Kinds:
#   LogCount   Pattern (regex)  Min / Max (either optional)         -- count of matching log lines
#   LogMatch   Pattern (regex)  Expect ($true = must appear, $false = must NOT appear)
#   LogValue   Pattern (regex with a NAMED group)  Group  Agg (max|min|last|first|mean|any|all)
#              Min / Max  -- extract a number from every matching line, aggregate, compare.
#              Agg 'any' passes if ANY value is in [Min,Max]; 'all' if EVERY value is.
#              Optional After='<mark>' restricts to lines after that flow mark's timestamp.
#   Mark       Phase (the final phase in marks.txt: BOOT|FLYBY|CARSELECT|DRIVING) or
#              Cue (a cue name that must have fired, i.e. not "(never)")
#   Frame      At ('<cue>' from marks.txt, 'last', or an integer frame index)  Offset (frames,
#              default 0)  Region ('x0,y0,x1,y1' pixels, or fractions 0..1)  Stat (see
#              frame_stats.py: lum_mean lum_std dark_frac bright_frac r_mean g_mean b_mean
#              sat_mean)  Min / Max
#   FrameRatio Same At/Offset; RegionA / RegionB; Stat; Min / Max on (statA / statB)
#   NewAsserts (no other fields; optional Known = path to a regex list, default known_asserts.txt)
#              -- groups every `[ASSERT n] <msg>` line into families (digits/paths stripped) and
#              FAILS if any family is not in the known list. Detail names the new families with
#              counts and the file:line of each -- the first thing to read on a red run.
#   Script     Script = { param($ctx) ... ; return @{ Pass=..; Detail=.. } }
#              $ctx has: Log (path), LogLines (string[]), Marks (hashtable cue->@{Secs;Frame}),
#              MarksText, Phase, FrameDir, RunDir, Case
#
# Dot-source this file; run_case.ps1 does.

$script:TestsRoot = $PSScriptRoot
$script:FrameStatsPy = Join-Path $PSScriptRoot 'frame_stats.py'

function Parse-Marks([string]$lsMarksPath) {
  # marks.txt lines look like:
  #   flyby    (never)
  #   carsel     17,6s  frame=-
  #   ingame     15.3s  frame=bb_001230.bmp
  #   asserts=0 phase=DRIVING
  # Decimal separator is locale-dependent (de-DE writes 17,6s) -- accept both.
  $lMarks = @{}
  $lsPhase = ''
  $liAsserts = -1
  if (-not (Test-Path $lsMarksPath)) { return @{ Marks = $lMarks; Phase = ''; Asserts = -1; Text = '' } }
  $laLines = Get-Content $lsMarksPath
  foreach ($lsLine in $laLines) {
    if ($lsLine -match '^asserts=(\d+)\s+phase=(\w+)') { $liAsserts = [int]$Matches[1]; $lsPhase = $Matches[2]; continue }
    if ($lsLine -match '^(\S+)\s+\(never\)') { $lMarks[$Matches[1]] = @{ Secs = $null; Frame = $null; Fired = $false }; continue }
    if ($lsLine -match '^(\S+)\s+([\d.,]+)s\s+frame=(\S+)') {
      $lsSecs = $Matches[2] -replace ',', '.'
      $lsFrame = $Matches[3]
      $lMarks[$Matches[1]] = @{
        Secs  = [double]::Parse($lsSecs, [System.Globalization.CultureInfo]::InvariantCulture)
        Frame = $(if ($lsFrame -eq '-') { $null } else { $lsFrame })
        Fired = $true
      }
    }
  }
  return @{ Marks = $lMarks; Phase = $lsPhase; Asserts = $liAsserts; Text = ($laLines -join "`n") }
}

function Get-FrameFiles([string]$lsFrameDir) {
  if (-not $lsFrameDir -or -not (Test-Path $lsFrameDir)) { return @() }
  return @(Get-ChildItem $lsFrameDir -Filter 'bb_*.bmp' | Sort-Object Name)
}

function Resolve-FrameAt($lCtx, $lAt, [int]$liOffset) {
  # Returns the full path of the frame a check names, or $null with a reason.
  $laFrames = Get-FrameFiles $lCtx.FrameDir
  if ($laFrames.Count -eq 0) { return @{ Path = $null; Why = "no frames in '$($lCtx.FrameDir)' (was the case run with Frames=`$true?)" } }
  $liIndex = -1
  if ($lAt -is [int]) {
    $lsWant = ('bb_{0:d6}.bmp' -f [int]$lAt)
    for ($i = 0; $i -lt $laFrames.Count; $i++) { if ($laFrames[$i].Name -eq $lsWant) { $liIndex = $i; break } }
    if ($liIndex -lt 0) { return @{ Path = $null; Why = "frame $lsWant not dumped" } }
  } elseif ("$lAt" -eq 'last') {
    $liIndex = $laFrames.Count - 1
  } else {
    $lMark = $lCtx.Marks["$lAt"]
    if ($null -eq $lMark) { return @{ Path = $null; Why = "no mark named '$lAt' in marks.txt" } }
    if (-not $lMark.Fired) { return @{ Path = $null; Why = "mark '$lAt' never fired" } }
    if ($null -eq $lMark.Frame) { return @{ Path = $null; Why = "mark '$lAt' fired but recorded no frame (frame=-)" } }
    for ($i = 0; $i -lt $laFrames.Count; $i++) { if ($laFrames[$i].Name -eq $lMark.Frame) { $liIndex = $i; break } }
    if ($liIndex -lt 0) { return @{ Path = $null; Why = "mark '$lAt' names $($lMark.Frame) which is not on disk" } }
  }
  $liIndex += $liOffset
  if ($liIndex -lt 0 -or $liIndex -ge $laFrames.Count) { return @{ Path = $null; Why = "offset $liOffset runs off the dumped range (have $($laFrames.Count))" } }
  return @{ Path = $laFrames[$liIndex].FullName; Why = '' }
}

function Invoke-FrameStat([string]$lsFrame, [string]$lsRegion, [string]$lsStat) {
  # Returns a [double] or throws with python's stderr.
  $laArgs = @('-3', $script:FrameStatsPy, $lsFrame, '--stat', $lsStat)
  if ($lsRegion) { $laArgs += @('--region', $lsRegion) }
  $lsOut = & py @laArgs 2>&1
  if ($LASTEXITCODE -ne 0) { throw "frame_stats.py failed: $lsOut" }
  return [double]::Parse(("$lsOut".Trim()), [System.Globalization.CultureInfo]::InvariantCulture)
}

function Test-Range([double]$lfValue, $lMin, $lMax) {
  if ($null -ne $lMin -and $lfValue -lt [double]$lMin) { return $false }
  if ($null -ne $lMax -and $lfValue -gt [double]$lMax) { return $false }
  return $true
}

function Format-Range($lMin, $lMax) {
  $lsMin = if ($null -ne $lMin) { "$lMin" } else { '-inf' }
  $lsMax = if ($null -ne $lMax) { "$lMax" } else { '+inf' }
  return "[$lsMin, $lsMax]"
}

function Invoke-Check($lCheck, $lCtx) {
  $lsKind = "$($lCheck.Kind)"
  try {
    switch ($lsKind) {
      'LogCount' {
        $liCount = @($lCtx.LogLines | Where-Object { $_ -match $lCheck.Pattern }).Count
        $lbPass = Test-Range $liCount $lCheck.Min $lCheck.Max
        return @{ Pass = $lbPass; Detail = ("{0} line(s) match /{1}/, want {2}" -f $liCount, $lCheck.Pattern, (Format-Range $lCheck.Min $lCheck.Max)) }
      }
      'LogMatch' {
        $lbExpect = if ($null -eq $lCheck.Expect) { $true } else { [bool]$lCheck.Expect }
        $lFirst = $lCtx.LogLines | Where-Object { $_ -match $lCheck.Pattern } | Select-Object -First 1
        $lbFound = $null -ne $lFirst
        $lsShown = if ($lbFound) { "first: " + $lFirst.Substring(0, [Math]::Min(140, $lFirst.Length)) } else { "no line matches" }
        return @{ Pass = ($lbFound -eq $lbExpect); Detail = ("/{0}/ expected {1}; {2}" -f $lCheck.Pattern, $(if ($lbExpect) { 'present' } else { 'ABSENT' }), $lsShown) }
      }
      'LogValue' {
        $laLines = $lCtx.LogLines
        if ($lCheck.After) {
          # Restrict to lines after the mark. Log lines carry no wall-clock, so use the line index
          # of the first cue hit as the boundary (the cue text is what marks.txt matched on).
          $lsCueRegex = $lCtx.CueRegex["$($lCheck.After)"]
          if ($lsCueRegex) {
            $liStart = -1
            for ($i = 0; $i -lt $laLines.Count; $i++) { if ($laLines[$i] -match $lsCueRegex) { $liStart = $i; break } }
            if ($liStart -ge 0) { $laLines = $laLines[$liStart..($laLines.Count - 1)] } else { $laLines = @() }
          }
        }
        $laValues = @()
        foreach ($lsLine in $laLines) {
          if ($lsLine -match $lCheck.Pattern) {
            $lsRaw = $Matches[$lCheck.Group]
            if ($null -ne $lsRaw) {
              $lfV = 0.0
              if ([double]::TryParse(($lsRaw -replace ',', '.'), [System.Globalization.NumberStyles]::Float, [System.Globalization.CultureInfo]::InvariantCulture, [ref]$lfV)) { $laValues += $lfV }
            }
          }
        }
        if ($laValues.Count -eq 0) { return @{ Pass = $false; Detail = ("no line matched /{0}/ with group '{1}' -- the witness never fired" -f $lCheck.Pattern, $lCheck.Group) } }
        $lsAgg = if ($lCheck.Agg) { "$($lCheck.Agg)" } else { 'max' }
        $lsRange = Format-Range $lCheck.Min $lCheck.Max
        switch ($lsAgg) {
          'any' { $laIn = @($laValues | Where-Object { Test-Range $_ $lCheck.Min $lCheck.Max }); return @{ Pass = ($laIn.Count -gt 0); Detail = ("{0}/{1} values in {2}; min {3:g5} max {4:g5}" -f $laIn.Count, $laValues.Count, $lsRange, ($laValues | Measure-Object -Minimum).Minimum, ($laValues | Measure-Object -Maximum).Maximum) } }
          'all' { $laOut = @($laValues | Where-Object { -not (Test-Range $_ $lCheck.Min $lCheck.Max) }); return @{ Pass = ($laOut.Count -eq 0); Detail = ("{0}/{1} values OUTSIDE {2}; min {3:g5} max {4:g5}" -f $laOut.Count, $laValues.Count, $lsRange, ($laValues | Measure-Object -Minimum).Minimum, ($laValues | Measure-Object -Maximum).Maximum) } }
          'max'   { $lfAgg = ($laValues | Measure-Object -Maximum).Maximum }
          'min'   { $lfAgg = ($laValues | Measure-Object -Minimum).Minimum }
          'mean'  { $lfAgg = ($laValues | Measure-Object -Average).Average }
          'first' { $lfAgg = $laValues[0] }
          'last'  { $lfAgg = $laValues[-1] }
          default { return @{ Pass = $false; Detail = "unknown Agg '$lsAgg'" } }
        }
        return @{ Pass = (Test-Range $lfAgg $lCheck.Min $lCheck.Max); Detail = ("{0} of {1} value(s) = {2:g6}, want {3}" -f $lsAgg, $laValues.Count, $lfAgg, $lsRange) }
      }
      'Mark' {
        if ($lCheck.Phase) {
          return @{ Pass = ($lCtx.Phase -eq "$($lCheck.Phase)"); Detail = ("final phase {0}, want {1}" -f $lCtx.Phase, $lCheck.Phase) }
        }
        if ($lCheck.Cue) {
          $lMark = $lCtx.Marks["$($lCheck.Cue)"]
          if ($null -eq $lMark) { return @{ Pass = $false; Detail = "no cue '$($lCheck.Cue)' in marks.txt (typo, or flow_run does not know it)" } }
          $lbExpect = if ($null -eq $lCheck.Expect) { $true } else { [bool]$lCheck.Expect }
          $lsWhen = if ($lMark.Fired) { ("fired at {0:f1}s" -f $lMark.Secs) } else { 'never fired' }
          return @{ Pass = ($lMark.Fired -eq $lbExpect); Detail = ("cue '{0}' {1}, expected {2}" -f $lCheck.Cue, $lsWhen, $(if ($lbExpect) { 'fired' } else { 'NOT fired' })) }
        }
        return @{ Pass = $false; Detail = 'Mark check needs Phase or Cue' }
      }
      'Frame' {
        $liOff = if ($null -ne $lCheck.Offset) { [int]$lCheck.Offset } else { 0 }
        $lR = Resolve-FrameAt $lCtx $lCheck.At $liOff
        if ($null -eq $lR.Path) { return @{ Pass = $false; Detail = $lR.Why } }
        $lfV = Invoke-FrameStat $lR.Path $lCheck.Region $lCheck.Stat
        return @{ Pass = (Test-Range $lfV $lCheck.Min $lCheck.Max); Detail = ("{0}({1}) on {2} region {3} = {4:g6}, want {5}" -f $lCheck.Stat, $lCheck.At, (Split-Path $lR.Path -Leaf), $(if ($lCheck.Region) { $lCheck.Region } else { 'full' }), $lfV, (Format-Range $lCheck.Min $lCheck.Max)) }
      }
      'FrameRatio' {
        $liOff = if ($null -ne $lCheck.Offset) { [int]$lCheck.Offset } else { 0 }
        $lR = Resolve-FrameAt $lCtx $lCheck.At $liOff
        if ($null -eq $lR.Path) { return @{ Pass = $false; Detail = $lR.Why } }
        $lfA = Invoke-FrameStat $lR.Path $lCheck.RegionA $lCheck.Stat
        $lfB = Invoke-FrameStat $lR.Path $lCheck.RegionB $lCheck.Stat
        $lfRatio = if ($lfB -ne 0) { $lfA / $lfB } else { [double]::PositiveInfinity }
        return @{ Pass = (Test-Range $lfRatio $lCheck.Min $lCheck.Max); Detail = ("{0} A/B on {1}: {2:g5}/{3:g5} = {4:g5}, want {5}" -f $lCheck.Stat, (Split-Path $lR.Path -Leaf), $lfA, $lfB, $lfRatio, (Format-Range $lCheck.Min $lCheck.Max)) }
      }
      'NewAsserts' {
        $lsKnownPath = if ($lCheck.Known) { "$($lCheck.Known)" } else { Join-Path $script:TestsRoot 'known_asserts.txt' }
        $laKnown = @()
        if (Test-Path $lsKnownPath) { $laKnown = @(Get-Content $lsKnownPath | Where-Object { $_.Trim() -ne '' -and -not $_.StartsWith('#') }) }
        $lFam = @{}
        foreach ($lsLine in $lCtx.LogLines) {
          if ($lsLine -match '^\[ASSERT \d+\]\s*(.*)$') {
            $lsMsg = $Matches[1]
            $lsMsg = $lsMsg -replace '\s*\[repeat.*$', ''
            $lsWhere = ''
            if ($lsMsg -match '\(([^()]*:\d+)\)\s*$') { $lsWhere = $Matches[1] -replace '^.*[\\/]b5-decomp[\\/]', ''; $lsMsg = $lsMsg -replace '\s*\([^()]*:\d+\)\s*$', '' }
            $lsKey = ($lsMsg -replace '\d+', 'N').Trim()
            if (-not $lFam.ContainsKey($lsKey)) { $lFam[$lsKey] = @{ Count = 0; Where = $lsWhere; Sample = $lsMsg.Trim() } }
            $lFam[$lsKey].Count++
            if ($lsWhere -and -not $lFam[$lsKey].Where) { $lFam[$lsKey].Where = $lsWhere }
          }
        }
        $laNew = @()
        $liKnownCount = 0
        foreach ($lsKey in $lFam.Keys) {
          $lbKnown = $false
          foreach ($lsRe in $laKnown) { if ($lFam[$lsKey].Sample -match $lsRe) { $lbKnown = $true; break } }
          if ($lbKnown) { $liKnownCount += $lFam[$lsKey].Count } else { $laNew += $lsKey }
        }
        if ($laNew.Count -eq 0) {
          return @{ Pass = $true; Detail = ("{0} assert family(ies), all known ({1} lines)" -f $lFam.Count, $liKnownCount) }
        }
        $lsList = ($laNew | Sort-Object { -$lFam[$_].Count } | Select-Object -First 6 | ForEach-Object { ("{0}x '{1}' @ {2}" -f $lFam[$_].Count, $lFam[$_].Sample.Substring(0, [Math]::Min(70, $lFam[$_].Sample.Length)), $lFam[$_].Where) }) -join '; '
        return @{ Pass = $false; Detail = ("{0} NEW assert family(ies): {1}" -f $laNew.Count, $lsList) }
      }
      'Script' {
        $lRes = & $lCheck.Script $lCtx
        if ($null -eq $lRes -or $null -eq $lRes.Pass) { return @{ Pass = $false; Detail = 'Script check returned nothing (must return @{Pass=..;Detail=..})' } }
        return @{ Pass = [bool]$lRes.Pass; Detail = "$($lRes.Detail)" }
      }
      default { return @{ Pass = $false; Detail = "unknown check Kind '$lsKind'" } }
    }
  } catch {
    return @{ Pass = $false; Detail = ("check threw: {0}" -f $_.Exception.Message) }
  }
}
