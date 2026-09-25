# net_lan_traffic_crash -- a traffic car the GUEST crashes into is replicated to the HOST: the crash is
# owned by the guest's race car, its transforms go out (msg 16) and the host's crash module plays them
# back on the same traffic vehicle (scratch\net_wave3\MAP_TRAFFIC.md s.0 item 4 and chain E).
#
# Run it (a PAIR case -- see net_lan_pair.ps1 for how pair cases work):
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_pair.ps1 -Case net_lan_traffic_crash
#
# NEEDS online traffic to exist first (net_lan_traffic GREEN: lanes TA T1-T3), then lane TB's
# CrashModule::HandleNetworkCrashingTraffic. Until then it is RED at "no crash-own" / "no crash-in".
#
# THE SET-UP. The traffic_soak_ram spot: the Guest is placed behind parked traffic car 553 at
# 3390.2,0.2,-1620.0 heading 182 and rams it (throttle 3 s at DRIVING+85 s, after the lobby's traffic
# restart); the Host is placed 30 m behind the Guest facing the same way, so its camera looks at the
# crash (frames every 300 presents). ⚠ Car 553 is a STATIC (parked) vehicle offline; if the online
# restart does not keep it, pick a moving car from a net_lan_traffic run's [traffic-track] lines and
# move the Guest spot (the check below does not name a vehicle id, only that both halves agree).
#
# THE ORACLE ([nettraf] witnesses, site words in scratch\net_wave3\CONTRACTS.md)
#   Guest  [nettraf] crash-own veh=<V> pos=(x, y, z)          CrashModule::GenerateOwnedTrafficUpdates
#   Host   [nettraf] crash-in veh=<V> owner=<arc> pos=(...)    CrashModule::HandleNetworkCrashingTraffic
#   PAIR   some vehicle V is crash-own on the Guest and crash-in on the Host, and one of the Host's
#          positions for V is within 2 m of one of the Guest's (the host plays the owner's transforms
#          back 1 s late, so compare against every owner sample, not the same line index)
param([string]$Role = '')
. (Join-Path $PSScriptRoot '..\_net_pair_common.ps1')

$lPairRoles = [ordered]@{
  Host  = @{ Other = 'Guest'; Harness = 'BRN_NET_HOST=1'; Spot = '3390.2,0.2,-1590.0,182'; Drives = $false; Rx = '\[nettraf\] crash-in veh=';  What = 'a remote crash arrived (crash-in)' }
  Guest = @{ Other = 'Host';  Harness = 'BRN_NET_JOIN=1'; Spot = '3390.2,0.2,-1620.0,182'; Drives = $true;  Rx = '\[nettraf\] crash-own veh='; What = 'its own traffic crash was published (crash-own)' }
}

$lCrashAgree = {
  param($p)
  $lRxO = '\[nettraf\] crash-own veh=(\d+) pos=\(([-0-9.]+), ([-0-9.]+), ([-0-9.]+)\)'
  $lRxI = '\[nettraf\] crash-in veh=(\d+) owner=\S+ pos=\(([-0-9.]+), ([-0-9.]+), ([-0-9.]+)\)'
  $lInv = [Globalization.CultureInfo]::InvariantCulture
  $laOwn = @($p.Halves['Guest'].LogLines | Where-Object { $_ -match $lRxO } | ForEach-Object { $null = $_ -match $lRxO; ,@([int]$Matches[1], [double]::Parse($Matches[2], $lInv), [double]::Parse($Matches[3], $lInv), [double]::Parse($Matches[4], $lInv)) })
  $laIn  = @($p.Halves['Host'].LogLines  | Where-Object { $_ -match $lRxI } | ForEach-Object { $null = $_ -match $lRxI; ,@([int]$Matches[1], [double]::Parse($Matches[2], $lInv), [double]::Parse($Matches[3], $lInv), [double]::Parse($Matches[4], $lInv)) })
  if ($laOwn.Count -eq 0 -or $laIn.Count -eq 0) { return @{ Pass = $false; Detail = ("guest crash-own {0} line(s), host crash-in {1} line(s)" -f $laOwn.Count, $laIn.Count) } }
  $lfBest = [double]::MaxValue; $liVeh = -1
  foreach ($li in $laIn) {
    foreach ($lo in $laOwn) {
      if ($li[0] -ne $lo[0]) { continue }
      $lfD = [Math]::Sqrt(($li[1] - $lo[1]) * ($li[1] - $lo[1]) + ($li[2] - $lo[2]) * ($li[2] - $lo[2]) + ($li[3] - $lo[3]) * ($li[3] - $lo[3]))
      if ($lfD -lt $lfBest) { $lfBest = $lfD; $liVeh = $li[0] }
    }
  }
  if ($liVeh -lt 0) { return @{ Pass = $false; Detail = ("no vehicle id in both: guest owns [{0}], host received [{1}]" -f (($laOwn | ForEach-Object { $_[0] } | Sort-Object -Unique) -join ' '), (($laIn | ForEach-Object { $_[0] } | Sort-Object -Unique) -join ' ')) } }
  return @{ Pass = ($lfBest -le 2.0); Detail = ("vehicle {0}: closest host playback sample is {1:f2} m from a guest owner sample" -f $liVeh, $lfBest) }
}

if ($Role -eq '') {
  return @{
    Name = 'net_lan_traffic_crash'
    Area = 'network'
    Bug  = 'wave 3 -- a traffic car crashed by one lobby player is replayed on the other instance'
    Pair = @{ Roles = @($lPairRoles.Keys); Slots = @(1, 2)
              Checks = @( @{ Name = 'the Guest''s crashed traffic car is played back on the Host (same vehicle, <= 2 m)'; Script = $lCrashAgree } ) }
  }
}
if (-not $lPairRoles.Contains($Role)) { throw "net_lan_traffic_crash: unknown -Role '$Role' (Host or Guest)" }
$lR = $lPairRoles[$Role]

$lRun = @{ MaxSeconds = 150; SkipIntro = $true; AcceptGap = 1.0; Teleport = $lR.Spot; FrameEvery = 300 }
if ($lR.Drives) {
  $lRun['Drive']          = $true
  $lRun['DriveDelay']     = 85.0
  $lRun['ThrottleScript'] = '0:accel,3:none'
}

@{
  Name    = "net_lan_traffic_crash_$Role"
  Area    = 'network'
  Bug     = "wave 3 -- the $Role half of net_lan_traffic_crash (run it through tools\tests\run_pair.ps1)"
  Frames  = $true
  Run     = $lRun
  DiagEnv = "$($lR.Harness),BRN_NET_DELAY=30,BRN_TRAFFIC_TRACK=1"
  Setup   = (& $NetPair.Setup $Role)
  Checks  = @(
    @{ Kind = 'LogCount'; Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';     Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'LogMatch'; Name = 'the lobby game started (mode 15)'; Pattern = '\[net\] game round start -> StartGameMode mode=15'; Expect = $true }
    @{ Kind = 'LogMatch'; Name = 'online traffic restarted'; Pattern = '\[nettraf\] restart-apply '; Expect = $true }
    @{ Kind = 'LogMatch'; Name = 'the crash-exit PARK line is gone'; Pattern = 'HandleNetworkCrashingTraffic is not reconstructed'; Expect = $false }
    @{ Kind = 'LogMatch'; Name = $lR.What; Pattern = $lR.Rx; Expect = $true }
  )
}
