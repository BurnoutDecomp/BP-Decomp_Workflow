# onact_debug_page -- the director's "Camera" debug page opens on a live drive (stub-retirement lane
# ONACT). baseline_boot_drive's scenario, plus a concurrent stimulus (Setup) that, once the car has
# been driving, types COMPONENT "Camera" into the debug console -- the DebugManager activation that
# runs BrnDirector::DebugComponent::OnActivate -- and SAVEs the UI state. The checks read that state:
# the page's writable tweakables are registered under /Camera with their shipped defaults, the four
# "Current Camera" readouts are read-only (SAVE skips them), and the activation raised no assert.
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case onact_debug_page
@{
  Name    = 'onact_debug_page'
  Area    = 'director'
  Bug     = 'BrnDirector::DebugComponent::OnActivate (issue #34 stub retirement)'
  Frames  = $false
  Run     = @{
    Drive       = $true
    MotionProbe = $true
    MaxSeconds  = 70
    SkipIntro   = $true
    AcceptGap   = 1.0
    Teleport    = '3040.7,-5.8,-1937.9,180'
  }
  DiagEnv = ''
  Setup   = {
    param($ctx)
    $lsHelper = Join-Path $ctx.Root 'tools\tests\tools\STUBS_ONACT_debugpage.ps1'
    $lsArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$lsHelper`"",
                '-GameLog', "`"$($ctx.GameLog)`"", '-OutDir', "`"$($ctx.RunDir)`"", '-Slot', "$($ctx.Slot)")
    return Start-Process powershell -ArgumentList $lsArgs -PassThru -WindowStyle Hidden
  }
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'LogCount';   Name = 'no IsAllocated() assert (the shared gameplay-external camera was live)'; Pattern = '\[ASSERT \d+\] IsAllocated\(\)'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'Script';     Name = 'the stimulus opened the page and saved the state'; Script = {
        param($ctx)
        $lsLog = Join-Path $ctx.RunDir 'onact_helper.log'
        if (-not (Test-Path $lsLog)) { return @{ Pass = $false; Detail = 'no onact_helper.log' } }
        $lsText = Get-Content $lsLog -Raw
        $lbDone = $lsText -match 'RESULT DONE'
        return @{ Pass = $lbDone; Detail = (($lsText -split "`r?`n" | Where-Object { $_ -match 'RESULT|typed' }) -join ' ; ') }
      } }
    @{ Kind = 'Script';     Name = 'no assert while the page registered'; Script = {
        param($ctx)
        $lsLog = Join-Path $ctx.RunDir 'onact_helper.log'
        if (-not (Test-Path $lsLog)) { return @{ Pass = $false; Detail = 'no onact_helper.log' } }
        if ((Get-Content $lsLog -Raw) -notmatch 'assert lines in the game log: (\d+) before the page opened, (\d+) after') { return @{ Pass = $false; Detail = 'no assert count' } }
        return @{ Pass = ([int]$Matches[1] -eq [int]$Matches[2]); Detail = "before=$($Matches[1]) after=$($Matches[2])" }
      } }
    @{ Kind = 'Script';     Name = 'the Camera page tweakables are registered with their defaults'; Script = {
        param($ctx)
        $lsState = Join-Path $ctx.RunDir 'onact_state.txt'
        if (-not (Test-Path $lsState)) { return @{ Pass = $false; Detail = 'no onact_state.txt' } }
        $lsText = Get-Content $lsState -Raw
        $laSet = @([regex]::Matches($lsText, '(?m)^SET "/Camera/[^\r\n]*') | ForEach-Object { $_.Value })
        $laNeed = @(
          'Testbed/Loop ICE testbed movies', 'Draw follow-cam pivot', 'Current Camera/Override Player',
          'Moment Options/Allow Jump Moment', 'Debug Ouput/Enable Default Debug Output', 'Debug Ouput/Show Crash Info',
          'Debug Ouput/Debug Display All Camera Transforms', 'Crash Thresholds/Min Speed below Max MPH for Normal Crashes',
          'Misc Flags/Do attract mode', 'Misc flags/Allow Showtime closeups', 'Clipping/Default Far Clip',
          'Zero Timestep', 'Single Non-Zero Timestep', 'Pic Paradise Delay Secs', 'RenderMetricsMode', 'Enable Boost Effects')
        $laMissing = @($laNeed | Where-Object { $n = $_; -not ($laSet | Where-Object { $_ -like ('*/' + $n + '" *') }) })
        $laReadOnly = @($laSet | Where-Object { $_ -match '/Current Camera/(FOV|X|Y|Z)"' })
        $lbComponent = $lsText -match '(?m)^COMPONENT "/?Camera"'
        $lbOk = $lbComponent -and $laSet.Count -ge 43 -and $laMissing.Count -eq 0 -and $laReadOnly.Count -eq 0
        $lsSample = ($laSet | Where-Object { $_ -match 'Override Player|Default Far Clip|Pic Paradise Delay|Normal Crashes|Allow Stunt|Show debug camera names' }) -join ' | '
        return @{ Pass = $lbOk; Detail = ("component={0} SET lines={1} missing=[{2}] read-only listed=[{3}] :: {4}" -f $lbComponent, $laSet.Count, ($laMissing -join ', '), ($laReadOnly -join ', '), $lsSample) }
      } }
  )
}
