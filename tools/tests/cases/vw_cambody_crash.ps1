# vw_cambody_crash -- a real wall crash does NOT build a BehaviourAftertouchCam (lane CAMBODY).
#
# The hard-stop crash moment hands the crash shot selector's output to the shot factory
# BehaviourManager::NewBehaviour, which has an aftertouchcam arm -- but ShotSelector::GetCrashShot
# skips every shot that is not iceanim or proceduralshot, so on the console no crash reaches it
# (the testbed is the only live path: vw_cambody_testbed). This is upstream's proven real wall
# stimulus (PlaytestCrashGyroClockLive) with the CAMBODY witness on; it pins that the crash ran
# its hard-stop camera and built no aftertouch camera.
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case vw_cambody_crash
@{
  Name           = 'vw_cambody_crash'
  Area           = 'director'
  Bug            = 'BehaviourAftertouchCam reachability: crash shots never allocate it (issue #34 leftover)'
  Frames         = $true
  ProfileFixture = 'rival_hunt_profile.sav'
  Run = @{
    SkipIntro = $true; AcceptGap = 1.0; MaxSeconds = 75
    Drive = $true; MotionProbe = $true
    CrashSweep = '3249.796,-3.7,-1925.404'
    CrashSweepShots = '225:70'; CrashSweepArm = 4
    FrameEvery = 3; MaxLogMB = 64
  }
  DiagEnv = 'BRN_CAMBODY_DIAG=1,BRN_CRASHCAM_DIAG=1,BRN_FRAME_DUMP_ARM=slomo,BRN_FRAME_DUMP_MAX=360'
  Checks = @(
    @{ Kind = 'Mark';     Name = 'reached driving'; Phase = 'DRIVING' }
    @{ Kind = 'LogMatch'; Name = 'real wall stimulus fired'; Pattern = '\[sweep\] shot 0/' }
    @{ Kind = 'LogMatch'; Name = 'real crash record opened'; Pattern = '\[crash-exit\] OPENED crash record' }
    @{ Kind = 'LogMatch'; Name = 'the hard-stop crash camera was allocated'; Pattern = '\[crashcam\] hardstop ALLOCATED' }
    @{ Kind = 'LogCount'; Name = 'no aftertouch camera from the crash shots'; Pattern = '\[cambody\] AftertouchCam'; Max = 0 }
    @{ Kind = 'LogCount'; Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
  )
}
