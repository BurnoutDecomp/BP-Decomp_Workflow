# traffic_soak_lane -- lane traffic_assert. "traffic cars crashing the game with asserts, sometimes".
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
# SCENARIO 2 -- THE LANE SOAK. Start on the live traffic lane, hold the throttle and weave, so the
# player clips whatever traffic the generator happens to put there over 200 s. This is the
# INTERMITTENT half of the report: it promotes by overlap, not by a scripted hit.
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
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case traffic_soak_lane -ExpectFail -Label pre-fix
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
#   ⚠ 60 -> 145, ON THE EVIDENCE OF ITS SIBLING. At MaxSeconds 60 this case PASSED -- with
#   exactly THREE `[T3-demote] ... physSlots` samples, i.e. one unlucky run away from the vacuous-
#   witness failure traffic_soak_ram actually hit at the same budget (run 20260906_140916). The
#   demote witness fires about once per 40 s of world time, so a 60 s budget makes this check a
#   coin toss rather than a measurement. 145 keeps the banked run's world time and still takes the
#   whole 6.8 s boot saving off the front.
#
@{
  Name    = 'traffic_soak_lane'
  Area    = 'traffic'
  Bug     = 'field report -- "traffic cars crashing the games with asserts sometimes"'
  Frames  = $false
  Run     = @{
    Drive          = $true
    MotionProbe    = $true
    MaxSeconds     = 145
    SkipIntro     = $true      # the console -skipvideos latch (see the banner)
    AcceptGap     = 1.0        # harness pump latency, not a game gate
    Teleport       = '3323.9,-2.4,-1793.2,0'
    ThrottleScript = '0:accel'
    SteerScript    = '0:none,6:left,7:none,14:right,15:none'
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
