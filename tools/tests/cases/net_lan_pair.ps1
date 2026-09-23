# net_lan_pair -- TWO game instances on this box find each other over the PC LAN backend and end
# up in one online game: each instance's log must name the OTHER player in the game's player list.
#
# Run it (a PAIR case -- it needs two slots at once, so it has its own runner):
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_pair.ps1 -Case net_lan_pair
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_pair.ps1 -Case net_lan_pair -NoRun -RunDir <pair run dir>
#
# ⛔ NOT a run_case / run_all case on its own. Called with no -Role this file returns the PAIR
#   DESCRIPTOR (no Checks, so run_case refuses it with exit 2). run_pair.ps1 calls it once per
#   role (-Role Host / -Role Guest) and runs each half through the ordinary run_case.ps1 on its
#   own slot, so every half gets the usual flow_run boot, box lock, provenance and REPORT.md.
#
# WHAT EACH HALF IS
#   * the ordinary returning-player boot to DRIVING (SkipIntro + AcceptGap, no pad input after);
#   * BP_LAN=1 and BP_LAN_NAME=<Host|Guest>, set by the half's Setup inside its own run_case
#     process (they are not BRN_* variables, so flow_run's wipe does not touch them and they
#     reach the game by inheritance). BP_LAN_XUID is cleared so the XUID derives from the name;
#   * the game-side harness role through -DiagEnv (BrnNetHarnessPC.cpp, PC harness only):
#     BRN_NET_HOST=1 -> sign in (GUI 272), create an unranked free-burn lobby game (GUI 256);
#     BRN_NET_JOIN=1 -> sign in (272), quick match unranked free burn (GUI 251), retried every 5 s.
#     BRN_NET_DELAY holds both until the boot has reached free roam.
#
# THE ORACLE -- bounded "[net] ..." witness lines (BrnNetHarnessPC::Witness, printed only when
# BP_LAN=1 or a harness role is set; the default offline run prints none of them):
#   [net] pclan up name=<me> ...                     the LAN transport bound its UDP port
#   [net] harness armed role=host|join ...           the harness saw its role
#   [net] login finished loggedIn=1 ...              StateManager::UpdateLogin, signed in
#   [net] create|quickjoin finished success=1 inGame=1
#   [net] player added id=<n> local=0 name=<other>   BrnNetworkManager::PlayerManagerEventCallback:
#                                                    the other player is in the PlayerManager list
#   [net] playerlist n=2 ...=<other>                 the list the network hands the GUI (bridge)
# PASS = every check below on BOTH halves; the last check is the goal itself.
param([string]$Role = '')

$lPairRoles = [ordered]@{
  Host  = @{ Other = 'Guest'; Harness = 'BRN_NET_HOST'; HarnessRole = 'host'; Finish = 'create'    }
  Guest = @{ Other = 'Host';  Harness = 'BRN_NET_JOIN'; HarnessRole = 'join'; Finish = 'quickjoin' }
}

$lRun = @{
  MaxSeconds = 150       # boot ~20 s + BRN_NET_DELAY 30 s + sign-in + create/quick-match retries
  SkipIntro  = $true
  AcceptGap  = 1.0
}

if ($Role -eq '') {
  return @{
    Name = 'net_lan_pair'
    Area = 'network'
    Bug  = 'none -- wave 2 goal: two instances on one machine find and join each other over the PC LAN backend'
    Pair = @{ Roles = @($lPairRoles.Keys); Slots = @(1, 2) }
  }
}
if (-not $lPairRoles.Contains($Role)) { throw "net_lan_pair: unknown -Role '$Role' (Host or Guest)" }
$lR = $lPairRoles[$Role]
$lsMe = $Role
$lsOther = $lR.Other

$lSetup = {
  param($ctx)
  $env:BP_LAN = '1'
  $env:BP_LAN_NAME = $lsMe
  Remove-Item Env:\BP_LAN_XUID -ErrorAction SilentlyContinue
  Write-Host ("[case] {0}: BP_LAN=1 BP_LAN_NAME={0}{1}" -f $lsMe,
              $(if ($env:BP_LAN_PORT) { " BP_LAN_PORT=$($env:BP_LAN_PORT)" } else { '' }))
  return $null
}.GetNewClosure()

$lOtherCheck = {
  param($ctx)
  $lHits = @($ctx.LogLines | Where-Object {
    $_ -match ('\[net\] player added id=\S+ local=0 name=' + [regex]::Escape($lsOther) + '\b') -or
    $_ -match ('\[net\] playerlist .*=' + [regex]::Escape($lsOther) + '(\s|$)')
  })
  if ($lHits.Count -eq 0) {
    $lMine = @($ctx.LogLines | Where-Object { $_ -match '\[net\] (player|playerlist) ' } | Select-Object -Last 3)
    return @{ Pass = $false; Detail = ("no [net] player line names '{0}'; last: {1}" -f $lsOther,
                                       $(if ($lMine.Count) { $lMine -join ' | ' } else { '(none)' })) }
  }
  return @{ Pass = $true; Detail = $lHits[0].Trim() }
}.GetNewClosure()

@{
  Name    = "net_lan_pair_$Role"
  Area    = 'network'
  Bug     = "none -- the $Role half of net_lan_pair (run it through tools\tests\run_pair.ps1)"
  Frames  = $false
  Run     = $lRun
  DiagEnv = "$($lR.Harness)=1,BRN_NET_DELAY=30"
  Setup   = $lSetup
  Checks  = @(
    @{ Kind = 'LogCount'; Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';     Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'LogMatch'; Name = "LAN transport up as $lsMe"; Pattern = ('\[net\] pclan up name=' + [regex]::Escape($lsMe) + ' '); Expect = $true }
    @{ Kind = 'LogMatch'; Name = "harness armed ($($lR.HarnessRole))"; Pattern = ('\[net\] harness armed role=' + $lR.HarnessRole); Expect = $true }
    @{ Kind = 'LogMatch'; Name = 'signed in'; Pattern = '\[net\] login finished loggedIn=1'; Expect = $true }
    @{ Kind = 'LogMatch'; Name = "$($lR.Finish) landed in a game"; Pattern = ('\[net\] ' + $lR.Finish + ' finished success=1 inGame=1'); Expect = $true }
    @{ Kind = 'Script';   Name = "the other player ($lsOther) is in my player list"; Script = $lOtherCheck }
  )
}
