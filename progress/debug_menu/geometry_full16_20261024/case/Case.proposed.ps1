# Proposal only. Root fills the binding after the hosted diagnostic build and private stage review.
$ErrorActionPreference = 'Stop'
$caseDir = $PSScriptRoot
$bindingPath = $env:GEOMETRY_RUNTIME_BINDING
$group = $env:GEOMETRY_CASE_GROUP
if ([string]::IsNullOrWhiteSpace($bindingPath) -or !(Test-Path -LiteralPath $bindingPath -PathType Leaf)) {
    throw 'Set GEOMETRY_RUNTIME_BINDING to the Root-reviewed private-run binding.'
}
if ($group -cne 'full16') { throw 'This packet exposes only the one-process full16 case.' }
$bindingPath = (Resolve-Path -LiteralPath $bindingPath).Path
$binding = Get-Content -LiteralPath $bindingPath -Raw | ConvertFrom-Json
$repoRoot = [IO.Path]::GetFullPath([string]$binding.repo_root)
$planPath = Join-Path $caseDir 'CASE_PLAN.json'
$sourceBindingsPath = Join-Path $caseDir 'CASE_SOURCE_BINDINGS.json'
$casePlan = Get-Content -LiteralPath $planPath -Raw | ConvertFrom-Json
if (!$casePlan.groups.PSObject.Properties[$group]) { throw "Unknown geometry case group: $group" }
$groupPlan = $casePlan.groups.$group
$stepsPath = Join-Path $caseDir ('steps/' + $group + '.txt')
$helperPath = Join-Path $caseDir 'TargetedGeometryKeys.proposed.ps1'
$checkerPath = Join-Path $caseDir 'checker.proposed.ps1'
$ownerCheckerPath = Join-Path $caseDir 'Check_owner.proposed.ps1'
$runCasePath = Join-Path $repoRoot 'tools/tests/run_case.ps1'
$flowRunPath = Join-Path $repoRoot 'tools/diagnostics/flow_run.ps1'

function Assert-Exact([string]$Name, [string]$Actual, [string]$Expected) {
    if ($Actual -cne $Expected) { throw "$Name differs: expected '$Expected', got '$Actual'." }
}
function Assert-FileHash([string]$Name, [string]$Path, [string]$Expected) {
    if ([string]::IsNullOrWhiteSpace($Path) -or !(Test-Path -LiteralPath $Path -PathType Leaf)) { throw "$Name is missing: $Path" }
    $actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    Assert-Exact $Name $actual $Expected.ToLowerInvariant()
}

$expectedSource = [string]$casePlan.candidate_source
$expectedTree = [string]$casePlan.candidate_tree
$expectedWorkflow = [string]$casePlan.base_hosted_workflow_source
$baseHostedExe = [string]$casePlan.base_hosted_401033_exe_sha256
if ([int]$binding.schema -ne 2 -or $binding.status -cne 'root_reviewed_ready' -or
    [int]$binding.slot -lt 1 -or [int]$binding.slot -gt 65535 -or
    [int]$binding.slot -in @(62064,62065,62066) -or !$binding.slot_created_for_this_case) {
    throw 'Binding schema/slot is not the reviewed private run.'
}
Assert-Exact 'candidate source' ([string]$binding.candidate_source) $expectedSource
Assert-Exact 'candidate tree' ([string]$binding.candidate_tree) $expectedTree
Assert-Exact 'base hosted workflow source' ([string]$binding.base_hosted_workflow_source) $expectedWorkflow
Assert-Exact 'hosted401033 base executable identity' ([string]$binding.base_hosted_401033_exe_sha256) $baseHostedExe
Assert-Exact 'probe patch identity' ([string]$binding.probe_patch_sha256) ([string]$casePlan.probe_patch_sha256)
Assert-Exact 'case source evidence binding' ([string]$binding.case_source_bindings_sha256) ([string]$casePlan.case_source_bindings_sha256)
if ([string]$binding.execution_exe_sha256 -notmatch '^[0-9a-f]{64}$' -or
    [string]$binding.execution_exe_sha256 -ceq $baseHostedExe) {
    throw 'Execution image must be the separately hosted build containing this exact diagnostic patch.'
}
if ($binding.hosted_probe_build.status -cne 'success' -or
    $binding.hosted_probe_build.candidate_source -cne $expectedSource -or
    $binding.hosted_probe_build.probe_patch_sha256 -cne [string]$casePlan.probe_patch_sha256 -or
    $binding.hosted_probe_build.exe_sha256 -cne [string]$binding.execution_exe_sha256) {
    throw 'Hosted probe-build receipt does not match the case source and staged executable.'
}

$privateRoot = [IO.Path]::GetFullPath([string]$binding.private_stage_root)
if ($privateRoot -ine [IO.Path]::GetFullPath((Join-Path $caseDir 'stage'))) { throw 'Private stage escaped this packet.' }
Assert-Exact 'private executable' ([string]$binding.private_exe_sha256) ([string]$binding.execution_exe_sha256)
Assert-FileHash 'staged executable' (Join-Path $privateRoot 'slot/Burnout_PC.exe') ([string]$binding.execution_exe_sha256)
Assert-FileHash 'staged config' (Join-Path $privateRoot 'slot/config.ini') ([string]$binding.private_config_sha256)
Assert-FileHash 'stage receipt' ([string]$binding.stage_receipt) ([string]$binding.stage_receipt_sha256)
Assert-FileHash 'hosted probe-build receipt' ([string]$binding.hosted_probe_build.receipt_path) ([string]$binding.hosted_probe_build.receipt_sha256)
Assert-FileHash 'profile fixture' ([string]$binding.profile_fixture.path) ([string]$binding.profile_fixture.sha256)
if ([IO.Path]::GetFileName($privateRoot) -cne 'stage') { throw 'Private stage root is not the packet-owned stage directory.' }
if ((Get-Item -LiteralPath $binding.profile_fixture.path).Length -ne [long]$binding.profile_fixture.bytes) { throw 'Profile fixture size differs.' }

foreach ($pair in @(
    @{Name='case';Path=$PSCommandPath;Expected=$binding.case_sha256},
    @{Name='plan';Path=$planPath;Expected=$binding.plan_sha256},
    @{Name='source evidence binding';Path=$sourceBindingsPath;Expected=$binding.case_source_bindings_sha256},
    @{Name='steps';Path=$stepsPath;Expected=$binding.steps_sha256.$group},
    @{Name='helper';Path=$helperPath;Expected=$binding.helper_sha256},
    @{Name='checker';Path=$checkerPath;Expected=$binding.checker_sha256},
    @{Name='owner checker';Path=$ownerCheckerPath;Expected=$binding.owner_checker_sha256},
    @{Name='run_case harness';Path=$runCasePath;Expected=$binding.run_case_sha256},
    @{Name='flow_run harness';Path=$flowRunPath;Expected=$binding.flow_run_sha256}
)) { Assert-FileHash $pair.Name $pair.Path ([string]$pair.Expected) }

@{
    Name = 'geometry_' + $group
    Area = 'scene-debug-controls'
    Bug = 'Exercise the exact registered TriangleCollision and SceneSweeper controls with independent per-site positive, negative, and restore states; require typed owner data before any site is exercised.'
    SourceRoot = $repoRoot
    RequiredSlot = [int]$binding.slot
    BindingPath = $bindingPath
    Binding = $binding
    CaseDir = $caseDir
    Group = $group
    Plan = $groupPlan
    PlanPath = $planPath
    StepsTemplatePath = $stepsPath
    CheckerPath = $checkerPath
    OwnerCheckerPath = $ownerCheckerPath
    HelperPath = $helperPath
    Frames = $true
    ProfileFixture = [string]$binding.profile_fixture.path
    ProfileFixtureSha256 = [string]$binding.profile_fixture.sha256
    Run = @{
        SkipIntro = $true
        TitleStart = $true
        AcceptGap = 1.0
        MaxSeconds = 240
        MinFreeGB = 20
        FrameEvery = 150
        BelowNormal = $true
        NoAssertRelease = $true
        StrictGameOwnership = $true
    }
    DiagEnv = 'BRN_DEBUG_GEOMETRY_WITNESS=1,BRN_FRAME_DUMP_REQUEST=1,BRN_FRAME_DUMP_MAX=96'
    Setup = {
        param($ctx)
        function Assert-SetupFileHash([string]$Name, [string]$Path, [string]$Expected) {
            if ([string]::IsNullOrWhiteSpace($Path) -or !(Test-Path -LiteralPath $Path -PathType Leaf)) { throw "$Name is missing: $Path" }
            $actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($actual -cne $Expected.ToLowerInvariant()) { throw "$Name hash differs." }
        }
        $lrBinding = Get-Content -LiteralPath $ctx.Case.BindingPath -Raw | ConvertFrom-Json
        $lrPlan = $ctx.Case.Plan
        if (!$ctx.Case.Run.StrictGameOwnership -or !$ctx.Case.Run.BelowNormal -or
            [int]$ctx.Slot -ne [int]$lrBinding.slot -or !$ctx.UsesPrivateStage) { throw 'Strict private-slot run binding differs.' }
        $lsStage = [IO.Path]::GetFullPath([string]$lrBinding.private_stage_root)
        if ([IO.Path]::GetFullPath($ctx.GameDir) -ine [IO.Path]::GetFullPath((Join-Path $lsStage 'slot')) -or
            [IO.Path]::GetFullPath($ctx.WorkingDirectory) -ine [IO.Path]::GetFullPath((Join-Path $lsStage 'data'))) {
            throw 'The run does not use the exact bound private slot/data pair.'
        }
        Assert-SetupFileHash 'owned executable' (Join-Path $ctx.GameDir 'Burnout_PC.exe') ([string]$lrBinding.execution_exe_sha256)
        Assert-SetupFileHash 'owned config' (Join-Path $ctx.GameDir 'config.ini') ([string]$lrBinding.private_config_sha256)
        $lsNormalRoster = @(Get-ChildItem -LiteralPath (Join-Path $lrBinding.repo_root 'build/game') -Directory -Filter 'Memcard*' |
            ForEach-Object { Join-Path $_.FullName 'Profile.sav' } | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Sort-Object)
        if (($lsNormalRoster -join "`n") -ine (@($lrBinding.normal_profile_roster | Sort-Object) -join "`n")) { throw 'Normal profile membership changed before Setup.' }
        foreach ($lrProtected in $lrBinding.normal_protected_paths) {
            $lrFile = Get-Item -LiteralPath $lrProtected.path
            if ($lrFile.PSIsContainer -or ($lrFile.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
                $lrFile.Length -ne [long]$lrProtected.bytes -or
                $lrFile.LastWriteTimeUtc.ToFileTimeUtc().ToString() -cne [string]$lrProtected.mtime_utc_filetime_ticks -or
                (Get-FileHash -LiteralPath $lrFile.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -cne [string]$lrProtected.sha256) {
                throw "Normal protected path changed before run: $($lrProtected.path)"
            }
        }
        $baseUri = [Uri]::new(([IO.Path]::GetFullPath($ctx.WorkingDirectory).TrimEnd('\') + '\'))
        $runUri = [Uri]::new(([IO.Path]::GetFullPath($ctx.RunDir).TrimEnd('\') + '\'))
        $lsRelative = [Uri]::UnescapeDataString($baseUri.MakeRelativeUri($runUri).ToString()).Replace('\','/')
        if ($lsRelative -match '[^A-Za-z0-9_./-]' -or $lsRelative.Length -gt 70) {
            throw "Run path cannot be typed by the bounded console helper: $lsRelative"
        }
        Copy-Item -LiteralPath $ctx.Case.BindingPath -Destination (Join-Path $ctx.RunDir 'runtime-binding.used.json') -Force
        Copy-Item -LiteralPath $ctx.Case.StepsTemplatePath -Destination (Join-Path $ctx.RunDir 'steps.template.txt') -Force
        Copy-Item -LiteralPath $ctx.Case.PlanPath -Destination (Join-Path $ctx.RunDir 'CASE_PLAN.used.json') -Force

        $laAliases = [Collections.Generic.List[object]]::new()
        foreach ($lrControl in $lrPlan.controls) {
            $laAliases.Add([pscustomobject]@{Name=[string]$lrControl.alias;Path=[string]$lrControl.path})
            if ($lrControl.paired_alias) { $laAliases.Add([pscustomobject]@{Name=[string]$lrControl.paired_alias;Path=[string]$lrControl.paired_path}) }
        }
        if ($lrPlan.support_sweep_test) { $laAliases.Add([pscustomobject]@{Name='TrSweep';Path='World/Collision/Test swept sphere collision'}) }
        $lrUnique = @{}
        foreach ($lrAlias in $laAliases) {
            if ($lrAlias.Name.Length -gt 9) { throw "Alias exceeds the original 9-character name limit: $($lrAlias.Name)" }
            if ($lrUnique.ContainsKey($lrAlias.Name)) { continue }
            $lrUnique[$lrAlias.Name] = $lrAlias.Path
        }

        $lsNonce = ([IO.Path]::GetFileName($ctx.RunDir) -replace '[^A-Za-z0-9_]','')
        if ($lsNonce.Length -gt 8) { $lsNonce = $lsNonce.Substring($lsNonce.Length - 8) }
        if ([string]::IsNullOrWhiteSpace($lsNonce)) { throw 'Cannot create a unique private setup command.' }
        $lsSetupName = 'geom_' + $lsNonce
        $lsSetupPath = Join-Path $ctx.WorkingDirectory $lsSetupName
        if (Test-Path -LiteralPath $lsSetupPath) { throw 'Private setup command already exists; use a fresh private stage.' }

        $lsInit = [Collections.Generic.List[string]]::new()
        foreach ($lsComponent in $lrPlan.component_names) { $lsInit.Add(('component "' + $lsComponent + '"')) }
        foreach ($lsAlias in $lrUnique.Keys) {
            $lsInit.Add(('alias "' + $lsAlias + '" "' + $lrUnique[$lsAlias] + '"'))
        }
        foreach ($lrAlias in $lrUnique.Keys) { $lsInit.Add(('alias "' + $lrAlias + '"')); $lsInit.Add([string]$lrAlias) }
        if ($lrPlan.support_sweep_test) { $null = $true } # The helper waits for owner/data preflight before enabling it.

        $laSchedule = @(Get-Content -LiteralPath $ctx.Case.StepsTemplatePath | Where-Object { $_ -match '^(?:SITE|SUPPORT)\|' })
        $laSiteSteps = @($laSchedule | Where-Object { $_ -match '^SITE\|' })
        $laSupportSteps = @($laSchedule | Where-Object { $_ -match '^SUPPORT\|' })
        if ($laSiteSteps.Count -ne 48 -or $laSupportSteps.Count -ne 2) { throw 'full16 must contain exactly48 site states and2 support actions.' }
        $lsInit.Add(('bind F1 exec "' + $lsRelative + '/action_01.txt"'))
        for ($i=1; $i -le 48; ++$i) {
            Set-Content -LiteralPath (Join-Path $ctx.RunDir ('action_{0:D2}.txt' -f $i)) -Value @('# owner-checked helper replaces this placeholder after data preflight') -Encoding ascii
        }
        $lsReadAliasNames = @($lrUnique.Keys)
        $lsReadLines = [Collections.Generic.List[string]]::new()
        foreach ($lsAlias in $lsReadAliasNames) { $lsReadLines.Add(('alias "' + $lsAlias + '"')); $lsReadLines.Add([string]$lsAlias) }
        $lsReadPath = Join-Path $ctx.RunDir 'readback.txt'
        Set-Content -LiteralPath $lsReadPath -Value $lsReadLines -Encoding ascii
        if ($lrPlan.support_sweep_test) {
            $lsInit.Add(('bind F2 exec "' + $lsRelative + '/support_on.txt"'))
            $lsInit.Add(('bind F3 exec "' + $lsRelative + '/support_restore.txt"'))
            $lsSupportOn = @('set "TrSweep" TRUE','alias "TrSweep"','TrSweep',('bind F2 exec "' + $lsRelative + '/readback.txt"'))
            Set-Content -LiteralPath (Join-Path $ctx.RunDir 'support_on.txt') -Value $lsSupportOn -Encoding ascii
            Set-Content -LiteralPath (Join-Path $ctx.RunDir 'support_restore.txt') -Value @('# generated from the captured baseline by the owner-checked helper') -Encoding ascii
        }
        $lsInitPath = Join-Path $ctx.RunDir 'setup.txt'
        Set-Content -LiteralPath $lsInitPath -Value $lsInit -Encoding ascii
        Copy-Item -LiteralPath $lsInitPath -Destination $lsSetupPath

        $loManifest = [ordered]@{
            schema=1; group=$ctx.Case.Group; candidate_source=$lrBinding.candidate_source
            candidate_tree=$lrBinding.candidate_tree; hosted_probe_build_id=$lrBinding.hosted_probe_build.id
            execution_exe_sha256=$lrBinding.execution_exe_sha256; slot=$ctx.Slot
            case_source_bindings_sha256=$lrBinding.case_source_bindings_sha256
            frame_capture_mode='one PID/slot-scoped named request per recorded state; periodic dump suppressed'; frame_every_presents_fallback=150
            frame_dump_cap=96; max_seconds=240; planned_capture_requests_if_all_gates_pass=51
            setup_command=$lsSetupName; components=@($lrPlan.component_names)
            aliases=$lrUnique; actions=$laSchedule; site_state_action_count=48; support_action_count=2
            diagnostic_caps=$ctx.Case.Binding.diagnostic_caps; gate=$lrPlan.preflight
            visual_review='required per site after machine evidence; no inventory disposition is emitted by this case'
        }
        $loManifest | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath (Join-Path $ctx.RunDir 'case-input-manifest.json') -Encoding ascii
        $laArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"' + $ctx.Case.HelperPath + '"'),
            '-GameLog',('"' + $ctx.GameLog + '"'),'-OutDir',('"' + $ctx.RunDir + '"'),
            '-FrameDir',('"' + (Join-Path $ctx.RunDir 'frames') + '"'),
            '-PlanPath',('"' + (Join-Path $ctx.RunDir 'CASE_PLAN.used.json') + '"'),
            '-StepsFile',('"' + (Join-Path $ctx.RunDir 'steps.template.txt') + '"'),
            '-RunRelativePath',([string]$lsRelative),
            '-Group',([string]$ctx.Case.Group),'-SetupCommand',([string]$lsSetupName),
            '-Slot',([string]$ctx.Slot),'-TimeoutSec','238',
            '-ExpectedImage',('"' + (Join-Path $ctx.GameDir 'Burnout_PC.exe') + '"'),
            '-ExpectedExeSha256',([string]$lrBinding.execution_exe_sha256),
            '-StartedAfterUtc',([DateTime]::UtcNow.ToString('o')))
        $helper = Start-Process -FilePath 'powershell.exe' -ArgumentList $laArgs -PassThru -WindowStyle Hidden
        $helper.PriorityClass = 'BelowNormal'
        return $helper
    }
    Checks = @(
        @{Kind='NewAsserts';Name='no new assert families'}
        @{Kind='LogCount';Name='zero assertions';Pattern='\[ASSERT \d+\]';Max=0}
        @{Kind='LogCount';Name='no game exceptions';Pattern='\[EXCEPTION\]';Max=0}
        @{Kind='Script';Name='actual geometry owners and per-site state capture';Script={ param($ctx) & $ctx.Case.OwnerCheckerPath -LogLines $ctx.LogLines -RunDir $ctx.RunDir -Binding $ctx.Case.Binding -Group $ctx.Case.Group }}
        @{Kind='Mark';Name='ordinary free-roam phase reached';Phase='DRIVING'}
        @{Kind='Script';Name='site machine gates and Root visual review';Script={ param($ctx) & $ctx.Case.CheckerPath -Context $ctx }}
    )
}
