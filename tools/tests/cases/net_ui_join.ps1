# net_ui_join -- two instances go online THROUGH THE REAL MENUS: the Host picks Easy Drive -> FREEBURN
# -> Create, the Guest (once the Host's lobby exists) picks Easy Drive -> FREEBURN -> Quick Match,
# and both end up in one free-burn lobby, each seeing the other's car. No BRN_NET_HOST / BRN_NET_JOIN:
# the PC harness posts nothing (it only prints its [net] state lines under BP_LAN=1).
#
# Run it (a PAIR case -- see net_lan_pair.ps1 for how pair cases work):
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_pair.ps1 -Case net_ui_join
#
# THE MENU PATH (developed on the a352bef0 exe, scratch\net_wave3\h_explore\ed2, 2026-09-24):
#   DPadRight          opens Easy Drive: "[easydrive-view] panel 1 list 2 ... count 8"
#   DPadDown           moves to FREEBURN (row 1) -- IGNORED while the panel is still opening (panel 1),
#                      hence tapuntil: "[easydrive-view] panel 2 list 2 branch 0 selected 1"
#   DPadRight          opens the FREEBURN branch: "branch 5" = Quick Match (option 0);
#   DPadDown           "branch 11" = Custom Match (option 1);  DPadDown again "branch 12" = Create (option 2)
#   DPadRight          selects: "[easydrive-command] main option <n>" (InGame, GUI 284) and
#                      "[screen] ENTER 'CN_ENTER_ON'" (sign-in), then ON_CREATE_FB / ON_QWK_MAT post
#                      GUI 256 / 251 and ADVANCE to ON_GAME_ROOM on GUI 50 (in game).
#   On a352bef0 the flow stops at the CN_ENTER_ON placeholder ("un-reconstructed state (FLAG)").
# The Guest waits for the Host's "host_in_lobby" signal file (run_pair's BP_PAIR_DIR\signals) before
# it opens Easy Drive, so it quick-matches into a lobby that exists.
#
# THE ORACLE (per half; BRN_SCREEN_DIAG + BRN_EASYDRIVE_TRACE through DiagEnv)
#   the menu script ran to its end (marks.txt MENUSCRIPT done=n/n)
#   [easydrive-command] main option 2 (Host) / 0 (Guest)
#   [screen] ENTER 'CN_ENTER_ON' -> 'ON_CREATE_FB' (Host) / 'ON_QWK_MAT' (Guest) -> 'ON_GAME_ROOM', in order (lanes UA, UB)
#   [net] create finished success=1 inGame=1 (Host) / [net] quickjoin finished success=1 inGame=1 (Guest)
#   the lobby game started (mode 15) and a network car was spawned for the other player
#   no "[net] harness armed" line (the harness did not drive this)
#   Guest: the first "[net] update-in applied" position is the Host's spot (within 6 m)
param([string]$Role = '')
. (Join-Path $PSScriptRoot '..\_net_pair_common.ps1')

$lsOpen   = 'wait:strfin|\[easydrive-route\];sleep:4;tapuntil:DPadRight:\[easydrive-view\] panel 1 list 2\b;tapuntil:DPadDown:\[easydrive-view\] panel \d+ list 2 branch 0 selected 1\b;tapuntil:DPadRight:\[easydrive-view\] panel \d+ list 2 branch 5\b;sleep:1'
$lsCreate = 'tapuntil:DPadDown:\[easydrive-view\] panel \d+ list 2 branch 11\b;sleep:1;tapuntil:DPadDown:\[easydrive-view\] panel \d+ list 2 branch 12\b;sleep:1;tap:DPadRight'
$lsLobby  = "timeout:100;wait:\[screen\] ENTER 'ON_GAME_ROOM;timeout:0"

$lPairRoles = [ordered]@{
  Host  = @{ Other = 'Guest'; Spot = $NetPair.Spots.Host;  Option = 2; Screen = 'ON_CREATE_FB'; Finish = 'create'
             Script = "$lsOpen;$lsCreate;$lsLobby;signal:host_in_lobby;mark:in-lobby" }
  Guest = @{ Other = 'Host';  Spot = $NetPair.Spots.Guest; Option = 0; Screen = 'ON_QWK_MAT';   Finish = 'quickjoin'
             Script = "wait:strfin|\[easydrive-route\];timeout:150;waitfile:host_in_lobby;timeout:0;sleep:2;$lsOpen;tap:DPadRight;$lsLobby;signal:guest_in_lobby;mark:in-lobby" }
}

if ($Role -eq '') {
  return @{
    Name = 'net_ui_join'
    Area = 'network'
    Bug  = 'wave 3 -- create and quick-match into one online free-burn lobby through Easy Drive (no harness posts)'
    Pair = @{ Roles = @($lPairRoles.Keys); Slots = @(1, 2) }
  }
}
if (-not $lPairRoles.Contains($Role)) { throw "net_ui_join: unknown -Role '$Role' (Host or Guest)" }
$lR = $lPairRoles[$Role]
$lsOther = $lR.Other
$laOther = @($lPairRoles[$lsOther].Spot.Split(',') | ForEach-Object { [double]::Parse($_, [Globalization.CultureInfo]::InvariantCulture) })

$lRun = @{ MaxSeconds = 180; SkipIntro = $true; AcceptGap = 1.0; Teleport = $lR.Spot; FrameEvery = 300; MenuScript = $lR.Script }

$lScriptDone = {
  param($ctx)
  if ($ctx.MarksText -match 'MENUSCRIPT done=(\d+)/(\d+) state=(\S+)(.*)') {
    return @{ Pass = ($Matches[1] -eq $Matches[2]); Detail = $Matches[0].Trim() }
  }
  return @{ Pass = $false; Detail = 'marks.txt has no MENUSCRIPT line' }
}
$lScreens = {
  param($ctx)
  return & $NetPair.Ordered $ctx.LogLines @("\[screen\] ENTER 'CN_ENTER_ON", "\[screen\] ENTER '$($lR.Screen)", "\[screen\] ENTER 'ON_GAME_ROOM")
}.GetNewClosure()
$lSeesOther = {
  param($ctx)
  $lRx = '\[net\] update-in applied since=\d+ from=\S+ car=(\d+) snap=\d pos=\(([-0-9.]+), ([-0-9.]+), ([-0-9.]+)\)'
  $lHit = @($ctx.LogLines | Where-Object { $_ -match $lRx }) | Select-Object -First 1
  if ($null -eq $lHit) { return @{ Pass = $false; Detail = 'no [net] update-in applied line' } }
  $null = $lHit -match $lRx
  $lfX = [double]::Parse($Matches[2], [Globalization.CultureInfo]::InvariantCulture); $lfZ = [double]::Parse($Matches[4], [Globalization.CultureInfo]::InvariantCulture)
  $lfD = [Math]::Sqrt(($lfX - $laOther[0]) * ($lfX - $laOther[0]) + ($lfZ - $laOther[2]) * ($lfZ - $laOther[2]))
  return @{ Pass = ($lfD -le 6.0); Detail = ("first applied ({0:f1}, {1:f1}) is {2:f1} m from {3}'s spot" -f $lfX, $lfZ, $lfD, $lsOther) }
}.GetNewClosure()

@{
  Name    = "net_ui_join_$Role"
  Area    = 'network'
  Bug     = "wave 3 -- the $Role half of net_ui_join (run it through tools\tests\run_pair.ps1)"
  Frames  = $true
  Run     = $lRun
  DiagEnv = 'BRN_SCREEN_DIAG=1,BRN_EASYDRIVE_TRACE=1'
  Setup   = (& $NetPair.Setup $Role)
  Checks  = @(
    @{ Kind = 'LogCount'; Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';     Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'LogMatch'; Name = 'the harness drove nothing (no BRN_NET_HOST / JOIN)'; Pattern = '\[net\] harness armed role='; Expect = $false }
    @{ Kind = 'LogMatch'; Name = "Easy Drive selected FREEBURN option $($lR.Option)"; Pattern = "\[easydrive-command\] main option $($lR.Option)\b"; Expect = $true }
    @{ Kind = 'Script';   Name = "screens CN_ENTER_ON -> $($lR.Screen) -> ON_GAME_ROOM"; Script = $lScreens }
    @{ Kind = 'LogMatch'; Name = "network: $($lR.Finish) landed in a game"; Pattern = ('\[net\] ' + $lR.Finish + ' finished success=1 inGame=1'); Expect = $true }
    @{ Kind = 'LogMatch'; Name = 'the lobby game started (mode 15)'; Pattern = '\[net\] game round start -> StartGameMode mode=15'; Expect = $true }
    @{ Kind = 'Script';   Name = "a network race car was spawned for $lsOther"; Script = { param($ctx) & $NetPair.Spawned $ctx.LogLines }.GetNewClosure() }
    @{ Kind = 'Script';   Name = "updates drive $lsOther's car where $lsOther is"; Script = $lSeesOther }
    @{ Kind = 'Script';   Name = 'the menu script ran to its end'; Script = $lScriptDone }
  )
}
