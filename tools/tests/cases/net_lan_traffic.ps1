# net_lan_traffic -- ONLINE TRAFFIC is synchronised between the two instances of the free-burn lobby.
#
# Run it (a PAIR case -- see net_lan_pair.ps1 for how pair cases work):
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_pair.ps1 -Case net_lan_traffic
#
# WHAT "SYNCHRONISED" MEANS (scratch\net_wave3\MAP_TRAFFIC.md s.0). Traffic positions are not
# streamed: every machine simulates the same traffic from the same restart. The host broadcasts
# "reset traffic at network frame F with these 8 hulls" (msg 28), every machine resets at F with the
# fixed seed, each machine predicts its own player's hull 5 s ahead and broadcasts the change
# stamped 50 traffic updates later (msg 13), and each machine hashes its traffic state on decision
# frames and sends the hash (msg 14) -- a mismatch only flags divergence.
#
# THE SET-UP. The net_lan_see halves (Host parked at the junkyard exit, Guest 25 m ahead), traffic
# census on both (BRN_TRAFFIC_TRACK=1), frames every 300 presents on both, and the Guest DRIVES for
# 4 s at DRIVING+75 s so its 5 s prediction crosses a hull boundary.
#
# THE ORACLE -- the [nettraf] witnesses (BrnNetHarnessPC::WitnessTag, lanes TA/TB; site words fixed
# in scratch\net_wave3\CONTRACTS.md) plus the traffic census:
#   per half   no mbActiveHullsValid assert (RED today: 8 on the Host -- nothing fills the hull table)
#              [nettraf] restart-apply fr=<n> hulls=<8 x hex> exactly once, >= 2 slots != ffff
#              [nettraf] action236 ...  (the restart reached the traffic module)
#              >= 20 [nettraf] hash lines, no [nettraf] DIVERGED
#              [traffic-track] SAMPLE alive=<n> with n > 0 after the restart (RED today: alive=0 online)
#   Guest      [nettraf] hull-predict ...        Host   [nettraf] hull-in ...
#   PAIR       the two halves' hashes agree on every common upd (>= 20 common)
#              restart-apply fr and the non-ffff hull multiset are equal on both halves
#              a Guest hull-predict (hull, upd) arrives as a Host hull-in with the same hull and upd
param([string]$Role = '')
. (Join-Path $PSScriptRoot '..\_net_pair_common.ps1')

$lPairRoles = [ordered]@{
  Host  = @{ Other = 'Guest'; Harness = 'BRN_NET_HOST=1'; Spot = $NetPair.Spots.Host;  Drives = $false; HullRx = '\[nettraf\] hull-in ';      HullWhat = 'a remote hull change arrived (hull-in)' }
  Guest = @{ Other = 'Host';  Harness = 'BRN_NET_JOIN=1'; Spot = $NetPair.Spots.Guest; Drives = $true;  HullRx = '\[nettraf\] hull-predict '; HullWhat = 'its own hull change was predicted (hull-predict)' }
}

# --- pair-level checks: both halves' logs at once (run_pair.ps1 evaluates them) ---------------------
$lHashAgree = {
  param($p)
  $lRx = '\[nettraf\] hash upd=(\d+) h=([0-9a-fA-F]+)'
  $laMaps = @()
  foreach ($lsRole in @('Host', 'Guest')) {
    $lMap = @{}
    foreach ($ls in $p.Halves[$lsRole].LogLines) { if ($ls -match $lRx) { $lMap[[int64]$Matches[1]] = $Matches[2].ToLowerInvariant() } }
    $laMaps += ,$lMap
  }
  $laCommon = @($laMaps[0].Keys | Where-Object { $laMaps[1].ContainsKey($_) } | Sort-Object)
  $laBad = @($laCommon | Where-Object { $laMaps[0][$_] -ne $laMaps[1][$_] })
  $lsDetail = ("host {0} / guest {1} hash lines, {2} common upd, {3} mismatch(es){4}" -f $laMaps[0].Count, $laMaps[1].Count,
               $laCommon.Count, $laBad.Count, $(if ($laBad.Count -gt 0) { "; first upd=$($laBad[0]) host=$($laMaps[0][$laBad[0]]) guest=$($laMaps[1][$laBad[0]])" } else { '' }))
  return @{ Pass = ($laCommon.Count -ge 20 -and $laBad.Count -eq 0); Detail = $lsDetail }
}
$lRestartAgree = {
  param($p)
  $lRx = '\[nettraf\] restart-apply fr=(\d+) hulls=([0-9a-fA-F, ]+)'
  $laSeen = @()
  foreach ($lsRole in @('Host', 'Guest')) {
    $lHit = @($p.Halves[$lsRole].LogLines | Where-Object { $_ -match $lRx }) | Select-Object -First 1
    if ($null -eq $lHit) { return @{ Pass = $false; Detail = "no [nettraf] restart-apply on the $lsRole" } }
    $null = $lHit -match $lRx
    $laH = @($Matches[2] -split '[, ]+' | Where-Object { $_ -ne '' -and $_.ToLowerInvariant() -ne 'ffff' } | ForEach-Object { $_.ToLowerInvariant() } | Sort-Object)
    $laSeen += ,@($Matches[1], ($laH -join ','))
  }
  $lbPass = ($laSeen[0][0] -eq $laSeen[1][0]) -and ($laSeen[0][1] -eq $laSeen[1][1])
  return @{ Pass = $lbPass; Detail = ("host fr={0} hulls={{{1}}} / guest fr={2} hulls={{{3}}}" -f $laSeen[0][0], $laSeen[0][1], $laSeen[1][0], $laSeen[1][1]) }
}
$lHullRelay = {
  param($p)
  $lRxP = '\[nettraf\] hull-predict arc=\S+ hull=(\d+) upd=(\d+)'
  $lRxI = '\[nettraf\] hull-in arc=\S+ hull=(\d+) upd=(\d+)'
  $laPred = @($p.Halves['Guest'].LogLines | Where-Object { $_ -match $lRxP } | ForEach-Object { $null = $_ -match $lRxP; "$($Matches[1])@$($Matches[2])" })
  $laIn   = @($p.Halves['Host'].LogLines  | Where-Object { $_ -match $lRxI } | ForEach-Object { $null = $_ -match $lRxI; "$($Matches[1])@$($Matches[2])" })
  $laBoth = @($laPred | Where-Object { $laIn -contains $_ })
  return @{ Pass = ($laBoth.Count -gt 0); Detail = ("guest predicted [{0}], host received [{1}]" -f ($laPred -join ' '), ($laIn -join ' ')) }
}

if ($Role -eq '') {
  return @{
    Name = 'net_lan_traffic'
    Area = 'network'
    Bug  = 'wave 3 -- online traffic: restart, hull sync and hash agree between the two lobby instances'
    Pair = @{ Roles = @($lPairRoles.Keys); Slots = @(1, 2)
              Checks = @(
                @{ Name = 'traffic hashes agree on every common update (>= 20)'; Script = $lHashAgree }
                @{ Name = 'both halves restarted at the same frame with the same hulls'; Script = $lRestartAgree }
                @{ Name = 'the Guest''s predicted hull change reached the Host (same hull, same update)'; Script = $lHullRelay }
              ) }
  }
}
if (-not $lPairRoles.Contains($Role)) { throw "net_lan_traffic: unknown -Role '$Role' (Host or Guest)" }
$lR = $lPairRoles[$Role]

$lRun = @{ MaxSeconds = 150; SkipIntro = $true; AcceptGap = 1.0; Teleport = $lR.Spot; FrameEvery = 300 }
if ($lR.Drives) {
  $lRun['Drive']          = $true
  $lRun['DriveDelay']     = 75.0
  $lRun['ThrottleScript'] = '0:accel,4:none'
}

$lRestartCheck = {
  param($ctx)
  $lRx = '\[nettraf\] restart-apply fr=(\d+) hulls=([0-9a-fA-F, ]+)'
  $laHits = @($ctx.LogLines | Where-Object { $_ -match $lRx })
  if ($laHits.Count -ne 1) { return @{ Pass = $false; Detail = "$($laHits.Count) restart-apply line(s), want exactly 1" } }
  $null = $laHits[0] -match $lRx
  $laSet = @($Matches[2] -split '[, ]+' | Where-Object { $_ -ne '' -and $_.ToLowerInvariant() -ne 'ffff' })
  return @{ Pass = ($laSet.Count -ge 2); Detail = ("{0} ({1} slot(s) != ffff)" -f $laHits[0].Trim(), $laSet.Count) }
}
$lAliveCheck = {
  param($ctx)
  $liFrom = & $NetPair.First $ctx.LogLines '\[nettraf\] restart-apply '
  $lRx = '\[traffic-track\] SAMPLE t=\S+ alive=(\d+)'
  if ($liFrom -lt 0) {
    # no restart to count from: say what the lobby had instead (RED evidence)
    $liLobby = & $NetPair.First $ctx.LogLines '\[net\] game round start -> StartGameMode mode=15'
    $laA = @(); if ($liLobby -ge 0) { for ($i = $liLobby; $i -lt $ctx.LogLines.Count; $i++) { if ($ctx.LogLines[$i] -match $lRx) { $laA += [int]$Matches[1] } } }
    return @{ Pass = $false; Detail = ("no restart-apply to count from; in the lobby {0} census sample(s), max alive={1}" -f $laA.Count, $(if ($laA.Count) { ($laA | Measure-Object -Maximum).Maximum } else { '-' })) }
  }
  $liMax = -1; $liN = 0
  for ($i = $liFrom; $i -lt $ctx.LogLines.Count; $i++) {
    if ($ctx.LogLines[$i] -match $lRx) { $liN++; if ([int]$Matches[1] -gt $liMax) { $liMax = [int]$Matches[1] } }
  }
  return @{ Pass = ($liMax -gt 0); Detail = ("{0} census sample(s) after the restart, max alive={1}" -f $liN, $liMax) }
}.GetNewClosure()

@{
  Name    = "net_lan_traffic_$Role"
  Area    = 'network'
  Bug     = "wave 3 -- the $Role half of net_lan_traffic (run it through tools\tests\run_pair.ps1)"
  Frames  = $true
  Run     = $lRun
  DiagEnv = "$($lR.Harness),BRN_NET_DELAY=30,BRN_TRAFFIC_TRACK=1"
  Setup   = (& $NetPair.Setup $Role)
  Checks  = @(
    @{ Kind = 'LogCount'; Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';     Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'LogMatch'; Name = 'the lobby game started (mode 15)'; Pattern = '\[net\] game round start -> StartGameMode mode=15'; Expect = $true }
    @{ Kind = 'LogCount'; Name = 'the active-hull table is filled (no mbActiveHullsValid assert)'; Pattern = '\[ASSERT \d+\] mbActiveHullsValid'; Max = 0 }
    @{ Kind = 'Script';   Name = 'traffic restarted once, with both players'' hulls'; Script = $lRestartCheck }
    @{ Kind = 'LogMatch'; Name = 'the restart reached the traffic module (action 236)'; Pattern = '\[nettraf\] action236 '; Expect = $true }
    @{ Kind = 'LogCount'; Name = 'traffic state hashed (>= 20 hash lines)'; Pattern = '\[nettraf\] hash upd=\d+'; Min = 20 }
    @{ Kind = 'LogCount'; Name = 'no traffic divergence'; Pattern = '\[nettraf\] DIVERGED'; Max = 0 }
    @{ Kind = 'Script';   Name = 'traffic exists after the restart'; Script = $lAliveCheck }
    @{ Kind = 'LogMatch'; Name = $lR.HullWhat; Pattern = $lR.HullRx; Expect = $true }
  )
}
