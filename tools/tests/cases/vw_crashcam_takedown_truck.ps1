# vw_crashcam_takedown_truck -- a live trucking GyroCam on the slowed world clock (lane CRASHCAM).
#
# Wraps upstream's b5-decomp\tests\PlaytestCrashGyroOrganicLive.ps1 (the AI-pad pursuit). On exe
# 15:29 that case went RED on exactly one check, "original tumbling moment selected valid"
# ([crashcam] crash camera: moment type=2 valid=1), while its two slowed-truck checks PASSED with
# 101 rows (20261008_171736). Those rows are not a player crash at all: they are gyro car=1, the
# TAKEDOWN victim, filmed by ArbStateTakedown's B3-classic player (its TUMBLING_TRUCKING_SIDE /
# LEAD_TAKEDOWN_ONLY moments), and the [crashcam] crash-camera line is printed only by
# ArbStateCrashing. The player's own crashes in that run were HardStop (crash type 3 and 2) and
# then the far bystander -- the crash selector's console order (HardStop weight 1.0 and not
# inhibitable; one active inhibitable tumbling moment, the LEAD gyro, which fails its visibility
# policy at a wall every frame and so keeps the trucking-side moment inhibited).
# So the type-2 check is a case defect: the stimulus produces a takedown, not a player tumble.
# This wrapper keeps every other upstream check and replaces that one with the takedown arm that
# actually produced the trucking rows. Frames are sampled every 10th present from the first
# slow motion on so the takedown camera is on film.
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case vw_crashcam_takedown_truck
$root = Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$case = & (Join-Path $root 'b5-decomp\tests\PlaytestCrashGyroOrganicLive.ps1')
$case.Name = 'vw_crashcam_takedown_truck'
$case.Run.FrameEvery = 10
$case.DiagEnv = ($case.DiagEnv -replace 'BRN_FRAME_DUMP_MAX=\d+', 'BRN_FRAME_DUMP_MAX=700') + ',BRN_CAMPOOL_DIAG=1'
$case.Checks = @($case.Checks | Where-Object { $_.Name -ne 'original tumbling moment selected valid' })
$case.Checks += @(
    @{Kind='LogMatch';Name='a takedown handed the camera to ArbStateTakedown';Pattern='\[crashcam\] container current state -> 3 \(ArbStateTakedown\)'}
    @{Kind='Script';Name='the slowed trucking rig films the takedown victim, not the player';Script={
        param($ctx)
        $inv=[cultureinfo]::InvariantCulture; $rows=0; $victims=@{}
        foreach($line in $ctx.LogLines) {
            if($line -notmatch '^\[camera-rig\] gyro car=(?<car>-?\d+) .* worldDt=(?<world>[^ ]+) noSlomoDt=(?<normal>[^ ]+) truck=1 ') {continue}
            $car=$Matches.car; $world=[double]::Parse($Matches.world,$inv); $normal=[double]::Parse($Matches.normal,$inv)
            if($world -gt 0 -and $world -lt $normal) {$rows++; $victims[$car]=1}
        }
        $lsCars = ($victims.Keys | Sort-Object) -join ','
        @{Pass=($rows -ge 1 -and -not $victims.ContainsKey('-1') -and -not $victims.ContainsKey('0')); Detail="slowed truck rows=$rows attached to race car(s) {$lsCars}"}
    }}
    @{Kind='Script';Name='every GyroCam rig lives in the small pool, which never runs dry';Script={
        param($ctx)
        $gyro=0; $gyroSmall=0; $lowSmall=99; $lowLarge=99
        foreach($line in $ctx.LogLines) {
            if($line -notmatch '^\[campool\] (?<ev>[+-]) (?<name>.+?) size (?<size>\d+) pool (?<pool>\w+) \| large free -?\d+ \(low (?<ll>-?\d+)\) small free -?\d+ \(low (?<sl>-?\d+)\)') {continue}
            $ev=$Matches.ev; $name=$Matches.name; $pool=$Matches.pool
            $lowSmall=[math]::Min($lowSmall,[int]$Matches.sl); $lowLarge=[math]::Min($lowLarge,[int]$Matches.ll)
            if($ev -eq '+' -and $name.Contains('GyroCam')) {$gyro++; if($pool -eq 'SMALL') {$gyroSmall++}}
        }
        @{Pass=($gyro -ge 1 -and $gyroSmall -eq $gyro -and $lowSmall -ge 1 -and $lowLarge -ge 1)
          Detail="GyroCam allocations=$gyro (small pool $gyroSmall); low-water free slots small=$lowSmall large=$lowLarge"}
    }}
    @{Kind='LogCount';Name='no camera pool ran out';Pattern='Ran out of slots';Max=0}
)
$case
