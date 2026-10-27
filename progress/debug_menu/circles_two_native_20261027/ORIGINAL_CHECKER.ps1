param([Parameter(Mandatory=$true)][hashtable]$Context)
$ErrorActionPreference='Stop'
. (Join-Path $Context.Case.CaseDir 'BoostBarEvidence.ps1')
. (Join-Path $Context.Case.CaseDir 'CandidateArtifactGuard.ps1')
$script:fail=[Collections.Generic.List[string]]::new()
function Need([bool]$ok,[string]$message){if(!$ok){$script:fail.Add($message)}}
function Get-ExpectedAliasQueryReceipt([string]$AliasName,[string]$RegisteredPath){
 if([string]::IsNullOrEmpty($AliasName) -or [string]::IsNullOrEmpty($RegisteredPath)){throw 'Alias receipt inputs must be nonempty.'}
 if($RegisteredPath.StartsWith('/') -or $RegisteredPath.StartsWith('\') -or $RegisteredPath.EndsWith('/') -or $RegisteredPath.EndsWith('\')){throw 'Alias registration path must be the exact relative path stored in CASE_PLAN.'}
 $segments=@([regex]::Split($RegisteredPath,'[\\/]'))
 if($segments.Count -lt 2){throw 'Alias query path must contain its menu path and variable/function leaf.'}
 foreach($segment in $segments){if([string]::IsNullOrEmpty([string]$segment)){throw 'Alias query path contains an empty menu segment.'}}
 $menuPath='';for($i=0;$i -lt ($segments.Count-1);$i++){$menuPath+='/'+[string]$segments[$i]}
 return ($AliasName+': '+$menuPath+'/'+[string]$segments[-1])
}
function Assert-CircleAliasContract([object]$Plan){
 $contract=$Plan.alias_contract
 Need ($null -ne $contract -and $contract.status -ceq 'author_static_source_contract_confirmed' -and [int]$contract.alias_count -eq 2 -and
      [int]$contract.reported_maximum_bytes -eq 10 -and [int]$contract.reject_if_byte_length_greater_or_equal -eq 10 -and [int]$contract.maximum_legal_ascii_bytes -eq 9) 'pinned CgsScriptInterface alias contract is missing/inconsistent'
 $sourceContract=$contract.source_contract
 Need ([int]$sourceContract.constant_bytes -eq 10 -and [int]$sourceContract.create_alias_rejects_length_greater_equal -eq 10 -and
       [int]$sourceContract.maximum_legal_ascii_bytes -eq 9 -and $sourceContract.observed_create_alias_error_format -ceq 'Alias too long. Max %d' -and
       $sourceContract.observed_alias_query_format -ceq '<alias>: <GetAliasString result>' -and
       [string]$sourceContract.observed_get_alias_string -match 'GetMenuItemPath.*append' -and
       [string]$sourceContract.observed_menu_path -match 'root path is empty') 'pinned source-level CreateAlias/query/path semantics are inconsistent'
 $sourceFiles=@($contract.source_evidence.PSObject.Properties)
 Need ($sourceFiles.Count -eq 4 -and @($sourceFiles|Where-Object{[string]$_.Value.sha256 -notmatch '^[0-9a-f]{64}$'}).Count -eq 0) 'alias source-contract hashes are absent/malformed'
 $controls=@($Plan.controls);$names=@($controls|ForEach-Object{[string]$_.alias})
 Need ($controls.Count -eq 2 -and ($names -join '|') -ceq 'WCircles|PCircles') 'plan does not contain exactly the two short aliases'
 foreach($name in $names){$bytes=[Text.Encoding]::UTF8.GetByteCount($name)
  Need (![string]::IsNullOrEmpty($name) -and $name -match '^[A-Za-z0-9_]+$' -and $bytes -ge 1 -and $bytes -le 10 -and $bytes -lt 10) ('alias fails the nonempty <=10/source-reject contract: '+$name)}
}
function Read-Json([string]$path){if(!(Test-Path -LiteralPath $path -PathType Leaf)){return $null};return Get-Content -LiteralPath $path -Raw|ConvertFrom-Json}
function Text-File([string]$path){if(!(Test-Path -LiteralPath $path -PathType Leaf)){return ''};return [IO.File]::ReadAllText($path)}
function Same-Number($a,$b){
 if($null -eq $a -or $null -eq $b){return $false}
 try{$x=Get-FiniteNumber ([Convert]::ToString($a,[cultureinfo]::InvariantCulture));$y=Get-FiniteNumber ([Convert]::ToString($b,[cultureinfo]::InvariantCulture));return ([Math]::Abs($x-$y) -le 0.000001)}catch{return $false}
}
function Utc-Ticks($value){
 if($value -is [DateTime]){return $value.ToUniversalTime().Ticks}
 if($value -is [DateTimeOffset]){return $value.UtcDateTime.Ticks}
 if([string]::IsNullOrWhiteSpace($value)){throw 'Missing canonical start time.'}
 return ([DateTime]::ParseExact($value,'o',[cultureinfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind)).ToUniversalTime().Ticks
}
function Exact-LinePositions([string[]]$lines,[string]$wanted){
 $at=[Collections.Generic.List[int]]::new();for($i=0;$i -lt $lines.Count;$i++){if($lines[$i] -ceq $wanted){$at.Add($i)}};return @($at.ToArray())
}
function Exact-LineAt([string[]]$lines,[string]$wanted){$at=@(Exact-LinePositions $lines $wanted);if($at.Count -ne 1){return -1};return [int]$at[0]}
function Check-IndexedRaw([string]$scope,$index,[string]$line){
 $valid=$null -ne $index -and [int]$index -ge 0 -and [int]$index -lt $script:logLines.Count -and ![string]::IsNullOrWhiteSpace($line)
 Need $valid ($scope+' missing/out-of-range zero-based raw index')
 if($valid){Need ($script:logLines[[int]$index] -ceq $line) ($scope+' indexed actual raw line differs')}
}
function Check-CircleReadbacks([string]$scope,[object]$window,[object[]]$rows,[bool]$worldExpected,[bool]$propExpected,[int]$stageIndex=-1,[string]$stageLine='',[string]$ackAlias=''){
 $bound=Get-BoundLogWindow $script:proofBytes $window;$lines=@($bound.lines)
 Need ($rows.Count -eq 2) ($scope+' must contain exactly the two named F2 aliases')
 if(![string]::IsNullOrWhiteSpace($ackAlias) -and $stageIndex -lt 0){throw ($scope+' has no nonnegative F1 ACK index.')}
 if($stageIndex -ge 0){
  Need ($stageIndex -lt $lines.Count -and $lines[$stageIndex] -ceq $stageLine) ($scope+' F1 ACK index differs inside its hashed window')
  for($i=0;$i -lt [Math]::Min($stageIndex,$lines.Count);$i++){Need ($lines[$i] -cne $stageLine) ($scope+' earlier duplicate F1 ACK')}
 }
 $lastValue=-1
 foreach($control in @($script:plan.controls)){
  $alias=[string]$control.alias;$path=[string]$control.path;$label=Get-ExpectedAliasQueryReceipt $alias $path
  $expected=if($alias -ceq [string]$script:plan.controls[0].alias){$worldExpected}else{$propExpected};$expectedText=if($expected){'TRUE'}else{'FALSE'}
  $found=@($rows|Where-Object{$_.name -ceq $alias})
  if($found.Count -ne 1){Need $false ($scope+' missing/duplicate F2 alias '+$alias);continue}
  $read=$found[0];$li=[int]$read.label_window_index;$vi=[int]$read.value_window_index
  Need ($null -ne $read.label_window_index -and $null -ne $read.value_window_index) ($scope+' absent cursor-relative F2 indexes '+$alias)
  Need ([string]$read.path -ceq $path -and [string]$read.text -ceq $expectedText) ($scope+' F2 path/parsed bool differs '+$alias)
  $valid=$li -ge 0 -and $li -lt $lines.Count -and $vi -gt $li -and $vi -lt $lines.Count
  Need $valid ($scope+' F2 indexes outside actual window '+$alias)
  if($valid){
   Need ($lines[$li] -ceq $label -and $lines[$li] -ceq [string]$read.label_line -and $lines[$vi] -ceq [string]$read.value_line -and $lines[$vi] -ceq $expectedText) ($scope+' raw indexed F2 label/value does not equal expected bool '+$alias)
   for($i=$li+1;$i -lt $vi;$i++){Need ([string]::IsNullOrWhiteSpace($lines[$i])) ($scope+' indexed value is not first nonblank line after alias '+$alias)}
   $lastValue=[Math]::Max($lastValue,[int]$bound.begin_line_index+$vi)
  }
  if($stageIndex -ge 0){Need ($li -gt $stageIndex) ($scope+' F2 precedes F1 '+$alias)}
  $positions=@(Exact-LinePositions $lines $label)
  if($stageIndex -ge 0 -and $alias -ceq $ackAlias){
   Need ($stageLine -ceq $label -and $positions.Count -eq 2 -and $positions[0] -eq $stageIndex -and $positions[1] -eq $li) ($scope+' F1/F2 occurrence/index policy differs '+$alias)
  }else{Need ($positions.Count -eq 1 -and $positions[0] -eq $li) ($scope+' F2 label missing/duplicated/misindexed '+$alias)}
 }
 return [pscustomobject]@{bound=$bound;last_value_global=$lastValue;stage_global=([int]$bound.begin_line_index+$stageIndex)}
}
function Check-PhysicsHeld([string]$scope,[object]$p){
 Need ($p.id -eq 0 -and $p.type -eq 0 -and $p.donut -eq 0 -and $p.onLine -eq 0 -and $p.ag -eq 1 -and $p.force -eq 0 -and
       $p.boost -eq 0 -and $p.showtime -eq 0 -and $p.crash -eq 0 -and [Math]::Abs($p.gas) -le 0.05 -and $p.brake -gt 0.95 -and $p.hb -gt 0.95 -and
       [Math]::Abs($p.steer) -le 0.01 -and $p.dt -gt 0 -and [Math]::Sqrt($p.vx*$p.vx+$p.vy*$p.vy+$p.vz*$p.vz) -le 1.0) ($scope+' actual slot0 physics is not held brake+handbrake without forcing/contact/state bypass')
}
function Check-Held([string]$scope,[object]$accept,[int]$after,[int]$before){
 Need ($null -ne $accept -and $accept.status -ceq 'observed_engine2_brake_handbrake_near_zero') ($scope+' held-player acceptance missing')
 if($null -eq $accept){return $null}
 Need ($null -ne $accept.origin_cursor -and [int]$accept.origin_cursor -eq $script:playerOrigin -and $null -ne $accept.fresh_cursor -and
       [int]$accept.fresh_cursor -gt $after -and [int]$accept.fresh_cursor -lt $before) ($scope+' attach/fresh cursor is not after preceding transaction')
 Need ((Same-Number $accept.max_speed 0.25) -and (Same-Number $accept.gross_speed_bound 1.0) -and (Same-Number $accept.gross_planar_bound 1.0)) ($scope+' screening bounds differ from retained producer')
 $motion=@($accept.motion);$physics=@($accept.physics_inputs)
 Need ($motion.Count -eq 4 -and $physics.Count -ge 2 -and $physics.Count -le 4) ($scope+' needs four fresh motion and two to four physics rows')
 $previous=-1;$previousN=-1L;$maxIndex=-1;$path=0.0;$last=$null;$indices=[Collections.Generic.List[int]]::new()
 foreach($row in $motion){
  # Historical held-player rows use one-based line numbers, unlike motion/ACK indexes.
  $index=[int]$row.line-1;Check-IndexedRaw ($scope+' motion') $index ([string]$row.text)
  Need ($null -ne $row.line -and $index -ge [int]$accept.fresh_cursor -and $index -gt $previous -and $index -lt $before) ($scope+' motion line stale/duplicated/after capture or write')
  $m=Read-PlayerMotionLine ([string]$row.text)
  Need ($m.engine -eq 2 -and $m.n -gt $previousN -and $m.n -gt 0 -and $m.speed -ge 0 -and $m.speed -le 0.25 -and [Math]::Abs($m.gas) -le 0.05 -and [Math]::Abs($m.steer) -le 0.01) ($scope+' actual fresh engine2/near-zero motion differs')
  Need ([long]$row.n -eq $m.n -and (Same-Number $row.x $m.x) -and (Same-Number $row.y $m.y) -and (Same-Number $row.z $m.z) -and (Same-Number $row.speed $m.speed)) ($scope+' motion metadata differs from indexed actual raw values')
  if($null -ne $last){$dx=$m.x-$last.x;$dz=$m.z-$last.z;$path+=[Math]::Sqrt($dx*$dx+$dz*$dz)}
  $last=$m;$previous=$index;$previousN=$m.n;$maxIndex=[Math]::Max($maxIndex,$index);$indices.Add($index)
 }
 Need ($path -le 0.5 -and (Same-Number $accept.sampled_planar_path $path)) ($scope+' recomputed planar path differs/exceeds bound')
 $actualIndices=[Collections.Generic.List[int]]::new()
 for($i=[Math]::Max(0,[int]$accept.fresh_cursor);$i -le $previous -and $i -lt $script:logLines.Count;$i++){if($script:logLines[$i].StartsWith('[motion] ')){$actualIndices.Add($i)}}
 $lastFour=if($actualIndices.Count -ge 4){@($actualIndices.ToArray()|Select-Object -Last 4)}else{@()}
 Need (($lastFour -join ',') -ceq ($indices.ToArray() -join ',')) ($scope+' selected four motion rows skip actual fresh raw samples')
 $previous=-1
 foreach($row in $physics){
  $index=[int]$row.line-1;Check-IndexedRaw ($scope+' physics') $index ([string]$row.text)
  Need ($null -ne $row.line -and $index -ge [int]$accept.fresh_cursor -and $index -gt $previous -and $index -lt $before) ($scope+' physics line stale/duplicated/after capture or write')
  $p=Read-PlayerPhysicsLine ([string]$row.text);Check-PhysicsHeld $scope $p;$previous=$index;$maxIndex=[Math]::Max($maxIndex,$index)
 }
 return [pscustomobject]@{last_line_index=$maxIndex;last_motion=$last}
}
function Check-Capture([string]$label,[string]$id,[string]$state,[object]$capture,[object]$readback,[object]$stage,[int]$sequence){
 $frames=@($capture.frames);Need ($frames.Count -eq 1 -and $capture.label -ceq $label) ($label+' must contain one exact labelled frame')
 if($frames.Count -ne 1){return $null}
 $frame=$frames[0];$window=$readback.bound;$lines=@($window.lines)
 $ack=[regex]::Match([string]$capture.ack_line,'^\[frame-request\] pid=(\d+) slot=(\d+) seq=(\d+) present=(\d+) file=(bb_\d{6}\.bmp)$')
 $ackAt=Exact-LineAt $lines ([string]$capture.ack_line);$ackGlobal=[int]$window.begin_line_index+$ackAt
 Need ($ack.Success -and $ackAt -ge 0 -and $null -ne $capture.ack_line_index -and [int]$capture.ack_line_index -eq $ackGlobal -and
       (Exact-LineAt $script:logLines ([string]$capture.ack_line)) -eq $ackGlobal) ($label+' ACK absent/duplicated/misindexed/outside raw state window')
 Need ($ack.Success -and [int]$ack.Groups[1].Value -eq [int]$script:owner.pid -and [int]$ack.Groups[2].Value -eq [int]$Context.Slot -and [int]$ack.Groups[3].Value -eq $sequence -and
       [int]$frame.sequence -eq $sequence -and [int]$ack.Groups[4].Value -eq [int]$capture.present -and $ack.Groups[5].Value -ceq [string]$frame.name) ($label+' raw ACK PID/slot/sequence/present/file differs')
 $fresh=[int]$capture.phase_fresh_cursor_line_index;$request=[int]$capture.request_cursor_line_index
 Need ($null -ne $capture.phase_fresh_cursor_line_index -and $null -ne $capture.request_cursor_line_index -and $fresh -gt [int]$readback.last_value_global -and
       $request -gt $fresh -and $request -le $ackGlobal) ($label+' F2 -> fresh-player -> request -> ACK raw order differs')
 $engineRows=@($script:manifest.preflight.engine2_phase_receipts|Where-Object{$_.label -ceq $label -and $_.site_id -ceq $id -and $_.state -ceq $state})
 $heldRows=@($script:manifest.preflight.held_player_capture_receipts|Where-Object{$_.label -ceq $label -and $_.site_id -ceq $id -and $_.state -ceq $state})
 Need ($engineRows.Count -eq 1 -and $heldRows.Count -eq 1) ($label+' lacks unique phase engine2/held-player receipts')
 $held=$null
 if($heldRows.Count -eq 1){
  Need ([int]$heldRows[0].player_acceptance.fresh_cursor -eq $fresh) ($label+' held-player fresh cursor differs from capture')
  $held=Check-Held ($label+' capture') $heldRows[0].player_acceptance ([int]$readback.last_value_global) $request
 }
 $witness=$capture.player_engine_witness;Need ($null -ne $witness) ($label+' captured actual player witness missing')
 if($null -ne $witness){
  Check-IndexedRaw ($label+' engine2') $witness.index ([string]$witness.line)
  $m=Read-PlayerMotionLine ([string]$witness.line);$index=[int]$witness.index
  Need ($index -ge $fresh -and $index -gt [int]$readback.last_value_global -and $index -lt $request -and $index -ge [int]$window.begin_line_index -and
        $index -lt [int]$window.end_line_index -and $m.engine -eq 2 -and [int]$witness.engine -eq 2 -and [long]$witness.sample -eq $m.n -and $m.n -gt 0 -and
        (Same-Number $witness.x $m.x) -and (Same-Number $witness.y $m.y) -and (Same-Number $witness.z $m.z) -and (Same-Number $witness.mph $m.mph)) ($label+' engine2 motion not actual/fresh/post-F2/before-request')
  if($null -ne $held){
   $latestHeldMotion=[int](($heldRows[0].player_acceptance.motion|ForEach-Object{[int]$_.line-1}|Measure-Object -Maximum).Maximum)
   Need ($index -ge $latestHeldMotion) ($label+' engine2 witness predates accepted fresh motion')
  }
  if($engineRows.Count -eq 1){
   $phase=$engineRows[0]
   Need ([string]$phase.stage_complete_line -ceq [string]$stage.line -and [int]$phase.stage_completion_window_index -eq [int]$stage.relative_index -and
         [int]$phase.stage_window_begin_line_index -eq [int]$stage.begin_line_index -and [string]$phase.motion_line -ceq [string]$witness.line -and
         [int]$phase.motion_line_index -eq $index -and [long]$phase.motion_sample -eq $m.n) ($label+' phase receipt does not join actual F1/setup anchor and captured motion')
  }
 }
 $topRows=@($script:manifest.frames|Where-Object{[int]$_.sequence -eq $sequence});Need ($topRows.Count -eq 1) ($label+' frame sequence absent/duplicated in roster')
 if($topRows.Count -eq 1){
  $top=$topRows[0]
  Need ($top.label -ceq $label -and $top.site_id -ceq $id -and $top.state -ceq $state -and $top.name -ceq $frame.name -and $top.sha256 -ceq $frame.sha256 -and
        [long]$top.bytes -eq [long]$frame.bytes -and [int]$top.present -eq [int]$capture.present -and $top.ack_line -ceq $capture.ack_line -and [int]$top.ack_line_index -eq $ackGlobal -and
        [int]$top.request_cursor_line_index -eq $request -and [int]$top.phase_fresh_cursor_line_index -eq $fresh) ($label+' top-level frame receipt differs from actual state capture')
 }
 $name=[string]$frame.name;Need ($name -cmatch '^bb_\d{6}\.bmp$' -and [string]$frame.sha256 -cmatch '^[0-9a-f]{64}$') ($label+' invalid retained frame name/hash')
 if($name -cmatch '^bb_\d{6}\.bmp$'){
  $path=Join-Path $script:frameDir $name;Need (Test-Path -LiteralPath $path -PathType Leaf) ($label+' actual BMP missing')
  if(Test-Path -LiteralPath $path -PathType Leaf){$item=Get-Item -LiteralPath $path;Need (!($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -and $item.Length -gt 54 -and
      $item.Length -eq [long]$frame.bytes -and (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ceq [string]$frame.sha256) ($label+' regular BMP raw hash/size differs')}
 }
 $csvRows=@($script:csvRows|Where-Object{[int]$_.present -eq [int]$capture.present});Need ($csvRows.Count -eq 1 -and $null -ne $capture.csv) ($label+' actual CSV lacks unique row for ACK present')
 if($csvRows.Count -eq 1 -and $null -ne $capture.csv){
  $row=$csvRows[0];$cols=$row.columns;$claimed=$capture.csv
  Need ([string]$claimed.raw_line -ceq [string]$row.line -and [int]$claimed.present -eq [int]$row.present -and [int]$claimed.columns -eq $cols.Count -and
        (Same-Number $claimed.live_boost_fraction (Get-FiniteNumber $cols[3])) -and [uint32]$claimed.boost_effect_mask -eq [uint32]$cols[$cols.Count-1] -and
        (Same-Number $claimed.player_x (Get-FiniteNumber $cols[20])) -and (Same-Number $claimed.player_y (Get-FiniteNumber $cols[21])) -and
        (Same-Number $claimed.player_z (Get-FiniteNumber $cols[22]))) ($label+' CSV metadata differs from actual raw present row')
  if($topRows.Count -eq 1){Need ((ConvertTo-Json $topRows[0].csv -Depth 5 -Compress) -ceq (ConvertTo-Json $capture.csv -Depth 5 -Compress)) ($label+' top/state raw CSV receipts differ')}
  if($null -ne $held -and $null -ne $held.last_motion){$dx=(Get-FiniteNumber $cols[20])-$held.last_motion.x;$dz=(Get-FiniteNumber $cols[22])-$held.last_motion.z;Need ([Math]::Sqrt($dx*$dx+$dz*$dz) -le 1.0) ($label+' CSV player position outside same gross planar bound from actual player motion')}
 }
 return [pscustomobject]@{ack_global=$ackGlobal;present=[int]$capture.present;window_end=[int]$window.end_line_index}
}

try{
 $caseDir=[string]$Context.Case.CaseDir;$runDir=[string]$Context.RunDir;$script:frameDir=Join-Path $runDir 'frames'
 Need ([IO.Path]::GetFullPath([string]$Context.FrameDir) -ieq [IO.Path]::GetFullPath($script:frameDir)) 'Context frame directory differs from exact retained run frames'
 $script:plan=Read-Json (Join-Path $runDir 'CASE_PLAN.used.json')
 Assert-CircleAliasContract $script:plan
 $script:manifest=Read-Json (Join-Path $runDir 'boost-hud-witnesses.json');$script:owner=Read-Json (Join-Path $runDir 'boost-hud-owner.json')
 $binding=Read-Json (Join-Path $runDir 'runtime-binding.used.json');$usedSourceBindings=Read-Json (Join-Path $runDir 'CASE_SOURCE_BINDINGS.used.json')
 $artifact=Read-Json (Join-Path $runDir 'HOSTED_ARTIFACT_BINDING.used.json');$stageBinding=Read-Json (Join-Path $runDir 'STAGING.used.json');$review=Read-Json (Join-Path $runDir 'ROOT_PRELAUNCH_REVIEW.used.json')
 $terminal=Read-Json (Join-Path $runDir 'flow/terminal-status.json');$handoff=Read-Json (Join-Path $caseDir 'ROOT_HANDOFF.json')
 foreach($required in @($script:plan,$script:manifest,$script:owner,$binding,$usedSourceBindings,$artifact,$stageBinding,$review,$terminal,$handoff)){if($null -eq $required){throw 'Missing canonical/helper/candidate/retained binding receipt.'}}
 $gameLog=[string]$Context.Log;$raw=Text-File $gameLog;$lines=[Collections.Generic.List[string]]::new()
 if(Test-Path -LiteralPath $gameLog -PathType Leaf){
  $text=[Text.UTF8Encoding]::new($false,$false).GetString([IO.File]::ReadAllBytes($gameLog));$parts=$text.Split([char]10)
  for($i=0;$i -lt $parts.Length-1;$i++){$line=$parts[$i];if($line.EndsWith([string][char]13)){$line=$line.Substring(0,$line.Length-1)};$lines.Add($line)}
 }
 $script:logLines=@($lines.ToArray());$script:proofBytes=Get-CompleteLogBytes $script:logLines
 Need ($script:logLines.Count -gt 0 -and $raw -notmatch '\[ASSERT(?:\s+\d+)?\]|\[EXCEPTION\]') 'actual game log empty or contains assert/exception'
 foreach($pair in @(
  @('CASE_PLAN.used.json','CASE_PLAN.json'),@('runtime-binding.used.json','BINDING.json'),@('CASE_SOURCE_BINDINGS.used.json','CASE_SOURCE_BINDINGS.json'),
  @('HOSTED_ARTIFACT_BINDING.used.json','HOSTED_ARTIFACT_BINDING.json'),@('STAGING.used.json','STAGING.json'),@('ROOT_PRELAUNCH_REVIEW.used.json','ROOT_PRELAUNCH_REVIEW.json')
 )){Need ((Get-FileHash -LiteralPath (Join-Path $runDir $pair[0]) -Algorithm SHA256).Hash -ceq (Get-FileHash -LiteralPath (Join-Path $caseDir $pair[1]) -Algorithm SHA256).Hash) ('retained launch data changed '+$pair[0])}
 # Recheck retained candidate blobs without reading physical World/Prop sources.
 $guarded=Assert-CurrentCandidateArtifact $script:plan $binding $usedSourceBindings $caseDir 'D:\Reverse\BP-Decomp_Workflow' $stageBinding $review
 $expectedIds=@('BrnWorld::WorldEntityModule::Construct#0002','BrnWorld::PropEntityModule::Construct#0001')
 Need (@($script:plan.controls).Count -eq 2 -and (@($script:plan.selected_site_ids) -join '|') -ceq ($expectedIds -join '|') -and
       (@($script:manifest.selected_site_ids) -join '|') -ceq ($expectedIds -join '|') -and [int]$script:manifest.site_count -eq 2 -and [int]$script:manifest.selected_site_count -eq 2) 'case/manifest is not exactly the two selected constructor bools'
 Need ($script:manifest.status -ceq 'machine_evidence_awaiting_root_visual_review' -and @($script:manifest.deferred_sites).Count -eq 0 -and [int]$script:manifest.planned_state_count -eq 6 -and
       [int]$script:manifest.site_state_count -eq 6 -and [int]$script:manifest.frame_count -eq 7 -and @($script:manifest.frames).Count -eq 7) 'full machine evidence requires six states/seven frames without deferred sites'
 foreach($field in @('candidate_source','candidate_tree','candidate_workflow_source','candidate_workflow_tree')){Need ([string]$script:manifest.$field -ceq [string]$script:plan.$field) ('actual manifest identity differs '+$field)}
 Need ($script:manifest.hosted_build_id -ceq $script:plan.hosted_probe_build.id -and $script:manifest.hosted_artifact_id -ceq $artifact.artifact_id -and
       $script:manifest.hosted_artifact_receipt_sha256 -ceq $artifact.receipt_sha256 -and $script:manifest.execution_exe_sha256 -ceq $binding.execution_exe_sha256 -and
       $script:manifest.hosted_artifact_binding_sha256 -ceq (Get-FileHash -LiteralPath (Join-Path $runDir 'HOSTED_ARTIFACT_BINDING.used.json') -Algorithm SHA256).Hash.ToLowerInvariant() -and
       $script:manifest.case_source_bindings_sha256 -ceq (Get-FileHash -LiteralPath (Join-Path $runDir 'CASE_SOURCE_BINDINGS.used.json') -Algorithm SHA256).Hash.ToLowerInvariant()) 'run artifact/source/build/executable receipts differ'
 foreach($path in @($script:plan.candidate_source_files.PSObject.Properties.Name)){
  $p=$script:plan.candidate_source_files.PSObject.Properties[$path].Value;$m=$script:manifest.candidate_source_files.PSObject.Properties[$path].Value
  foreach($field in @('source_commit','snapshot_path','raw_sha256','git_blob_sha1')){Need ([string]$p.$field -ceq [string]$m.$field) ('run source snapshot metadata differs '+$path+'/'+$field)}
 }
 $expectedImage=[IO.Path]::GetFullPath((Join-Path $binding.private_stage_root 'slot/Burnout_PC.exe'))
 Need ($expectedImage -ieq [IO.Path]::GetFullPath((Join-Path $caseDir 'stage/slot/Burnout_PC.exe')) -and [IO.Path]::GetFullPath([string]$script:owner.image) -ieq $expectedImage -and
       $script:owner.exe_sha256 -ceq $binding.execution_exe_sha256 -and [int]$script:owner.pid -gt 0 -and [int]$script:owner.slot -eq [int]$Context.Slot -and
       [int]$script:manifest.slot -eq [int]$Context.Slot -and [int]$binding.slot -eq [int]$Context.Slot) 'helper differs from exact private candidate image/hash/PID/slot'
 $ownerTicks=Utc-Ticks $script:owner.start_utc
 Need ([string]$script:owner.start_utc_ticks -ceq $ownerTicks.ToString() -and [int]$handoff.pid -eq [int]$script:owner.pid -and [IO.Path]::GetFullPath([string]$handoff.image) -ieq $expectedImage -and
       [int]$handoff.slot -eq [int]$Context.Slot -and (Utc-Ticks $handoff.start_utc) -eq $ownerTicks -and [int]$handoff.canonical_launcher_pid -gt 0) 'helper PID/image/start differs from canonical driver handoff'
 Need ($terminal.success -eq $true -and $terminal.launched -eq $true -and $terminal.completed -eq $true -and [int]$terminal.requested_exit -eq 0 -and
       $terminal.direct_creation_handle_retained -eq $true -and $terminal.owned_cleanup_complete -eq $true -and $terminal.input_reset_complete -eq $true -and
       $terminal.foreign_game -eq $false -and $terminal.first_assert_stop -eq $false -and $terminal.runaway_log_abort -eq $false -and [int]$terminal.observed_asserts -eq 0 -and
       [string]::IsNullOrWhiteSpace([string]$terminal.error) -and $terminal.allow_concurrent_games -eq $true -and [int]$terminal.max_other_games_observed -le 1 -and
       $terminal.title_start_requested -eq $true -and $terminal.title_start_ready_observed -eq $true -and
       (!$terminal.game_exited_on_own -or ($null -ne $terminal.game_exit -and [int]$terminal.game_exit -eq 0))) 'canonical terminal lacks owned cleanup/input reset/natural title startup/normal outcome'
 Need ([int]$terminal.owned_pid -eq [int]$script:owner.pid -and [IO.Path]::GetFullPath([string]$terminal.owned_image) -ieq $expectedImage -and
       (Utc-Ticks $terminal.owned_start_utc) -eq $ownerTicks) 'helper and canonical terminal exact PID/image/start differ'
 $flowText=Text-File (Join-Path $runDir 'flow_run.console.log')
 $ownedMarkers=[regex]::Matches($flowText,'(?m)^\[flow\] OWNED_PROCESS pid=(\d+) image=(.*?) start=(\S+) priority=BelowNormal\r?$')
 Need ($ownedMarkers.Count -eq 1) 'canonical console has no unique actual OWNED_PROCESS marker'
 if($ownedMarkers.Count -eq 1){$o=$ownedMarkers[0];Need ([int]$o.Groups[1].Value -eq [int]$script:owner.pid -and [IO.Path]::GetFullPath($o.Groups[2].Value) -ieq $expectedImage -and (Utc-Ticks $o.Groups[3].Value) -eq $ownerTicks) 'canonical console marker differs from helper/handoff/terminal ownership'}
 Need ($flowText -match 'TITLESTART ready' -and $flowText -match 'TITLESTART tap:Start' -and $flowText -match 'pedal\s+t\+\s+0[,.]00s -> brake\+handbrake' -and
       $flowText -notmatch 'SKIP INTRO: launching with -skipvideos' -and $flowText -match 'log confirmed fresh') 'canonical console lacks natural startup/fresh log/held brake+handbrake policy'
 # Keep the allowed distinct other game. Only exact owned PID/image/start must exit.
 $games=@(Get-CimInstance Win32_Process -Filter "Name LIKE 'Burnout%.exe' OR Name='TUB_Burnout_PC_External.exe' OR Name='BrnGame.exe'" -ErrorAction Stop)
 Need ($games.Count -le 1) 'more than one other game remains after owned cleanup'
 foreach($g in $games){
  $rawImage=[string]$g.ExecutablePath;$root=[IO.Path]::GetPathRoot($rawImage)
  Need (![string]::IsNullOrWhiteSpace($rawImage) -and [IO.Path]::IsPathFullyQualified($rawImage) -and ($root -match '^[A-Za-z]:\\$' -or $root -match '^\\\\[^\\]+\\[^\\]+\\?$')) 'remaining other game has no known absolute image'
  if(![string]::IsNullOrWhiteSpace($rawImage)){Need ([IO.Path]::GetFullPath($rawImage) -ine $expectedImage) 'staged owned image is still running'}
  if([int]$g.ProcessId -eq [int]$script:owner.pid){$live=Get-Process -Id ([int]$g.ProcessId) -ErrorAction Stop;Need ($live.StartTime.ToUniversalTime().Ticks -ne $ownerTicks) 'exact owned PID/start is still running'}
 }
 $helperText=Text-File (Join-Path $runDir 'boost-hud-keys.log')
 $done=[regex]::Matches($helperText,'(?m)^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{7}Z) RESULT DONE sites=(\d+) deferred=(\d+) states=(\d+) frames=(\d+)\r?$')
 Need ($done.Count -eq 1 -and $helperText -notmatch '(?m)^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{7}Z RESULT FAIL: [^\r\n]+\r?$') 'helper strict terminal marker missing/duplicated or failure recorded'
 if($done.Count -eq 1){Need ((Utc-Ticks $done[0].Groups[1].Value) -gt $ownerTicks -and [int]$done[0].Groups[2].Value -eq 2 -and [int]$done[0].Groups[3].Value -eq 0 -and [int]$done[0].Groups[4].Value -eq [int]$script:manifest.site_state_count -and [int]$done[0].Groups[5].Value -eq [int]$script:manifest.frame_count) 'strict helper DONE counts/time differ from owned manifest'}
 Need ($script:manifest.line_representation -ceq 'complete UTF-8 lines with blank lines preserved and partial-tail carry; exact named aliases only; no SaveState; hashed complete-line prefix byte bounds; cursor-relative F1 and F2 indexes must point to exact lines inside the bound state window') 'producer/checker complete-line representation changed'
 $csvPath=Join-Path $script:frameDir 'frames.csv';$csvFile=$script:manifest.frame_csv_file
 Need ($null -ne $csvFile -and $csvFile.path -ceq 'frames/frames.csv' -and (Test-Path -LiteralPath $csvPath -PathType Leaf)) 'retained raw frame CSV missing'
 $csvItem=Get-Item -LiteralPath $csvPath
 Need (!($csvItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -and $csvItem.Length -eq [long]$csvFile.bytes -and (Get-FileHash -LiteralPath $csvPath -Algorithm SHA256).Hash.ToLowerInvariant() -ceq [string]$csvFile.sha256) 'retained whole CSV raw hash/bytes differ'
 $script:csvRows=@()
 foreach($line in [IO.File]::ReadAllLines($csvPath)){
  if([string]::IsNullOrWhiteSpace($line)){continue};$cols=$line.Split(',');$present=0;$mask=[uint32]0
  Need ($cols.Count -ge 24 -and [int]::TryParse($cols[0],[ref]$present) -and $present -gt 0 -and [uint32]::TryParse($cols[$cols.Count-1],[ref]$mask)) 'malformed actual frame CSV row'
  foreach($col in $cols){$null=Get-FiniteNumber $col}
  $script:csvRows+=[pscustomobject]@{line=$line;present=$present;columns=$cols}
 }
 Need ($script:csvRows.Count -eq 7 -and @($script:csvRows.present|Select-Object -Unique).Count -eq 7) 'raw CSV is not exactly seven unique presents'
 Need (@($script:manifest.frames.name|Select-Object -Unique).Count -eq 7 -and @($script:logLines|Where-Object{$_ -match '^\[frame-request\] '}).Count -eq 7 -and @(Get-ChildItem -LiteralPath $script:frameDir -File -Filter '*.bmp').Count -eq 7) 'extra/missing/duplicate named captures'
 $attach=$script:manifest.preflight.player_attach_receipt;Check-IndexedRaw 'player attach' $attach.line_index ([string]$attach.line)
 Need ([string]$attach.line -match '^\[ignition\] attach slot 0 type=0\b.*\binCarSelect=0\b' -and [int]$attach.origin_cursor -eq [int]$attach.line_index+1) 'actual player slot0 attach outside CarSelect missing'
 $script:playerOrigin=[int]$attach.origin_cursor
 $startupExit=$script:manifest.preflight.carselect_exit
 $streamAt=Exact-LineAt $script:logLines ([string]$startupExit.streaming_line);$exitAt=Exact-LineAt $script:logLines ([string]$startupExit.exit_line)
 Need ($startupExit.status -ceq 'observed' -and $streamAt -ge 0 -and $exitAt -gt $streamAt -and
       [string]$startupExit.streaming_line -match 'CarSelectManager: streaming complete -- signalling StreamingFinished' -and
       [string]$startupExit.exit_line -match 'CarSelectManager: Exit state is finished') 'actual unique CarSelect streaming/exit receipts missing or unordered'
 $brake=$script:manifest.preflight.player_brake_engine_receipt;Check-IndexedRaw 'player brake/engine startup' $brake.line_index ([string]$brake.line)
 $brakeMatch=[regex]::Match([string]$brake.line,'^\[ignition\] tick state=2 active=1 enableSwitchOff=[01] carInGameMode=[01] inCarSelect=0 crashing=0 accel=([-+0-9.eE]+) brake=([-+0-9.eE]+)$')
 Need ($brakeMatch.Success -and [int]$brake.line_index -ge $script:playerOrigin) 'actual engine2 startup does not follow player attach'
 if($brakeMatch.Success){Need ((Get-FiniteNumber $brakeMatch.Groups[1].Value) -le 0.05 -and (Get-FiniteNumber $brakeMatch.Groups[2].Value) -gt 0.05) 'actual ignition receipt lacks player brake/engine2 state'}
 $natural=$script:manifest.preflight.in_run_natural_baseline
 Need ($null -ne $natural -and $natural.status -ceq 'captured_this_owned_candidate_run' -and $natural.source -ceq $script:plan.candidate_source -and $natural.source_tree -ceq $script:plan.candidate_tree -and
       $natural.workflow_source -ceq $script:plan.candidate_workflow_source -and $natural.workflow_tree -ceq $script:plan.candidate_workflow_tree -and $natural.exe_sha256 -ceq $script:owner.exe_sha256 -and
       [int]$natural.pid -eq [int]$script:owner.pid -and [int]$natural.slot -eq [int]$Context.Slot -and $natural.root_visual_review -ceq 'pending_after_run') 'natural baseline not this candidate/owned run or claims prior pixel approval'
 Need ($null -ne $natural.setup_control_write_commands -and [int]$natural.setup_control_write_commands -eq 0 -and $null -ne $script:manifest.preflight.setup_control_write_commands -and
       [int]$script:manifest.preflight.setup_control_write_commands -eq 0 -and $script:manifest.preflight.initial_alias_baselines.WCircles -eq $false -and
       $script:manifest.preflight.initial_alias_baselines.PCircles -eq $false -and $natural.initial_alias_baselines.WCircles -eq $false -and
       $natural.initial_alias_baselines.PCircles -eq $false -and $null -eq $script:manifest.preflight.root_baseline_pixel_witness) 'natural baseline written/not both original false/inherited pixels'
 $close=[int]$natural.console_close_line_index;Check-IndexedRaw 'natural baseline console close' $natural.console_close_line_index ([string]$natural.console_close_line)
 Need ($close -gt $exitAt -and $close -gt [int]$attach.line_index) 'initial console close predates actual startup/player attach'
 Need ([string]$natural.console_close_line -match '^\[debug-ui\] event=0 visible=0 .* key=0$' -and $script:manifest.preflight.console_close_receipt -ceq $natural.console_close_line -and
       [int]$script:manifest.preflight.console_close_line_index -eq $close) 'actual console close receipt differs'
 $startup=Check-Held 'startup' $script:manifest.preflight.player_startup_acceptance ($script:playerOrigin-1) $close
 $setupStage=[pscustomobject]@{line=[string]$natural.stage_complete_line;relative_index=[int]$natural.stage_completion_window_index;begin_line_index=[int]$natural.stage_window_begin_line_index}
 $setupGlobal=$setupStage.begin_line_index+$setupStage.relative_index
 $setupControls=@($script:plan.controls);$setupReceipts=@($script:manifest.preflight.setup_input_receipts.alias_registrations)
 Need ($setupControls.Count -eq 2 -and $setupReceipts.Count -eq 2) 'setup lacks both planned alias-query receipts'
 $enterIndex=[int]$script:manifest.preflight.setup_input_receipts.enter_line_index
 $setupStartIndex=[int]$script:manifest.preflight.setup_input_receipts.setup_start_line_index
 Need ($setupStartIndex -ge 0 -and $enterIndex -ge $setupStartIndex -and $setupStartIndex -eq $setupStage.begin_line_index) 'fresh setup-start/Enter indices are absent or inconsistent'
 if($setupStartIndex -ge 0){
  foreach($control in $setupControls){
   $staleReceipt=Get-ExpectedAliasQueryReceipt ([string]$control.alias) ([string]$control.path)
   for($i=0;$i -lt [Math]::Min($setupStartIndex,$script:logLines.Count);$i++){Need ($script:logLines[$i] -cne $staleReceipt) ('stale alias-query receipt precedes setup: '+[string]$control.alias)}
  }
 }
 if($setupControls.Count -eq 2 -and $setupReceipts.Count -eq 2){
  for($i=0;$i -lt 2;$i++){
   $control=$setupControls[$i];$receipt=$setupReceipts[$i]
   $expectedReceipt=Get-ExpectedAliasQueryReceipt ([string]$control.alias) ([string]$control.path)
   Need ([string]$receipt.alias -ceq [string]$control.alias -and [string]$receipt.target_path -ceq [string]$control.path -and
        [string]$receipt.expected_line -ceq $expectedReceipt -and [string]$receipt.line -ceq $expectedReceipt) ('setup alias receipt differs from exact registered path: '+[string]$control.alias)
   Check-IndexedRaw ('setup alias receipt '+[string]$control.alias) $receipt.line_index $expectedReceipt
   Need ([int]$receipt.line_index -ge $setupStartIndex -and [int]$receipt.line_index -lt $close) ('setup alias receipt is outside fresh setup/console-close window: '+[string]$control.alias)
   if($i -gt 0){Need ([int]$receipt.line_index -gt [int]$setupReceipts[$i-1].line_index) 'setup alias receipts are not in registration/query order'}
  }
 }
 Check-IndexedRaw 'setup alias anchor' $setupGlobal $setupStage.line
 $lastControl=$setupControls[-1];$lastAliasReceipt=Get-ExpectedAliasQueryReceipt ([string]$lastControl.alias) ([string]$lastControl.path)
 Need ($setupStage.line -ceq $lastAliasReceipt -and $setupReceipts.Count -eq 2 -and $setupGlobal -eq [int]$setupReceipts[-1].line_index -and $setupGlobal -lt $close) 'natural setup completion is not the final exact alias-query receipt before close'
 $setupLines=@([IO.File]::ReadAllLines((Join-Path $runDir 'setup.txt')));$trigger=Read-Json (Join-Path $runDir 'ROOT_TRIGGER_CONTEXT.json');$rel=[string]$trigger.run_relative_path
 $expectedSetup=[Collections.Generic.List[string]]::new()
 foreach($control in $setupControls){$expectedSetup.Add(('alias "'+[string]$control.alias+'" "'+[string]$control.path+'"'))}
 $expectedSetup.Add(('bind F1 exec "'+$rel+'/stage_001.txt"'));$expectedSetup.Add(('bind F2 exec "'+$rel+'/readback.txt"'))
 foreach($control in $setupControls){$expectedSetup.Add(('alias "'+[string]$control.alias+'"'))}
 Need (($setupLines -join "`n") -ceq ($expectedSetup.ToArray() -join "`n")) 'actual exec setup differs from the two aliases derived from their exact target paths plus F1/F2'
 $actualCfg=Join-Path $caseDir 'stage/data/b1.cfg'
 Need ((Get-FileHash -LiteralPath $actualCfg -Algorithm SHA256).Hash -ceq
       (Get-FileHash -LiteralPath (Join-Path $runDir 'setup.txt') -Algorithm SHA256).Hash) 'actual executed private b1.cfg differs from the retained zero-write setup script'
 $actualReadback=@([IO.File]::ReadAllLines((Join-Path $runDir 'readback.txt')));$expectedReadback=[Collections.Generic.List[string]]::new()
 foreach($control in $setupControls){$expectedReadback.Add(('alias "'+[string]$control.alias+'"'));$expectedReadback.Add([string]$control.alias)}
 Need ($actualReadback.Count -eq 4 -and (@($actualReadback|Sort-Object) -join '|') -ceq (@($expectedReadback.ToArray()|Sort-Object) -join '|')) 'retained F2 script differs from the two read-only alias queries'
 $input=$script:manifest.preflight.setup_key_sequence_before_enter;$inputCursor=[int]$input.cursor_line_count;$codes=@()
 $setupInputEndGlobal=[Math]::Max($setupGlobal,$enterIndex)
 Need ($input.command -ceq 'exec b1.cfg' -and $inputCursor -ge 0 -and $inputCursor -lt $setupInputEndGlobal -and $setupInputEndGlobal -lt $close) 'typed setup command/cursor/Enter window invalid'
 for($i=$inputCursor;$i -le $setupInputEndGlobal;$i++){if($script:logLines[$i] -match '^\[debug-ui\].*visible=1 .*key=(\d+)$' -and [int]$Matches[1] -ne 0){$codes+=[int]$Matches[1]}}
 $expectedCodes=@(101,120,101,99,32,98,49,46,99,102,103,10)
 Need (($codes -join ',') -ceq ($expectedCodes -join ',')) 'actual indexed setup key stream differs from exec b1.cfg plus Enter'
 $readback=Check-CircleReadbacks 'initial baseline F2' $script:manifest.preflight.baseline_alias_readback_window @($script:manifest.preflight.baseline_alias_readbacks) $false $false
 Need ([int]$readback.bound.begin_line_index -gt $close) 'initial F2 does not follow actual console close'
 $baselineWindow=Get-BoundLogWindow $script:proofBytes $natural.log_window
 Need ($natural.log_window.begin.sha256 -ceq $script:manifest.preflight.baseline_alias_readback_window.begin.sha256 -and [long]$natural.log_window.begin.bytes -eq [long]$script:manifest.preflight.baseline_alias_readback_window.begin.bytes) 'natural capture window does not begin at actual initial F2 prefix'
 $readback.bound=$baselineWindow
 Need ((ConvertTo-Json $natural.capture -Depth 12 -Compress) -ceq (ConvertTo-Json $script:manifest.preflight.baseline_capture -Depth 12 -Compress)) 'natural baseline and retained baseline capture differ'
 $previous=Check-Capture 'in-run-natural-baseline' '' 'baseline' $natural.capture $readback $setupStage 1
 $baselineEngine=@($script:manifest.preflight.engine2_phase_receipts|Where-Object{$_.label -ceq 'in-run-natural-baseline'})
 $baselineHeld=@($script:manifest.preflight.held_player_capture_receipts|Where-Object{$_.label -ceq 'in-run-natural-baseline'})
 Need ($baselineEngine.Count -eq 1 -and $baselineHeld.Count -eq 1 -and
       (ConvertTo-Json $natural.engine2_receipt -Depth 8 -Compress) -ceq (ConvertTo-Json $baselineEngine[0] -Depth 8 -Compress) -and
       (ConvertTo-Json $natural.held_player_receipt -Depth 12 -Compress) -ceq (ConvertTo-Json $baselineHeld[0] -Depth 12 -Compress)) 'nested natural-baseline phase receipts differ from actual checked phase rows'
 Need (@($script:manifest.preflight.engine2_phase_receipts).Count -eq 7 -and @($script:manifest.preflight.held_player_capture_receipts).Count -eq 7 -and @($script:manifest.preflight.held_player_write_receipts).Count -eq 6) 'extra/missing per-phase engine2/held-player receipts'
 $sites=@($script:manifest.sites);Need ($sites.Count -eq 2 -and (@($sites.site_id) -join '|') -ceq ($expectedIds -join '|')) 'site roster/order differs'
 $flatStates=@()
 foreach($id in $expectedIds){
  $siteRows=@($sites|Where-Object{$_.site_id -ceq $id});Need ($siteRows.Count -eq 1) ('site absent/duplicated '+$id)
  if($siteRows.Count -ne 1){continue};$site=$siteRows[0];$states=@($site.states)
  Need ($site.status -ceq 'machine_evidence_awaiting_root_visual_review' -and $states.Count -eq 3 -and (@($states.state) -join '|') -ceq 'positive|negative|restore') ('site lacks ordered positive/negative/restore states '+$id)
  foreach($s in $states){$flatStates+=[pscustomobject]@{id=$id;row=$s}}
 }
 Need ($flatStates.Count -eq 6 -and @($script:plan.state_sequence).Count -eq 6) 'state schedule is not exactly six'
 $lastState=$null
 for($j=0;$j -lt $flatStates.Count;$j++){
  $id=$flatStates[$j].id;$s=$flatStates[$j].row;$label=$id+'/'+[string]$s.state;$sequence=$j+2;$isWorld=$id -ceq $expectedIds[0]
  $world=$isWorld -and $s.state -ceq 'positive';$prop=!$isWorld -and $s.state -ceq 'positive';$worldText=if($world){'TRUE'}else{'FALSE'};$propText=if($prop){'TRUE'}else{'FALSE'}
  $planned=$script:plan.state_sequence[$j]
  Need ($planned.control -ceq $id -and $planned.state -ceq $s.state -and $planned.values.WCircles -eq $world -and $planned.values.PCircles -eq $prop) ($label+' differs from isolated bool schedule')
  Need ($s.actual_values.WCircles -ceq $worldText -and $s.actual_values.PCircles -ceq $propText -and [string]$s.requested -ceq $(if($isWorld){$worldText}else{$propText}) -and
        [string]$s.actual -ceq [string]$s.requested -and $s.baseline -ceq 'FALSE') ($label+' parsed bool request/readback/baseline differs')
  $controlIndex=if($isWorld){0}else{1};$selectedControl=$script:plan.controls[$controlIndex]
  $alias=[string]$selectedControl.alias;$path=[string]$selectedControl.path;$expectedAck=Get-ExpectedAliasQueryReceipt $alias $path
  Need ($null -ne $s.stage_completion_window_index -and $s.stage_completion_line -ceq $expectedAck) ($label+' missing exact source-derived F1 marker/index')
  $r=Check-CircleReadbacks $label $s.log_window @($s.alias_readbacks) $world $prop ([int]$s.stage_completion_window_index) ([string]$s.stage_completion_line) $alias
  Need ([int]$r.bound.begin_line_index -ge [int]$previous.window_end -and [int]$r.stage_global -gt [int]$previous.ack_global) ($label+' raw window/F1 precedes previous accepted frame')
  $writeRows=@($script:manifest.preflight.held_player_write_receipts|Where-Object{$_.label -ceq $label});Need ($writeRows.Count -eq 1) ($label+' lacks unique pre-write acceptance')
  if($writeRows.Count -eq 1){$null=Check-Held ($label+' before write') $writeRows[0].player_acceptance ([int]$previous.ack_global) ([int]$r.stage_global)}
  $stage=[pscustomobject]@{line=[string]$s.stage_completion_line;relative_index=[int]$s.stage_completion_window_index;begin_line_index=[int]$r.bound.begin_line_index}
  $file=('stage_{0:D3}.txt' -f ($j+1));$next=('stage_{0:D3}.txt' -f ($j+2));Need ($s.stage_file -ceq $file) ($label+' stage file order differs')
  $stageLines=@([IO.File]::ReadAllLines((Join-Path $runDir $file)))
  $expectedStage=@(('set "WCircles" '+$worldText),('set "PCircles" '+$propText),('alias "'+$alias+'"'),('bind F1 exec "'+$rel+'/'+$next+'"'))
  Need (($stageLines -join "`n") -ceq ($expectedStage -join "`n")) ($label+' actual F1 script modifies other values/prerequisites or differs from selected bools')
  $captured=Check-Capture $label $id ([string]$s.state) $s.capture $r $stage $sequence
  Need ([int]$captured.present -gt [int]$previous.present) ($label+' raw present does not advance')
  $previous=$captured;$lastState=$s
 }
 Need (@(Get-ChildItem -LiteralPath $runDir -File -Filter 'stage_*.txt').Count -eq 6) 'successful path has extra/missing variable-write stages'
 $final=$script:manifest.preflight.final_circle_restore
 Need ($null -ne $final -and $final.status -ceq 'observed_captured_terminal_restore' -and $final.site_id -ceq $expectedIds[1] -and $final.state -ceq 'restore' -and
       $null -ne $final.writes_after_terminal_capture -and [int]$final.writes_after_terminal_capture -eq 0 -and @($script:manifest.preflight.final_restore_mismatches).Count -eq 0) 'no complete captured final original-value restoration'
 if($null -ne $final -and $null -ne $lastState){
  Need ($final.stage_file -ceq $lastState.stage_file -and $final.stage_completion_line -ceq $lastState.stage_completion_line -and [int]$final.stage_completion_window_index -eq [int]$lastState.stage_completion_window_index -and
        (ConvertTo-Json $final.log_window -Depth 5 -Compress) -ceq (ConvertTo-Json $lastState.log_window -Depth 5 -Compress) -and
        (ConvertTo-Json $final.capture -Depth 12 -Compress) -ceq (ConvertTo-Json $lastState.capture -Depth 12 -Compress) -and [int]$final.capture.frames[0].sequence -eq 7) 'final cleanup did not adopt actual seventh captured restore transaction'
  $null=Check-CircleReadbacks 'final original-value restore' $final.log_window @($final.alias_readbacks) $false $false ([int]$final.stage_completion_window_index) ([string]$final.stage_completion_line) ([string]$script:plan.controls[1].alias)
 }
 # Check the whole actual player history, including rows omitted from acceptance metadata.
 $origin=$null;$previousN=-1L;$engineSeen=$false
 for($i=$script:playerOrigin;$i -le [int]$previous.ack_global;$i++){
  $line=$script:logLines[$i]
  if($i -gt $close){Need ($line -notmatch '^\[debug-ui\].*visible=1 ') 'debug console reopened after observed close'}
  if($line.StartsWith('[motion] ')){
   $m=Read-PlayerMotionLine $line;if($null -eq $origin){$origin=$m};$dx=$m.x-$origin.x;$dz=$m.z-$origin.z
   Need ($m.n -gt $previousN -and $m.speed -ge 0 -and $m.speed -le 1.0 -and [Math]::Sqrt($dx*$dx+$dz*$dz) -le 1.0) 'actual full player history violated sample/gross speed/planar bounds'
   if($engineSeen){Need ($m.engine -eq 2) 'actual player left engine2 after acceptance'}
   if($m.engine -eq 2){$engineSeen=$true};$previousN=$m.n
  }elseif($line.StartsWith('[startline] ')){
   $p=Read-PlayerPhysicsLine $line;Need ($p.id -eq 0 -and $p.type -eq 0 -and [Math]::Sqrt($p.vx*$p.vx+$p.vy*$p.vy+$p.vz*$p.vz) -le 1.0) 'actual full physics history is not bounded selected player'
   if($engineSeen){Check-PhysicsHeld 'full player history' $p}
  }
 }
 Need ($engineSeen -and $null -ne $origin) 'no actual accepted player motion/engine2 history'
 Need ($script:manifest.visual_review -match 'Root' -and $script:manifest.visual_review -match 'no inventory') 'missing Root pixel-review boundary'
}catch{Need $false ('strict raw evidence validation: '+$_.Exception.Message)}
$detail='machine evidence: two bools, six states, seven same-run frames, canonical PID/image/start, indexed F1/F2/raw motion/physics/ACK/CSV; Root visual review required; no inventory credit.'
@{Pass=($script:fail.Count -eq 0);Detail=$(if($script:fail.Count){$script:fail -join '; '}else{$detail})}
