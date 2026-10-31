$ErrorActionPreference = 'Stop'
$owner = $PSScriptRoot
$stagePath = Join-Path $owner 'STAGING.json'
if (!(Test-Path -LiteralPath $stagePath -PathType Leaf)) {
    throw 'Root must create the reviewed private STAGING.json from STAGING.TEMPLATE.json before a run.'
}
$stage = Get-Content -Raw -LiteralPath $stagePath | ConvertFrom-Json
$scope = Get-Content -Raw -LiteralPath (Join-Path $owner 'SCOPE.json') | ConvertFrom-Json
if ($stage.slot -ne 62190) { throw 'Only private slot 62190 is reserved for this draft.' }
if ($stage.exe_sha256 -cne $scope.candidate.exe_sha256) { throw 'Stage executable pin mismatch.' }
if ($stage.profile_sha256 -cne $stage.profile_fixture_sha256) { throw 'Private profile fixture pin mismatch.' }
$case = @{
    Name = 'native_scene_shadow_director_62190'
    OwnerDir = $owner
    Area = 'debug-menu-native'
    Bug = 'Scene Manager, ShadowMap and remaining pending Director controls; field P/N/restore only. Per-site consumer gaps remain pending.'
    Frames = $true
    ProfileFixture = $stage.profile_fixture
    ProfileFixtureSha256 = $stage.profile_fixture_sha256
    Run = @{
        Drive = $true
        MotionProbe = $true
        TitleStart = $true
        SkipIntro = $true
        AcceptGap = 1.0
        MaxSeconds = 1500
        MinFreeGB = 2
        MaxLogMB = 48
        NoAssertRelease = $true
        StrictGameOwnership = $true
        AllowConcurrentGames = $false
        Audio = $false
        DriveDelay = 2.0
        ThrottleScript = '0:accel,6:brake+handbrake,10:none'
        FrameEvery = 1000000000
    }
    DiagEnv = 'BRN_DEBUG_UI_TRACE=1,BRN_FRAME_DUMP_REQUEST=1,BRN_FRAME_DUMP_MAX=90'
    Setup = {
        param($ctx)
        $package = $ctx.Case.OwnerDir
        $scope = Get-Content -Raw -LiteralPath (Join-Path $package 'SCOPE.json') | ConvertFrom-Json
        $stage = Get-Content -Raw -LiteralPath (Join-Path $package 'STAGING.json') | ConvertFrom-Json
        $pins = Get-Content -Raw -LiteralPath (Join-Path $package 'SOURCE_PINS.json') | ConvertFrom-Json
        if ($ctx.Slot -ne 62190 -or !$ctx.UsesPrivateStage -or
            $ctx.GameDir -ine $stage.exe_dir -or $ctx.WorkingDirectory -ine $stage.cwd) {
            throw 'Wrong private 62190 stage binding.'
        }
        if ($env:NATIVE_SCENE_RUN_CASE_PATH -cne [string]$pins.runner_binding.workflow_helpers.run_case.path -or
            $env:NATIVE_SCENE_FLOW_RUN_PATH -cne [string]$pins.runner_binding.workflow_helpers.flow_run.path) {
            throw 'Run only through Invoke-PrivateCase.ps1 with the pinned private run_case/flow_run pair.'
        }
        $preflight = & (Join-Path $package 'Preflight.ps1') -AtRun -RunDir $ctx.RunDir -StagePath (Join-Path $package 'STAGING.json')
        if ($preflight.pass -ne $true) { throw ('prelaunch static preflight failed: ' + ($preflight.problems -join '; ')) }
        $exe = Join-Path $ctx.GameDir 'Burnout_PC.exe'
        if ((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant() -cne $scope.candidate.exe_sha256) {
            throw 'Private stage executable does not match the clean installed artifact.'
        }
        if (Test-Path -LiteralPath $ctx.GameLog) { throw 'Owned game log must be fresh.' }
        . (Join-Path $package 'PathGuards.ps1')
        $private = Assert-BrnPrivateProfile $stage.profile 'private current profile'
        if ($private.status -cne 'regular_single_link_private_file' -or
            $private.sha256 -cne $stage.profile_sha256 -or
            [IO.Path]::GetFullPath($stage.profile) -ieq [IO.Path]::GetFullPath($stage.profile_fixture)) {
            throw 'Private 62190 profile identity/hash mismatch.'
        }
        $private | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $ctx.RunDir 'PRIVATE_PROFILE_BINDING.json') -Encoding utf8

        $all = @($scope.controls) + @($scope.context_aliases)
        $setupCommands = [Collections.Generic.List[string]]::new()
        foreach ($row in @($all | Where-Object { $_.id -like 'BrnWorld::ShadowMap*' })) {
            $setupCommands.Add(('alias ' + $row.alias + ' "' + $row.lookup_path + '"'))
        }
        $setupCommands.Add('component "Scene manager"')
        foreach ($row in @($all | Where-Object { $_.id -like 'CgsSceneManager*' })) {
            $setupCommands.Add(('alias ' + $row.alias + ' "' + $row.lookup_path + '"'))
        }
        $setupCommands.Add('component "Camera"')
        foreach ($row in @($all | Where-Object { $_.id -like 'BrnDirector::DebugComponent*' })) {
            $setupCommands.Add(('alias ' + $row.alias + ' "' + $row.lookup_path + '"'))
        }
        $setupCommands.Add('bind F11 exec q62190.cfg')
        foreach ($row in $all) {
            $setupCommands.Add(('alias ' + $row.alias))
            $setupCommands.Add($row.alias)
            $setupCommands.Add(('alias ' + $row.alias))
        }
        [IO.File]::WriteAllLines((Join-Path $ctx.WorkingDirectory 'b1.cfg'), $setupCommands.ToArray(), [Text.Encoding]::ASCII)
        [IO.File]::WriteAllText((Join-Path $ctx.WorkingDirectory 'q62190.cfg'), ('# private phase placeholder' + [Environment]::NewLine), [Text.Encoding]::ASCII)

        $driver = Join-Path $package 'Driver.ps1'
        $args = @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"' + $driver + '"'),
            '-RunDir',('"' + $ctx.RunDir + '"'),
            '-ExpectedSlotExe',('"' + $exe + '"'),
            '-GameLog',('"' + $ctx.GameLog + '"'),
            '-Slot','62190')
        $proc = Start-Process pwsh -WindowStyle Hidden -PassThru -ArgumentList $args -RedirectStandardOutput (Join-Path $ctx.RunDir 'driver.console.log') -RedirectStandardError (Join-Path $ctx.RunDir 'driver.stderr.log')
        $readyPath = Join-Path $ctx.RunDir 'DRIVER_READY.json'
        $until = [DateTime]::UtcNow.AddSeconds(12)
        while (!(Test-Path -LiteralPath $readyPath)) {
            if ($proc.HasExited -or [DateTime]::UtcNow -gt $until) { throw 'Driver did not establish slot-scoped input events.' }
            Start-Sleep -Milliseconds 50
        }
        $ready = Get-Content -Raw -LiteralPath $readyPath | ConvertFrom-Json
        if ($ready.status -cne 'ready' -or $ready.slot -ne 62190 -or
            $ready.driver_pid -ne $proc.Id -or $ready.event_count -ne 256 -or
            $ready.planned_max_frames -gt $scope.raw_frame_budget.max_frames -or
            $ready.max_raw_frames -ne $scope.raw_frame_budget.max_frames) {
            throw 'Wrong driver event owner.'
        }
        return $proc
    }
    Checks = @(
        @{ Kind='NewAsserts'; Name='no new assertions' },
        @{ Kind='LogCount'; Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 },
        @{ Kind='Mark'; Name='reached DRIVING'; Phase='DRIVING' },
        @{ Kind='Script'; Name='native mutation, terminal restore and capture audit'; Script={
            param($ctx)
            $runScope = Get-Content -Raw -LiteralPath (Join-Path $ctx.Case.OwnerDir 'SCOPE.json') | ConvertFrom-Json
            $resultPath = Join-Path $ctx.RunDir 'driver-result.json'
            $capturePath = Join-Path $ctx.RunDir 'CAPTURE_AUDIT.json'
            $phaseRequestPath = Join-Path $ctx.RunDir 'PHASE_DONE_REQUEST.json'
            $flowTerminalPath = Join-Path $ctx.RunDir 'flow-terminal.json'
            if (!(Test-Path -LiteralPath $resultPath)) { return @{Pass=$false;Detail='missing driver result'} }
            if (!(Test-Path -LiteralPath $capturePath)) { return @{Pass=$false;Detail='missing capture integrity audit'} }
            if (!(Test-Path -LiteralPath $phaseRequestPath)) { return @{Pass=$false;Detail='missing exact-owned phase completion receipt'} }
            if (!(Test-Path -LiteralPath $flowTerminalPath)) { return @{Pass=$false;Detail='missing pinned flow terminal receipt'} }
            $r = Get-Content -Raw -LiteralPath $resultPath | ConvertFrom-Json
            $c = Get-Content -Raw -LiteralPath $capturePath | ConvertFrom-Json
            $p = Get-Content -Raw -LiteralPath $phaseRequestPath | ConvertFrom-Json
            $f = Get-Content -Raw -LiteralPath $flowTerminalPath | ConvertFrom-Json
            $phaseStartTicks = [DateTimeOffset]::Parse([string]$p.start_utc,[cultureinfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind).UtcDateTime.Ticks
            $expectedPhaseEvent = 'Local\BurnoutPC_HarnessPhaseDone_{0}_{1}_{2}' -f $p.process_id,$p.slot,$phaseStartTicks
            $eventPass = ($p.status -ceq 'exact_owned_phase_completion_stop_requested' -and
                $p.event_set -eq $true -and $p.process_id -eq $r.process_id -and $p.slot -eq 62190 -and
                $p.image -ieq $r.process_path -and $f.flow_status.owned_pid -eq $r.process_id -and
                $f.flow_status.owned_image -ieq $r.process_path -and
                $p.event_name -ceq $expectedPhaseEvent -and
                $p.witness_sha256 -ceq (Get-FileHash -LiteralPath $resultPath -Algorithm SHA256).Hash.ToLowerInvariant() -and
                $f.flow_status.phase_collection_stop_requested -eq $true -and
                $f.flow_status.owned_cleanup_complete -eq $true -and $f.flow_status.success -eq $true)
            $pass = ($r.status -ceq 'machine_complete_awaiting_independent_pixels' -and
                $r.terminal_restore_verified -eq $true -and $r.slot -eq 62190 -and
                $r.site_credit -eq 0 -and $c.pass -eq $true -and
                $c.frame_count -le $runScope.raw_frame_budget.max_frames -and
                $r.planned_max_frames -le $runScope.raw_frame_budget.max_frames -and $eventPass)
            return @{Pass=$pass;Detail=('status='+$r.status+' restored='+$r.terminal_restore_verified+
                ' written='+$r.completed_target_count+' skipped='+$r.skipped_controls.Count+
                ' frames='+$c.frame_count+' event_stop='+$eventPass+' site_credit=0')}
        } }
    )
}
$case


