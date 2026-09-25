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
#   Host  -> 95 m up the east parking lane from parked car 579 (static, identical on both halves since the
#            traffic runs in lockstep; (3390.21, 0.17, -1641.10)), heading 180, aimed straight at it. Once
#            the lobby is up and the traffic restarted (flow_run -Drive, 80 s after DRIVING) the throttle
#            is pinned for the rest of the run.
#   Guest -> (3392.0, -1700.0) heading 0, 59 m beyond car 579 in the same lane, never driving.
#
# WHAT THIS LAYOUT GIVES, AND WHAT NO LAYOUT HAS GIVEN YET (all measured on the wave-3 exe):
#   - The ram at car 579 is a CHECK (~69 mph), and a check makes no crash record with the harness car:
#     PhysicalTrafficVehicle::OnChecked @0x8261E360 arms the checked BODY's crash only for a checker
#     strength > 8 (lbz 0x140E @0x8261E3F0 / cmplwi 8 / ble 0x8261E3F8; the harness car is 5), and even
#     then SetTrafficVehicleChecked @0x8262D748 posts only the SLAMMED event (li r9, 3 @0x8262D9BC ->
#     TrafficSlammedEvent::AddEvent 0x8262D9F8), which HandleExternalResponses' loop 2 records with
#     mbNeedsToBeSentToCrashModule = false. Run 20260925_132839 (BRN_STRENGTH_STAT_OVERRIDE=10):
#     "[T4-hit] outcome=CHECKED ... checkerStrength=10 trafficCrashingAfter=1" and still no record.
#   - The host's owned crash records come later, wherever the pinned throttle takes it: mostly
#     PhysicalTrafficManager::TestForNearMissFreakOut @0x82637A30 (a race car >= 60 mph brushing past
#     the front of a FULL-physical traffic car doing >= 15 mph -> SetTrafficVehicleCrashing with the
#     race car as crasher: "[T4-hit] outcome=CRASHING ... crasherOwner=1 crasherIdx=0" then NEARMISS),
#     hundreds of metres to kilometres on.
#   - The guest keeps a copy only inside the console's 150 m camera cull:
#     TrafficEntityModule::TryClearupOffscreenTraffic @0x8273C4C8 (called by GenerateDriverInputs for
#     every physical traffic car, every frame) RemoveVehicle's (0x8273CAD0) a physical car that was NOT
#     rendered last frame and is farther than flt_8200D50C = 22500 (150 m, squared) from
#     mCameraLastFrame (+0x728C0) -- the LOCAL camera.
#   - So for a far wreck the guest's witness is ONE line, and only when its copy is still alive and not
#     physical when the first update lands: HandleNetworkCrashingTraffic posts it, the copy is promoted,
#     UpdateNetworkTrafficVehicle snaps it, and the cull removes it in the same frame chain. Run
#     20260925_124335 (this layout): car 78, 1.48 km on, "UpdateNetworkTrafficVehicle slot=0
#     global=78 ... snapped=1" once -> GREEN. When the host's NETWORK car touched the car on the guest
#     first (slam or check), the copy was physical, far, and culled before the update -> RED: runs
#     20260925_115458 / _122225 (car 270) and _132839 (car 386: "outcome=CHECKED ... raceCarIdx=1"
#     then "[T3-demote] ... vehicle 386 ... clearupKills 3" before the first "posted=1").
#   - Layouts that tried to put the wreck inside 150 m of the guest, and why they failed:
#     - guest 30 m behind the host's start (runs _115458 / _122225): first wreck ~800 m on;
#     - host waiting WRONG-WAY in the inner northbound lane for a head-on (run _131154): northbound
#       cars swerved round the waiting host and crashed on BOTH halves, each owned by its own local
#       player (UpdateVehiclesJob::UpdateVehicle's swerve promotion targets params+0x74, the local
#       player, 0x8291DB34..0x8291DC40), so the guest applied none of the host's updates ("posted=0"),
#       and the host then met no oncoming car in 335 m;
#     - a strength-10 check of car 579 with the guest 26 m behind the host (run _132839): no record
#       (above);
#     - host angled (183) from the parking lane across both southbound lanes into the northbound
#       ones, guest 180 m down the parking lane (run _140405): no contact at all in that stretch; the
#       first record (car 260, a near miss at 119 mph) came 360 m from the guest -> culled, RED.
#   The first owned wrecks of runs _110031, _131154 and _140405 all fell on the SW-bound road at
#   (3262..3282, -1917..-1889), 480 m down the host's route: that stretch carries traffic both ways.
#   Re-run of this exact layout on a newer exe (run _135054, b5 335639ce): no owned record at all -> RED.
#   So this case is GREEN only when the drive happens to make a record whose guest copy survives to
#   the first update; a layout that keeps the observer within 150 m of the wreck is still open.
#   This layout also stands the guest on the line the host takes after the check; in run _124335 the
#   host ran into it and shoved it 50 m. That changes nothing the checks read.
#
# THE ORACLE (capped, default-off witness lines; BRN_NETCRASH_DIAG=1 on both halves):
#   Host   [traffic-crash] added vehicle=V owner=O ...              (BRN_CRASH_ACTION_DIAG) the ram
#          [netcrash] GenerateOwnedTrafficUpdates owner=O published=N first=V ...  N >= 1
#   Guest  [netcrash] HandleNetworkCrashingTraffic player=P updates=N posted=M ... first=V ...  M >= 1
#                     (posted = the updates accepted for that player; 0 when the guest owns the crash itself)
#          [netcrash] UpdateNetworkTrafficVehicle slot=S global=V before=(..) target=(..) after=(..)
#                     snapped=0|1 steps=K        -- the car HandleNetworkCrashingTraffic named MOVED
#                     (a snap moves it inside the call; otherwise the armed slerp moves it over the
#                     next frames, which a later line's `before` shows)
#   Both   0 [ASSERT n] lines, 0 [EXCEPTION] lines, DRIVING reached, the lobby game started.
param([string]$Role = '')

# See THE SET-UP above for both spots.
$lsHostSpot  = '3390.2,0.2,-1546.0,180'   # 95 m up the parking lane from parked car 579, aimed at it
$lsGuestSpot = '3392.0,0.2,-1700.0,0'     # 59 m beyond car 579 (run 20260925_124335's layout)

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
  $laPosted = @($lHits | Where-Object { $null = $_ -match $lRx; [int]$Matches[3] -ge 1 })
  if ($laPosted.Count -eq 0) {
    return @{ Pass = $false; Detail = ("{0} line(s), none with posted >= 1 (every update was for a crash this machine owns itself); first: {1}" -f
                                       $lHits.Count, $lHits[0].Trim()) }
  }
  return @{ Pass = $true; Detail = ("{0} line(s), {1} with posted >= 1; first posted: {2}" -f $lHits.Count, $laPosted.Count, $laPosted[0].Trim()) }
}.GetNewClosure()

$lMoveCheck = {
  param($ctx)
  $lRxH = '\[netcrash\] HandleNetworkCrashingTraffic player=-?\d+ updates=\d+ posted=([1-9]\d*) new=\d+ cleared=\d+ first=(\d+)'
  $lNamed = @{}
  foreach ($lsLine in $ctx.LogLines) { if ($lsLine -match $lRxH) { $lNamed[$Matches[2]] = $true } }
  if ($lNamed.Count -eq 0) { return @{ Pass = $false; Detail = 'HandleNetworkCrashingTraffic posted no update for any vehicle' } }
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
$lsDiag += ',BRN_TRAFFIC_DIAG=1'   # both halves: the guest's own contact / promotion lines matter too

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
