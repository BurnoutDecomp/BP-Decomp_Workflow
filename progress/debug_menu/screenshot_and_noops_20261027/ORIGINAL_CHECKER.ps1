param([Parameter(Mandatory=$true)][hashtable]$Context)
$ErrorActionPreference='Stop'
. (Join-Path $Context.Case.CaseDir 'ScreenshotEvidence.ps1')
. (Join-Path $Context.Case.CaseDir 'ScreenshotFileEvidence.ps1')
. (Join-Path $Context.Case.CaseDir 'CandidateArtifactGuard.ps1')
$script:fail=[Collections.Generic.List[string]]::new()
function Need([bool]$ok,[string]$message){if(!$ok){$script:fail.Add($message)}}
. (Join-Path $Context.Case.CaseDir 'checker.primitives.ps1')
function Assert-ScreenshotAliasContract([object]$Plan){
 $contract=$Plan.alias_contract
 if($null -eq $contract -or $contract.status -cne 'author_static_source_contract_confirmed' -or
    [int]$contract.alias_count -ne 4 -or [int]$contract.reported_maximum_bytes -ne 10 -or
    [int]$contract.reject_if_byte_length_greater_or_equal -ne 10 -or [int]$contract.maximum_legal_ascii_bytes -ne 9){throw 'Pinned alias source contract is missing or inconsistent.'}
 $controls=@($Plan.alias_controls)
 if($controls.Count -ne 4 -or (@($controls.alias) -join '|') -cne 'SSReq|SSOvly|WCircles|PCircles'){throw 'Exactly four source-derived aliases are required.'}
 foreach($control in $controls){
  $name=[string]$control.alias;$bytes=[Text.Encoding]::UTF8.GetByteCount($name)
  if($name -cnotmatch '^[A-Za-z0-9_]+$' -or $bytes -lt 1 -or $bytes -ge 10 -or [string]::IsNullOrEmpty([string]$control.path)){throw 'Alias must be nonempty ASCII, shorter than the source rejection threshold of 10 bytes, and have an exact registered path.'}
 }
 $sources=@($contract.source_evidence.PSObject.Properties)
 if($sources.Count -ne 4){throw 'All four alias/path source blobs must be pinned.'}
 foreach($source in $sources){
  $row=$Plan.candidate_source_files.PSObject.Properties[[string]$source.Value.path]
  if($null -eq $row -or [string]$row.Value.raw_sha256 -cne [string]$source.Value.sha256){throw 'Alias source evidence does not equal the target Git snapshot.'}
 }
}
function Check-ScreenshotReadbacks([string]$scope,[object]$window,[object[]]$rows,[object]$Expected,[int]$stageIndex=-1,[string]$stageLine='',[string]$ackAlias=''){
 $bound=Get-BoundLogWindow $script:proofBytes $window;$lines=@($bound.lines)
 Need ($rows.Count -eq 4) ($scope+' must contain exactly the four named F2 aliases')
 if(![string]::IsNullOrWhiteSpace($ackAlias) -and $stageIndex -lt 0){throw ($scope+' has no nonnegative F1 ACK index.')}
 if($stageIndex -ge 0){
  Need ($stageIndex -lt $lines.Count -and $lines[$stageIndex] -ceq $stageLine) ($scope+' F1 ACK index differs inside its hashed window')
  for($i=0;$i -lt [Math]::Min($stageIndex,$lines.Count);$i++){Need ($lines[$i] -cne $stageLine) ($scope+' earlier duplicate F1 ACK')}
 }
 $lastValue=-1
 foreach($control in @($script:plan.alias_controls)){
  $alias=[string]$control.alias;$path=[string]$control.path;$label=Get-ExpectedAliasQueryReceipt $alias $path
  $expectedText=[string]$Expected.$alias
  Need ($expectedText -cin @('TRUE','FALSE')) ($scope+' missing expected literal '+$alias)
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

try{
 $caseDir=[string]$Context.Case.CaseDir;$runDir=[string]$Context.RunDir;$script:frameDir=Join-Path $runDir 'frames'
 Need ([IO.Path]::GetFullPath([string]$Context.FrameDir) -ieq [IO.Path]::GetFullPath($script:frameDir)) 'Context frame directory differs from exact retained run frames'
 $script:plan=Read-Json (Join-Path $runDir 'CASE_PLAN.used.json')
 Assert-ScreenshotAliasContract $script:plan
 $script:manifest=Read-Json (Join-Path $runDir 'screenshot-witnesses.json');$script:owner=Read-Json (Join-Path $runDir 'screenshot-owner.json')
 $binding=Read-Json (Join-Path $runDir 'runtime-binding.used.json');$usedSourceBindings=Read-Json (Join-Path $runDir 'CASE_SOURCE_BINDINGS.used.json')
 $artifact=Read-Json (Join-Path $runDir 'HOSTED_ARTIFACT_BINDING.used.json');$stageBinding=Read-Json (Join-Path $runDir 'STAGING.used.json');$review=Read-Json (Join-Path $runDir 'ROOT_PRELAUNCH_REVIEW.used.json')
 $terminal=Read-Json (Join-Path $runDir 'flow/terminal-status.json');$handoff=Read-Json (Join-Path $caseDir 'ROOT_HANDOFF.json')

 # Final run_case Context has Case and RunDir but no Slot. Derive the slot from
 # the actual canonical terminal; cross-check Context only if it supplies one.
 $caseTerminal=Read-Json (Join-Path $runDir 'flow-terminal.json')
 $parsedSlot=0
 if($null -eq $caseTerminal -or ![int]::TryParse([string]$caseTerminal.slot,[ref]$parsedSlot) -or $parsedSlot -lt 1 -or $parsedSlot -gt 65535){throw 'Canonical case terminal lacks a valid selected slot; never cast a missing Context.Slot to zero.'}
 $script:selectedSlot=$parsedSlot
 Need ([int]$caseTerminal.schema -eq 1 -and $caseTerminal.case -ceq [string]$Context.Case.Name -and
       [IO.Path]::GetFullPath([string]$caseTerminal.run_dir) -ieq [IO.Path]::GetFullPath($runDir) -and
       $caseTerminal.flow_invoked -eq $true -and $caseTerminal.success -eq $true -and $null -ne $caseTerminal.flow_exit -and [int]$caseTerminal.flow_exit -eq 0 -and
       $caseTerminal.helper_cleanup_complete -eq $true -and $caseTerminal.profile_restoration_complete -eq $true -and $caseTerminal.post_flow_foreign_game -eq $false -and
       [string]::IsNullOrWhiteSpace([string]$caseTerminal.error) -and
       $caseTerminal.flow_status_sha256 -ceq (Get-FileHash -LiteralPath (Join-Path $runDir 'flow/terminal-status.json') -Algorithm SHA256).Hash.ToLowerInvariant()) 'canonical terminal case/run/slot/status hash/cleanup differs'
 Need ([int]$Context.Case.Binding.slot -eq $script:selectedSlot -and [int]$stageBinding.slot -eq $script:selectedSlot) 'Context.Case.Binding/Stage slot differs from canonical final terminal'
 if($Context.ContainsKey('Slot')){Need ($null -ne $Context.Slot -and [string]$Context.Slot -ceq [string]$script:selectedSlot) 'optional Context.Slot disagrees with canonical terminal'}

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
 $expectedIds=@('BrnGraphics::DebugComponent::OnActivate#0029','BrnGraphics::DebugComponent::OnActivate#0030')
 Need (@($script:plan.controls).Count -eq 2 -and (@($script:plan.selected_site_ids) -join '|') -ceq ($expectedIds -join '|') -and
       (@($script:manifest.selected_site_ids) -join '|') -ceq ($expectedIds -join '|') -and [int]$script:manifest.site_count -eq 2 -and [int]$script:manifest.selected_site_count -eq 2) 'case/manifest is not exactly the two selected constructor bools'
 Need ($script:manifest.status -ceq 'machine_evidence_awaiting_root_visual_review' -and @($script:manifest.deferred_sites).Count -eq 0 -and [int]$script:manifest.planned_state_count -eq 6 -and
       [int]$script:manifest.site_state_count -eq 6 -and [int]$script:manifest.frame_count -eq 10 -and @($script:manifest.frames).Count -eq 10) 'full machine evidence requires six states/ten frames without deferred sites'
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
       $script:owner.exe_sha256 -ceq $binding.execution_exe_sha256 -and [int]$script:owner.pid -gt 0 -and [int]$script:owner.slot -eq [int]$script:selectedSlot -and
       [int]$script:manifest.slot -eq [int]$script:selectedSlot -and [int]$binding.slot -eq [int]$script:selectedSlot) 'helper differs from exact private candidate image/hash/PID/slot'
 $ownerTicks=Utc-Ticks $script:owner.start_utc
 Need ([string]$script:owner.start_utc_ticks -ceq $ownerTicks.ToString() -and [int]$handoff.pid -eq [int]$script:owner.pid -and [IO.Path]::GetFullPath([string]$handoff.image) -ieq $expectedImage -and
       [int]$handoff.slot -eq [int]$script:selectedSlot -and (Utc-Ticks $handoff.start_utc) -eq $ownerTicks -and [int]$handoff.canonical_launcher_pid -gt 0) 'helper PID/image/start differs from canonical driver handoff'
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
 $helperText=Text-File (Join-Path $runDir 'screenshot-keys.log')
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
 Need ($script:csvRows.Count -eq 10 -and @($script:csvRows.present|Select-Object -Unique).Count -eq 10) 'raw CSV is not exactly ten unique presents'
 Need (@($script:manifest.frames.name|Select-Object -Unique).Count -eq 10 -and @($script:logLines|Where-Object{$_ -match '^\[frame-request\] '}).Count -eq 10 -and @(Get-ChildItem -LiteralPath $script:frameDir -File -Filter '*.bmp').Count -eq 10) 'extra/missing/duplicate named captures'
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
       [int]$natural.pid -eq [int]$script:owner.pid -and [int]$natural.slot -eq [int]$script:selectedSlot -and $natural.root_visual_review -ceq 'pending_after_run') 'natural baseline not this candidate/owned run or claims prior pixel approval'
 Need ($null -ne $natural.setup_control_write_commands -and [int]$natural.setup_control_write_commands -eq 0 -and $null -ne $script:manifest.preflight.setup_control_write_commands -and
       [int]$script:manifest.preflight.setup_control_write_commands -eq 0 -and $script:manifest.preflight.initial_alias_baselines.WCircles -eq $false -and
       $script:manifest.preflight.initial_alias_baselines.PCircles -eq $false -and $natural.initial_alias_baselines.WCircles -eq $false -and
       $natural.initial_alias_baselines.PCircles -eq $false -and $null -eq $script:manifest.preflight.root_baseline_pixel_witness) 'natural baseline written/not both original false/inherited pixels'
 foreach($name in @('SSReq','SSOvly','WCircles','PCircles')){Need ($null -ne $script:manifest.preflight.initial_alias_baselines.$name -and $script:manifest.preflight.initial_alias_baselines.$name -eq $false -and $null -ne $natural.initial_alias_baselines.$name -and $natural.initial_alias_baselines.$name -eq $false) ('Actual zero-write baseline is not FALSE: '+$name)}
 $close=[int]$natural.console_close_line_index;Check-IndexedRaw 'natural baseline console close' $natural.console_close_line_index ([string]$natural.console_close_line)
 Need ($close -gt $exitAt -and $close -gt [int]$attach.line_index) 'initial console close predates actual startup/player attach'
 Need ([string]$natural.console_close_line -match '^\[debug-ui\] event=0 visible=0 .* key=0$' -and $script:manifest.preflight.console_close_receipt -ceq $natural.console_close_line -and
       [int]$script:manifest.preflight.console_close_line_index -eq $close) 'actual console close receipt differs'
 $startup=Check-Held 'startup' $script:manifest.preflight.player_startup_acceptance ($script:playerOrigin-1) $close
 $setupStage=[pscustomobject]@{line=[string]$natural.stage_complete_line;relative_index=[int]$natural.stage_completion_window_index;begin_line_index=[int]$natural.stage_window_begin_line_index}
 $setupGlobal=$setupStage.begin_line_index+$setupStage.relative_index
 $setupControls=@($script:plan.alias_controls);$setupReceipts=@($script:manifest.preflight.setup_input_receipts.alias_registrations)
 Need ($setupControls.Count -eq 4 -and $setupReceipts.Count -eq 4) 'setup lacks both planned alias-query receipts'
 $enterIndex=[int]$script:manifest.preflight.setup_input_receipts.enter_line_index
 $setupStartIndex=[int]$script:manifest.preflight.setup_input_receipts.setup_start_line_index
 Need ($setupStartIndex -ge 0 -and $enterIndex -ge $setupStartIndex -and $setupStartIndex -eq $setupStage.begin_line_index) 'fresh setup-start/Enter indices are absent or inconsistent'
 if($setupStartIndex -ge 0){
  foreach($control in $setupControls){
   $staleReceipt=Get-ExpectedAliasQueryReceipt ([string]$control.alias) ([string]$control.path)
   for($i=0;$i -lt [Math]::Min($setupStartIndex,$script:logLines.Count);$i++){Need ($script:logLines[$i] -cne $staleReceipt) ('stale alias-query receipt precedes setup: '+[string]$control.alias)}
  }
 }
 if($setupControls.Count -eq 4 -and $setupReceipts.Count -eq 4){
  for($i=0;$i -lt 4;$i++){
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
 Need ($setupStage.line -ceq $lastAliasReceipt -and $setupReceipts.Count -eq 4 -and $setupGlobal -eq [int]$setupReceipts[-1].line_index -and $setupGlobal -lt $close) 'natural setup completion is not the final exact alias-query receipt before close'
 $setupLines=@([IO.File]::ReadAllLines((Join-Path $runDir 'setup.txt')));$trigger=Read-Json (Join-Path $runDir 'ROOT_TRIGGER_CONTEXT.json');$rel=[string]$trigger.run_relative_path
 $expectedSetup=[Collections.Generic.List[string]]::new()
 $expectedSetup.Add('component "Renderer/RendererModule"')
 foreach($control in $setupControls){$expectedSetup.Add(('alias "'+[string]$control.alias+'" "'+[string]$control.path+'"'))}
 $expectedSetup.Add(('bind F1 exec "'+$rel+'/stage_001.txt"'));$expectedSetup.Add(('bind F2 exec "'+$rel+'/readback.txt"'))
 foreach($control in $setupControls){$expectedSetup.Add(('alias "'+[string]$control.alias+'"'))}
 Need (($setupLines -join "`n") -ceq ($expectedSetup.ToArray() -join "`n")) 'actual exec setup differs from the two aliases derived from their exact target paths plus F1/F2'
 $actualCfg=Join-Path $caseDir 'stage/data/b1.cfg'
 Need ((Get-FileHash -LiteralPath $actualCfg -Algorithm SHA256).Hash -ceq
       (Get-FileHash -LiteralPath (Join-Path $runDir 'setup.txt') -Algorithm SHA256).Hash) 'actual executed private b1.cfg differs from the retained zero-write setup script'
 $actualReadback=@([IO.File]::ReadAllLines((Join-Path $runDir 'readback.txt')));$expectedReadback=[Collections.Generic.List[string]]::new()
 foreach($control in $setupControls){$expectedReadback.Add(('alias "'+[string]$control.alias+'"'));$expectedReadback.Add([string]$control.alias)}
 Need ($actualReadback.Count -eq 8 -and (@($actualReadback|Sort-Object) -join '|') -ceq (@($expectedReadback.ToArray()|Sort-Object) -join '|')) 'retained F2 script differs from the two read-only alias queries'
 $input=$script:manifest.preflight.setup_key_sequence_before_enter;$inputCursor=[int]$input.cursor_line_count;$codes=@()
 $setupInputEndGlobal=[Math]::Max($setupGlobal,$enterIndex)
 Need ($input.command -ceq 'exec b1.cfg' -and $inputCursor -ge 0 -and $inputCursor -lt $setupInputEndGlobal -and $setupInputEndGlobal -lt $close) 'typed setup command/cursor/Enter window invalid'
 for($i=$inputCursor;$i -le $setupInputEndGlobal;$i++){if($script:logLines[$i] -match '^\[debug-ui\].*visible=1 .*key=(\d+)$' -and [int]$Matches[1] -ne 0){$codes+=[int]$Matches[1]}}
 $expectedCodes=@(101,120,101,99,32,98,49,46,99,102,103,10)
 Need (($codes -join ',') -ceq ($expectedCodes -join ',')) 'actual indexed setup key stream differs from exec b1.cfg plus Enter'
 $readback=Check-ScreenshotReadbacks 'initial baseline F2' $script:manifest.preflight.baseline_alias_readback_window @($script:manifest.preflight.baseline_alias_readbacks) @{SSReq='FALSE';SSOvly='FALSE';WCircles='FALSE';PCircles='FALSE'}
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
 Need (@($script:manifest.preflight.engine2_phase_receipts).Count -eq 10 -and @($script:manifest.preflight.held_player_capture_receipts).Count -eq 10 -and @($script:manifest.preflight.held_player_write_receipts).Count -eq 11) 'extra/missing per-phase engine2/held-player receipts'
 $transactions=@($script:manifest.transactions)
 Need ($transactions.Count -eq 11 -and @($script:manifest.capture_transactions).Count -eq 9 -and @($script:manifest.tga_receipts).Count -eq 4) 'transaction, diagnostic bracket, or native TGA count differs'
 Need ($script:plan.case -ceq 'debug_menu_screenshot_two_control' -and [int]$script:plan.schedule.hard_frame_cap -eq 10 -and [int]$script:plan.schedule.max_seconds -eq 420 -and
       [int]$script:plan.schedule.vsync -eq 1 -and @($script:plan.transaction_sequence).Count -eq 11 -and @($script:plan.capture_sequence).Count -eq 10) 'bounded screenshot schedule differs'
 $allCaptures=@{}
 $allCaptures[1]=$natural.capture
 $transactionChecks=@{}
 $previousTransactionEnd=[int]$baselineWindow.end_line_index
 $lastAck=[int]$previous.ack_global
 foreach($tx in $transactions){
  $number=[int]$tx.number
  Need ($number -ge 1 -and $number -le 11 -and $number -eq $transactionChecks.Count+1) 'transaction number is missing/duplicate/out of order'
  if($number -lt 1 -or $number -gt 11){throw 'Transaction index outside bounded schedule.'}
  $planned=$script:plan.transaction_sequence[$number-1];$label=[string]$planned.label
  Need ($tx.label -ceq $label -and (@($tx.commands) -join '|') -ceq (@($planned.commands) -join '|') -and $tx.ack_alias -ceq 'SSOvly') ($label+' actual stage commands/alias differ')
  Need ((ConvertTo-Json $tx.expected -Depth 5 -Compress) -ceq (ConvertTo-Json $planned.expected -Depth 5 -Compress)) ($label+' expected state changed')
  $expectedAck=Get-ExpectedAliasQueryReceipt 'SSOvly' 'Renderer/RendererModule/Capture overlays in screenshot'
  Need ([string]$tx.stage_completion_line -ceq $expectedAck -and $null -ne $tx.stage_completion_window_index) ($label+' exact source-derived ACK/index missing')
  $r=Check-ScreenshotReadbacks $label $tx.log_window @($tx.alias_readbacks) $planned.expected ([int]$tx.stage_completion_window_index) ([string]$tx.stage_completion_line) 'SSOvly'
  Need ([int]$r.bound.begin_line_index -ge $previousTransactionEnd -and [int]$r.stage_global -gt $lastAck -and
        [int]$tx.stage_completion_index -eq [int]$r.stage_global -and [int]$tx.f2_cursor -gt [int]$r.stage_global -and
        [int]$tx.f2_cursor -le [int]$r.last_value_global) ($label+' stage/F2/prefix order differs')
  $writeRows=@($script:manifest.preflight.held_player_write_receipts|Where-Object{$_.label -ceq $label})
  Need ($writeRows.Count -eq 1) ($label+' lacks unique pre-write held-player receipt')
  if($writeRows.Count -eq 1){$null=Check-Held ($label+' before write') $writeRows[0].player_acceptance $lastAck ([int]$r.stage_global)}
  $file=('stage_{0:D3}.txt' -f $number);$next=('stage_{0:D3}.txt' -f ($number+1))
  Need ($tx.stage_file -ceq $file) ($label+' stage path/order differs')
  $stageLines=@([IO.File]::ReadAllLines((Join-Path $runDir $file)))
  $expectedStage=@($planned.commands)+@('alias "SSOvly"',('bind F1 exec "'+$rel+'/'+$next+'"'))
  Need (($stageLines -join "`n") -ceq ($expectedStage -join "`n")) ($label+' actual executable script changes other values or differs')
  Need (@($stageLines|Where-Object{[Text.Encoding]::ASCII.GetByteCount($_) -gt 255 -or $_ -match '[^\x20-\x7e]'}).Count -eq 0) ($label+' native script buffer bounds exceeded')
  Need ((@($tx.capture_sequences) -join ',') -ceq (@($planned.captures) -join ',')) ($label+' phase capture sequence differs')
  $phase=[pscustomobject]@{line=[string]$tx.stage_completion_line;relative_index=[int]$tx.stage_completion_window_index;begin_line_index=[int]$r.bound.begin_line_index}
  foreach($sequence in @($planned.captures)){
   $capRows=@($script:manifest.capture_transactions|Where-Object{[int]$_.transaction -eq $number -and [int]$_.capture.frames[0].sequence -eq [int]$sequence})
   Need ($capRows.Count -eq 1) ($label+' unique capture transaction join missing')
   if($capRows.Count -ne 1){throw 'Missing exact capture-to-transaction join.'}
   $capture=$capRows[0].capture;$capPlan=$script:plan.capture_sequence[[int]$sequence-1]
   Need ([int]$capPlan.sequence -eq [int]$sequence -and [int]$capPlan.transaction -eq $number -and $capRows[0].label -ceq $capPlan.label -and
         $capRows[0].site_id -ceq $capPlan.site_id -and $capRows[0].state -ceq $capPlan.state) ($label+' capture label/site/state/transaction differs')
   $checked=Check-Capture ([string]$capPlan.label) ([string]$capPlan.site_id) ([string]$capPlan.state) $capture $r $phase ([int]$sequence)
   Need ([int]$checked.ack_global -gt $lastAck -and [int]$checked.present -gt [int]$previous.present) ($label+' diagnostic ACK/present did not advance')
   $lastAck=[int]$checked.ack_global;$previous=$checked;$allCaptures[[int]$sequence]=$capture
  }
  $native=$tx.native
  if($planned.native -ceq 'missing_directory'){
   Need ($number -eq 2 -and $null -ne $native -and $native.kind -ceq 'missing_directory' -and [int]$native.counter -eq 0 -and
         $native.expected_filename -ceq 'screenshot0_.tga' -and $native.directory_absent_after -eq $true -and $null -eq $native.tga_ack) 'original missing-directory failure proof absent or invented'
   Check-IndexedRaw 'counter-zero original fopen failure' $native.line_index ([string]$native.line)
   Need ($native.line -ceq '[screenshot] open failed: d_\screenshot0_.tga' -and [int]$native.request_cursor -eq [int]$r.bound.begin_line_index -and
         [int]$native.line_index -ge [int]$r.bound.begin_line_index -and [int]$native.line_index -lt [int]$tx.f2_cursor) 'original failure line does not fall in exact scoped request before F2'
  }elseif([string]$planned.native -cmatch '^screenshot([1-4])_\.tga$'){
   $counter=[int]$Matches[1]
   Need ($null -ne $native -and $native.kind -ceq 'native_tga' -and [int]$native.counter -eq $counter -and $native.name -ceq $planned.native -and
         $native.label -ceq $label -and $native.native_relative_path -ceq ('d_/'+$planned.native) -and $native.retained_path -ceq ('native_tga/'+('{0:D2}_{1}.tga' -f $counter,$label)) -and
         [int]$native.bytes -eq 2764818 -and [int]$native.width -eq 1280 -and [int]$native.height -eq 720 -and [int]$native.bits_per_pixel -eq 24 -and [int]$native.image_type -eq 2 -and
         $native.bottom_origin -eq $true -and [int]$native.exclusive_closed_reads -eq 2 -and $null -eq $native.tga_ack -and $native.same_present_as_diagnostic_bmp -eq $false) ($label+' native TGA shape/lifecycle/identity contract differs')
   Need ($native.action_utc -ceq $tx.action_utc -and [long]$native.action_tick -eq [long]$tx.action_tick -and [int]$native.request_cursor -eq [int]$r.bound.begin_line_index -and
         [long]$native.first_closed_read_tick -gt [long]$tx.action_tick -and [long]$native.second_closed_read_tick -gt [long]$native.first_closed_read_tick -and
         (Utc-Ticks $native.first_closed_read_utc) -ge (Utc-Ticks $tx.action_utc) -and (Utc-Ticks $native.second_closed_read_utc) -ge (Utc-Ticks $native.first_closed_read_utc) -and
         [long]$native.mtime_utc_filetime_ticks -ge ([DateTime]::Parse([string]$tx.action_utc).ToUniversalTime().ToFileTimeUtc())) ($label+' native closed-file observation predates scoped action')
   $copyPath=Join-Path $runDir ([string]$native.retained_path);$actual=Read-NativeTga $copyPath
   Need ($actual.sha256 -ceq $native.sha256 -and $actual.bytes -eq [long]$native.bytes) ($label+' retained original native TGA raw hash/bytes/header differs')
   $originalPath=Join-Path (Join-Path $caseDir 'stage/data') ([string]$native.native_relative_path);$original=Read-NativeTga $originalPath
   Need ($original.sha256 -ceq $native.sha256 -and $original.mtime_utc_filetime_ticks -ceq [string]$native.mtime_utc_filetime_ticks) ($label+' native original changed after retained copy')
   $top=@($script:manifest.tga_receipts|Where-Object{[int]$_.counter -eq $counter})
   Need ($top.Count -eq 1 -and (ConvertTo-Json $top[0] -Depth 12 -Compress) -ceq (ConvertTo-Json $native -Depth 12 -Compress)) ($label+' top native receipt differs from exact transaction')
   Need (@($native.roster_before).Count -eq $counter-1 -and @($native.roster_after).Count -eq $counter) ($label+' per-request native roster count differs')
   for($k=0;$k -lt $counter;$k++){
    $earlier=$script:manifest.tga_receipts[$k];$current=$native.roster_after[$k]
    foreach($field in @('name','bytes','sha256','mtime_utc_filetime_ticks')){Need ([string]$current.$field -ceq [string]$earlier.$field) ($label+' after roster differs from independently checked native files '+$field)}
    if($k -lt $counter-1){foreach($field in @('name','bytes','sha256','mtime_utc_filetime_ticks')){Need ([string]$native.roster_before[$k].$field -ceq [string]$earlier.$field) ($label+' prior file changed '+$field)}}
   }
  }else{Need ($null -eq $native) ($label+' invented native action receipt in a no-request phase')}
  $transactionChecks[$number]=[pscustomobject]@{tx=$tx;readback=$r;stage=$phase}
  $previousTransactionEnd=[int]$r.bound.end_line_index
 }
 Need ($allCaptures.Count -eq 10 -and @(Get-ChildItem -LiteralPath $runDir -File -Filter 'stage_*.txt').Count -eq 11) 'complete run has extra/missing frames or control-write stages'
 $errors=@($script:logLines|Where-Object{$_ -match '^\[screenshot\] '})
 Need ($errors.Count -eq 1 -and $errors[0] -ceq '[screenshot] open failed: d_\screenshot0_.tga') 'native failure path changed or an unexpected screenshot producer/lock/write/open failure occurred'
 $directory=Join-Path $caseDir 'stage/data/d_'
 $actualRoster=@(Get-NativeOutputRoster $directory)
 Need ($actualRoster.Count -eq 4 -and @(Get-ChildItem -LiteralPath (Join-Path $runDir 'native_tga') -Force).Count -eq 4) 'extra/missing native originals or retained TGA copies'
 $baselineOutput=$script:manifest.preflight.output_baseline;$created=$script:manifest.preflight.private_directory_creation
 Need ($baselineOutput.absent -eq $true -and $baselineOutput.directory -ceq 'd_' -and @($baselineOutput.native_files).Count -eq 0 -and @($baselineOutput.screenshot_error_lines).Count -eq 0 -and
       [int]$baselineOutput.checked_before_transaction -eq 1) 'native path was not absent at the original untouched baseline'
 Need ($null -ne $created -and [IO.Path]::GetFullPath([string]$created.path) -ieq [IO.Path]::GetFullPath($directory) -and $created.relative_path -ceq 'd_' -and
       [int]$created.after_transaction -eq 2 -and [int]$created.after_capture_sequence -eq 3 -and [int]$created.before_transaction -eq 3 -and @($created.initial_roster).Count -eq 0 -and
       $created.production_mkdir_change -eq $false -and [long]$created.created_tick -gt [long]$transactions[1].native.observed_tick -and
       [long]$created.created_tick -lt [long]$transactions[2].action_tick) 'private test-directory creation did not preserve the original failure before the next request'
 $negative=$script:manifest.preflight.negative_interval
 Need ($null -ne $negative -and [int]$negative.transaction -eq 4 -and (@($negative.capture_sequences) -join ',') -ceq '5,6' -and
       [int]$negative.first_present -eq [int]$allCaptures[5].present -and [int]$negative.last_present -eq [int]$allCaptures[6].present -and
       [int]$negative.last_present-[int]$negative.first_present -ge 2 -and [long]$negative.stopwatch_frequency -gt 0 -and
       ([long]$negative.wait_end_tick-[long]$negative.wait_begin_tick)/[double]$negative.stopwatch_frequency -ge 2.0) 'no-request interval lacks actual bounded wait and advancing original presents'
 Assert-SameNativeRoster @($negative.roster_before) @($negative.roster_after)
 Need (@($negative.roster_before).Count -eq 1 -and [string]$negative.roster_before[0].sha256 -ceq [string]$script:manifest.tga_receipts[0].sha256) 'negative interval did not preserve only the first native TGA'
 foreach($field in @('name','bytes','sha256','mtime_utc_filetime_ticks')){Need ([string]$negative.roster_before[0].$field -ceq [string]$script:manifest.tga_receipts[0].$field) ('negative interval first-file evidence differs '+$field)}
 $sites=@($script:manifest.sites)
 Need ($sites.Count -eq 2 -and (@($sites.site_id) -join '|') -ceq ($expectedIds -join '|')) 'selected screenshot site roster differs'
 $stateToTransaction=@(@(3,4,11),@(6,8,10))
 $stateToCapture=@(@(4,6,10),@(7,8,9))
 for($i=0;$i -lt 2;$i++){
  $site=$sites[$i];$states=@($site.states)
  Need ($site.status -ceq 'machine_evidence_awaiting_root_visual_review' -and $states.Count -eq 3 -and (@($states.state) -join '|') -ceq 'positive|negative|restore') 'site lacks three ordered qualified states'
  for($k=0;$k -lt 3;$k++){
   $row=$states[$k];$txCheck=$transactionChecks[[int]$stateToTransaction[$i][$k]];$tx=$txCheck.tx
   $cap=$allCaptures[[int]$stateToCapture[$i][$k]]
   $requested=if($k -eq 0){'TRUE'}else{'FALSE'}
   Need ($row.stage_file -ceq $tx.stage_file -and $row.stage_completion_line -ceq $tx.stage_completion_line -and [int]$row.stage_completion_window_index -eq [int]$tx.stage_completion_window_index -and
         (ConvertTo-Json $row.alias_readbacks -Depth 8 -Compress) -ceq (ConvertTo-Json $tx.alias_readbacks -Depth 8 -Compress) -and
         (ConvertTo-Json $row.capture -Depth 12 -Compress) -ceq (ConvertTo-Json $cap -Depth 12 -Compress) -and $row.requested -ceq $requested -and $row.baseline -ceq 'FALSE') 'site state does not join exact transaction/readbacks/original capture'
   $null=Get-BoundLogWindow $script:proofBytes $row.log_window
   Need ((ConvertTo-Json $row.log_window -Depth 5 -Compress) -ceq (ConvertTo-Json $tx.log_window -Depth 5 -Compress)) 'site raw window differs from its exact observed transaction'
   foreach($aliasControl in $script:plan.alias_controls){$aliasName=[string]$aliasControl.alias;Need ([string]$row.actual_values.$aliasName -ceq [string]$tx.expected.$aliasName) ('site parsed value differs from exact transaction '+$aliasName)}
   Need ($row.actual -ceq $(if($i -eq 0){'FALSE'}else{$requested})) 'site state ignores consumed request FALSE or overlay readback'
  }
 }
 $final=$script:manifest.preflight.final_screenshot_restore
 Need ($null -ne $final -and $final.status -ceq 'observed_captured_terminal_restore' -and [int]$final.transaction -eq 11 -and [int]$final.capture_sequence -eq 10 -and
       [int]$final.writes_after_terminal_capture -eq 0 -and $final.companion_restored -eq $true -and $final.prop_companion_never_written -eq $true -and
       @($script:manifest.preflight.final_restore_mismatches).Count -eq 0 -and
       (ConvertTo-Json $final.receipt -Depth 14 -Compress) -ceq (ConvertTo-Json $transactions[10] -Depth 14 -Compress)) 'captured terminal original-value restoration missing or fallback mislabelled'
 foreach($name in @('SSReq','SSOvly','WCircles','PCircles')){Need ($null -ne $final.actual_baselines.$name -and $final.actual_baselines.$name -eq $false -and $transactions[10].expected.$name -ceq 'FALSE') ('terminal actual original baseline differs '+$name)}
 Need ($script:manifest.preflight.companion_witness.new_site_credit -eq $false -and [int]$script:manifest.preflight.companion_witness.capture_sequence -eq 2 -and
       $script:manifest.preflight.companion_witness.root_visual_review -ceq 'pending') 'companion was credited or visual review was pre-approved'
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
}catch{Need $false ('strict native screenshot evidence validation: '+$_.Exception.Message)}
$detail='Machine evidence for two screenshot variables, six states, ten owned diagnostic BMPs and four actual native TGAs; full raw F1/F2/held-player/ACK/CSV and canonical slot joins; Root must inspect original pixels before any inventory credit.'
@{Pass=($script:fail.Count -eq 0);Detail=$(if($script:fail.Count){$script:fail -join '; '}else{$detail})}
