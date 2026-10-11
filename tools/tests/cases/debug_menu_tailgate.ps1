# Drive the original COMPONENT/SET/EXEC commands through the real debug console.
# Extreme legal slider values deliberately make detection independent of rival
# position; the witness only observes the resulting detector/boost state.
@{
    Name = 'debug_menu_tailgate'
    Area = 'debug-menu'
    Bug = 'Tailgate sliders must control the live detector and boost-credit threshold.'
    Frames = $false
    ProfileFixture = 'rival_hunt_profile.sav'
    Run = @{
        MotionProbe = $true
        Drive = $true
        DriveDelay = 3.0
        DriveSeconds = 1.0
        SkipIntro = $true
        AcceptGap = 1.0
        Teleport = '3040.7,-5.8,-1937.9,180'
        StartEvent = $true
        EventFsm = $true
        SkipTrainingTip = $true
        MaxSeconds = 90
    }
    DiagEnv = 'BRN_DEBUG_UI_TRACE=1,BRN_TAILGATE_DEBUG_TRACE=1'
    Setup = {
        param($ctx)
        $lsRelative = '../../' + $ctx.RunDir.Substring(([string]$ctx.Root).TrimEnd('\').Length + 1).Replace('\','/')
        $lsGroup = 'Race Car Entity/Tailgate.../'
        $laScripts = @(
            @('component "Race Car Entity"',
              ('set "' + $lsGroup + 'Cone HalfAngle (Rads)" 3'),
              ('set "' + $lsGroup + 'Cone Depth" 100000'),
              ('set "' + $lsGroup + 'Min Tailgate Speed" -100000'),
              ('set "' + $lsGroup + 'Max Relative Speed" 100000'),
              ('set "' + $lsGroup + 'Min Duration" 0')),
            @(('set "' + $lsGroup + 'Min Duration" 100000')),
            @(('set "' + $lsGroup + 'Min Duration" 0')),
            @(('set "' + $lsGroup + 'Min Tailgate Speed" 100000')),
            @(('set "' + $lsGroup + 'Min Tailgate Speed" -100000'),
              ('set "' + $lsGroup + 'Cone Depth" 0')),
            @(('set "' + $lsGroup + 'Cone Depth" 100000'),
              ('set "' + $lsGroup + 'Max Relative Speed" 0')),
            @(('set "' + $lsGroup + 'Max Relative Speed" 100000'))
        )
        $laSteps = @('wait:CarSelectManager: Exit state is finished', 'sleep:4', 'key:192')
        for ($liStage = 0; $liStage -lt $laScripts.Count; ++$liStage) {
            $lsFile = 'tailgate-' + $liStage + '.txt'
            if ($liStage -gt 0) {
                $laScripts[0] += ('bind F' + ($liStage+1) + ' exec "' + $lsRelative + '/' + $lsFile + '"')
            }
            Set-Content -LiteralPath (Join-Path $ctx.RunDir $lsFile) -Value $laScripts[$liStage] -Encoding ascii
            $laSteps += $(if ($liStage -eq 0) { 'cmd:exec "' + $lsRelative + '/' + $lsFile + '"' } else { 'key:' + (112+$liStage) })
            $laSteps += 'sleep:1'
            $laSteps += ('note:stage-' + $liStage)
        }
        # The initial script also installs the original F2..F7 EXEC bindings.
        Set-Content -LiteralPath (Join-Path $ctx.RunDir 'tailgate-0.txt') -Value $laScripts[0] -Encoding ascii
        $laSteps += 'key:192'
        $lsSteps = Join-Path $ctx.RunDir 'debug-menu-steps.txt'
        Set-Content -LiteralPath $lsSteps -Value $laSteps -Encoding ascii
        $lsHelper = Join-Path $ctx.Root 'tools/tests/tools/VW_DEFORM_debugkeys.ps1'
        $laArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$lsHelper`"",
            '-GameLog', "`"$($ctx.GameLog)`"", '-OutDir', "`"$($ctx.RunDir)`"",
            '-Slot', "$($ctx.Slot)", '-StepsFile', "`"$lsSteps`"", '-TimeoutSec', '85')
        return Start-Process powershell -ArgumentList $laArgs -PassThru -WindowStyle Hidden
    }
    Checks = @(
        @{ Kind='NewAsserts'; Name='no new assert families' }
        @{ Kind='LogCount'; Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }
        @{ Kind='Mark'; Name='reached driving'; Phase='DRIVING' }
        @{ Kind='Script'; Name='all real console commands completed'; Script={
            param($ctx)
            $lsFile = Join-Path $ctx.RunDir 'vw_deform_keys.log'
            $lsText = if (Test-Path $lsFile) { Get-Content $lsFile -Raw } else { '' }
            return @{ Pass=($lsText -match 'RESULT DONE'); Detail=($lsText -split "`r?`n" | Where-Object { $_ -match 'note:|RESULT' }) -join ' | ' }
        } }
        @{ Kind='Script'; Name='menu changes reach detection and boost, including reversibility'; Script={
            param($ctx)
            $laRows = @()
            foreach ($lsLine in $ctx.LogLines) {
                if ($lsLine -match '\[tailgate-debug\] cone=(\S+) depth=(\S+) minSpeed=(\S+) maxRelative=(\S+) minDuration=(\S+) duration=(\S+) car=(-?\d+) active=(\d)') {
                    $laRows += ,@((1..6 | ForEach-Object { [double]::Parse($Matches[$_], [cultureinfo]::InvariantCulture) }) + @([int]$Matches[7], [int]$Matches[8]))
                }
            }
            $laStages = @(
                @($laRows | Where-Object { $_[0] -eq 3 -and $_[1] -eq 100000 -and $_[2] -eq -100000 -and $_[3] -eq 100000 -and $_[4] -eq 0 -and $_[6] -ge 0 -and $_[7] -eq 1 }),
                @($laRows | Where-Object { $_[2] -eq 100000 -and $_[6] -eq -1 -and $_[7] -eq 0 }),
                @($laRows | Where-Object { $_[1] -eq 0 -and $_[2] -eq -100000 -and $_[6] -eq -1 -and $_[7] -eq 0 }),
                @($laRows | Where-Object { $_[1] -eq 100000 -and $_[3] -eq 0 -and $_[6] -eq -1 -and $_[7] -eq 0 }),
                @($laRows | Where-Object { $_[3] -eq 100000 -and $_[4] -eq 100000 -and $_[5] -gt 0 -and $_[6] -ge 0 -and $_[7] -eq 0 })
            )
            $laMissing = @(for ($liStage=0; $liStage -lt $laStages.Count; ++$liStage) {
                if ($laStages[$liStage].Count -eq 0) { $liStage }
            })
            $lbRestored = $false
            for ($liRow=1; $liRow -lt $laRows.Count; ++$liRow) {
                if ($laRows[$liRow-1][4] -eq 100000 -and $laRows[$liRow][4] -eq 0 -and $laRows[$liRow][7] -eq 1) { $lbRestored=$true }
            }
            return @{ Pass=($laMissing.Count -eq 0 -and $lbRestored); Detail="samples=$($laRows.Count) missing stages=[$($laMissing -join ',')] restored=$lbRestored" }
        } }
    )
}
