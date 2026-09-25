# net_lan_challenge -- the HOST starts a free-burn challenge in the online lobby and the GUEST sees
# it start too.
#
# Run it (a PAIR case -- see net_lan_pair.ps1 for how pair cases work):
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_pair.ps1 -Case net_lan_challenge
#
# THE CHALLENGE. ONLINECHALLENGES.BNDL (the B5ChallengeList resource, 458 entries, read 2026-09-24)
# entry 5: CgsID 0x8DACC, title FBCT_580300, 2 players, one action CRASH_INTO_PLAYER (target 1, coop
# "once": either player crashing into the other completes it), no location, no time limit, easy,
# release entitlement. A 2-player challenge that needs nothing but the two cars.
#
# THE STIMULUS. The Host's BrnNetHarnessPC posts, 20 s after it is first seen in its lobby, the GUI
# record the challenge selector posts when a challenge is picked -- GUI 573
# GuiChallengeSelectedEvent { u64 challenge id, s32 selector action 0, s32 style 1 (NORMAL) },
# channel-40 wrapped, into the GUI out queue right before BridgeGuiToGameState -- i.e.
#   BRN_NET_SCRIPT=20:gui:573:q0x8DACC/0/1
# The bridge turns it into game event 162 exactly as for a real selection (GameBridgeGUIToX_GameState
# case 573). The host relays challenges to every player (StateManager AmIHost ->
# SendFreeburnChallengeMessage); the Guest receives network event 65 -> game event 163/164.
# The Guest is parked 30 m in front of the Host facing it and drives into it at DRIVING+85 s, so
# the challenge's own goal (crash into a player) can be met; both halves dump frames (the challenge
# HUD) every 300 presents.
#
# THE ORACLE
#   Host   [net] harness ... script #0 post gui GUI 573        the stimulus happened
#          [net] game fburn select id=<id> sub=0               case 162 (lane GS; MM's HandleLocalStart...)
#   Guest  [net] game fburn remote start|trigger id=<id>       case 163 / 164 (lane GS; MM's HandleRemote...)
#   PAIR   both halves name the same challenge id, and it is 0x8DACC
param([string]$Role = '')
. (Join-Path $PSScriptRoot '..\_net_pair_common.ps1')

$lsChallenge = '8DACC'
$lPairRoles = [ordered]@{
  Host  = @{ Other = 'Guest'; Harness = "BRN_NET_HOST=1,BRN_NET_SCRIPT=20:gui:573:q0x$lsChallenge/0/1"; Spot = $NetPair.Spots.Host;  Drives = $false }
  Guest = @{ Other = 'Host';  Harness = 'BRN_NET_JOIN=1'; Spot = '3040.7,-5.8,-1967.9,0'; Drives = $true }
}

$lIdAgree = {
  param($p)
  $lRxH = '\[net\] game fburn select id=(?:0x)?0*([0-9a-fA-F]+)'
  $lRxG = '\[net\] game fburn remote (?:start|trigger) id=(?:0x)?0*([0-9a-fA-F]+)'
  $lH = @($p.Halves['Host'].LogLines  | Where-Object { $_ -match $lRxH }) | Select-Object -First 1
  $lG = @($p.Halves['Guest'].LogLines | Where-Object { $_ -match $lRxG }) | Select-Object -First 1
  if ($null -eq $lH -or $null -eq $lG) { return @{ Pass = $false; Detail = ("host select: {0}; guest remote start: {1}" -f $(if ($lH) { 'yes' } else { 'NONE' }), $(if ($lG) { 'yes' } else { 'NONE' })) } }
  $null = $lH -match $lRxH; $lsH = $Matches[1].ToUpperInvariant()
  $null = $lG -match $lRxG; $lsG = $Matches[1].ToUpperInvariant()
  return @{ Pass = ($lsH -eq $lsG -and $lsH -eq $lsChallenge); Detail = "host id $lsH, guest id $lsG, injected $lsChallenge" }
}.GetNewClosure()

if ($Role -eq '') {
  return @{
    Name = 'net_lan_challenge'
    Area = 'network'
    Bug  = 'wave 3 -- a free-burn challenge the host starts in the online lobby starts on the guest too'
    Pair = @{ Roles = @($lPairRoles.Keys); Slots = @(1, 2)
              Checks = @( @{ Name = 'both halves run the same challenge (the injected id)'; Script = $lIdAgree } ) }
  }
}
if (-not $lPairRoles.Contains($Role)) { throw "net_lan_challenge: unknown -Role '$Role' (Host or Guest)" }
$lR = $lPairRoles[$Role]
$lsOther = $lR.Other

$lRun = @{ MaxSeconds = 150; SkipIntro = $true; AcceptGap = 1.0; Teleport = $lR.Spot; FrameEvery = 300 }
if ($lR.Drives) {
  $lRun['Drive']          = $true
  $lRun['DriveDelay']     = 85.0
  $lRun['ThrottleScript'] = '0:accel,3:none'
}

$lChecks = @(
  @{ Kind = 'LogCount'; Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
  @{ Kind = 'Mark';     Name = 'reached DRIVING'; Phase = 'DRIVING' }
  @{ Kind = 'LogMatch'; Name = 'the lobby game started (mode 15)'; Pattern = '\[net\] game round start -> StartGameMode mode=15'; Expect = $true }
  @{ Kind = 'Script';   Name = "a network race car was spawned for $lsOther"; Script = { param($ctx) & $NetPair.Spawned $ctx.LogLines }.GetNewClosure() }
)
if ($Role -eq 'Host') {
  $lChecks += @(
    @{ Kind = 'LogMatch'; Name = 'the harness posted the challenge selection (GUI 573)'; Pattern = '\[net\] harness t=\S+ script #0 post gui GUI 573 '; Expect = $true }
    @{ Kind = 'LogMatch'; Name = 'game: the selection reached GameState (case 162)'; Pattern = ('(?i)\[net\] game fburn select id=(0x)?0*' + $lsChallenge + ' sub=0'); Expect = $true }
  )
} else {
  $lChecks += @(
    @{ Kind = 'LogMatch'; Name = 'game: the Host''s challenge started here (case 163/164)'; Pattern = ('(?i)\[net\] game fburn remote (start|trigger) id=(0x)?0*' + $lsChallenge); Expect = $true }
  )
}

@{
  Name    = "net_lan_challenge_$Role"
  Area    = 'network'
  Bug     = "wave 3 -- the $Role half of net_lan_challenge (run it through tools\tests\run_pair.ps1)"
  Frames  = $true
  Run     = $lRun
  DiagEnv = "$($lR.Harness),BRN_NET_DELAY=30"
  Setup   = (& $NetPair.Setup $Role)
  Checks  = $lChecks
}
