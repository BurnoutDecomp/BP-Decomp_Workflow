$ErrorActionPreference='Stop'
$own=$PSScriptRoot
$stage=Get-Content -Raw (Join-Path $own 'STAGING.json')|ConvertFrom-Json
$scope=Get-Content -Raw (Join-Path $own 'SCOPE.json')|ConvertFrom-Json
function Assert-Hash([string]$Path,[string]$Expected){if((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $Expected){throw "Hash mismatch $Path"}}
Assert-Hash (Join-Path $own 'ROOT_NATIVE_EXECUTION_DELEGATION_V8_20261029.json') '092948117cf40424c555943e3760f2e07f3c1bc5f97f0a08a91e0712237ddb38'
Assert-Hash (Join-Path $own 'ROOT_NORMAL41_ROSTER.json') '0679dfb7c4dfc121056e8f146b0792fb2c52879ba8f348729923a8c8d540a94b'
if($PSVersionTable.PSVersion.Major -lt 7 -or $scope.controls.Count -ne 24 -or $stage.slot -ne 62181 -or $stage.exe_sha256 -cne $scope.candidate.exe_sha256){throw 'Wrong shell/source/slot/cohort'}
foreach($p in $stage.launch_files.PSObject.Properties){Assert-Hash (Join-Path $stage.exe_dir $p.Name) $p.Value}
Assert-Hash (Join-Path $stage.exe_dir 'config.ini') $stage.config_sha256
Assert-Hash $stage.profile $stage.profile_seed_sha256
foreach($set in @($stage.runtime_overlay_files,$stage.runtime_shared_readonly_dependencies)){foreach($p in $set.PSObject.Properties){Assert-Hash $p.Name $p.Value}}
foreach($p in (Get-Content -Raw (Join-Path $own 'NORMAL_BEFORE.json')|ConvertFrom-Json).PSObject.Properties){Assert-Hash $p.Name $p.Value.sha256}
foreach($path in @($own,$stage.exe_dir,$stage.cwd,(Split-Path $stage.profile -Parent))){if((Get-Item -LiteralPath $path).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Unexpected private stage reparse point'}}
$parsed=@()
foreach($path in @((Join-Path $own 'Case.ps1'),(Join-Path $own 'Driver.ps1'),(Join-Path $own 'Request-HarnessPhaseDone.ps1'))+@($stage.runtime_overlay_files.PSObject.Properties.Name)){
 $tokens=$null;$errors=$null;$null=[Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)
 if($errors.Count){throw ($path+': '+($errors.Message -join '; '))};$parsed+=@{path=$path;errors=0}
}
$aliases=@($scope.controls)+@($scope.context_aliases)
if($aliases.Count -ne 28 -or @($aliases|Where-Object{$_.alias.Length -gt 9}).Count -or @($aliases.alias|Sort-Object -Unique).Count -ne 28){throw 'Native alias capacity or name contract'}
$case=& (Join-Path $own 'Case.ps1')
if($case.Run.MaxSeconds -ne 240 -or $case.Run.MaxLogMB -ne 64 -or $case.Run.MinFreeGB -ne 1.25 -or !$case.Run.AllowConcurrentGames -or !$case.Run.StrictGameOwnership -or $case.Run.Teleport){throw 'Case scenario or owned-process contract changed'}
$free=(Get-PSDrive D).Free
if($free -lt $stage.storage.required_free_at_launch_bytes){throw 'Insufficient free bytes for immutable250MiB peak plus1GiB floor'}
@{verdict='pass';kind='read-only exact batch preflight';controls=24;aliases=28;max_frames=43;max_log_mib=64;planned_output_peak_bytes=$stage.storage.planned_output_peak_bytes;free_bytes=$free;slot=62181;parsed=$parsed;game_launched=$false;site_credit=0}|ConvertTo-Json -Depth 5|Set-Content (Join-Path $own 'PREFLIGHT_RESULT.json') -Encoding utf8
Get-Content (Join-Path $own 'PREFLIGHT_RESULT.json') -Raw
