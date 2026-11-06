# net_lan_full_race -- one whole online race over LAN, end to end: lobby -> launch -> car select ->
# OnlineLoading -> race -> results -> back to the lobby.
# It then watches the lobby: the game must stay there. net_lan_start_mode stops at IN_PROGRESS, so it can
# never see what happens after the finish line.
#
# Run it (a PAIR case; in the main checkout use slots 3 and 4, slot 1 has an online-server config.ini):
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_pair.ps1 -Case net_lan_full_race -SlotA 3 -SlotB 4
#
# THE BUG IT WAS WRITTEN FOR (2026-11-05, played by hand): after the race the guest started a launch of
# its own from the lobby and sat on "The Host is choosing everyone's car" for good, while the host stayed
# in the lobby. A guest launches when it sees the game record's started flag (StateManager, not host &&
# IsGameStarted); that flag is raised on 'gsta' by the PC lobby layer.
#
# Both cars reach the finish through -WinTeleport, which places each car in the landmark box and leaves
# the game's own finish detection to do the rest. Neither of the alternatives finishes the round:
# BRN_AI_DRIVES_PLAYER leaves both cars stationary at the online start line (run 20261105_021925, speed 0
# for 400 s) and a harness-posted GUI 231 has no effect (run 20261105_023023). The driving itself is not
# exercised.
#
# A SECOND RACE follows from the post-race lobby (2026-11-06), for the online race intro's rival indexing
# : the shot cursor is never reset by Prepare, so only a second intro shows whether the
# handles are still indexed by rival. In-game clock (the harness's, from the lobby join): race 1 launches at
# +40 s and is back in the lobby near +152 s (run 20261106_021131); the host re-posts 193 and 257 and
# launches again at +185 s. BRN_WIN_TELEPORT_REPEAT re-arms the win teleport in the lobby. The lobby watch
# then runs after the SECOND race.
param([string]$Role = '')
. (Join-Path $PSScriptRoot '..\_net_pair_common.ps1')

$liMaxSeconds = if ($env:BP_FULL_RACE_MAX) { [int]$env:BP_FULL_RACE_MAX } else { 480 }

$lPairRoles = [ordered]@{
  Host  = @{ Other = 'Guest'; Harness = "BRN_NET_HOST=1,BRN_NET_START_MODE=25:10:175,BRN_NET_SCRIPT=10:gui:193:10;40:net:54;170:gui:193:10;185:net:54" }
  Guest = @{ Other = 'Host';  Harness = 'BRN_NET_JOIN=1' }
}

$lOneRace = @(
  '\[net\] mode-start mode=OnlineRace type=10 params-type=10',
  'mode state -> E_GMS_INTRO',
  'mode state -> E_GMS_IN_PROGRESS',
  'mode state -> E_GMS_RESULTS',
  '\[net\] mode-start mode=OnlineFreeBurnLobby type=15'
)

$lRaceEnded = {
  param($laLines)
  return (& $NetPair.Ordered $laLines $lOneRace)
}.GetNewClosure()

$lSecondRaceEnded = {
  param($laLines)
  return (& $NetPair.Ordered $laLines @($lOneRace + $lOneRace))
}.GetNewClosure()

# The second race, from its mode-start to its results: no assert but the known above-car family.
$lSecondRaceAsserts = {
  param($laLines)
  $lOrder = & $lSecondRaceEnded $laLines
  if (-not $lOrder.Pass) { return @{ Pass = $false; Detail = "no second race: $($lOrder.Detail)" } }
  $liStart = & $NetPair.First $laLines $lOneRace[0] ((& $lRaceEnded $laLines).Index + 1)
  $liEnd = $lOrder.Index
  $laOther = @($laLines[$liStart..$liEnd] | Where-Object { $_ -match '^\[ASSERT \d+\]' -and $_ -notmatch 'Invalid rival position for active race car' })
  $lsFirst = if ($laOther.Count -gt 0) { " first: $($laOther[0])" } else { '' }
  return @{ Pass = ($laOther.Count -eq 0); Detail = "second race lines $liStart..${liEnd}: $($laOther.Count) other assert line(s)$lsFirst" }
}.GetNewClosure()

# After the post-race lobby has started, nothing may launch or enter car select until the end of the run.
$lStayedInLobby = {
  param($laLines)
  $lOrder = & $lSecondRaceEnded $laLines
  if (-not $lOrder.Pass) { return @{ Pass = $false; Detail = "the race never got back to the lobby: $($lOrder.Detail)" } }
  $liFrom = $lOrder.Index + 1
  $liAfter = @($laLines[$liFrom..($laLines.Count - 1)])
  $liLaunches = @($liAfter | Where-Object { $_ -match '\[net\] launch-mgr substate 1 -> 2' }).Count
  $liCarSelects = @($liAfter | Where-Object { $_ -match 'CS Manager : EnterOnlineCarSelect' }).Count
  return @{ Pass = ($liLaunches -eq 0 -and $liCarSelects -eq 0); Detail = "after the post-race lobby: launches=$liLaunches car-selects=$liCarSelects, over $($liAfter.Count) log lines" }
}.GetNewClosure()

if ($Role -eq '') {
  return @{
    Name = 'net_lan_full_race'
    Area = 'network'
    Bug  = 'after an online race the guest launches again from the lobby and waits on the host for good'
    Pair = @{
      Roles  = @($lPairRoles.Keys)
      Slots  = @(1, 2)
      Checks = @(
        @{ Name = 'host: race finished and back in the lobby';  Script = { param($p) $r = & $lRaceEnded $p.Halves.Host.LogLines;  @{ Pass = $r.Pass; Detail = $r.Detail } }.GetNewClosure() }
        @{ Name = 'guest: race finished and back in the lobby'; Script = { param($p) $r = & $lRaceEnded $p.Halves.Guest.LogLines; @{ Pass = $r.Pass; Detail = $r.Detail } }.GetNewClosure() }
        @{ Name = 'host: second race finished and back in the lobby';  Script = { param($p) $r = & $lSecondRaceEnded $p.Halves.Host.LogLines;  @{ Pass = $r.Pass; Detail = $r.Detail } }.GetNewClosure() }
        @{ Name = 'guest: second race finished and back in the lobby'; Script = { param($p) $r = & $lSecondRaceEnded $p.Halves.Guest.LogLines; @{ Pass = $r.Pass; Detail = $r.Detail } }.GetNewClosure() }
        @{ Name = 'host: no new assert in the second race';  Script = { param($p) & $lSecondRaceAsserts $p.Halves.Host.LogLines }.GetNewClosure() }
        @{ Name = 'guest: no new assert in the second race'; Script = { param($p) & $lSecondRaceAsserts $p.Halves.Guest.LogLines }.GetNewClosure() }
        @{ Name = 'host stayed in the lobby';  Script = { param($p) & $lStayedInLobby $p.Halves.Host.LogLines }.GetNewClosure() }
        @{ Name = 'guest stayed in the lobby'; Script = { param($p) & $lStayedInLobby $p.Halves.Guest.LogLines }.GetNewClosure() }
      )
    }
  }
}
if (-not $lPairRoles.Contains($Role)) { throw "net_lan_full_race: unknown -Role '$Role' (Host or Guest)" }
$lR = $lPairRoles[$Role]

@{
  Name    = "net_lan_full_race_$Role"
  Area    = 'network'
  Bug     = "none -- the $Role half of net_lan_full_race (run it through tools\tests\run_pair.ps1)"
  Frames  = $true
  Run     = @{ MaxSeconds = $liMaxSeconds; TitleStart = $true; SkipIntro = $true; AcceptGap = 1.0; FrameEvery = 300; WinTeleport = 5 }
  DiagEnv = "$($lR.Harness),BRN_NET_DELAY=20,BRN_SCREEN_DIAG=1,BRN_WIN_TELEPORT_REPEAT=1"
  Setup   = (& $NetPair.Setup $Role)
  Checks  = @(
    @{ Kind = 'LogCount'; Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';     Name = 'reached DRIVING'; Phase = 'DRIVING' }
  )
}
