$ErrorActionPreference='Stop'
$scene=Join-Path $PSScriptRoot 'native_scene_batch_20261031_v3'
$out=Join-Path $PSScriptRoot ('scene_v3_validation_'+[DateTime]::UtcNow.ToString('yyyyMMdd_HHmmss'))
if(Test-Path -LiteralPath $out){throw 'Fresh test output required'}
[void][IO.Directory]::CreateDirectory($out)
$results=[Collections.Generic.List[object]]::new()
function Check([string]$Name,[bool]$Pass,[string]$Detail){$results.Add(@{name=$Name;pass=$Pass;detail=$Detail});if(!$Pass){throw ($Name+': '+$Detail)}}

# Execute the actual phase loop and its actual command builders against recording I/O.
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $scene 'Driver.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Driver parse errors'}
$functions=@{};foreach($n in $ast.FindAll({param($a)$a -is [Management.Automation.Language.FunctionDefinitionAst]},$true)){$functions[$n.Name]=$n.Extent.Text}
foreach($name in @('Get-PhaseCommands','Get-PhaseName','Test-RestorableBaseline','Apply-Target')){Invoke-Expression $functions[$name]}
$loops=@($ast.FindAll({param($a)$a -is [Management.Automation.Language.ForEachStatementAst] -and $a.Extent.Text -match 'Apply-Target \$control'},$true))
if($loops.Count -ne 1){throw 'Actual target loop is not unique'}
$loopBody=$loops[0].Extent.Text
$scope=Get-Content -LiteralPath (Join-Path $scene 'SCOPE.json') -Raw|ConvertFrom-Json
function Commands-For([hashtable]$Values){$r=@();foreach($c in $controls){if($Values.ContainsKey($c.alias)){$r+=('set '+$c.alias+' '+$Values[$c.alias])}};return $r}
function Say([string]$Text){}
function Execute([string]$Name,[string[]]$Commands,[hashtable]$Expected,[bool]$Capture=$true){
 foreach($line in $Commands){if($line -notmatch '^set (SC0[12]) (TRUE|FALSE)$'){throw ('Unexpected simulated command '+$line)};$script:actual[$Matches[1]]=$Matches[2]}
 foreach($alias in $Expected.Keys){if($script:actual[$alias] -cne [string]$Expected[$alias]){throw ($Name+' expects '+$alias+'='+$Expected[$alias]+' but actual='+$script:actual[$alias])}}
 $script:phases.Add(@{phase=$Name;commands=$Commands;expected=$Expected.Clone();actual=$script:actual.Clone()})
 $frameRows.Add(@{phase=$Name;sha256='synthetic_no_native_frame';sequence=($frameRows.Count+1)})
 $phaseRows.Add(@{proofs=@()})
 return $script:actual.Clone()
}
foreach($baseline02 in @('FALSE','TRUE')){
 $plan=[pscustomobject]@{controls=@($scope.controls|Select-Object -First 2)};$controls=@($plan.controls)
 $script:baseline=@{SC01='FALSE';SC02=$baseline02};$script:actual=$script:baseline.Clone();$script:exactBaseline=@{}
 $script:touchedAliases=@{};$script:skippedAliases=@();$script:skippedControls=@();$script:completedControls=[Collections.Generic.List[object]]::new();$script:writesStarted=$false
 $script:sceneAnchorSeedPhase='natural_baseline';$script:phases=[Collections.Generic.List[object]]::new()
 $frameRows=[Collections.Generic.List[object]]::new();$phaseRows=[Collections.Generic.List[object]]::new();$targetRows=[Collections.Generic.List[object]]::new()
 Invoke-Expression $loopBody
 Check ('seed_branch_'+$baseline02) ($script:actual['SC01'] -ceq 'FALSE' -and $script:actual['SC02'] -ceq $baseline02) 'Actual phase builders/target loop completed and restored both captured values.'
 $script:phases.ToArray()|ConvertTo-Json -Depth 10|Set-Content -LiteralPath (Join-Path $out ('SC02_'+$baseline02+'.json')) -Encoding utf8
}

# Keep all synthetic profile data under the named test scope, never the live save.
. (Join-Path $scene 'PathGuards.ps1')
. (Join-Path $scene 'StageBoundary.ps1')
$fixture=Join-Path $out 'fixture.bin';[IO.File]::WriteAllText($fixture,'synthetic fixture only')
$fixtureHash=(Get-FileHash -LiteralPath $fixture).Hash.ToLowerInvariant()
function Stage([string]$Name){
 $root=Join-Path $out $Name;$exe=Join-Path $root 'slot';$data=Join-Path $root 'data'
 [void][IO.Directory]::CreateDirectory($exe);[void][IO.Directory]::CreateDirectory($data)
 return @{root=$root;value=@{exe_dir=$exe;cwd=$data;profile=(Join-Path $data 'Memcard_62190/Profile.sav')}}
}
$valid=Stage 'plain';$r=Assert-BrnSceneStageBoundary $valid.value $valid.root $fixture $fixtureHash
Check 'private_absent_profile_accepted' ($r.pass -and $r.profile_identity.status -ceq 'absent_before_fixture_copy') 'Guard is read-only and accepts a missing private target.'
$protected=Join-Path $out 'synthetic_protected';[void][IO.Directory]::CreateDirectory($protected)
$protectedFile=Join-Path $protected 'Profile.sav';Copy-Item -LiteralPath $fixture -Destination $protectedFile
$protectedHash=(Get-FileHash -LiteralPath $protectedFile).Hash
$junction=Stage 'junction';New-Item -ItemType Junction -Path (Join-Path $junction.value.cwd 'Memcard_62190') -Target $protected|Out-Null
$denied=$false;try{[void](Assert-BrnSceneStageBoundary $junction.value $junction.root $fixture $fixtureHash)}catch{$denied=$_.Exception.Message -match 'reparse point'}
Check 'junction_denied_before_copy' ($denied -and (Get-FileHash -LiteralPath $protectedFile).Hash -ceq $protectedHash) 'Synthetic protected target stayed unchanged.'
$hard=Stage 'hardlink';[void][IO.Directory]::CreateDirectory((Split-Path -Parent $hard.value.profile));New-Item -ItemType HardLink -Path $hard.value.profile -Target $protectedFile|Out-Null
$denied=$false;try{[void](Assert-BrnSceneStageBoundary $hard.value $hard.root $fixture $fixtureHash)}catch{$denied=$_.Exception.Message -match 'filesystem links'}
Check 'hardlink_denied_before_copy' ($denied -and (Get-FileHash -LiteralPath $protectedFile).Hash -ceq $protectedHash) 'Synthetic protected target stayed unchanged.'

# Exercise metadata additions on an exact text-only clone, without staging any game.
$clone=Join-Path $out 'metadata_case';[void][IO.Directory]::CreateDirectory($clone)
Get-ChildItem -LiteralPath $scene -File|ForEach-Object {Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $clone $_.Name)}
[IO.File]::WriteAllText((Join-Path $clone 'REVIEW.md'),'synthetic review receipt')
[IO.File]::WriteAllText((Join-Path $clone 'REVIEW.json'),'{}')
$r=& (Join-Path $clone 'Preflight.ps1')
Check 'review_outputs_preserve_immutable_preflight' $r.pass ($r.problems -join '; ')
[IO.File]::WriteAllText((Join-Path $clone 'STAGING.json'),'{}')
$r=& (Join-Path $clone 'Preflight.ps1') -AtRun -RunDir (Join-Path $clone 'runs/future') -StagePath (Join-Path $clone 'STAGING.json')
$pins=@($r.checks|Where-Object name -in @('v2_artifact_hash_pins','all_file_hash_manifest'))
Check 'stage_metadata_does_not_break_authored_hashes' ($pins.Count -eq 2 -and @($pins|Where-Object { !$_.pass }).Count -eq 0 -and !$r.pass) 'Authored pins accept the metadata filename; the invalid stage is separately rejected.'
[IO.File]::WriteAllText((Join-Path $clone 'unknown.ps1'),'# must not be absorbed')
$r=& (Join-Path $clone 'Preflight.ps1') -AtRun -RunDir (Join-Path $clone 'runs/future') -StagePath (Join-Path $clone 'STAGING.json')
Check 'unknown_authored_file_rejected' (@($r.checks|Where-Object { $_.name -eq 'v2_artifact_hash_pins' -and !$_.pass }).Count -eq 1) 'The three metadata exceptions do not admit new executable inputs.'
@{pass=$true;checks=$results.ToArray();native_runs=0;real_profile_operations=0;source_mutations=0;script_sha256=(Get-FileHash -LiteralPath $PSCommandPath).Hash.ToLowerInvariant()}|ConvertTo-Json -Depth 10|Set-Content -LiteralPath (Join-Path $out 'RESULT.json') -Encoding utf8
@{run_dir=$out;result_sha256=(Get-FileHash -LiteralPath (Join-Path $out 'RESULT.json')).Hash.ToLowerInvariant()}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $PSScriptRoot 'scene_v3_validation_latest.json') -Encoding utf8
$results.ToArray()|ConvertTo-Json -Depth 4
