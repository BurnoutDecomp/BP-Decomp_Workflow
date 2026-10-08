# vw_camparams_testbed -- the director's "Testbed" debug menu lists every parameter block of the
# camera bank's version-5 walk (lane CAMPARAMS, issue #34 leftover). baseline_boot_drive's scenario
# plus a concurrent stimulus (Setup) that, once the car has been driving, activates the "Camera"
# debug component (DebugComponent::OnActivate runs the bank walk through TestbedSetupSerialiser),
# opens /Camera/Testbed as a window and walks it with the Down key under BRN_DEBUG_UI_TRACE.
# The console's walk registers 27 bank blocks there, each under its walk name; the checks count
# how many of the 27 names are rows of the live menu.
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case vw_camparams_testbed
@{
  Name    = 'vw_camparams_testbed'
  Area    = 'director'
  Bug     = 'Testbed menu lists 9 of the 27 bank blocks (seven Parameters types without the Behaviour::Parameters head)'
  Frames  = $true
  Run     = @{
    Drive       = $true
    MotionProbe = $true
    MaxSeconds  = 80
    SkipIntro   = $true
    AcceptGap   = 1.0
    FrameEvery  = 15
    Teleport    = '3040.7,-5.8,-1937.9,180'
  }
  DiagEnv = 'BRN_DEBUG_UI_TRACE=1'
  Setup   = {
    param($ctx)
    $lsHelper = Join-Path $ctx.Root 'tools\tests\tools\VW_CAMPARAMS_testbed.ps1'
    $lsArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$lsHelper`"",
                '-GameLog', "`"$($ctx.GameLog)`"", '-OutDir', "`"$($ctx.RunDir)`"", '-Slot', "$($ctx.Slot)")
    return Start-Process powershell -ArgumentList $lsArgs -PassThru -WindowStyle Hidden
  }
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'Script';     Name = 'the stimulus opened and walked the Testbed menu'; Script = {
        param($ctx)
        $lsLog = Join-Path $ctx.RunDir 'testbed_helper.log'
        if (-not (Test-Path $lsLog)) { return @{ Pass = $false; Detail = 'no testbed_helper.log' } }
        $lsText = Get-Content $lsLog -Raw
        return @{ Pass = ($lsText -match 'RESULT DONE'); Detail = (($lsText -split "`r?`n" | Where-Object { $_ -match 'RESULT|distinct|assert lines' }) -join ' ; ') }
      } }
    @{ Kind = 'Script';     Name = 'no assert while the page registered and was walked'; Script = {
        param($ctx)
        $lsLog = Join-Path $ctx.RunDir 'testbed_helper.log'
        if (-not (Test-Path $lsLog)) { return @{ Pass = $false; Detail = 'no testbed_helper.log' } }
        if ((Get-Content $lsLog -Raw) -notmatch 'assert lines in the game log: (\d+) before the page opened, (\d+) after') { return @{ Pass = $false; Detail = 'no assert count' } }
        return @{ Pass = ([int]$Matches[1] -eq [int]$Matches[2]); Detail = "before=$($Matches[1]) after=$($Matches[2])" }
      } }
    @{ Kind = 'Script';     Name = 'the Testbed menu lists all 27 bank blocks under the console walk names'; Script = {
        param($ctx)
        $lsRows = Join-Path $ctx.RunDir 'testbed_rows.txt'
        if (-not (Test-Path $lsRows)) { return @{ Pass = $false; Detail = 'no testbed_rows.txt' } }
        $laRows = @(Get-Content $lsRows | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' })
        # The console's testbed walk (BehaviourParameterBank::Serialise<TestbedSetupSerialiser>,
        # version 5), in walk order.
        $laBank = @(
          'Aftertouch', 'Aftertouch Crash', 'Crash Debug', 'HeliCam Default',
          'GyroCam Default', 'GyroCam Truck Front', 'GyroCam Truck Left', 'GyroCam Truck Right',
          'GyroCam Follow', 'GyroCam Always Low', 'GyroCam Takedown', 'GyroCam Takedown Zoomed Out',
          'GyroCam High', 'GyroCam Helicam', 'GyroCam DriveBy L', 'GyroCam DriveBy R',
          'Bystander Close', 'Bystander Far',
          'Rig Bonnet Low Right', 'Rig Rear Q Fwd', 'Rig Front Q Cu Fwd', 'Rig Front Q Bwd',
          'Failsafe', 'Fixed Cam Default', 'Rotate About Vehicle Default', 'Spiralling Deathcam Default',
          'Road Runner Default')
        $laFound   = @($laBank | Where-Object { $laRows -ccontains $_ })
        $laMissing = @($laBank | Where-Object { $laRows -cnotcontains $_ })
        $laOther   = @($laRows | Where-Object { $laBank -cnotcontains $_ })
        $lbOk = $laFound.Count -eq 27
        return @{ Pass = $lbOk; Detail = ("bank rows {0}/27; menu rows {1}; missing=[{2}]; other rows=[{3}]" -f $laFound.Count, $laRows.Count, ($laMissing -join ', '), ($laOther -join ', ')) }
      } }
  )
}
