@{
  Name = 'current_dev_playability_periodic_20261025'
  Area = 'debug-menu'
  Bug = 'Check current-dev startup, junkyard exit, player input and actual rendered driving before normal installation.'
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
    ThrottleScript = '0:accel,10:none'
    MotionProbe = $true
    FrameEvery = 1000
  }
  DiagEnv = 'BRN_HUD_VIS=1,BRN_FRAME_DUMP_MAX=6'
  Checks = @(
    @{ Kind = 'LogCount'; Name = 'no assertion'; Pattern = '\[ASSERT(?:\s+\d+)?\]'; Max = 0 }
    @{ Kind = 'LogCount'; Name = 'no exception'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark'; Name = 'reached driving'; Phase = 'DRIVING' }
    @{ Kind = 'LogMatch'; Name = 'player engine runs under ordinary accelerator input'; Pattern = '^\[ignition\] tick state=2\b[^\r\n]*\binCarSelect=0\b[^\r\n]*\baccel=1\.0+\b' }
    @{ Kind = 'LogMatch'; Name = 'player accelerator witnessed'; Pattern = '^\[motion\][^\r\n]*\bgas 1(?:\.0+)?\b' }
    @{ Kind = 'Script'; Name = 'player actually moved over20m'; Script = {
        param($ctx)
        $s = Get-DriveSegment $ctx.LogLines
        if (-not $s.Known) { return @{ Pass = $false; Detail = 'No player motion samples.' } }
        return @{ Pass = ($s.Path -gt 20.0); Detail = ('path={0:f1}m samples={1} respawns={2}' -f $s.Path,$s.Samples,$s.Respawns) }
    } }
    @{ Kind = 'Script'; Name = 'bounded supported periodic capture'; Script = { param($ctx) $f = @(Get-FrameFiles $ctx.FrameDir); return @{ Pass = ($f.Count -ge 2 -and $f.Count -le 6); Detail = ('{0} BMP files, cap6' -f $f.Count) } } }
    @{ Kind = 'Frame'; Name = 'last image is not a black world'; At = 'last'; Region = '0.1,0.1,0.9,0.8'; Stat = 'dark_frac'; Max = 0.85 }
  )
}
