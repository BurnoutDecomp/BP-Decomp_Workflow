@{
  Name = 'title_start_drive_probe_20261025'
  Area = 'harness'
  Bug = 'A batch without title Start reached driving with player gas and engine both zero.'
  ProfileFixture = 'DISCO_collect_base.sav'
  Frames = $false
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
    DriveSeconds = 10
    MotionProbe = $true
  }
  DiagEnv = 'BRN_HUD_VIS=1'
  Checks = @(
    @{ Kind = 'LogCount'; Name = 'no assertion'; Pattern = '\[ASSERT(?:\s+\d+)?\]'; Max = 0 }
    @{ Kind = 'LogCount'; Name = 'no exception'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark'; Name = 'reached driving'; Phase = 'DRIVING' }
    @{ Kind = 'LogMatch'; Name = 'player throttle reaches a running engine'; Pattern = '^\[motion\][^\r\n]*\bgas 1\.0+\b[^\r\n]*\bengine 2\b' }
    @{ Kind = 'Script'; Name = 'player moves more than 10 metres'; Script = {
      param($ctx)
      $segment = Get-DriveSegment $ctx.LogLines
      return @{ Pass = ($segment.Known -and $segment.Net -gt 10.0); Detail = ('net={0}m path={1}m samples={2}..{3}' -f $segment.Net,$segment.Path,$segment.FromSample,$segment.ToSample) }
    } }
  )
}
