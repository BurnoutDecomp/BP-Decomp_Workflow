$ErrorActionPreference='Stop'
$own=$PSScriptRoot
$scope=Get-Content -Raw (Join-Path $own 'SCOPE.json')|ConvertFrom-Json
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $own 'Driver.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Driver parse failure'}
foreach($name in @('Lines','Read-Values','Queries','Commands-For')){
 $node=$ast.FindAll({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $name},$true)|Select-Object -First 1
 if(!$node){throw ('Missing actual function '+$name)}
 Invoke-Expression $node.Extent.Text
}
function Own {}
$controls=@($scope.controls)+@($scope.context_aliases)
$source=[regex]::Replace((Get-Content -Raw (Join-Path $own 'source/BrnSkyDebugComponent.cpp')),'\s+',' ')
foreach($control in $controls){
 $call=[regex]::Replace([string]$control.source_call,'\s+',' ')
 if(!$call -or !$source.Contains($call)){throw ('Alias source call is not attested '+$control.alias)}
 $m=[regex]::Match($call,'Register(?:Float|Variable)\([^,]+,\s*(KPC_ROOT|"[^"]*"),\s*"([^"]*)"')
 if(!$m.Success){throw ('Cannot decode actual source category '+$control.alias)}
 $category=if($m.Groups[1].Value -ceq 'KPC_ROOT'){''}else{$m.Groups[1].Value.Trim('"')+'/'}
 if($control.lookup_path -cne ('Environment/'+$category+$m.Groups[2].Value)){throw ('Alias actual source-root/category mismatch '+$control.alias)}
}
$actual=@(Queries)
if($actual.Count -ne 84){throw ('Native query emission count '+$actual.Count)}
for($i=0;$i -lt 28;$i++){
 if($actual[$i*3] -cne ('alias '+$controls[$i].alias) -or $actual[$i*3+1] -cne $controls[$i].alias -or $actual[$i*3+2] -cne ('alias '+$controls[$i].alias)){throw 'Query emission is not alias/value/alias'}
}
$testDir=Join-Path $own 'offline_fixture';New-Item -ItemType Directory -Force $testDir|Out-Null
$GameLog=Join-Path $testDir 'raw.log'
$lines=@();$expect=@{}
foreach($c in $controls){$value=if($c.type -eq 'bool'){'FALSE'}else{'0.375'};$ack=$c.alias+': /'+$c.lookup_path;$lines+=@($ack,$value,$ack);$expect[$c.alias]=$value}
[IO.File]::WriteAllText($GameLog,([string]::Join("`n",$lines)+"`n"),[Text.UTF8Encoding]::new($false))
$script:gameLines=[Collections.Generic.List[string]]::new();$script:gameBytes=0L;$script:prefixHash=$null
$read=Read-Values 0
if($read.proofs.Count -ne 28 -or $read.values.Count -ne 28){throw 'Actual raw reader did not decode every typed control/context'}
foreach($key in $expect.Keys){if($expect[$key] -cne $read.values[$key]){throw 'Actual typed value mismatch'}}
$commands=@(Commands-For $expect)
if($commands.Count -ne 28 -or $commands[0] -cne 'set E51 0.375' -or $commands[-1] -cne 'set CCLOUD 0.375'){throw 'Actual restore command generator is malformed'}
# The unchanged reviewed reader must refuse an equal-length rewritten prefix.
$raw=[IO.File]::ReadAllText($GameLog);[IO.File]::WriteAllText($GameLog,$raw.Replace('0.375','0.875'),[Text.UTF8Encoding]::new($false))
$rejected=$false;try{$null=Lines}catch{if($_.Exception.Message -match 'prefix changed'){$rejected=$true}else{throw}}
if(!$rejected){throw 'Reader accepted rewritten prior proof'}
# Exercise the actual corrected capture wrapper on the retained real native BMP/CSV/motion.
$captureNode=$ast.FindAll({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Capture-Phase'},$true)|Select-Object -First 1
Invoke-Expression $captureNode.Extent.Text
$fixture=Get-Content -Raw (Join-Path $own 'CAPTURE_SOURCE_FIXTURE.json')|ConvertFrom-Json -AsHashtable
if((Get-FileHash -LiteralPath $fixture.frame.path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $fixture.frame.sha256){throw 'Retained actual capture changed'}
$frameRows=[Collections.Generic.List[object]]::new();$script:baselinePose=$null
function Lines {return ,([Collections.Generic.List[string]]::new())}
function Wait-Line([string]$Pattern,[int]$Cursor,[int]$Seconds){
 if($fixture.motion_line -notmatch $Pattern){throw 'Actual signed stationary engine2 motion was rejected'}
 return @{line=$fixture.motion_line;index=$fixture.motion_index}
}
function Capture-PhaseRaw([object]$Phase){$frameRows.Add($fixture.frame)}
Capture-Phase @{name='retained_native_capture_fixture'}
if($frameRows.Count -ne 1 -or $frameRows[0].boost_effect_mask -ne 514 -or $frameRows[0].car_engine_state -ne 2){throw 'Actual capture wrapper confused boostmask with carengine state'}
@{verdict='pass';actual_native_alias_triplets=28;actual_query_commands=84;actual_restore_commands=28;equal_length_prefix_rewrite_rejected=$true;actual_capture_wrapper_accepts_retained_boostmask514=$true;actual_signed_stationary_motion_accepted=$true;game_launched=$false;mocked_only='Owned process/read transport for offline decoder and actual retained frame wrapper; native driver retains genuine process identity';site_credit=0}|ConvertTo-Json -Depth 4|Set-Content (Join-Path $own 'OFFLINE_RESULT.json') -Encoding UTF8
Get-Content (Join-Path $own 'OFFLINE_RESULT.json') -Raw
