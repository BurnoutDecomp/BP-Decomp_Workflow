# _net_pair_common.ps1 -- shared pieces of the net_* pair cases. Dot-sourced by a case file; it is
# NOT a case (it lives outside cases\ so run_all never picks it up).
#
# Everything is a VARIABLE, not a function: a case's Script checks are closures
# (.GetNewClosure()), and a closure captures variables but not functions, while run_case invokes
# the checks long after the case file's own scope is gone. So a case captures $NetPair and calls
# `& $NetPair.Ordered ...` etc.
#
#   $NetPair.Spots          Host / Guest teleports of the net_lan_see shape (Host at the junkyard exit
#                           heading 180; Guest 25 m ahead, 4.5 m to the side, where the Host's chase
#                           camera looks)
#   $NetPair.Setup          scriptblock factory: & $NetPair.Setup '<name>' -> the half's Setup
#                           (BP_LAN=1, BP_LAN_NAME=<name>, BP_LAN_XUID cleared)
#   $NetPair.Ordered        & $NetPair.Ordered $lines @('rx1','rx2',...) -> @{ Pass; Detail; Index }
#                           every regex matches a line AFTER the previous one's match
#   $NetPair.First          & $NetPair.First $lines 'rx' [$from] -> index of the first match at/after $from, or -1
#   $NetPair.States         & $NetPair.States $lines -> the harness "[net] state" lines as objects
#                           { Index; T; Wall; LoggedIn; InGame; Host; Players }
#   $NetPair.WallTime       & $NetPair.WallTime 'HH:MM:SS.mmm' <reference DateTime> -> DateTime that day
#   $NetPair.FramesAround   & $NetPair.FramesAround <frameDir> <DateTime> <secBefore> <secAfter>
#                           -> @{ Before = <FileInfo|null>; After = <FileInfo|null> } by file time
#   $NetPair.FrameStat      & $NetPair.FrameStat <bmp> '<x0,y0,x1,y1>' 'lum_mean' -> [double]
#   $NetPair.Spawned        & $NetPair.Spawned $lines -> @{ Pass; Detail } a NETWORK race car was spawned
#   $NetPair.CarGoneFrame   & $NetPair.CarGoneFrame $ctx <DateTime of the leave> -> @{ Pass; Detail }
#                           the Host frame check of the leave cases (see its banner)
#   $NetPair.CarGoneLog     & $NetPair.CarGoneLog $lines -> @{ Pass; Detail } the network car was drawn
#                           before '[net] world ... removed' and never reported after it
$NetPair = @{}
$NetPair.Spots = @{ Host = '3040.7,-5.8,-1937.9,180'; Guest = '3036.2,-5.8,-1962.9,180' }
$NetPair.StatsPy = Join-Path $PSScriptRoot 'frame_stats.py'

$NetPair.Setup = {
  param([string]$lsName)
  return {
    param($ctx)
    $env:BP_LAN = '1'
    $env:BP_LAN_NAME = $lsName
    Remove-Item Env:\BP_LAN_XUID -ErrorAction SilentlyContinue
    Write-Host ("[case] {0}: BP_LAN=1 BP_LAN_NAME={0}" -f $lsName)
    return $null
  }.GetNewClosure()
}

$NetPair.First = {
  param($laLines, [string]$lsRx, [int]$liFrom = 0)
  for ($i = [Math]::Max(0, $liFrom); $i -lt $laLines.Count; $i++) { if ($laLines[$i] -match $lsRx) { return $i } }
  return -1
}

$NetPair.Ordered = {
  param($laLines, [string[]]$laRx)
  $liFrom = 0
  $laHit = @()
  foreach ($lsRx in $laRx) {
    $liAt = -1
    for ($i = $liFrom; $i -lt $laLines.Count; $i++) { if ($laLines[$i] -match $lsRx) { $liAt = $i; break } }
    if ($liAt -lt 0) {
      $lsMissing = $(if ($laHit.Count -gt 0) { "after line $liFrom" } else { 'anywhere' })
      return @{ Pass = $false; Index = -1; Detail = ("no line matches /{0}/ {1}{2}" -f $lsRx, $lsMissing,
                $(if ($laHit.Count -gt 0) { " (had: " + ($laHit -join ' | ') + ")" } else { '' })) }
    }
    $laHit += $laLines[$liAt].Trim()
    $liFrom = $liAt + 1
  }
  return @{ Pass = $true; Index = $liFrom - 1; Detail = ($laHit -join ' | ') }
}

$NetPair.States = {
  param($laLines)
  $lRx = '\[net\] state t=([0-9.]+)s wall=([0-9:.]+) loggedIn=(\d) inGame=(\d) host=(\d) players=(\d+)'
  $laOut = @()
  for ($i = 0; $i -lt $laLines.Count; $i++) {
    if ($laLines[$i] -match $lRx) {
      $laOut += [pscustomobject]@{ Index = $i; T = [double]::Parse($Matches[1], [Globalization.CultureInfo]::InvariantCulture)
                                   Wall = $Matches[2]; LoggedIn = [int]$Matches[3]; InGame = [int]$Matches[4]
                                   Host = [int]$Matches[5]; Players = [int]$Matches[6] }
    }
  }
  return ,$laOut
}

$NetPair.WallTime = {
  param([string]$lsWall, [datetime]$lRef)
  $lTod = [TimeSpan]::ParseExact($lsWall, 'hh\:mm\:ss\.fff', [Globalization.CultureInfo]::InvariantCulture)
  $lWhen = $lRef.Date + $lTod
  # a run that crossed midnight: pick the day that puts the stamp nearest the reference
  if (($lWhen - $lRef).TotalHours -gt 12) { $lWhen = $lWhen.AddDays(-1) }
  if (($lRef - $lWhen).TotalHours -gt 12) { $lWhen = $lWhen.AddDays(1) }
  return $lWhen
}

$NetPair.FramesAround = {
  param([string]$lsFrameDir, [datetime]$lWhen, [double]$lfBefore, [double]$lfAfter)
  $laFrames = @()
  if ($lsFrameDir -and (Test-Path $lsFrameDir)) { $laFrames = @(Get-ChildItem $lsFrameDir -Filter 'bb_*.bmp' | Sort-Object LastWriteTime) }
  $lBefore = @($laFrames | Where-Object { $_.LastWriteTime -le $lWhen.AddSeconds(-$lfBefore) }) | Select-Object -Last 1
  $lAfter  = @($laFrames | Where-Object { $_.LastWriteTime -ge $lWhen.AddSeconds($lfAfter) }) | Select-Object -First 1
  return @{ Before = $lBefore; After = $lAfter; Count = $laFrames.Count }
}

$NetPair.FrameStat = {
  param([string]$lsFrame, [string]$lsRegion, [string]$lsStat)
  $lsOut = & py -3 $NetPair.StatsPy $lsFrame --stat $lsStat --region $lsRegion 2>&1
  if ($LASTEXITCODE -ne 0) { throw "frame_stats.py failed on ${lsFrame}: $lsOut" }
  return [double]::Parse(("$lsOut".Trim()), [Globalization.CultureInfo]::InvariantCulture)
}

$NetPair.Spawned = {
  param($laLines)
  $laHits = @($laLines | Where-Object {
    $_ -match '\[net\] world grid car \d+ net=\S+ local=0 type=2 ' -or $_ -match '\[net\] world network car spawned for net='
  })
  if ($laHits.Count -eq 0) { return @{ Pass = $false; Detail = 'no network race car was spawned' } }
  return @{ Pass = $true; Detail = $laHits[0].Trim() }
}

# ⭐ THE HOST FRAME ORACLE OF THE LEAVE CASES (calibrated 2026-09-24 on the LV_proof pair of
#   net_lan_see run 091434, host frames 4800 "guest parked" and 5400 "guest driven away"):
#   with the Host at its spot and the Guest parked at its spot, the Guest's car sits in the Host's
#   frame at pixels 512,355..575,388. That region's mean luminance was 72.8 with the car there and
#   95.0 once it had gone; two road/building control regions moved by less than 1.5 between the
#   same two frames. So: the frame >= 1 s BEFORE the leave and the frame >= 6 s AFTER it (the
#   removal has to travel lobby refresh -> event 129 -> action 220 -> world) must differ by
#   >= 12 in the car region while the road control 680,352..760,380 moves by <= 6. A dead car left
#   in the world (today's behaviour) keeps the car region dark and FAILS.
#   ⚠ Valid only while neither car moves between the two frames (neither half drives before the leave).
$NetPair.CarGoneFrame = {
  param($ctx, [datetime]$lLeave)
  $lsCar = '512,355,575,388'; $lsCtl = '680,352,760,380'
  $lF = & $NetPair.FramesAround $ctx.FrameDir $lLeave 1.0 6.0
  if ($lF.Count -eq 0) { return @{ Pass = $false; Detail = "no frames in $($ctx.FrameDir)" } }
  if ($null -eq $lF.Before -or $null -eq $lF.After) {
    return @{ Pass = $false; Detail = ("no frame {0} the leave at {1:HH:mm:ss.fff} ({2} frames)" -f
              $(if ($null -eq $lF.Before) { 'before' } else { 'after' }), $lLeave, $lF.Count) }
  }
  $lfCarB = & $NetPair.FrameStat $lF.Before.FullName $lsCar 'lum_mean'
  $lfCarA = & $NetPair.FrameStat $lF.After.FullName $lsCar 'lum_mean'
  $lfCtlB = & $NetPair.FrameStat $lF.Before.FullName $lsCtl 'lum_mean'
  $lfCtlA = & $NetPair.FrameStat $lF.After.FullName $lsCtl 'lum_mean'
  $lbPass = (($lfCarA - $lfCarB) -ge 12.0) -and ([Math]::Abs($lfCtlA - $lfCtlB) -le 6.0)
  return @{ Pass = $lbPass; Detail = ("{0} -> {1}: car region lum {2:f1} -> {3:f1} (need +12), road control {4:f1} -> {5:f1} (need |d|<=6)" -f
            $lF.Before.Name, $lF.After.Name, $lfCarB, $lfCarA, $lfCtlB, $lfCtlA) }
}

# The leave cases' camera-independent oracle, from the '[net] netcar present=...' witness (every
# attached NETWORK car slot, once per 150 presents, render=<drawn this frame>): the last line before
# '[net] world ... removed' says render=1, and no netcar line follows the removal. The witness is
# bounded (24 lines per site); a run that spent the budget before the removal proves nothing.
# (The frame check stays for the screenshots: online traffic can shunt the parked Host, which
# moves the camera off the region the frame check measures.)
$NetPair.CarGoneLog = {
  param($laLines)
  $liRemoved = & $NetPair.First $laLines '\[net\] world .*removed'
  if ($liRemoved -lt 0) { return @{ Pass = $false; Detail = 'no [net] world ... removed line' } }
  $laBefore = @(); $laAfter = @()
  for ($i = 0; $i -lt $laLines.Count; $i++) {
    if ($laLines[$i] -match '\[net\] netcar present=') { if ($i -lt $liRemoved) { $laBefore += $laLines[$i] } else { $laAfter += $laLines[$i] } }
  }
  if ($laBefore.Count -eq 0) { return @{ Pass = $false; Detail = 'no netcar line before the removal' } }
  if (($laBefore.Count + $laAfter.Count) -ge 24) { return @{ Pass = $false; Detail = "netcar witness budget spent ($($laBefore.Count + $laAfter.Count) lines): absence proves nothing" } }
  $lsLast = $laBefore[-1].Trim()
  $lbDrawn = $lsLast -match 'render=1'
  return @{ Pass = ($lbDrawn -and $laAfter.Count -eq 0); Detail = ("last before removal: '{0}'; {1} netcar line(s) after it" -f $lsLast, $laAfter.Count) }
}

# Bind every helper to $NetPair (a closure captures the variable, i.e. this same hashtable), so a
# helper that calls another one works wherever run_case invokes it.
foreach ($lsKey in @($NetPair.Keys)) {
  if ($NetPair[$lsKey] -is [scriptblock]) { $NetPair[$lsKey] = $NetPair[$lsKey].GetNewClosure() }
}
