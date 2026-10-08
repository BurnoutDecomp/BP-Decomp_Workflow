# vw_cambody_testbed -- BehaviourFailsafe and BehaviourAftertouchCam run live (lane CAMBODY).
#
# On the console both behaviours are allocated by exactly one live path: the director debug page's
# Testbed rows (ArbStateTestbed::GenericActivateCam arms the state, ArbStateTestbed::Update
# allocates NewBehaviour<BehaviourFailsafe> / NewBehaviour<BehaviourAftertouchCam>, adopts the
# bank's "Failsafe" / "Aftertouch" block and, for the aftertouch camera, the resource manager's
# aftertouchcam shot). The crash shot selector only ever hands out iceanim / proceduralshot shots,
# so no crash reaches an aftertouch camera.
#
# The scenario: baseline drive; once the car is moving a concurrent stimulus types into the debug
# console (the named-event key channels, VW_DEFORM_debugkeys.ps1's step runner):
#     COMPONENT "Camera"                   -> DebugComponent::OnActivate (registers the Testbed rows)
#     CALL "Camera/Testbed/Failsafe"       -> the failsafe camera for ~10 s
#     CALL "Camera/Testbed/Aftertouch"     -> the aftertouch camera for ~10 s (the testbed releases
#                                             the failsafe one first)
#     CALL "Camera/Testbed/Deactivate"     -> released
# BRN_CAMBODY_DIAG prints one [cambody] line per Construct / Prepare and the first Update frames.
# The checks want all three slots witnessed for both behaviours, finite published poses that stay
# with the car, and no new assert family.
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case vw_cambody_testbed
@{
  Name    = 'vw_cambody_testbed'
  Area    = 'director'
  Bug     = 'BehaviourFailsafe / BehaviourAftertouchCam Construct/Prepare/Update (issue #34 leftover)'
  Frames  = $true
  Run     = @{
    Drive       = $true
    MotionProbe = $true
    MaxSeconds  = 95
    SkipIntro   = $true
    AcceptGap   = 1.0
    Teleport    = '3040.7,-5.8,-1937.9,180'
    FrameEvery  = 30
  }
  DiagEnv = 'BRN_CAMBODY_DIAG=1,BRN_DEBUG_UI_TRACE=1'
  Setup   = {
    param($ctx)
    $lsHelper = Join-Path $ctx.Root 'tools\tests\tools\VW_DEFORM_debugkeys.ps1'
    $lsSteps = @(
      'wait:CarSelectManager: Exit state is finished', 'sleep:12', 'note:driving',
      'key:192', 'cmd:component "Camera"', 'key:192', 'sleep:2', 'note:activated',
      'key:192', 'cmd:call "Camera/Testbed/Failsafe"', 'key:192', 'sleep:10', 'note:failsafe',
      'key:192', 'cmd:call "Camera/Testbed/Aftertouch"', 'key:192', 'sleep:10', 'note:aftertouch',
      'key:192', 'cmd:call "Camera/Testbed/Deactivate"', 'key:192', 'sleep:3', 'note:deactivated'
    )
    $lsStepsFile = Join-Path $ctx.RunDir 'vw_cambody_steps.txt'
    Set-Content -LiteralPath $lsStepsFile -Value $lsSteps -Encoding ascii
    $lsArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$lsHelper`"",
                '-GameLog', "`"$($ctx.GameLog)`"", '-OutDir', "`"$($ctx.RunDir)`"", '-Slot', "$($ctx.Slot)",
                '-StepsFile', "`"$lsStepsFile`"")
    return Start-Process powershell -ArgumentList $lsArgs -PassThru -WindowStyle Hidden
  }
  Checks  = @(
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Script';     Name = 'the debug-console sequence ran to the end'; Script = {
        param($ctx)
        $lsLog = Join-Path $ctx.RunDir 'vw_deform_keys.log'
        if (-not (Test-Path $lsLog)) { return @{ Pass = $false; Detail = 'no vw_deform_keys.log' } }
        $lsText = Get-Content $lsLog -Raw
        return @{ Pass = ($lsText -match 'RESULT DONE'); Detail = (($lsText -split "`r?`n" | Where-Object { $_ -match 'note:|RESULT' }) -join ' ; ') }
      } }
    @{ Kind = 'LogMatch'; Name = 'failsafe Construct ran';       Pattern = '\[cambody\] Failsafe Construct' }
    @{ Kind = 'LogMatch'; Name = 'failsafe Prepare bound a take'; Pattern = '\[cambody\] Failsafe Prepare take "[^"]+"' }
    @{ Kind = 'LogMatch'; Name = 'failsafe Update ran';          Pattern = '\[cambody\] Failsafe Update frame' }
    @{ Kind = 'LogMatch'; Name = 'aftertouch Construct ran';     Pattern = '\[cambody\] AftertouchCam Construct' }
    @{ Kind = 'LogMatch'; Name = 'aftertouch Prepare ran';       Pattern = '\[cambody\] AftertouchCam Prepare' }
    @{ Kind = 'LogMatch'; Name = 'aftertouch Update ran';        Pattern = '\[cambody\] AftertouchCam Update frame' }
    @{ Kind = 'Script';   Name = 'both cameras publish finite poses that stay with the car'; Script = {
        param($ctx)
        $inv = [cultureinfo]::InvariantCulture
        $lsNum = '(-?[0-9.eE+-]+|nan|inf|-inf|-?nan\S*|-?inf\S*)'
        $laOut = @()
        $lbOk = $true
        foreach ($lsWho in @('Failsafe', 'AftertouchCam')) {
          $liRows = 0; $liBad = 0; $lfMax = 0.0; $lfMin = 1.0e9; $lsFov = ''
          foreach ($lsLine in $ctx.LogLines) {
            if ($lsLine -notmatch ('^\[cambody\] ' + $lsWho + ' Update frame \d+ .*?car (?<cx>\S+) (?<cy>\S+) (?<cz>\S+) .*?cam (?<x>\S+) (?<y>\S+) (?<z>\S+) .*?fov (?<fov>\S+)')) { continue }
            $liRows++
            $la = @()
            foreach ($k in 'cx','cy','cz','x','y','z','fov') {
              $v = 0.0
              if (-not [double]::TryParse($Matches[$k], [Globalization.NumberStyles]::Float, $inv, [ref]$v) -or [double]::IsNaN($v) -or [double]::IsInfinity($v)) { $liBad++; $v = [double]::NaN }
              $la += $v
            }
            $lsFov = $Matches.fov
            $lfD = [math]::Sqrt([math]::Pow($la[3]-$la[0],2) + [math]::Pow($la[4]-$la[1],2) + [math]::Pow($la[5]-$la[2],2))
            if (-not [double]::IsNaN($lfD)) { $lfMax = [math]::Max($lfMax, $lfD); $lfMin = [math]::Min($lfMin, $lfD) }
          }
          $lbThis = ($liRows -ge 2 -and $liBad -eq 0 -and $lfMax -lt 60.0 -and $lfMax -gt 0.5)
          if (-not $lbThis) { $lbOk = $false }
          $laOut += ("{0}: rows={1} nonfinite={2} cam-to-car min={3:f2} max={4:f2} m last fov={5}" -f $lsWho, $liRows, $liBad, $lfMin, $lfMax, $lsFov)
        }
        return @{ Pass = $lbOk; Detail = ($laOut -join ' ; ') }
      } }
  )
}
