# net_lan_leave -- a player LEAVES the online free-burn lobby without any UI, and the other instance
# REMOVES that player's car; the leaver drops back to offline free roam and can still drive.
#
# Run it (a PAIR case -- see net_lan_pair.ps1 for how pair cases work):
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_pair.ps1 -Case net_lan_leave
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_pair.ps1 -Case net_lan_leave -NoRun -RunDir <pair run dir>
#
# THE SET-UP. The net_lan_see halves (BP_LAN=1, BRN_NET_HOST / BRN_NET_JOIN, BRN_NET_DELAY=30, the
# Host at the junkyard exit and the Guest parked 25 m ahead of it, in the Host's view), plus:
#   Guest  BRN_NET_LEAVE_AT=30: 30 s after the Guest is first seen in the lobby, the PC harness posts
#          GUI event 52 -- the record the game room's leave overlay posts on Accept -- into the network
#          GUI queue (BrnNetHarnessPC.cpp). Nothing else is forged: StateManager case 52 ->
#          MatchMakingManager LEAVE_GAME -> 'glea' -> PCLAN_LEAVE to the Host, and the Guest's own
#          chain 46 / net 24 -> game event 124 as on the console.
#          -MotionProbe + a throttle 95 s after DRIVING (well after the leave): the leaver still drives.
#   Host   stays parked. Both halves dump frames every 300 presents (the Host's are the before /
#          after proof frames, the Guest's show it back in free roam).
#
# THE ORACLE
#   Host   [net] state ... players=2 then ... players=1       the lobby record dropped the Guest (PC LAN)
#          [net] game player removed ...                         ProcessGameEvents case 129 -> action 220 (lane GS)
#          [net] world ... removed ...                           RaceCarEntityModule action 220 arm (lane NC)
#          the Guest's car is GONE from the Host's world          $NetPair.CarGoneLog (netcar witness; the
#                                                                 frame check rides along as info: traffic
#                                                                 can shunt the parked Host's camera)
#   Guest  [net] harness ... post 52 leave game                  the stimulus happened
#          [net] state ... inGame=0 after it                     the lobby membership ended
#          [net] game local left ...                             case 124 -> UserCancelCurrentMode (lane GS/MM/FB)
#          [net] world ... removed ...                           action 41 -> RemoveAllNetworkCarsFromWorld (lane NC)
#          [motion] after the leave covers > 8 m                 the leaver still drives
# RED: on the a352bef0 exe the harness has no BRN_NET_LEAVE_AT (no stimulus at all, run
# scratch\bugtest\runs\net_lan_leave\20260924_215324); on a build with the wave-3 harness but without
# the GS/NC arms the lobby drop passes and the game/world lines and the frame fail.
param([string]$Role = '')
. (Join-Path $PSScriptRoot '..\_net_pair_common.ps1')

$lPairRoles = [ordered]@{
  Host  = @{ Other = 'Guest'; Harness = 'BRN_NET_HOST=1'; Spot = $NetPair.Spots.Host;  Frames = $true;  Leaves = $false }
  Guest = @{ Other = 'Host';  Harness = 'BRN_NET_JOIN=1,BRN_NET_LEAVE_AT=30'; Spot = $NetPair.Spots.Guest; Frames = $true;  Leaves = $true }
}

if ($Role -eq '') {
  return @{
    Name = 'net_lan_leave'
    Area = 'network'
    Bug  = 'wave 3 -- a player leaving the online lobby must disappear from the other instance (UI-free leave)'
    Pair = @{ Roles = @($lPairRoles.Keys); Slots = @(1, 2) }
  }
}
if (-not $lPairRoles.Contains($Role)) { throw "net_lan_leave: unknown -Role '$Role' (Host or Guest)" }
$lR = $lPairRoles[$Role]
$lsOther = $lR.Other

$lRun = @{ MaxSeconds = 150; SkipIntro = $true; AcceptGap = 1.0; Teleport = $lR.Spot }
if ($lR.Frames) { $lRun['FrameEvery'] = 300 }
if ($lR.Leaves) {
  $lRun['Drive']          = $true
  $lRun['DriveDelay']     = 95.0
  $lRun['ThrottleScript'] = '0:accel,4:none'
  $lRun['MotionProbe']    = $true
}

$lChecks = @(
  @{ Kind = 'LogCount'; Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
  @{ Kind = 'Mark';     Name = 'reached DRIVING'; Phase = 'DRIVING' }
  @{ Kind = 'LogMatch'; Name = 'the lobby game started (mode 15)'; Pattern = '\[net\] game round start -> StartGameMode mode=15'; Expect = $true }
  @{ Kind = 'Script';   Name = "a network race car was spawned for $lsOther"; Script = { param($ctx) & $NetPair.Spawned $ctx.LogLines }.GetNewClosure() }
)

if ($Role -eq 'Host') {
  $lDropCheck = {
    param($ctx)
    $laS = & $NetPair.States $ctx.LogLines
    $l2 = @($laS | Where-Object { $_.InGame -eq 1 -and $_.Players -ge 2 }) | Select-Object -First 1
    if ($null -eq $l2) { return @{ Pass = $false; Detail = 'never saw the Guest in the lobby ([net] state players>=2)' } }
    $l1 = @($laS | Where-Object { $_.Index -gt $l2.Index -and $_.InGame -eq 1 -and $_.Players -eq 1 }) | Select-Object -First 1
    if ($null -eq $l1) { return @{ Pass = $false; Detail = "players stayed >= 2 after '$($ctx.LogLines[$l2.Index].Trim())'" } }
    return @{ Pass = $true; Detail = ("players 2 at t={0}s -> 1 at t={1}s wall={2}" -f $l2.T, $l1.T, $l1.Wall) }
  }.GetNewClosure()
  $lFrameCheck = {
    param($ctx)
    $laS = & $NetPair.States $ctx.LogLines
    $l2 = @($laS | Where-Object { $_.InGame -eq 1 -and $_.Players -ge 2 }) | Select-Object -First 1
    $l1 = if ($l2) { @($laS | Where-Object { $_.Index -gt $l2.Index -and $_.InGame -eq 1 -and $_.Players -eq 1 }) | Select-Object -First 1 } else { $null }
    if ($null -eq $l1) { return @{ Pass = $false; Detail = 'no lobby drop to time the frames against' } }
    $lRef = (Get-Item $ctx.Log).LastWriteTime
    $lFrame = & $NetPair.CarGoneFrame $ctx (& $NetPair.WallTime $l1.Wall $lRef)
    $lLog   = & $NetPair.CarGoneLog $ctx.LogLines
    return @{ Pass = $lLog.Pass; Detail = ("{0} | frames (info): {1}" -f $lLog.Detail, $lFrame.Detail) }
  }.GetNewClosure()
  $lChecks += @(
    @{ Kind = 'Script';   Name = 'the lobby record dropped the Guest (players 2 -> 1)'; Script = $lDropCheck }
    @{ Kind = 'LogMatch'; Name = 'game: the removed player reached GameState (case 129 -> action 220)'; Pattern = '\[net\] game player removed'; Expect = $true }
    @{ Kind = 'LogMatch'; Name = 'world: the Guest''s network car was removed'; Pattern = '\[net\] world .*removed'; Expect = $true }
    @{ Kind = 'Script';   Name = 'the Guest''s car is gone from the Host''s world'; Script = $lFrameCheck }
  )
} else {
  $lLeftCheck = {
    param($ctx)
    return & $NetPair.Ordered $ctx.LogLines @('\[net\] harness t=\S+ wall=\S+ post 52 leave game', '\[net\] state t=\S+ wall=\S+ loggedIn=\d inGame=0')
  }.GetNewClosure()
  $lDrivesCheck = {
    param($ctx)
    $liLeave = & $NetPair.First $ctx.LogLines '\[net\] harness t=\S+ wall=\S+ post 52 leave game'
    if ($liLeave -lt 0) { return @{ Pass = $false; Detail = 'no leave was posted' } }
    $lRx = '\[motion\] n \d+ pos (-?[0-9.]+) (-?[0-9.]+) (-?[0-9.]+)'
    $laP = @()
    for ($i = $liLeave; $i -lt $ctx.LogLines.Count; $i++) {
      if ($ctx.LogLines[$i] -match $lRx) { $laP += ,@([double]::Parse($Matches[1], [Globalization.CultureInfo]::InvariantCulture), [double]::Parse($Matches[3], [Globalization.CultureInfo]::InvariantCulture)) }
    }
    if ($laP.Count -lt 2) { return @{ Pass = $false; Detail = "only $($laP.Count) [motion] sample(s) after the leave" } }
    $lfMax = 0.0
    foreach ($lp in $laP) { $lfD = [Math]::Sqrt(($lp[0] - $laP[0][0]) * ($lp[0] - $laP[0][0]) + ($lp[1] - $laP[0][1]) * ($lp[1] - $laP[0][1])); if ($lfD -gt $lfMax) { $lfMax = $lfD } }
    return @{ Pass = ($lfMax -gt 8.0); Detail = ("{0} [motion] samples after the leave; the car got {1:f1} m from where it was" -f $laP.Count, $lfMax) }
  }.GetNewClosure()
  $lChecks += @(
    @{ Kind = 'Script';   Name = 'the harness leave was posted and the lobby membership ended'; Script = $lLeftCheck }
    @{ Kind = 'LogMatch'; Name = 'game: the local leave reached GameState (case 124 -> cancel the lobby mode)'; Pattern = '\[net\] game local left'; Expect = $true }
    @{ Kind = 'LogMatch'; Name = 'world: the Host''s network car was dropped (action 41)'; Pattern = '\[net\] world .*removed'; Expect = $true }
    @{ Kind = 'Script';   Name = 'the leaver still drives in free roam'; Script = $lDrivesCheck }
  )
}

@{
  Name    = "net_lan_leave_$Role"
  Area    = 'network'
  Bug     = "wave 3 -- the $Role half of net_lan_leave (run it through tools\tests\run_pair.ps1)"
  Frames  = $lR.Frames
  Run     = $lRun
  DiagEnv = "$($lR.Harness),BRN_NET_DELAY=30"
  Setup   = (& $NetPair.Setup $Role)
  Checks  = $lChecks
}
