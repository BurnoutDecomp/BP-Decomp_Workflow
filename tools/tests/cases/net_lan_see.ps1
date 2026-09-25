# net_lan_see -- TWO game instances on this box join one online free-burn lobby over the PC LAN
# backend, and each one SEES the other player's car: the lobby game starts on both, each world
# spawns a NETWORK race car for the other player, and car-state update messages flow both ways and
# drive that car to where the other instance's own car actually is.
#
# Run it (a PAIR case -- see net_lan_pair.ps1 for how pair cases work):
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_pair.ps1 -Case net_lan_see
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_pair.ps1 -Case net_lan_see -NoRun -RunDir <pair run dir>
#
# THE SET-UP. Same halves as net_lan_pair (BP_LAN=1, BRN_NET_HOST / BRN_NET_JOIN, BRN_NET_DELAY),
# plus a teleport per half through flow_run's -Teleport (the console place-on-track reset chain),
# done at boot, before the lobby exists -- the lobby start keeps each local car where it is:
#   Host  -> the road outside the junkyard exit, heading 180 (the baseline_boot_drive spot);
#   Guest -> the same road, 25 m further along heading 180 (-Z) and 4.5 m to the side (-X), i.e.
#            ahead of the host car and clear of it, where the host's chase camera looks.
# The Guest DRIVES once the lobby is up (flow_run -Drive through the slot's harness accelerate
# event, 75 s after DRIVING, throttle for 2.5 s), so the host's copy of the guest car has to MOVE.
# The Host half dumps sparse frames (FrameEvery 300 presents) into its run dir's frames\ folder;
# the proof frame is one taken after the "[net] update-in applied" lines start.
#
# THE ORACLE (bounded "[net] ..." witness lines, printed only on a LAN run):
#   [net] game round start -> StartGameMode mode=15 ...     ProcessGameEvents case 18 started the lobby
#   [net] world grid car <n> ... type=2 ...                  the world spawned the other player's car
#     or [net] world network car spawned for net=...         (joiner: at lobby start; host: action 219)
#   [net] update-out sent since=n ... pos=(x, y, z)          this instance's car state went out
#   [net] update-in applied since=n ... pos=(x, y, z)        the other instance's state drove our
#                                                            network car: the FIRST applied position
#                                                            must be the OTHER instance's teleport
#                                                            spot (within 6 m), not our own; on the
#                                                            Host (whose Guest drives) the LAST one
#                                                            must have moved > 8 m down the road
#                                                            (-Z) from it; on the Guest the last
#                                                            one must be a position the Host sent
#                                                            (pair check; traffic can shunt the Host).
param([string]$Role = '')

$lsHostSpot  = '3040.7,-5.8,-1937.9,180'
$lsGuestSpot = '3036.2,-5.8,-1962.9,180'

$lPairRoles = [ordered]@{
  Host  = @{ Other = 'Guest'; Harness = 'BRN_NET_HOST'; Spot = $lsHostSpot;  OtherSpot = $lsGuestSpot; Frames = $true;  Drives = $false; OtherDrives = $true  }
  Guest = @{ Other = 'Host';  Harness = 'BRN_NET_JOIN'; Spot = $lsGuestSpot; OtherSpot = $lsHostSpot;  Frames = $false; Drives = $true;  OtherDrives = $false }
}

# PAIR CHECK: the last position each half applied for the other player's car is a position the
# other half really SENT for its own car (within 1.5 m). This replaces "the Host stays at its
# spot": online traffic runs in the lobby, and a van can shunt the parked Host car.
$lSentMatches = {
  param($p)
  $lRxOut = '\[net\] update-out sent since=\d+ frame=\d+ car=\d+ pos=\(([-0-9.]+), ([-0-9.]+), ([-0-9.]+)\)'
  $lRxIn  = '\[net\] update-in applied since=\d+ from=\S+ car=\d+ snap=\d pos=\(([-0-9.]+), ([-0-9.]+), ([-0-9.]+)\)'
  $lInv = [Globalization.CultureInfo]::InvariantCulture
  $laOut = @()
  foreach ($ls in $p.Halves['Host'].LogLines) { if ($ls -match $lRxOut) { $laOut += ,@([double]::Parse($Matches[1], $lInv), [double]::Parse($Matches[3], $lInv)) } }
  $lLast = $null
  foreach ($ls in $p.Halves['Guest'].LogLines) { if ($ls -match $lRxIn) { $lLast = @([double]::Parse($Matches[1], $lInv), [double]::Parse($Matches[3], $lInv)) } }
  if ($laOut.Count -eq 0 -or $null -eq $lLast) { return @{ Pass = $false; Detail = "host sent $($laOut.Count), guest applied none" } }
  $lfBest = 1e9
  foreach ($lo in $laOut) { $lfD = [Math]::Sqrt(($lo[0] - $lLast[0]) * ($lo[0] - $lLast[0]) + ($lo[1] - $lLast[1]) * ($lo[1] - $lLast[1])); if ($lfD -lt $lfBest) { $lfBest = $lfD } }
  $lHostLast = $laOut[-1]
  return @{ Pass = ($lfBest -le 1.5); Detail = ("guest's last applied Host pos ({0:f1}, {1:f1}) is {2:f1} m from the nearest position the Host sent; Host's last sent ({3:f1}, {4:f1})" -f $lLast[0], $lLast[1], $lfBest, $lHostLast[0], $lHostLast[1]) }
}

if ($Role -eq '') {
  return @{
    Name = 'net_lan_see'
    Area = 'network'
    Bug  = 'none -- LV goal: each of two LAN instances sees the other player''s car, driven by update messages'
    Pair = @{ Roles = @($lPairRoles.Keys); Slots = @(1, 2)
              Checks = @(
                @{ Name = 'the Guest shows the Host car where the Host last sent it'; Script = $lSentMatches }
              ) }
  }
}
if (-not $lPairRoles.Contains($Role)) { throw "net_lan_see: unknown -Role '$Role' (Host or Guest)" }
$lR = $lPairRoles[$Role]
$lsMe = $Role
$lsOther = $lR.Other
$laOther = @($lR.OtherSpot.Split(',') | ForEach-Object { [double]::Parse($_, [Globalization.CultureInfo]::InvariantCulture) })

$lRun = @{
  MaxSeconds = 150
  SkipIntro  = $true
  AcceptGap  = 1.0
  Teleport   = $lR.Spot
}
if ($lR.Frames) { $lRun['FrameEvery'] = 300 }
if ($lR.Drives) {
  $lRun['Drive']          = $true
  $lRun['DriveDelay']     = 75.0
  $lRun['ThrottleScript'] = '0:accel,2.5:none'
}
$lbOtherDrives = $lR.OtherDrives

$lSetup = {
  param($ctx)
  $env:BP_LAN = '1'
  $env:BP_LAN_NAME = $lsMe
  Remove-Item Env:\BP_LAN_XUID -ErrorAction SilentlyContinue
  Write-Host ("[case] {0}: BP_LAN=1 BP_LAN_NAME={0}" -f $lsMe)
  return $null
}.GetNewClosure()

# The network car this instance drives from the other player's updates must sit where the OTHER
# instance put its own car (its teleport spot, x/z within 6 m -- place-on-track snaps to the lane).
$lTrackCheck = {
  param($ctx)
  $lRx = '\[net\] update-in applied since=\d+ from=\S+ car=(\d+) snap=\d pos=\(([-0-9.]+), ([-0-9.]+), ([-0-9.]+)\)'
  $lHits = @($ctx.LogLines | Where-Object { $_ -match $lRx })
  if ($lHits.Count -eq 0) { return @{ Pass = $false; Detail = 'no [net] update applied line' } }
  $laPos = @($lHits | ForEach-Object {
    $null = $_ -match $lRx
    ,@([double]::Parse($Matches[2], [Globalization.CultureInfo]::InvariantCulture),
       [double]::Parse($Matches[4], [Globalization.CultureInfo]::InvariantCulture))
  })
  $lFirst = $laPos[0]; $lLast = $laPos[-1]
  $lfD0 = [Math]::Sqrt(($lFirst[0] - $laOther[0]) * ($lFirst[0] - $laOther[0]) + ($lFirst[1] - $laOther[2]) * ($lFirst[1] - $laOther[2]))
  $lfDLast = [Math]::Sqrt(($lLast[0] - $laOther[0]) * ($lLast[0] - $laOther[0]) + ($lLast[1] - $laOther[2]) * ($lLast[1] - $laOther[2]))
  $lfAlongMinusZ = $lFirst[1] - $lLast[1]
  $lbPass = ($lfD0 -le 6.0)
  # The non-driving side's last position is checked at pair level (see `$lSentMatches).
  if ($lbOtherDrives) { $lbPass = $lbPass -and ($lfAlongMinusZ -gt 8.0) }
  $lsDetail = ("{0} applied lines; first ({1:f1}, {2:f1}) is {3:f1} m from {4}'s spot; last ({5:f1}, {6:f1}) moved {7:f1} m along -Z" -f
               $lHits.Count, $lFirst[0], $lFirst[1], $lfD0, $lsOther, $lLast[0], $lLast[1], $lfAlongMinusZ)
  return @{ Pass = $lbPass; Detail = $lsDetail }
}.GetNewClosure()

$lSpawnCheck = {
  param($ctx)
  $lHits = @($ctx.LogLines | Where-Object {
    $_ -match '\[net\] world grid car \d+ net=\S+ local=0 type=2 ' -or
    $_ -match '\[net\] world network car spawned for net='
  })
  if ($lHits.Count -eq 0) { return @{ Pass = $false; Detail = 'no network race car was spawned' } }
  return @{ Pass = $true; Detail = $lHits[0].Trim() }
}.GetNewClosure()

@{
  Name    = "net_lan_see_$Role"
  Area    = 'network'
  Bug     = "none -- the $Role half of net_lan_see (run it through tools\tests\run_pair.ps1)"
  Frames  = $lR.Frames
  Run     = $lRun
  DiagEnv = "$($lR.Harness)=1,BRN_NET_DELAY=30"
  Setup   = $lSetup
  Checks  = @(
    @{ Kind = 'LogCount'; Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';     Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'LogMatch'; Name = 'the lobby game started (case 18 -> StartGameMode mode 15)'; Pattern = '\[net\] game round start -> StartGameMode mode=15'; Expect = $true }
    @{ Kind = 'Script';   Name = "a network race car was spawned for $lsOther"; Script = $lSpawnCheck }
    @{ Kind = 'LogMatch'; Name = 'update messages sent'; Pattern = '\[net\] update-out sent since=\d+'; Expect = $true }
    @{ Kind = 'Script';   Name = "received updates drive $lsOther's car where $lsOther is"; Script = $lTrackCheck }
  )
}
