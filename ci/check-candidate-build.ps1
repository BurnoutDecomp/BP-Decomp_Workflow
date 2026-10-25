<#
Build/check an exact b5 commit on the hosted Windows runner, using the shipping
bat/compile_exe path. No assets, gameplay, publishing, releases or server calls.
The parent gitlink override is intentional, recorded and never committed.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $B5Commit,
    [Parameter(Mandatory)] [string] $WorkflowSha,
    [ValidateRange(1, 8)] [int] $Jobs = 4,
    [switch] $RunRegressions,
    [switch] $RunAptLifetime,
    [switch] $RunHudRegressions,
    [switch] $RunResourceRegressions,
    [switch] $RunGuiIORegressions,
    [switch] $RunGuiAnimationRegressions,
    [switch] $RunStartupIORegressions,
    [switch] $RunGuiLicenseRegressions,
    [switch] $RunKeyboardUIContract,
    [switch] $RunRwacCommandCapacity,
    [switch] $RunSystemUserProfile,
    [switch] $RunTrafficFlowtypeOverride,
    [switch] $RunOnlineSaveRoute,
    [switch] $RunGuiMenuMusicWire
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_OS -ne 'Windows' -or
    $env:CANDIDATE_RUNNER_ENVIRONMENT -ne 'github-hosted') {
    throw 'Candidate builds run only on the GitHub-hosted Windows runner.'
}

$Root = Split-Path -Parent $PSScriptRoot
$SourceRoot = Join-Path $Root 'b5-decomp'
$WorkRoot = Join-Path $Root 'build/candidate'
$ArtifactRoot = Join-Path $WorkRoot 'artifacts'
$GameOut = Join-Path $Root 'build/game'
New-Item -ItemType Directory -Force -Path $ArtifactRoot | Out-Null
$NativeCommands = [System.Collections.Generic.List[object]]::new()
$RuntimeOutputs = @{}
$ExitCode = 1
$NativeFailureCode = 0
$Receipt = [ordered]@{
    requested_b5_commit = $B5Commit; workflow_sha = $WorkflowSha
    workflow_ref = $env:CANDIDATE_WORKFLOW_REF; runner_label = 'windows-2022'
    runner_name = $env:RUNNER_NAME; image_os = $env:ImageOS; image_version = $env:ImageVersion
    run_id = $env:GITHUB_RUN_ID; run_attempt = $env:GITHUB_RUN_ATTEMPT
    started_utc = [DateTime]::UtcNow.ToString('o'); jobs = $Jobs; validated = $false
    attribution = 'Detached b5 candidate overrides the parent gitlink when different; no commit is made.'
    regressions = @{ requested = [bool]($RunRegressions -or $RunAptLifetime -or $RunHudRegressions -or $RunResourceRegressions -or $RunGuiIORegressions -or $RunGuiAnimationRegressions -or $RunStartupIORegressions -or $RunGuiLicenseRegressions -or $RunKeyboardUIContract -or $RunRwacCommandCapacity -or $RunSystemUserProfile -or $RunTrafficFlowtypeOverride -or $RunOnlineSaveRoute -or $RunGuiMenuMusicWire); status = 'not_requested'; inputs = @{}; negative_controls = @{}; gui_license_status = 'not_requested'; keyboard_ui_contract_status = 'not_requested'; keyboard_ui_contract = @{}; rwac_command_capacity_status = $(if ($RunRwacCommandCapacity) { 'running' } else { 'not_requested' }); rwac_command_capacity = @{}; system_user_profile_status = $(if ($RunSystemUserProfile) { 'running' } else { 'not_requested' }); system_user_profile = @{}; traffic_flowtype_override_status = $(if ($RunTrafficFlowtypeOverride) { 'running' } else { 'not_requested' }); traffic_flowtype_override = @{}; online_save_route_status = $(if ($RunOnlineSaveRoute) { 'running' } else { 'not_requested' }); online_save_route = @{}; gui_menu_music_wire_status = $(if ($RunGuiMenuMusicWire) { 'running' } else { 'not_requested' }); gui_menu_music_wire = @{}; startup_io_status = 'not_requested'; gui_animation_status = 'not_requested'; gui_io_status = 'not_requested'; hud_status = 'not_requested'; remaining_status = 'not_requested' }
}
$OutputNames = @('Burnout_PC.exe', 'Burnout_PC.map', 'Burnout_PC.cgsmap', 'Burnout_PC.exe.provenance.json')
$SystemUserProfileSourceBase = 'bef9346f9dc61f2ae1770bf3c9dbdc89fe4f15a7'
$SystemUserProfilePinsLfSha256 = '8bc2257f30e89eafcb7f1e6801d1a943885914e9a9112f95705a6ea9e6a58202'
$SystemUserProfilePlanLfSha256 = 'b922bc45991763901be63194b7824ae1aae83d309f10dce457988c1a82833686'
$SystemUserProfileRunnerLfSha256 = '2eee426e6e0f540311c15943b77c4f5a5dc4b3defc8d57e6b32e66aa606716a3'
# Exact delta03 diagnostic-support payload content; checkout line endings may differ.
$OnlineSaveRoutePayloadPins = @{
    'tests/OnlineSaveRoute.cpp' = @{ lf_sha256 = '9105e7eeec51378a21136e80409b502ca0d383c80c267a4520384f879577d728'; lf_bytes = 22917 }
    'tests/run_online_save_route.py' = @{ lf_sha256 = '053ae3b9fa21178b1b81fe1b864c991dcdd058fc1d43488fe92e25e44890ac9b'; lf_bytes = 11772 }
    'tests/online_save_route_binding.py' = @{ lf_sha256 = '4b44e0c8f7c7705f11616b59c95d730ae9660d27486f234ebd1bf9097cc446dc'; lf_bytes = 7456 }
    'tests/online_save_route_owned.py' = @{ lf_sha256 = 'c21a018a37c094eec2c6befcd19b8862f8c33c84b66f84c33c55eac600649179'; lf_bytes = 12783 }
    'tests/evidence/online_save_route/source_pins.json' = @{ lf_sha256 = '455eec70f7b026ac7545eeeef2b942bda479ce0afd0b2e0ff6ce8d2d1bda6cb1'; lf_bytes = 5017 }
    'tests/evidence/online_save_route/test_plan.json' = @{ lf_sha256 = '1709fa6b36657f903668e72943956566eb1d7ce3e24797fbbda5d270b308bc8e'; lf_bytes = 4435 }
    'tests/evidence/online_save_route/BrnGuiOptionsDataProfile_8b2940d4.cpp' = @{ lf_sha256 = 'e36d09bce219ca3125a204bcb34fe95aab2e7784c37d2f247a6eef980124c74d'; lf_bytes = 26153 }
    'tests/OnlineSaveRouteDiagnosticGlobals.cpp' = @{ lf_sha256 = 'ba311bf5c9397d9b61ad795458351a9ba400e88a2257ce6d8202ba9334960710'; lf_bytes = 453 }
}

function Invoke-Native([string] $Command, [string[]] $Arguments, [string] $LogName) {
    & $Command @Arguments 2>&1 | Tee-Object -FilePath (Join-Path $ArtifactRoot $LogName) -Append | Out-Host
    $code = $LASTEXITCODE
    $script:NativeCommands.Add(@{ command = $Command; arguments = $Arguments; exit_code = $code })
    if ($code -ne 0) {
        $script:NativeFailureCode = $code
        throw "$Command failed with native exit code $code; see $LogName"
    }
}
function Get-GitText([string[]] $GitArguments) {
    $lines = & git @GitArguments 2>&1
    $code = $LASTEXITCODE
    $script:NativeCommands.Add(@{ command = 'git'; arguments = $GitArguments; exit_code = $code })
    if ($code -ne 0) {
        $script:NativeFailureCode = $code
        throw "git failed with native exit code ${code}: $($lines -join ' ')"
    }
    return ($lines -join "`n").TrimEnd()
}
function Assert-CleanTrees {
    if ((Get-GitText @('-C', $Root, 'rev-parse', 'HEAD')) -ne $WorkflowSha) { throw 'Workflow checkout changed.' }
    $sourceStatus = Get-GitText @('-C', $SourceRoot, 'status', '--porcelain=v1', '--untracked-files=all', '--ignore-submodules=none')
    if ($sourceStatus) { throw "Candidate source/dependencies changed: $sourceStatus" }
    if ((Get-GitText @('-C', $SourceRoot, 'rev-parse', 'HEAD')) -ne $B5Commit -or
        (Get-GitText @('-C', $SourceRoot, 'rev-parse', '--abbrev-ref', 'HEAD')) -ne 'HEAD') {
        throw 'Candidate must remain at the requested detached commit.'
    }
    $parentStatus = Get-GitText @('-C', $Root, 'status', '--porcelain=v1', '--untracked-files=all', '--ignore-submodules=none')
    $expectedStatus = if ($Receipt.gitlink_overridden) { ' M b5-decomp' } else { '' }
    if ($parentStatus -cne $expectedStatus) { throw "Unexpected parent changes: $parentStatus" }
    $Receipt.source_status = $sourceStatus
    $Receipt.parent_status = $parentStatus
}
function Get-FileRecord([string] $Path) {
    return @{ bytes = (Get-Item -LiteralPath $Path).Length; sha256 = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
}
function Get-LFFileRecord([string] $Path) {
    $raw = [IO.File]::ReadAllBytes($Path)
    $lf = [Text.Encoding]::UTF8.GetBytes([Text.Encoding]::UTF8.GetString($raw).Replace("`r`n", "`n"))
    return @{
        path = [IO.Path]::GetFullPath($Path); raw_bytes = $raw.Length
        raw_sha256 = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($raw)).ToLowerInvariant()
        lf_bytes = $lf.Length
        lf_sha256 = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($lf)).ToLowerInvariant()
    }
}
function Assert-SystemUserProfilePath([string] $Observed, [string] $Expected, [string] $Label) {
    $observedFull = [IO.Path]::GetFullPath($Observed)
    $expectedFull = [IO.Path]::GetFullPath($Expected)
    if (-not [string]::Equals($observedFull, $expectedFull, [StringComparison]::OrdinalIgnoreCase)) {
        throw "System-user-profile $Label path mismatch: $observedFull"
    }
}
function Assert-SystemUserProfileRunRecord(
    [System.Collections.IDictionary] $RunRecord,
    [string] $ExpectedLog,
    [int] $TimeoutSeconds,
    [int] $ExpectedExitCode
) {
    if ($RunRecord.exit_code -ne $ExpectedExitCode -or $RunRecord.timed_out -ne $false -or
        $RunRecord.timeout_seconds -ne $TimeoutSeconds -or $RunRecord.owned_job -ne $true -or
        $RunRecord.transcript_hash_after_cleanup -ne $true) {
        throw 'System-user-profile compile/run exit, timeout, job or transcript state is invalid.'
    }
    Assert-SystemUserProfilePath ([string]$RunRecord.log) $ExpectedLog 'log'
    $cleanup = $RunRecord.cleanup
    if ($cleanup.complete -ne $true -or $cleanup.job_handle_closed -ne $true -or
        $cleanup.process_handles_closed -ne $true -or $cleanup.stdio_handles_closed -ne $true -or
        $cleanup.child_wait_complete -ne $true -or $cleanup.job_active_processes_after_cleanup -ne 0) {
        throw 'System-user-profile owned child cleanup was incomplete; log hash is not accepted.'
    }
    if (-not (Test-Path -LiteralPath $ExpectedLog -PathType Leaf)) { throw "System-user-profile log is missing: $ExpectedLog" }
    $actualLog = Get-FileRecord $ExpectedLog
    if ($RunRecord.log_raw_sha256 -cnotmatch '\A[0-9a-f]{64}\z' -or
        $RunRecord.log_sha256 -cne $RunRecord.log_raw_sha256.ToLowerInvariant() -or
        $RunRecord.log_bytes -ne $actualLog.bytes -or $RunRecord.log_raw_sha256 -cne $actualLog.sha256) {
        throw 'System-user-profile log hash/size changed after owned-child cleanup.'
    }
    $logText = [IO.File]::ReadAllText($ExpectedLog)
    return $logText.Replace("`r`n", "`n").Replace("`r", "`n")
}
function Assert-SystemUserProfileMode(
    [System.Collections.IDictionary] $ModeRecord,
    [string] $Variant,
    [string] $ModeName,
    [string] $OutputRoot,
    [int] $TimeoutSeconds,
    [int] $ExitCode,
    [int] $Checks,
    [int] $Failures,
    [int] $Assertions,
    [string[]] $ExpectedCheckIds,
    [string[]] $ExpectedFailureIds = @(),
    [string] $AssertSubstring = ''
) {
    $expectedStatus = if ($Failures) { 'expected_failure_observed' } else { 'pass' }
    if ($ModeRecord.status -cne $expectedStatus -or $ModeRecord.expected.checks -ne $Checks -or
        $ModeRecord.expected.failures -ne $Failures -or $ModeRecord.expected.assertions -ne $Assertions) {
        throw "System-user-profile $Variant/$ModeName result classification differs from its contract."
    }
    $logPath = Join-Path (Join-Path $OutputRoot $Variant) ($ModeName + '.log')
    $log = Assert-SystemUserProfileRunRecord $ModeRecord.run $logPath $TimeoutSeconds $ExitCode
    $summaries = [regex]::Matches($log, '(?m)^SYSTEM_USER_PROFILE checks=(\d+) failures=(\d+) assertions=(\d+)$')
    if ($summaries.Count -ne 1 -or [int]$summaries[0].Groups[1].Value -ne $Checks -or
        [int]$summaries[0].Groups[2].Value -ne $Failures -or [int]$summaries[0].Groups[3].Value -ne $Assertions) {
        throw "System-user-profile $Variant/$ModeName numeric summary is not the expected actual execution."
    }
    $checkRows = [regex]::Matches($log, '(?m)^CHECK (\S+) (PASS|FAIL)$')
    $observedIds = [string[]]@($checkRows | ForEach-Object { $_.Groups[1].Value })
    $failureIds = [string[]]@($checkRows | Where-Object { $_.Groups[2].Value -eq 'FAIL' } | ForEach-Object { $_.Groups[1].Value })
    if ([string]::Join("`n", $observedIds) -cne [string]::Join("`n", $ExpectedCheckIds) -or
        [string]::Join("`n", [string[]]@($ModeRecord.observed_check_ids)) -cne [string]::Join("`n", $observedIds) -or
        [string]::Join("`n", $failureIds) -cne [string]::Join("`n", $ExpectedFailureIds) -or
        [string]::Join("`n", [string[]]@($ModeRecord.observed_failure_ids)) -cne [string]::Join("`n", $failureIds)) {
        throw "System-user-profile $Variant/$ModeName check order or failure identities differ."
    }
    $assertLines = [regex]::Matches($log, '(?m)^LEGACY_ASSERT (.*)$')
    if ($assertLines.Count -ne $Assertions -or ($AssertSubstring -and
        ($assertLines.Count -ne 1 -or -not $assertLines[0].Groups[1].Value.Contains($AssertSubstring)))) {
        throw "System-user-profile $Variant/$ModeName assertion witness differs."
    }
    return @{
        status = $ModeRecord.status; checks = $Checks; failures = $Failures; assertions = $Assertions
        observed_check_ids = $observedIds; observed_failure_ids = $failureIds
        exit_code = $ModeRecord.run.exit_code; timed_out = $ModeRecord.run.timed_out
        log_raw_sha256 = $ModeRecord.run.log_raw_sha256; log_bytes = $ModeRecord.run.log_bytes
        transcript_hash_after_cleanup = $ModeRecord.run.transcript_hash_after_cleanup
    }
}
function Assert-SystemUserProfileReceipt(
    [System.Collections.IDictionary] $ProfileResult,
    [string] $OutputRoot,
    [string] $SourceRoot,
    [string] $WorkflowRoot
) {
    if ($ProfileResult.schema_version -ne 1 -or $ProfileResult.fixture -cne 'SYSTEM_USER_PROFILE' -or
        $ProfileResult.executed -ne $true -or $ProfileResult.success -ne $true -or $ProfileResult.status -cne 'pass') {
        throw 'System-user-profile receipt is not an executed passing fixture result.'
    }
    Assert-SystemUserProfilePath $ProfileResult.b5_root $SourceRoot 'B5 root'
    Assert-SystemUserProfilePath $ProfileResult.workflow_root $WorkflowRoot 'workflow root'
    Assert-SystemUserProfilePath $ProfileResult.artifact_root $OutputRoot 'artifact root'
    $source = $ProfileResult.sources
    if ($source.base_head -cne $SystemUserProfileSourceBase -or @($source.mismatches).Count -ne 0) {
        throw 'System-user-profile source receipt has the wrong pinned base or source mismatches.'
    }
    $pinPath = Join-Path $SourceRoot 'tests/evidence/system_user_profile_pc/source_pins.json'
    $pinRaw = Get-FileRecord $pinPath
    $pinIdentity = $source.pins_file
    if ($pinIdentity.actual_raw_sha256 -cne $pinRaw.sha256 -or $pinIdentity.actual_raw_bytes -ne $pinRaw.bytes -or
        $pinIdentity.actual_lf_sha256 -cne $SystemUserProfilePinsLfSha256 -or $pinIdentity.actual_lf_bytes -ne 4543) {
        throw 'System-user-profile receipt is not bound to the updated delta04 source pins and raw checkout bytes.'
    }
    $pins = Get-Content -Raw -LiteralPath $pinPath | ConvertFrom-Json -AsHashtable
    if ($pins.schema_version -ne 2 -or $pins.normalization -cne 'crlf_to_lf_only' -or
        $pins.base_head -cne $SystemUserProfileSourceBase -or @($pins.files.Keys).Count -ne 20) {
        throw 'System-user-profile source-pin contract differs from the approved fixture packet.'
    }
    $pinKeys = [string[]]@($pins.files.Keys | Sort-Object)
    $receiptKeys = [string[]]@($source.files.Keys | Sort-Object)
    if ([string]::Join("`n", $pinKeys) -cne [string]::Join("`n", $receiptKeys)) {
        throw 'System-user-profile source receipt does not cover the exact pinned file set.'
    }
    foreach ($relative in $pinKeys) {
        $expected = $pins.files[$relative]
        $row = $source.files[$relative]
        $path = Join-Path $SourceRoot $relative.Replace('/', [IO.Path]::DirectorySeparatorChar)
        $raw = Get-FileRecord $path
        if ($row.matches_lf_content -ne $true -or $row.expected_lf_sha256 -cne $expected.expected_lf_sha256 -or
            $row.expected_lf_bytes -ne $expected.expected_lf_bytes -or $row.actual_lf_sha256 -cne $expected.expected_lf_sha256 -or
            $row.actual_lf_bytes -ne $expected.expected_lf_bytes -or $row.actual_raw_sha256 -cne $raw.sha256 -or
            $row.actual_raw_bytes -ne $raw.bytes -or $row.actual_raw_sha256 -cnotmatch '\A[0-9a-f]{64}\z') {
            throw "System-user-profile source pin/raw identity mismatch: $relative"
        }
    }
    if ($pins.files['tests/run_system_user_profile_pc.py'].expected_lf_sha256 -cne $SystemUserProfileRunnerLfSha256 -or
        $pins.files['tests/run_system_user_profile_pc.py'].expected_lf_bytes -ne 29458 -or
        $pins.files['tests/evidence/system_user_profile_pc/test_plan.json'].expected_lf_sha256 -cne $SystemUserProfilePlanLfSha256 -or
        $pins.files['tests/evidence/system_user_profile_pc/test_plan.json'].expected_lf_bytes -ne 3468) {
        throw 'System-user-profile runner or ordered test-plan pin differs from the reviewed packet.'
    }
    $expectedBaselines = @{
        'tests/evidence/system_user_profile_pc/CgsGuideIntegration_bef9346f9.cpp' = 'dbf6f7a8a47889c3358f30787676ad994e2f9494'
        'tests/evidence/system_user_profile_pc/CgsXboxLivePC_bef9346f9.cpp' = '46218b2dc5ca92b78668faf71b0318996dbaa3e0'
    }
    if (@($source.baseline_evidence).Count -ne 2 -or
        [string]::Join('|', [string[]]@($source.baseline_evidence.path | Sort-Object)) -cne [string]::Join('|', [string[]]@($expectedBaselines.Keys | Sort-Object))) {
        throw 'System-user-profile original API/consumer baseline path set changed.'
    }
    foreach ($baseline in $source.baseline_evidence) {
        if ($baseline.matches_original_git_lf_blob -ne $true -or
            $baseline.original_git_lf_blob_sha1 -cne $expectedBaselines[[string]$baseline.path] -or
            $baseline.actual_checkout_lf_git_blob_sha1 -cne $expectedBaselines[[string]$baseline.path]) {
            throw "System-user-profile baseline source identity mismatch: $($baseline.path)"
        }
    }
    foreach ($relative in @('tools/build/msvc_flags.txt','tools/build/msvc_includes.txt','tools/build/msvc_env.bat')) {
        $tool = $source.canonical_tool_files[$relative]
        $raw = Get-FileRecord (Join-Path $WorkflowRoot $relative)
        if ($tool.actual_raw_sha256 -cne $raw.sha256 -or $tool.actual_raw_bytes -ne $raw.bytes) {
            throw "System-user-profile workflow tool path/raw identity mismatch: $relative"
        }
    }
    $planPath = Join-Path $SourceRoot 'tests/evidence/system_user_profile_pc/test_plan.json'
    $plan = Get-Content -Raw -LiteralPath $planPath | ConvertFrom-Json -AsHashtable
    $expectedIds = [string[]]@($plan.candidate_check_ids)
    $resultIds = [string[]]@($ProfileResult.test_plan.candidate_check_ids)
    if ($plan.expected_candidate_checks -ne 82 -or $plan.expected_candidate_failures -ne 0 -or
        $expectedIds.Count -ne 82 -or @($expectedIds | Select-Object -Unique).Count -ne 82 -or
        [string]::Join("`n", $expectedIds) -cne [string]::Join("`n", $resultIds) -or
        $ProfileResult.test_plan.expected_candidate_checks -ne 82 -or $ProfileResult.test_plan.expected_candidate_failures -ne 0 -or
        $plan.baseline_api.checks -ne 9 -or $plan.baseline_api.failures -ne 1 -or $plan.baseline_api.assertions -ne 0 -or
        $plan.baseline_api.failure_id -cne 'default_actual_api_success' -or
        $plan.baseline_consumer.checks -ne 3 -or $plan.baseline_consumer.failures -ne 1 -or
        $plan.baseline_consumer.assertions -ne 1 -or
        $plan.baseline_consumer.failure_id -cne 'legacy_consumer_selected_user_settings_callback' -or
        $plan.baseline_consumer.assert_substring -cne 'problem reading user settings') {
        throw 'System-user-profile candidate/control test-plan numeric or ordered-ID contract changed.'
    }
    if ($ProfileResult.test_plan.baseline_api.checks -ne 9 -or $ProfileResult.test_plan.baseline_api.failures -ne 1 -or
        $ProfileResult.test_plan.baseline_api.assertions -ne 0 -or $ProfileResult.test_plan.baseline_api.failure_id -cne 'default_actual_api_success' -or
        $ProfileResult.test_plan.baseline_consumer.checks -ne 3 -or $ProfileResult.test_plan.baseline_consumer.failures -ne 1 -or
        $ProfileResult.test_plan.baseline_consumer.assertions -ne 1 -or
        $ProfileResult.test_plan.baseline_consumer.failure_id -cne 'legacy_consumer_selected_user_settings_callback' -or
        $ProfileResult.test_plan.baseline_consumer.assert_substring -cne 'problem reading user settings') {
        throw 'System-user-profile result test plan differs from the exact pinned source plan.'
    }
    $variantKeys = [string[]]@($ProfileResult.variants.Keys | Sort-Object)
    if ([string]::Join('|', $variantKeys) -cne 'baseline|candidate') {
        throw 'System-user-profile receipt must contain exactly candidate and original baseline variants.'
    }
    $variantSummaries = @{}
    foreach ($variantName in @('candidate','baseline')) {
        $variant = $ProfileResult.variants[$variantName]
        if ($variant.status -cne 'pass') { throw "System-user-profile $variantName variant did not pass." }
        $variantRoot = Join-Path $OutputRoot $variantName
        $exePath = Join-Path $variantRoot 'regression.exe'
        if (-not (Test-Path -LiteralPath $exePath -PathType Leaf) -or
            $variant.executable_sha256 -cnotmatch '\A[0-9a-f]{64}\z' -or $variant.executable_bytes -le 0) {
            throw "System-user-profile $variantName executable/hash is missing."
        }
        $exe = Get-FileRecord $exePath
        if ($exe.sha256 -cne $variant.executable_sha256 -or $exe.bytes -ne $variant.executable_bytes) {
            throw "System-user-profile $variantName executable hash/size differs from the runner receipt."
        }
        if ($variantName -eq 'candidate') {
            $provider = 'src/GameShared/GameClasses/System/PC/CgsXboxLivePC.cpp'
            $consumer = 'src/GameShared/GameClasses/Gui/CgsGuideIntegration.cpp'
            $expectedModes = 'candidate'
        } else {
            $provider = 'tests/evidence/system_user_profile_pc/CgsXboxLivePC_bef9346f9.cpp'
            $consumer = 'tests/evidence/system_user_profile_pc/CgsGuideIntegration_bef9346f9.cpp'
            $expectedModes = 'baseline_api|baseline_consumer'
        }
        $wrapper = $variant.consumer_wrapper
        $expectedWrapperPrelude = (
            "#define WIN32_LEAN_AND_MEAN`n" +
            "#define NOMINMAX`n" +
            "#include <Windows.h>`n" +
            "#include <array>`n" +
            "#include <cstddef>`n" +
            "#include <cstdio>`n" +
            "#include <cstring>`n" +
            "#include <exception>`n" +
            "#include <fstream>`n" +
            "#include <stdexcept>`n" +
            "#include <string>`n" +
            "#include <vector>`n" +
            '#include "types.hpp"' + "`n" +
            '#include "GameShared/GameClasses/Core/CgsAssert.h"' + "`n`n" +
            "#define private public`n" +
            '#include "GameShared/GameClasses/Gui/CgsGuideIntegration.h"' + "`n" +
            "#undef private`n`n"
        )
        $expectedWrapperMarker = "// Generated test-only consumer wrapper; exact pinned consumer source is included below: $consumer`n"
        $consumerIncludePath = ([IO.Path]::GetFullPath((Join-Path $SourceRoot $consumer))).Replace('\', '/')
        $expectedConsumerInclude = '#include "' + $consumerIncludePath + '"'
        if ($wrapper.wrapper_relative_path -cne 'SystemUserProfilePC_consumer_wrapper.cpp' -or
            $wrapper.recipe -cne 'fixture-matched standard/Windows prelude + private-public owning header + exact consumer source include' -or
            $wrapper.prelude -cne $expectedWrapperPrelude -or
            $wrapper.marker -cne $expectedWrapperMarker -or
            $wrapper.include_directive -ine $expectedConsumerInclude) {
            throw "System-user-profile $variantName consumer-wrapper recipe/include differs from the pinned fixture contract."
        }
        $wrapperConsumer = $wrapper.consumer_source
        $pinnedConsumer = $source.files[$consumer]
        if ($wrapperConsumer.repository_path -cne $consumer -or $null -eq $pinnedConsumer -or
            $wrapperConsumer.actual_raw_sha256 -cne $pinnedConsumer.actual_raw_sha256 -or
            $wrapperConsumer.actual_raw_bytes -ne $pinnedConsumer.actual_raw_bytes -or
            $wrapperConsumer.actual_lf_sha256 -cne $pinnedConsumer.actual_lf_sha256 -or
            $wrapperConsumer.actual_lf_bytes -ne $pinnedConsumer.actual_lf_bytes) {
            throw "System-user-profile $variantName wrapper consumer identity differs from its pinned source."
        }
        $wrapperPath = Join-Path $variantRoot 'SystemUserProfilePC_consumer_wrapper.cpp'
        $expectedWrapperText = $expectedWrapperPrelude + $expectedWrapperMarker + [string]$wrapper.include_directive + "`n"
        $expectedWrapperBytes = [Text.Encoding]::UTF8.GetBytes($expectedWrapperText)
        $actualWrapperBytes = [IO.File]::ReadAllBytes($wrapperPath)
        if ([Convert]::ToBase64String($actualWrapperBytes) -cne [Convert]::ToBase64String($expectedWrapperBytes)) {
            throw "System-user-profile $variantName wrapper bytes do not match the validated prelude and exact consumer include."
        }
        $wrapperFile = Get-FileRecord $wrapperPath
        if ($wrapper.wrapper.actual_raw_sha256 -cne $wrapperFile.sha256 -or
            $wrapper.wrapper.actual_raw_bytes -ne $wrapperFile.bytes -or
            $wrapper.wrapper.actual_lf_sha256 -cne $wrapperFile.sha256 -or
            $wrapper.wrapper.actual_lf_bytes -ne $wrapperFile.bytes -or
            $wrapper.wrapper.actual_raw_crlf_pairs -ne 0 -or $wrapper.wrapper.actual_raw_bare_cr -ne 0 -or
            $wrapper.wrapper.actual_raw_eol_variant -cne 'lf') {
            throw "System-user-profile $variantName generated consumer wrapper hash/line endings differ from its receipt."
        }
        $expectedSources = @(
            (Join-Path $SourceRoot 'tests/SystemUserProfilePC.cpp'),
            (Join-Path $SourceRoot $provider),
            $wrapperPath,
            (Join-Path $SourceRoot 'src/GameShared/GameClasses/System/PC/CgsPcNetIdentity.cpp'),
            (Join-Path $SourceRoot 'src/GameShared/GameClasses/System/X360/CgsXOverlappedX360.cpp'),
            (Join-Path $variantRoot 'SPrintfProvider.cpp')
        ) | ForEach-Object { [IO.Path]::GetFullPath($_) }
        $recordedSources = [string[]]@($variant.source_paths | ForEach-Object { [IO.Path]::GetFullPath([string]$_) })
        if ([string]::Join("`n", [string[]]$expectedSources) -cne [string]::Join("`n", $recordedSources)) {
            throw "System-user-profile $variantName compiler source path/order differs from the approved runner."
        }
        $commandArguments = [string[]]@($variant.compile_command | ForEach-Object { [string]$_ })
        $firstSourceIndex = [Array]::IndexOf($commandArguments, [string]$expectedSources[0])
        $lastSourceIndex = $firstSourceIndex + $expectedSources.Count - 1
        if ($firstSourceIndex -lt 0 -or $lastSourceIndex -ge $commandArguments.Count) {
            throw "System-user-profile $variantName command receipt omits the expected compiler source sequence."
        }
        $commandSources = [string[]]@($commandArguments[$firstSourceIndex..$lastSourceIndex])
        $afterSourcesIndex = $lastSourceIndex + 1
        if ([string]::Join("`n", [string[]]$expectedSources) -cne [string]::Join("`n", $commandSources) -or
            $afterSourcesIndex -ge $commandArguments.Count -or $commandArguments[$afterSourcesIndex] -notmatch '\A/Fe:') {
            throw "System-user-profile $variantName compiler command source order/termination differs from its receipt."
        }
        $compileLog = Join-Path $variantRoot 'compile.log'
        $null = Assert-SystemUserProfileRunRecord $variant.compile $compileLog 120 0
        $modeKeys = [string[]]@($variant.modes.Keys | Sort-Object)
        if ([string]::Join('|', $modeKeys) -cne $expectedModes) {
            throw "System-user-profile $variantName run modes differ from the candidate/control contract."
        }
        $modeSummaries = @{}
        if ($variantName -eq 'candidate') {
            $modeSummaries['candidate'] = Assert-SystemUserProfileMode $variant.modes['candidate'] 'candidate' 'candidate' $OutputRoot 25 0 82 0 0 $expectedIds
        } else {
            $apiIds = [string[]]@($expectedIds | Select-Object -First 9)
            $consumerIds = [string[]]@('legacy_consumer_selected_user_settings_callback','legacy_consumer_preserves_signin_name_before_settings','legacy_consumer_actual_error87_assert')
            $modeSummaries['baseline_api'] = Assert-SystemUserProfileMode $variant.modes['baseline_api'] 'baseline' 'baseline_api' $OutputRoot 25 1 9 1 0 $apiIds @('default_actual_api_success')
            $modeSummaries['baseline_consumer'] = Assert-SystemUserProfileMode $variant.modes['baseline_consumer'] 'baseline' 'baseline_consumer' $OutputRoot 25 1 3 1 1 $consumerIds @('legacy_consumer_selected_user_settings_callback') 'problem reading user settings'
        }
        $variantSummaries[$variantName] = @{
            status = $variant.status; executable = @{ path = $exePath; bytes = $exe.bytes; sha256 = $exe.sha256 }
            compile = @{ exit_code = $variant.compile.exit_code; timed_out = $variant.compile.timed_out; log_raw_sha256 = $variant.compile.log_raw_sha256; log_bytes = $variant.compile.log_bytes }
            modes = $modeSummaries
        }
    }
    return $variantSummaries
}

# Validate the existing fxgs_common retained-output contract; never execute receipt commands.
function Assert-TrafficFlowtypeVariant([string] $VariantRoot, [string] $Revision, [bool] $Baseline) {
    $row = Get-Content -Raw -LiteralPath (Join-Path $VariantRoot 'result.json') | ConvertFrom-Json -AsHashtable
    $extraction = Get-Content -Raw -LiteralPath (Join-Path $VariantRoot 'extraction.json') | ConvertFrom-Json -AsHashtable
    $stdout = [IO.File]::ReadAllText((Join-Path $VariantRoot 'run.stdout.txt'))
    $summary = [regex]::Matches($stdout, '(?m)^TrafficFlowtypeOverride: (\d+) checks, (\d+) failures\r?$')
    $failures = [regex]::Matches($stdout, '(?m)^FAIL [^\r\n]+\r?$').Count
    $exit = if ($Baseline) { 1 } else { 0 }
    if ($row.tag -cne 'TrafficFlowtypeOverride' -or $row.process_exit_code -ne $exit -or
        $null -eq $row.numeric -or $row.numeric.checks -ne 44 -or $summary.Count -ne 1 -or
        [int]$summary[0].Groups[1].Value -ne 44 -or
        [int]$summary[0].Groups[2].Value -ne $row.numeric.failures -or
        $failures -ne $row.numeric.failures -or $failures -gt 44 -or
        ($Baseline -and $failures -lt 1) -or (-not $Baseline -and $failures -ne 0)) {
        throw 'Traffic flowtype variant did not execute exactly 44 checks with its expected exit/result.'
    }
    $exePath = Join-Path $VariantRoot 'regression.exe'
    $exe = Get-FileRecord $exePath
    if ($exe.bytes -le 0 -or $row.executable_sha256 -cne $exe.sha256) {
        throw 'Traffic flowtype retained executable hash differs from the process receipt.'
    }
    $expectedInputs = @(
        (Join-Path $SourceRoot 'tests/TrafficFlowtypeOverride.cpp'),
        (Join-Path $VariantRoot 'traffic_flowtype_override.inc'),
        (Join-Path $VariantRoot 'run.cmd'),
        (Join-Path $Root 'tools/build/msvc_flags.txt'),
        (Join-Path $Root 'tools/build/msvc_includes.txt'),
        (Join-Path $SourceRoot 'src/GameShared/GameClasses/System/Resource/CgsBaseResourcePtr.cpp'),
        (Join-Path $SourceRoot 'src/GameShared/GameClasses/System/Resource/CgsResourcePtr.cpp'),
        (Join-Path $SourceRoot 'src/GameShared/GameClasses/System/Resource/CgsResourceHandle.cpp')
    )
    $seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    if (@($row.inputs).Count -ne $expectedInputs.Count) { throw 'Traffic flowtype input set differs.' }
    foreach ($compiledInput in $row.inputs) {
        $full = [IO.Path]::GetFullPath([string]$compiledInput.path)
        if ($full -notin $expectedInputs -or -not $seen.Add($full) -or
            $compiledInput.sha256 -cne (Get-FileRecord $full).sha256) {
            throw 'Traffic flowtype compiled input path/hash differs or is duplicated.'
        }
    }
    $scriptText = [IO.File]::ReadAllText((Join-Path $VariantRoot 'run.cmd')).Replace("`r`n", "`n")
    $envScript = Join-Path $Root 'tools/build/msvc_env.bat'
    $expectedScript = "@echo off`ncall `"$envScript`" >nul 2>&1`nif errorlevel 1 exit /b 1`n" +
        $row.command + "`nif errorlevel 1 exit /b 90`nregression.exe`nexit /b %ERRORLEVEL%`n"
    if ($row.command -notmatch '\Acl ' -or $row.command -match '[\r\n]' -or $scriptText -cne $expectedScript) {
        throw 'Traffic flowtype retained command script differs from the helper contract.'
    }
    if ($extraction.schema -ne 1 -or $extraction.source_revision -cne $Revision -or
        $extraction.include_name -cne 'traffic_flowtype_override.inc' -or $extraction.source_objects.Count -ne 5) {
        throw 'Traffic flowtype extraction revision/shape differs.'
    }
    foreach ($relative in @(
        'src/GameSource/World/EntityModules/TrafficEntityModule/BrnTrafficEntityModule.cpp',
        'src/GameSource/World/EntityModules/TrafficEntityModule/BrnTrafficCarStreamer.cpp',
        'src/GameShared/GameClasses/System/Resource/CgsBaseResourcePtr.cpp',
        'src/GameShared/GameClasses/System/Resource/CgsResourcePtr.cpp',
        'src/GameShared/GameClasses/System/Resource/CgsResourceHandle.cpp')) {
        $expectedBlob = Get-GitText @('-C', $SourceRoot, 'rev-parse', "${Revision}:$relative")
        if ($extraction.source_objects[$relative] -cne $expectedBlob) { throw 'Traffic flowtype source blob differs.' }
    }
    $includeText = [IO.File]::ReadAllText((Join-Path $VariantRoot 'traffic_flowtype_override.inc')).Replace("`r`n", "`n")
    $includeHash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData(
        [Text.Encoding]::UTF8.GetBytes($includeText))).ToLowerInvariant()
    if ($extraction.generated_include_lf_sha256 -cne $includeHash) { throw 'Traffic flowtype generated body hash differs.' }
    return @{
        status = $(if ($Baseline) { 'expected_failure_observed' } else { 'pass' })
        revision = $Revision; checks = 44; failures = $failures; process_exit_code = $row.process_exit_code
        executable = @{ path = $exePath; bytes = $exe.bytes; sha256 = $exe.sha256 }
        stdout = Get-FileRecord (Join-Path $VariantRoot 'run.stdout.txt')
        stderr = Get-FileRecord (Join-Path $VariantRoot 'run.stderr.txt')
        result = Get-FileRecord (Join-Path $VariantRoot 'result.json')
        extraction = Get-FileRecord (Join-Path $VariantRoot 'extraction.json')
        compiled_inputs = $row.inputs; source_objects = $extraction.source_objects
    }
}

function Assert-OnlineSaveRouteProcess(
    [System.Collections.IDictionary] $Run, [string] $Log, [int] $Timeout, [int] $Exit
) {
    # The existing validator covers this identical run_owned cleanup/transcript schema.
    try { return Assert-SystemUserProfileRunRecord $Run $Log $Timeout $Exit }
    catch { throw "Online-save-route process receipt rejected: $($_.Exception.Message)" }
}

Push-Location $Root
try {
    foreach ($sha in @($B5Commit, $WorkflowSha)) {
        if ($sha -cnotmatch '\A[0-9a-fA-F]{40}\z') { throw 'Both inputs must be exact 40-hex commit SHAs.' }
    }
    $B5Commit = $B5Commit.ToLowerInvariant()
    $WorkflowSha = $WorkflowSha.ToLowerInvariant()
    $Receipt.parent_head = Get-GitText @('rev-parse', 'HEAD')
    if ($Receipt.parent_head -ne $WorkflowSha) { throw 'Checkout does not match the workflow SHA.' }
    if (Get-GitText @('status', '--porcelain=v1', '--untracked-files=all', '--ignore-submodules=none')) {
        throw 'Parent checkout must start clean.'
    }
    $gitlink = Get-GitText @('ls-tree', 'HEAD', '--', 'b5-decomp')
    if ($gitlink -notmatch '\A160000 commit ([0-9a-f]{40})\tb5-decomp\z') { throw 'Expected the b5-decomp gitlink.' }
    $Receipt.parent_gitlink = $Matches[1]
    $Receipt.gitlink_overridden = $Receipt.parent_gitlink -ne $B5Commit

    # Same two-level dependency selection as the publisher; no recursive test trees.
    Invoke-Native git @('config', '--global', 'core.longpaths', 'true') 'source.log'
    Invoke-Native git @('config', '--global', 'url.https://github.com/.insteadOf', 'git@github.com:') 'source.log'
    Invoke-Native git @('submodule', 'update', '--init', '--checkout', 'b5-decomp') 'source.log'
    Invoke-Native git @('-C', $SourceRoot, 'fetch', '--recurse-submodules=no', '--no-tags', '--depth=1', 'origin', $B5Commit) 'source.log'
    if ((Get-GitText @('-C', $SourceRoot, 'cat-file', '-t', $B5Commit)) -ne 'commit') { throw 'Candidate is not a commit object.' }
    Invoke-Native git @('-C', $SourceRoot, 'checkout', '--detach', $B5Commit) 'source.log'
    Invoke-Native git @('-C', $SourceRoot, 'submodule', 'update', '--init', '--checkout', 'vendor/EABase', 'vendor/EASTL', 'vendor/EAThread') 'source.log'
    $Receipt.b5_head = Get-GitText @('-C', $SourceRoot, 'rev-parse', 'HEAD')
    $Receipt.required_submodules = Get-GitText @('-C', $SourceRoot, 'submodule', 'status', '--', 'vendor/EABase', 'vendor/EASTL', 'vendor/EAThread')
    Assert-CleanTrees

    $clPath = (Get-Command cl.exe -CommandType Application -All | Select-Object -First 1).Source
    $linkPath = Join-Path (Split-Path -Parent $clPath) 'link.exe'
    if ((Get-Command link.exe -CommandType Application -All | Select-Object -First 1).Source -ne $linkPath) {
        throw 'The linker on PATH must belong to the selected MSVC compiler.'
    }
    $clVersion = [Diagnostics.FileVersionInfo]::GetVersionInfo($clPath)
    if ($env:VSCMD_ARG_TGT_ARCH -ne 'x64' -or $env:VSINSTALLDIR -notmatch '\\2022\\' -or $clVersion.FileMajorPart -ne 19) {
        throw 'Expected the Windows 2022 / Visual Studio 2022 MSVC x64 toolchain.'
    }
    $Receipt.toolchain = @{
        cl_path = $clPath; cl_version = $clVersion.FileVersion; cl_sha256 = (Get-FileRecord $clPath).sha256
        link_path = $linkPath; link_version = [Diagnostics.FileVersionInfo]::GetVersionInfo($linkPath).FileVersion
        link_sha256 = (Get-FileRecord $linkPath).sha256
        vc_tools_version = $env:VCToolsVersion; vs_install_dir = $env:VSINSTALLDIR
        windows_sdk_version = $env:WindowsSDKVersion; ucrt_version = $env:UCRTVersion
    }
    $Receipt.build_inputs = @{}
    foreach ($path in @('.github/workflows/build-candidate.yml', 'ci/check-candidate-build.ps1', 'tools/build/build_game_exe.bat', 'tools/build/compile_exe.py', 'tools/build/msvc_flags.txt', 'tools/build/msvc_includes.txt')) {
        $Receipt.build_inputs[$path] = Get-FileRecord (Join-Path $Root $path)
    }
    Invoke-Native py @('-3', '--version') 'toolchain.log'


    if ($RunGuiMenuMusicWire) {
        $Receipt.regressions.status = 'running'
        $Receipt.regressions.gui_menu_music_wire_status = 'running'
        if ($Jobs -ne 4 -or $env:ImageOS -cne 'win22' -or $env:RUNNER_ARCH -cne 'X64') {
            throw 'Menu-music wire checks require hosted Windows 2022 x64 / Jobs=4.'
        }
        Assert-CleanTrees
        $musicReceipt = @{ status = 'running'; candidate_source = $B5Commit; workflow_sha = $WorkflowSha; variants = @{} }
        $Receipt.regressions.gui_menu_music_wire = $musicReceipt
        $musicHarnessPins = @{
            'tests/run_gui_menu_music_wire.py' = '5f77f5f8ca820c34421fa9a2def526dfcda1d8a37bb13b0a13eabfdcdc9fb07e'
            'tests/GuiMenuMusicWire.cpp' = '2603f206fc3f1f3ed808e1fe5ddf4d1d48cd26a28d36c586fe85599bea6ddde2'
            'tests/fxgs_common.py' = '6230372da7ef60e446a165470a61850964b7b7498576eaec93dbb58555ae9033'
        }
        foreach ($relative in $musicHarnessPins.Keys) {
            $actual = Get-LFFileRecord (Join-Path $SourceRoot $relative)
            if ($actual.lf_sha256 -cne $musicHarnessPins[$relative]) { throw "Menu-music reviewed harness differs: $relative" }
            $Receipt.regressions.inputs[$relative] = Get-FileRecord $actual.path
        }
        $musicControl = 'b595d61d2440ca94d61aa8fa610ab0bf6048cc66'
        $null = Get-GitText @('-C', $SourceRoot, 'fetch', '--no-tags', '--depth', '1', 'origin', $musicControl)
        if ((Get-GitText @('-C', $SourceRoot, 'rev-parse', ($musicControl + '^{commit}'))) -cne $musicControl) {
            throw 'Menu-music negative-control revision differs.'
        }
        Remove-Item Env:NoDefaultCurrentDirectoryInExePath -ErrorAction SilentlyContinue
        $musicOut = Join-Path $ArtifactRoot 'gui-menu-music-wire'
        if (Test-Path -LiteralPath $musicOut) { throw 'Menu-music artifact directory must be fresh.' }
        Invoke-Native py @('-3', '-B', (Join-Path $SourceRoot 'tests/run_gui_menu_music_wire.py'),
            '--rev', $B5Commit, '--control-rev', $musicControl, '--output-dir', $musicOut) 'regressions.log'
        $musicResultPath = Join-Path $musicOut 'fixture.json'
        $musicResult = Get-Content -Raw -LiteralPath $musicResultPath | ConvertFrom-Json -AsHashtable
        if ($musicResult.status -cne 'pass' -or $musicResult.candidate_source -cne $B5Commit -or
            $musicResult.negative_control_revision -cne $musicControl) {
            throw 'Menu-music result does not identify the exact passing candidate and unchanged control.'
        }
        foreach ($spec in @(
            @{ name = 'candidate'; directory = 'candidate'; key = 'candidate_receipt'; tag = 'Menu23Candidate'; checks = 217 },
            @{ name = 'negative_control'; directory = 'b595_negative_control'; key = 'negative_control_receipt'; tag = 'Menu23OldControl'; checks = 189 }
        )) {
            $variant = $musicResult[$spec.key]
            $variantRoot = Join-Path $musicOut $spec.directory
            $runRecord = Get-Content -Raw -LiteralPath (Join-Path $variantRoot 'result.json') | ConvertFrom-Json -AsHashtable
            $logPath = Join-Path $variantRoot 'run.stdout.txt'
            $log = Get-Content -Raw -LiteralPath $logPath
            $summary = [regex]::Matches($log, ('(?m)^' + $spec.tag + ': (\d+) checks, (\d+) failures\r?$'))
            $expectedSource = if ($spec.name -ceq 'candidate') { $B5Commit } else { $musicControl }
            if ($variant.source_tree -cne $expectedSource -or $variant.tag -cne $spec.tag -or
                $variant.process_exit_code -ne 0 -or $runRecord.process_exit_code -ne 0 -or
                $variant.numeric.checks -ne $spec.checks -or $variant.numeric.failures -ne 0 -or
                $runRecord.numeric.checks -ne $spec.checks -or $runRecord.numeric.failures -ne 0 -or
                $summary.Count -ne 1 -or [int]$summary[0].Groups[1].Value -ne $spec.checks -or
                [int]$summary[0].Groups[2].Value -ne 0 -or $log -match '(?m)^FAIL ' -or
                @($variant.field_observations).Count -ne 12 -or
                @($variant.field_failure_witnesses).Count -ne 0 -or
                $variant.compile_and_numeric_output_reached -ne $true) {
                throw "Menu-music compile/numeric/field receipts differ: $($spec.name)"
            }
            $exeRecord = Get-FileRecord (Join-Path $variantRoot 'regression.exe')
            if ($exeRecord.sha256 -cne $variant.executable_sha256 -or
                $exeRecord.sha256 -cne $runRecord.executable_sha256) { throw 'Menu-music executable hash differs.' }
            $mismatches = [regex]::Matches($log, '(?m)^NEGATIVE_CONTROL_RAW8_MISMATCH flags=(00|01|10|11) ')
            $expectedMismatchCount = if ($spec.name -ceq 'negative_control') { 4 } else { 0 }
            if ($mismatches.Count -ne $expectedMismatchCount -or
                @($variant.expected_raw8_mismatch_witnesses).Count -ne $expectedMismatchCount) {
                throw 'Menu-music negative-control mismatch witnesses differ.'
            }
            if ($expectedMismatchCount -eq 4 -and
                [string]::Join('|', [string[]]@($mismatches | ForEach-Object { $_.Groups[1].Value } | Sort-Object)) -cne '00|01|10|11') {
                throw 'Menu-music negative control did not cover all four flag pairs.'
            }
            # The candidate shadow headers and source snippets must be the current production files.
            # The old control is independently bound to its exact Git revision by the runner.
            if ($spec.name -ceq 'candidate') {
                $sourcePins = @{} + $variant.shadow_header_sha256
                foreach ($relative in @('src/GameSource/Sound/Module/LogicModule/BrnSoundLogicModule.cpp',
                                         'src/GameSource/Gui/Flow/HUD/States/BrnBootLegal.cpp')) {
                    $sourcePins[$relative] = $variant.source_text_sha256[$relative]
                }
                foreach ($relative in $sourcePins.Keys) {
                    if (-not $relative.StartsWith('src/') -or $relative.Contains('..')) { throw 'Menu-music source path differs.' }
                    $actual = Get-LFFileRecord (Join-Path $SourceRoot $relative)
                    if ($actual.lf_sha256 -cne $sourcePins[$relative]) { throw "Menu-music production input differs: $relative" }
                    $Receipt.regressions.inputs[$relative] = Get-FileRecord $actual.path
                }
                $relative = 'src/GameShared/GameClasses/Development/CgsStrStream.cpp'
                $Receipt.regressions.inputs[$relative] = Get-FileRecord (Join-Path $SourceRoot $relative)
            }
            $musicReceipt.variants[$spec.name] = @{ checks = $spec.checks; failures = 0; process_exit_code = 0;
                source = $expectedSource; executable = $exeRecord; numeric_receipt = Get-FileRecord (Join-Path $variantRoot 'result.json');
                log = Get-FileRecord $logPath; expected_raw_mismatches = $expectedMismatchCount }
        }
        $musicReceipt.fixture = Get-FileRecord $musicResultPath
        $musicReceipt.scope = 'Extracted production case23 and actual queue/message types; channel40 drain and audible playback remain native checks.'
        $musicReceipt.status = 'pass'
        Assert-CleanTrees
        $Receipt.regressions.gui_menu_music_wire_status = 'pass'
        $Receipt.regressions.status = 'partial_selected_fixtures_pass'
    }

    if ($RunOnlineSaveRoute) {
        $Receipt.regressions.status = 'running'
        $Receipt.regressions.online_save_route_status = 'running'
        $routeReceipt = @{
            status = 'running'; actual_b5_commit = $B5Commit; actual_workflow_sha = $WorkflowSha
            subject_commit_metadata = '17ab0a96e27bed5e60ffc55cb81dcf0a653b1e4e'
            source_base_metadata = '8b2940d40e76fd6a88a37615f6163a99c2d5e3b8'
            payloads = @{}; pinned_inputs = @{}; variants = @{}
        }
        $Receipt.regressions.online_save_route = $routeReceipt
        if ($Jobs -ne 4 -or $env:ImageOS -cne 'win22' -or $env:RUNNER_ARCH -cne 'X64') {
            throw 'Online-save-route requires the existing hosted Windows 2022 x64 / Jobs=4 job.'
        }
        Assert-CleanTrees
        foreach ($relative in $OnlineSaveRoutePayloadPins.Keys) {
            $actual = Get-LFFileRecord (Join-Path $SourceRoot $relative)
            $expected = $OnlineSaveRoutePayloadPins[$relative]
            if ($actual.lf_sha256 -cne $expected.lf_sha256 -or $actual.lf_bytes -ne $expected.lf_bytes) {
                throw "Online-save-route reviewed payload differs: $relative"
            }
            $routeReceipt.payloads[$relative] = $actual
            $Receipt.regressions.inputs[$relative] = Get-FileRecord $actual.path
        }
        $routePins = Get-Content -Raw -LiteralPath (Join-Path $SourceRoot 'tests/evidence/online_save_route/source_pins.json') | ConvertFrom-Json -AsHashtable
        if ($routePins.schema_version -ne 1 -or $routePins.normalization -cne 'crlf_to_lf_only' -or
            $routePins.base -cne $routeReceipt.source_base_metadata -or @($routePins.b5_files.Keys).Count -ne 24 -or
            @($routePins.workflow_files.Keys).Count -ne 3) { throw 'Online-save-route source-pin schema differs.' }
        # 8b is proof metadata. The baseline blob is supplied and hashed by the
        # pinned binder; no historical Git object is needed in this shallow checkout.
        foreach ($kind in @('b5', 'workflow')) {
            $pinRoot = if ($kind -eq 'b5') { $SourceRoot } else { $Root }
            $filePins = if ($kind -eq 'b5') { $routePins.b5_files } else { $routePins.workflow_files }
            foreach ($relative in $filePins.Keys) {
                $actual = Get-LFFileRecord (Join-Path $pinRoot $relative)
                if ($actual.lf_sha256 -cne $filePins[$relative].lf_sha256 -or
                    $actual.lf_bytes -ne $filePins[$relative].lf_bytes) {
                    throw "Online-save-route pinned input differs: $kind/$relative"
                }
                $routeReceipt.pinned_inputs["$kind/$relative"] = $actual
                if ($kind -eq 'b5') { $Receipt.regressions.inputs[$relative] = Get-FileRecord $actual.path }
            }
        }
        $routePlan = Get-Content -Raw -LiteralPath (Join-Path $SourceRoot 'tests/evidence/online_save_route/test_plan.json') | ConvertFrom-Json -AsHashtable
        $routeOut = Join-Path $ArtifactRoot 'online-save-route'
        if (Test-Path -LiteralPath $routeOut) { throw 'Online-save-route artifact directory must be fresh.' }
        $routeResultPath = Join-Path $routeOut 'result.json'
        try {
            Invoke-Native py @('-3', '-B', (Join-Path $SourceRoot 'tests/run_online_save_route.py'),
                '--workflow-root', $Root, '--out', $routeOut, '--run') 'regressions.log'
        } finally {
            if (Test-Path -LiteralPath $routeResultPath -PathType Leaf) {
                $routeReceipt.result_path = $routeResultPath
                $routeReceipt.result_file = Get-FileRecord $routeResultPath
            }
        }
        $routeResult = Get-Content -Raw -LiteralPath $routeResultPath | ConvertFrom-Json -AsHashtable
        if ($routeResult.schema_version -ne 1 -or $routeResult.fixture -cne 'ONLINE_SAVE_ROUTE' -or
            $routeResult.status -cne 'pass' -or $routeResult.executed -ne $true -or $routeResult.success -ne $true -or
            $routeResult.checkout.b5_sha -cne $B5Commit -or $routeResult.checkout.workflow_sha -cne $WorkflowSha -or
            $routeResult.checkout.b5_branch -cne 'HEAD' -or $routeResult.checkout.b5_status -cne '' -or
            ([string]::Join('|', [string[]]@($routeResult.variants.Keys | Sort-Object))) -cne 'candidate|oldtrap|omitted_init') {
            throw 'Online-save-route result is not the exact executed passing candidate/control composition.'
        }
        foreach ($pair in @(@('b5_root', $SourceRoot), @('workflow_root', $Root), @('artifact_root', $routeOut))) {
            if (-not [string]::Equals([IO.Path]::GetFullPath($routeResult[$pair[0]]),
                [IO.Path]::GetFullPath($pair[1]), [StringComparison]::OrdinalIgnoreCase)) {
                throw 'Online-save-route result root differs.'
            }
        }
        $routeVariantModes = @{ candidate = @('candidate'); oldtrap = @('oldtrap_save', 'oldtrap_load'); omitted_init = @('omitted_init') }
        foreach ($variantName in @('candidate', 'oldtrap', 'omitted_init')) {
            $variant = $routeResult.variants[$variantName]
            $variantRoot = Join-Path $routeOut $variantName
            if (@($variant.compile).Count -ne 8 -or $variant.dependencies_unchanged_after_run -ne $true -or
                @($variant.dependency_inputs.Keys).Count -eq 0 -or
                ([string]::Join('|', [string[]]@($variant.modes.Keys | Sort-Object))) -cne
                ([string]::Join('|', [string[]]@($routeVariantModes[$variantName] | Sort-Object)))) {
                throw "Online-save-route compile/dependency/mode composition differs: $variantName"
            }
            for ($index = 0; $index -lt 8; ++$index) {
                $null = Assert-OnlineSaveRouteProcess $variant.compile[$index].run (Join-Path $variantRoot "compile$index.log") 120 0
            }
            $null = Assert-OnlineSaveRouteProcess $variant.link.run (Join-Path $variantRoot 'link.log') 120 0
            $exePath = Join-Path $variantRoot 'OnlineSaveRoute.exe'
            $exeRecord = Get-FileRecord $exePath
            if ($variant.executable.raw_sha256 -cne $exeRecord.sha256 -or $variant.executable.raw_bytes -ne $exeRecord.bytes) {
                throw "Online-save-route retained executable differs: $variantName"
            }
            $routeReceipt.variants[$variantName] = @{ compile_count = 8; link_exit_code = 0; executable = $exeRecord; modes = @{} }
        }
        $routeModes = @(
            @{ variant = 'candidate'; name = 'candidate'; checks = 71; failures = 0; exit = 0 },
            @{ variant = 'omitted_init'; name = 'omitted_init'; checks = 13; failures = 6; exit = 1 },
            @{ variant = 'oldtrap'; name = 'oldtrap_save'; checks = 1; failures = 1; exit = 1; breakpoint = 'save' },
            @{ variant = 'oldtrap'; name = 'oldtrap_load'; checks = 1; failures = 1; exit = 1; breakpoint = 'load' }
        )
        foreach ($spec in $routeModes) {
            $mode = $routeResult.variants[$spec.variant].modes[$spec.name]
            $expected = $routePlan.modes[$spec.name]
            $status = if ($spec.failures) { 'expected_failure_observed' } else { 'pass' }
            $logPath = Join-Path (Join-Path $routeOut $spec.variant) ($spec.name + '.log')
            $text = Assert-OnlineSaveRouteProcess $mode.run $logPath 20 $spec.exit
            $summary = [regex]::Matches($text, '(?m)^ONLINE_SAVE_ROUTE checks=(\d+) failures=(\d+) assertions=(\d+)$')
            $checkRows = [regex]::Matches($text, '(?m)^CHECK (\S+) (PASS|FAIL)$')
            $ids = [string[]]@($checkRows | ForEach-Object { $_.Groups[1].Value })
            $failedIds = [string[]]@($checkRows | Where-Object { $_.Groups[2].Value -eq 'FAIL' } | ForEach-Object { $_.Groups[1].Value })
            if ($mode.valid -ne $true -or $mode.status -cne $status -or $summary.Count -ne 1 -or
                [int]$summary[0].Groups[1].Value -ne $spec.checks -or [int]$summary[0].Groups[2].Value -ne $spec.failures -or
                [int]$summary[0].Groups[3].Value -ne 0 -or $text -match '(?m)^UNEXPECTED_ASSERT ' -or
                @($expected.check_ids).Count -ne $spec.checks -or @($expected.failure_ids).Count -ne $spec.failures -or
                [string]::Join('|', $ids) -cne [string]::Join('|', [string[]]@($expected.check_ids)) -or
                [string]::Join('|', $ids) -cne [string]::Join('|', [string[]]@($mode.observed_check_ids)) -or
                [string]::Join('|', $failedIds) -cne [string]::Join('|', [string[]]@($expected.failure_ids)) -or
                [string]::Join('|', $failedIds) -cne [string]::Join('|', [string[]]@($mode.observed_failure_ids))) {
                throw "Online-save-route real mode identity/count/failure witness differs: $($spec.name)"
            }
            if ($spec.ContainsKey('breakpoint')) {
                $breaks = [regex]::Matches($text, '(?m)^ORIGINAL_BREAKPOINT mode=(save|load) code=([0-9A-F]{8})$')
                if ($breaks.Count -ne 1 -or $breaks[0].Groups[1].Value -cne $spec.breakpoint -or
                    $breaks[0].Groups[2].Value -cne '80000003') { throw 'Online-save-route original breakpoint witness differs.' }
            }
            $routeReceipt.variants[$spec.variant].modes[$spec.name] = @{
                status = $status; checks = $spec.checks; failures = $spec.failures; assertions = 0
                process_exit_code = $spec.exit; failure_ids = $failedIds; log = Get-FileRecord $logPath
            }
            if ($spec.failures) {
                $Receipt.regressions.negative_controls['online-save-route-' + $spec.name] = @{
                    status = 'expected_behavior_failure'; exit_code = $spec.exit; log = $logPath
                }
            }
        }
        # The exact pinned runner additionally validates body composition, input and
        # dependency hashes before/after, and every owned-child cleanup internally.
        $routeReceipt.runner_result = @{ status = $routeResult.status; executed = $routeResult.executed; success = $routeResult.success }
        Assert-CleanTrees
        $routeReceipt.status = 'pass'
        $Receipt.regressions.online_save_route_status = 'pass'
        $Receipt.regressions.status = 'partial_selected_fixtures_pass'
    }

    if ($RunTrafficFlowtypeOverride) {
        $Receipt.regressions.status = 'running'
        $Receipt.regressions.traffic_flowtype_override_status = 'running'
        if ($Jobs -ne 4 -or $env:ImageOS -ne 'win22') { throw 'Traffic flowtype requires hosted Windows 2022 / Jobs=4.' }
        # Fix the reviewed harness while allowing the requested production revision to vary.
        $flowHarnessPins = @{
            'tests/TrafficFlowtypeOverride.cpp' = 'ca57fb44af73b7ffdc6903484dc7648def57dd9e07ae2e396f565bd8c4b61158'
            'tests/run_traffic_flowtype_override.py' = 'f5b8bb80a80aa1b0ef8044b3459eee71d9d5ea26d17a0980d6bae31ea0a028b6'
            'tests/fxgs_common.py' = '6230372da7ef60e446a165470a61850964b7b7498576eaec93dbb58555ae9033'
        }
        foreach ($relative in $flowHarnessPins.Keys) {
            $rawText = [Text.Encoding]::UTF8.GetString([IO.File]::ReadAllBytes((Join-Path $SourceRoot $relative)))
            $lfHash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData(
                [Text.Encoding]::UTF8.GetBytes($rawText.Replace("`r`n", "`n")))).ToLowerInvariant()
            if ($lfHash -cne $flowHarnessPins[$relative]) { throw 'Traffic flowtype reviewed harness content differs.' }
        }
        $flowOut = Join-Path $ArtifactRoot 'traffic-flowtype-override'
        if (Test-Path -LiteralPath $flowOut) { throw 'Traffic flowtype artifact directory must be fresh.' }
        $flowInputs = @{}
        foreach ($relative in @(
            'tests/run_traffic_flowtype_override.py', 'tests/TrafficFlowtypeOverride.cpp', 'tests/fxgs_common.py',
            'src/GameSource/World/EntityModules/TrafficEntityModule/BrnTrafficEntityModule.cpp',
            'src/GameSource/World/EntityModules/TrafficEntityModule/BrnTrafficEntityModule.h',
            'src/GameSource/World/EntityModules/TrafficEntityModule/BrnTrafficCarStreamer.cpp',
            'src/GameSource/World/EntityModules/TrafficEntityModule/BrnTrafficCarStreamer.h',
            'src/GameSource/World/BrnBaseStreamer.h', 'src/SharedClasses/Traffic/BrnTrafficDataResourceType.h',
            'src/SharedClasses/Traffic/BrnTrafficFlowType.h', 'src/SharedClasses/Traffic/BrnTrafficVehicleType.h',
            'src/SharedClasses/Traffic/BrnTrafficHull.h', 'src/SharedClasses/Traffic/BrnTrafficSharedConstants.h',
            'src/GameShared/GameClasses/Containers/CgsArray.h', 'src/GameShared/GameClasses/Core/CgsAssert.h',
            'src/GameShared/GameClasses/System/Resource/CgsResourcePtr.h',
            'src/GameShared/GameClasses/System/Resource/CgsBaseResourcePtr.cpp',
            'src/GameShared/GameClasses/System/Resource/CgsResourcePtr.cpp',
            'src/GameShared/GameClasses/System/Resource/CgsResourceHandle.cpp',
            'src/GameShared/GameClasses/System/Resource/CgsResourceHandle.h',
            'src/GameShared/GameClasses/System/Resource/CgsResourceBasePool.h', 'src/types.hpp')) {
            $flowInputs[$relative] = Get-FileRecord (Join-Path $SourceRoot $relative)
        }
        foreach ($relative in @('tools/build/msvc_flags.txt', 'tools/build/msvc_includes.txt', 'tools/build/msvc_env.bat')) {
            $flowInputs['parent/' + $relative] = Get-FileRecord (Join-Path $Root $relative)
        }
        $Receipt.regressions.traffic_flowtype_override = @{
            status = 'running'; inputs = $flowInputs; harness_lf_pins = $flowHarnessPins
            coverage = '44 production-body checks with exact old-return control; high bytes capture only; native #0081 unverified.'
        }
        $flowBaseline = '8fec93bd4d2806ca9b60fb53dc272fe28081f8b8'
        Invoke-Native git @('-C', $SourceRoot, 'fetch', '--recurse-submodules=no', '--no-tags', '--depth=1', 'origin', $flowBaseline) 'source.log'
        # These real compiled providers are shared by both variants; require exact control blobs.
        foreach ($relative in @(
            'src/GameShared/GameClasses/System/Resource/CgsBaseResourcePtr.cpp',
            'src/GameShared/GameClasses/System/Resource/CgsResourcePtr.cpp',
            'src/GameShared/GameClasses/System/Resource/CgsResourceHandle.cpp')) {
            $candidateProvider = Get-GitText @('-C', $SourceRoot, 'rev-parse', "${B5Commit}:$relative")
            $controlProvider = Get-GitText @('-C', $SourceRoot, 'rev-parse', "${flowBaseline}:$relative")
            if ($candidateProvider -cne $controlProvider) { throw 'Flowtype fixture provider differs from exact control.' }
        }
        $flowNoDefaultWasPresent = Test-Path -LiteralPath Env:NoDefaultCurrentDirectoryInExePath
        $flowNoDefault = [Environment]::GetEnvironmentVariable('NoDefaultCurrentDirectoryInExePath', 'Process')
        try {
            Remove-Item -LiteralPath Env:NoDefaultCurrentDirectoryInExePath -ErrorAction SilentlyContinue
            Invoke-Native py @('-3', '-B', (Join-Path $SourceRoot 'tests/run_traffic_flowtype_override.py'),
                '--rev', $B5Commit, '--output-dir', $flowOut) 'regressions.log'
        } finally {
            if ($flowNoDefaultWasPresent) {
                Set-Item -LiteralPath Env:NoDefaultCurrentDirectoryInExePath -Value ([string]$flowNoDefault)
            } else {
                Remove-Item -LiteralPath Env:NoDefaultCurrentDirectoryInExePath -ErrorAction SilentlyContinue
            }
        }
        $flowVariants = @{
            candidate = Assert-TrafficFlowtypeVariant (Join-Path $flowOut 'candidate') $B5Commit $false
            baseline = Assert-TrafficFlowtypeVariant (Join-Path $flowOut 'baseline') $flowBaseline $true
        }
        foreach ($key in $flowInputs.Keys) {
            $inputPath = if ($key.StartsWith('parent/')) { Join-Path $Root $key.Substring(7) } else { Join-Path $SourceRoot $key }
            $now = Get-FileRecord $inputPath
            if ($now.sha256 -cne $flowInputs[$key].sha256 -or $now.bytes -ne $flowInputs[$key].bytes) {
                throw 'Traffic flowtype source/helper/toolchain input changed while running.'
            }
        }
        Assert-CleanTrees
        $Receipt.regressions.traffic_flowtype_override.variants = $flowVariants
        $Receipt.regressions.traffic_flowtype_override.status = 'pass'
        $Receipt.regressions.traffic_flowtype_override_status = 'pass'
        $Receipt.regressions.status = 'partial_selected_fixtures_pass'
    }

    # Optional, source-pinned PC profile fixture with the exact old API/consumer controls.
    if ($RunSystemUserProfile) {
        $Receipt.regressions.status = 'running'
        $Receipt.regressions.system_user_profile_status = 'running'
        if ($Jobs -ne 4 -or $Receipt.runner_label -cne 'windows-2022' -or
            $env:RUNNER_OS -cne 'Windows' -or $env:CANDIDATE_RUNNER_ENVIRONMENT -cne 'github-hosted') {
            throw 'System-user-profile fixture is limited to GitHub-hosted Windows 2022 with four build jobs.'
        }
        Assert-CleanTrees
        Remove-Item -LiteralPath Env:NoDefaultCurrentDirectoryInExePath -ErrorAction SilentlyContinue
        foreach ($relative in @('tests/run_system_user_profile_pc.py',
                                'tests/evidence/system_user_profile_pc/source_pins.json',
                                'tests/evidence/system_user_profile_pc/test_plan.json')) {
            $Receipt.regressions.inputs[$relative] = Get-FileRecord (Join-Path $SourceRoot $relative)
        }
        $profileRunner = Join-Path $SourceRoot 'tests/run_system_user_profile_pc.py'
        $profileOut = Join-Path $ArtifactRoot 'system-user-profile'
        if (Test-Path -LiteralPath $profileOut) {
            if (@(Get-ChildItem -LiteralPath $profileOut -Force).Count -ne 0) {
                throw 'System-user-profile output directory must be fresh and empty.'
            }
        } else {
            New-Item -ItemType Directory -Path $profileOut | Out-Null
        }
        Invoke-Native py @('-3', '-B', $profileRunner, '--workflow-root', $Root,
                           '--out', $profileOut, '--run') 'regressions.log'
        $profileResultPath = Join-Path $profileOut 'result.json'
        if (-not (Test-Path -LiteralPath $profileResultPath -PathType Leaf)) {
            throw 'System-user-profile runner did not retain result.json.'
        }
        $profileResult = Get-Content -Raw -LiteralPath $profileResultPath | ConvertFrom-Json -AsHashtable
        $Receipt.regressions.system_user_profile = @{
            status = 'running'
            result = Get-FileRecord $profileResultPath
            runner = Get-FileRecord $profileRunner
            source_pins = Get-FileRecord (Join-Path $SourceRoot 'tests/evidence/system_user_profile_pc/source_pins.json')
            test_plan = Get-FileRecord (Join-Path $SourceRoot 'tests/evidence/system_user_profile_pc/test_plan.json')
            source_base_head = $profileResult.sources.base_head
            b5_head = $Receipt.b5_head
        }
        $profileVariants = Assert-SystemUserProfileReceipt $profileResult $profileOut $SourceRoot $Root
        Assert-CleanTrees
        $Receipt.regressions.system_user_profile.status = 'pass'
        $Receipt.regressions.system_user_profile.source_receipt = $profileResult.sources
        $Receipt.regressions.system_user_profile.source_status = $Receipt.source_status
        $Receipt.regressions.system_user_profile.parent_status = $Receipt.parent_status
        $Receipt.regressions.system_user_profile.variants = $profileVariants
        $Receipt.regressions.system_user_profile_status = 'pass'
        $Receipt.regressions.status = 'partial_selected_fixtures_pass'
    }

    # Independent IO fixtures run before the exe gate; their receipts survive
    # a separate compile/link failure and cannot mark the candidate validated.
    if ($RunGuiIORegressions) {
        $Receipt.regressions.status = 'running'
        $Receipt.regressions.gui_io_status = 'running'
        Remove-Item -LiteralPath Env:NoDefaultCurrentDirectoryInExePath -ErrorAction SilentlyContinue
        foreach ($relative in @('tests/run_gui_model_io.py', 'tests/GuiModelIO.cpp',
                                'tests/run_gui_interpreter_io.py', 'tests/GuiInterpreterIO.cpp',
                                'tests/run_apt_textformat_binding.py', 'tests/AptTextFormatBinding.cpp',
                                'src/SDKs/EATech/include/Apt/AptTextFormat.cpp',
                                'src/SDKs/EATech/include/Apt/AptTextFormat.h',
                                'src/SDKs/EATech/Apt/AptTextFormatMembersIndex.cpp',
                                'src/SDKs/EATech/Apt/AptTextFormatMembersIndex.h')) {
            $Receipt.regressions.inputs[$relative] = Get-FileRecord (Join-Path $SourceRoot $relative)
        }
        $guiIORoot = Join-Path $ArtifactRoot 'gui-io-regressions'
        $guiIOFixtures = @(
            @{ name = 'model'; runner = 'tests/run_gui_model_io.py'; tag = 'GuiModelIO'; checks = 377 },
            @{ name = 'interpreter'; runner = 'tests/run_gui_interpreter_io.py'; tag = 'GuiInterpreterIO'; checks = 169 },
            @{ name = 'text-format'; runner = 'tests/run_apt_textformat_binding.py'; tag = 'AptTextFormatBinding'; checks = 78 }
        )
        foreach ($fixture in $guiIOFixtures) {
            $fixtureDir = Join-Path $guiIORoot $fixture.name
            Invoke-Native py @('-3', '-B', (Join-Path $SourceRoot $fixture.runner), '--output-dir', $fixtureDir) 'regressions.log'
            $result = Get-Content -Raw -LiteralPath (Join-Path $fixtureDir 'result.json') | ConvertFrom-Json
            $log = Get-Content -Raw -LiteralPath (Join-Path $fixtureDir 'run.stdout.txt')
            $witness = [regex]::Escape($fixture.tag) + ':\s+' + $fixture.checks + ' checks, 0 failures'
            if ($result.process_exit_code -ne 0 -or $null -eq $result.numeric -or
                $result.numeric.checks -ne $fixture.checks -or $result.numeric.failures -ne 0 -or $log -notmatch $witness) {
                throw "GUI IO fixture $($fixture.name) did not execute its expected numeric checks."
            }
        }
        $guiIOControls = @(
            @{ name = 'model-base-only'; runner = 'tests/run_gui_model_io.py'; flag = '--base-only'; witness = 'FAIL queue is constructed, empty and aligned' },
            @{ name = 'model-retain-view'; runner = 'tests/run_gui_model_io.py'; flag = '--retain-view-events'; witness = 'FAIL queue is constructed, empty and aligned' },
            @{ name = 'interpreter-old-capacity'; runner = 'tests/run_gui_interpreter_io.py'; flag = '--old-capacity'; witness = 'FAIL (ARTIST output event capacity|event record beyond the old)' },
            @{ name = 'interpreter-clear-input'; runner = 'tests/run_gui_interpreter_io.py'; flag = '--clear-input-on-destruct'; witness = 'FAIL input Destruct leaves its complete populated queue unchanged' },
            @{ name = 'text-format-old-setter'; runner = 'tests/run_apt_textformat_binding.py'; flag = '--old-setter'; witness = 'FAIL captured font-fit loop progresses and terminates before its test bound' }
        )
        foreach ($control in $guiIOControls) {
            $controlDir = Join-Path $guiIORoot $control.name
            $logName = 'gui-io-negative-' + $control.name + '.log'
            & py -3 -B (Join-Path $SourceRoot $control.runner) $control.flag --output-dir $controlDir 2>&1 |
                Tee-Object -FilePath (Join-Path $ArtifactRoot $logName) | Out-Host
            $code = $LASTEXITCODE
            $NativeCommands.Add(@{ command = 'py'; arguments = @('-3', '-B', (Join-Path $SourceRoot $control.runner), $control.flag, '--output-dir', $controlDir); exit_code = $code; expected_failure = $true })
            $result = Get-Content -Raw -LiteralPath (Join-Path $controlDir 'result.json') | ConvertFrom-Json
            $log = Get-Content -Raw -LiteralPath (Join-Path $controlDir 'run.stdout.txt')
            if ($code -eq 0 -or $result.process_exit_code -eq 0 -or $null -eq $result.numeric -or
                $result.numeric.checks -lt 1 -or $result.numeric.failures -lt 1 -or $log -notmatch $control.witness) {
                throw "GUI IO negative control $($control.name) failed before its intended behavior witness."
            }
            $Receipt.regressions.negative_controls['gui-io-' + $control.name] = @{ status = 'expected_behavior_failure'; exit_code = $code; log = $logName }
        }
        $Receipt.regressions.gui_io_status = 'pass'
        $Receipt.regressions.status = 'partial_gui_io_pass'
        Assert-CleanTrees
    }

    # HUD fixtures are independent of native GUI platform linking. Preserve
    # execution receipts before the exe gate, without validating a partial candidate.
    if ($RunHudRegressions) {
        $Receipt.regressions.status = 'running'
        $Receipt.regressions.hud_status = 'running'
        Remove-Item -LiteralPath Env:NoDefaultCurrentDirectoryInExePath -ErrorAction SilentlyContinue
        foreach ($relative in @('tests/run_fxgs_hud_crashes.py', 'tests/FxGsHudCrashes.cpp',
                                'tests/run_fxgs_online_roadrage_hud.py', 'tests/FxGsOnlineRoadRageHud.cpp',
                                'tests/fxgs_common.py')) {
            $Receipt.regressions.inputs[$relative] = Get-FileRecord (Join-Path $SourceRoot $relative)
        }
        $hudRoot = Join-Path $ArtifactRoot 'hud-regressions'
        $hudFixtures = @(
            @{ name = 'crashes'; runner = 'tests/run_fxgs_hud_crashes.py'; tag = 'FxGsHudCrashes'; checks = 38 },
            @{ name = 'road-rage'; runner = 'tests/run_fxgs_online_roadrage_hud.py'; tag = 'FxGsOnlineRoadRageHud'; checks = 19 }
        )
        foreach ($fixture in $hudFixtures) {
            $fixtureDir = Join-Path $hudRoot $fixture.name
            Invoke-Native py @('-3', '-B', (Join-Path $SourceRoot $fixture.runner), '--output-dir', $fixtureDir) 'regressions.log'
            $result = Get-Content -Raw -LiteralPath (Join-Path $fixtureDir 'result.json') | ConvertFrom-Json
            $log = Get-Content -Raw -LiteralPath (Join-Path $fixtureDir 'run.stdout.txt')
            $witness = [regex]::Escape($fixture.tag) + ':\s+' + $fixture.checks + ' checks, 0 failures'
            if ($result.process_exit_code -ne 0 -or $null -eq $result.numeric -or
                $result.numeric.checks -ne $fixture.checks -or $result.numeric.failures -ne 0 -or $log -notmatch $witness) {
                throw "HUD fixture $($fixture.name) did not execute its expected numeric checks."
            }
        }
        $hudControls = @(
            @{ name = 'legacy-team-predicate'; runner = 'tests/run_fxgs_online_roadrage_hud.py'; flag = '--legacy-team-predicate'; checks = 19; witness = 'FAIL: 164 first team != 1 remains eligible' },
            @{ name = 'omit-team-tail'; runner = 'tests/run_fxgs_hud_crashes.py'; flag = '--omit-team-tail'; checks = 38; witness = 'FAIL: team-change tail posts ordered 254 records outside mode-specific arms' }
        )
        foreach ($control in $hudControls) {
            $controlDir = Join-Path $hudRoot $control.name
            $logName = 'hud-negative-' + $control.name + '.log'
            & py -3 -B (Join-Path $SourceRoot $control.runner) $control.flag --output-dir $controlDir 2>&1 |
                Tee-Object -FilePath (Join-Path $ArtifactRoot $logName) | Out-Host
            $code = $LASTEXITCODE
            $NativeCommands.Add(@{ command = 'py'; arguments = @('-3', '-B', (Join-Path $SourceRoot $control.runner), $control.flag, '--output-dir', $controlDir); exit_code = $code; expected_failure = $true })
            $result = Get-Content -Raw -LiteralPath (Join-Path $controlDir 'result.json') | ConvertFrom-Json
            $log = Get-Content -Raw -LiteralPath (Join-Path $controlDir 'run.stderr.txt')
            if ($code -eq 0 -or $result.process_exit_code -eq 0 -or $null -eq $result.numeric -or
                $result.numeric.checks -ne $control.checks -or $result.numeric.failures -lt 1 -or -not $log.Contains($control.witness)) {
                throw "HUD negative control $($control.name) failed before its intended behavior witness."
            }
            $Receipt.regressions.negative_controls['hud-' + $control.name] = @{ status = 'expected_behavior_failure'; exit_code = $code; log = $logName }
        }
        $Receipt.regressions.hud_status = 'pass'
        $Receipt.regressions.status = 'partial_selected_fixtures_pass'
        Assert-CleanTrees
    }

    # Actual animation bodies run independently of shipping linkage. This is
    # a deterministic initializer regression, not a game/Create Match success verdict.
    if ($RunGuiAnimationRegressions) {
        $Receipt.regressions.status = 'running'
        $Receipt.regressions.gui_animation_status = 'running'
        Remove-Item -LiteralPath Env:NoDefaultCurrentDirectoryInExePath -ErrorAction SilentlyContinue
        foreach ($relative in @('tests/run_gui_animation_initialization.py', 'tests/GuiAnimationInitialization.cpp')) {
            $Receipt.regressions.inputs[$relative] = Get-FileRecord (Join-Path $SourceRoot $relative)
        }
        $animationRunner = Join-Path $SourceRoot 'tests/run_gui_animation_initialization.py'
        $animationRoot = Join-Path $ArtifactRoot 'gui-animation-regressions'
        $positiveDir = Join-Path $animationRoot 'positive'
        Invoke-Native py @('-3', '-B', $animationRunner, '--output-dir', $positiveDir) 'regressions.log'
        $positive = Get-Content -Raw -LiteralPath (Join-Path $positiveDir 'result.json') | ConvertFrom-Json
        $positiveLog = Get-Content -Raw -LiteralPath (Join-Path $positiveDir 'run.stdout.txt')
        if ($positive.process_exit_code -ne 0 -or $null -eq $positive.numeric -or
            $positive.numeric.checks -ne 68 -or $positive.numeric.failures -ne 0 -or
            -not $positiveLog.Contains('GUI_ANIMATION_INITIALIZATION: 68 checks, 0 failures')) {
            throw 'GUI animation positive fixture did not execute its expected68 numeric checks.'
        }
        $negativeDir = Join-Path $animationRoot 'omit-channel-construct'
        $logName = 'gui-animation-negative-omit-channel-construct.log'
        & py -3 -B $animationRunner --omit-channel-construct --output-dir $negativeDir 2>&1 |
            Tee-Object -FilePath (Join-Path $ArtifactRoot $logName) | Out-Host
        $code = $LASTEXITCODE
        $NativeCommands.Add(@{ command = 'py'; arguments = @('-3', '-B', $animationRunner, '--omit-channel-construct', '--output-dir', $negativeDir); exit_code = $code; expected_failure = $true })
        $negative = Get-Content -Raw -LiteralPath (Join-Path $negativeDir 'result.json') | ConvertFrom-Json
        $negativeLog = (Get-Content -Raw -LiteralPath (Join-Path $negativeDir 'run.stdout.txt')) +
            (Get-Content -Raw -LiteralPath (Join-Path $negativeDir 'run.stderr.txt'))
        if ($code -ne 1 -or $negative.process_exit_code -ne 1 -or $null -eq $negative.numeric -or
            $negative.numeric.checks -ne 68 -or $negative.numeric.failures -lt 1 -or
            -not $negativeLog.Contains('FAIL channel[0] null binding') -or
            -not $negativeLog.Contains('FAIL channel[0] inactive')) {
            throw 'GUI animation omission control failed before its intended channel-initialization witnesses.'
        }
        $Receipt.regressions.negative_controls['gui-animation-omit-channel-construct'] = @{ status = 'expected_behavior_failure'; exit_code = $code; log = $logName }
        $Receipt.regressions.gui_animation_status = 'pass'
        $Receipt.regressions.status = 'partial_selected_fixtures_pass'
        Assert-CleanTrees
    }

    # Actual production event-order fixture; native startup and gameplay remain separate.
    if ($RunGuiLicenseRegressions) {
        $Receipt.regressions.status = 'running'
        $Receipt.regressions.gui_license_status = 'running'
        Remove-Item -LiteralPath Env:NoDefaultCurrentDirectoryInExePath -ErrorAction SilentlyContinue
        foreach ($relative in @('tests/run_gui_license_intro_handoff.py', 'tests/GuiLicenseIntroHandoff.cpp')) {
            $Receipt.regressions.inputs[$relative] = Get-FileRecord (Join-Path $SourceRoot $relative)
        }
        $licenseRunner = Join-Path $SourceRoot 'tests/run_gui_license_intro_handoff.py'
        $licenseRoot = Join-Path $ArtifactRoot 'gui-license-regressions'
        $positiveDir = Join-Path $licenseRoot 'positive'
        Invoke-Native py @('-3', '-B', $licenseRunner, '--output-dir', $positiveDir) 'regressions.log'
        $positive = Get-Content -Raw -LiteralPath (Join-Path $positiveDir 'result.json') | ConvertFrom-Json
        $positiveLog = Get-Content -Raw -LiteralPath (Join-Path $positiveDir 'run.stdout.txt')
        if ($positive.process_exit_code -ne 0 -or $null -eq $positive.numeric -or
            $positive.numeric.checks -ne 64 -or $positive.numeric.failures -ne 0 -or
            -not $positiveLog.Contains('GUI_LICENSE_INTRO_HANDOFF: 64 checks, 0 failures')) {
            throw 'GUI licence handoff positive fixture did not execute its expected64 numeric checks.'
        }
        $negativeDir = Join-Path $licenseRoot 'old-tail-cache'
        $logName = 'gui-license-negative-old-tail-cache.log'
        & py -3 -B $licenseRunner --old-tail-cache --output-dir $negativeDir 2>&1 |
            Tee-Object -FilePath (Join-Path $ArtifactRoot $logName) | Out-Host
        $code = $LASTEXITCODE
        $NativeCommands.Add(@{ command = 'py'; arguments = @('-3', '-B', $licenseRunner, '--old-tail-cache', '--output-dir', $negativeDir); exit_code = $code; expected_failure = $true })
        $negative = Get-Content -Raw -LiteralPath (Join-Path $negativeDir 'result.json') | ConvertFrom-Json
        $negativeLog = (Get-Content -Raw -LiteralPath (Join-Path $negativeDir 'run.stdout.txt')) +
            (Get-Content -Raw -LiteralPath (Join-Path $negativeDir 'run.stderr.txt'))
        if ($code -ne 1 -or $negative.process_exit_code -ne 1 -or $null -eq $negative.numeric -or
            $negative.numeric.checks -ne 64 -or $negative.numeric.failures -lt 1 -or
            -not $negativeLog.Contains('FAIL license profile bound before cache use')) {
            throw 'GUI licence handoff old-tail control failed before its intended profile-binding witness.'
        }
        $Receipt.regressions.negative_controls['gui-license-old-tail-cache'] = @{ status = 'expected_behavior_failure'; exit_code = $code; log = $logName }
        $Receipt.regressions.gui_license_status = 'pass'
        $Receipt.regressions.status = 'partial_selected_fixtures_pass'
        Assert-CleanTrees
    }

    # Independent production-body startup ownership checks. These do not prove boot.
    if ($RunStartupIORegressions) {
        $Receipt.regressions.status = 'running'
        $Receipt.regressions.startup_io_status = 'running'
        Remove-Item -LiteralPath Env:NoDefaultCurrentDirectoryInExePath -ErrorAction SilentlyContinue
        foreach ($relative in @('tests/run_startup_io_ownership.py', 'tests/StartupIOOwnership.cpp')) {
            $Receipt.regressions.inputs[$relative] = Get-FileRecord (Join-Path $SourceRoot $relative)
        }
        $startupRunner = Join-Path $SourceRoot 'tests/run_startup_io_ownership.py'
        $startupRoot = Join-Path $ArtifactRoot 'startup-io-regressions'
        $positiveDir = Join-Path $startupRoot 'positive'
        Invoke-Native py @('-3', '-B', $startupRunner, '--output-dir', $positiveDir) 'regressions.log'
        $positive = Get-Content -Raw -LiteralPath (Join-Path $positiveDir 'result.json') | ConvertFrom-Json
        $positiveLog = Get-Content -Raw -LiteralPath (Join-Path $positiveDir 'run.stdout.txt')
        if ($positive.process_exit_code -ne 0 -or $null -eq $positive.numeric -or
            $positive.numeric.checks -ne 62 -or $positive.numeric.failures -ne 0 -or
            -not $positiveLog.Contains('STARTUP_IO_OWNERSHIP: 62 checks, 0 failures')) {
            throw 'Startup IO positive fixture did not execute its expected62 numeric checks.'
        }
        $startupControls = @(
            @{ name = 'base-only-postworld'; flag = '--base-only-postworld'; witnesses = @('FAIL postworld bind queue owns inline backing', 'FAIL postworld mapping queue owns inline backing') },
            @{ name = 'legacy-gui-write-lock'; flag = '--legacy-gui-write-lock'; witnesses = @('ASSERT Already locked for write', 'FAIL initial-loading caller retains GameData locks') }
        )
        foreach ($control in $startupControls) {
            $controlDir = Join-Path $startupRoot $control.name
            $logName = 'startup-io-negative-' + $control.name + '.log'
            & py -3 -B $startupRunner $control.flag --output-dir $controlDir 2>&1 |
                Tee-Object -FilePath (Join-Path $ArtifactRoot $logName) | Out-Host
            $code = $LASTEXITCODE
            $NativeCommands.Add(@{ command = 'py'; arguments = @('-3', '-B', $startupRunner, $control.flag, '--output-dir', $controlDir); exit_code = $code; expected_failure = $true })
            $result = Get-Content -Raw -LiteralPath (Join-Path $controlDir 'result.json') | ConvertFrom-Json
            $log = (Get-Content -Raw -LiteralPath (Join-Path $controlDir 'run.stdout.txt')) +
                (Get-Content -Raw -LiteralPath (Join-Path $controlDir 'run.stderr.txt'))
            if ($code -ne 1 -or $result.process_exit_code -ne 1 -or $null -eq $result.numeric -or
                $result.numeric.checks -ne 62 -or $result.numeric.failures -lt 1) {
                throw "Startup IO control $($control.name) failed before numeric execution."
            }
            foreach ($witness in $control.witnesses) {
                if (-not $log.Contains($witness)) { throw "Startup IO control $($control.name) missed witness: $witness" }
            }
            $Receipt.regressions.negative_controls['startup-io-' + $control.name] = @{ status = 'expected_behavior_failure'; exit_code = $code; log = $logName }
        }
        $Receipt.regressions.startup_io_status = 'pass'
        $Receipt.regressions.status = 'partial_selected_fixtures_pass'
        Assert-CleanTrees
    }

    # Hosted bounded RWAC capacity fixture plus the original-source negative control.
    if ($RunRwacCommandCapacity) {
        $Receipt.regressions.status = 'running'
        $Receipt.regressions.rwac_command_capacity_status = 'running'
        if ($Jobs -ne 4 -or $Receipt.runner_label -cne 'windows-2022') {
            throw 'RWAC command-capacity fixture is limited to hosted Windows 2022 with four build jobs.'
        }

        $rwacRunner = Join-Path $SourceRoot 'tests/run_rwac_command_capacity.py'
        $rwacPinPath = Join-Path $SourceRoot 'tests/evidence/rwac_command_capacity/source_pins.json'
        $rwacOut = Join-Path $ArtifactRoot 'rwac-capacity'
        if ((Test-Path -LiteralPath $rwacOut -PathType Container) -and
            @(Get-ChildItem -LiteralPath $rwacOut -Force).Count -ne 0) {
            throw 'RWAC command-capacity output directory already contains a prior receipt.'
        }

        $expectedRwacSources = @(
            'src/GameShared/GameClasses/System/PC/CgsAudioOutputPC.cpp',
            'src/GameShared/GameClasses/System/PC/CgsDacOutputPC.cpp',
            'src/GameShared/GameClasses/System/PC/CgsRwacCommandTracePC.h',
            'src/GameSource/Sound/Module/BrnRootSoundModule.cpp',
            'vendor/renderware/src/rw/audio/core/PlugIn.cpp',
            'tests/RwacCommandCapacity.cpp',
            'tests/run_rwac_command_capacity.py',
            'tests/evidence/rwac_command_capacity/PlugIn_b823.cpp'
        )
        foreach ($relative in $expectedRwacSources) {
            $path = Join-Path $SourceRoot $relative
            if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
                throw "RWAC source-pinned input is missing: $relative"
            }
            $Receipt.regressions.inputs['rwac-capacity/' + $relative] = Get-FileRecord $path
        }
        foreach ($tool in @(
            @{ relative = 'tools/build/msvc_flags.txt'; path = (Join-Path $Root 'tools/build/msvc_flags.txt') },
            @{ relative = 'tools/build/msvc_includes.txt'; path = (Join-Path $Root 'tools/build/msvc_includes.txt') }
        )) {
            if (-not (Test-Path -LiteralPath $tool.path -PathType Leaf)) {
                throw "RWAC canonical build input is missing: $($tool.relative)"
            }
            $Receipt.regressions.inputs['parent/' + $tool.relative] = Get-FileRecord $tool.path
        }
        $Receipt.regressions.inputs['rwac-capacity/tests/evidence/rwac_command_capacity/source_pins.json'] =
            Get-FileRecord $rwacPinPath

        $pins = Get-Content -Raw -LiteralPath $rwacPinPath | ConvertFrom-Json
        if ($pins.schema_version -ne 2 -or $pins.normalization -cne 'crlf_to_lf_only' -or
            $pins.base_head -cne 'b823505348af025a784fc3ac171cfd0e7f0c1f99') {
            throw 'RWAC source pins are not the reviewed schema-2 LF-content contract.'
        }
        $pinNames = @($pins.files.PSObject.Properties | ForEach-Object { $_.Name } | Sort-Object -CaseSensitive)
        $expectedPinNames = @($expectedRwacSources | Sort-Object -CaseSensitive)
        if ($pinNames.Count -ne $expectedPinNames.Count -or
            [string]::Join("`n", $pinNames) -cne [string]::Join("`n", $expectedPinNames)) {
            throw 'RWAC pin manifest does not contain the exact eight production/test/control inputs.'
        }

        & py -3 -B $rwacRunner --workflow-root $Root --out $rwacOut --run 2>&1 |
            Tee-Object -FilePath (Join-Path $ArtifactRoot 'rwac-capacity.log') | Out-Host
        $rwacCode = $LASTEXITCODE
        $rwacArguments = @('-3', '-B', $rwacRunner, '--workflow-root', $Root,
                           '--out', $rwacOut, '--run')
        $NativeCommands.Add(@{ command = 'py'; arguments = $rwacArguments; exit_code = $rwacCode })
        if ($rwacCode -ne 0) { $NativeFailureCode = $rwacCode }

        $rwacResultPath = Join-Path $rwacOut 'result.json'
        if (-not (Test-Path -LiteralPath $rwacResultPath -PathType Leaf)) {
            throw 'RWAC runner did not retain result.json.'
        }
        $rwacResult = Get-Content -Raw -LiteralPath $rwacResultPath | ConvertFrom-Json
        if (-not [string]::Equals([IO.Path]::GetFullPath([string]$rwacResult.runner),
                [IO.Path]::GetFullPath($rwacRunner), [StringComparison]::OrdinalIgnoreCase) -or
            -not [string]::Equals([IO.Path]::GetFullPath([string]$rwacResult.source_checkout),
                [IO.Path]::GetFullPath($SourceRoot), [StringComparison]::OrdinalIgnoreCase) -or
            -not [string]::Equals([IO.Path]::GetFullPath([string]$rwacResult.workflow_root),
                [IO.Path]::GetFullPath($Root), [StringComparison]::OrdinalIgnoreCase)) {
            throw 'RWAC result does not identify this exact candidate source and workflow checkout.'
        }
        if ($rwacResult.sources.schema_version -ne 2 -or
            $rwacResult.sources.normalization -cne 'crlf_to_lf_only' -or
            $rwacResult.sources.base_head -cne $pins.base_head -or
            @($rwacResult.sources.mismatches).Count -ne 0 -or
            @($rwacResult.sources.files.PSObject.Properties).Count -ne 8) {
            throw 'RWAC source receipt reports a schema, normalization, coverage, or pin mismatch.'
        }
        $pinsFileRecord = Get-FileRecord $rwacPinPath
        if ($rwacResult.sources.pins_file.actual_raw_sha256 -cne $pinsFileRecord.sha256 -or
            $rwacResult.sources.pins_file.actual_raw_bytes -ne $pinsFileRecord.bytes) {
            throw 'RWAC result source-pins file record does not match the actual manifest bytes.'
        }
        foreach ($relative in $expectedRwacSources) {
            $pinProperty = $pins.files.PSObject.Properties[$relative]
            $sourceProperty = $rwacResult.sources.files.PSObject.Properties[$relative]
            if ($null -eq $pinProperty -or $null -eq $sourceProperty) {
                throw "RWAC source receipt is missing a pin row: $relative"
            }
            $pin = $pinProperty.Value
            $sourceRow = $sourceProperty.Value
            $actualSource = Get-FileRecord (Join-Path $SourceRoot $relative)
            if ($sourceRow.expected_lf_sha256 -cne $pin.expected_lf_sha256 -or
                $sourceRow.expected_lf_bytes -ne $pin.expected_lf_bytes -or
                $sourceRow.actual_lf_sha256 -cne $pin.expected_lf_sha256 -or
                $sourceRow.actual_lf_bytes -ne $pin.expected_lf_bytes -or
                $sourceRow.matches_lf_content -isnot [bool] -or -not $sourceRow.matches_lf_content -or
                $sourceRow.actual_raw_sha256 -cne $actualSource.sha256 -or
                $sourceRow.actual_raw_bytes -ne $actualSource.bytes) {
                throw "RWAC source-content or raw-byte receipt mismatch: $relative"
            }
        }
        $baselineIdentity = $rwacResult.sources.baseline_evidence
        if ($baselineIdentity.path -cne 'tests/evidence/rwac_command_capacity/PlugIn_b823.cpp' -or
            $baselineIdentity.original_git_lf_blob_sha1 -cne 'd1c98a807112e3052d8e9c8701cb3464e7619f7c' -or
            $baselineIdentity.original_git_lf_sha256 -cne 'e28e6fd1463b76ddc71d5dd51404787f225034014da99b67cdfdd1882a6a27c8' -or
            $baselineIdentity.original_git_lf_bytes -ne 8921 -or
            $baselineIdentity.matches_original_git_lf_blob -isnot [bool] -or
            -not $baselineIdentity.matches_original_git_lf_blob -or
            $baselineIdentity.actual_checkout_lf_git_blob_sha1 -cne $baselineIdentity.original_git_lf_blob_sha1) {
            throw 'RWAC original-source negative control does not match its retained original Git blob.'
        }
        foreach ($tool in @(
            @{ relative = 'tools/build/msvc_flags.txt'; path = (Join-Path $Root 'tools/build/msvc_flags.txt') },
            @{ relative = 'tools/build/msvc_includes.txt'; path = (Join-Path $Root 'tools/build/msvc_includes.txt') }
        )) {
            $toolProperty = $rwacResult.sources.canonical_tool_files.PSObject.Properties[$tool.relative]
            if ($null -eq $toolProperty) { throw "RWAC receipt omitted canonical build input: $($tool.relative)" }
            $actualTool = Get-FileRecord $tool.path
            if ($toolProperty.Value.actual_raw_sha256 -cne $actualTool.sha256 -or
                $toolProperty.Value.actual_raw_bytes -ne $actualTool.bytes) {
                throw "RWAC canonical build input hash mismatch: $($tool.relative)"
            }
        }
        if ($null -eq $rwacResult.toolchain -or
            @($rwacResult.toolchain.files.PSObject.Properties).Count -lt 2) {
            throw 'RWAC result omitted compiler/linker toolchain hashes.'
        }
        if ($rwacResult.toolchain.environment.VSCMD_ARG_TGT_ARCH -cne 'x64' -or
            $rwacResult.toolchain.environment.CL -or $rwacResult.toolchain.environment._CL_) {
            throw 'RWAC toolchain receipt does not identify an unmodified x64 MSVC environment.'
        }
        $rwacToolchainRecords = @{}
        foreach ($toolchainFile in $rwacResult.toolchain.files.PSObject.Properties) {
            $toolchainPath = [string]$toolchainFile.Name
            if (-not (Test-Path -LiteralPath $toolchainPath -PathType Leaf)) {
                throw "RWAC hashed toolchain file is missing: $toolchainPath"
            }
            $actualToolchainFile = Get-FileRecord $toolchainPath
            if ($toolchainFile.Value -cnotmatch '\A[0-9a-f]{64}\z' -or
                $toolchainFile.Value -cne $actualToolchainFile.sha256) {
                throw "RWAC compiler/linker input hash mismatch: $toolchainPath"
            }
            $rwacToolchainRecords[$toolchainPath] = $actualToolchainFile
        }

        if ($rwacCode -ne 0 -or $rwacResult.state -cne 'pass' -or
            $rwacResult.fixture_failures -ne 0 -or
            $rwacResult.intentional_failure_controls -ne 1 -or
            $rwacResult.intentional_failure_checks -ne 6 -or
            @($rwacResult.runs).Count -ne 2) {
            throw 'RWAC fixture result did not pass its positive and original-source control gates.'
        }
        $expectedNames = @('candidate', 'baseline_control')
        $expectedFailureLabels = @(
            'overflow stops before fifth record',
            'overflow leaves cursor untouched',
            'overflow leaves full backing and canaries untouched',
            'overflow has explicit synchronous record',
            'record contains actual pending/capacity/stride/highwater/frame',
            'record is bounded and complete'
        )
        $rwacRows = @()
        for ($index = 0; $index -lt 2; $index++) {
            $row = $rwacResult.runs[$index]
            $isBaseline = $index -eq 1
            if ($row.name -cne $expectedNames[$index] -or
                $row.intentional_failure_control -isnot [bool] -or
                $row.intentional_failure_control -ne $isBaseline -or
                $row.pass -isnot [bool] -or -not $row.pass -or
                $null -eq $row.checks -or $row.checks -le 0 -or
                $null -eq $row.failures -or
                $row.run.timed_out -isnot [bool] -or $row.run.timed_out -or
                $row.compile.timed_out -isnot [bool] -or $row.compile.timed_out -or
                $row.compile.exit_code -ne 0 -or
                $row.compile.timeout_seconds -ne 120 -or
                $row.run.timeout_seconds -ne 20 -or
                $row.compile.owned_job -isnot [bool] -or -not $row.compile.owned_job -or
                $row.run.owned_job -isnot [bool] -or -not $row.run.owned_job) {
                throw "RWAC $($expectedNames[$index]) run is missing a successful bounded execution receipt."
            }
            if ($row.compile.exit_code -ne 0) { throw "RWAC $($row.name) compilation failed." }
            $expectedRunExit = if ($isBaseline) { 1 } else { 0 }
            if ($row.run.exit_code -ne $expectedRunExit) {
                throw "RWAC $($row.name) executable returned an unexpected exit code."
            }
            foreach ($childName in @('compile', 'run')) {
                $child = $row.$childName
                $cleanup = $child.cleanup
                if ($cleanup.complete -isnot [bool] -or -not $cleanup.complete -or
                    $cleanup.cleanup_timeout_seconds -ne 5 -or
                    $cleanup.job_termination_requested -isnot [bool] -or
                    $cleanup.child_wait_complete -isnot [bool] -or -not $cleanup.child_wait_complete -or
                    $cleanup.job_handle_closed -isnot [bool] -or -not $cleanup.job_handle_closed -or
                    $cleanup.process_handles_closed -isnot [bool] -or -not $cleanup.process_handles_closed -or
                    $cleanup.stdio_handles_closed -isnot [bool] -or -not $cleanup.stdio_handles_closed -or
                    $cleanup.job_active_processes_after_cleanup -ne 0 -or
                    $child.transcript_hash_after_cleanup -isnot [bool] -or -not $child.transcript_hash_after_cleanup) {
                    throw "RWAC $($row.name) child cleanup or transcript-sealing receipt is incomplete."
                }
                $expectedLogName = $row.name + '_' + $childName + '.log'
                $expectedLogPath = Join-Path $rwacOut $expectedLogName
                if (-not [string]::Equals([IO.Path]::GetFullPath([string]$child.log),
                    [IO.Path]::GetFullPath($expectedLogPath), [StringComparison]::OrdinalIgnoreCase) -or
                    -not (Test-Path -LiteralPath $expectedLogPath -PathType Leaf)) {
                    throw "RWAC $($row.name) child transcript path is unexpected or missing."
                }
                $actualLog = Get-FileRecord $expectedLogPath
                if ($child.log_raw_sha256 -cnotmatch '\A[0-9a-f]{64}\z' -or
                    $child.log_raw_sha256 -cne $actualLog.sha256 -or
                    $child.log_sha256 -cne $actualLog.sha256 -or
                    $child.log_bytes -ne $actualLog.bytes) {
                    throw "RWAC $($row.name) transcript hash/size does not match bytes after cleanup."
                }
            }

            $exePath = Join-Path $rwacOut ($row.name + '.exe')
            if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
                throw "RWAC $($row.name) executable was not retained."
            }
            $actualExe = Get-FileRecord $exePath
            if ($row.fixture_exe_sha256 -cnotmatch '\A[0-9a-f]{64}\z' -or
                $row.fixture_exe_sha256 -cne $actualExe.sha256 -or
                $row.fixture_exe_bytes -ne $actualExe.bytes -or $actualExe.bytes -le 0) {
                throw "RWAC $($row.name) executable hash/size differs from its receipt."
            }

            $runLogPath = Join-Path $rwacOut ($row.name + '_run.log')
            $runTextForParsing = (Get-Content -Raw -LiteralPath $runLogPath).Replace(([string][char]13 + [char]10), [string][char]10)
            $summaries = [regex]::Matches($runTextForParsing, '(?m)^RWAC_CAPACITY checks=(\d+) failures=(\d+)$')
            if ($summaries.Count -ne 1 -or
                [int]$summaries[0].Groups[1].Value -ne $row.checks -or
                [int]$summaries[0].Groups[2].Value -ne $row.failures) {
                throw "RWAC $($row.name) result counts differ from its actual retained transcript."
            }
            $actualLabels = @([regex]::Matches($runTextForParsing, '(?m)^FAIL (.+)$') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -CaseSensitive)
            if ($isBaseline) {
                $expectedSortedLabels = @($expectedFailureLabels | Sort-Object -CaseSensitive)
                $rowLabels = @($row.failure_labels | ForEach-Object { [string]$_ } | Sort-Object -CaseSensitive)
                if ($row.checks -le 0 -or $row.failures -ne 6 -or
                    [string]::Join("`n", $rowLabels) -cne [string]::Join("`n", $expectedSortedLabels) -or
                    [string]::Join("`n", $actualLabels) -cne [string]::Join("`n", $expectedSortedLabels)) {
                    throw 'RWAC original-source control did not expose exactly its six expected failures.'
                }
            } else {
                if ($row.checks -le 0 -or $row.failures -ne 0 -or $actualLabels.Count -ne 0 -or
                    -not $runTextForParsing.Contains('TRACE_BURST ') -or
                    -not $runTextForParsing.Contains('TRACE_STARVATION ')) {
                    throw 'RWAC candidate did not produce positive checks, zero failures, and both trace witnesses.'
                }
            }
            $rwacRows += @{ name = $row.name; checks = $row.checks; failures = $row.failures;
                exit_code = $row.run.exit_code; executable = $actualExe;
                compile_log = $(Get-FileRecord (Join-Path $rwacOut ($row.name + '_compile.log')));
                run_log = $(Get-FileRecord $runLogPath) }
        }
        if ($rwacResult.fixture_checks -ne $rwacRows[0].checks -or
            $rwacResult.fixture_failures -ne 0 -or
            $rwacResult.intentional_failure_checks -ne $rwacRows[1].failures) {
            throw 'RWAC top-level numeric counts do not match the two actual executable transcripts.'
        }
        $Receipt.regressions.rwac_command_capacity = @{
            result = $(Get-FileRecord $rwacResultPath)
            runner_log = $(Get-FileRecord (Join-Path $ArtifactRoot 'rwac-capacity.log'))
            runs = $rwacResult.runs
            verified_runs = $rwacRows
            source_receipt = $rwacResult.sources
            toolchain = $rwacResult.toolchain
            verified_toolchain_files = $rwacToolchainRecords
        }
        Assert-CleanTrees
        $Receipt.regressions.rwac_command_capacity_status = 'pass'
        $Receipt.regressions.status = 'partial_selected_fixtures_pass'
    }

    # Hosted native PC keyboard provider contract; independent of the shipping exe link.
    if ($RunKeyboardUIContract) {
        if ($Jobs -ne 4 -or $Receipt.runner_label -cne 'windows-2022') {
            throw 'Keyboard UI contract is limited to hosted Windows 2022 with four build jobs.'
        }
        $Receipt.regressions.status = 'running'
        $Receipt.regressions.keyboard_ui_contract_status = 'running'
        Remove-Item -LiteralPath Env:NoDefaultCurrentDirectoryInExePath -ErrorAction SilentlyContinue

        $keyboardInputSpecs = @(
            @{ path = (Join-Path $SourceRoot 'tests/run_cgs_keyboard_pc_contract.py'); kind = 'runner' },
            @{ path = (Join-Path $SourceRoot 'tests/CgsKeyboardPCContract.cpp'); kind = 'source' },
            @{ path = (Join-Path $SourceRoot 'src/GameShared/GameClasses/System/PC/CgsXboxLivePC.cpp'); kind = 'source' },
            @{ path = (Join-Path $SourceRoot 'src/GameShared/GameClasses/System/X360/CgsXOverlappedX360.cpp'); kind = 'source' },
            @{ path = (Join-Path $SourceRoot 'tests/fxgs_common.py'); kind = 'toolchain' },
            @{ path = (Join-Path $Root 'tools/build/msvc_flags.txt'); kind = 'toolchain' },
            @{ path = (Join-Path $Root 'tools/build/msvc_includes.txt'); kind = 'toolchain' },
            @{ path = (Join-Path $Root 'tools/build/msvc_env.bat'); kind = 'toolchain' }
        )
        foreach ($keyboardInputSpec in $keyboardInputSpecs) {
            if ($keyboardInputSpec.path.StartsWith($SourceRoot, [StringComparison]::OrdinalIgnoreCase)) {
                $relative = $keyboardInputSpec.path.Substring($SourceRoot.Length).TrimStart([char[]]@([char]92, [char]47)).Replace('\', '/')
            } else {
                $relative = 'parent/' + $keyboardInputSpec.path.Substring($Root.Length).TrimStart([char[]]@([char]92, [char]47)).Replace('\', '/')
            }
            $Receipt.regressions.inputs[$relative] = Get-FileRecord $keyboardInputSpec.path
        }

        $keyboardRunner = Join-Path $SourceRoot 'tests/run_cgs_keyboard_pc_contract.py'
        $keyboardRoot = Join-Path $ArtifactRoot 'keyboard-ui-contract'
        $keyboardPositive = Join-Path $keyboardRoot 'positive'
        if ((Test-Path -LiteralPath $keyboardPositive -PathType Container) -and
            @(Get-ChildItem -LiteralPath $keyboardPositive -Force).Count -ne 0) {
            throw 'Keyboard UI contract output directory already contains a prior receipt.'
        }
        & py -3 -B $keyboardRunner --output-dir $keyboardPositive 2>&1 |
            Tee-Object -FilePath (Join-Path $ArtifactRoot 'keyboard-ui-contract.log') | Out-Host
        $keyboardCode = $LASTEXITCODE
        $keyboardArguments = @('-3', '-B', $keyboardRunner, '--output-dir', $keyboardPositive)
        $NativeCommands.Add(@{ command = 'py'; arguments = $keyboardArguments; exit_code = $keyboardCode })
        if ($keyboardCode -ne 0) { $NativeFailureCode = $keyboardCode }

        $keyboardResultPath = Join-Path $keyboardPositive 'result.json'
        if (-not (Test-Path -LiteralPath $keyboardResultPath -PathType Leaf)) {
            throw 'Keyboard UI runner did not write result.json.'
        }
        $keyboardResult = Get-Content -Raw -LiteralPath $keyboardResultPath | ConvertFrom-Json
        $keyboardStdoutPath = Join-Path $keyboardPositive 'run.stdout.txt'
        $keyboardStderrPath = Join-Path $keyboardPositive 'run.stderr.txt'
        if (-not (Test-Path -LiteralPath $keyboardStdoutPath -PathType Leaf) -or
            -not (Test-Path -LiteralPath $keyboardStderrPath -PathType Leaf)) {
            throw 'Keyboard UI runner did not retain both run transcripts.'
        }
        $keyboardOutput = (Get-Content -Raw -LiteralPath $keyboardStdoutPath) +
            (Get-Content -Raw -LiteralPath $keyboardStderrPath)
        if ($keyboardResult.ui_unavailable -isnot [bool] -or $keyboardResult.ui_unavailable -or
            $keyboardOutput.Contains('UI_UNAVAILABLE')) {
            throw 'Keyboard UI contract reported UI_UNAVAILABLE.'
        }
        if ($keyboardCode -ne 0 -or $keyboardResult.status -cne 'pass' -or
            $keyboardResult.process_exit_code -ne 0 -or $keyboardResult.build_exit_code -ne 0 -or
            $keyboardResult.run_exit_code -ne 0 -or $keyboardResult.run_timed_out -isnot [bool] -or
            $keyboardResult.run_timed_out -or $keyboardResult.run_timeout_seconds -ne 30 -or
            $keyboardResult.numeric_expected -ne 157 -or $null -eq $keyboardResult.numeric -or
            $keyboardResult.numeric.checks -ne 157 -or $keyboardResult.numeric.failures -ne 0 -or
            @($keyboardResult.failures).Count -ne 0 -or
            $keyboardOutput -notmatch 'CgsKeyboardPCContract:\s+157 checks, 0 failures') {
            throw 'Keyboard UI contract did not produce its bounded 157-check, zero-failure result.'
        }

        $keyboardExecutablePath = Join-Path $keyboardPositive 'regression.exe'
        if ($null -eq $keyboardResult.executable -or
            -not (Test-Path -LiteralPath $keyboardExecutablePath -PathType Leaf)) {
            throw 'Keyboard UI result is missing its actual fixture executable.'
        }
        $keyboardExecutable = Get-FileRecord $keyboardExecutablePath
        $reportedExecutablePath = [IO.Path]::GetFullPath([string]$keyboardResult.executable.path)
        $expectedExecutablePath = [IO.Path]::GetFullPath($keyboardExecutablePath)
        if (-not [string]::Equals($reportedExecutablePath, $expectedExecutablePath, [StringComparison]::OrdinalIgnoreCase) -or
            $keyboardResult.executable.bytes -ne $keyboardExecutable.bytes -or
            $keyboardResult.executable.sha256 -cnotmatch '\A[0-9a-f]{64}\z' -or
            $keyboardResult.executable.sha256 -cne $keyboardExecutable.sha256 -or
            $keyboardExecutable.bytes -le 0) {
            throw 'Keyboard UI receipt does not match the actual fixture executable SHA-256 and size.'
        }

        $keyboardInputs = @($keyboardResult.input_hashes)
        $expectedKeyboardInputCount = $keyboardInputSpecs.Count + 1
        if ($keyboardInputs.Count -ne $expectedKeyboardInputCount) {
            throw 'Keyboard UI receipt is missing runner, source, toolchain, or generated build-script hashes.'
        }
        $allKeyboardInputSpecs = @($keyboardInputSpecs) + @(
            @{ path = (Join-Path $keyboardPositive 'build.cmd'); kind = 'generated_build_script' }
        )
        foreach ($keyboardInputSpec in $allKeyboardInputSpecs) {
            if (-not (Test-Path -LiteralPath $keyboardInputSpec.path -PathType Leaf)) {
                throw "Keyboard UI hashed input is missing: $($keyboardInputSpec.path)"
            }
            $expectedPath = [IO.Path]::GetFullPath($keyboardInputSpec.path)
            $matchingRecords = @($keyboardInputs | Where-Object { $_.path } | Where-Object {
                [string]::Equals([IO.Path]::GetFullPath([string]$_.path), $expectedPath,
                    [StringComparison]::OrdinalIgnoreCase)
            })
            if ($matchingRecords.Count -ne 1) {
                throw "Keyboard UI receipt has a missing or duplicate input hash: $($keyboardInputSpec.path)"
            }
            $actualInput = Get-FileRecord $keyboardInputSpec.path
            $reportedInput = $matchingRecords[0]
            if ($reportedInput.kind -cne $keyboardInputSpec.kind -or
                $reportedInput.bytes -ne $actualInput.bytes -or
                $reportedInput.sha256 -cnotmatch '\A[0-9a-f]{64}\z' -or
                $reportedInput.sha256 -cne $actualInput.sha256) {
                throw "Keyboard UI runner/toolchain input hash mismatch: $($keyboardInputSpec.path)"
            }
        }

        foreach ($retained in @(
            @{ name = 'build_stdout'; file = 'build.stdout.txt' },
            @{ name = 'build_stderr'; file = 'build.stderr.txt' },
            @{ name = 'run_stdout'; file = 'run.stdout.txt' },
            @{ name = 'run_stderr'; file = 'run.stderr.txt' },
            @{ name = 'build_script'; file = 'build.cmd' }
        )) {
            $retainedName = [string]$retained.name
            $retainedPath = $keyboardResult.retained_outputs.PSObject.Properties[$retainedName].Value
            if ($retainedPath -cne $retained.file -or
                -not (Test-Path -LiteralPath (Join-Path $keyboardPositive $retained.file) -PathType Leaf)) {
                throw "Keyboard UI runner did not retain its $retainedName output."
            }
        }

        $Receipt.regressions.keyboard_ui_contract = @{
            result = Get-FileRecord $keyboardResultPath
            executable = @{ path = $expectedExecutablePath; bytes = $keyboardExecutable.bytes; sha256 = $keyboardExecutable.sha256 }
            numeric = $keyboardResult.numeric
            numeric_expected = $keyboardResult.numeric_expected
            input_hashes = $keyboardInputs
            process_exit_code = $keyboardResult.process_exit_code
            build_exit_code = $keyboardResult.build_exit_code
            run_exit_code = $keyboardResult.run_exit_code
            run_timeout_seconds = $keyboardResult.run_timeout_seconds
            run_timed_out = $keyboardResult.run_timed_out
            ui_unavailable = $keyboardResult.ui_unavailable
        }
        $Receipt.regressions.keyboard_ui_contract_status = 'pass'
        $Receipt.regressions.status = 'partial_selected_fixtures_pass'
        Assert-CleanTrees
    }
    # Proven publisher prerequisites: release FFmpeg, NuGet XAudio2, vendored Lua.
    $ffmpeg = Join-Path $SourceRoot 'vendor/ffmpeg-build'
    $archive = Join-Path $WorkRoot 'ffmpeg-build.zip'
    Invoke-Native gh @('release', 'download', 'ffmpeg-prebuilt', '--repo', 'BurnoutDecomp/FFmpeg-Xenia-new', '-p', 'ffmpeg-build.zip', '-O', $archive) 'dependencies.log'
    Expand-Archive -LiteralPath $archive -DestinationPath $ffmpeg -Force
    if (-not (Test-Path -LiteralPath (Join-Path $ffmpeg 'bin/avcodec.lib'))) { throw 'Prebuilt FFmpeg import library is missing.' }
    Invoke-Native cmd.exe @('/d', '/c', ('"{0}"' -f (Join-Path $Root 'tools/build/fetch_xaudio2_redist.bat'))) 'dependencies.log'
    Invoke-Native python @((Join-Path $Root 'tools/build/fetch_sdl3.py')) 'dependencies.log'
    $lua = Join-Path $SourceRoot 'vendor/lua/lua515.lib'
    if (-not (Test-Path -LiteralPath $lua)) {
        Invoke-Native cmd.exe @('/d', '/c', ('"{0}"' -f (Join-Path $Root 'tools/build/build_lua.bat'))) 'lua.log'
    }
    $Receipt.dependencies = @{
        ffmpeg_release = 'BurnoutDecomp/FFmpeg-Xenia-new/ffmpeg-prebuilt'
        archive = Get-FileRecord $archive; lua = Get-FileRecord $lua
        xaudio2_version = (Get-Content -LiteralPath (Join-Path $SourceRoot 'vendor/xaudio2redist/VERSION.txt') -Raw).Trim()
        xaudio2_header = Get-FileRecord (Join-Path $SourceRoot 'vendor/xaudio2redist/include/xaudio2Redist.h')
        sdl3_version = (Get-Content -LiteralPath (Join-Path $SourceRoot 'vendor/sdl3/VERSION.txt') -Raw).Trim()
        sdl3_header = Get-FileRecord (Join-Path $SourceRoot 'vendor/sdl3/include/SDL3/SDL.h')
    }
    # Match the shipping bat's runtime staging inputs, including SDL's license.
    # A playable install must have the matching DLLs.
    $ffmpegDlls = @(Get-ChildItem -LiteralPath (Join-Path $ffmpeg 'bin') -Filter '*.dll' -File)
    if ($ffmpegDlls.Count -eq 0) { throw 'Prebuilt FFmpeg runtime DLLs are missing.' }
    $runtimeFiles = @($ffmpegDlls) + @(Get-Item -LiteralPath (Join-Path $SourceRoot 'vendor/xaudio2redist/bin/x64/xaudio2_9redist.dll')) +
        @(Get-Item -LiteralPath (Join-Path $SourceRoot 'vendor/sdl3/lib/x64/SDL3.dll'))
    foreach ($file in $runtimeFiles) {
        if ($RuntimeOutputs.ContainsKey($file.Name)) { throw "Duplicate runtime name: $($file.Name)" }
        $RuntimeOutputs[$file.Name] = Get-FileRecord $file.FullName
    }
    $RuntimeOutputs['SDL3-LICENSE.txt'] = Get-FileRecord (Join-Path $SourceRoot 'vendor/sdl3/LICENSE.txt')
    $Receipt.expected_runtime_outputs = $RuntimeOutputs
    Assert-CleanTrees

    # Source-body fixtures need their own dependencies, not a successful shipping
    # link. Retain their results independently of native platform-provider failures.
    if ($RunRegressions -or $RunAptLifetime -or $RunResourceRegressions) {
        $Receipt.regressions.status = 'running'
        $Receipt.regressions.remaining_status = 'running'
        $Receipt.regressions.coverage = 'Selected production-body fixtures with IO/heap doubles; callback wiring is source-only. No game or end-to-end parity claim.'
        foreach ($relative in @('tests/run_profile_delivery.py', 'tests/ProfileDelivery.cpp',
                                'tests/run_fxgs2_gui_iface.py', 'tests/FxGs2GuiIface.cpp',
                                'tests/fxgs_common.py')) {
            $Receipt.regressions.inputs[$relative] = Get-FileRecord (Join-Path $SourceRoot $relative)
        }
        # The fixture executables live in temporary directories and must resolve
        # their own current directory. Nothing invokes the game or window input.
        Remove-Item -LiteralPath Env:NoDefaultCurrentDirectoryInExePath -ErrorAction SilentlyContinue
        if ($RunRegressions) {
            foreach ($runner in @('tests/run_profile_delivery.py', 'tests/run_fxgs2_gui_iface.py')) {
                Invoke-Native py @('-3', '-B', (Join-Path $SourceRoot $runner)) 'regressions.log'
            }
        }
        if ($RunAptLifetime) {
            foreach ($relative in @('tests/run_pc_bundle_ownership.py', 'tests/PCBundleOwnership.cpp')) {
                $Receipt.regressions.inputs[$relative] = Get-FileRecord (Join-Path $SourceRoot $relative)
            }
            $aptRunner = Join-Path $SourceRoot 'tests/run_pc_bundle_ownership.py'
            Invoke-Native py @('-3', '-B', $aptRunner) 'regressions.log'
            $controls = @(
                @{ flag = '--omit-apt-retain'; witness = 'FAIL\s+(Apt pin holds every member|logical unload preserves)' },
                @{ flag = '--require-new-apt-resources'; witness = 'FAIL[^\r\n]*(reload|lead|acquire)' }
            )
            $helpArguments = @('-3', '-B', $aptRunner, '--help')
            $aptHelp = & py @helpArguments 2>&1
            $helpCode = $LASTEXITCODE
            $NativeCommands.Add(@{ command = 'py'; arguments = $helpArguments; exit_code = $helpCode })
            if ($helpCode -ne 0) { throw 'APT runner capability check failed.' }
            if (($aptHelp -join "`n") -match '--legacy-free-state-offset') {
                $Receipt.regressions.inputs['tests/pc_apt_callback_fixture.h'] = Get-FileRecord (Join-Path $SourceRoot 'tests/pc_apt_callback_fixture.h')
                $controls += @{ flag = '--legacy-free-state-offset'; witness = 'FAIL[^\r\n]*(FreeAnimation|state|offset|const)' }
            }
            foreach ($control in $controls) {
                $logName = 'apt-negative' + $control.flag + '.log'
                $logPath = Join-Path $ArtifactRoot $logName
                & py -3 -B $aptRunner $control.flag 2>&1 | Tee-Object -FilePath $logPath | Out-Host
                $controlCode = $LASTEXITCODE
                $NativeCommands.Add(@{ command = 'py'; arguments = @('-3', '-B', $aptRunner, $control.flag); exit_code = $controlCode; expected_failure = $true })
                $controlLog = Get-Content -Raw -LiteralPath $logPath
                if ($controlCode -eq 0 -or $controlLog -notmatch $control.witness) {
                    throw "APT negative control $($control.flag) did not expose its intended runtime ownership/GUI failure."
                }
                $Receipt.regressions.negative_controls[$control.flag] = @{ status = 'expected_behavior_failure'; exit_code = $controlCode; log = $logName }
            }
        }
        if ($RunResourceRegressions) {
            foreach ($relative in @('tests/run_pool_create_protocol.py', 'tests/PoolCreateProtocol.cpp',
                                    'tests/run_pc_resource_shuttle.py', 'tests/PCResourceShuttle.cpp',
                                    'tests/run_game_data_pool_hierarchy.py', 'tests/GameDataPoolHierarchy.cpp',
                                    'tests/run_pc_gui_pool_acquire.py', 'tests/PCGuiPoolAcquire.cpp')) {
                $Receipt.regressions.inputs[$relative] = Get-FileRecord (Join-Path $SourceRoot $relative)
            }
            $resourceRoot = Join-Path $ArtifactRoot 'resource-regressions'
            $poolRunner = Join-Path $SourceRoot 'tests/run_pool_create_protocol.py'
            $poolPositive = Join-Path $resourceRoot 'pool-positive'
            Invoke-Native py @('-3', '-B', $poolRunner, '--output-dir', $poolPositive) 'regressions.log'
            $poolResult = Get-Content -Raw -LiteralPath (Join-Path $poolPositive 'result.json') | ConvertFrom-Json
            if (@($poolResult.results).Count -ne 2) { throw 'Pool fixture must execute both protocol and layout modes.' }
            foreach ($mode in @('protocol', 'layout')) {
                $modeResult = @($poolResult.results | Where-Object mode -eq $mode)
                $modeLog = Get-Content -Raw -LiteralPath (Join-Path $poolPositive "$mode/run.stdout.txt")
                if ($modeResult.Count -ne 1 -or -not $modeResult[0].compiled -or $modeResult[0].exit_code -ne 0 -or
                    $modeLog -notmatch 'PoolCreateProtocol:\s+[1-9][0-9]* checks, 0 failures; mode=') {
                    throw "Pool positive fixture did not execute successfully in $mode mode."
                }
            }
            $resourceFixtures = @(
                @{ runner = 'tests/run_pc_resource_shuttle.py'; tag = 'PCResourceShuttle'; name = 'shuttle'; checks = 14 },
                @{ runner = 'tests/run_pc_gui_pool_acquire.py'; tag = 'PCGuiPoolAcquire'; name = 'gui-acquire'; checks = 27 }
            )
            foreach ($fixture in $resourceFixtures) {
                $fixtureDir = Join-Path $resourceRoot $fixture.name
                Invoke-Native py @('-3', '-B', (Join-Path $SourceRoot $fixture.runner), '--output-dir', $fixtureDir) 'regressions.log'
                $fixtureResult = Get-Content -Raw -LiteralPath (Join-Path $fixtureDir 'result.json') | ConvertFrom-Json
                $fixtureLog = Get-Content -Raw -LiteralPath (Join-Path $fixtureDir 'run.stdout.txt')
                $fixtureWitness = [regex]::Escape($fixture.tag) + ':\s+' + $fixture.checks + ' checks, 0 failures'
                if ($fixtureResult.process_exit_code -ne 0 -or $null -eq $fixtureResult.numeric -or
                    $fixtureResult.numeric.checks -ne $fixture.checks -or $fixtureResult.numeric.failures -ne 0 -or
                    $fixtureLog -notmatch $fixtureWitness) {
                    throw "Resource fixture $($fixture.name) did not execute its expected positive numeric checks."
                }
            }
            Invoke-Native py @('-3', '-B', (Join-Path $SourceRoot 'tests/run_game_data_pool_hierarchy.py'),
                '--output-dir', (Join-Path $resourceRoot 'game-data-hierarchy')) 'regressions.log'
            $poolControls = @(
                @{ name = 'tag10'; mode = 'protocol'; witness = 'FAIL[^\r\n]*tag10' },
                @{ name = 'event-sentinel'; mode = 'protocol'; witness = 'FAIL[^\r\n]*(tag.?-1|unacquire|sentinel)' },
                @{ name = 'batch-count'; mode = 'layout'; witness = 'FAIL[^\r\n]*(Entry carve|guard|batch)' },
                @{ name = 'shared-buffer'; mode = 'protocol'; witness = 'FAIL[^\r\n]*(formatting buffers|isolated message|shared buffer)' }
            )
            foreach ($control in $poolControls) {
                $controlDir = Join-Path $resourceRoot ('pool-negative-' + $control.name)
                $controlLogName = 'pool-negative-' + $control.name + '.log'
                & py -3 -B $poolRunner --negative $control.name --output-dir $controlDir 2>&1 |
                    Tee-Object -FilePath (Join-Path $ArtifactRoot $controlLogName) | Out-Host
                $controlCode = $LASTEXITCODE
                $NativeCommands.Add(@{ command = 'py'; arguments = @('-3', '-B', $poolRunner, '--negative', $control.name, '--output-dir', $controlDir); exit_code = $controlCode; expected_failure = $true })
                $controlResult = Get-Content -Raw -LiteralPath (Join-Path $controlDir 'result.json') | ConvertFrom-Json
                if (@($controlResult.results).Count -ne 1 -or -not $controlResult.results[0].compiled) {
                    throw "Pool negative control $($control.name) failed before behavioral execution."
                }
                $controlLog = Get-Content -Raw -LiteralPath (Join-Path $controlDir ($control.mode + '/run.stdout.txt'))
                if ($controlCode -eq 0 -or $controlResult.results[0].exit_code -eq 0 -or
                    $controlLog -notmatch 'PoolCreateProtocol:\s+[1-9][0-9]* checks, [1-9][0-9]* failures; mode=' -or
                    $controlLog -notmatch $control.witness) {
                    throw "Pool negative control $($control.name) did not expose its intended behavior failure."
                }
                $Receipt.regressions.negative_controls['pool-' + $control.name] = @{ status = 'expected_behavior_failure'; exit_code = $controlCode; log = $controlLogName }
            }
        }

        Assert-CleanTrees
        $Receipt.regressions.remaining_status = 'pass'
        $Receipt.regressions.status = 'partial_selected_fixtures_pass'
    }

    # Never accept a cached or prior exe/map/stamp as proof of this link.
    foreach ($name in $OutputNames) {
        $path = Join-Path $GameOut $name
        if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
    }
    $env:BRN_EXE_JOBS = [string]$Jobs
    $env:BRN_EXE_HASH_DEPS = '1'
    Invoke-Native cmd.exe @('/d', '/c', ('"{0}"' -f (Join-Path $Root 'tools/build/build_game_exe.bat'))) 'build.log'
    foreach ($name in $OutputNames) {
        $path = Join-Path $GameOut $name
        if (-not (Test-Path -LiteralPath $path) -or (Get-Item -LiteralPath $path).Length -eq 0) { throw "Build output is missing or empty: $name" }
    }
    foreach ($name in $RuntimeOutputs.Keys) {
        $path = Join-Path $GameOut $name
        if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or
            (Get-FileRecord $path).sha256 -ne $RuntimeOutputs[$name].sha256) {
            throw "Staged runtime DLL does not match its dependency: $name"
        }
    }
    $cgsmap = Join-Path $GameOut 'Burnout_PC.cgsmap'
    $reader = [IO.BinaryReader]::new([IO.File]::OpenRead($cgsmap))
    try {
        $count = $reader.ReadUInt32(); $offset = $reader.ReadUInt32()
        $base = $reader.ReadUInt32(); $version = $reader.ReadUInt32()
        if ($count -eq 0 -or $offset -ne 16 -or $base -ne 0 -or $version -ne 1 -or $reader.BaseStream.Length -ne (16L + 128L * $count)) {
            throw 'Cgsmap is empty or incomplete.'
        }
    } finally { $reader.Dispose() }
    $provenance = Get-Content -LiteralPath (Join-Path $GameOut 'Burnout_PC.exe.provenance.json') -Raw | ConvertFrom-Json -AsHashtable
    $exe = Get-FileRecord (Join-Path $GameOut 'Burnout_PC.exe')
    if ($provenance.b5_head -ne $B5Commit -or $provenance.parent_head -ne $WorkflowSha -or
        $provenance.exe_sha256 -ne $exe.sha256 -or $provenance.b5_dirty -isnot [bool] -or $provenance.b5_dirty -ne $false -or
        $provenance.parent_dirty -isnot [bool] -or $provenance.parent_dirty -ne $Receipt.gitlink_overridden) {
        throw 'Provenance does not match the candidate, workflow, clean source and actual exe.'
    }
    Assert-CleanTrees
    if ($Receipt.regressions.requested) { $Receipt.regressions.status = 'pass' }
    $Receipt.validated = $true
    $ExitCode = 0
} catch {
    if ($Receipt.regressions.gui_menu_music_wire_status -eq 'running') {
        $Receipt.regressions.gui_menu_music_wire_status = 'fail'
        $Receipt.regressions.gui_menu_music_wire.status = 'fail'
    }
    if ($Receipt.regressions.online_save_route_status -eq 'running') {
        $Receipt.regressions.online_save_route_status = 'fail'
        $Receipt.regressions.online_save_route.status = 'fail'
    }
    if ($Receipt.regressions.system_user_profile_status -eq 'running') {
        $Receipt.regressions.system_user_profile_status = 'fail'
        if ($Receipt.regressions.system_user_profile.Contains('status') -and
            $Receipt.regressions.system_user_profile.status -eq 'running') {
            $Receipt.regressions.system_user_profile.status = 'fail'
        }
    }
    if ($Receipt.regressions.traffic_flowtype_override_status -eq 'running') {
        $Receipt.regressions.traffic_flowtype_override_status = 'fail'
        if ($Receipt.regressions.traffic_flowtype_override.Contains('status')) { $Receipt.regressions.traffic_flowtype_override.status = 'fail' }
    }
    if ($Receipt.regressions.gui_io_status -eq 'running') { $Receipt.regressions.gui_io_status = 'fail' }
    if ($Receipt.regressions.gui_animation_status -eq 'running') { $Receipt.regressions.gui_animation_status = 'fail' }
    if ($Receipt.regressions.startup_io_status -eq 'running') { $Receipt.regressions.startup_io_status = 'fail' }
    if ($Receipt.regressions.gui_license_status -eq 'running') { $Receipt.regressions.gui_license_status = 'fail' }
    if ($Receipt.regressions.keyboard_ui_contract_status -eq 'running') { $Receipt.regressions.keyboard_ui_contract_status = 'fail' }
    if ($Receipt.regressions.rwac_command_capacity_status -eq 'running') { $Receipt.regressions.rwac_command_capacity_status = 'fail' }
    if ($Receipt.regressions.hud_status -eq 'running') { $Receipt.regressions.hud_status = 'fail' }
    if ($Receipt.regressions.remaining_status -eq 'running') { $Receipt.regressions.remaining_status = 'fail' }
    if ($Receipt.regressions.status -eq 'running') { $Receipt.regressions.status = 'fail' }
    if ($NativeFailureCode -ne 0) { $ExitCode = $NativeFailureCode }
    $Receipt.failure = $_.Exception.Message
    Write-Warning $Receipt.failure
} finally {
    $Receipt.native_commands = $NativeCommands.ToArray()
    $Receipt.exit_code = $ExitCode
    $Receipt.finished_utc = [DateTime]::UtcNow.ToString('o')
    $Receipt.outputs = @{}
    foreach ($name in (@($OutputNames) + @($RuntimeOutputs.Keys))) {
        $path = Join-Path $GameOut $name
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            Copy-Item -LiteralPath $path -Destination (Join-Path $ArtifactRoot $name)
            $Receipt.outputs[$name] = Get-FileRecord $path
        }
    }
    $Receipt | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $ArtifactRoot 'input-receipt.json') -Encoding utf8
    Pop-Location
}
exit $ExitCode
