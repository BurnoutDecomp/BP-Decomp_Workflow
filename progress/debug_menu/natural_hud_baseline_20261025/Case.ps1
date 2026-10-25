@{
  Name = 'root_boostbar_brake_capture_20261025'
  Area = 'debug-menu'
  Bug = 'Observe the natural HUD while ordinary brake input holds the player engine running.'
  ProfileFixture = 'DISCO_collect_base.sav'
  Frames = $true
  Run = @{
    MaxSeconds = 60
    LogWaitSeconds = 40
    StrictGameOwnership = $true
    BelowNormal = $true
    NoAssertRelease = $true
    SkipIntro = $true
    TitleStart = $true
    AcceptGap = 1.0
    Drive = $true
    DriveDelay = 2
    ThrottleScript = '0:brake'
    FrameEvery = 1000000
  }
  DiagEnv = 'BRN_HUD_VIS=1,BRN_FRAME_DUMP_REQUEST=1,BRN_FRAME_DUMP_MAX=2'
  Checks = @(
    @{ Kind = 'LogCount'; Name = 'no assertion'; Pattern = '\[ASSERT(?:\s+\d+)?\]'; Max = 0 }
    @{ Kind = 'LogCount'; Name = 'no exception'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark'; Name = 'reached driving'; Phase = 'DRIVING' }
    @{ Kind = 'LogMatch'; Name = 'player engine runs under ordinary brake input'; Pattern = '^\[ignition\] tick state=2\b[^\r\n]*\binCarSelect=0\b[^\r\n]*\bbrake=1\.0+\b' }
    @{ Kind = 'LogCount'; Name = 'one PID and slot scoped capture'; Pattern = '^\[frame-request\] pid=\d+ slot=62076 seq=1 present=\d+ file=bb_\d{6}\.bmp$'; Min = 1; Max = 1 }
  )
}
