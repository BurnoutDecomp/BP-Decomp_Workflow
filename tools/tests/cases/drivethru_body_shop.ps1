# drivethru_body_shop -- BurnoutDecomp/b5-decomp#6 "drive-trough: camera is completely broken,
# and the world rendering is corrupted after".
#
# THE SCENARIO. The player car is placed 26 m short of the BODY SHOP drive-thru bay in River City
# and told to hold the throttle. The bay is GenericRegion sub-type 2 at (917.02, 23.77, -1383.39),
# rotY = 0.0434 rad, box 10.0 x 6.0 x 12.39 -- read straight out of the SHIPPED TRIGGERS.DAT with
# scratch\bugtest\drivethru\dtscan.py (offline; no boot needed to find a bay). Its long axis is
# world Z, so the approach lane is +Z -> -Z; heading 180 deg faces -Z (the teleport's heading is
# degrees clockwise from +Z, at = (sin h, 0, cos h)). Same bay the 2026-09-03 AI soak drove into
# by accident (scratch\aiwave\run5\BrnGame.log:446817 "[drivethru] ENTER type=2 id=252645").
#
# WHAT IT MEASURES. Two independent claims, because the report makes two:
#   (a) the drive-thru CAMERA frames the car. The [dt-cam] witness in
#       BrnArbStateDriveThru::Update prints, per frame the state owns, the camera position, the
#       player car position, the camera's height ABOVE the car (dy) and its DISTANCE to the car.
#       A shop shot that frames a car sits above it and within a few metres; "goes to ground
#       level" is dy <= 0 and "no car in frame" is dist in the tens of metres.
#   (b) the world still renders after the hand-back. The frame checks below look at the LAST
#       dumped frame (several seconds after the state hands control back to the roaming camera).
#
#   plus: the chain actually ran at all (the manager's ENTER line and the director's action-97
#   line), no NEW assert family, no exception.
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case drivethru_body_shop -ExpectFail -Label pre-fix
@{
  Name    = 'drivethru_body_shop'
  Area    = 'director/camera'
  Bug     = 'BurnoutDecomp/b5-decomp#6 -- drive-thru: camera changes FOV repeatedly and drops to ground level; world geometry corrupted afterwards'
  Frames  = $true
  Run     = @{
    Drive          = $true
    MotionProbe    = $true
    MaxSeconds     = 120
    # 26 m up the approach lane on +Z, facing -Z into the bay.
    Teleport       = '917.0,23.9,-1357.0,180'
    ThrottleScript = '0:accel,4:none'      # roll in, then coast -- the shop stops the car itself
    FrameEvery     = 30
  }
  # BRN_DRIVETHRU_DIAG arms both the manager's region gazetteer + GATE/ENTER/POST rungs, the
  # director's action rung, BehaviourManager::NewBehaviour's shot rung, and the [dt-cam] witness.
  # BRN_ICE_TRACE arms KeyAnimController's own bursty (4-in-300-calls) `[ice]` sampler, which
  # prints the take's eyeSpace/lookSpace and the raw -> world projection of both points. That is
  # the measurement that separates "the shot never ran" from "the space it is authored against
  # projects to nothing"; it is what says WHICH of the two the drive-thru camera is.
  DiagEnv = 'BRN_DRIVETHRU_DIAG=1,BRN_ICE_TRACE=1'
  Checks  = @(
    @{ Kind='Mark';     Name='reached DRIVING'; Phase='DRIVING' }

    # ---- the chain ran (if these fail the rest says nothing about the bug) -----------------
    @{ Kind='LogMatch'; Name='the body shop drive-thru triggered'; Pattern='\[drivethru\] ENTER type=2' }
    @{ Kind='LogMatch'; Name='the director raised the drive-thru camera gate'; Pattern='\[drivethru\] DIRECTOR action=97 -> active=1' }
    @{ Kind='LogMatch'; Name='a shop-shot behaviour was allocated'; Pattern='\[drivethru\] NewBehaviour shot .* behaviour=1' }

    # ---- (a) the camera ---------------------------------------------------------------------
    # dy: the camera's height RELATIVE TO THE CAR. A shot that frames a car sits within a few
    # metres of it vertically -- above it for a look-down, level with it for a low hero shot.
    # "The camera goes to ground level" is the camera sitting tens of metres below the car,
    # because it is not anchored to the car at all.
    #
    # ⚠️ THIS BOUND WAS CORRECTED, and the correction is worth reading. It was first written as
    # `dy >= 0.5` ("a shop shot looks DOWN on the bay"), which was MY ASSUMPTION, not the
    # console's. The take actually authors its eye at (-2.548, 0.079, -2.942) in eICE_HEADING_SPACE
    # -- 0.08 m above the car's own transform origin and 3.7 m from it, i.e. a LOW hero shot of the
    # car in the bay. `dy >= 0.5` therefore failed on a CORRECT camera (post-fix run 20260906_104924
    # measured -0.319..+0.079), which is a check measuring the wrong thing. The band below is the
    # physical statement instead -- a camera filming a car is within a few metres of it vertically
    # -- and it still separates the two builds by two orders of magnitude:
    #     pre-fix  20260906_100326: 203/203 OUTSIDE, min -23.978 max -22.426
    #     post-fix 20260906_104924: 0/203 outside,  min  -0.319 max   0.079
    @{ Kind='LogValue'; Name='camera stays vertically within a few metres of the car, every drive-thru frame';
       Pattern='\[dt-cam\].* dy=(?<v>-?[\d.]+(?:[eE][-+]?\d+)?) '; Group='v'; Agg='all'; Min=-3.0; Max=8.0 }
    # dist: a shot that frames the car is metres from it. 25 m is generous (the bay box itself is
    # 12.4 m long), and the earlier wave measured this shot showing an overpass with no car at all.
    @{ Kind='LogValue'; Name='camera stays within 25 m of the car for every drive-thru frame';
       Pattern='\[dt-cam\].* dist=(?<v>[\d.]+(?:[eE][-+]?\d+)?) '; Group='v'; Agg='all'; Max=25.0 }
    # FOV: a real shot's FOV is a sane camera FOV. Anything outside 5..120 degrees is not a shot,
    # it is an unresolved take. (The report: "it changes the FOV multiple times".)
    @{ Kind='LogValue'; Name='camera FOV stays in a sane range for every drive-thru frame';
       Pattern='\[dt-cam\].* fov=(?<v>-?[\d.]+(?:[eE][-+]?\d+)?)'; Group='v'; Agg='all'; Min=5.0; Max=120.0 }

    # ---- (b) the world after the hand-back --------------------------------------------------
    # The last dumped frame is ~85 s after the drive-thru ends. Sky band: the top strip of the
    # street scene is sky/building, never a fan of blown-out shards -- the issue's third
    # screenshot shows exactly that, huge near-white translucent spikes filling the upper middle
    # of the screen. bright_frac there is the cheapest number that moves with it.
    #
    # ⚠️ READ THIS BEFORE TRUSTING THIS CHECK'S PASS. It passed on the PRE-FIX build too
    # (run 20260906_100326): the world-corruption half of issue #6 did NOT reproduce in this
    # scenario, so this check is a floor, not a witness -- it says "the post-exit frame is not
    # obviously blown out", not "the corruption is gone". The frames either side of the drive-thru
    # (bb_002100..bb_003000 of that run) were inspected by eye and are clean. The corruption still
    # has no test. The lead: the world dispatch camera IS the director camera
    # (BrnGameModule.cpp:2654 -> WorldModule::SetBringUpCameraOverride), so while the drive-thru
    # shot sat at the world origin the world's visibility/streaming centre sat there too --
    # 1654 m from the car, for 203 frames. That is a streamer-eviction mechanism for "the world is
    # corrupted after", and the camera fix removes its cause; a denser district (the reporter's
    # shots are Downtown / River City) is the scenario most likely to show it.
    @{ Kind='Frame';    Name='post-exit: upper-middle screen is not filled with blown-out shards';
       At='last'; Region='0.35,0.05,0.75,0.45'; Stat='bright_frac'; Max=0.35 }

    # ---- the usual floor --------------------------------------------------------------------
    @{ Kind='NewAsserts'; Name='no NEW assert families' }
    @{ Kind='LogCount';   Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }
  )
}
