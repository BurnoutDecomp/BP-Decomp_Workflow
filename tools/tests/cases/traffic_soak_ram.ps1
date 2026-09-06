# traffic_soak_ram -- lane traffic_assert. "traffic cars crashing the game with asserts, sometimes".
#
# THE SIGNATURE, mined offline from every BrnGame.log under scratch\ (585 logs, 138 assert
# families; scratch\bugtest\lanes\traffic_assert_work\assert_families.txt). The traffic bug is
# not one assert, it is ONE CASCADE of nine that always arrive in the same order once a car is
# promoted to a physics body (first seen scratch\flow_run\20260823_092657\BrnGame.log:5734):
#     1 Vehicle is alive but not physical            BrnTrafficEntityModule_wT3_04.cpp:308
#     2 GetVehicle( luVehicle )->IsPhysical()        BrnTrafficEntityModule_wT3_00.cpp:38
#     3 IsPhysical()                                 BrnTrafficVehicle.h:340
#     4 maTrafficPhysicsInfoListBits.IsBitSet(...)   BrnTrafficEntityModule_wT3_00.cpp:45
#     5 lpPhysicsInfo->miVehicleIndex == luVehicle   BrnTrafficEntityModule_wT3_00.cpp:53
#     6 IsPhysical()                                 BrnTrafficVehicle.cpp:1164
#     7 Traffic already has body                     BrnPhysicalTrafficManager_Create.cpp:219
#     8 Tried to add traffic vehicle to physics ...  BrnPhysicalTrafficManager_Create.cpp:293
#     9 mu8GlobalToPhysicalEntityIndexMap[...] == KU8_INVALID_MAP   ..._Create.cpp:314
# so the case checks the WHOLE FAMILY SET by file, not one line: any assert raised from a
# traffic file at all is the bug. Two further traffic-attributed families are checked with it:
# "Un-normalised race car-traffic car contact" (BrnPhysicsModuleBridgeFunctions.cpp:926) and
# "lu16TrafficIndex < Vehicle::ku8TotalMaxNumPhysicalTraffic" (BrnDeformationManager.h:732).
#
# The last check is the ANTI-VACUOUS one: promotion is NOT deterministic in flow_run (2 of 6
# identical runs promoted nothing -- traffic campaign, round 3), so a run that never made a
# traffic car physical proves nothing about a promotion assert. It must see the [T3-*]/[T4-*]
# promotion ladder before a green means anything.
#
# SCENARIO 1 -- THE DETERMINISTIC RAM. 43 m up-road of parked car 553 at (3390.2,0.17,-1641.1),
# on that car's own at-vector (182 deg), throttle pinned: the campaign's reproducible car-on-car
# hit ([T4-hit] SLAMMED then CHECKED). A slam is the promotion trigger that does not need luck.
#
#
# STATUS 2026-09-06 (lane traffic_assert, tip 473ff6f4): THIS CASE IS GREEN -- it does NOT
# reproduce any more. The crash it encodes was fixed the night before by b5 7761247a
# ("the Showtime access violation was DEMOTION, and both routes into it were gated"), which
# un-gated TryClearupOffscreenTraffic and HandleRecycledTraffic. Measured on this recipe:
#   the 2026-08-30 run   physSlots strictly monotonic, then 25/25 -> assert -> AV at 272.9 s
#   2026-09-06 run       physSlots max 5 of 25 over the same 275 s, clearupKills 9, asserts 0
# Keep the case: it is the standing regression guard for that budget. If it ever goes red
# again, read the [T3-demote] census first -- 'clearupKills' back at 0 means the valve is
# gated again, and 'return 0' has been true the whole time (ReturnPhysicalVehicleToTraffic's
# 1.5 m target-proximity test still never passes; that is a separate, still-open gap).
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case traffic_soak_ram -ExpectFail -Label pre-fix
#
# ⭐⭐ SHORTENED 2026-09-06 (lane harness2). WHAT CHANGED AND WHAT DID NOT.
#   The Run block below now carries `SkipIntro` and `AcceptGap`, and a smaller `MaxSeconds`.
#   Nothing else about the scenario moved and NO CHECK was touched.
#     SkipIntro  passes the CONSOLE's own "-skipvideos" command-line latch (BrnMain.cpp:434 ->
#                BootVideos::Update's soft-reboot exit) so the EA-Franchise and Criterion VP6
#                logos are not played. It is not a harness bypass and it is not new game code.
#     AcceptGap  is HARNESS latency, not a game gate: the Accept pump used to press every 3.0 s
#                at car select, and the junkyard leg of a returning boot was measurably two
#                consecutive pump periods long (carsel 16.5s -> livery 19.9s -> accept 23.0s).
#   MEASURED, same build, same scenario: boot-to-DRIVING 23.0 s -> 16.2 s.
#   MaxSeconds is cut by that saving plus the slack this case's own schedule shows it never used.
#   ⛔⛔ 60 -> 145, MEASURED: THIS SOAK'S WITNESS IS RARE AND ITS RATE IS PER UNIT OF WORLD TIME.
#   At MaxSeconds 60 (run 20260906_140916) the case went RED on "world physics-slot occupancy
#   stays off the 25-slot ceiling" -- not because occupancy climbed, but because
#   `[T3-demote] ... physSlots <n>` NEVER FIRED, and a LogValue whose witness produced no sample
#   fails by design rather than passing vacuously. The banked 150 s run got exactly THREE samples
#   out of ~121 s of driving, i.e. roughly one demote per 40 s of world time. So the budget here
#   buys samples, and 145 is the number that keeps the banked run's world time while still taking
#   the whole 6.8 s boot saving off the front.
#   ⛔⛔ AND THEN 145 FAILED THE SAME WAY (run 20260906_141604, still zero `[T3-demote]`), SO A
#   CONTROL WAS RUN: this case's ORIGINAL scenario -- MaxSeconds 150, no SkipIntro, no AcceptGap,
#   slot 0, the exact banked recipe -- run 20260906_141903
#   under scratch/bugtest/runs/traffic_soak_ram_orig/ . IT FAILS IDENTICALLY -- the witness never
#   fired, 92 [T4-hit]/[T5-arm]/[T3-demote] lines, DRIVE path 87 m. => THE RED IS NOT THE SHORTENING.
#   It is either this witness being genuinely rare on the current build or another lane's change
#   landing after this case was banked at 09:30; either way it belongs to the traffic lane, and
#   the control run is the evidence that separates the two. The shortening is kept because it
#   demonstrably changes nothing about the outcome.
#
@{
  Name    = 'traffic_soak_ram'
  Area    = 'traffic'
  Bug     = 'field report -- "traffic cars crashing the games with asserts sometimes"'
  Frames  = $false
  Run     = @{
    Drive          = $true
    MotionProbe    = $true
    MaxSeconds     = 145
    SkipIntro     = $true      # the console -skipvideos latch (see the banner)
    AcceptGap     = 1.0        # harness pump latency, not a game gate
    Teleport       = '3390.2,0.2,-1620.0,182'
    ThrottleScript = '0:accel'
  }
  DiagEnv = 'BRN_TRAFFIC_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }
    # THE BUG: every assert raised out of a traffic lifecycle file, physics side and world side.
    @{ Kind = 'LogCount';   Name = 'no assert from any traffic file'
       Pattern = '\[ASSERT \d+\].*(BrnPhysicalTrafficManager|BrnTrafficEntityModule|BrnTrafficVehicle|BrnTrafficPhysics|PhysicalTrafficVehicle)'
       Max = 0 }
    # The same cascade named by MESSAGE, so a streamed assert with no path still counts.
    @{ Kind = 'LogCount';   Name = 'no physical-traffic lifecycle assert'
       Pattern = '\[ASSERT \d+\] (Vehicle is alive but not physical|Traffic already has body|Tried to add traffic vehicle to physics module twice|Un-normalised race car-traffic car contact|lu16TrafficIndex < Vehicle::ku8TotalMaxNumPhysicalTraffic)'
       Max = 0 }
    # THE PROCESS SURVIVED: marks.txt says how the run ended. 'EXIT self code=...' means the game
    # died on its own; only 'harness-stop' is a clean finish.
    @{ Kind = 'Script';     Name = 'the game was still alive at the end'; Script = {
        param($ctx)
        $l = ($ctx.MarksText -split "`n") | Where-Object { $_ -match '^EXIT\s+' } | Select-Object -First 1
        if (-not $l) { return @{ Pass = $false; Detail = 'no EXIT line in marks.txt' } }
        return @{ Pass = ($l -match 'harness-stop'); Detail = $l.Trim() }
      } }
    # The world's 25-slot physics-info budget, read off its own [T3-demote] census line.
    @{ Kind = 'LogValue';   Name = 'world physics-slot occupancy stays off the 25-slot ceiling'
       Pattern = '\[T3-demote\].* physSlots (?<n>\d+)'; Group = 'n'; Agg = 'max'; Max = 22 }
    # ANTI-VACUOUS: the run must actually have promoted a traffic car to a physics body. The
    # [T3-*] create/state rungs were deleted in the T5 cleanup; these three are what survives.
    @{ Kind = 'LogCount';   Name = 'traffic promotion happened (else the run proves nothing)'
       Pattern = '\[T4-hit\]|\[T5-arm\]|\[T3-demote\]'
       Min = 1 }
  )
}
