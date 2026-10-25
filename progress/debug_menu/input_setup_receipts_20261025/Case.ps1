@{
  Name = 'root_setup_receipts_20261025'
  Area = 'debug-menu'
  Bug = 'Require the game to acknowledge the full short setup command and Enter before testing controls.'
  ProfileFixture = 'DISCO_collect_base.sav'
  Frames = $false
  Run = @{
    MaxSeconds = 90
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
  }
  DiagEnv = 'BRN_HUD_VIS=1,BRN_DEBUG_UI_TRACE=1'
  Checks = @(
    @{ Kind = 'LogCount'; Name = 'no assertion'; Pattern = '\[ASSERT(?:\s+\d+)?\]'; Max = 0 }
    @{ Kind = 'LogCount'; Name = 'no exception'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark'; Name = 'reached driving'; Phase = 'DRIVING' }
    @{ Kind = 'LogMatch'; Name = 'custom renderer component activated'; Pattern = '^\[debug-component\] path="Gui/Gui Custom Renderer" request=menu controls=1$' }
    @{ Kind = 'LogMatch'; Name = 'read only alias query completed'; Pattern = '^BOutR: /Gui/Gui Custom Renderer/Outer boost Red$' }
    @{ Kind = 'LogCount'; Name = 'one game observed Enter'; Pattern = '^\[debug-ui\] event=0 visible=1 .* key=10$'; Min = 1; Max = 1 }
  )
}
