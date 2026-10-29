$ErrorActionPreference='Stop'
$own=$PSScriptRoot;$old=Join-Path (Split-Path $own -Parent) 'next_native_batch_20261029_remainder'
$scope=Get-Content -Raw (Join-Path $own 'SCOPE.json')|ConvertFrom-Json
$controls=@($scope.controls)+@($scope.context_aliases)
$prior=Get-Content -Raw (Join-Path $old 'run_62180_game01/driver-result.json')|ConvertFrom-Json
$phase=@($prior.phases|Where-Object phase -ceq '0051_positive')[0]
$GameLog=Join-Path $old 'stage/slot/BrnGame.log'
function Own {}
$rows=@()
foreach($version in @('old','new')){
 $path=if($version -ceq 'old'){Join-Path $old 'Driver.ps1'}else{Join-Path $own 'Driver.ps1'}
 $ast=[Management.Automation.Language.Parser]::ParseFile($path,[ref]$null,[ref]$null)
 foreach($name in @('Lines','Read-Values')){$node=$ast.FindAll({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$true)|Select-Object -First 1;Invoke-Expression $node.Extent.Text}
 $script:gameLines=[Collections.Generic.List[string]]::new();$script:gameBytes=0L;$script:prefixHash=$null
 $null=Lines
 $watch=[Diagnostics.Stopwatch]::StartNew();$read=Read-Values $phase.cursor;$watch.Stop()
 if($read.proofs.Count -ne 28){throw 'Actual old/new reader did not decode retained28proofs'}
 for($i=0;$i -lt 28;$i++){if($read.proofs[$i].ack_before -ne $phase.proofs[$i].ack_before -or $read.proofs[$i].value -cne $phase.proofs[$i].value){throw 'Actual old/new proof differs'}}
 $rows+=@{version=$version;milliseconds=$watch.Elapsed.TotalMilliseconds;actual_proofs=28;raw_complete_bytes=$script:gameBytes;prefix_hash=$script:prefixHash}
}
@{verdict='pass_actual_old_new_same28proofs';raw_log=$GameLog;raw_log_sha256=(Get-FileHash $GameLog -Algorithm SHA256).Hash.ToLowerInvariant();rows=$rows;speedup=($rows[0].milliseconds/$rows[1].milliseconds);mocked_only='Own process liveness for pure raw decoder benchmark; actual runtime retains original Own guards';game_launched=$false}|ConvertTo-Json -Depth 5|Set-Content (Join-Path $own 'READER_BENCHMARK.json') -Encoding utf8
Get-Content (Join-Path $own 'READER_BENCHMARK.json') -Raw
