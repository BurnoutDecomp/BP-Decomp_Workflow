# traffic_swept_wall -- a fast physical traffic car stays on the console's world-contact arm.
#
# THE ARMS: VehicleManager::DoTrafficCarWorldContactGeneration picks, per physical FULL traffic car,
# between in-place deformation spheres and SWEPT spheres (DeformationManager::IsUsingSweptSpheres:
# the model's mbDoSweptSphereTests AND forward speed above 6 m/s AND not crashing). The swept arm
# posts a synchronous batch through BaseCollisionGenerator::CollideSweptSphereListWithTriangleList.
#
# WHY THE SWEPT ARM IS NEVER TAKEN FOR TRAFFIC (read off the console image, 2026-09-28):
#   * DeformableObject::mbDoSweptSphereTests has exactly ONE store in the image, in
#     DeformableObject::Prepare, copied from AddDeformationModelEvent::mbDoSweptSphereTests.
#   * AddDeformationModelEvent has two producers: DeformationInputInterface::AddDeformationModel
#     (only caller VehicleManager::AddRaceCarDeformationModel, which passes true) and
#     PhysicalTrafficManager::SendCreateRemoveTrafficEvents, which builds the event inline and
#     stores a literal 0 into that byte before AddEvent.
#   So every traffic deformation model has swept tests OFF, IsUsingSweptSpheres is false for every
#   traffic car at any speed, and a fast traffic car takes the IN-PLACE sphere arm (or the deformed
#   box once the frame's 21-test budget is spent). The PC tree does the same
#   (BrnPhysicalTrafficManager_Remove.cpp passes false). The swept traffic arm is dead code in
#   the retail build: no scenario can reach it, and its body stays link-proven only.
#
# WHAT THIS CASE PROVES instead: the swept arm's SPEED condition is met by a FULL, non-crashing,
# modelled physical traffic car, and the arm is still not taken (console parity). If someone ever
# turns swept tests on for traffic, the last check goes red.
#
# SCENARIO: the deterministic ram of traffic_soak_ram -- 43 m up-road of parked car 553, on that
# car's own heading, throttle pinned. The hit promotes 553 to a FULL physics body and shoves it
# down the road at 10+ m/s (`[T5-ram] ... ptype=0 ... |tv|=` BRN_TRAFFIC_DIAG).
#
# WITNESS: BRN_SWEPT_DIAG prints `[swept] traffic=<i> batches=<n> ...` from inside the swept arm
# only; the host guard `no deformation model for physical traffic car` (unconditional, once)
# returns before either arm.
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case traffic_swept_wall
#
@{
  Name    = 'traffic_swept_wall'
  Area    = 'traffic'
  Bug     = 'fast physical traffic world contacts: the swept arm is console-dead for traffic; the in-place arm must stay the one taken'
  Frames  = $false
  Run     = @{
    Drive          = $true
    MotionProbe    = $true
    MaxSeconds     = 90
    SkipIntro      = $true      # the console -skipvideos latch
    AcceptGap      = 1.0        # harness pump latency, not a game gate
    Teleport       = '3390.2,0.2,-1620.0,182'
    ThrottleScript = '0:accel'
  }
  DiagEnv = 'BRN_SWEPT_DIAG=1,BRN_TRAFFIC_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }
    # ANTI-VACUOUS: a traffic car must have been promoted, or nothing below means anything.
    @{ Kind = 'LogCount';   Name = 'traffic promotion happened (else the run proves nothing)'
       Pattern = '\[T4-hit\]|\[T5-arm\]|\[T3-demote\]'
       Min = 1 }
    # The swept arm's speed condition was met by a FULL (ptype=0), non-crashing traffic car.
    @{ Kind = 'LogValue';   Name = 'a FULL non-crashing physical traffic car moved above 6 m/s'
       Pattern = '\[T5-ram\] post .* ptype=0 .*\|tv\|=(?<v>[\d.]+) crashing=0'; Group = 'v'; Agg = 'max'; Min = 6.0 }
    # ...and it had a deformation model, so the world pass reached the FULL arms.
    @{ Kind = 'LogCount';   Name = 'no promoted traffic car lacked a deformation model'
       Pattern = 'no deformation model for physical traffic car'; Max = 0 }
    # CONSOLE PARITY: traffic deformation models carry swept tests OFF, so the swept arm never runs.
    @{ Kind = 'LogCount';   Name = 'the traffic swept arm was not taken (swept tests are off for traffic)'
       Pattern = '\[swept\] traffic=\d+ batches=\d+'
       Max = 0 }
  )
}
