# vw_deform_menu_max -- the maximum deformation preset reached through the REAL debug UI (lane DEFORM,
# visual wave VW). The returning-player car is seated at rest on the road and heading of the original
# maximum-deformation screenshot (At 0.092,-0.015,-0.996 near 3039.3,-3.8,-1995.3), then a concurrent
# stimulus types into the in-game debug console through the named-event key channels:
#     COMPONENT "Physics/Deformation"            -> DeformationDebugComponent::OnActivate (selects rig 0)
#     INCREMENT ".../Compress../Preset"  x2      -> OnCompressionPresetChange: Max drivetime, Max total
#     CALL ".../Reset selected rig"              -> ResetDeformationNextUpdate -> the post-scene sweep
# No harness shortcut (BRN_PLAYTEST_MAX_DEFORM_AT is not set). Frames are dumped across the whole
# sequence so the rest, maximum and reset poses can be compared at the same camera.
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case vw_deform_menu_max
@{
  Name    = 'vw_deform_menu_max'
  Area    = 'physics'
  Bug     = 'VW item 1: maximum deformation through the real debug menu looks unlike the original'
  Frames  = $true
  ProfileFixture = 'rival_hunt_profile.sav'
  Run     = @{
    SkipIntro        = $true
    AcceptGap        = 1.0
    Drive            = $true
    DriveDelay       = 4.0
    DriveSeconds     = 1.0
    CrashSweep       = '3039.3,-3.8,-1995.3'
    CrashSweepShots  = '174.723:0,174.723:0'
    CrashSweepArm    = 0.1
    CrashSweepSettle = 900
    CrashSweepMax    = 1200
    MaxSeconds       = 140
    FrameEvery       = 30
    MenuScript       = 'timeout:135;wait:\[sweep\] seat ok shot 1;hold:Brake:100;hold:HandBrake:100;sleep:2;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;sleep:40;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;hold:CameraLeft:0.3;sleep:0.6;sleep:30'
  }
  DiagEnv = 'BRN_SWEEP_WAIT_ROAMING=1,BRN_DEBUG_UI_TRACE=1,BRN_DEFORM_TRACE=1,BRN_FRAME_DUMP_START=1800,BRN_FRAME_DUMP_MAX=300'
  Setup   = {
    param($ctx)
    $lsHelper = Join-Path $ctx.Root 'tools\tests\tools\VW_DEFORM_debugkeys.ps1'
    $lsSteps = @(
      'wait:\[sweep\] seat ok shot 1', 'sleep:20', 'note:rest',
      'key:192', 'cmd:component "Physics/Deformation"', 'key:192', 'sleep:3', 'note:activated',
      'key:192', 'cmd:increment "Physics/Deformation/Compress../Preset"', 'key:192', 'sleep:3', 'note:maxdrivetime',
      'key:192', 'cmd:increment "Physics/Deformation/Compress../Preset"', 'key:192', 'sleep:24', 'note:maxtotal',
      'key:192', 'cmd:call "Physics/Deformation/Reset selected rig"', 'key:192', 'sleep:8', 'note:reset'
    )
    $lsStepsFile = Join-Path $ctx.RunDir 'vw_deform_steps.txt'
    Set-Content -LiteralPath $lsStepsFile -Value $lsSteps -Encoding ascii
    $lsArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$lsHelper`"",
                '-GameLog', "`"$($ctx.GameLog)`"", '-OutDir', "`"$($ctx.RunDir)`"", '-Slot', "$($ctx.Slot)",
                '-StepsFile', "`"$lsStepsFile`"")
    return Start-Process powershell -ArgumentList $lsArgs -PassThru -WindowStyle Hidden
  }
  Checks  = @(
    @{ Kind = 'Mark';     Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'LogCount'; Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'LogCount'; Name = 'no asserts'; Pattern = '\[ASSERT(?:\s|\])'; Max = 0 }
    @{ Kind = 'Script';   Name = 'the debug-console sequence ran to the end'; Script = {
        param($ctx)
        $lsLog = Join-Path $ctx.RunDir 'vw_deform_keys.log'
        if (-not (Test-Path $lsLog)) { return @{ Pass = $false; Detail = 'no vw_deform_keys.log' } }
        $lsText = Get-Content $lsLog -Raw
        return @{ Pass = ($lsText -match 'RESULT DONE'); Detail = (($lsText -split "`r?`n" | Where-Object { $_ -match 'note:|RESULT' }) -join ' ; ') }
      } }
    @{ Kind = 'Script';   Name = 'menu presets reach the player skin rows and the reset clears them'; Script = {
        param($ctx)
        # Window the player's [deform-trace] skin-row sums by the game-log line each menu step ran at
        # (the helper records it), then compare: rest ~0, Max drivetime partial, Max total full, reset ~0.
        $lsLog = Join-Path $ctx.RunDir 'vw_deform_keys.log'
        if (-not (Test-Path $lsLog)) { return @{ Pass = $false; Detail = 'no vw_deform_keys.log' } }
        $laStep = @{}
        foreach ($lsLine in (Get-Content $lsLog)) {
          if ($lsLine -match 'step \d+ note:(?<n>\w+) \(log line (?<l>\d+)\)') { $laStep[$Matches.n] = [int]$Matches.l }
        }
        foreach ($lsNeed in @('rest', 'activated', 'maxdrivetime', 'maxtotal', 'reset')) {
          if (-not $laStep.ContainsKey($lsNeed)) { return @{ Pass = $false; Detail = "helper never reached $lsNeed" } }
        }
        $laSum = @()
        for ($i = 0; $i -lt $ctx.LogLines.Count; ++$i) {
          if ($ctx.LogLines[$i] -match '^\[deform-trace\] .* player 1 .* sumVerlet (?<s>[\d.eE+-]+) nnzVerlet (?<n>\d+)') {
            $laSum += ,@(($i + 1), [double]::Parse($Matches.s, [cultureinfo]::InvariantCulture), [int]$Matches.n)
          }
        }
        function Last-Before([int]$liLine) { $lr = $null; foreach ($e in $laSum) { if ($e[0] -le $liLine) { $lr = $e } }; return $lr }
        $lRest  = Last-Before $laStep['rest']
        $lDrive = Last-Before $laStep['maxdrivetime']
        $lTotal = Last-Before $laStep['maxtotal']
        $lReset = Last-Before $laStep['reset']
        if (-not ($lRest -and $lDrive -and $lTotal -and $lReset)) { return @{ Pass = $false; Detail = "missing [deform-trace] samples ($($laSum.Count))" } }
        $lbOk = ($lRest[1] -lt 0.05) -and ($lDrive[1] -gt 5.0) -and ($lTotal[1] -gt ($lDrive[1] + 20.0)) -and ($lTotal[2] -eq 128) -and ($lReset[1] -lt 0.01)
        return @{ Pass = $lbOk; Detail = ("sumVerlet rest={0:g4} maxDrivetime={1:g4} maxTotal={2:g4} (rows {3}) afterReset={4:g4}" -f $lRest[1], $lDrive[1], $lTotal[1], $lTotal[2], $lReset[1]) }
      } }
  )
}
