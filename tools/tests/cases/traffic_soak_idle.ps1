# traffic_soak_idle -- lane traffic_assert. THE PROVEN CRASH RECIPE.
#
# Mined offline out of every BrnGame.log under scratch\ (585 logs). ONE run in the whole set
# ends the way the field report describes -- asserts, then the game dies:
#   scratch\x360_road_shaders\run_after\BrnGame.log:25777 (2026-08-30, 272.9 s in)
#     [ASSERT 1] liPartsIndex >= 0   BrnTrafficEntityModule_wT3_01.cpp:436
#     [ASSERT 2] Index:              BrnTrafficEntityModule_wT3_01.cpp:438  (CgsBitArray.h:222)
#     [EXCEPTION] EXCEPTION_ACCESS_VIOLATION (0xC0000005) ... rdi=00000000FFFFFFFF
#   callstack: TrafficEntityModule::RecordTrafficVehicleIsPhysical <- HandleExternalResponses
#              <- PostPhysicsUpdate <- WorldModule::Update
# and marks.txt records EXIT self code=-1073741819 (0xC0000005): the process died, it was not
# stopped by the harness. That is the bug: the WORLD-side 25-slot maTrafficPhysicsInfoListBits
# budget runs out, GetFirstClearBit() returns -1, the console's own two asserts fire, and the
# SetBit(-1) that follows them (an assert is not a guard) faults.
#
# THE RECIPE IS THAT RUN'S, VERBATIM, and it is not the ram or the weave: teleport into the
# stunt junction, accelerate for 8 s, then LET GO and sit in traffic for four minutes. Promotion
# is driven by traffic hitting a nearly stationary player, so the slot budget is what the run
# actually measures. Long by necessity -- the earlier crash needed 272 s.
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
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case traffic_soak_idle -ExpectFail -Label pre-fix
@{
  Name    = 'traffic_soak_idle'
  Area    = 'traffic'
  Bug     = 'field report -- "traffic cars crashing the games with asserts sometimes"'
  Frames  = $false
  Run     = @{
    Drive          = $true
    MotionProbe    = $true
    MaxSeconds     = 275
    Teleport       = '2641.5,1.3,-1723.8,169'
    ThrottleScript = '0:accel,8:none'
  }
  DiagEnv = 'BRN_TRAFFIC_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    # THE CRASH ITSELF. The 2026-08-30 run died here.
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }
    # THE SIGNATURE: the world-side physics-slot budget ran dry.
    @{ Kind = 'LogCount';   Name = 'world traffic physics-slot budget not exhausted'
       Pattern = '\[ASSERT \d+\] (liPartsIndex >= 0|Index: )'
       Max = 0 }
    # ...and every other assert raised out of a traffic lifecycle file, physics or world side.
    @{ Kind = 'LogCount';   Name = 'no assert from any traffic file'
       Pattern = '\[ASSERT \d+\].*(BrnPhysicalTrafficManager|BrnTrafficEntityModule|BrnTrafficVehicle|BrnTrafficPhysics|PhysicalTrafficVehicle)'
       Max = 0 }
    # THE PROCESS SURVIVED: marks.txt says how the run ended. 'EXIT self code=...' means the game
    # died on its own; only 'harness-stop' is a clean finish.
    @{ Kind = 'Script';     Name = 'the game was still alive at the end'; Script = {
        param($ctx)
        $l = ($ctx.MarksText -split "`n") | Where-Object { $_ -match '^EXIT\s+' } | Select-Object -First 1
        if (-not $l) { return @{ Pass = $false; Detail = 'no EXIT line in marks.txt' } }
        return @{ Pass = ($l -match 'harness-stop'); Detail = $l.Trim() }
      } }
    # THE BUDGET ITSELF, read off the world's own [T3-demote] census line (physSlots is the
    # occupancy AFTER the demote, so 24 means it was full at 25 when that car went). Fixed by
    # b5 7761247a; this check is what keeps it fixed.
    @{ Kind = 'LogValue';   Name = 'world physics-slot occupancy stays off the 25-slot ceiling'
       Pattern = '\[T3-demote\].* physSlots (?<n>\d+)'; Group = 'n'; Agg = 'max'; Max = 22 }
    # ANTI-VACUOUS: the run must actually have promoted traffic to physics bodies.
    @{ Kind = 'LogCount';   Name = 'traffic promotion happened (else the run proves nothing)'
       Pattern = '\[T4-hit\]|\[T5-arm\]|\[T3-demote\]'
       Min = 1 }
  )
}
