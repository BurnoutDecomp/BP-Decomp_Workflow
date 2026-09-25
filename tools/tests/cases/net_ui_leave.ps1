# net_ui_leave -- a player leaves the online free-burn lobby THROUGH THE REAL MENU: Easy Drive ->
# Leave game -> the "leave the game?" overlay -> Accept; the other instance removes the car.
#
# Run it (a PAIR case -- see net_lan_pair.ps1 for how pair cases work):
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_pair.ps1 -Case net_ui_leave
#
# THE JOIN IS THE HARNESS'S (BRN_NET_HOST / BRN_NET_JOIN, the net_lan_see shape) ON PURPOSE: the
# case measures the LEAVE through the UI, so it must not also depend on the UI join lanes
# (CN_ENTER_ON / ON_QWK_MAT / ON_CREATE_FB). net_ui_join proves the join; this proves the leave.
# The hybrid join already lands both instances in ON_GAME_ROOM (InGame case 93 posts ENTER_GAME).
#
# THE MENU PATH (Guest; console chain in scratch\net_wave3\MAP_UI_JOIN_LEAVE.md s.1b):
#   in the lobby, Easy Drive's ONLINE list: non-host [0 FRIENDS, 1?, 12, 18, 20, 13 LEAVE_GAME],
#   host [0, 15?, 1, 10, 19?, (11), 12, 18, 20, 13]; LEAVE_GAME is ALWAYS the last row and the list
#   does not wrap (BrnFriendsList.cpp SelectNext), so: open, wait until the panel takes a DPadDown
#   (tapuntil ... selected 1), 12 more DPadDowns (the bottom), DPadRight -> internal GUI 283
#   {4 LEAVE_GAME} -> ON_GAME_ROOM PerformPauseOption(4) -> HandleLeaveGameRequest -> overlay
#   "CNOnlLvGmQn" -> Accept -> HandleOverlayComplete posts GUI 52 -> StateManager leave -> 53 -> 46
#   -> 273 -> HandleLeftGameEvent -> back to INGAME; game event 124 cancels the lobby mode.
# The overlay has no log line of its own (a [netui] overlay witness is requested from lane UB in
# CONTRACTS.md); the script waits 3 s for it and taps Accept.
#
# THE ORACLE
#   Guest  the menu script ran to its end ("left" mark: [net] state ... inGame=0 was seen)
#          before the DPadRight the view was on the LAST row ("selected <count-1> ... count <count>")
#          [net] state ... inGame=0 after the Easy Drive selection, WITHOUT a harness post 52
#          [screen] ENTER 'INGAME' (from 'ON_GAME_ROOM')          the game room let go (lane UB)
#          [net] game local left ...                                case 124 (lane GS)
#   Host   the lobby record dropped the Guest, [net] game player removed, [net] world ... removed,
#          and the Guest's car is gone from the Host's frame (as net_lan_leave)
param([string]$Role = '')
. (Join-Path $PSScriptRoot '..\_net_pair_common.ps1')

$lsLeaveScript = 'timeout:150;wait:\[net\] (state t=\S+ wall=\S+ loggedIn=1 inGame=1 host=\d players=2|harness t=\S+ players in game=2);timeout:0;sleep:20;' +
                 'tapuntil:DPadRight:\[easydrive-view\] panel 1 list 2\b;' +
                 'tapuntil:DPadDown:\[easydrive-view\] panel \d+ list 2 branch 0 selected 1\b;' +
                 'gap:0.4;tap:DPadDown x12;sleep:1;mark:at-bottom;tap:DPadRight;sleep:3;tap:Accept;' +
                 'timeout:60;wait:\[net\] (state t=\S+ wall=\S+ loggedIn=\d inGame=0|harness t=\S+ left the game);mark:left'

$lPairRoles = [ordered]@{
  Host  = @{ Other = 'Guest'; Harness = 'BRN_NET_HOST=1'; Spot = $NetPair.Spots.Host;  Frames = $true;  Script = '' }
  Guest = @{ Other = 'Host';  Harness = 'BRN_NET_JOIN=1'; Spot = $NetPair.Spots.Guest; Frames = $true;  Script = $lsLeaveScript }
}

if ($Role -eq '') {
  return @{
    Name = 'net_ui_leave'
    Area = 'network'
    Bug  = 'wave 3 -- Easy Drive -> Leave game takes the player out of the lobby and off the other instance'
    Pair = @{ Roles = @($lPairRoles.Keys); Slots = @(1, 2) }
  }
}
if (-not $lPairRoles.Contains($Role)) { throw "net_ui_leave: unknown -Role '$Role' (Host or Guest)" }
$lR = $lPairRoles[$Role]
$lsOther = $lR.Other

$lRun = @{ MaxSeconds = 170; SkipIntro = $true; AcceptGap = 1.0; Teleport = $lR.Spot; FrameEvery = 300 }
if ($lR.Script) { $lRun['MenuScript'] = $lR.Script }

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
    if ($null -eq $l1) { return @{ Pass = $false; Detail = 'players stayed >= 2: the Guest never left the lobby record' } }
    $lGone = & $NetPair.CarGoneFrame $ctx (& $NetPair.WallTime $l1.Wall (Get-Item $ctx.Log).LastWriteTime)
    return @{ Pass = $lGone.Pass; Detail = ("players 2 -> 1 at wall={0}; {1}" -f $l1.Wall, $lGone.Detail) }
  }.GetNewClosure()
  $lChecks += @(
    @{ Kind = 'LogMatch'; Name = 'game: the removed player reached GameState (case 129 -> action 220)'; Pattern = '\[net\] game player removed'; Expect = $true }
    @{ Kind = 'LogMatch'; Name = 'world: the Guest''s network car was removed'; Pattern = '\[net\] world .*removed'; Expect = $true }
    @{ Kind = 'Script';   Name = 'the Guest left the lobby record and its car is gone from the Host''s frame'; Script = $lDropCheck }
  )
} else {
  $lScriptDone = {
    param($ctx)
    if ($ctx.MarksText -match 'MENUSCRIPT done=(\d+)/(\d+) state=(\S+)(.*)') { return @{ Pass = ($Matches[1] -eq $Matches[2]); Detail = $Matches[0].Trim() } }
    return @{ Pass = $false; Detail = 'marks.txt has no MENUSCRIPT line' }
  }
  $lBottomCheck = {
    param($ctx)
    $lRx = '\[easydrive-view\] panel \d+ list 2 branch 0 selected (\d+) row \d+ count (\d+)'
    $laV = @($ctx.LogLines | Where-Object { $_ -match $lRx })
    if ($laV.Count -eq 0) { return @{ Pass = $false; Detail = 'no Easy Drive list view line' } }
    $null = $laV[-1] -match $lRx
    $liSel = [int]$Matches[1]; $liCount = [int]$Matches[2]
    return @{ Pass = ($liCount -gt 0 -and $liSel -eq $liCount - 1); Detail = ("last view: selected {0} of {1} rows ({2})" -f $liSel, $liCount, $laV[-1].Trim()) }
  }
  $lLeftCheck = {
    param($ctx)
    $lR1 = & $NetPair.Ordered $ctx.LogLines @('\[easydrive-view\] panel \d+ list 2 branch 0 selected', '\[net\] (state t=\S+ wall=\S+ loggedIn=\d inGame=0|harness t=\S+ left the game)')
    if (-not $lR1.Pass) { return $lR1 }
    $liPost = & $NetPair.First $ctx.LogLines '\[net\] harness t=\S+ wall=\S+ post 52'
    if ($liPost -ge 0) { return @{ Pass = $false; Detail = 'the HARNESS posted 52 -- this case must leave through the UI only' } }
    return $lR1
  }.GetNewClosure()
  $lChecks += @(
    @{ Kind = 'Script';   Name = 'the menu script ran to its end (left the lobby)'; Script = $lScriptDone }
    @{ Kind = 'Script';   Name = 'Easy Drive was on its last row (LEAVE_GAME) when selected'; Script = $lBottomCheck }
    @{ Kind = 'Script';   Name = 'the lobby membership ended after the Easy Drive selection'; Script = $lLeftCheck }
    @{ Kind = 'LogMatch'; Name = 'the game room handed back to INGAME'; Pattern = "\[screen\] ENTER 'INGAME\s*' \(from 'ON_GAME_ROOM"; Expect = $true }
    @{ Kind = 'LogMatch'; Name = 'game: the local leave reached GameState (case 124)'; Pattern = '\[net\] game local left'; Expect = $true }
  )
}

@{
  Name    = "net_ui_leave_$Role"
  Area    = 'network'
  Bug     = "wave 3 -- the $Role half of net_ui_leave (run it through tools\tests\run_pair.ps1)"
  Frames  = $lR.Frames
  Run     = $lRun
  DiagEnv = "$($lR.Harness),BRN_NET_DELAY=30,BRN_SCREEN_DIAG=1,BRN_EASYDRIVE_TRACE=1"
  Setup   = (& $NetPair.Setup $Role)
  Checks  = $lChecks
}
