# Case proposal only. Root supplies the reviewed binding and private slot before invoking run_case.
$caseRoot = $PSScriptRoot
$casePlanPath = Join-Path $caseRoot 'CASE_PLAN.json'
$casePlan = Get-Content -LiteralPath $casePlanPath -Raw | ConvertFrom-Json
$caseBindingPath = Join-Path $caseRoot 'BINDING.json'
$caseBinding = if (Test-Path -LiteralPath $caseBindingPath -PathType Leaf) { Get-Content -LiteralPath $caseBindingPath -Raw | ConvertFrom-Json } else { $null }
. (Join-Path $caseRoot 'CandidateArtifactGuard.ps1')



@{
    Name = 'debug_menu_circle_flags_two_control'
    CaseDir = $caseRoot
    Binding = $caseBinding
    Area = 'debug-menu'
    Bug = 'Verify the two source-backed World bounding-circle controls with paired pixel captures and exact bool readbacks.'
    Frames = $true
    ProfileFixture = 'DISCO_collect_base.sav'
    ProfileFixtureSha256 = [string]$caseBinding.profile_fixture.sha256
    Run = @{
        SkipIntro = $false
        AcceptGap = 1.0
        MaxSeconds = 420
        MinFreeGB = 20
        FrameEvery = 1000000000
        BelowNormal = $true
        NoAssertRelease = $true
        StrictGameOwnership = $true
        AllowConcurrentGames = $true
        Drive = $true
        TitleStart = $true
        DriveDelay = 2
        ThrottleScript = '0:brake+handbrake'
        MotionProbe = $true
    }
    DiagEnv = 'BRN_DEBUG_UI_TRACE=1,BRN_FRAME_DUMP_REQUEST=1,BRN_FRAME_DUMP_MAX=7,BRN_STARTLINE_DIAG=1'
    Setup = {
        param($ctx)
        $caseDir = $caseRoot
        . (Join-Path $caseDir 'CandidateArtifactGuard.ps1')
        $bindingPath = Join-Path $caseDir 'BINDING.json'
        $stagePath = Join-Path $caseDir 'STAGING.json'
        $reviewPath = Join-Path $caseDir 'ROOT_PRELAUNCH_REVIEW.json'
        $planPath = Join-Path $caseDir 'CASE_PLAN.json'
        $bindingsPath = Join-Path $caseDir 'CASE_SOURCE_BINDINGS.json'
        foreach ($path in @($bindingPath,$stagePath,$reviewPath,$planPath,$bindingsPath,(Join-Path $caseDir 'HOSTED_ARTIFACT_BINDING.json'))) {
            if (!(Test-Path -LiteralPath $path -PathType Leaf)) { throw "Root case binding is missing: $path" }
        }
        $binding = Get-Content -LiteralPath $bindingPath -Raw | ConvertFrom-Json
        $stage = Get-Content -LiteralPath $stagePath -Raw | ConvertFrom-Json
        $review = Get-Content -LiteralPath $reviewPath -Raw | ConvertFrom-Json
        $plan = Get-Content -LiteralPath $planPath -Raw | ConvertFrom-Json
        $expectedSelectedSites = @(
            'BrnWorld::WorldEntityModule::Construct#0002',
            'BrnWorld::PropEntityModule::Construct#0001'
        )
        if (@($plan.controls).Count -ne 2 -or (@($plan.selected_site_ids) -join '|') -cne ($expectedSelectedSites -join '|')) {
            throw 'Case plan must select exactly the two World bounding-circle controls.'
        }
        $sourceBindings = Get-Content -LiteralPath $bindingsPath -Raw | ConvertFrom-Json
        $repoRoot = 'D:\Reverse\BP-Decomp_Workflow'
        $artifact = Assert-CurrentCandidateArtifact $plan $binding $sourceBindings $caseDir $repoRoot $stage $review
        if ($sourceBindings.candidate_source -cne $plan.candidate_source -or
            $sourceBindings.candidate_tree -cne $plan.candidate_tree -or
            $sourceBindings.hosted_build_id -cne $plan.hosted_probe_build.id -or
            $sourceBindings.hosted_exe_sha256 -cne $plan.hosted_probe_build.exe_sha256 -or
            $sourceBindings.runtime_flow_run_source -cne '2b45db07e5496869a1b475e855ed9308b59b77fc') {
            throw 'Case source/build/runtime harness identity differs.'
        }
        foreach ($h in @(
            @{Path=(Join-Path $repoRoot 'tools/diagnostics/flow_run.ps1');Hash=$sourceBindings.runtime_flow_run_repo_file_sha256},
            @{Path=(Join-Path $repoRoot 'tools/tests/run_case.ps1');Hash=$sourceBindings.source_files.'tools/tests/run_case.ps1'.repo_file_sha256}
        )) {
            if ((Get-FileHash -LiteralPath $h.Path -Algorithm SHA256).Hash.ToLowerInvariant() -cne [string]$h.Hash) {
                throw "Runtime harness changed after source review: $($h.Path)"
            }
        }
        $expectedFixture = Join-Path $repoRoot 'tools/tests/fixtures/DISCO_collect_base.sav'
        if ([IO.Path]::GetFullPath([string]$binding.profile_fixture.path) -ine [IO.Path]::GetFullPath($expectedFixture) -or
            !(Test-Path -LiteralPath $expectedFixture -PathType Leaf) -or
            (Get-Item -LiteralPath $expectedFixture).Length -ne [long]$binding.profile_fixture.bytes -or
            (Get-FileHash -LiteralPath $expectedFixture -Algorithm SHA256).Hash.ToLowerInvariant() -cne [string]$binding.profile_fixture.sha256) {
            throw 'The pinned DISCO returning-profile fixture changed.'
        }
        if ([int]$binding.schema -ne 2 -or $binding.status -cne 'root_reviewed_ready' -or
            !$binding.slot_created_for_this_case -or [int]$binding.slot -ne [int]$ctx.Slot -or
            $binding.candidate_source -cne $plan.candidate_source -or
            $binding.candidate_tree -cne $plan.candidate_tree -or
            $binding.candidate_workflow_source -cne $plan.candidate_workflow_source -or
            $binding.candidate_workflow_tree -cne $plan.candidate_workflow_tree -or
            $binding.execution_exe_sha256 -cne $plan.hosted_probe_build.exe_sha256 -or
            $binding.case_source_bindings_sha256 -cne (Get-FileHash -LiteralPath $bindingsPath -Algorithm SHA256).Hash.ToLowerInvariant()) {
            throw 'Root-reviewed private-slot binding does not match the candidate or source bindings.'
        }
        $stageRoot = [IO.Path]::GetFullPath([string]$binding.private_stage_root)
        if ($stageRoot -ine [IO.Path]::GetFullPath((Join-Path $caseDir 'stage')) -or
            [IO.Path]::GetFullPath($ctx.GameDir) -ine [IO.Path]::GetFullPath((Join-Path $stageRoot 'slot')) -or
            [IO.Path]::GetFullPath($ctx.WorkingDirectory) -ine [IO.Path]::GetFullPath((Join-Path $stageRoot 'data')) -or
            !$ctx.UsesPrivateStage) {
            throw 'Setup is not using this case exact private stage/slot/data pair.'
        }
        if ((Get-FileHash -LiteralPath (Join-Path $ctx.GameDir 'Burnout_PC.exe') -Algorithm SHA256).Hash.ToLowerInvariant() -cne [string]$binding.execution_exe_sha256) {
            throw 'Private executable differs from the Root-reviewed hosted image.'
        }
        if ((Get-FileHash -LiteralPath (Join-Path $ctx.GameDir 'config.ini') -Algorithm SHA256).Hash.ToLowerInvariant() -cne [string]$binding.private_config_sha256) {
            throw 'Private config differs from Root staging.'
        }
        $helper = Join-Path $caseDir 'BoostHudKeys.proposed.ps1'
        $controls = Join-Path $caseDir 'DebugCircleControls.ps1'
        $evidence = Join-Path $caseDir 'BoostBarEvidence.ps1'
        $checker = Join-Path $caseDir 'checker.proposed.ps1'
        $candidateGuard = Join-Path $caseDir 'CandidateArtifactGuard.ps1'
        $helperHash = (Get-FileHash -LiteralPath $helper -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($binding.helper_sha256 -cne $helperHash -or
            $binding.controls_sha256 -cne (Get-FileHash -LiteralPath $controls -Algorithm SHA256).Hash.ToLowerInvariant() -or
            $binding.evidence_sha256 -cne (Get-FileHash -LiteralPath $evidence -Algorithm SHA256).Hash.ToLowerInvariant() -or
            $binding.checker_sha256 -cne (Get-FileHash -LiteralPath $checker -Algorithm SHA256).Hash.ToLowerInvariant() -or
            $binding.candidate_guard_sha256 -cne (Get-FileHash -LiteralPath $candidateGuard -Algorithm SHA256).Hash.ToLowerInvariant() -or
            $binding.case_sha256 -cne (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant() -or
            $binding.case_plan_sha256 -cne (Get-FileHash -LiteralPath $planPath -Algorithm SHA256).Hash.ToLowerInvariant() -or
            $binding.case_source_bindings_sha256 -cne (Get-FileHash -LiteralPath $bindingsPath -Algorithm SHA256).Hash.ToLowerInvariant()) {
            throw 'Case, plan, or helper changed after Root review.'
        }
        $baseUri = [Uri]::new(([IO.Path]::GetFullPath($ctx.WorkingDirectory).TrimEnd('\') + '\'))
        $runUri = [Uri]::new(([IO.Path]::GetFullPath($ctx.RunDir).TrimEnd('\') + '\'))
        $relative = [Uri]::UnescapeDataString($baseUri.MakeRelativeUri($runUri).ToString()).Replace('\','/')
        if ($relative -match '[^A-Za-z0-9_./-]' -or $relative.Length -gt 70) { throw "Run path cannot be typed by the bounded console helper: $relative" }
        Copy-Item -LiteralPath $bindingPath -Destination (Join-Path $ctx.RunDir 'runtime-binding.used.json') -Force
        Copy-Item -LiteralPath $planPath -Destination (Join-Path $ctx.RunDir 'CASE_PLAN.used.json') -Force
        Copy-Item -LiteralPath $bindingsPath -Destination (Join-Path $ctx.RunDir 'CASE_SOURCE_BINDINGS.used.json') -Force
        Copy-Item -LiteralPath (Join-Path $caseDir 'HOSTED_ARTIFACT_BINDING.json') -Destination (Join-Path $ctx.RunDir 'HOSTED_ARTIFACT_BINDING.used.json') -Force
        Copy-Item -LiteralPath $stagePath -Destination (Join-Path $ctx.RunDir 'STAGING.used.json') -Force
        Copy-Item -LiteralPath $reviewPath -Destination (Join-Path $ctx.RunDir 'ROOT_PRELAUNCH_REVIEW.used.json') -Force
        $contextPath=Join-Path $ctx.RunDir 'ROOT_TRIGGER_CONTEXT.json'
        if(Test-Path -LiteralPath $contextPath){throw 'Trigger context already exists; no retry.'}
        [ordered]@{slot=[int]$ctx.Slot;image=(Join-Path $ctx.GameDir 'Burnout_PC.exe');exe_sha256=[string]$binding.execution_exe_sha256;
            game_log=$ctx.GameLog;flow_log=(Join-Path $ctx.RunDir 'flow_run.console.log');out_dir=$ctx.RunDir;
            working_directory=$ctx.WorkingDirectory;frame_dir=(Join-Path $ctx.RunDir 'frames');
            plan_path=(Join-Path $ctx.RunDir 'CASE_PLAN.used.json');binding_path=(Join-Path $ctx.RunDir 'runtime-binding.used.json');
            run_relative_path=$relative;started_after_utc=[DateTime]::UtcNow.ToString('o')}|
            ConvertTo-Json -Depth 5|Set-Content -LiteralPath $contextPath -Encoding UTF8
        Write-Host '[case] Prepared exact two-control circle trigger context; Root immediate owned-process handoff starts the helper.'
    }.GetNewClosure()
    Checks = @(
        @{ Kind='NewAsserts'; Name='no new assert families' }
        @{ Kind='LogCount'; Name='no game exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }
        @{ Kind='Mark'; Name='ordinary free-roam driving reached'; Phase='DRIVING' }
        @{ Kind='Script'; Name='single owned helper completes within the case bound'; Script={
            param($ctx)
            $p=Join-Path $ctx.RunDir 'boost-hud-keys.log'
            $t=if(Test-Path -LiteralPath $p -PathType Leaf){[IO.File]::ReadAllText($p)}else{''}
            $done=[regex]::Matches($t,'(?m)^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{7}Z RESULT DONE sites=(\d+) deferred=(\d+) states=(\d+) frames=(\d+)\r?$');$failed=[regex]::Matches($t,'(?m)^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{7}Z RESULT FAIL: [^\r\n]+\r?$')
            return @{Pass=($done.Count -eq 1 -and $failed.Count -eq 0);Detail=($t -split '\r?\n' | Where-Object { $_ -match 'RESULT|SITE ' }) -join ' | '}
        } }
        @{ Kind='Script'; Name='owner, capture, source-gate, and restoration witness checker'; Script={
            param($ctx)
            & (Join-Path $caseRoot 'checker.proposed.ps1') -Context $ctx
        }.GetNewClosure() }
    )
}
