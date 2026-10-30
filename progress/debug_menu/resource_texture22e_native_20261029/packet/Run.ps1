param(
  [Parameter(Mandatory=$true)][ValidateSet('resource_windows','resource_stats_allocator')][string]$Suite,
  [Parameter(Mandatory=$true)][string]$RunName,
  [switch]$PreflightOnly
)
$ErrorActionPreference='Stop'
function Get-ResourceStorageBudget([long]$AvailableBytes,[long]$DataBytesToCopy,[int]$FrameCount,[double]$MinFreeGiB,[long]$FrameReserveBytesPerFrame,[long]$SidecarReserveBytes){
  if($AvailableBytes -lt 0 -or $DataBytesToCopy -lt 0 -or $FrameCount -lt 0 -or $MinFreeGiB -lt 0 -or $FrameReserveBytesPerFrame -lt 0 -or $SidecarReserveBytes -lt 0){throw 'Resource storage budget arguments cannot be negative.'}
  $minFreeBytes=[long][Math]::Ceiling($MinFreeGiB * 1GB)
  $frameBytes=[long]$FrameCount * [long]$FrameReserveBytesPerFrame
  $required=[long]$minFreeBytes + [long]$DataBytesToCopy + [long]$frameBytes + [long]$SidecarReserveBytes
  return [pscustomobject]@{available_bytes=[long]$AvailableBytes;min_free_gib=[double]$MinFreeGiB;min_free_bytes=$minFreeBytes;data_copy_bytes=[long]$DataBytesToCopy;frame_count=[int]$FrameCount;frame_reserve_bytes_per_frame=[long]$FrameReserveBytesPerFrame;frame_reserve_bytes=$frameBytes;sidecar_reserve_bytes=[long]$SidecarReserveBytes;required_bytes=$required;headroom_bytes=([long]$AvailableBytes-$required);pass=([long]$AvailableBytes -ge $required)}
}
function Assert-ResourceStorageBudget([string]$Path,[long]$DataBytesToCopy,[int]$FrameCount,[double]$MinFreeGiB,[long]$FrameReserveBytesPerFrame,[long]$SidecarReserveBytes,[string]$Phase){
  $full=[IO.Path]::GetFullPath($Path)
  $driveRoot=[IO.Path]::GetPathRoot($full)
  $drive=[IO.DriveInfo]::new($driveRoot)
  if(!$drive.IsReady){throw "Resource output volume is not ready: $driveRoot"}
  $budget=Get-ResourceStorageBudget -AvailableBytes ([long]$drive.AvailableFreeSpace) -DataBytesToCopy $DataBytesToCopy -FrameCount $FrameCount -MinFreeGiB $MinFreeGiB -FrameReserveBytesPerFrame $FrameReserveBytesPerFrame -SidecarReserveBytes $SidecarReserveBytes
  $record=[pscustomobject]@{phase=$Phase;path=$full;drive_root=$driveRoot;measured_utc=[DateTime]::UtcNow.ToString('o');available_bytes=$budget.available_bytes;min_free_gib=$budget.min_free_gib;min_free_bytes=$budget.min_free_bytes;data_copy_bytes=$budget.data_copy_bytes;frame_count=$budget.frame_count;frame_reserve_bytes_per_frame=$budget.frame_reserve_bytes_per_frame;frame_reserve_bytes=$budget.frame_reserve_bytes;sidecar_reserve_bytes=$budget.sidecar_reserve_bytes;required_bytes=$budget.required_bytes;headroom_bytes=$budget.headroom_bytes;pass=$budget.pass}
  if(!$record.pass){throw "Resource storage budget failed at $Phase on ${driveRoot}: available=$($record.available_bytes) required=$($record.required_bytes) min_free_gib=$MinFreeGiB data_copy_bytes=$DataBytesToCopy frames=$FrameCount."}
  return $record
}
function Copy-FrozenResourceData([string]$SourceRoot,[string]$DestinationRoot,[object]$Manifest){
  $tempReceipt=Join-Path (Split-Path -Parent $DestinationRoot) 'READONLY_LINK_COPY.json'
  $null=& python (Join-Path $PSScriptRoot 'ReadonlyResourcePool.py') link --root $DestinationRoot --output $tempReceipt
  if($LASTEXITCODE -ne 0){throw 'Readonly Resource hardlink staging failed.'}
  $linked=Get-Content -LiteralPath $tempReceipt -Raw|ConvertFrom-Json
  $linked.excluded_runtime_files=@($Manifest.selection.excluded_runtime_files)
  return $linked
}
$repoRoot='D:\Reverse\BP-Decomp_Workflow'
. (Join-Path $PSScriptRoot 'TextureNormalProtection.ps1')
$packetRoot=Split-Path -Parent $PSCommandPath
$privateTemp='C:\Users\adri1\Documents\Codex\resource_texture_source22e_62144_20261029\transient'
New-Item -ItemType Directory -Path $privateTemp -Force|Out-Null
$env:TEMP=$privateTemp;$env:TMP=$privateTemp;$env:PYTHONDONTWRITEBYTECODE='1'

$suiteRoot=Join-Path $packetRoot ('suites\'+$Suite)
$slot=if($Suite -eq 'resource_windows'){62144}else{62145}
$casePath=Join-Path $suiteRoot $(if($Suite -eq 'resource_windows'){'Case_ResourceWindows.ps1'}else{'Case_ResourceStatsAllocator.ps1'})
$case=& $casePath
if($case -isnot [System.Collections.IDictionary]){throw 'Selected Resource case did not return the expected hashtable.'}
$frameMatch=[regex]::Match([string]$case.DiagEnv,'(?:^|,)BRN_FRAME_DUMP_MAX=(?<count>\d+)(?:,|$)')
if(!$frameMatch.Success){throw 'Selected Resource case does not bind an exact BRN_FRAME_DUMP_MAX frame count.'}
$caseFrameCount=[int]$frameMatch.Groups['count'].Value
$caseMinFreeGiB=[double]$case.Run.MinFreeGB
if($caseFrameCount -le 0 -or $caseMinFreeGiB -le 0){throw 'Selected Resource case has invalid frame-count/free-space policy.'}
$frameReserveBytesPerFrame=[long]8388608
$sidecarReserveBytes=[long]100663296
if($RunName -notmatch ('^'+[regex]::Escape($Suite)+'_[0-9]{8}_[0-9]{6}$')){throw 'RunName must be <suite>_yyyyMMdd_HHmmss.'}
$bindingPath=Join-Path $suiteRoot 'BINDING.json'
$stagingPath=Join-Path $suiteRoot 'STAGING.json'
$reviewPath=Join-Path $suiteRoot 'ROOT_PRELAUNCH_REVIEW.json'
foreach($p in @($bindingPath,$stagingPath,$reviewPath)){if(!(Test-Path -LiteralPath $p -PathType Leaf)){throw "Root review gate file missing: $p. Copy and complete its template after protocol review."}}
$binding=Get-Content -LiteralPath $bindingPath -Raw|ConvertFrom-Json
$staging=Get-Content -LiteralPath $stagingPath -Raw|ConvertFrom-Json
$review=Get-Content -LiteralPath $reviewPath -Raw|ConvertFrom-Json
# Bind the reviewed peer capacity before the staging-policy gate consumes it.
$reviewPeers=@($review.allowed_peer_processes)
$reviewPeerLimit=[int]$review.max_concurrent_other_games
$bindingHash=(Get-FileHash -LiteralPath $bindingPath -Algorithm SHA256).Hash.ToLowerInvariant()
$stagingHash=(Get-FileHash -LiteralPath $stagingPath -Algorithm SHA256).Hash.ToLowerInvariant()
$planPath=Join-Path $packetRoot 'CASE_PLAN.json'
$sourceBindingsPath=Join-Path $packetRoot 'CASE_SOURCE_BINDINGS.json'
$plan=Get-Content -LiteralPath $planPath -Raw|ConvertFrom-Json
if($Suite -notin @($plan.active_native_suites)){throw 'This successor runs Texture-only Resource Windows on the new private candidate.'}
$sourceBindings=Get-Content -LiteralPath $sourceBindingsPath -Raw|ConvertFrom-Json
$candidateScopeProperty=$plan.candidate_execution_scope.suites.PSObject.Properties[$Suite]
$driverSourcePath=Join-Path $packetRoot 'ResourceNativeDriver.ps1'
$driverSourceText=[IO.File]::ReadAllText($driverSourcePath)
if($null -eq $candidateScopeProperty -or [string]::IsNullOrWhiteSpace([string]$candidateScopeProperty.Value.scope_id) -or
   !$driverSourceText.Contains('$candidateScopeProperty=$driverPlan.candidate_execution_scope.suites.PSObject.Properties[$Suite]') -or
   ($Suite -eq 'resource_windows' -and !$driverSourceText.Contains('$driverPlan.candidate_execution_scope.suites.resource_windows.enable_max_partial_fixups'))){
  throw 'Selected case has no nested candidate execution scope, or the actual driver prefix does not resolve the exact sealed CASE_PLAN.suites member.'
}
$parallelMonitorPath=Join-Path $packetRoot 'ResourceV5ParallelMonitor.ps1'
if(!(Test-Path -LiteralPath $parallelMonitorPath -PathType Leaf)){throw 'Immutable V5 peer-monitor helper is missing.'}
. $parallelMonitorPath
. (Join-Path $packetRoot 'ResourceLaunchAdoption.ps1')
$parallelAuthority=Assert-ResourceV5ParallelAuthority -RepoRoot $repoRoot -Spec $plan.parallel_native_policy
$parallelPolicyPath=[string]$parallelAuthority.policy_path
$parallelPolicySha256=[string]$parallelAuthority.policy_sha256
$casePlanHash=(Get-FileHash -LiteralPath $planPath -Algorithm SHA256).Hash.ToLowerInvariant()
$caseSourceHash=(Get-FileHash -LiteralPath $sourceBindingsPath -Algorithm SHA256).Hash.ToLowerInvariant()
$packetManifestPath=Join-Path $packetRoot 'MANIFEST.json'
$packetSealPath=Join-Path $packetRoot 'SEAL.json'
if(!(Test-Path -LiteralPath $packetManifestPath -PathType Leaf) -or !(Test-Path -LiteralPath $packetSealPath -PathType Leaf)){throw 'Immutable packet MANIFEST/SEAL is missing.'}
$packetManifest=Get-Content -LiteralPath $packetManifestPath -Raw|ConvertFrom-Json
$packetSeal=Get-Content -LiteralPath $packetSealPath -Raw|ConvertFrom-Json
$packetManifestHash=(Get-FileHash -LiteralPath $packetManifestPath -Algorithm SHA256).Hash.ToLowerInvariant()
if($packetSeal.status -cne 'sealed' -or $packetSeal.manifest_sha256 -cne $packetManifestHash -or $packetManifest.schema -ne 1){throw 'Immutable packet seal does not bind the current manifest.'}
foreach($item in $packetManifest.files){
  $path=[IO.Path]::GetFullPath((Join-Path $packetRoot ([string]$item.path -replace '/','\')))
  $prefix=[IO.Path]::GetFullPath($packetRoot).TrimEnd('\')+'\'
  if(!$path.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase) -or !(Test-Path -LiteralPath $path -PathType Leaf)){throw "Packet manifest path is absent or escaped the packet: $($item.path)"}
  $fi=Get-Item -LiteralPath $path -Force
  if($fi.Attributes -band [IO.FileAttributes]::ReparsePoint){throw "Packet manifest path is a reparse point: $($item.path)"}
  if([long]$fi.Length -ne [long]$item.bytes -or (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $item.sha256){throw "Immutable packet file changed after review: $($item.path)"}
}
foreach($rel in $sourceBindings.packet_files.PSObject.Properties.Name){
  $spec=$sourceBindings.packet_files.PSObject.Properties[$rel].Value
  $path=[IO.Path]::GetFullPath((Join-Path $packetRoot ($rel -replace '/','\')))
  if(!(Test-Path -LiteralPath $path -PathType Leaf) -or (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $spec.sha256){throw "Owned script/evidence packet changed: $rel"}
}
$expectedExe=[string]$plan.shipping_build.exe_sha256
$expectedB5=[string]$plan.candidate_source
$expectedWorkflow=[string]$plan.candidate_workflow_source
$frozenDataPlan=$plan.frozen_data_source
$protectedConfigPlan=$plan.protected_config_source
$privateDisplayPlan=$protectedConfigPlan.private_display_config
$rootDelegationPlan=$plan.root_execution_delegation
$storagePolicyPlan=$plan.root_authorized_storage_policy
if($null -eq $frozenDataPlan -or $null -eq $protectedConfigPlan -or $null -eq $privateDisplayPlan){throw 'Case plan lacks the root-selected frozen data and private display-config bindings.'}
if([int]$privateDisplayPlan.schema -ne 1 -or [string]$privateDisplayPlan.source_sha256 -cne [string]$protectedConfigPlan.sha256 -or
   [int]$privateDisplayPlan.source_bytes -ne [long]$protectedConfigPlan.bytes -or
   [string]$privateDisplayPlan.derived_sha256 -notmatch '^[0-9a-f]{64}$' -or [int]$privateDisplayPlan.derived_bytes -le 0 -or
   [int]$privateDisplayPlan.private_values.Width -ne 1280 -or [int]$privateDisplayPlan.private_values.Height -ne 720 -or
   [int]$privateDisplayPlan.private_values.Fullscreen -ne 0 -or [int]$privateDisplayPlan.capture.header_bytes -ne 54 -or
   [int]$privateDisplayPlan.capture.bytes_per_pixel -ne 4 -or [long]$privateDisplayPlan.capture.frame_file_bytes -ne 3686454 -or
   [long]$privateDisplayPlan.capture.frame_file_bytes -ne ([long]$privateDisplayPlan.capture.header_bytes + [long]$privateDisplayPlan.private_values.Width * [long]$privateDisplayPlan.private_values.Height * [long]$privateDisplayPlan.capture.bytes_per_pixel) -or
   [long]$privateDisplayPlan.capture.reserve_bytes_per_frame -ne 8388608){throw 'Case plan private Display transform, parser bounds, or exact frame reservation differs.'}
$rootDelegationPath=Join-Path $packetRoot ([string]$rootDelegationPlan.receipt_path -replace '/','\')
if(!(Test-Path -LiteralPath $rootDelegationPath -PathType Leaf) -or (Get-FileHash -LiteralPath $rootDelegationPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne [string]$rootDelegationPlan.sha256){throw 'Root execution delegation V3 receipt is missing or changed.'}
$rootDelegation=Get-Content -LiteralPath $rootDelegationPath -Raw|ConvertFrom-Json
$rootResourceExecutor=$rootDelegation.executors.resource_recovery_swarm
if($rootDelegation.authorizes_reviewed_successors -ne $true -or $rootDelegation.policy.max_concurrent_other_games -ne 100 -or
   [string]$rootResourceExecutor.selected_asset_roster -cne [string]$frozenDataPlan.snapshot_receipt_path -or
   !([int]$slot -in @($rootResourceExecutor.slots)) -or $rootDelegationPlan.successor_scope_authorized -ne $true){throw 'Root delegation does not authorize this exact slot/frozen roster/reviewed successor scope.'}
$storagePolicyPath=Join-Path $packetRoot ([string]$storagePolicyPlan.receipt_path -replace '/','\')
if(!(Test-Path -LiteralPath $storagePolicyPath -PathType Leaf) -or (Get-FileHash -LiteralPath $storagePolicyPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne [string]$storagePolicyPlan.receipt_sha256){throw 'Root-authorized MinFreeGB6 storage policy receipt is missing or changed.'}
$storagePolicy=Get-Content -LiteralPath $storagePolicyPath -Raw|ConvertFrom-Json
if($storagePolicy.status -cne 'root_authorized_actual_footprint_resource_staging' -or [long]$storagePolicy.free_floor_bytes -ne 2147483648 -or $caseMinFreeGiB -ne 2 -or $storagePolicyPlan.strategy -cne 'readonly_hardlinks_retained'){throw 'Exact Root readonly-pool authority/floor/strategy mismatch.'}
$budgetPlanPath=Join-Path $packetRoot $plan.readonly_physical_budget.path
if((Get-FileHash $budgetPlanPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $plan.readonly_physical_budget.sha256){throw 'Physical budget plan hash mismatch.'}
$physicalPlan=Get-Content -LiteralPath $budgetPlanPath -Raw|ConvertFrom-Json
$resourceSuiteMutex=[Threading.Mutex]::new($false,'Local\BurnoutPC_ResourceV7Suites_v1')
if(!$resourceSuiteMutex.WaitOne(0)){throw 'Another Resource V7 suite owns the physical-output budget.'}
$otherSuiteFutureBytes=[long]0
. (Join-Path $packetRoot 'TextureVolumeBudgets.ps1')
if([int]$physicalPlan.frame_caps.PSObject.Properties[$Suite].Value -ne $caseFrameCount -or [long]$physicalPlan.sidecar_log_archive_output_per_suite -ne $sidecarReserveBytes){throw 'Concrete physical budget and case frame/sidecar caps differ.'}
$frozenSnapshotPath=[IO.Path]::GetFullPath((Join-Path $repoRoot ([string]$frozenDataPlan.snapshot_receipt_path -replace '/','\')))
$frozenRosterPath=[IO.Path]::GetFullPath((Join-Path $repoRoot ([string]$frozenDataPlan.source_roster_path -replace '/','\')))
$normalInstallRoot=[IO.Path]::GetFullPath((Join-Path $repoRoot ([string]$protectedConfigPlan.normal_install_root -replace '/','\')))
$protectedConfigRosterPath=[IO.Path]::GetFullPath((Join-Path $repoRoot ([string]$protectedConfigPlan.roster_path -replace '/','\')))
$expectedFrozenDataPath=[IO.Path]::GetFullPath((Join-Path $repoRoot ([string]$frozenDataPlan.data_path -replace '/','\')))
$expectedProtectedConfigPath=[IO.Path]::GetFullPath((Join-Path $normalInstallRoot ([string]$protectedConfigPlan.relative_config_path -replace '/','\')))
if(!(Test-Path -LiteralPath $frozenSnapshotPath -PathType Leaf) -or (Get-FileHash -LiteralPath $frozenSnapshotPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne [string]$frozenDataPlan.snapshot_receipt_sha256){throw 'Root-selected frozen data snapshot receipt is missing or changed.'}
if(!(Test-Path -LiteralPath $frozenRosterPath -PathType Leaf) -or (Get-FileHash -LiteralPath $frozenRosterPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne [string]$frozenDataPlan.source_roster_sha256){throw 'Independent frozen source asset roster is missing or changed.'}
$frozenSnapshot=Get-Content -LiteralPath $frozenSnapshotPath -Raw|ConvertFrom-Json
if([IO.Path]::GetFullPath([string]$frozenSnapshot.data) -ine $expectedFrozenDataPath -or [string]$frozenSnapshot.roster_path -ine [string]$frozenRosterPath -or [string]$frozenSnapshot.roster_sha256 -cne [string]$frozenDataPlan.source_roster_sha256 -or [int]$frozenSnapshot.count -ne [int]$frozenDataPlan.file_count -or [long]$frozenSnapshot.bytes -ne [long]$frozenDataPlan.bytes){throw 'Frozen data snapshot receipt differs from the exact CASE_PLAN selection.'}
if(!(Test-Path -LiteralPath $protectedConfigRosterPath -PathType Leaf) -or (Get-FileHash -LiteralPath $protectedConfigRosterPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne [string]$protectedConfigPlan.roster_sha256){throw 'Protected normal-install config roster is missing or changed.'}
$protectedConfigRoster=Get-Content -LiteralPath $protectedConfigRosterPath -Raw|ConvertFrom-Json
if([string]$protectedConfigRoster.executable_sha256 -and [string]$protectedConfigRoster.executable_sha256 -cne [string]$protectedConfigPlan.normal_install_exe_sha256){throw 'Protected normal-install executable identity differs from the config source binding.'}
$protectedConfigEntries=@($protectedConfigRoster.profile_config_log_preserved|Where-Object {$_.relative_path -ceq 'config.ini'})
if($protectedConfigEntries.Count -ne 1 -or [long]$protectedConfigEntries[0].bytes -ne [long]$protectedConfigPlan.bytes -or [string]$protectedConfigEntries[0].sha256 -cne [string]$protectedConfigPlan.sha256){throw 'Protected normal-install config roster does not contain the exact selected config.ini.'}
$protectedConfigFile=Get-Item -LiteralPath $expectedProtectedConfigPath -Force
if($protectedConfigFile.Attributes -band [IO.FileAttributes]::ReparsePoint -or [long]$protectedConfigFile.Length -ne [long]$protectedConfigPlan.bytes -or (Get-FileHash -LiteralPath $expectedProtectedConfigPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne [string]$protectedConfigPlan.sha256){throw 'Protected normal-install config.ini bytes differ from the exact roster.'}
if([IO.Path]::GetFullPath([string]$staging.data_source_path) -ine $expectedFrozenDataPath -or
   [string]$staging.frozen_snapshot_receipt_path -ine [string]$frozenDataPlan.snapshot_receipt_path -or
   [string]$staging.frozen_snapshot_receipt_sha256 -cne [string]$frozenDataPlan.snapshot_receipt_sha256 -or
   [string]$staging.source_roster_path -ine [string]$frozenDataPlan.source_roster_path -or
   [string]$staging.source_roster_sha256 -cne [string]$frozenDataPlan.source_roster_sha256){throw 'STAGING does not bind the exact Root-selected frozen 5,622-file private data snapshot.'}
if([IO.Path]::GetFullPath([string]$staging.config_source_path) -ine $expectedProtectedConfigPath -or
   [string]$staging.config_source_roster_path -ine [string]$protectedConfigPlan.roster_path -or
   [string]$staging.config_source_roster_sha256 -cne [string]$protectedConfigPlan.roster_sha256){throw 'STAGING config source is not the exact separate protected normal-install config.'}
if([IO.Path]::GetFullPath([string]$binding.data_source_path) -ine $expectedFrozenDataPath -or
   [string]$binding.frozen_snapshot_receipt_path -ine [string]$frozenDataPlan.snapshot_receipt_path -or
   [string]$binding.frozen_snapshot_receipt_sha256 -cne [string]$frozenDataPlan.snapshot_receipt_sha256 -or
   [string]$binding.source_roster_path -ine [string]$frozenDataPlan.source_roster_path -or
   [string]$binding.source_roster_sha256 -cne [string]$frozenDataPlan.source_roster_sha256 -or
   [IO.Path]::GetFullPath([string]$binding.config_source_path) -ine $expectedProtectedConfigPath -or
   [string]$binding.config_source_roster_path -ine [string]$protectedConfigPlan.roster_path -or
   [string]$binding.config_source_roster_sha256 -cne [string]$protectedConfigPlan.roster_sha256){throw 'BINDING does not bind the selected frozen assets and separate protected config.'}
if([IO.Path]::GetFullPath([string]$review.data_source_path) -ine $expectedFrozenDataPath -or
   [string]$review.frozen_snapshot_receipt_path -ine [string]$frozenDataPlan.snapshot_receipt_path -or
   [string]$review.frozen_snapshot_receipt_sha256 -cne [string]$frozenDataPlan.snapshot_receipt_sha256 -or
   [string]$review.source_roster_path -ine [string]$frozenDataPlan.source_roster_path -or
   [string]$review.source_roster_sha256 -cne [string]$frozenDataPlan.source_roster_sha256 -or
   [IO.Path]::GetFullPath([string]$review.config_source_path) -ine $expectedProtectedConfigPath -or
   [string]$review.config_source_roster_path -ine [string]$protectedConfigPlan.roster_path -or
   [string]$review.config_source_roster_sha256 -cne [string]$protectedConfigPlan.roster_sha256 -or
   [string]$review.storage_policy_receipt_sha256 -cne [string]$storagePolicyPlan.receipt_sha256 -or
   [double]$review.min_free_gib -ne [double]$storagePolicyPlan.min_free_gib){throw 'ROOT_PRELAUNCH_REVIEW does not bind the frozen assets, separate config, or Root-authorized storage policy.'}
foreach($record in @(@{name='STAGING';value=$staging},@{name='BINDING';value=$binding},@{name='ROOT_PRELAUNCH_REVIEW';value=$review})){
  $private=$record.value
  if([string]$private.private_config_source_sha256 -cne [string]$protectedConfigPlan.sha256 -or
     [string]$private.private_config_sha256 -cne [string]$privateDisplayPlan.derived_sha256 -or
     [string]$private.private_config_path_in_slot -cne [string]$privateDisplayPlan.private_slot_relative_path -or
     [int]$private.private_display_width -ne [int]$privateDisplayPlan.private_values.Width -or
     [int]$private.private_display_height -ne [int]$privateDisplayPlan.private_values.Height -or
     [int]$private.private_display_fullscreen -ne [int]$privateDisplayPlan.private_values.Fullscreen -or
     [long]$private.capture_frame_file_bytes -ne [long]$privateDisplayPlan.capture.frame_file_bytes -or
     [long]$private.capture_frame_reserve_bytes -ne [long]$privateDisplayPlan.capture.reserve_bytes_per_frame -or
     [string]$private.audio_mute_environment -cne [string]$privateDisplayPlan.audio_policy.environment -or
     [string]$private.audio_mute_value -cne [string]$privateDisplayPlan.audio_policy.value -or
     [string]$private.audio_mute_scope -cne [string]$privateDisplayPlan.audio_policy.scope){throw "$($record.name) does not bind the reviewed private Display-only config, capture-size limit, and flow audio policy."}
}
if([string]$staging.storage_policy_receipt_sha256 -cne [string]$storagePolicyPlan.receipt_sha256 -or
   [string]$binding.storage_policy_receipt_sha256 -cne [string]$storagePolicyPlan.receipt_sha256 -or
   [string]$staging.root_delegation_sha256 -cne [string]$rootDelegationPlan.sha256 -or
   [string]$binding.root_delegation_sha256 -cne [string]$rootDelegationPlan.sha256 -or
   [string]$review.root_delegation_sha256 -cne [string]$rootDelegationPlan.sha256){throw 'BINDING/STAGING/ROOT_PRELAUNCH do not bind the Root delegation and MinFreeGB6 reserve receipts.'}
if($review.status -cne 'ready' -or $review.protocol_reviewed -ne $true -or $review.scripts_reviewed -ne $true -or $review.provenance_reviewed -ne $true -or $review.private_stage_reviewed -ne $true -or $review.launch_authorized -ne $true){throw 'Fresh root prelaunch review is incomplete; no launch was attempted.'}
if($review.acknowledgements.no_game_launch_before_this_review -ne $true -or $review.acknowledgements.no_foreign_game_will_be_killed -ne $true -or $review.acknowledgements.root_parallel_v5_policy_bound -ne $true -or $review.acknowledgements.dynamic_campaign_handoffs_required -ne $true -or $review.acknowledgements.foreign_presence_is_informational -ne $true -or $review.acknowledgements.SET_readback_is_not_pixel_proof -ne $true -or $review.acknowledgements.D_dump_stats_action_mutex_required -ne $true -or $review.acknowledgements.coreCgsGuiResource_owner_lifecycle_excluded -ne $true -or $review.acknowledgements.private_runtime_overlay_hashes_bound -ne $true -or $review.acknowledgements.phase_done_request_after_restore_only -ne $true -or $review.acknowledgements.phase_done_requester_does_not_stop_process -ne $true){throw 'Required Root V5 parallel-policy acknowledgements are missing.'}
if($review.root_parallel_policy_path -cne [string]$plan.parallel_native_policy.policy_path -or $review.root_parallel_policy_sha256 -cne $parallelPolicySha256 -or $review.root_parallel_delegation_sha256 -cne [string]$plan.parallel_native_policy.delegation_sha256 -or [int]$review.max_concurrent_other_games -ne 100){throw 'Root prelaunch review does not bind exact V5 dynamic-peer policy/delegation and its 100 known-peer limit.'}
if($review.v5_parallel_monitor_review_status -cne 'PASS' -or [string]::IsNullOrWhiteSpace([string]$review.v5_parallel_monitor_review_path) -or [string]::IsNullOrWhiteSpace([string]$review.v5_parallel_monitor_review_sha256) -or $review.v5_parallel_monitor_review_packet_manifest_sha256 -cne $packetManifestHash -or $review.v5_parallel_monitor_review_policy_sha256 -cne $parallelPolicySha256){throw 'Root prelaunch review lacks the exact independent V5 monitor verdict, packet manifest, or Root policy hash.'}
$v5MonitorReviewPath=Get-ResourceV5Path $repoRoot ([string]$review.v5_parallel_monitor_review_path)
$v5MonitorReviewItem=Get-Item -LiteralPath $v5MonitorReviewPath -Force
if($v5MonitorReviewItem.Attributes -band [IO.FileAttributes]::ReparsePoint -or (Get-FileHash -LiteralPath $v5MonitorReviewPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne [string]$review.v5_parallel_monitor_review_sha256){throw 'V5 monitor peer-review report bytes differ from the exact Root-bound report hash.'}
$v5MonitorReviewText=[IO.File]::ReadAllText($v5MonitorReviewPath)
if(!$v5MonitorReviewText.Contains([string]$packetManifestHash) -or !$v5MonitorReviewText.Contains([string]$parallelPolicySha256)){throw 'V5 monitor peer-review report does not mention the exact packet manifest and Root policy hashes.'}
if($review.suite -cne $Suite -or [int]$review.slot -ne $slot -or $review.run_name -cne $RunName -or [string]::IsNullOrWhiteSpace([string]$review.reviewer) -or [string]::IsNullOrWhiteSpace([string]$review.observations)){throw 'Root review is not bound to this exact suite, run name, slot, and reviewer.'}
if($review.binding_sha256 -cne $bindingHash -or $review.staging_sha256 -cne $stagingHash){throw 'Root review does not bind the exact final binding and staging files.'}
if($review.runtime_root_path -cne $staging.runtime_root_path -or $binding.runtime_root_path -cne $staging.runtime_root_path -or $review.protected_runtime_root_path -cne $sourceBindings.runtime_harness.protected_source_root -or $staging.protected_runtime_root_path -cne $sourceBindings.runtime_harness.protected_source_root -or $binding.protected_runtime_root_path -cne $sourceBindings.runtime_harness.protected_source_root -or $review.runtime_workflow_source -cne $sourceBindings.runtime_harness.upstream_commit -or $review.runtime_workflow_tree -cne $sourceBindings.runtime_harness.upstream_tree -or $review.runtime_overlay_manifest_sha256 -cne $sourceBindings.runtime_harness.overlay_package_manifest_sha256 -or $review.runtime_overlay_seal_sha256 -cne $sourceBindings.runtime_harness.overlay_package_seal_sha256 -or $review.runtime_run_case_sha256 -cne $sourceBindings.runtime_harness.overlay_files.'tools/tests/run_case.ps1'.sha256 -or $review.runtime_flow_run_sha256 -cne $sourceBindings.runtime_harness.overlay_files.'tools/diagnostics/flow_run.ps1'.sha256 -or $review.phase_done_requester_sha256 -cne $sourceBindings.runtime_harness.phase_done_requester.sha256 -or $review.runtime_review_receipt_sha256 -cne $sourceBindings.runtime_harness.review_receipt_sha256 -or $review.runtime_verify_receipt_sha256 -cne $sourceBindings.runtime_harness.verify_receipt_sha256){throw 'Root review does not bind the exact private runtime overlay and phase-done requester.'}
if($binding.runtime_workflow_commit -cne $sourceBindings.runtime_harness.upstream_commit -or $binding.runtime_workflow_tree -cne $sourceBindings.runtime_harness.upstream_tree -or $binding.runtime_overlay_manifest_sha256 -cne $sourceBindings.runtime_harness.overlay_package_manifest_sha256 -or $binding.runtime_overlay_seal_sha256 -cne $sourceBindings.runtime_harness.overlay_package_seal_sha256 -or $binding.runtime_verify_receipt_sha256 -cne $sourceBindings.runtime_harness.verify_receipt_sha256 -or $staging.runtime_overlay_manifest_sha256 -cne $sourceBindings.runtime_harness.overlay_package_manifest_sha256 -or $staging.runtime_overlay_seal_sha256 -cne $sourceBindings.runtime_harness.overlay_package_seal_sha256 -or $staging.runtime_verify_receipt_sha256 -cne $sourceBindings.runtime_harness.verify_receipt_sha256){throw 'Root binding/staging runtime overlay identity differs from the frozen runtime package.'}
if($review.data_source_path -cne $staging.data_source_path -or $review.data_source_manifest_sha256 -cne $staging.data_source_manifest_sha256 -or $review.config_source_path -cne $staging.config_source_path -or $review.config_source_sha256 -cne $staging.config_source_sha256 -or $review.private_stage_root -cne $staging.stage_root){throw 'Root review data/config/private-stage binding differs from STAGING.json.'}
if($binding.data_source_manifest_sha256 -cne $staging.data_source_manifest_sha256 -or $binding.config_source_sha256 -cne $staging.config_source_sha256 -or
   $review.frozen_snapshot_receipt_path -cne $staging.frozen_snapshot_receipt_path -or $review.source_roster_path -cne $staging.source_roster_path -or
   $review.config_source_roster_path -cne $staging.config_source_roster_path){throw 'BINDING/ROOT_PRELAUNCH_REVIEW data, snapshot, or separate config hashes differ from STAGING.'}
if($binding.status -cne 'root_reviewed_ready' -or $staging.status -cne 'root_reviewed_ready' -or $binding.slot_reserved_for_this_case -ne $true -or $review.slot_reserved_for_this_case -ne $true -or $binding.suite -cne $Suite -or $staging.suite -cne $Suite -or [int]$binding.slot -ne $slot -or [int]$staging.slot -ne $slot -or $binding.run_name -cne $RunName -or $staging.run_name -cne $RunName){throw 'Reviewed binding/staging status, run name, or reserved slot differs.'}
if($binding.candidate_source -cne $expectedB5 -or $binding.candidate_source_tree -cne $plan.candidate_source_tree -or $binding.candidate_workflow_source -cne $expectedWorkflow -or $binding.candidate_workflow_tree -cne $plan.candidate_workflow_tree -or $binding.candidate_exe_sha256 -cne $expectedExe){throw 'Binding source/build identity differs from the pinned candidate.'}
if($review.candidate_source -cne $expectedB5 -or $review.candidate_source_tree -cne $plan.candidate_source_tree -or $review.candidate_workflow_source -cne $expectedWorkflow -or $review.candidate_workflow_tree -cne $plan.candidate_workflow_tree -or $review.candidate_exe_sha256 -cne $expectedExe){throw 'Root review source/build identity differs.'}
if($binding.case_plan_sha256 -cne $casePlanHash -or $binding.case_source_bindings_sha256 -cne $caseSourceHash -or $review.case_source_bindings_sha256 -cne $caseSourceHash){throw 'Root binding/review does not hash the current immutable plan/source bindings.'}
if($binding.packet_manifest_sha256 -cne $packetManifestHash -or $review.packet_manifest_sha256 -cne $packetManifestHash){throw 'Root binding/review does not hash the sealed packet manifest.'}
if($staging.candidate_source -cne $expectedB5 -or $staging.candidate_workflow_source -cne $expectedWorkflow -or $staging.candidate_exe_sha256 -cne $expectedExe){throw 'Staging source/build identity differs.'}
if($staging.run_name -cne $RunName -or $staging.created_for_this_case -ne $false){throw 'Staging must be newly created by this exact run.'}
if($binding.profile_fixture.kind -cne 'current_normal_profile_copy' -or $plan.fixture.kind -cne 'current_normal_profile_copy' -or $binding.profile_fixture.sha256 -cne $plan.fixture.sha256 -or [long]$binding.profile_fixture.bytes -ne [long]$plan.fixture.bytes -or [IO.Path]::GetFullPath([string]$binding.profile_fixture.path) -ine [IO.Path]::GetFullPath([string]$plan.fixture.path) -or $staging.run_policy.profile_fixture_sha256 -cne $plan.fixture.sha256){throw 'Pinned independent current-save ProfileFixture identity differs.'}
if([string]::IsNullOrWhiteSpace([string]$review.reviewed_utc) -or [string]::IsNullOrWhiteSpace([string]$staging.data_source_path) -or [string]::IsNullOrWhiteSpace([string]$staging.data_source_manifest_sha256) -or [string]::IsNullOrWhiteSpace([string]$staging.config_source_path) -or [string]::IsNullOrWhiteSpace([string]$staging.config_source_sha256)){throw 'Root must bind exact data/config sources and their manifests before launch.'}
if($binding.root_parallel_policy_sha256 -cne $parallelPolicySha256 -or $staging.root_parallel_policy_sha256 -cne $parallelPolicySha256 -or $staging.run_policy.root_parallel_policy_sha256 -cne $parallelPolicySha256 -or $staging.run_policy.peer_identity_mode -cne 'dynamic_root_v5_handoffs' -or $staging.run_policy.private_sibling_slot_data -ne $true -or $staging.run_policy.strict_game_ownership -ne $true -or $staging.run_policy.allow_concurrent_games -ne $true -or [int]$staging.run_policy.max_concurrent_other_games -ne $reviewPeerLimit -or [int]$staging.run_policy.max_game_instances -ne ($reviewPeerLimit+1) -or [int]$staging.run_policy.max_game_instances -gt 101 -or $staging.run_policy.frames_named_request -ne $true -or [int]$staging.run_policy.frame_slot -ne $slot -or [double]$staging.run_policy.min_free_gib -ne $caseMinFreeGiB -or [int]$staging.run_policy.max_frame_count -ne $caseFrameCount -or [long]$staging.run_policy.frame_reserve_bytes_per_frame -ne $frameReserveBytesPerFrame -or [long]$staging.run_policy.sidecar_reserve_bytes -ne $sidecarReserveBytes -or [long]$staging.run_policy.data_source_bytes -ne [long]$frozenDataPlan.bytes){throw 'Binding/staging must bind exact Root V5 peer policy, dynamic handoff mode, 100-peer ceiling, frozen assets, frame limit, and disk reserve.'}
if([IO.Path]::GetFullPath([string]$staging.runtime_root_path) -ine [IO.Path]::GetFullPath([string]$sourceBindings.runtime_harness.runtime_root_path) -or $staging.runtime_overlay_manifest_sha256 -cne $sourceBindings.runtime_harness.overlay_package_manifest_sha256 -or $staging.runtime_overlay_seal_sha256 -cne $sourceBindings.runtime_harness.overlay_package_seal_sha256){throw 'Staging runtime clone path/overlay hashes do not match the frozen reviewed binding.'}

$receiptPath=Join-Path $repoRoot ([string]$plan.shipping_build.receipt_path)
if((Get-FileHash -LiteralPath $receiptPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $plan.shipping_build.receipt_sha256){throw 'Canonical native whole-link receipt changed.'}
if($staging.shipping_receipt_sha256 -cne $plan.shipping_build.receipt_sha256){throw 'Staging canonical link binding differs.'}
$linkReceipt=Get-Content -LiteralPath $receiptPath -Raw|ConvertFrom-Json
if($linkReceipt.whole_link -cne 'pass' -or $linkReceipt.exe_sha256 -cne $expectedExe -or $linkReceipt.built_source_commit -cne $expectedB5 -or $linkReceipt.built_workflow_commit -cne $expectedWorkflow -or [int]$linkReceipt.final_incremental_compile.source_tus -ne 3019 -or [int]$linkReceipt.final_incremental_compile.compile_failures -ne 0 -or [int]$linkReceipt.final_incremental_compile.link_errors -ne 0 -or @($linkReceipt.source_input_drift).Count -ne 0 -or @($linkReceipt.external_link_package_drift).Count -ne 0){throw 'New private canonical whole-link3019 proof differs.'}
$payloadBindingPath=Join-Path $packetRoot ([string]$plan.shipping_build.payload_binding_path)
if((Get-FileHash -LiteralPath $payloadBindingPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $plan.shipping_build.payload_binding_sha256){throw 'Exact private runtime payload projection changed.'}
$buildReceipt=Get-Content -LiteralPath $payloadBindingPath -Raw|ConvertFrom-Json
if($buildReceipt.exe_sha256 -cne $expectedExe -or $buildReceipt.source_commit -cne $expectedB5 -or [int]$buildReceipt.file_count -ne 15 -or $buildReceipt.canonical_link_receipt_sha256 -cne $plan.shipping_build.receipt_sha256){throw 'Native baseline runtime payload projection differs.'}
$baselinePath=Join-Path $packetRoot ([string]$plan.shipping_build.startup_baseline_path)
if((Get-FileHash -LiteralPath $baselinePath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $plan.shipping_build.startup_baseline_sha256){throw 'Actual new private startup baseline receipt changed.'}
$baseline=Get-Content -LiteralPath $baselinePath -Raw|ConvertFrom-Json
if([int]$baseline.case_checks_with_terminal -ne 17 -or [int]$baseline.asserts -ne 0 -or $baseline.exe_sha256 -cne $expectedExe -or $baseline.source_commit -cne $expectedB5){throw 'New private actual startup baseline did not pass17 checks.'}
$shippingOut=[string]$buildReceipt.source_payload_root
$buildResultPath=$receiptPath
$exeSource=Join-Path $shippingOut 'Burnout_PC.exe'
if((Get-FileHash -LiteralPath $exeSource -Algorithm SHA256).Hash.ToLowerInvariant() -cne $expectedExe){throw 'Candidate executable bytes changed.'}
$provPath=$exeSource+'.provenance.json'
$provenance=Get-Content -LiteralPath $provPath -Raw|ConvertFrom-Json
if($provenance.exe_sha256 -cne $expectedExe -or $provenance.b5_head -cne $expectedB5 -or $provenance.parent_head -cne $expectedWorkflow){throw 'Executable provenance sidecar differs from pinned candidate.'}
$runtimeBinding=$sourceBindings.runtime_harness
$runtimePackage=Join-Path $packetRoot ([string]$runtimeBinding.overlay_package_path -replace '/','\')
$runtimeManifestPath=Join-Path $runtimePackage 'MANIFEST.json';$runtimeSealPath=Join-Path $runtimePackage 'SEAL.json'
$runtimeManifest=Get-Content -LiteralPath $runtimeManifestPath -Raw|ConvertFrom-Json;$runtimeSeal=Get-Content -LiteralPath $runtimeSealPath -Raw|ConvertFrom-Json
if((Get-FileHash -LiteralPath $runtimeManifestPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $runtimeBinding.overlay_package_manifest_sha256 -or (Get-FileHash -LiteralPath $runtimeSealPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $runtimeBinding.overlay_package_seal_sha256 -or $runtimeSeal.manifest_sha256 -cne $runtimeBinding.overlay_package_manifest_sha256 -or $runtimeSeal.package -cne 'native_runtime_overlay_successor_20261029_v5_parallel' -or [int]$runtimeSeal.file_count -ne @($runtimeManifest.files).Count){throw 'Reviewed V5 runtime overlay package manifest/seal changed.'}
foreach($item in $runtimeManifest.files){$p=Join-Path $runtimePackage ([string]$item.path -replace '/','\');if(!(Test-Path -LiteralPath $p -PathType Leaf) -or (Get-Item -LiteralPath $p).Length -ne [long]$item.bytes -or (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -cne $item.sha256){throw "Runtime overlay package file changed: $($item.path)"}}
$runtimeReviewReceipt=Join-Path $packetRoot ([string]$runtimeBinding.review_receipt_path -replace '/','\')
if(!(Test-Path -LiteralPath $runtimeReviewReceipt -PathType Leaf) -or (Get-FileHash -LiteralPath $runtimeReviewReceipt -Algorithm SHA256).Hash.ToLowerInvariant() -cne $runtimeBinding.review_receipt_sha256 -or (Get-Content -LiteralPath $runtimeReviewReceipt -Raw|ConvertFrom-Json).status -cne 'PASS'){throw 'Independent base runtime overlay review receipt is missing or changed.'}
$runtimeVerifyReceipt=Join-Path $packetRoot ([string]$runtimeBinding.verify_receipt_path -replace '/','\')
if(!(Test-Path -LiteralPath $runtimeVerifyReceipt -PathType Leaf) -or (Get-FileHash -LiteralPath $runtimeVerifyReceipt -Algorithm SHA256).Hash.ToLowerInvariant() -cne $runtimeBinding.verify_receipt_sha256 -or (Get-Content -LiteralPath $runtimeVerifyReceipt -Raw|ConvertFrom-Json).status -cne 'PASS'){throw 'Private runtime overlay verify receipt is missing or changed.'}
$runtimeRoot=[IO.Path]::GetFullPath([string]$staging.runtime_root_path)
if(@($runtimeBinding.executed_dependency_files.PSObject.Properties).Count -ne 4){throw 'Exact executed runtime check/known-assert/frame/box-lock dependencies are not bound.'}
if($runtimeRoot -ieq [IO.Path]::GetFullPath($repoRoot) -or !(Test-Path -LiteralPath $runtimeRoot -PathType Container)){throw 'Runtime overlay must use the separate reviewed private Git clone.'}
$protectedRuntimeRoot=[IO.Path]::GetFullPath([string]$runtimeBinding.protected_source_root)
if($protectedRuntimeRoot -ine [IO.Path]::GetFullPath([string]$staging.protected_runtime_root_path) -or $protectedRuntimeRoot -ieq [IO.Path]::GetFullPath($runtimeRoot) -or !(Test-Path -LiteralPath $protectedRuntimeRoot -PathType Container)){throw 'Protected runtime source clone path is missing, mismatched, or aliases the writable overlay clone.'}
$protectedHead=(& git -C $protectedRuntimeRoot rev-parse HEAD).Trim();$protectedTree=(& git -C $protectedRuntimeRoot rev-parse 'HEAD^{tree}').Trim()
$runtimeHead=(& git -C $runtimeRoot rev-parse HEAD).Trim();$runtimeTree=(& git -C $runtimeRoot rev-parse 'HEAD^{tree}').Trim()
if($protectedHead -cne $runtimeBinding.upstream_commit -or $protectedTree -cne $runtimeBinding.upstream_tree -or $runtimeHead -cne $runtimeBinding.upstream_commit -or $runtimeTree -cne $runtimeBinding.upstream_tree){throw 'Protected source/private runtime Git commit or tree differs from the reviewed overlay base.'}
foreach($entry in $runtimeBinding.protected_source_runtime_files.PSObject.Properties){$p=Join-Path $protectedRuntimeRoot ($entry.Name -replace '/','\');if(!(Test-Path -LiteralPath $p -PathType Leaf) -or (Get-Item -LiteralPath $p).Length -ne [long]$entry.Value.bytes -or (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -cne $entry.Value.sha256){throw "Protected source runtime file changed: $($entry.Name)"}}
$overlayStatus=@(& git -C $runtimeRoot status --porcelain --untracked-files=all)
$overlayPaths=@($overlayStatus|ForEach-Object {$_.Substring(3).Trim()}|Sort-Object)
$expectedOverlayPaths=@('tools/diagnostics/flow_run.ps1','tools/tests/run_case.ps1')
$expectedOverlayPaths=@($expectedOverlayPaths|Sort-Object)
if((Compare-Object $expectedOverlayPaths $overlayPaths).Count -ne 0){throw 'Private runtime clone contains paths outside the exact reviewed two-file overlay.'}
foreach($rel in $runtimeBinding.overlay_files.PSObject.Properties.Name){$spec=$runtimeBinding.overlay_files.PSObject.Properties[$rel].Value;$p=Join-Path $runtimeRoot ($rel -replace '/','\');if(!(Test-Path -LiteralPath $p -PathType Leaf) -or (Get-Item -LiteralPath $p).Length -ne [long]$spec.bytes -or (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -cne $spec.sha256){throw "Private runtime overlay file differs: $rel"}}
$phaseRequester=Join-Path $packetRoot ([string]$runtimeBinding.phase_done_requester.path -replace '/','\')
if(!(Test-Path -LiteralPath $phaseRequester -PathType Leaf) -or (Get-FileHash -LiteralPath $phaseRequester -Algorithm SHA256).Hash.ToLowerInvariant() -cne $runtimeBinding.phase_done_requester.sha256){throw 'Reviewed phase-done requester bytes differ.'}
$fixture=[IO.Path]::GetFullPath([string]$plan.fixture.path)
$expectedFixture=[IO.Path]::GetFullPath((Join-Path (Join-Path ([string]$plan.runtime_output_root) ('profile_snapshots\'+$RunName)) 'Profile.sav'))
$currentNormalProfile=[IO.Path]::GetFullPath((Join-Path $normalInstallRoot 'Memcard\Profile.sav'))
if($fixture -ine $expectedFixture -or [IO.Path]::GetFullPath([string]$plan.fixture.source_normal_path) -ine $currentNormalProfile -or [IO.Path]::GetPathRoot($fixture) -ine 'C:\' -or [IO.Path]::GetPathRoot($currentNormalProfile) -ine 'D:\'){throw 'Current-save fixture must be the exact independent C per-run copy of the D normal profile.'}
Assert-TextureOrdinaryFileChain $fixture
Assert-TextureOrdinaryFileChain $currentNormalProfile
$fixtureReceiptPath=Join-Path $packetRoot ([string]$plan.fixture.snapshot_receipt_path)
$fixtureReceipt=Get-Content -LiteralPath $fixtureReceiptPath -Raw|ConvertFrom-Json
if($fixtureReceipt.independent_copy -ne $true -or $fixtureReceipt.same_file -ne $false -or $fixtureReceipt.normal_original_written -ne $false -or $fixtureReceipt.source_before_after_stable -ne $true -or $fixtureReceipt.run_name -cne $RunName -or $fixtureReceipt.fixture.sha256 -cne $plan.fixture.sha256 -or [IO.Path]::GetFullPath([string]$fixtureReceipt.fixture.path) -ine $fixture){throw 'Stable current-save copy receipt differs.'}
if((Get-FileHash -LiteralPath $fixture -Algorithm SHA256).Hash.ToLowerInvariant() -cne $plan.fixture.sha256 -or (Get-FileHash -LiteralPath $currentNormalProfile -Algorithm SHA256).Hash.ToLowerInvariant() -cne $plan.fixture.sha256 -or [long](Get-Item -LiteralPath $fixture).Length -ne [long]$plan.fixture.bytes){throw 'Current-save copy or live protected source evolved; retain snapshot and prepare a fresh successor.'}

function Get-LiveGameProcessIdentity([int]$ProcessId){
  $proc=$null
  try{
    $proc=Get-Process -Id $ProcessId -ErrorAction Stop
    $handle=[IntPtr]$proc.Handle
    $proc.Refresh()
    if($proc.HasExited){$proc.Dispose();return $null}
    if($handle -eq [IntPtr]::Zero){throw 'Process handle is zero.'}
    $start=$proc.StartTime.ToUniversalTime()
    return [pscustomobject]@{process=$proc;handle=$handle;start_time_utc=$start.ToString('o');start_ticks=[long]$start.Ticks}
  }catch{
    $firstError=$_.Exception.Message
    if($null -ne $proc){try{$proc.Dispose()}catch{}}
    try{$still=Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction Stop}catch{throw "Cannot revalidate game PID $ProcessId after process-handle failure: $($_.Exception.Message)"}
    if($null -eq $still){return $null}
    if([string]::IsNullOrWhiteSpace([string]$still.Name)){throw "Cannot prove whether game PID $ProcessId still exists after process-handle failure."}
    if($still.Name -notmatch '^(?i:Burnout.*\.exe|TUB_Burnout_PC_External\.exe|BrnGame\.exe)$'){return $null}
    $retry=$null
    try{
      $retry=Get-Process -Id $ProcessId -ErrorAction Stop
      $retryHandle=[IntPtr]$retry.Handle
      $retry.Refresh()
      if($retry.HasExited){$retry.Dispose();return $null}
      if($retryHandle -eq [IntPtr]::Zero){throw 'Process handle is zero.'}
      $retryStart=$retry.StartTime.ToUniversalTime()
      return [pscustomobject]@{process=$retry;handle=$retryHandle;start_time_utc=$retryStart.ToString('o');start_ticks=[long]$retryStart.Ticks}
    }catch{
      $retryError=$_.Exception.Message
      if($null -ne $retry){try{$retry.Dispose()}catch{}}
      try{$stillAgain=Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction Stop}catch{throw "Cannot distinguish exited from live game PID $ProcessId after handle retry: $($_.Exception.Message)"}
      if($null -eq $stillAgain){return $null}
      if([string]::IsNullOrWhiteSpace([string]$stillAgain.Name)){throw "Cannot prove whether game PID $ProcessId still exists after the process-handle retry."}
      if($stillAgain.Name -notmatch '^(?i:Burnout.*\.exe|TUB_Burnout_PC_External\.exe|BrnGame\.exe)$'){return $null}
      throw "Live or uncertain game PID $ProcessId has no retained process handle/start identity: $firstError; retry: $retryError"
    }
  }
}
function Get-GameProcessSnapshots {
  $cims=@(Get-CimInstance Win32_Process -Filter "Name LIKE 'Burnout%.exe' OR Name='TUB_Burnout_PC_External.exe' OR Name='BrnGame.exe'" -ErrorAction Stop)
  $rows=@()
  foreach($cim in $cims){
    $live=Get-LiveGameProcessIdentity ([int]$cim.ProcessId)
    if($null -eq $live){continue}
    try{
      $image=$null
      if(![string]::IsNullOrWhiteSpace([string]$cim.ExecutablePath)){
        try{$image=[IO.Path]::GetFullPath([string]$cim.ExecutablePath)}catch{$image=$null}
      }
      $rows+=@([pscustomobject]@{pid=[int]$cim.ProcessId;name=[string]$cim.Name;image_path=$image;start_time_utc=$live.start_time_utc;start_ticks=[long]$live.start_ticks})
    }finally{$live.process.Dispose()}
  }
  return ,@($rows|Sort-Object pid)
}
function Get-GameProcessFast {
  $cims=@(Get-CimInstance Win32_Process -Filter "Name LIKE 'Burnout%.exe' OR Name='TUB_Burnout_PC_External.exe' OR Name='BrnGame.exe'" -ErrorAction Stop)
  $rows=@()
  foreach($cim in $cims){
    $live=Get-LiveGameProcessIdentity ([int]$cim.ProcessId)
    if($null -eq $live){continue}
    try{
      $image=$null
      if(![string]::IsNullOrWhiteSpace([string]$cim.ExecutablePath)){
        try{$image=[IO.Path]::GetFullPath([string]$cim.ExecutablePath)}catch{$image=$null}
      }
      $rows+=@([pscustomobject]@{pid=[int]$cim.ProcessId;name=[string]$cim.Name;image_path=$image;start_ticks=[long]$live.start_ticks;parent_pid=[int]$cim.ParentProcessId})
    }finally{$live.process.Dispose()}
  }
  return ,@($rows|Sort-Object pid)
}
function Get-WindowsPowerShellChildModulePath {
  $powershellCommand=Get-Command powershell.exe -CommandType Application -ErrorAction Stop|Select-Object -First 1
  if($null -eq $powershellCommand -or [string]::IsNullOrWhiteSpace([string]$powershellCommand.Source)){throw 'Cannot resolve the exact Windows PowerShell executable for run_case.'}
  $powershellPath=[IO.Path]::GetFullPath([string]$powershellCommand.Source)
  $powershellHome=Split-Path -Parent $powershellPath
  $systemModules=[IO.Path]::GetFullPath((Join-Path $powershellHome 'Modules'))
  if(!(Test-Path -LiteralPath $systemModules -PathType Container)){throw "Windows PowerShell system module path is missing: $systemModules"}
  $candidates=@()
  if($env:ProgramFiles){$candidates+=@((Join-Path $env:ProgramFiles 'WindowsPowerShell\Modules'))}
  $candidates+=@($systemModules)
  $roots=@()
  foreach($candidate in $candidates){
    if(Test-Path -LiteralPath $candidate -PathType Container){
      $full=[IO.Path]::GetFullPath($candidate)
      if($roots -notcontains $full){$roots+=@($full)}
    }
  }
  if($roots.Count -eq 0 -or $roots -notcontains $systemModules){throw 'Clean Windows PowerShell module roots do not include the executable-matched system Modules directory.'}
  return [pscustomobject]@{executable=$powershellPath;module_roots=$roots;module_path=($roots -join [IO.Path]::PathSeparator)}
}
function Start-WindowsPowerShellChild([object]$Settings,[string[]]$ArgumentList,[string]$Stdout,[string]$Stderr) {
  if($null -eq $Settings -or [IO.Path]::GetFullPath([string]$Settings.executable) -ine [IO.Path]::GetFullPath([string](Get-Command powershell.exe -CommandType Application -ErrorAction Stop|Select-Object -First 1 -ExpandProperty Source))){throw 'Windows PowerShell child settings are not bound to the installed powershell.exe.'}
  $modulePathBefore=[Environment]::GetEnvironmentVariable('PSModulePath','Process')
  try{
    [Environment]::SetEnvironmentVariable('PSModulePath',[string]$Settings.module_path,'Process')
    if([string]::IsNullOrWhiteSpace($Stdout) -or [string]::IsNullOrWhiteSpace($Stderr) -or $Stdout -ceq $Stderr){throw 'Windows PowerShell child stdout/stderr paths must be distinct non-empty paths.'}
    return Start-Process -FilePath ([string]$Settings.executable) -ArgumentList $ArgumentList -PassThru -WindowStyle Hidden -RedirectStandardOutput $Stdout -RedirectStandardError $Stderr
  }finally{
    [Environment]::SetEnvironmentVariable('PSModulePath',$modulePathBefore,'Process')
  }
}
function Test-ReviewedStart([string]$StartUtc,[long]$Ticks){
  try{return ([DateTime]::Parse($StartUtc).ToUniversalTime().Ticks -eq $Ticks)}catch{return $false}
}
function Test-NoReparseChain([string]$Root,[string[]]$RelativePaths){
  $rootFull=[IO.Path]::GetFullPath($Root).TrimEnd('\')
  foreach($relative in $RelativePaths){
    $current=[IO.Path]::GetFullPath((Join-Path $rootFull ($relative -replace '/','\')))
    $rootPrefix=$rootFull.TrimEnd('\')+'\'
    if(!$current.StartsWith($rootPrefix,[StringComparison]::OrdinalIgnoreCase)){return $false}
    while($current.StartsWith($rootPrefix,[StringComparison]::OrdinalIgnoreCase)){
      if(!(Test-Path -LiteralPath $current)){return $false}
      $item=Get-Item -LiteralPath $current -Force
      if($item.Attributes -band [IO.FileAttributes]::ReparsePoint){return $false}
      $current=[IO.Path]::GetDirectoryName($current)
      if(!$current){return $false}
      $current=[IO.Path]::GetFullPath($current)
    }
    if($current -ine $rootFull){return $false}
    $rootItem=Get-Item -LiteralPath $rootFull -Force
    if($rootItem.Attributes -band [IO.FileAttributes]::ReparsePoint){return $false}
  }
  return $true
}
function Get-RuntimeIntegrity {
  $bad=[Collections.Generic.List[string]]::new()
  $pinned=@($runtimeBinding.overlay_files.PSObject.Properties.Name)+@($runtimeBinding.executed_dependency_files.PSObject.Properties.Name)
  if(!(Test-NoReparseChain $runtimeRoot $pinned)){$bad.Add('private_runtime_reparse_chain')}
  if(!(Test-NoReparseChain $protectedRuntimeRoot @('tools/tests/run_case.ps1','tools/diagnostics/flow_run.ps1','tools/diagnostics/_box_lock.ps1'))){$bad.Add('protected_runtime_reparse_chain')}
  $head=(& git -C $runtimeRoot rev-parse HEAD).Trim();$tree=(& git -C $runtimeRoot rev-parse 'HEAD^{tree}').Trim()
  if($head -cne $runtimeBinding.upstream_commit -or $tree -cne $runtimeBinding.upstream_tree){$bad.Add('private_runtime_git_identity')}
  $status=@(& git -C $runtimeRoot status --porcelain --untracked-files=all)
  $paths=@($status|ForEach-Object {$_.Substring(3).Trim()}|Sort-Object)
  $expected=@('tools/diagnostics/flow_run.ps1','tools/tests/run_case.ps1')
  $expected=@($expected|Sort-Object)
  if((Compare-Object $expected $paths).Count -ne 0){$bad.Add('private_runtime_changed_paths')}
  foreach($rel in $runtimeBinding.overlay_files.PSObject.Properties.Name){
    $spec=$runtimeBinding.overlay_files.PSObject.Properties[$rel].Value;$file=Join-Path $runtimeRoot ($rel -replace '/','\')
    if(!(Test-Path -LiteralPath $file -PathType Leaf) -or (Get-Item -LiteralPath $file).Length -ne [long]$spec.bytes -or (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -cne $spec.sha256){$bad.Add(('private_runtime_file:'+ $rel))}
  }
  foreach($entry in $runtimeBinding.executed_dependency_files.PSObject.Properties){
    $file=Join-Path $runtimeRoot ($entry.Name -replace '/','\')
    if(!(Test-Path -LiteralPath $file -PathType Leaf) -or (Get-Item -LiteralPath $file).Length -ne [long]$entry.Value.bytes -or (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -cne $entry.Value.sha256){$bad.Add(('executed_runtime_dependency:'+ $entry.Name))}
  }
  foreach($entry in $runtimeBinding.protected_source_runtime_files.PSObject.Properties){
    $file=Join-Path $protectedRuntimeRoot ($entry.Name -replace '/','\')
    if(!(Test-Path -LiteralPath $file -PathType Leaf) -or (Get-Item -LiteralPath $file).Length -ne [long]$entry.Value.bytes -or (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -cne $entry.Value.sha256){$bad.Add(('protected_runtime_file:'+ $entry.Name))}
  }
  return [ordered]@{pass=($bad.Count -eq 0);failures=@($bad);runtime_head=$head;runtime_tree=$tree;status_paths=$paths;checked_utc=[DateTime]::UtcNow.ToString('o')}
}
function Write-RunPolicyAbort([string]$Reason){
  $path=Join-Path $runDir 'RESOURCE_RUN_POLICY_ABORT.json'
  if(Test-Path -LiteralPath $path){return}
  $record=[ordered]@{schema=1;status='stop_resource_driver_input_and_restore';suite=$Suite;slot=$slot;run_name=$RunName;reason=$Reason;created_utc=[DateTime]::UtcNow.ToString('o')}
  [IO.File]::WriteAllText($path,($record|ConvertTo-Json -Depth 5)+"`n",[Text.UTF8Encoding]::new($false))
}
if($review.allow_concurrent_games -ne $true -or $reviewPeerLimit -ne 100 -or $reviewPeers.Count -ne 0){throw 'Root V5 requires a 100-peer dynamic handoff ceiling with no stale static PID allowlist.'}
$runtimeIntegrityPre=Get-RuntimeIntegrity
if($runtimeIntegrityPre.pass -ne $true){throw ('Private runtime overlay failed prelaunch integrity: '+($runtimeIntegrityPre.failures -join ', '))}
$windowsPowerShellChild=Get-WindowsPowerShellChildModulePath
$runRoot=[IO.Path]::GetFullPath([string]$plan.runtime_output_root)
$runDir=Join-Path $runRoot $RunName
$stageRoot=[IO.Path]::GetFullPath((Join-Path (Join-Path $suiteRoot 'stage') $RunName))
$slotDir=Join-Path $stageRoot 'slot';$dataDir=Join-Path $stageRoot 'data'
$expectedOwnedPath=[IO.Path]::GetFullPath((Join-Path $slotDir 'Burnout_PC.exe'))
$expectedProfilePath=Get-ResourceV5ProfilePath $stageRoot $slot
if(Test-Path -LiteralPath $runDir){throw "Run directory already exists; refusing to overwrite: $runDir"}
if(Test-Path -LiteralPath $stageRoot){throw "Private stage already exists; refusing to overwrite: $stageRoot"}
$prelaunchGames=Get-GameProcessSnapshots
$prelaunchCampaignPeers=Get-ResourceV5PeerAuthorityRows -RepoRoot $repoRoot -Authority $parallelAuthority -Processes $prelaunchGames
$normalProfilePaths=@($protectedConfigRoster.profile_config_log_preserved|Where-Object {([string]$_.relative_path).Replace('\','/') -match '^Memcard(?:_[0-9]+)?/Profile\.sav$'}|ForEach-Object {[IO.Path]::GetFullPath((Join-Path $normalInstallRoot ([string]$_.relative_path -replace '/','\')))})
if($normalProfilePaths.Count -ne 11 -or @($normalProfilePaths|Where-Object {[string]::IsNullOrWhiteSpace([string]$_)}).Count -gt 0){throw 'Current exact normal roster must supply its11 protected profile paths.'}
$prelaunchObservation=Resolve-ResourceV5ProcessObservations -Processes $prelaunchGames -CampaignPeers $prelaunchCampaignPeers -OwnedImagePath $expectedOwnedPath -OwnedStageRoot $stageRoot -OwnedProfilePath $expectedProfilePath -OwnedSlot $slot -OwnedProcessId 0 -OwnedStartTicks 0 -NormalInstallRoot $normalInstallRoot -NormalProfilePaths $normalProfilePaths -SharedOutputPath 'D:\cgsresourcedump_0.txt' -SharedOutputMutex 'Local\BurnoutPC_ResourceDumpStats_v1' -MaxKnownPeers $reviewPeerLimit
$prelaunchPeers=@($prelaunchObservation.known_campaign_peers)
$prelaunchForeignGames=@($prelaunchObservation.foreign_games)

$candidateRecordPath=Get-ResourceV5Path $repoRoot ([string]$plan.parallel_native_policy.candidate_authority_supplement.path)
$candidateRecord=Get-Content -LiteralPath $candidateRecordPath -Raw|ConvertFrom-Json
$currentProfileRecord=[pscustomobject]@{normal_profile_observation_sha256=[string]$plan.fixture.sha256}
$normalBefore=Get-TextureNormalSnapshot -Roster $protectedConfigRoster -NormalRoot $normalInstallRoot -CandidateRecord $currentProfileRecord
if($PreflightOnly){
  $budgets=Assert-TextureVolumeBudgets -Budget $physicalPlan -StagePath $stageRoot -OutputPath $runDir -StagePending $true -Phase 'preflight-only'
  $preflightRecord=[ordered]@{status='pass';mode='preflight_only_no_game_or_stage';candidate_source=$expectedB5;candidate_exe_sha256=$expectedExe;normal_rows=$normalBefore.Count;runtime_integrity=$runtimeIntegrityPre;volume_budgets=$budgets;checked_utc=[DateTime]::UtcNow.ToString('o')}
  [IO.File]::WriteAllText((Join-Path $packetRoot ('pre/TEXTURE_FULL_PREFLIGHT_PS'+$PSVersionTable.PSVersion.Major+'.json')),($preflightRecord|ConvertTo-Json -Depth 10)+"`n",[Text.UTF8Encoding]::new($false))
  $resourceSuiteMutex.ReleaseMutex();$resourceSuiteMutex.Dispose();return
}
New-Item -ItemType Directory -Force $runRoot|Out-Null
if(Test-Path -LiteralPath $runDir){throw "Run directory already exists; refusing to overwrite: $runDir"}
New-Item -ItemType Directory -Path $runDir|Out-Null
[IO.File]::WriteAllText((Join-Path $runDir 'NORMAL_PROTECTION_BEFORE.json'),(@{rows=$normalBefore;normal_writes_performed=$false}|ConvertTo-Json -Depth 8)+"`n",[Text.UTF8Encoding]::new($false))
$firstObservationLedgerPath=Join-Path $runDir 'CAMPAIGN_PEER_FIRST_OBSERVATIONS.jsonl'
$firstObservationSeen=@{}
Add-ResourceV5FirstObservation -RepoRoot $repoRoot -OwnedRunRoot $runDir -OwnedSuite $Suite -OwnedRunName $RunName -LedgerPath $firstObservationLedgerPath -Phase 'prelaunch' -Observation ([pscustomobject]@{processes=$prelaunchObservation.processes;policy_path=$parallelAuthority.policy_path;delegation_path=$parallelAuthority.delegation_path}) -Seen $firstObservationSeen -PolicySha256 $parallelPolicySha256
$buildEvidence=Join-Path $runDir 'build_provenance'
New-Item -ItemType Directory -Path $buildEvidence|Out-Null
Copy-Item -LiteralPath $receiptPath -Destination (Join-Path $buildEvidence 'SHIPPING_BUILD_RECEIPT.json')
Copy-Item -LiteralPath $provPath -Destination (Join-Path $buildEvidence 'Burnout_PC.exe.provenance.json')
Copy-Item -LiteralPath $buildResultPath -Destination (Join-Path $buildEvidence 'NATIVE_LINK_RECEIPT.json')
$expectedStage=[IO.Path]::GetFullPath((Join-Path (Join-Path $suiteRoot 'stage') $RunName))
if([IO.Path]::GetFullPath([string]$staging.stage_root) -ine $expectedStage -or [IO.Path]::GetFullPath([string]$binding.private_stage_root) -ine $expectedStage){throw 'Root stage paths do not bind this exact run-owned directory.'}
if([IO.Path]::GetFullPath([string]$staging.slot_directory) -ine [IO.Path]::GetFullPath($slotDir) -or [IO.Path]::GetFullPath([string]$staging.data_directory) -ine [IO.Path]::GetFullPath($dataDir)){throw 'STAGING sibling slot/data paths differ from the exact run-owned stage.'}
if(Test-Path -LiteralPath $stageRoot){throw "Private stage already exists; refusing to overwrite: $stageRoot"}
$stageCreated=$false;$gameLaunched=$false;$caseExit=$null;$profileBefore=$null;$phaseStopReceipt=$null;$phaseRequestReceipt=$null;$policyMonitorError=$null;$ownerRecord=$null
try {
  $manifestTool=Join-Path $packetRoot 'GetResourceDataManifest.ps1'
  $sourceManifestPath=Join-Path $runDir 'DATA_SOURCE_MANIFEST.json'
  $stageManifestPath=Join-Path $runDir 'DATA_STAGE_PRELAUNCH_MANIFEST.json'
  $null=& $manifestTool -Path ([string]$staging.data_source_path) -FrozenSnapshotPath $frozenSnapshotPath -Output $sourceManifestPath *> (Join-Path $runDir 'data_manifest_source.log')
  $sourceManifest=Get-Content -LiteralPath $sourceManifestPath -Raw|ConvertFrom-Json
  $actualExcludedPaths=[System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
  foreach($excludedRow in @($sourceManifest.selection.excluded_runtime_files)){[void]$actualExcludedPaths.Add([string]$excludedRow.path)}
  $expectedExcludedPaths=[System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
  foreach($excludedPath in @($frozenDataPlan.excluded_runtime_files)){[void]$expectedExcludedPaths.Add([string]$excludedPath)}
  if($sourceManifest.manifest_sha256 -cne $staging.data_source_manifest_sha256 -or
     $sourceManifest.selection.kind -cne 'frozen_asset_roster' -or
     [int]$sourceManifest.file_count -ne [int]$frozenDataPlan.file_count -or
     [long]$sourceManifest.bytes -ne [long]$frozenDataPlan.bytes -or
     $sourceManifest.selection.snapshot_sha256 -cne [string]$frozenDataPlan.snapshot_receipt_sha256 -or
     $sourceManifest.selection.asset_roster_sha256 -cne [string]$frozenDataPlan.source_roster_sha256 -or
     !$actualExcludedPaths.SetEquals($expectedExcludedPaths)){throw 'Root-bound frozen asset manifest or excluded runtime-file set differs from the exact selected snapshot/roster.'}
  $configSource=[IO.Path]::GetFullPath([string]$staging.config_source_path)
  $configSourceItem=Get-Item -LiteralPath $configSource -Force
  if($configSourceItem.Attributes -band [IO.FileAttributes]::ReparsePoint -or
     [long]$configSourceItem.Length -ne [long]$protectedConfigPlan.bytes -or
     (Get-FileHash -LiteralPath $configSource -Algorithm SHA256).Hash.ToLowerInvariant() -cne [string]$protectedConfigPlan.sha256 -or
     [string]$staging.config_source_sha256 -cne [string]$protectedConfigPlan.sha256){throw 'Separate protected config source bytes differ from the Root-bound normal-install roster.'}
  $dataSourceBytes=[long]$sourceManifest.bytes
  if($dataSourceBytes -ne [long]$staging.run_policy.data_source_bytes){throw 'Root-bound source data byte total differs from STAGING.'}
  $storageBeforeCopy=Assert-TextureVolumeBudgets -Budget $physicalPlan -StagePath $stageRoot -OutputPath $runDir -StagePending $true -Phase 'before-private-data-hardlinks'
  New-Item -ItemType Directory -Path (Split-Path -Parent $stageRoot) -Force|Out-Null
  New-Item -ItemType Directory -Path $stageRoot -Force|Out-Null
  $stageCreated=$true
  $owner=[ordered]@{schema=2;owner='Run.ps1';suite=$Suite;slot=$slot;run_name=$RunName;candidate_exe_sha256=$expectedExe;stage_root=$stageRoot;runtime_workflow_commit=$runtimeBinding.upstream_commit;runtime_workflow_tree=$runtimeBinding.upstream_tree;runtime_root_path=$runtimeRoot;runtime_overlay_manifest_sha256=$runtimeBinding.overlay_package_manifest_sha256;runtime_overlay_seal_sha256=$runtimeBinding.overlay_package_seal_sha256;runtime_run_case_sha256=$runtimeBinding.overlay_files.'tools/tests/run_case.ps1'.sha256;runtime_flow_run_sha256=$runtimeBinding.overlay_files.'tools/diagnostics/flow_run.ps1'.sha256;phase_done_requester_sha256=$runtimeBinding.phase_done_requester.sha256;created_utc=[DateTime]::UtcNow.ToString('o')}
  [IO.File]::WriteAllText((Join-Path $stageRoot 'RESOURCE_STAGE_OWNER.json'),($owner|ConvertTo-Json -Depth 5)+"`n",[Text.UTF8Encoding]::new($false))
  New-Item -ItemType Directory -Path $slotDir,$dataDir -Force|Out-Null

  # Copy every file explicitly listed by the compile/link receipt, checking source bytes before copy.
  $payload=@()
  foreach($property in $buildReceipt.files.PSObject.Properties){
    $key=[string]$property.Name
    if($key -notmatch '^shipping_out[\\/]'){continue}
    $relative=($key -replace '^shipping_out[\\/]+','').Replace('/','\')
    $src=Join-Path $shippingOut $relative
    if(!(Test-Path -LiteralPath $src -PathType Leaf)){throw "Receipt-listed payload missing: $src"}
    $actual=(Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash.ToLowerInvariant()
    if($actual -cne [string]$property.Value.sha256){throw "Receipt-listed payload changed: $relative"}
    $dst=Join-Path $slotDir $relative
    New-Item -ItemType Directory -Force (Split-Path -Parent $dst)|Out-Null
    Copy-Item -LiteralPath $src -Destination $dst
    if((Get-FileHash -LiteralPath $dst -Algorithm SHA256).Hash.ToLowerInvariant() -cne $actual){throw "Staged payload hash mismatch: $relative"}
    $payload+=@([ordered]@{path=$relative;bytes=[long]$property.Value.bytes;sha256=$actual})
  }
  if((Get-FileHash -LiteralPath (Join-Path $slotDir 'Burnout_PC.exe') -Algorithm SHA256).Hash.ToLowerInvariant() -cne $expectedExe){throw 'Private stage executable hash differs.'}

  # Copy only the frozen roster's immutable assets. Source profiles/configs/logs and other
  # runtime-mutables are recorded in the source manifest but never enter the private asset stage.
  $dataCopyReceipt=Copy-FrozenResourceData -SourceRoot ([string]$staging.data_source_path) -DestinationRoot $dataDir -Manifest $sourceManifest
  $dataCopyReceiptPath=Join-Path $runDir 'DATA_COPY_RECEIPT.json'
  [IO.File]::WriteAllText($dataCopyReceiptPath,($dataCopyReceipt|ConvertTo-Json -Depth 12)+"`n",[Text.UTF8Encoding]::new($false))
  $dataCopyReceiptHash=(Get-FileHash -LiteralPath $dataCopyReceiptPath -Algorithm SHA256).Hash.ToLowerInvariant()
  if($dataCopyReceipt.status -cne 'complete' -or $dataCopyReceipt.source_manifest_sha256 -cne $sourceManifest.manifest_sha256 -or
     [int]$dataCopyReceipt.file_count -ne [int]$sourceManifest.file_count -or [long]$dataCopyReceipt.bytes -ne [long]$sourceManifest.bytes){throw 'Frozen asset copy receipt does not bind every selected source manifest row.'}
  $null=& $manifestTool -Path $dataDir -Output $stageManifestPath *> (Join-Path $runDir 'data_manifest_stage.log')
  $stageManifest=Get-Content -LiteralPath $stageManifestPath -Raw|ConvertFrom-Json
  if($stageManifest.manifest_sha256 -cne $sourceManifest.manifest_sha256 -or
     [int]$stageManifest.file_count -ne [int]$sourceManifest.file_count -or
     [long]$stageManifest.bytes -ne [long]$sourceManifest.bytes -or
     [int]$stageManifest.mutable_count -ne 0){throw 'Private asset stage differs from the exact frozen source roster or contains runtime-mutables before launch.'}
  $privateConfigPath=Join-Path $slotDir ([string]$privateDisplayPlan.private_slot_relative_path)
  $privateConfigTool=Join-Path $packetRoot 'NewPrivateResourceConfig.ps1'
  $configDerivation=& $privateConfigTool -SourcePath $configSource -DestinationPath $privateConfigPath `
    -ExpectedSourceSha256 ([string]$protectedConfigPlan.sha256) -ExpectedSourceBytes ([long]$protectedConfigPlan.bytes) `
    -ExpectedPrivateSha256 ([string]$privateDisplayPlan.derived_sha256) `
    -SourceWidth ([int]$privateDisplayPlan.source_values.Width) -SourceHeight ([int]$privateDisplayPlan.source_values.Height) `
    -SourceFullscreen ([int]$privateDisplayPlan.source_values.Fullscreen) -PrivateWidth ([int]$privateDisplayPlan.private_values.Width) `
    -PrivateHeight ([int]$privateDisplayPlan.private_values.Height) -PrivateFullscreen ([int]$privateDisplayPlan.private_values.Fullscreen)
  if($configDerivation.status -cne 'derived_private_display_config' -or $configDerivation.source_sha256 -cne $protectedConfigPlan.sha256 -or
     $configDerivation.private_sha256 -cne $privateDisplayPlan.derived_sha256 -or $configDerivation.private_bytes -ne $privateDisplayPlan.derived_bytes -or
     $configDerivation.source_unchanged -ne $true){throw 'Private slot config derivation receipt does not match the exact Root-bound display-only transform.'}
  $configDerivationReceiptPath=Join-Path $runDir 'PRIVATE_CONFIG_DERIVATION.json'
  [IO.File]::WriteAllText($configDerivationReceiptPath,($configDerivation|ConvertTo-Json -Depth 8)+"`n",[Text.UTF8Encoding]::new($false))
  $configDerivationReceiptHash=(Get-FileHash -LiteralPath $configDerivationReceiptPath -Algorithm SHA256).Hash.ToLowerInvariant()
  $slotConfigHash=(Get-FileHash -LiteralPath $privateConfigPath -Algorithm SHA256).Hash.ToLowerInvariant()
  if($slotConfigHash -cne [string]$privateDisplayPlan.derived_sha256){throw 'Private slot config hash differs from the reviewed Display-only derivation.'}
  $storageBeforeRunCase=Assert-TextureVolumeBudgets -Budget $physicalPlan -StagePath $stageRoot -OutputPath $runDir -StagePending $false -Phase 'before-run-case'
  $slotProfile=Join-Path $dataDir ('Memcard_'+$slot+'\Profile.sav')
  if(Test-Path -LiteralPath $slotProfile){$profileBefore=[ordered]@{existed=$true;sha256=(Get-FileHash -LiteralPath $slotProfile -Algorithm SHA256).Hash.ToLowerInvariant();bytes=(Get-Item -LiteralPath $slotProfile).Length}}
  else{$profileBefore=[ordered]@{existed=$false;sha256=$null;bytes=0}}

  $prelaunch=[ordered]@{schema=3;status='root_reviewed_prelaunch_pass';suite=$Suite;slot=$slot;run_name=$RunName;candidate_source=$expectedB5;candidate_workflow_source=$expectedWorkflow;candidate_exe_sha256=$expectedExe;shipping_receipt_sha256=(Get-FileHash -LiteralPath $receiptPath -Algorithm SHA256).Hash.ToLowerInvariant();profile_fixture_sha256=$plan.fixture.sha256;prelaunch_game_process_count=$prelaunchGames.Count;storage_budget_before_data_copy=$storageBeforeCopy;storage_budget_before_run_case=$storageBeforeRunCase;max_concurrent_other_games=$reviewPeerLimit;allowed_peer_processes=$prelaunchPeers;stage_root=$stageRoot;stage_owner_marker_sha256=(Get-FileHash -LiteralPath (Join-Path $stageRoot 'RESOURCE_STAGE_OWNER.json') -Algorithm SHA256).Hash.ToLowerInvariant();source_data_manifest_sha256=$sourceManifest.manifest_sha256;source_asset_file_count=$sourceManifest.file_count;source_asset_bytes=$sourceManifest.bytes;frozen_snapshot_receipt_sha256=$frozenDataPlan.snapshot_receipt_sha256;source_roster_sha256=$frozenDataPlan.source_roster_sha256;data_copy_receipt_path='DATA_COPY_RECEIPT.json';data_copy_receipt_sha256=$dataCopyReceiptHash;prelaunch_stage_manifest_sha256=$stageManifest.manifest_sha256;config_source_path=$configSource;config_source_sha256=$protectedConfigPlan.sha256;config_sha256=$slotConfigHash;private_config_path=$privateConfigPath;private_config_path_in_slot=$privateDisplayPlan.private_slot_relative_path;private_config_source_sha256=$protectedConfigPlan.sha256;private_config_sha256=$slotConfigHash;private_config_derivation_receipt_path='PRIVATE_CONFIG_DERIVATION.json';private_config_derivation_receipt_sha256=$configDerivationReceiptHash;private_display_width=[int]$privateDisplayPlan.private_values.Width;private_display_height=[int]$privateDisplayPlan.private_values.Height;private_display_fullscreen=[int]$privateDisplayPlan.private_values.Fullscreen;capture_frame_file_bytes=[long]$privateDisplayPlan.capture.frame_file_bytes;capture_frame_reserve_bytes=[long]$privateDisplayPlan.capture.reserve_bytes_per_frame;config_source_roster_sha256=$protectedConfigPlan.roster_sha256;runtime_workflow_source=$runtimeBinding.upstream_commit;runtime_workflow_tree=$runtimeBinding.upstream_tree;runtime_root_path=$runtimeRoot;protected_runtime_root_path=$protectedRuntimeRoot;runtime_overlay_manifest_sha256=$runtimeBinding.overlay_package_manifest_sha256;runtime_overlay_seal_sha256=$runtimeBinding.overlay_package_seal_sha256;runtime_files=$runtimeBinding.overlay_files;phase_done_requester_sha256=$runtimeBinding.phase_done_requester.sha256;runtime_overlay_review_receipt_sha256=$runtimeBinding.review_receipt_sha256;runtime_verify_receipt_sha256=$runtimeBinding.verify_receipt_sha256;runtime_integrity=$runtimeIntegrityPre;windows_powershell_child=$windowsPowerShellChild;payload=$payload;profile_before=$profileBefore;binding_sha256=$bindingHash;staging_sha256=$stagingHash;root_review_sha256=(Get-FileHash -LiteralPath $reviewPath -Algorithm SHA256).Hash.ToLowerInvariant();created_utc=[DateTime]::UtcNow.ToString('o')}
  $prelaunch['root_parallel_policy_path']=$parallelAuthority.policy_path
  $prelaunch['root_parallel_policy_sha256']=$parallelPolicySha256
  $prelaunch['root_parallel_delegation_path']=$parallelAuthority.delegation_path
  $prelaunch['root_parallel_delegation_sha256']=$parallelAuthority.delegation_sha256
  $prelaunch['parallel_census_policy']='informational; exact owned handoffs are resolved dynamically'
  $prelaunch['known_campaign_peer_count']=$prelaunchPeers.Count
  $prelaunch['foreign_game_count']=$prelaunchForeignGames.Count
  $prelaunch['known_campaign_peers']=$prelaunchPeers
  $prelaunch['allowed_peer_processes']=$prelaunchPeers
  $prelaunch['foreign_game_processes']=$prelaunchForeignGames
  $prelaunch['first_observation_ledger_path']='CAMPAIGN_PEER_FIRST_OBSERVATIONS.jsonl'
  $prelaunch['data_source_path']=[IO.Path]::GetFullPath([string]$staging.data_source_path)
  $prelaunch['frozen_snapshot_receipt_path']=[string]$staging.frozen_snapshot_receipt_path
  $prelaunch['source_roster_path']=[string]$staging.source_roster_path
  [IO.File]::WriteAllText((Join-Path $runDir 'PRELAUNCH.json'),($prelaunch|ConvertTo-Json -Depth 10)+"`n",[Text.UTF8Encoding]::new($false))
  $stagingReceipt=[ordered]@{schema=3;suite=$Suite;slot=$slot;run_name=$RunName;candidate_exe_sha256=$expectedExe;staged_exe_path=(Join-Path $slotDir 'Burnout_PC.exe');stage_root=$stageRoot;max_concurrent_other_games=$reviewPeerLimit;max_game_instances=[int]$staging.run_policy.max_game_instances;runtime_workflow_source=$runtimeBinding.upstream_commit;runtime_workflow_tree=$runtimeBinding.upstream_tree;runtime_root_path=$runtimeRoot;protected_runtime_root_path=$protectedRuntimeRoot;runtime_overlay_manifest_sha256=$runtimeBinding.overlay_package_manifest_sha256;runtime_overlay_seal_sha256=$runtimeBinding.overlay_package_seal_sha256;phase_done_requester_sha256=$runtimeBinding.phase_done_requester.sha256;runtime_verify_receipt_sha256=$runtimeBinding.verify_receipt_sha256;windows_powershell_child=$windowsPowerShellChild;source_data_manifest_sha256=$sourceManifest.manifest_sha256;source_asset_file_count=$sourceManifest.file_count;source_asset_bytes=$sourceManifest.bytes;frozen_snapshot_receipt_sha256=$frozenDataPlan.snapshot_receipt_sha256;source_roster_sha256=$frozenDataPlan.source_roster_sha256;data_copy_receipt_sha256=$dataCopyReceiptHash;prelaunch_stage_manifest_sha256=$stageManifest.manifest_sha256;config_source_path=$configSource;config_source_sha256=$protectedConfigPlan.sha256;config_sha256=$slotConfigHash;private_config_path=$privateConfigPath;private_config_path_in_slot=$privateDisplayPlan.private_slot_relative_path;private_config_source_sha256=$protectedConfigPlan.sha256;private_config_sha256=$slotConfigHash;private_config_derivation_receipt_path='PRIVATE_CONFIG_DERIVATION.json';private_config_derivation_receipt_sha256=$configDerivationReceiptHash;private_display_width=[int]$privateDisplayPlan.private_values.Width;private_display_height=[int]$privateDisplayPlan.private_values.Height;private_display_fullscreen=[int]$privateDisplayPlan.private_values.Fullscreen;capture_frame_file_bytes=[long]$privateDisplayPlan.capture.frame_file_bytes;capture_frame_reserve_bytes=[long]$privateDisplayPlan.capture.reserve_bytes_per_frame;config_source_roster_sha256=$protectedConfigPlan.roster_sha256;payload=$payload;profile_before=$profileBefore;storage_budget_before_data_copy=$storageBeforeCopy;storage_budget_before_run_case=$storageBeforeRunCase;game_launched=$false}
  $stagingReceipt['root_parallel_policy_path']=$parallelAuthority.policy_path
  $stagingReceipt['root_parallel_policy_sha256']=$parallelPolicySha256
  $stagingReceipt['root_parallel_delegation_sha256']=$parallelAuthority.delegation_sha256
  $stagingReceipt['parallel_census_policy']='informational; exact owned handoffs are resolved dynamically'
  $stagingReceipt['prelaunch_known_campaign_peer_count']=$prelaunchPeers.Count
  $stagingReceipt['prelaunch_foreign_game_count']=$prelaunchForeignGames.Count
  $stagingReceipt['first_observation_ledger_path']='CAMPAIGN_PEER_FIRST_OBSERVATIONS.jsonl'
  $stagingReceipt['data_source_path']=[IO.Path]::GetFullPath([string]$staging.data_source_path)
  $stagingReceipt['frozen_snapshot_receipt_path']=[string]$staging.frozen_snapshot_receipt_path
  $stagingReceipt['source_roster_path']=[string]$staging.source_roster_path
  [IO.File]::WriteAllText((Join-Path $runDir 'STAGING_RECEIPT.json'),($stagingReceipt|ConvertTo-Json -Depth 10)+"`n",[Text.UTF8Encoding]::new($false))

  $casePath=Join-Path $suiteRoot $(if($Suite -eq 'resource_windows'){'Case_ResourceWindows.ps1'}else{'Case_ResourceStatsAllocator.ps1'})
  $runCase=Join-Path $runtimeRoot 'tools\tests\run_case.ps1'
  $pointerRoot=Join-Path $runDir 'run_case_pointer'
  New-Item -ItemType Directory -Force $pointerRoot|Out-Null
  $stdout=Join-Path $runDir 'run_case.stdout.log';$stderr=Join-Path $runDir 'run_case.stderr.log'
  $arguments=@('-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$runCase`"",'-Case',"`"$casePath`"",'-RunDir',"`"$runDir`"",'-RunsRoot',"`"$pointerRoot`"",'-Slot',"$slot",'-GameDir',"`"$slotDir`"",'-WorkingDirectory',"`"$dataDir`"",'-MaxConcurrentOtherGames',"$reviewPeerLimit")
  $parentModulePathBefore=[Environment]::GetEnvironmentVariable('PSModulePath','Process')
  $caseProcess=Start-WindowsPowerShellChild $windowsPowerShellChild $arguments $stdout $stderr
  $gameLaunched=$true
  $parentModulePathAfter=[Environment]::GetEnvironmentVariable('PSModulePath','Process')
  if($parentModulePathAfter -cne $parentModulePathBefore){throw 'Outer runner PSModulePath was not restored exactly after starting Windows PowerShell 5.1.'}
  $childLaunchReceipt=[ordered]@{schema=1;status='windows_powershell_child_started_clean';suite=$Suite;slot=$slot;run_name=$RunName;process_id=[int]$caseProcess.Id;executable=$windowsPowerShellChild.executable;module_roots=@($windowsPowerShellChild.module_roots);child_module_path=$windowsPowerShellChild.module_path;parent_module_path_before=$parentModulePathBefore;parent_module_path_after=$parentModulePathAfter;parent_module_path_restored=($parentModulePathAfter -ceq $parentModulePathBefore);created_utc=[DateTime]::UtcNow.ToString('o')}
  [IO.File]::WriteAllText((Join-Path $runDir 'WINDOWS_POWERSHELL_LAUNCH_RECEIPT.json'),($childLaunchReceipt|ConvertTo-Json -Depth 6)+[Environment]::NewLine,[Text.UTF8Encoding]::new($false))
  $phaseDonePath=Join-Path $runDir 'RESOURCE_PHASE_DONE.json'
  $phaseWitnessPath=Join-Path $runDir 'RESOURCE_PHASE_DONE_WITNESS.json'
  $ownerRecordPath=Join-Path $runDir 'RESOURCE_GAME_OWNER.json'
  $expectedOwnedPath=[IO.Path]::GetFullPath((Join-Path $slotDir 'Burnout_PC.exe'))
  $pendingLaunch=$null;$adoptionReceiptPath=Join-Path $runDir 'RESOURCE_LAUNCH_ADOPTION.json'
  $adoptionDeadline=[DateTime]::UtcNow.AddSeconds(45).Ticks
  $caseStartTicks=[long]$caseProcess.StartTime.ToUniversalTime().Ticks
  $peerMonitorNext=[DateTime]::UtcNow
  while($true){
    $caseProcess.Refresh();if($caseProcess.HasExited){break}
    if([DateTime]::UtcNow -ge $peerMonitorNext){
      try{
        $null=Assert-TextureVolumeBudgets -Budget $physicalPlan -StagePath $stageRoot -OutputPath $runDir -StagePending $false -Phase 'live-owned-run'
        $sidecarUsed=[long]0
        foreach($output in @(Get-ChildItem -LiteralPath $runDir -Recurse -File -Force)){
          if($output.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Resource output reparse point appeared.'}
          if($output.Extension -ine '.bmp'){$sidecarUsed += [long]$output.Length}
        }
        foreach($output in @(Get-ChildItem -LiteralPath $dataDir -Recurse -File -Force)){
          if($output.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Resource mutable output reparse point appeared.'}
          if(!($output.Attributes -band [IO.FileAttributes]::ReadOnly)){$sidecarUsed += [long]$output.Length}
        }
        if($sidecarUsed -gt ($sidecarReserveBytes - 8388608)){throw 'Resource sidecar/log bound reached; retaining8MiB emergency restore reserve.'}
        $slotLogBytes=[long]0;foreach($file in @(Get-ChildItem -LiteralPath $slotDir -Filter '*.log' -File -Force)){$slotLogBytes+=[long]$file.Length}
        if($slotLogBytes -gt ([long]$physicalPlan.volumes.D.slot_log_bytes-8388608)){throw 'Owned D slot-log cap reached; scoped restore required.'}
        $fastGames=Get-GameProcessFast
        $ownedPid=0;$ownedStartTicks=[long]0
        $monitorGames=$fastGames
        $ownerAvailable=Test-Path -LiteralPath $ownerRecordPath
        if($ownerAvailable){
          if((!$pendingLaunch -or $pendingLaunch.status -cne 'driver_owner_confirmed') -and [DateTime]::UtcNow.Ticks -gt $adoptionDeadline){throw 'Resource driver owner arrived after the bounded launch adoption deadline.'}
          $ownerRecord=Get-Content -LiteralPath $ownerRecordPath -Raw|ConvertFrom-Json
          if(!$pendingLaunch){
            $firstOwnerRows=@($fastGames|Where-Object {[int]$_.pid -eq [int]$ownerRecord.pid})
            if($firstOwnerRows.Count -eq 0){$fastGames=Get-GameProcessFast;$monitorGames=$fastGames}
            $firstOwnerExeSha=(Get-FileHash -LiteralPath $expectedOwnedPath -Algorithm SHA256).Hash.ToLowerInvariant()
            $pendingLaunch=Get-ResourcePendingLaunch -Processes $fastGames -ExpectedImagePath $expectedOwnedPath -CaseProcessId ([int]$caseProcess.Id) -CaseStartTicks $caseStartTicks -NowTicks ([DateTime]::UtcNow.Ticks) -DeadlineTicks $adoptionDeadline -ExpectedExeSha256 $expectedExe -ActualExeSha256 $firstOwnerExeSha -Previous $null
            if(!$pendingLaunch){throw 'Driver owner receipt has no exact live new child to confirm.'}
          }
          Assert-ResourceDriverAdoption -Pending $pendingLaunch -Owner $ownerRecord -ExpectedImagePath $expectedOwnedPath -ExpectedStageRoot $stageRoot -ExpectedSlot $slot -ExpectedExeSha256 $expectedExe
          $ownedPid=[int]$ownerRecord.pid;$ownedStartTicks=[long]$ownerRecord.start_ticks
          $ownRows=@($fastGames|Where-Object {[int]$_.pid -eq $ownedPid})
          if($ownRows.Count -eq 1 -and ([int]$ownRows[0].parent_pid -ne [int]$caseProcess.Id -or [long]$ownRows[0].start_ticks -le $caseStartTicks)){throw 'Driver owner PID is not the exact new child of this retained run_case launch.'}
          if($ownRows.Count -gt 1 -or ($ownRows.Count -eq 1 -and ([int]$ownRows[0].pid -ne [int]$ownerRecord.pid -or !$ownerRecord.start_ticks -or [long]$ownRows[0].start_ticks -ne [long]$ownerRecord.start_ticks))){throw 'Monitored owned game path/PID/start identity changed.'}
          if($ownRows.Count -eq 1 -and ($null -eq $ownRows[0].image_path -or [IO.Path]::GetFullPath([string]$ownRows[0].image_path) -ine [IO.Path]::GetFullPath([string]$ownerRecord.image_path))){throw 'Monitored owned game PID no longer resolves to its exact private image path.'}
          if($pendingLaunch.status -cne 'driver_owner_confirmed'){$pendingLaunch.status='driver_owner_confirmed';[IO.File]::WriteAllText($adoptionReceiptPath,($pendingLaunch|ConvertTo-Json -Depth 5)+[Environment]::NewLine,[Text.UTF8Encoding]::new($false))}
        }
        if(!$ownerAvailable){
          if($pendingLaunch -and $pendingLaunch.status -ceq 'driver_owner_confirmed'){throw 'Confirmed Resource driver owner receipt disappeared.'}
          $pendingImageRows=@($fastGames|Where-Object {$_.image_path -and [IO.Path]::GetFullPath([string]$_.image_path) -ieq $expectedOwnedPath})
          $pendingExeSha=if($pendingImageRows.Count){(Get-FileHash -LiteralPath $expectedOwnedPath -Algorithm SHA256).Hash.ToLowerInvariant()}else{$expectedExe}
          $pendingLaunch=Get-ResourcePendingLaunch -Processes $fastGames -ExpectedImagePath $expectedOwnedPath -CaseProcessId ([int]$caseProcess.Id) -CaseStartTicks $caseStartTicks -NowTicks ([DateTime]::UtcNow.Ticks) -DeadlineTicks $adoptionDeadline -ExpectedExeSha256 $expectedExe -ActualExeSha256 $pendingExeSha -Previous $pendingLaunch
          if($pendingLaunch){
            [IO.File]::WriteAllText($adoptionReceiptPath,($pendingLaunch|ConvertTo-Json -Depth 5)+[Environment]::NewLine,[Text.UTF8Encoding]::new($false))
            # The independently proved new run_case child stays pending; all other
            # rows still receive exact collision/foreign checks during this interval.
            $monitorGames=@($fastGames|Where-Object {[int]$_.pid -ne [int]$pendingLaunch.pid})
          }
        }
        $campaignPeers=Get-ResourceV5PeerAuthorityRows -RepoRoot $repoRoot -Authority $parallelAuthority -Processes $monitorGames
        $monitorObservation=Resolve-ResourceV5ProcessObservations -Processes $monitorGames -CampaignPeers $campaignPeers -OwnedImagePath $expectedOwnedPath -OwnedStageRoot $stageRoot -OwnedProfilePath $slotProfile -OwnedSlot $slot -OwnedProcessId $ownedPid -OwnedStartTicks $ownedStartTicks -NormalInstallRoot $normalInstallRoot -NormalProfilePaths $normalProfilePaths -SharedOutputPath 'D:\cgsresourcedump_0.txt' -SharedOutputMutex 'Local\BurnoutPC_ResourceDumpStats_v1' -MaxKnownPeers $reviewPeerLimit
        Add-ResourceV5FirstObservation -RepoRoot $repoRoot -OwnedRunRoot $runDir -OwnedSuite $Suite -OwnedRunName $RunName -LedgerPath $firstObservationLedgerPath -Phase 'monitor' -Observation ([pscustomobject]@{processes=$monitorObservation.processes;policy_path=$parallelAuthority.policy_path;delegation_path=$parallelAuthority.delegation_path}) -Seen $firstObservationSeen -PolicySha256 $parallelPolicySha256
      }catch{if(!$policyMonitorError){$policyMonitorError=$_.Exception.Message;Add-Content -LiteralPath (Join-Path $runDir 'RUN_POLICY_MONITOR_FAILURE.txt') -Value $policyMonitorError;Write-RunPolicyAbort $policyMonitorError}}
      $peerMonitorNext=[DateTime]::UtcNow.AddSeconds(1)
    }
        if(!$phaseRequestAttempted -and (Test-Path -LiteralPath $phaseWitnessPath -PathType Leaf) -and (Test-Path -LiteralPath $ownerRecordPath -PathType Leaf)){
      try{
        $witness=Get-Content -LiteralPath $phaseWitnessPath -Raw|ConvertFrom-Json
        $ownerRecord=Get-Content -LiteralPath $ownerRecordPath -Raw|ConvertFrom-Json
        $restoreReceiptPath=Join-Path $runDir 'RESOURCE_RESTORE_RECEIPT.json'
        $driverReceiptPath=Join-Path $runDir 'RESOURCE_DRIVER_RECEIPT.json'
        $requestPath=Join-Path $runDir 'RESOURCE_PHASE_DONE_REQUEST.json'
        $expectedHelperPath=[IO.Path]::GetFullPath((Join-Path $packetRoot 'ResourceNativeDriver.ps1'))
        $helperIdentity=$witness.driver_process
        if($witness.restoration_verified -ne $true -or $witness.status -notin @('resource_actions_complete_and_restored','resource_actions_failed_but_restored') -or
           [int]$witness.slot -ne $slot -or $witness.suite -cne $Suite -or
           [int]$witness.process.pid -ne [int]$ownerRecord.pid -or [long]$witness.process.start_ticks -ne [long]$ownerRecord.start_ticks -or
           [IO.Path]::GetFullPath([string]$witness.process.image_path) -ine $expectedOwnedPath -or
           [IO.Path]::GetFullPath([string]$witness.process.stage_root) -ine [IO.Path]::GetFullPath($stageRoot) -or
           $witness.process.runtime_workflow_commit -cne $runtimeBinding.upstream_commit -or $witness.process.runtime_workflow_tree -cne $runtimeBinding.upstream_tree -or
           [IO.Path]::GetFullPath([string]$witness.process.runtime_root_path) -ine $runtimeRoot -or
           $witness.process.runtime_overlay_manifest_sha256 -cne $runtimeBinding.overlay_package_manifest_sha256 -or
           $witness.process.runtime_overlay_seal_sha256 -cne $runtimeBinding.overlay_package_seal_sha256 -or
           $witness.process.phase_done_requester_sha256 -cne $runtimeBinding.phase_done_requester.sha256){throw 'Semantic/restoration witness does not bind the exact owned game, suite, slot, and runtime.'}
        if([int]$helperIdentity.pid -le 0 -or [long]$helperIdentity.start_ticks -le 0 -or
           [int]$helperIdentity.parent_pid -ne [int]$caseProcess.Id -or
           [IO.Path]::GetFullPath([string]$helperIdentity.command_path) -ine $expectedHelperPath){throw 'Witness does not bind the exact Setup helper PID/start/parent/driver path.'}
        if(!(Test-Path -LiteralPath $restoreReceiptPath -PathType Leaf) -or !(Test-Path -LiteralPath $driverReceiptPath -PathType Leaf)){throw 'Final driver/restore receipts are not both present before phase notification.'}
        $driverReceipt=Get-Content -LiteralPath $driverReceiptPath -Raw|ConvertFrom-Json
        $restoreReceipt=Get-Content -LiteralPath $restoreReceiptPath -Raw|ConvertFrom-Json
        $driverSha=(Get-FileHash -LiteralPath $driverReceiptPath -Algorithm SHA256).Hash.ToLowerInvariant()
        $restoreSha=(Get-FileHash -LiteralPath $restoreReceiptPath -Algorithm SHA256).Hash.ToLowerInvariant()
        $witnessSha=(Get-FileHash -LiteralPath $phaseWitnessPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if($driverReceipt.suite -cne $Suite -or [int]$driverReceipt.slot -ne $slot -or
           [long]$driverReceipt.stimulus_process.start_ticks -ne [long]$helperIdentity.start_ticks -or
           $driverSha -cne $witness.driver_receipt_sha256 -or $restoreSha -cne $witness.restore_receipt_sha256 -or
           $restoreReceipt.status -cne 'restored' -or [int]$restoreReceipt.process.pid -ne [int]$ownerRecord.pid -or
           [long]$restoreReceipt.process.start_ticks -ne [long]$ownerRecord.start_ticks -or
           $driverReceipt.restore_complete -ne $true){throw 'Driver/restoration receipt hashes or exact process references differ from the completed witness.'}
        if(Test-Path -LiteralPath $phaseDonePath){throw 'Refusing to reuse an existing phase-done signal.'}
        if(Test-Path -LiteralPath $requestPath){throw 'Refusing to reuse an existing phase-done requester receipt.'}
        $helperStillRunning=$false
        $helperCim=$null
        try{$helperCim=Get-CimInstance Win32_Process -Filter "ProcessId=$([int]$helperIdentity.pid)" -ErrorAction Stop}catch{throw "Cannot query Setup helper identity before phase notification: $($_.Exception.Message)"}
        $helperProcess=$null
        try{
          $helperProcess=Get-Process -Id ([int]$helperIdentity.pid) -ErrorAction Stop
          $helperHandle=[IntPtr]$helperProcess.Handle
          $helperProcess.Refresh()
          $helperStartTicks=[long]$helperProcess.StartTime.ToUniversalTime().Ticks
          if($helperStartTicks -eq [long]$helperIdentity.start_ticks){
            if($helperHandle -eq [IntPtr]::Zero){throw 'Witnessed Setup helper has no retained process handle.'}
            if(!$helperProcess.HasExited){
              if($null -ne $helperCim -and ([int]$helperCim.ParentProcessId -ne [int]$caseProcess.Id -or [string]::IsNullOrWhiteSpace([string]$helperCim.CommandLine) -or $helperCim.CommandLine -notmatch [regex]::Escape($expectedHelperPath))){throw 'Live Setup helper handle does not match its witnessed PID/parent/command path.'}
              $helperStillRunning=$true
            }
          }elseif($null -ne $helperCim -and [int]$helperCim.ParentProcessId -eq [int]$caseProcess.Id -and $helperCim.CommandLine -match [regex]::Escape($expectedHelperPath)){throw 'A new Resource Setup helper reused the witnessed PID before phase notification.'}
        }catch{
          $helperQueryError=$_.Exception.Message
          if($null -ne $helperProcess){try{$helperProcess.Dispose()}catch{};$helperProcess=$null}
          $still=Get-CimInstance Win32_Process -Filter "ProcessId=$([int]$helperIdentity.pid)" -ErrorAction Stop
          if($null -ne $still){throw "Cannot prove witnessed Setup helper exit: $helperQueryError"}
        }finally{if($null -ne $helperProcess){try{$helperProcess.Dispose()}catch{}}}
        if($helperStillRunning){Start-Sleep -Milliseconds 200;continue}
        $phaseFastRows=Get-GameProcessFast
        $ownFast=@($phaseFastRows|Where-Object {[int]$_.pid -eq [int]$ownerRecord.pid -and $_.image_path -ieq $expectedOwnedPath})
        if($ownFast.Count -ne 1 -or [long]$ownFast[0].start_ticks -ne [long]$ownerRecord.start_ticks){throw 'Owned game handle/path/start did not remain exact through the restored witness.'}
        $phaseRequestAttempted=$true
        & $phaseRequester -ProcessId ([int]$ownerRecord.pid) -Slot $slot -ExpectedImagePath $expectedOwnedPath -ExpectedStartUtc ([string]$ownerRecord.start_time_utc) -WitnessPath $phaseWitnessPath -WitnessSha256 $witnessSha -ReceiptPath $requestPath | Out-Null
        if(!(Test-Path -LiteralPath $requestPath -PathType Leaf)){throw 'Reviewed phase-done requester returned without its exact owner receipt.'}
        $request=Get-Content -LiteralPath $requestPath -Raw|ConvertFrom-Json
        if($request.status -cne 'exact_owned_phase_completion_stop_requested' -or $request.event_set -ne $true -or [int]$request.process_id -ne [int]$ownerRecord.pid -or [int]$request.slot -ne $slot -or $request.witness_sha256 -cne $witnessSha -or [IO.Path]::GetFullPath([string]$request.witness_path) -ine [IO.Path]::GetFullPath($phaseWitnessPath)){throw 'Reviewed phase-done requester receipt failed exact owner/witness verification.'}
        $requestSha=(Get-FileHash -LiteralPath $requestPath -Algorithm SHA256).Hash.ToLowerInvariant()
        $phaseDone=[ordered]@{schema=1;status=$(if($witness.phase_actions_complete){'complete'}else{'failed_but_restored'});suite=$Suite;slot=$slot;run_name=$RunName;pid=[int]$ownerRecord.pid;image_path=$expectedOwnedPath;start_time_utc=[string]$ownerRecord.start_time_utc;start_ticks=[long]$ownerRecord.start_ticks;stage_root=[IO.Path]::GetFullPath($stageRoot);runtime_workflow_commit=$runtimeBinding.upstream_commit;runtime_workflow_tree=$runtimeBinding.upstream_tree;runtime_root_path=$runtimeRoot;runtime_overlay_manifest_sha256=$runtimeBinding.overlay_package_manifest_sha256;runtime_overlay_seal_sha256=$runtimeBinding.overlay_package_seal_sha256;phase_done_requester_sha256=$runtimeBinding.phase_done_requester.sha256;phase_actions_complete=[bool]$witness.phase_actions_complete;restoration_complete=$true;driver_receipt_sha256=$driverSha;restore_receipt_sha256=$restoreSha;witness_path='RESOURCE_PHASE_DONE_WITNESS.json';witness_sha256=$witnessSha;request_receipt_path='RESOURCE_PHASE_DONE_REQUEST.json';request_receipt_sha256=$requestSha;driver_process=$helperIdentity;driver_process_exit_verified=$true;created_utc=[DateTime]::UtcNow.ToString('o')}
        [IO.File]::WriteAllText($phaseDonePath,($phaseDone|ConvertTo-Json -Depth 10)+[Environment]::NewLine,[Text.UTF8Encoding]::new($false))
        $phaseRequestReceipt=[ordered]@{schema=1;status='exact_owned_phase_event_requested';suite=$Suite;slot=$slot;run_name=$RunName;pid=[int]$ownerRecord.pid;image_path=$expectedOwnedPath;start_ticks=[long]$ownerRecord.start_ticks;phase_actions_complete=[bool]$witness.phase_actions_complete;restoration_complete=$true;driver_process_exit_verified=$true;phase_done_sha256=(Get-FileHash -LiteralPath $phaseDonePath -Algorithm SHA256).Hash.ToLowerInvariant();request_receipt_sha256=$requestSha;witness_sha256=$witnessSha;created_utc=[DateTime]::UtcNow.ToString('o')}
        [IO.File]::WriteAllText((Join-Path $runDir 'RESOURCE_PHASE_REQUEST_MONITOR_RECEIPT.json'),($phaseRequestReceipt|ConvertTo-Json -Depth 8)+[Environment]::NewLine,[Text.UTF8Encoding]::new($false))
      }catch{
        $phaseRequestAttempted=$true
        if(!$policyMonitorError){$policyMonitorError='Phase-done exact owner cleanup failed: '+$_.Exception.Message;Add-Content -LiteralPath (Join-Path $runDir 'RUN_POLICY_MONITOR_FAILURE.txt') -Value $policyMonitorError}
      }
    }
    Start-Sleep -Milliseconds 200
  }
  $caseExit=[int]$caseProcess.ExitCode
  $terminalPath=Join-Path $runDir 'flow-terminal.json'
  $terminal=if(Test-Path -LiteralPath $terminalPath){Get-Content -LiteralPath $terminalPath -Raw|ConvertFrom-Json}else{$null}
  $caseResultPath=Join-Path $runDir 'result.json'
  $caseResult=if(Test-Path -LiteralPath $caseResultPath){Get-Content -LiteralPath $caseResultPath -Raw|ConvertFrom-Json}else{$null}
  $phaseDone=if(Test-Path -LiteralPath $phaseDonePath){Get-Content -LiteralPath $phaseDonePath -Raw|ConvertFrom-Json}else{$null}
  $phaseRequest=if(Test-Path -LiteralPath (Join-Path $runDir 'RESOURCE_PHASE_DONE_REQUEST.json')){Get-Content -LiteralPath (Join-Path $runDir 'RESOURCE_PHASE_DONE_REQUEST.json') -Raw|ConvertFrom-Json}else{$null}
  $phaseMonitorPath=Join-Path $runDir 'RESOURCE_PHASE_REQUEST_MONITOR_RECEIPT.json'
  $phaseMonitor=if(Test-Path -LiteralPath $phaseMonitorPath){Get-Content -LiteralPath $phaseMonitorPath -Raw|ConvertFrom-Json}else{$null}
  $phaseMonitorSha=if(Test-Path -LiteralPath $phaseMonitorPath){(Get-FileHash -LiteralPath $phaseMonitorPath -Algorithm SHA256).Hash.ToLowerInvariant()}else{$null}
  $phaseWitnessPath=if($null -ne $phaseDone){Join-Path $runDir ([string]$phaseDone.witness_path)}else{''}
  $phaseWitness=if($phaseWitnessPath -and (Test-Path -LiteralPath $phaseWitnessPath -PathType Leaf)){Get-Content -LiteralPath $phaseWitnessPath -Raw|ConvertFrom-Json}else{$null}
  $flowStatus=if($null -ne $terminal){$terminal.flow_status}else{$null}
  $phaseIdentityOk=($null -ne $phaseDone -and $null -ne $phaseRequest -and $null -ne $flowStatus -and
    $null -ne $phaseWitness -and $phaseDone.restoration_complete -eq $true -and
    $phaseDone.driver_process_exit_verified -eq $true -and $null -ne $phaseMonitor -and
    $phaseMonitor.status -ceq 'exact_owned_phase_event_requested' -and $phaseMonitor.driver_process_exit_verified -eq $true -and
    $phaseMonitor.phase_done_sha256 -ceq (Get-FileHash -LiteralPath $phaseDonePath -Algorithm SHA256).Hash.ToLowerInvariant() -and
    $phaseMonitor.request_receipt_sha256 -ceq (Get-FileHash -LiteralPath (Join-Path $runDir 'RESOURCE_PHASE_DONE_REQUEST.json') -Algorithm SHA256).Hash.ToLowerInvariant() -and
    $phaseMonitor.witness_sha256 -ceq $phaseDone.witness_sha256 -and
    $phaseRequest.status -ceq 'exact_owned_phase_completion_stop_requested' -and $phaseRequest.event_set -eq $true -and
    [int]$phaseDone.pid -eq [int]$phaseRequest.process_id -and [int]$phaseDone.pid -eq [int]$flowStatus.owned_pid -and
    [IO.Path]::GetFullPath([string]$phaseDone.image_path) -ieq [IO.Path]::GetFullPath([string]$flowStatus.owned_image) -and
    (Test-ReviewedStart ([string]$phaseDone.start_time_utc) ([long]([DateTime]::Parse([string]$flowStatus.owned_start_utc).ToUniversalTime().Ticks))) -and
    [int]$phaseDone.slot -eq $slot -and [int]$phaseRequest.slot -eq $slot -and
    $phaseRequest.witness_sha256 -ceq $phaseDone.witness_sha256 -and [IO.Path]::GetFullPath([string]$phaseRequest.witness_path) -ieq [IO.Path]::GetFullPath($phaseWitnessPath) -and
    $phaseWitness.restoration_verified -eq $true -and $phaseWitness.restore_receipt_sha256 -ceq $phaseDone.restore_receipt_sha256 -and
    $phaseWitness.driver_receipt_sha256 -ceq $phaseDone.driver_receipt_sha256 -and $phaseWitness.phase_actions_complete -eq $phaseDone.phase_actions_complete -and
    [int]$phaseWitness.driver_process.pid -eq [int]$phaseDone.driver_process.pid -and [long]$phaseWitness.driver_process.start_ticks -eq [long]$phaseDone.driver_process.start_ticks -and [int]$phaseWitness.driver_process.parent_pid -eq [int]$caseProcess.Id -and
    $phaseDone.runtime_workflow_commit -ceq $runtimeBinding.upstream_commit -and $phaseDone.runtime_workflow_tree -ceq $runtimeBinding.upstream_tree -and [IO.Path]::GetFullPath([string]$phaseDone.runtime_root_path) -ieq $runtimeRoot -and $phaseDone.runtime_overlay_manifest_sha256 -ceq $runtimeBinding.overlay_package_manifest_sha256 -and $phaseDone.runtime_overlay_seal_sha256 -ceq $runtimeBinding.overlay_package_seal_sha256 -and $phaseDone.phase_done_requester_sha256 -ceq $runtimeBinding.phase_done_requester.sha256 -and
    $phaseWitness.process.runtime_workflow_commit -ceq $runtimeBinding.upstream_commit -and $phaseWitness.process.runtime_workflow_tree -ceq $runtimeBinding.upstream_tree -and [IO.Path]::GetFullPath([string]$phaseWitness.process.runtime_root_path) -ieq $runtimeRoot -and $phaseWitness.process.runtime_overlay_manifest_sha256 -ceq $runtimeBinding.overlay_package_manifest_sha256 -and $phaseWitness.process.runtime_overlay_seal_sha256 -ceq $runtimeBinding.overlay_package_seal_sha256 -and $phaseWitness.process.phase_done_requester_sha256 -ceq $runtimeBinding.phase_done_requester.sha256 -and
    $flowStatus.phase_collection_stop_requested -eq $true -and $flowStatus.owned_cleanup_complete -eq $true -and $flowStatus.input_reset_complete -eq $true -and $flowStatus.foreign_game -eq $false)
  $phaseStopReceipt=[ordered]@{schema=1;status=$(if($phaseIdentityOk -and $caseExit -eq 0){'flow_owned_phase_done_cleanup_complete'}else{'phase_done_cleanup_not_confirmed'});suite=$Suite;slot=$slot;run_name=$RunName;phase_actions_complete=($null -ne $phaseDone -and $phaseDone.phase_actions_complete -eq $true);restoration_complete=($null -ne $phaseDone -and $phaseDone.restoration_complete -eq $true);driver_process_exit_verified=($null -ne $phaseDone -and $phaseDone.driver_process_exit_verified -eq $true);phase_done_sha256=$(if(Test-Path -LiteralPath $phaseDonePath){(Get-FileHash -LiteralPath $phaseDonePath -Algorithm SHA256).Hash.ToLowerInvariant()}else{$null});request_receipt_sha256=$(if(Test-Path -LiteralPath (Join-Path $runDir 'RESOURCE_PHASE_DONE_REQUEST.json')){(Get-FileHash -LiteralPath (Join-Path $runDir 'RESOURCE_PHASE_DONE_REQUEST.json') -Algorithm SHA256).Hash.ToLowerInvariant()}else{$null});phase_monitor_sha256=$phaseMonitorSha;witness_sha256=$(if($null -ne $phaseDone){$phaseDone.witness_sha256}else{$null});terminal_status_sha256=$(if(Test-Path -LiteralPath $terminalPath){(Get-FileHash -LiteralPath $terminalPath -Algorithm SHA256).Hash.ToLowerInvariant()}else{$null});terminal_phase_requested=($null -ne $flowStatus -and $flowStatus.phase_collection_stop_requested -eq $true);terminal_owned_cleanup=($null -ne $flowStatus -and $flowStatus.owned_cleanup_complete -eq $true);terminal_input_reset=($null -ne $flowStatus -and $flowStatus.input_reset_complete -eq $true);terminal_foreign_game=($null -ne $flowStatus -and $flowStatus.foreign_game -eq $true);phase_identity_valid=$phaseIdentityOk;no_direct_process_stop_by_runner=$true;created_utc=[DateTime]::UtcNow.ToString('o')}
  [IO.File]::WriteAllText((Join-Path $runDir 'RESOURCE_PHASE_STOP_RECEIPT.json'),($phaseStopReceipt|ConvertTo-Json -Depth 8)+"`n",[Text.UTF8Encoding]::new($false))
  if($null -ne $caseResult){$stagingReceipt.game_launched=$true;$stagingReceipt.run_case_exit=$caseExit;$stagingReceipt.case_verdict=$caseResult.verdict;$stagingReceipt.case_success=$caseResult.as_expected}
  [IO.File]::WriteAllText((Join-Path $runDir 'STAGING_RECEIPT.json'),($stagingReceipt|ConvertTo-Json -Depth 10)+"`n",[Text.UTF8Encoding]::new($false))

  $driverReceipt=if(Test-Path -LiteralPath (Join-Path $runDir 'RESOURCE_DRIVER_RECEIPT.json')){Get-Content -LiteralPath (Join-Path $runDir 'RESOURCE_DRIVER_RECEIPT.json') -Raw|ConvertFrom-Json}else{$null}
  $runtimeIntegrityPost=Get-RuntimeIntegrity
  $runtimeUnchanged=($runtimeIntegrityPost.pass -eq $true)
  $dumpCopy=Join-Path $runDir 'resource_evidence\cgsresourcedump_0.txt'
  $dumpCleanup=if($null -ne $driverReceipt){[string]$driverReceipt.dump_cleanup}else{'not_completed'}
  $remainingGames=@();$approvedPostPeers=@();$postForeignGames=@();$unapprovedGameProcesses=@();$postProcessError=$null
  try{
    $remainingGames=Get-GameProcessSnapshots
    $postCampaignPeers=Get-ResourceV5PeerAuthorityRows -RepoRoot $repoRoot -Authority $parallelAuthority -Processes $remainingGames
    $postObservation=Resolve-ResourceV5ProcessObservations -Processes $remainingGames -CampaignPeers $postCampaignPeers -OwnedImagePath $expectedOwnedPath -OwnedStageRoot $stageRoot -OwnedProfilePath $slotProfile -OwnedSlot $slot -OwnedProcessId 0 -OwnedStartTicks 0 -NormalInstallRoot $normalInstallRoot -NormalProfilePaths $normalProfilePaths -SharedOutputPath 'D:\cgsresourcedump_0.txt' -SharedOutputMutex 'Local\BurnoutPC_ResourceDumpStats_v1' -MaxKnownPeers $reviewPeerLimit
    Add-ResourceV5FirstObservation -RepoRoot $repoRoot -OwnedRunRoot $runDir -OwnedSuite $Suite -OwnedRunName $RunName -LedgerPath $firstObservationLedgerPath -Phase 'postrun' -Observation ([pscustomobject]@{processes=$postObservation.processes;policy_path=$parallelAuthority.policy_path;delegation_path=$parallelAuthority.delegation_path}) -Seen $firstObservationSeen -PolicySha256 $parallelPolicySha256
    $approvedPostPeers=@($postObservation.known_campaign_peers)
    $postForeignGames=@($postObservation.foreign_games)
  }catch{$postProcessError=$_.Exception.Message;$unapprovedGameProcesses+=@([ordered]@{error=$postProcessError;processes=$remainingGames})}
  if($policyMonitorError){$unapprovedGameProcesses+=@([ordered]@{error=$policyMonitorError;processes=@()})}
  $ownedGame=@($remainingGames | Where-Object {$_.image_path -ieq [IO.Path]::GetFullPath((Join-Path $slotDir 'Burnout_PC.exe'))})
  $noOwnedGame=($ownedGame.Count -eq 0)
  $stageAfterManifestPath=Join-Path $runDir 'DATA_STAGE_POSTRUN_MANIFEST.json'
  $postManifestExit=0
  try {$null=& $manifestTool -Path $dataDir -Output $stageAfterManifestPath *> (Join-Path $runDir 'data_manifest_postrun.log')} catch {$postManifestExit=1}
  $sourceAfterManifestPath=Join-Path $runDir 'DATA_SOURCE_POSTRUN_MANIFEST.json'
  $sourcePostExit=0
  try {$null=& $manifestTool -Path ([string]$staging.data_source_path) -Output $sourceAfterManifestPath *> (Join-Path $runDir 'data_manifest_source_postrun.log')} catch {$sourcePostExit=1}
  $immutableUnchanged=$false;$changedAssets=@()
  if($postManifestExit -eq 0){
    $postManifest=Get-Content -LiteralPath $stageAfterManifestPath -Raw|ConvertFrom-Json
    $beforeMap=@{};foreach($f in $stageManifest.files){if($f.role -eq 'immutable_asset'){$beforeMap[$f.path]=$f.sha256}}
    $afterMap=@{};foreach($f in $postManifest.files){if($f.role -eq 'immutable_asset'){$afterMap[$f.path]=$f.sha256}}
    foreach($name in $beforeMap.Keys){if(!$afterMap.ContainsKey($name) -or $afterMap[$name] -cne $beforeMap[$name]){$changedAssets+=@($name)}}
    foreach($name in $afterMap.Keys){if(!$beforeMap.ContainsKey($name)){$changedAssets+=@(('NEW:'+ $name))}}
    $immutableUnchanged=($changedAssets.Count -eq 0)
  }
  $sourceAssetsUnchanged=$false;$changedSourceAssets=@()
  if($sourcePostExit -eq 0){
    $sourceAfter=Get-Content -LiteralPath $sourceAfterManifestPath -Raw|ConvertFrom-Json
    $sourceBeforeMap=@{};foreach($f in $sourceManifest.files){if($f.role -eq 'immutable_asset'){$sourceBeforeMap[$f.path]=$f.sha256}}
    $sourceAfterMap=@{};foreach($f in $sourceAfter.files){if($f.role -eq 'immutable_asset'){$sourceAfterMap[$f.path]=$f.sha256}}
    foreach($name in $sourceBeforeMap.Keys){if(!$sourceAfterMap.ContainsKey($name) -or $sourceAfterMap[$name] -cne $sourceBeforeMap[$name]){$changedSourceAssets+=@($name)}}
    foreach($name in $sourceAfterMap.Keys){if(!$sourceBeforeMap.ContainsKey($name)){$changedSourceAssets+=@(('NEW:'+ $name))}}
    $sourceAssetsUnchanged=($changedSourceAssets.Count -eq 0)
  }
  $dataCopyReceiptPath=Join-Path $runDir 'DATA_COPY_RECEIPT.json'
  $dataCopyReceiptAfter=if(Test-Path -LiteralPath $dataCopyReceiptPath -PathType Leaf){Get-Content -LiteralPath $dataCopyReceiptPath -Raw|ConvertFrom-Json}else{$null}
  $dataCopyReceiptComplete=($null -ne $dataCopyReceiptAfter -and (Get-FileHash -LiteralPath $dataCopyReceiptPath -Algorithm SHA256).Hash.ToLowerInvariant() -ceq $dataCopyReceiptHash -and
    $dataCopyReceiptAfter.status -ceq 'complete' -and [int]$dataCopyReceiptAfter.file_count -eq [int]$frozenDataPlan.file_count -and
    [long]$dataCopyReceiptAfter.bytes -eq [long]$frozenDataPlan.bytes -and $dataCopyReceiptAfter.source_manifest_sha256 -ceq $sourceManifest.manifest_sha256)
  $payloadUnchanged=$true
  foreach($f in $payload){$p=Join-Path $slotDir $f.path;if(!(Test-Path -LiteralPath $p -PathType Leaf) -or (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -cne $f.sha256){$payloadUnchanged=$false}}
  $configAfterHash=if(Test-Path -LiteralPath (Join-Path $slotDir 'config.ini')){(Get-FileHash -LiteralPath (Join-Path $slotDir 'config.ini') -Algorithm SHA256).Hash.ToLowerInvariant()}else{''}
  $configUnchanged=($configAfterHash -ceq $slotConfigHash -and $slotConfigHash -ceq [string]$privateDisplayPlan.derived_sha256)
  $profileAfterExists=Test-Path -LiteralPath $slotProfile -PathType Leaf
  $profileRestored=if($profileBefore.existed){$profileAfterExists -and (Get-FileHash -LiteralPath $slotProfile -Algorithm SHA256).Hash.ToLowerInvariant() -ceq $profileBefore.sha256}else{!$profileAfterExists}
  $windowsPowerShellLaunchPath=Join-Path $runDir 'WINDOWS_POWERSHELL_LAUNCH_RECEIPT.json'
  $windowsPowerShellLaunch=if(Test-Path -LiteralPath $windowsPowerShellLaunchPath){Get-Content -LiteralPath $windowsPowerShellLaunchPath -Raw|ConvertFrom-Json}else{$null}
  $windowsPowerShellLaunchOk=($null -ne $windowsPowerShellLaunch -and $windowsPowerShellLaunch.status -ceq 'windows_powershell_child_started_clean' -and $windowsPowerShellLaunch.parent_module_path_restored -eq $true -and $windowsPowerShellLaunch.parent_module_path_before -ceq $windowsPowerShellLaunch.parent_module_path_after)
  $terminalOk=($null -ne $terminal -and $terminal.success -eq $true -and $terminal.helper_cleanup_complete -eq $true -and $terminal.profile_restoration_complete -eq $true -and $terminal.flow_status.owned_cleanup_complete -eq $true)
  $phaseStopOk=($null -ne $phaseStopReceipt -and $phaseStopReceipt.status -ceq 'flow_owned_phase_done_cleanup_complete' -and $phaseStopReceipt.phase_actions_complete -eq $true -and $phaseStopReceipt.restoration_complete -eq $true)
  $normalProtection=Compare-TextureNormalSnapshot -Before $normalBefore
  [IO.File]::WriteAllText((Join-Path $runDir 'NORMAL_PROTECTION_AFTER.json'),($normalProtection|ConvertTo-Json -Depth 8)+"`n",[Text.UTF8Encoding]::new($false))
  $normalOk=($normalProtection.pass -and $terminalOk -and $caseExit -eq 0 -and $null -ne $caseResult -and $caseResult.verdict -ceq 'PASS' -and $caseResult.as_expected -eq $true -and $null -ne $driverReceipt -and $driverReceipt.status -ceq 'complete' -and $driverReceipt.restore_complete -eq $true -and $windowsPowerShellLaunchOk -and $payloadUnchanged -and $immutableUnchanged -and $sourceAssetsUnchanged -and $dataCopyReceiptComplete -and $profileRestored -and $configUnchanged -and $runtimeUnchanged -and $noOwnedGame -and $unapprovedGameProcesses.Count -eq 0 -and $phaseStopOk -and $dumpCleanup -ceq 'deleted_hash_match_under_mutex')
  $post=[ordered]@{schema=2;status=$(if($normalOk){'normal_files_and_profiles_unchanged'}else{'postcheck_incomplete'});suite=$Suite;slot=$slot;run_name=$RunName;windows_powershell_launch_receipt=$windowsPowerShellLaunch;windows_powershell_launch_complete=$windowsPowerShellLaunchOk;no_owned_game=$noOwnedGame;unapproved_game_processes=$unapprovedGameProcesses;allowed_peer_processes=$approvedPostPeers;remaining_game_processes=@($remainingGames|ForEach-Object{[ordered]@{pid=[int]$_.pid;name=$_.name;path=$_.image_path;start_time_utc=$_.start_time_utc;slot=$_.slot;stage_root=$_.stage_root;candidate_exe_sha256=$_.candidate_exe_sha256}});owned_game_pids=@($ownedGame|ForEach-Object{[int]$_.pid});terminal_success=($null -ne $terminal -and $terminal.success -eq $true);helper_cleanup_complete=($null -ne $terminal -and $terminal.helper_cleanup_complete -eq $true);profile_restoration_complete=($null -ne $terminal -and $terminal.profile_restoration_complete -eq $true);profile_before=$profileBefore;profile_restored=$profileRestored;private_config_unchanged=$configUnchanged;private_config_source_sha256=$protectedConfigPlan.sha256;private_config_sha256=$configAfterHash;private_config_expected_sha256=$privateDisplayPlan.derived_sha256;private_display_width=[int]$privateDisplayPlan.private_values.Width;private_display_height=[int]$privateDisplayPlan.private_values.Height;private_display_fullscreen=[int]$privateDisplayPlan.private_values.Fullscreen;capture_frame_file_bytes=[long]$privateDisplayPlan.capture.frame_file_bytes;capture_frame_reserve_bytes=[long]$privateDisplayPlan.capture.reserve_bytes_per_frame;immutable_assets_unchanged=$immutableUnchanged;changed_immutable_assets=$changedAssets;source_assets_unchanged=$sourceAssetsUnchanged;changed_source_assets=$changedSourceAssets;shipping_payload_unchanged=$payloadUnchanged;runtime_overlay_unchanged=$runtimeUnchanged;runtime_integrity=$runtimeIntegrityPost;dump_cleanup=$dumpCleanup;dump_cleanup_receipt_complete=($dumpCleanup -ceq 'deleted_hash_match_under_mutex');phase_stop=$phaseStopReceipt;phase_stop_complete=$phaseStopOk;process_monitor_error=$postProcessError;created_utc=[DateTime]::UtcNow.ToString('o')}
  $post['data_copy_receipt_complete']=$dataCopyReceiptComplete
  $post['data_copy_receipt_sha256']=if($dataCopyReceiptComplete){$dataCopyReceiptHash}else{$null}
  $post['root_parallel_policy_path']=$parallelAuthority.policy_path
  $post['root_parallel_policy_sha256']=$parallelPolicySha256
  $post['root_parallel_delegation_sha256']=$parallelAuthority.delegation_sha256
  $post['parallel_census_policy']='informational; exact owned handoffs are resolved dynamically'
  $post['known_campaign_peers']=$approvedPostPeers
  $post['foreign_game_processes']=$postForeignGames
  $post['first_observation_ledger_path']='CAMPAIGN_PEER_FIRST_OBSERVATIONS.jsonl'
  $post['source_asset_file_count']=[int]$sourceManifest.file_count
  $post['source_asset_bytes']=[long]$sourceManifest.bytes
  $post['frozen_snapshot_receipt_sha256']=[string]$frozenDataPlan.snapshot_receipt_sha256
  $post['source_roster_sha256']=[string]$frozenDataPlan.source_roster_sha256
  $post['config_source_roster_sha256']=[string]$protectedConfigPlan.roster_sha256
  [IO.File]::WriteAllText((Join-Path $runDir 'POSTCHECK.json'),($post|ConvertTo-Json -Depth 12)+"`n",[Text.UTF8Encoding]::new($false))
  if(!$normalOk){throw "Post-run cleanup/provenance verification did not pass; stage preserved for review. Status=$($post.status)"}
  Write-Output ("Completed {0}; run evidence: {1}; stage retained at {2} until reviewed cleanup." -f $Suite,$runDir,$stageRoot)
}
catch {
  $msg=$_.Exception.Message
  [IO.File]::WriteAllText((Join-Path $runDir 'RUNNER_FAILURE.txt'),($msg+"`n"),[Text.UTF8Encoding]::new($false))
  if($stageCreated -and !$gameLaunched){
    $resolved=[IO.Path]::GetFullPath($stageRoot)
    $allowed=[IO.Path]::GetFullPath((Join-Path (Join-Path $suiteRoot 'stage') $RunName))
    if($resolved -ieq $allowed){
      $marker=Join-Path $stageRoot 'RESOURCE_STAGE_OWNER.json'
      if(Test-Path -LiteralPath $marker){$m=Get-Content -LiteralPath $marker -Raw|ConvertFrom-Json;$reparse=@(Get-ChildItem -LiteralPath $resolved -Recurse -Force -ErrorAction Stop|Where-Object{$_.Attributes -band [IO.FileAttributes]::ReparsePoint});if($m.owner -ceq 'Run.ps1' -and $m.run_name -ceq $RunName -and $m.suite -ceq $Suite -and $reparse.Count -eq 0){Write-Output 'Readonly stage retained after prelaunch failure.'}}
    }
  }
  throw
}

finally {
  if($normalBefore -and (Test-Path -LiteralPath $runDir -PathType Container) -and !(Test-Path -LiteralPath (Join-Path $runDir 'NORMAL_PROTECTION_AFTER.json'))){
    try{$normalProtection=Compare-TextureNormalSnapshot -Before $normalBefore;[IO.File]::WriteAllText((Join-Path $runDir 'NORMAL_PROTECTION_AFTER.json'),($normalProtection|ConvertTo-Json -Depth 8)+"`n",[Text.UTF8Encoding]::new($false))}catch{[IO.File]::WriteAllText((Join-Path $runDir 'NORMAL_PROTECTION_ERROR.txt'),$_.Exception.Message)}
  }
}
