[CmdletBinding()]
param(
    [switch]$AtRun,
    [string]$RunDir,
    [string]$StagePath
)

$ErrorActionPreference = 'Stop'
$package = $PSScriptRoot
# These data/review outputs are not executable authored inputs. Unknown top-level files still fail.
$runtimeMetadataFiles=@('STAGING.json','REVIEW.md','REVIEW.json')
. (Join-Path $package 'PathGuards.ps1')
. (Join-Path $package 'StageBoundary.ps1')
$problems = [Collections.Generic.List[string]]::new()
$checks = [Collections.Generic.List[object]]::new()

function Add-Check([string]$Name,[bool]$Pass,[string]$Detail) {
    $script:checks.Add([ordered]@{name=$Name;pass=$Pass;detail=$Detail})
    if (-not $Pass) { $script:problems.Add($Name + ': ' + $Detail) }
}
function ConvertTo-PreflightF32([object]$Value,[string]$Label) {
    $text = [Convert]::ToString($Value,[cultureinfo]::InvariantCulture)
    $single = [single]0
    if (-not [single]::TryParse($text,[Globalization.NumberStyles]::Float,[cultureinfo]::InvariantCulture,[ref]$single)) {
        throw ($Label + ' is not a valid invariant f32')
    }
    if ([single]::IsNaN($single) -or [single]::IsInfinity($single)) { throw ($Label + ' is non-finite') }
    return $single
}
function Get-PreflightBits([object]$Value,[string]$Label) {
    $single = ConvertTo-PreflightF32 $Value $Label
    return [BitConverter]::ToUInt32([BitConverter]::GetBytes($single),0).ToString('X8')
}
function Get-Family([object]$Control) {
    if ([string]$Control.id -like 'CgsSceneManager::*') { return 'scene' }
    if ([string]$Control.id -like 'BrnWorld::ShadowMap::*') { return 'shadow' }
    if ([string]$Control.id -like 'BrnDirector::*') { return 'director' }
    throw ('unclassified phase family: ' + $Control.id)
}

$scopePath = Join-Path $package 'SCOPE.json'
$pinsPath = Join-Path $package 'SOURCE_PINS.json'
$stageTemplatePath = Join-Path $package 'STAGING.TEMPLATE.json'
$expectedProgressPath = Join-Path $package 'CURRENT_SAVE_EXPECTED_PROGRESS.json'
$casePath = Join-Path $package 'Case.ps1'
$scope = Get-Content -Raw -LiteralPath $scopePath | ConvertFrom-Json
$pins = Get-Content -Raw -LiteralPath $pinsPath | ConvertFrom-Json
$stageTemplate = Get-Content -Raw -LiteralPath $stageTemplatePath | ConvertFrom-Json
$expectedProgress = Get-Content -Raw -LiteralPath $expectedProgressPath | ConvertFrom-Json

$draftHashProblems = [Collections.Generic.List[string]]::new()
foreach ($pin in $pins.authored_files_sha256.PSObject.Properties) {
    $filePath = Join-Path $package $pin.Name
    if (-not (Test-Path -LiteralPath $filePath -PathType Leaf)) { $draftHashProblems.Add(([string]$pin.Name + ' missing')); continue }
    $actual = (Get-FileHash -LiteralPath $filePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -cne [string]$pin.Value) { $draftHashProblems.Add(([string]$pin.Name + ' hash mismatch')) }
}
$expectedDraftNames = @(Get-ChildItem -LiteralPath $package -File | Where-Object { $_.Name -notin (@('SOURCE_PINS.json','ALL_FILE_HASHES.sha256')+$runtimeMetadataFiles) } | ForEach-Object Name | Sort-Object)
$pinnedDraftNames = @($pins.authored_files_sha256.PSObject.Properties | ForEach-Object Name | Sort-Object)
if (($expectedDraftNames -join "`n") -cne ($pinnedDraftNames -join "`n")) { $draftHashProblems.Add('v2 source hash pin name set is incomplete or stale') }
Add-Check 'v2_artifact_hash_pins' ($draftHashProblems.Count -eq 0 -and $pins.authored_files_sha256.PSObject.Properties.Count -gt 0) $(if ($draftHashProblems.Count) { $draftHashProblems -join '; ' } else { 'All v2 source and metadata files match their SHA-256 pins, and the pin list covers the complete package except the pin file and recursive hash manifest.' })

Add-Check 'batch_size' ($scope.control_count -eq 28 -and $scope.controls.Count -eq 28) '28 pending targets are retained.'
$allAliases = @($scope.controls.alias) + @($scope.context_aliases.alias)
$uniqueAliases = @($allAliases | Sort-Object -Unique)
Add-Check 'declared_aliases' ($allAliases.Count -eq 30 -and $uniqueAliases.Count -eq 30) '30 unique target/context aliases.'

$validAliases = @{}
foreach ($alias in $allAliases) { $validAliases[[string]$alias] = $true }
$contextProblems = [Collections.Generic.List[string]]::new()
foreach ($control in $scope.controls) {
    foreach ($override in @($control.context_overrides)) {
        if ([string]$override.alias -match '=' -or -not $validAliases.ContainsKey([string]$override.alias) -or $override.value -isnot [bool]) {
            $contextProblems.Add(([string]$control.alias + ' -> ' + [string]$override.alias))
        }
    }
}
Add-Check 'context_alias_contract' ($contextProblems.Count -eq 0) $(if ($contextProblems.Count) { $contextProblems -join ', ' } else { 'Every temporary context uses a plain declared alias and Boolean value, including the restore-map inputs.' })

$floatProblems = [Collections.Generic.List[string]]::new()
foreach ($control in $scope.controls | Where-Object type -eq 'f32') {
    try {
        foreach ($field in @('source_default','positive','negative')) { [void](ConvertTo-PreflightF32 $control.$field ($control.alias + ' ' + $field)) }
        foreach ($field in @('source_default','positive','negative')) {
            $key = $field + '_bits'
            $actual = Get-PreflightBits $control.$field ($control.alias + ' ' + $field)
            if ($actual -cne [string]$control.f32_baseline.$key) { throw ($key + ' pin mismatch') }
        }
    } catch { $floatProblems.Add(([string]$control.alias + ': ' + $_.Exception.Message)) }
}
Add-Check 'typed_f32_values' ($floatProblems.Count -eq 0) $(if ($floatProblems.Count) { $floatProblems -join '; ' } else { 'Every f32 source default and probe is finite and has a matching exact IEEE-754 single bit pin.' })

$sc08 = $scope.controls | Where-Object alias -eq 'SC08'
$stepRatio = ([double]$sc08.negative - [double]$sc08.source_default) / [double]$sc08.ui.step
Add-Check 'scene_padding_step' ([Math]::Abs($stepRatio - [Math]::Round($stepRatio)) -lt 0.000001) ('SC08 negative delta is ' + $stepRatio + ' registered 0.25 steps.')

$phaseNames = [Collections.Generic.List[string]]::new()
foreach ($control in $scope.controls) {
    $family = Get-Family $control
    foreach ($state in @('positive','negative','restore')) { $phaseNames.Add(($family + '_' + [string]$control.alias + '_' + $state)) }
}
foreach ($name in @('natural_baseline','scene_triangle_anchor_seed','terminal_restore','post_restore_readback','emergency_restore')) { $phaseNames.Add($name) }
$phaseUnique = @($phaseNames | Sort-Object -Unique -CaseSensitive)
$plannedMaximum = 1 + ($scope.controls.Count * 3) + 3
$receiptPaths = [Collections.Generic.List[string]]::new()
foreach ($name in $phaseNames) { $receiptPaths.Add(('phase_' + $name + '.cfg')) }
for ($i=1; $i -le $plannedMaximum; $i++) { $receiptPaths.Add(('frames\bb_{0:D6}.bmp' -f $i)) }
foreach ($name in @('frames\frames.csv','CAPTURE_AUDIT.json','driver-result.json','PHASE_DONE_REQUEST.json','PRIVATE_FIXTURE_LOAD_GATE.json','NATURAL_BASELINE.json','DRIVER_READY.json','PRIVATE_PROFILE_BINDING.json','driver.log','driver.console.log','driver.stderr.log','flow-terminal.json','flow\terminal-status.json')) { $receiptPaths.Add($name) }
$receiptPathSet = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($path in $receiptPaths) { [void]$receiptPathSet.Add($path) }
$budgetPass = $scope.raw_frame_budget.max_frames -eq 90 -and
    $scope.raw_frame_budget.maximum_planned -eq $plannedMaximum -and
    $plannedMaximum -le $scope.raw_frame_budget.max_frames -and
    $scope.raw_frame_budget.width -eq 1280 -and $scope.raw_frame_budget.height -eq 720 -and
    $scope.raw_frame_budget.max_bytes_each -eq 3686454 -and
    $scope.capture_contract.includes_terminal_in_budget -eq $true
Add-Check 'unique_phase_namespace' ($phaseUnique.Count -eq $phaseNames.Count) ('Family/alias/state receipt names are unique; count=' + $phaseNames.Count)
Add-Check 'complete_command_frame_receipt_namespace' ($receiptPathSet.Count -eq $receiptPaths.Count) ('All planned phase command files, numbered frame files and fixed run receipts are path-unique; count=' + $receiptPaths.Count)
Add-Check 'bounded_frame_plan' $budgetPass ('1 natural + 1 optional SC02 seed + 28*3 target phases + terminal + post-restore = ' + $plannedMaximum + ' maximum; cap 90; 1280x720; 3686454 bytes each.')

$caseText = Get-Content -Raw -LiteralPath $casePath
$runPolicyPass = $caseText.Contains('AllowConcurrentGames = $false') -and
    $caseText -notmatch 'MaxConcurrentOtherGames' -and
    $caseText.Contains("ThrottleScript = '0:accel,6:brake+handbrake,10:none'") -and
    $caseText -notmatch '(?i)ThrottleScript\s*=\s*[^\r\n]*jump'
Add-Check 'concurrency_policy' $runPolicyPass 'The private strict run disables the unsupported concurrency opt-in, supplies no invalid zero limit, and injects no jump action.'

$siteStatusProblems=@($scope.controls|Where-Object{$_.status -cne 'pending' -or $_.site_credit -ne 0 -or $_.behavior_credit -ne 0})
Add-Check 'zero_site_credit' ($siteStatusProblems.Count -eq 0) 'All 28 targets remain pending with zero site and behavior credit.'
$e14=$scope.controls|Where-Object alias -eq 'E14'
$runtimeGateText=Get-Content -Raw -LiteralPath (Join-Path $package 'RUNTIME_GATES.md')
$e14Pass=($null -ne $e14.known_source_blocker -and $e14.known_source_blocker.kind -eq 'known_pc_trap_source_defect' -and
    $e14.status -ceq 'pending' -and $e14.behavior_credit -eq 0 -and
    $runtimeGateText.Contains('BehaviourCollection::Prepare') -and $runtimeGateText.Contains('CGS_ASSERT(lbPrepared)'))
Add-Check 'e14_known_source_blocker' $e14Pass 'E14 remains a pending field target with an explicit published-source PC trap/assert blocker, not a no-op disposition.'

$fixturePath = [string]$pins.profile_snapshot.path
$fixturePresent = Test-Path -LiteralPath $fixturePath -PathType Leaf
$fixtureHash = if ($fixturePresent) { (Get-FileHash -LiteralPath $fixturePath -Algorithm SHA256).Hash.ToLowerInvariant() } else { '' }
$fixturePass = $fixturePresent -and $fixtureHash -ceq [string]$pins.profile_snapshot.sha256 -and
    $fixtureHash -ceq [string]$stageTemplate.profile_fixture_sha256 -and
    $fixtureHash -ceq [string]$expectedProgress.source_sha256 -and
    [IO.Path]::GetFullPath($fixturePath) -notlike (([IO.Path]::GetFullPath($package)).TrimEnd('\') + '\*')
Add-Check 'private_fixture_pin' $fixturePass ('External read-only profile snapshot SHA-256=' + $fixtureHash)
Add-Check 'no_live_log_binding' ($expectedProgress.runtime_reference.live_log_immutability_required -eq $false -and $expectedProgress.runtime_reference.use -eq 'archived_read_only_progress_reference') 'The expected progress gate compares the private fixture run only; the archived normal log hash is not a live-run invariant.'

$helperChecks = [Collections.Generic.List[string]]::new()
foreach ($helperName in @('run_case','flow_run')) {
    $helper = $pins.runner_binding.workflow_helpers.$helperName
    if (-not (Test-Path -LiteralPath $helper.path -PathType Leaf)) { $helperChecks.Add($helperName + ' missing'); continue }
    $actual = (Get-FileHash -LiteralPath $helper.path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -cne [string]$helper.sha256) { $helperChecks.Add($helperName + ' hash mismatch') }
}
foreach ($dep in $pins.runner_binding.supporting_dependencies) {
    if (-not (Test-Path -LiteralPath $dep.path -PathType Leaf)) { $helperChecks.Add(([string]$dep.role + ' missing')); continue }
    $actual = (Get-FileHash -LiteralPath $dep.path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -cne [string]$dep.sha256) { $helperChecks.Add(([string]$dep.role + ' hash mismatch')) }
}
$flowText = Get-Content -Raw -LiteralPath $pins.runner_binding.workflow_helpers.flow_run.path
$eventEvidence = $flowText.Contains("Local\BurnoutPC_HarnessPhaseDone_{0}_{1}_{2}") -and
    $flowText.Contains('$phaseStopEvent=[Threading.EventWaitHandle]::new') -and
    $flowText.Contains('$phaseStopEvent.WaitOne(0)') -and
    $flowText.Contains('PHASE_COLLECTION_STOP')
if (-not $eventEvidence) { $helperChecks.Add('phase event producer/poller contract missing') }
Add-Check 'pinned_event_capable_runner' ($helperChecks.Count -eq 0) $(if ($helperChecks.Count) { $helperChecks -join '; ' } else { 'Exact private run_case/flow_run hashes and supporting dot-sourced helpers match; flow_run creates, polls and validates the PID/slot/start-time event.' })

$localFiles = @(Get-ChildItem -LiteralPath $package -File)
$nonText = @($localFiles | Where-Object Extension -notin @('.ps1','.json','.md','.sha256'))
Add-Check 'text_only_package' ($nonText.Count -eq 0) $(if ($nonText.Count) { $nonText.Name -join ', ' } else { 'No binaries, profile files, or asset files were copied into the v2 package.' })

$manifestPath = Join-Path $package 'ALL_FILE_HASHES.sha256'
$manifestProblems = [Collections.Generic.List[string]]::new()
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { $manifestProblems.Add('all-file SHA-256 manifest missing') }
else {
    $manifestRows = @{}
    foreach ($line in Get-Content -LiteralPath $manifestPath) {
        if ($line -notmatch '^([0-9a-f]{64})  (.+)$') { $manifestProblems.Add('malformed manifest line'); continue }
        $expectedHash=$Matches[1];$name=$Matches[2]
        if ($manifestRows.ContainsKey($name)) { $manifestProblems.Add('duplicate manifest path: ' + $name); continue }
        $manifestRows[$name]=$expectedHash
        $filePath=Join-Path $package $name
        if (-not (Test-Path -LiteralPath $filePath -PathType Leaf)) { $manifestProblems.Add('manifest file missing: ' + $name); continue }
        $actual=(Get-FileHash -LiteralPath $filePath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -cne $expectedHash) { $manifestProblems.Add('manifest hash mismatch: ' + $name) }
    }
    $expectedManifestNames=@(Get-ChildItem -LiteralPath $package -File|Where-Object { $_.Name -notin (@('ALL_FILE_HASHES.sha256')+$runtimeMetadataFiles) }|ForEach-Object Name|Sort-Object)
    $listedManifestNames=@($manifestRows.Keys|Sort-Object)
    if (($expectedManifestNames -join "`n") -cne ($listedManifestNames -join "`n")) { $manifestProblems.Add('manifest does not cover every package file except itself') }
}
Add-Check 'all_file_hash_manifest' ($manifestProblems.Count -eq 0) $(if ($manifestProblems.Count) { $manifestProblems -join '; ' } else { 'The SHA-256 manifest covers every v2 package file except itself and every listed hash matches.' })

if ($AtRun) {
    $runProblems = [Collections.Generic.List[string]]::new()
    if ([string]::IsNullOrWhiteSpace($RunDir)) { $runProblems.Add('RunDir missing') }
    if ([string]::IsNullOrWhiteSpace($StagePath) -or -not (Test-Path -LiteralPath $StagePath -PathType Leaf)) { $runProblems.Add('STAGING.json missing') }
    if ($RunDir -and (Test-Path -LiteralPath $RunDir -PathType Container)) {
        foreach ($name in $receiptPaths) { if (Test-Path -LiteralPath (Join-Path $RunDir $name)) { $runProblems.Add('receipt exists: ' + $name) } }
        if (@(Get-ChildItem -LiteralPath $RunDir -Recurse -File -Filter 'PHASE_DONE_REQUEST.json.pending.*').Count -gt 0) { $runProblems.Add('pending phase-stop receipt exists') }
    }
    if ($StagePath -and (Test-Path -LiteralPath $StagePath -PathType Leaf)) {
        try {
            $stage = Get-Content -Raw -LiteralPath $StagePath | ConvertFrom-Json
            [void](Assert-BrnSceneStageBoundary $stage (Join-Path $package 'stage') $fixturePath $fixtureHash)
            if ($stage.slot -ne 62190 -or $stage.exe_sha256 -cne [string]$scope.candidate.exe_sha256) { $runProblems.Add('stage slot/exe pin mismatch') }
            $exeDir = [IO.Path]::GetFullPath([string]$stage.exe_dir)
            $dataDir = [IO.Path]::GetFullPath([string]$stage.cwd)
            if ((Split-Path -Leaf $exeDir) -ine 'slot' -or (Split-Path -Leaf $dataDir) -ine 'data' -or
                [IO.Path]::GetFullPath((Split-Path -Parent $exeDir)) -ine [IO.Path]::GetFullPath((Split-Path -Parent $dataDir))) {
                $runProblems.Add('stage slot/data are not private siblings')
            }
            $expectedPrivateProfile = [IO.Path]::GetFullPath((Join-Path $dataDir 'Memcard_62190\Profile.sav'))
            $actualPrivateProfile = [IO.Path]::GetFullPath([string]$stage.profile)
            if ($actualPrivateProfile -ine $expectedPrivateProfile -or $actualPrivateProfile -ieq [IO.Path]::GetFullPath($fixturePath)) {
                $runProblems.Add('profile path is not the private slot 62190 stage profile')
            }
            if ([IO.Path]::GetFullPath([string]$stage.profile_fixture) -ine [IO.Path]::GetFullPath($fixturePath) -or
                [string]$stage.profile_fixture_sha256 -cne $fixtureHash) { $runProblems.Add('stage fixture snapshot pin mismatch') }
            if ($RunDir -and (Test-Path -LiteralPath $RunDir -PathType Container)) {
                if (-not (Test-Path -LiteralPath $stage.profile -PathType Leaf)) { $runProblems.Add('private stage fixture profile missing before game launch') }
                else {
                    $actualProfileHash=(Get-FileHash -LiteralPath $stage.profile -Algorithm SHA256).Hash.ToLowerInvariant()
                    if ($actualProfileHash -cne $fixtureHash) { $runProblems.Add('private stage profile is not the pinned fixture before game launch') }
                }
            }
            if (Test-Path -LiteralPath (Join-Path $stage.exe_dir 'Burnout_PC.exe') -PathType Leaf) {
                $actualExe = (Get-FileHash -LiteralPath (Join-Path $stage.exe_dir 'Burnout_PC.exe') -Algorithm SHA256).Hash.ToLowerInvariant()
                if ($actualExe -cne [string]$scope.candidate.exe_sha256) { $runProblems.Add('stage executable hash mismatch') }
            } else { $runProblems.Add('private staged executable missing') }
            if (Test-Path -LiteralPath (Join-Path $stage.exe_dir 'Burnout_PC.map') -PathType Leaf) {
                $actualMap = (Get-FileHash -LiteralPath (Join-Path $stage.exe_dir 'Burnout_PC.map') -Algorithm SHA256).Hash.ToLowerInvariant()
                if ($actualMap -cne [string]$scope.candidate.map_sha256) { $runProblems.Add('stage map hash mismatch') }
            } else { $runProblems.Add('private staged linker map missing') }
        } catch { $runProblems.Add('stage parse/check failed: ' + $_.Exception.Message) }
    }
    Add-Check 'prelaunch_receipt_stage_gate' ($runProblems.Count -eq 0) $(if ($runProblems.Count) { $runProblems -join '; ' } else { 'Stage pins, private paths and the complete receipt namespace are clear before native setters.' })
} else {
    Add-Check 'no_actual_staging' (-not (Test-Path -LiteralPath (Join-Path $package 'STAGING.json'))) 'Only STAGING.TEMPLATE.json exists; this prep created no actual stage manifest.'
}

[pscustomobject]@{
    schema=1
    pass=($problems.Count -eq 0)
    mode=$(if ($AtRun) { 'prelaunch_read_only' } else { 'preparation_read_only' })
    checks=@($checks.ToArray())
    problems=@($problems.ToArray())
    site_credit=0
    native_run_performed=$false
    files_inspected=$localFiles.Count
}
