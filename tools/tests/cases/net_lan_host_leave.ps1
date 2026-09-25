# net_lan_host_leave -- the HOST leaves the online free-burn lobby and the game goes on: the remaining
# player takes the lobby record over (PC LAN host handover) instead of being thrown back offline,
# and removes the old host's car.
#
# Run it (a PAIR case -- see net_lan_pair.ps1 for how pair cases work):
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_pair.ps1 -Case net_lan_host_leave
#
# WHY. On the console the lobby server keeps a game whose host leaves and moves it to another
# player; the games component sees a 'game' record whose HOST changed and the game manager migrates
# ConnApi. On PC the lobby record lives in the host process (pclan_lobby.cpp), and until wave 3 its
# leave path sent PCLAN_KICK NOGAME to every member, i.e. "the host leaves" == "the game ends for
# everyone". The wave-3 handover names the next host (the first remaining player of the record) in
# a PCLAN_HANDOVER; that member takes the record over and publishes it with HOST changed.
#
# THE SET-UP. The net_lan_see halves, with the leave on the HOST: BRN_NET_LEAVE_AT=30 there (GUI 52
# 30 s after it is first seen in its own lobby, the record the game room's leave overlay posts).
# The Guest stays and dumps frames every 300 presents.
#
# THE ORACLE
#   Guest  [net] pclan_lobby: host handover: took over game ...   the member took the record over
#          [net] state ... inGame=1 host=1 players=1 after the leave     still online, now the host
#          no "[net] harness ... left the game"                         never dropped out
#          [net] game player removed ...                                case 129 for the old host (lane GS)
#          [net] world ... removed ...                                  its car removed (lane NC)
#   Host   [net] harness ... post 52 leave game, [net] pclan_lobby: host handover: leaving ...
#          [net] state ... inGame=0 after it, [net] game local left ... (lane GS)
# RED: the a352bef0 exe has neither BRN_NET_LEAVE_AT nor the handover; a build with the harness but
# the old pclan_lobby.cpp kicks the Guest (inGame=0, no handover line).
param([string]$Role = '')
. (Join-Path $PSScriptRoot '..\_net_pair_common.ps1')

$lPairRoles = [ordered]@{
  Host  = @{ Other = 'Guest'; Harness = 'BRN_NET_HOST=1,BRN_NET_LEAVE_AT=30'; Spot = $NetPair.Spots.Host;  Frames = $true }
  Guest = @{ Other = 'Host';  Harness = 'BRN_NET_JOIN=1'; Spot = $NetPair.Spots.Guest; Frames = $true }
}

if ($Role -eq '') {
  return @{
    Name = 'net_lan_host_leave'
    Area = 'network'
    Bug  = 'wave 3 -- the host leaving must hand the lobby to the remaining player, not end the game'
    Pair = @{ Roles = @($lPairRoles.Keys); Slots = @(1, 2) }
  }
}
if (-not $lPairRoles.Contains($Role)) { throw "net_lan_host_leave: unknown -Role '$Role' (Host or Guest)" }
$lR = $lPairRoles[$Role]
$lsOther = $lR.Other

$lRun = @{ MaxSeconds = 150; SkipIntro = $true; AcceptGap = 1.0; Teleport = $lR.Spot }
if ($lR.Frames) { $lRun['FrameEvery'] = 300 }

$lChecks = @(
  @{ Kind = 'LogCount'; Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
  @{ Kind = 'Mark';     Name = 'reached DRIVING'; Phase = 'DRIVING' }
  @{ Kind = 'LogMatch'; Name = 'the lobby game started (mode 15)'; Pattern = '\[net\] game round start -> StartGameMode mode=15'; Expect = $true }
  @{ Kind = 'Script';   Name = "a network race car was spawned for $lsOther"; Script = { param($ctx) & $NetPair.Spawned $ctx.LogLines }.GetNewClosure() }
)

if ($Role -eq 'Guest') {
  $lTookOver = {
    param($ctx)
    $laS = & $NetPair.States $ctx.LogLines
    $l2 = @($laS | Where-Object { $_.InGame -eq 1 -and $_.Players -ge 2 }) | Select-Object -First 1
    if ($null -eq $l2) { return @{ Pass = $false; Detail = 'never saw the Host in the lobby ([net] state players>=2)' } }
    $lAfter = @($laS | Where-Object { $_.Index -gt $l2.Index })
    $lOut = @($lAfter | Where-Object { $_.InGame -eq 0 }) | Select-Object -First 1
    $lNew = @($lAfter | Where-Object { $_.InGame -eq 1 -and $_.Host -eq 1 -and $_.Players -eq 1 }) | Select-Object -First 1
    if ($null -ne $lOut -and ($null -eq $lNew -or $lOut.Index -lt $lNew.Index)) {
      return @{ Pass = $false; Detail = "dropped out of the game: '$($ctx.LogLines[$lOut.Index].Trim())'" }
    }
    if ($null -eq $lNew) { return @{ Pass = $false; Detail = 'never became the host of a 1-player game after the Host left' } }
    return @{ Pass = $true; Detail = $ctx.LogLines[$lNew.Index].Trim() }
  }.GetNewClosure()
  $lChecks += @(
    @{ Kind = 'LogMatch'; Name = 'PC LAN: this member took the lobby record over'; Pattern = '\[net\] pclan_lobby: host handover: took over game'; Expect = $true }
    @{ Kind = 'Script';   Name = 'still in the game, now as its host'; Script = $lTookOver }
    @{ Kind = 'LogMatch'; Name = 'the harness never saw this instance leave the game'; Pattern = '\[net\] harness t=\S+ left the game'; Expect = $false }
    @{ Kind = 'LogMatch'; Name = 'game: the old host''s removal reached GameState (case 129)'; Pattern = '\[net\] game player removed'; Expect = $true }
    @{ Kind = 'LogMatch'; Name = 'world: the old host''s network car was removed'; Pattern = '\[net\] world .*removed'; Expect = $true }
  )
} else {
  $lLeftCheck = {
    param($ctx)
    return & $NetPair.Ordered $ctx.LogLines @('\[net\] harness t=\S+ wall=\S+ post 52 leave game', '\[net\] pclan_lobby: host handover: leaving', '\[net\] state t=\S+ wall=\S+ loggedIn=\d inGame=0')
  }.GetNewClosure()
  $lChecks += @(
    @{ Kind = 'Script';   Name = 'the host left through a handover, not a kick'; Script = $lLeftCheck }
    @{ Kind = 'LogMatch'; Name = 'game: the local leave reached GameState (case 124)'; Pattern = '\[net\] game local left'; Expect = $true }
  )
}

@{
  Name    = "net_lan_host_leave_$Role"
  Area    = 'network'
  Bug     = "wave 3 -- the $Role half of net_lan_host_leave (run it through tools\tests\run_pair.ps1)"
  Frames  = $lR.Frames
  Run     = $lRun
  DiagEnv = "$($lR.Harness),BRN_NET_DELAY=30"
  Setup   = (& $NetPair.Setup $Role)
  Checks  = $lChecks
}
