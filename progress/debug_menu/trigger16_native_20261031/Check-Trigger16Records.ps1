[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$RunDir)
$ErrorActionPreference='Stop'
$run=[IO.Path]::GetFullPath($RunDir)
$package='D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/trigger16_prepare_20261031_v3'
$scope=Get-Content -Raw (Join-Path $package 'SCOPE.json')|ConvertFrom-Json
function Need([bool]$Pass,[string]$Message){if(!$Pass){throw $Message}}
function ConvertTo-TriggerExpectedText([object]$Control,[object]$Value){
    if($Control.type -eq 'bool'){
        if($Value -is [bool]){if($Value){return 'TRUE'};return 'FALSE'}
        if([string]$Value -cin @('TRUE','FALSE')){return [string]$Value}
        throw ('invalid Boolean receipt '+$Control.alias)
    }
    if($Control.type -eq 'i32'){
        $n=[int]0;$text=[Convert]::ToString($Value,[cultureinfo]::InvariantCulture)
        if(![int]::TryParse($text,[Globalization.NumberStyles]::Integer,[cultureinfo]::InvariantCulture,[ref]$n) -or $n -lt [int]$Control.min_value -or $n -gt [int]$Control.max_value){throw ('invalid i32 receipt '+$Control.alias)}
        return $n.ToString([cultureinfo]::InvariantCulture)
    }
    if($Control.type -eq 'f32'){
        $n=[single]0;$text=[Convert]::ToString($Value,[cultureinfo]::InvariantCulture)
        if(![single]::TryParse($text,[Globalization.NumberStyles]::Float,[cultureinfo]::InvariantCulture,[ref]$n) -or [single]::IsNaN($n) -or [single]::IsInfinity($n)){throw ('invalid f32 receipt '+$Control.alias)}
        if($n -lt [single]$Control.ui.min -or $n -gt [single]$Control.ui.max){throw ('out-of-range f32 receipt '+$Control.alias)}
        return $n.ToString('R',[cultureinfo]::InvariantCulture)
    }
    throw ('unknown typed receipt '+$Control.alias)
}
function Get-PhaseName([object]$Control,[string]$State){
    $family=if($Control.id -like 'BrnGameState::TriggerQueryManagerDebugComponent::*'){'trigger_regions'}elseif($Control.id -like 'BrnWorld::TriggerEntityModuleDebugComponent::*'){'trigger_entities'}else{throw ('unknown trigger family '+$Control.id)}
    return ($family+'_'+$Control.alias+'_'+$State)
}
$files=@{
    result=Join-Path $run 'driver-result.json';capture=Join-Path $run 'CAPTURE_AUDIT.json';phase=Join-Path $run 'PHASE_DONE_REQUEST.json'
    terminal=Join-Path $run 'flow-terminal.json';save=Join-Path $run 'CURRENT_SAVE_LOAD_GATE.json';concurrent_pre=Join-Path $run 'CONCURRENT_GAME_PRE.json'
    concurrent_final=Join-Path $run 'CONCURRENT_GAME_FINAL.json';concurrent_runtime=Join-Path $run 'CONCURRENT_GAME_RUNTIME.jsonl'
    baseline=Join-Path $run 'NATURAL_BASELINE.json';game_log=Join-Path $run 'flow\BrnGame.log';marks=Join-Path $run 'flow\marks.txt';flow_console=Join-Path $run 'flow_run.console.log'
}
foreach($path in $files.Values){Need (Test-Path -LiteralPath $path -PathType Leaf) ('missing receipt: '+$path)}
$r=Get-Content -Raw $files.result|ConvertFrom-Json;$c=Get-Content -Raw $files.capture|ConvertFrom-Json;$p=Get-Content -Raw $files.phase|ConvertFrom-Json
$f=Get-Content -Raw $files.terminal|ConvertFrom-Json;$g=Get-Content -Raw $files.save|ConvertFrom-Json;$b=Get-Content -Raw $files.baseline|ConvertFrom-Json
$pre=Get-Content -Raw $files.concurrent_pre|ConvertFrom-Json;$post=Get-Content -Raw $files.concurrent_final|ConvertFrom-Json
$runtime=@(Get-Content -LiteralPath $files.concurrent_runtime|ForEach-Object{$_|ConvertFrom-Json});$log=@(Get-Content -LiteralPath $files.game_log);$marks=Get-Content -Raw $files.marks;$flowConsole=Get-Content -Raw $files.flow_console
Need ($scope.control_count -eq 16 -and $scope.controls.Count -eq 16) 'scope is not exactly16 controls'
Need ($r.status -ceq 'machine_complete_awaiting_independent_pixels') 'driver did not finish machine-only collection'
Need ($r.slot -eq 62206 -and $r.selected_controls -eq 16 -and $r.completed_target_count -eq 16 -and @($r.skipped_controls).Count -eq 0 -and @($r.target_results).Count -eq 16) 'wrong slot/count or one or more targets skipped'
Need ($r.terminal_restore_verified -eq $true -and $r.site_credit -eq 0 -and $r.exe_sha256 -ceq $scope.candidate.exe_sha256) 'terminal restore, zero-credit or executable pin failed'
Need ($marks -match 'asserts=0 phase=DRIVING') 'marks do not prove DRIVING with zero asserts'
Need ($flowConsole -match 'BRN_JUMP_DUMP=1') 'flow output does not show BRN_JUMP_DUMP=1'
Need ($g.pass -eq $true -and $g.normal_written -eq $false -and $g.live_profile_read_or_written -eq $false) 'latest private fixture/current-save gate failed'
Need ($c.pass -eq $true -and $c.frame_count -eq 51 -and $c.max_raw_frames -eq 52 -and @($c.frames).Count -eq 51 -and @($r.frames).Count -eq 51 -and $r.planned_max_frames -eq 51) 'capture audit is not the exact bounded 51/52 plan'
$frameSequences=@($r.frames|ForEach-Object{[int]$_.sequence}|Sort-Object -Unique)
Need ($frameSequences.Count -eq 51 -and $frameSequences[0] -eq 1 -and $frameSequences[-1] -eq 51) 'raw frame sequences are not unique and contiguous'
Need (@($r.frames|Where-Object {$_.width -ne 1280 -or $_.height -ne 720 -or $_.slot -ne 62206 -or $_.pid -ne $r.process_id}).Count -eq 0) 'frame dimensions, PID or slot mismatch'
Need ($p.witness_sha256 -ceq (Get-FileHash $files.result -Algorithm SHA256).Hash.ToLowerInvariant()) 'PhaseDone witness hash differs from result'
. (Join-Path $package 'PhaseTime.ps1')
$phaseTicks=Get-ShadowPhaseStartUtcTicks -Value $p.start_utc
$clockPass=Test-ShadowOwnedStartTicksMatch -PhaseDoneStartUtc $p.start_utc -FlowOwnedStartUtc $f.flow_status.owned_start_utc -DriverStartTicks $r.process_start_ticks
Need ($clockPass -eq $true) 'PhaseDone, flow owned_start_utc and driver process_start_ticks differ'
$event='Local\BurnoutPC_HarnessPhaseDone_{0}_{1}_{2}' -f $p.process_id,$p.slot,$phaseTicks
Need ($r.process_id -eq $p.process_id -and $r.process_path -ieq $p.image -and [string]$r.process_start_ticks -ceq [string]$phaseTicks) 'driver and exact PhaseDone owner differ'
Need ($p.status -ceq 'exact_owned_phase_completion_stop_requested' -and $p.event_set -eq $true -and $p.slot -eq 62206 -and $p.event_name -ceq $event) 'PhaseDone event is not the exact owned PID/slot/start-time event'
Need ($f.flow_status.owned_pid -eq $r.process_id -and $f.flow_status.owned_image -ieq $r.process_path -and $f.flow_status.phase_collection_stop_requested -eq $true -and $f.flow_status.owned_cleanup_complete -eq $true -and $f.flow_status.success -eq $true) 'flow terminal lacks actual phase_collection_stop_requested ownership/cleanup'
Need ($pre.pass -eq $true -and $post.pass -eq $true -and $runtime.Count -gt 0 -and $runtime.Count -eq $r.concurrent_sample_count) 'concurrent identity/count receipts failed'
foreach($sample in $runtime){
    Need ($sample.pass -eq $true -and $sample.owned_pid_excluded -eq $r.process_id -and $sample.observed_other_game_count -le 1 -and $sample.exact_identity_checked -eq $true) 'runtime process sample is not attributable to this PID or exceeds the one-peer limit'
    if($sample.observed_other_game_count -eq 1){$other=$sample.observed_other_games[0];$auth=$sample.authorized_concurrent_game;Need ($null -ne $auth -and $other.process_id -eq $auth.process_id -and $other.image_path -ieq $auth.image_path -and $other.start_ticks -ceq $auth.start_ticks) 'runtime other game differs from the authorized private Root peer'}
}
$baselineValues=$b.values
$f32Base=@('TQ10','TQ11')
foreach($control in $scope.controls){
    $baseProperty=$baselineValues.PSObject.Properties[$control.alias]
    Need ($null -ne $baseProperty) ('missing captured baseline '+$control.alias)
    $baseText=ConvertTo-TriggerExpectedText $control $baseProperty.Value
    if($control.type -eq 'f32'){
        $exact=$b.exact_f32_baselines.PSObject.Properties[$control.alias]
        Need ($f32Base -contains $control.alias -and $null -ne $exact -and $exact.Value.kind -ceq 'published_constructor_source_default' -and $exact.Value.finite -eq $true -and $exact.Value.value -ceq $baseText) ('f32 baseline lacks exact constructor/no-override provenance '+$control.alias)
    }
    $target=@($r.target_results|Where-Object {$_.id -ceq $control.id -and $_.alias -ceq $control.alias})
    Need ($target.Count -eq 1 -and $target[0].restore_verified -eq $true -and @($target[0].phases).Count -eq 3) ('incomplete target receipt '+$control.alias)
    foreach($state in @('positive','negative','restore')){
        $stateRecord=@($target[0].phases|Where-Object {$_.state -ceq $state})
        Need ($stateRecord.Count -eq 1) ('missing '+$control.alias+' '+$state+' target phase')
        $want=if($state -eq 'restore'){$baseText}else{ConvertTo-TriggerExpectedText $control $control.$state}
        Need ((ConvertTo-TriggerExpectedText $control $stateRecord[0].value) -ceq $want) ('requested typed value mismatch '+$control.alias+' '+$state)
        $proof=@($stateRecord[0].raw_alias_readbacks|Where-Object {$_.alias -ceq $control.alias -and $_.path -ceq $control.lookup_path})
        Need ($proof.Count -eq 1 -and (ConvertTo-TriggerExpectedText $control $proof[0].value) -ceq $want) ('full-path typed readback mismatch '+$control.alias+' '+$state)
        if($control.type -ceq 'i32' -and $null -ne $control.enum_options -and @($control.enum_options).Count -gt 0){Need ([string]$proof[0].display_value -ceq [string]$control.enum_options[[int]$want]) ('native enum display label differs from pinned option index '+$control.alias+' '+$state)}
        foreach($override in @($control.context_overrides)){
            $ctxControl=@($scope.controls|Where-Object {$_.alias -ceq $override.alias});Need ($ctxControl.Count -eq 1) ('unknown context alias '+$override.alias)
            $ctxBase=$baselineValues.PSObject.Properties[$override.alias];Need ($null -ne $ctxBase) ('missing captured context baseline '+$override.alias)
            $ctxWant=if($state -eq 'restore'){ConvertTo-TriggerExpectedText $ctxControl[0] $ctxBase.Value}else{ConvertTo-TriggerExpectedText $ctxControl[0] $override.value}
            $ctxProof=@($stateRecord[0].raw_alias_readbacks|Where-Object {$_.alias -ceq $override.alias -and $_.path -ceq $ctxControl[0].lookup_path})
            Need ($ctxProof.Count -eq 1 -and (ConvertTo-TriggerExpectedText $ctxControl[0] $ctxProof[0].value) -ceq $ctxWant) ('typed context readback mismatch '+$override.alias+' in '+$control.alias+' '+$state)
            if($ctxControl[0].type -ceq 'i32' -and $null -ne $ctxControl[0].enum_options -and @($ctxControl[0].enum_options).Count -gt 0){Need ([string]$ctxProof[0].display_value -ceq [string]$ctxControl[0].enum_options[[int]$ctxWant]) ('native enum context label differs from pinned option index '+$override.alias)}
        }
        $phaseName=Get-PhaseName $control $state
        $phaseRow=@($r.phases|Where-Object {$_.phase -ceq $phaseName});$frame=@($r.frames|Where-Object {$_.phase -ceq $phaseName})
        Need ($phaseRow.Count -eq 1 -and $frame.Count -eq 1 -and $frame[0].pid -eq $r.process_id -and $frame[0].slot -eq 62206) ('phase/frame owner missing '+$phaseName)
        Need ($stateRecord[0].frame_sequence -eq $frame[0].sequence -and $stateRecord[0].frame_sha256 -ceq $frame[0].sha256) ('target result and frame audit differ '+$phaseName)
    }
}
Need (@($r.frames|Where-Object phase -ceq 'natural_baseline').Count -eq 1 -and @($r.frames|Where-Object phase -ceq 'terminal_restore').Count -eq 1 -and @($r.frames|Where-Object phase -ceq 'post_restore_readback').Count -eq 1) 'fixed baseline/terminal/post-restore frames missing'
foreach($phaseRecord in $r.phases){foreach($command in @($phaseRecord.commands)){Need ([string]$command -notmatch '(?i)^\s*End\s*$') 'unexpected End command'}}
$jumpRows=@($log|Where-Object {$_ -match '^\[jump-dump\]'})
$report=[ordered]@{
    pass=$true
    classification='machine_receipts_only_visual_and_native_behavior_review_required'
    candidate_exe_sha256=$r.exe_sha256
    process_id=$r.process_id
    process_path=$r.process_path
    process_start_ticks=$r.process_start_ticks
    target_ids=@($scope.controls.id)
    frame_count=$c.frame_count
    terminal_restore_verified=$r.terminal_restore_verified
    site_credit=0
    behavior_credit=0
    per_id_status=@($scope.controls|ForEach-Object {@{id=$_.id;alias=$_.alias;status='pending';reason='native pixel/consumer scene witness still required'}})
    jump_dump_context=[ordered]@{line_count=$jumpRows.Count;target_id=355882;target_index=4413;target_listed='unknown';role='load-time geometry hints only; no per-phase producer evidence'}
    evidence_limits=@('Typed values and exact full paths establish field writes only.','TQ02/TQ03 readbacks display option labels; reported s32 values are decoded from the pinned table and retain the raw label.','BRN_JUMP_DUMP runs at TriggerData load and lists only the first24 jump regions without CgsID; no current-phase producer is attached.','Absent pixels, no camera hit, changed fields and unchanged views are insufficient; they do not show original no-op behavior.')
}
$out=Join-Path $PSScriptRoot 'TRIGGER16_MACHINE_RECORD_CHECK.json'
if(Test-Path -LiteralPath $out){throw 'refusing to overwrite TRIGGER16_MACHINE_RECORD_CHECK.json'}
$report|ConvertTo-Json -Depth 12|Set-Content -LiteralPath $out -Encoding utf8
[pscustomobject]$report
