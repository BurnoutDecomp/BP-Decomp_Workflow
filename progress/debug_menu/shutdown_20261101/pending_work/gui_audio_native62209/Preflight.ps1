param([switch]$AtRun,[string]$RunDir='')
$ErrorActionPreference='Stop';$package=$PSScriptRoot
$pins=Get-Content -Raw (Join-Path $package 'SOURCE_PINS.json')|ConvertFrom-Json
function Require-Hash([string]$Path,[string]$Sha){
 if($Sha -notmatch '^[0-9a-f]{64}$' -or !(Test-Path -LiteralPath $Path -PathType Leaf) -or (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $Sha){throw ('Pinned file mismatch: '+$Path)}
}
$manifest=Get-Content -Raw (Join-Path $package 'AUTHORED_FILES.json')|ConvertFrom-Json
foreach($file in $manifest.files){Require-Hash (Join-Path $package $file.path) $file.sha256}
$offline=Get-Content -Raw (Join-Path $package 'OFFLINE_TESTS.json')|ConvertFrom-Json
if($offline.pass -ne $true -or $offline.count -lt 36 -or $offline.actual_helpers_executed -ne $true -or $offline.native_run -ne $false -or $offline.temporary_fixtures_removed -ne $true){throw 'Offline actual-helper receipt is missing or failed'}
foreach($input in $offline.input_sha256.PSObject.Properties){Require-Hash (Join-Path $package $input.Name) $input.Value}
$build=$pins.candidate
Require-Hash $build.build_receipt.path $build.build_receipt.sha256
$receipt=Get-Content -Raw $build.build_receipt.path|ConvertFrom-Json
if($receipt.status -cne 'BUILD_PASS' -or $receipt.b5_commit -cne '5a4a19cace1dc080c0b61de4ba15130035706d19' -or $receipt.source_dirty -ne $false -or $receipt.provenance.b5_dirty -ne $false -or $receipt.provenance.parent_dirty -ne $true -or $receipt.parent_dirty_only_submodule_pointer -ne $true -or $receipt.parent_status -cne ' M b5-decomp' -or $receipt.exe_sha256 -cne $build.exe_sha256 -or $receipt.installed -ne $false){throw 'Build provenance differs from the actual clean-b5/parent-pointer-only receipt'}
foreach($file in $build.artifacts.PSObject.Properties){Require-Hash (Join-Path $build.artifact_dir $file.Name) $file.Value.sha256}
foreach($file in $build.selected_source_sha256.PSObject.Properties){Require-Hash (Join-Path $build.source_root $file.Name) $file.Value}
foreach($helper in $pins.runner_binding.workflow_helpers.PSObject.Properties){Require-Hash $helper.Value.path $helper.Value.sha256}
foreach($helper in $pins.runner_binding.supporting_dependencies){Require-Hash $helper.path $helper.sha256}
Require-Hash $pins.profile.fixture.path $pins.profile.fixture.sha256
. (Join-Path $package 'CaseHelpers.ps1')
$run=New-BrnGuiAudioRunArguments
if($run.ContainsKey('Audio') -or $run.ContainsKey('SkipIntro') -or $run.PauseTarget -cne 'map' -or $run.PauseAt -cne '22' -or $run.UnpauseAt -cne '46' -or $run.MenuTapAt -cne '30:Next,38:Prev' -or !$run.StrictGameOwnership){throw 'Normal GUI schedule/muted/intro policy changed'}
if($AtRun){
 $stage=Get-Content -Raw (Join-Path $package 'STAGING.json')|ConvertFrom-Json
 if($stage.slot -ne 62209 -or $stage.exe_sha256 -cne $build.exe_sha256 -or $stage.source_commit -cne $build.b5_commit -or $stage.selected_source_digest -cne $build.selected_source_digest -or $stage.build_receipt_sha256 -cne $build.build_receipt.sha256 -or $stage.profile_sha256 -cne $pins.profile.source_sha256 -or $stage.profile_fixture_sha256 -cne $pins.profile.fixture.sha256 -or [IO.Path]::GetFullPath($stage.profile_fixture) -ine [IO.Path]::GetFullPath($pins.profile.fixture.path)){throw 'Root-created private stage binding mismatch'}
 . (Join-Path $package 'PathGuards.ps1');. (Join-Path $package 'StageBoundary.ps1')
 $null=Assert-BrnSceneStageBoundary $stage (Join-Path $package 'stage') $pins.profile.fixture.path $pins.profile.fixture.sha256
 foreach($file in $build.artifacts.PSObject.Properties){Require-Hash (Join-Path $stage.exe_dir $file.Name) $file.Value.sha256}
 $config=Join-Path $stage.exe_dir 'config.ini'
 if([IO.Path]::GetFullPath($stage.config_path) -ine [IO.Path]::GetFullPath($config)){throw 'Private executable-adjacent config path differs'}
 $configIdentity=Assert-BrnPrivateProfile $config 'private GUI config'
 if($configIdentity.status -cne 'regular_single_link_private_file'){throw 'Private config must be a regular single-link file'}
 Require-Hash $config $stage.config_sha256
 . (Join-Path $package 'ConfigReadOnly.ps1')
 if(@(Get-Sound32DebugIniSoundKeys $config).Count -ne 0){throw 'Sound Debug keys would activate Sound early; reject without editing config'}
 if($RunDir){$prefix=[IO.Path]::GetFullPath((Join-Path $package 'runs')).TrimEnd('\')+'\';if(![IO.Path]::GetFullPath($RunDir).StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)){throw 'Run path outside this private packet'}}
 . (Join-Path $package 'ConcurrentOwner.ps1')
 $null=Assert-BrnConcurrentOwnerSet -Stage $stage -OwnedPid 0 -Phase 'prelaunch'
}else{
 foreach($name in @('STAGING.json','stage','runs')){if(Test-Path -LiteralPath (Join-Path $package $name)){throw ('Preparation is no longer authoring-only: '+$name)}}
}
@{pass=$true;slot=62209;at_run=[bool]$AtRun;source_commit=$build.b5_commit;exe_sha256=$build.exe_sha256;source_dirty=$false;parent_dirty_pointer_only=$true;max_frames=8;normal_written=$false}
