# vw_crashcam_wall -- a 70 m/s wall hard stop gets the crash camera at the impact (lane CRASHCAM).
#
# Wraps upstream's b5-decomp\tests\PlaytestCrashGyroClockLive.ps1 (the proven wall stimulus,
# 3249.796,-3.7,-1925.404 heading 225 at 70 m/s). Two harness defects in that case, measured on
# exe 15:29:
#   1. It fires shot 0 4 m after the junkyard exit WITHOUT BRN_SWEEP_WAIT_ROAMING, i.e. while the
#      arbitrator is still in ArbStateCarSelect playing the junkyard outro take (JY_MC_Outro). The
#      outro holds the camera until its take finishes, so the car hit the wall and tumbled to a near
#      stop in real time on the outro camera, and only then got ArbStateCrashing and its slow
#      motion (20261008_170516: crash record opened between motion samples 750 and 780, container
#      -> 2 after sample 1020, i.e. ~250 sim frames late).
#      That is the console's ordering for a crash inside the outro, not a crash-camera fault, and
#      it is not what the case means to measure.
#   2. With the wait in place the first far placement can seat 139 m up (PlaceCarOnTrack finds no
#      road before the district streams in; PlaytestCrashGyroGlancingLive 20261008_170815 shot 0).
#      The freeburn case's staged sweep is the cure: a zero-speed placement first, then the shot.
# Its slow-truck check also cannot pass here: a head-on wall hit is a HardStop crash (crash
# analysis flags 105, hardstopVsWall 1), and ArbStateCrashing films it with the HardStop moment
# (weight 1.0, not inhibitable); MomentTumbling's LEAD gyro candidate fails its visibility policy
# against the wall every frame, so no gyro rig is trucking. That check is not carried over; the
# slowed-truck evidence lives in vw_crashcam_takedown_truck.
#
# The impact point is not fixed: in 20261008_170516 the car struck at 3171,-2004 about 110 m from
# the launch; in this case's GREEN run 20261008_174057 it passed that spot on the same line and hit
# a wall at 2074,-2392 (still a wall hard stop, crash type 3, 121 mph). Every check below reads the
# FIRST crash after the seated shot, wherever it happens.
#
# What this case pins:
#   * the crash camera takes over at the impact: no [motion] sample between the crash record
#     opening and the container entering ArbStateCrashing;
#   * the HardStop moment is the selected crash camera, valid, with its ultra slow motion;
#   * camera-pool witness (BRN_CAMPOOL_DIAG): every GyroCam rig lives in the SMALL pool, no pool
#     ever runs out, the small pool keeps at least one slot free.
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case vw_crashcam_wall
$root = Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$case = & (Join-Path $root 'b5-decomp\tests\PlaytestCrashGyroClockLive.ps1')
$case.Name = 'vw_crashcam_wall'
$case.Run.MaxSeconds = 100
$case.Run.CrashSweepShots = '45:0,225:70'
$case.Run.CrashSweepSettle = 600
$case.DiagEnv = 'BRN_CAMERA_RIG_DIAG=1,BRN_CRASHCAM_DIAG=1,BRN_DIRECTOR_TRACE=1,BRN_BLACKBARS_DIAG=1,BRN_CAMPOOL_DIAG=1,BRN_SWEEP_WAIT_ROAMING=1,BRN_FRAME_DUMP_ARM=slomo,BRN_FRAME_DUMP_MAX=240'
$case.Checks = @(
    @{Kind='Mark';Name='reached driving';Phase='DRIVING'}
    @{Kind='LogMatch';Name='the wall shot fired';Pattern='\[sweep\] shot 1/2'}
    @{Kind='LogCount';Name='the wall shot is not a bad seat';Pattern='SEAT BAD shot 1';Max=0}
    @{Kind='LogMatch';Name='the wall shot is seated on the road';Pattern='\[sweep\] seat ok shot 1'}
    @{Kind='Script';Name='the crash camera takes over at the impact';Script={
        param($ctx)
        $after=$false; $open=$false; $samples=0; $entered=$false; $type=$null
        foreach($line in $ctx.LogLines) {
            if($line -match '\[sweep\] seat ok shot 1') {$after=$true; continue}
            if(!$after) {continue}
            if(!$open) { if($line -match '\[crash-exit\] OPENED crash record for active race car 0') {$open=$true}; continue }
            if(!$entered) {
                if($line -match '^\[motion\] ') {$samples++}
                if($line -match '\[crashcam\] container current state -> 2 \(ArbStateCrashing\)') {$entered=$true}
                continue
            }
            if($line -match '\[crashcam\] crash camera: moment type=(?<t>-?\d+) valid=1') {$type=[int]$Matches.t; break}
        }
        @{Pass=($open -and $entered -and $samples -eq 0 -and $type -eq 0)
          Detail="crash record opened=$open, ArbStateCrashing entered=$entered after $samples [motion] sample(s), first valid crash moment type=$type (0 = HardStop)"}
    }}
    @{Kind='LogMatch';Name='the HardStop moment went valid with its ultra slow motion';Pattern='\[crashcam\] hardstop VALID after \d+ preparing frames, using \w \(ultra slo-mo\)'}
    @{Kind='LogMatch';Name='the slow motion reached the world clock';Pattern='\[slomo\] FILM LATCH raised on dilation episode'}
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
    @{Kind='LogCount';Name='no assertions';Pattern='\[ASSERT(?:\s|\])';Max=0}
    @{Kind='LogCount';Name='no exceptions';Pattern='\[EXCEPTION\]';Max=0}
)
$case
