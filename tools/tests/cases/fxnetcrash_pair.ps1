# fxnetcrash_pair -- crash parity FX-NETCRASH (2026-09-24). TWO game instances in one online
# free-burn lobby over the PC LAN backend; the HOST rams a traffic car, and the GUEST replays that
# wreck from the host's crashing-traffic updates:
#   host  CrashModule::GenerateOwnedTrafficUpdates (0x827C53F0) publishes the owned wreck's
#         transform -> network TrafficManager::SendCrashingTrafficMessages (round robin)
#   guest TrafficManager::ReceiveCrashingTrafficMessages (applied one second late) -> the crash
#         module's NetworkInputInterface -> CrashModule::HandleNetworkCrashingTraffic (0x827CB788,
#         called from PreSceneUpdate 0x827D3B64, b5 6c535ee9) -> VehicleInputInterface::
#         UpdateNetworkTraffic -> PhysicalTrafficManager::ProcessUpdateNetworkTrafficEvents
#         (0x8262CED0) -> UpdateNetworkTrafficVehicle (0x8261CBD0) arms the catch-up that moves the
#         guest's copy.
#
# Run it (a PAIR case -- see net_lan_pair.ps1 for how pair cases work). While a pair runs, hold the
# SLOT-0 box lock (the pair itself uses slots 1 and 2):
#   . tools\diagnostics\_box_lock.ps1; Enter-BoxLock -TimeoutSec 7200 -Label FX-NETCRASH-pair -Slot 0
#   & tools\tests\run_pair.ps1 -Case fxnetcrash_pair
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_pair.ps1 -Case fxnetcrash_pair -NoRun -RunDir <pair run dir>
#
# THE SET-UP. Same halves as net_lan_see (BP_LAN=1, BRN_NET_HOST / BRN_NET_JOIN, BRN_NET_DELAY=30;
# the teleport is done at boot, before the lobby exists, and the lobby start keeps each local car
# where it is):
#   Host  -> 150 m up-road of the parked traffic car at (3390.2, 0.17, -1641.1) (traffic_soak_ram's
#            car 553; its id changes after the online traffic restart, 579 in run 20260925_101502),
#            on that car's own at-vector (182 deg). Once the lobby is up and the traffic restarted
#            (flow_run -Drive, 80 s after DRIVING -- net_lan_see's guest drives at 75 s) the throttle
#            is pinned. The run-up is what decides the outcome:
#            VehicleManager::DecideOutcomeOfRaceCarTrafficContact CHECKS the traffic car only when
#            impactSpeed * raceCarMass / trafficMass > 30 (the tail at 0x825C7500), otherwise it
#            SLAMS it, and only a CHECKED car becomes a crashing traffic car
#            (eCrashTrafficType_Checked) the host OWNS. Measured: soak_ram's 21 m run-up reaches
#            36.7 mph and slams (magnitude 17.6, run 20260925_101502); the old claim here that it
#            gives "SLAMMED then CHECKED" is stale. 150 m buys the ~61 mph a check needs.
#   Guest -> the same road 30 m BEHIND the host, facing the same way, never driving: close enough
#            that the parked car's hull is active in the guest's world too, and out of the host's path.
#
# THE ORACLE (capped, default-off witness lines; BRN_NETCRASH_DIAG=1 on both halves):
#   Host   [traffic-crash] added vehicle=V owner=O ...              (BRN_CRASH_ACTION_DIAG) the ram
#          [netcrash] GenerateOwnedTrafficUpdates owner=O published=N first=V ...  N >= 1
#   Guest  [netcrash] HandleNetworkCrashingTraffic player=P updates=N ... first=V ...  N >= 1
#          [netcrash] UpdateNetworkTrafficVehicle slot=S global=V before=(..) target=(..) after=(..)
#                     snapped=0|1 steps=K        -- the car HandleNetworkCrashingTraffic named MOVED
#                     (a snap moves it inside the call; otherwise the armed slerp moves it over the
#                     next frames, which a later line's `before` shows)
#   Both   0 [ASSERT n] lines, 0 [EXCEPTION] lines, DRIVING reached, the lobby game started.
param([string]$Role = '')

# The host's line: a throttle-only drive holds its 182 deg heading (at = (-0.0349, -0.9994)), so it
# drifts 0.0349 m in x per metre -- 5.2 m over the run-up, which MISSED the parked car at x 3390.2
# in run 20260925_105022 (the host passed at x 3384.3, 38 m/s). Start 5.2 m to the right instead.
$lsHostSpot  = '3395.4,0.2,-1491.1,182'   # 150 m up-road of the parked car (a CHECK needs ~61 mph)
$lsGuestSpot = '3396.4,0.2,-1461.1,182'   # 30 m behind the host on the same line, out of its path

$lPairRoles = [ordered]@{
  Host  = @{ Other = 'Guest'; Harness = 'BRN_NET_HOST'; Spot = $lsHostSpot;  Rams = $true  }
  Guest = @{ Other = 'Host';  Harness = 'BRN_NET_JOIN'; Spot = $lsGuestSpot; Rams = $false }
}

if ($Role -eq '') {
  return @{
    Name = 'fxnetcrash_pair'
    Area = 'network'
    Bug  = 'crash parity FX-NETCRASH -- the host''s crashing traffic reaches the guest (HandleNetworkCrashingTraffic) and moves the guest''s copy (UpdateNetworkTrafficVehicle)'
    Pair = @{ Roles = @($lPairRoles.Keys); Slots = @(1, 2) }
  }
}
if (-not $lPairRoles.Contains($Role)) { throw "fxnetcrash_pair: unknown -Role '$Role' (Host or Guest)" }
$lR = $lPairRoles[$Role]
$lsMe = $Role

$lRun = @{
  MaxSeconds = 170
  SkipIntro  = $true
  AcceptGap  = 1.0
  Teleport   = $lR.Spot
}
if ($lR.Rams) {
  $lRun['Drive']          = $true
  $lRun['DriveDelay']     = 80.0
  $lRun['ThrottleScript'] = '0:accel'
}

$lSetup = {
  param($ctx)
  $env:BP_LAN = '1'
  $env:BP_LAN_NAME = $lsMe
  Remove-Item Env:\BP_LAN_XUID -ErrorAction SilentlyContinue
  Write-Host ("[case] {0}: BP_LAN=1 BP_LAN_NAME={0}" -f $lsMe)
  return $null
}.GetNewClosure()

$lCulture = [Globalization.CultureInfo]::InvariantCulture

# HOST: a traffic crash record made ONLINE. Traffic that hits the parked host before the lobby (run
# 20260925_105022: vehicle 278, offline) also writes '[traffic-crash] added', so only lines after the
# first online traffic restart ('[netcrash] HandleExternalRequests RESTART_TRAFFIC') count.
$lOnlineCrashCheck = {
  param($ctx)
  $lbOnline = $false
  $laHits = @()
  foreach ($lsLine in $ctx.LogLines) {
    if (-not $lbOnline) { if ($lsLine -match '\[netcrash\] HandleExternalRequests RESTART_TRAFFIC') { $lbOnline = $true }; continue }
    if ($lsLine -match '\[traffic-crash\] added vehicle=\d+ owner=\d+') { $laHits += $lsLine.Trim() }
  }
  if (-not $lbOnline) { return @{ Pass = $false; Detail = 'the online traffic restart never happened (no RESTART_TRAFFIC line)' } }
  if ($laHits.Count -eq 0) { return @{ Pass = $false; Detail = 'no traffic crash record after the online traffic restart' } }
  return @{ Pass = $true; Detail = ("{0} crash record(s) after the restart; first: {1}" -f $laHits.Count, $laHits[0]) }
}.GetNewClosure()

# HOST: the ram produced a wreck this machine owns, and the crash module published it.
$lPublishCheck = {
  param($ctx)
  $lRx = '\[netcrash\] GenerateOwnedTrafficUpdates owner=(-?\d+) published=(\d+) crashes=(\d+) first=(\d+)'
  $lHits = @($ctx.LogLines | Where-Object { $_ -match $lRx })
  if ($lHits.Count -eq 0) {
    $lAdded = @($ctx.LogLines | Where-Object { $_ -match '\[traffic-crash\] added vehicle=' } | Select-Object -First 2)
    return @{ Pass = $false; Detail = ("no GenerateOwnedTrafficUpdates publish line; traffic crashes recorded: {0}" -f
                                       $(if ($lAdded.Count) { $lAdded -join ' | ' } else { '(none -- the ram crashed nothing)' })) }
  }
  $null = $lHits[0] -match $lRx
  return @{ Pass = $true; Detail = ("{0} publish line(s); first: {1}" -f $lHits.Count, $lHits[0].Trim()) }
}.GetNewClosure()

# GUEST: HandleNetworkCrashingTraffic consumed >= 1 crashing-traffic update, and
# UpdateNetworkTrafficVehicle moved a car it named.
$lConsumeCheck = {
  param($ctx)
  $lRx = '\[netcrash\] HandleNetworkCrashingTraffic player=(-?\d+) updates=(\d+) posted=(\d+) new=(\d+) cleared=(\d+) first=(\d+)'
  $lHits = @($ctx.LogLines | Where-Object { $_ -match $lRx })
  if ($lHits.Count -eq 0) { return @{ Pass = $false; Detail = 'no HandleNetworkCrashingTraffic line -- no crashing-traffic update reached the crash module' } }
  $liMax = 0
  foreach ($lsLine in $lHits) { $null = $lsLine -match $lRx; $liMax = [Math]::Max($liMax, [int]$Matches[2]) }
  return @{ Pass = ($liMax -ge 1); Detail = ("{0} line(s), max updates {1}; first: {2}" -f $lHits.Count, $liMax, $lHits[0].Trim()) }
}.GetNewClosure()

$lMoveCheck = {
  param($ctx)
  $lRxH = '\[netcrash\] HandleNetworkCrashingTraffic player=-?\d+ updates=\d+ posted=\d+ new=\d+ cleared=\d+ first=(\d+)'
  $lNamed = @{}
  foreach ($lsLine in $ctx.LogLines) { if ($lsLine -match $lRxH) { $lNamed[$Matches[1]] = $true } }
  if ($lNamed.Count -eq 0) { return @{ Pass = $false; Detail = 'HandleNetworkCrashingTraffic named no vehicle' } }
  $lsNum = '(-?[0-9.eE+-]+)'
  $lRxU = '\[netcrash\] UpdateNetworkTrafficVehicle slot=(\d+) global=(\d+) before=\(' + $lsNum + ', ' + $lsNum + ', ' + $lsNum +
          '\) target=\(' + $lsNum + ', ' + $lsNum + ', ' + $lsNum + '\) after=\(' + $lsNum + ', ' + $lsNum + ', ' + $lsNum + '\) snapped=(\d)'
  $lPer = @{}
  $liLines = 0
  foreach ($lsLine in $ctx.LogLines) {
    if ($lsLine -notmatch $lRxU) { continue }
    ++$liLines
    $lsG = $Matches[2]
    if (-not $lNamed.ContainsKey($lsG)) { continue }
    $laB = @([double]::Parse($Matches[3], $lCulture), [double]::Parse($Matches[4], $lCulture), [double]::Parse($Matches[5], $lCulture))
    $laA = @([double]::Parse($Matches[9], $lCulture), [double]::Parse($Matches[10], $lCulture), [double]::Parse($Matches[11], $lCulture))
    if (-not $lPer.ContainsKey($lsG)) { $lPer[$lsG] = @{ First = $laB; Last = $laA; Step = 0.0; Snaps = 0; Lines = 0 } }
    $lE = $lPer[$lsG]
    $lE.Last = $laA
    $lE.Lines++
    if ($Matches[12] -eq '1') { $lE.Snaps++ }
    $lfStep = [Math]::Sqrt(($laA[0]-$laB[0])*($laA[0]-$laB[0]) + ($laA[1]-$laB[1])*($laA[1]-$laB[1]) + ($laA[2]-$laB[2])*($laA[2]-$laB[2]))
    $lE.Step = [Math]::Max($lE.Step, $lfStep)
  }
  if ($lPer.Count -eq 0) {
    return @{ Pass = $false; Detail = ("{0} UpdateNetworkTrafficVehicle line(s), none for a vehicle HandleNetworkCrashingTraffic named ({1})" -f
                                       $liLines, (@($lNamed.Keys) -join ',')) }
  }
  $laWhy = @()
  $lbMoved = $false
  foreach ($lsG in $lPer.Keys) {
    $lE = $lPer[$lsG]
    $lfSpan = [Math]::Sqrt(($lE.Last[0]-$lE.First[0])*($lE.Last[0]-$lE.First[0]) + ($lE.Last[1]-$lE.First[1])*($lE.Last[1]-$lE.First[1]) + ($lE.Last[2]-$lE.First[2])*($lE.Last[2]-$lE.First[2]))
    if ($lE.Step -gt 0.01 -or $lfSpan -gt 0.05) { $lbMoved = $true }
    $laWhy += ("global {0}: {1} line(s), {2} snap(s), max in-call move {3:f3} m, first-before -> last-after {4:f3} m" -f
               $lsG, $lE.Lines, $lE.Snaps, $lE.Step, $lfSpan)
  }
  return @{ Pass = $lbMoved; Detail = ($laWhy -join '; ') }
}.GetNewClosure()

$lChecks = @(
  @{ Kind = 'LogCount'; Name = 'no exceptions (0 AV)'; Pattern = '\[EXCEPTION\]'; Max = 0 }
  @{ Kind = 'LogCount'; Name = 'no asserts'; Pattern = '^\[ASSERT \d+\]'; Max = 0 }
  @{ Kind = 'Mark';     Name = 'reached DRIVING'; Phase = 'DRIVING' }
  @{ Kind = 'LogMatch'; Name = 'the lobby game started (case 18 -> StartGameMode mode 15)'; Pattern = '\[net\] game round start -> StartGameMode mode=15'; Expect = $true }
)
if ($lR.Rams) {
  $lChecks += @(
    @{ Kind = 'Script';   Name = 'the ram crashed a traffic car AFTER the online traffic restart'; Script = $lOnlineCrashCheck }
    @{ Kind = 'Script';   Name = 'GenerateOwnedTrafficUpdates published the owned wreck'; Script = $lPublishCheck }
  )
} else {
  $lChecks += @(
    @{ Kind = 'Script';   Name = 'HandleNetworkCrashingTraffic consumed >= 1 crashing-traffic update'; Script = $lConsumeCheck }
    @{ Kind = 'Script';   Name = 'UpdateNetworkTrafficVehicle moved the car HandleNetworkCrashingTraffic named'; Script = $lMoveCheck }
  )
}

$lsDiag = "$($lR.Harness)=1,BRN_NET_DELAY=30,BRN_NETCRASH_DIAG=1,BRN_CRASH_ACTION_DIAG=1"
if ($lR.Rams) { $lsDiag += ',BRN_TRAFFIC_DIAG=1' }

@{
  Name    = "fxnetcrash_pair_$Role"
  Area    = 'network'
  Bug     = "crash parity FX-NETCRASH -- the $Role half of fxnetcrash_pair (run it through tools\tests\run_pair.ps1)"
  Frames  = $false
  Run     = $lRun
  DiagEnv = $lsDiag
  Setup   = $lSetup
  Checks  = $lChecks
}
