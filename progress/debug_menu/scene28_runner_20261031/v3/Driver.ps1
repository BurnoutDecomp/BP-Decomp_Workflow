param([string]$RunDir,[string]$ExpectedSlotExe,[string]$GameLog,[int]$Slot=62190)
$ErrorActionPreference='Stop'
$PackageRoot=$PSScriptRoot
. (Join-Path $PackageRoot 'CurrentSaveProgress.ps1')
. (Join-Path $PackageRoot 'Capture.ps1')
. (Join-Path $PackageRoot 'Driver.Helpers.ps1')
$plan=Get-Content -Raw -LiteralPath (Join-Path $PackageRoot 'SCOPE.json')|ConvertFrom-Json
$stage=Get-Content -Raw -LiteralPath (Join-Path $PackageRoot 'STAGING.json')|ConvertFrom-Json
$ExpectedSha256=$plan.candidate.exe_sha256
$controls=@($plan.controls)+@($plan.context_aliases)
$logPath=Join-Path $RunDir 'driver.log'
$keys=@{}
$owner=$null
$frameEvent=$null
$script:sequence=0
$started=[DateTime]::UtcNow
$deadline=$started.AddSeconds(1450)
$script:nextCim=[DateTime]::MinValue
$script:consoleVisible=$null
$script:logAccepted=$false
$script:writesStarted=$false
$script:cleanupMode=$false
$script:terminalRestoreVerified=$false
$script:phaseHash=$null
$frameRows=[Collections.Generic.List[object]]::new()
$phaseRows=[Collections.Generic.List[object]]::new()
$targetRows=[Collections.Generic.List[object]]::new()
$script:gameLines=[Collections.Generic.List[string]]::new()
$script:gameBytes=0L
$script:assertCursor=0
$script:prefixHash=$null
$script:touchedAliases=@{}
$script:skippedControls=@()
$script:skippedAliases=@()
$script:completedControls=[Collections.Generic.List[object]]::new()
$script:exactBaseline=@{}
$script:baseline=@{}
$script:maxRawFrames=[int]$plan.raw_frame_budget.max_frames
$script:plannedMaxFrames=[int]$plan.raw_frame_budget.maximum_planned
$script:sceneAnchorSeedPhase=$null
function Say([string]$s) {
    Add-Content -LiteralPath $logPath -Encoding UTF8 -Value ((Get-Date).ToString('HH:mm:ss.fff')+' '+$s)
}
function Test-RestorableBaseline([object]$Control,[hashtable]$Baseline,[hashtable]$ExactBaseline) {
    $value=[string]$Baseline[$Control.alias]
    if ($Control.type -eq 'bool') { return $value -cin @('TRUE','FALSE') }
    return ($ExactBaseline.ContainsKey($Control.alias) -and $ExactBaseline[$Control.alias].finite -eq $true -and
        [string]$ExactBaseline[$Control.alias].bits -match '^[0-9A-F]{8}$' -and
        $value -ceq [string]$ExactBaseline[$Control.alias].value)
}
function Get-PhaseCommands([object]$Control,[string]$Value,[string]$State,[hashtable]$Baseline,[hashtable]$Expected) {
    $commands=@()
    foreach ($override in @($Control.context_overrides)) {
        if ($override.alias -match '=' -or $override.alias -notin $Baseline.Keys) { throw ('invalid or missing captured context baseline '+$override.alias) }
        $contextValue=if($State -eq 'restore'){$Baseline[$override.alias]}elseif($override.value){'TRUE'}else{'FALSE'}
        $commands+=('set '+$override.alias+' '+$contextValue)
        $Expected[$override.alias]=$contextValue
    }
    $commands+=('set '+$Control.alias+' '+$Value)
    return $commands
}
function Save-Result([string]$Status,[string]$ErrorText='') {
    $result=[ordered]@{
        status=$Status
        error=$ErrorText
        slot=$Slot
        process_id=if($owner){$owner.Pid}else{$null}
        process_path=if($owner){$owner.Path}else{$ExpectedSlotExe}
        process_start_ticks=if($owner){[string]$owner.Ticks}else{$null}
        exe_sha256=$ExpectedSha256
        selected_controls=$plan.controls.Count
        completed_target_count=$script:completedControls.Count
        skipped_controls=@($script:skippedControls)
        target_results=@($targetRows.ToArray())
        frames=@($frameRows.ToArray())
        phases=@($phaseRows.ToArray())
        terminal_restore_verified=$script:terminalRestoreVerified
        site_credit=0
        max_raw_frames=$script:maxRawFrames
        planned_max_frames=$script:plannedMaxFrames
        scene_anchor_seed_phase=$script:sceneAnchorSeedPhase
        note='Typed field behavior only; live consumer conditions and pixels require independent review.'
    }
    $path=Join-Path $RunDir 'driver-result.json'
    $result|ConvertTo-Json -Depth 16|Set-Content -LiteralPath $path -Encoding utf8
}
function Get-PhaseName([object]$Control,[string]$State) {
    $family=if([string]$Control.id -like 'CgsSceneManager::*'){'scene'}elseif([string]$Control.id -like 'BrnWorld::ShadowMap::*'){'shadow'}elseif([string]$Control.id -like 'BrnDirector::*'){'director'}else{throw ('unknown phase family '+$Control.id)}
    return ($family+'_'+[string]$Control.alias+'_'+$State)
}
function Apply-Target([object]$Control) {
    $alias=$Control.alias
    $controlResult=[ordered]@{
        id=$Control.id
        alias=$alias
        scene_gate=$Control.scene_gate
        effect_witness=$Control.effect_witness
        phases=@()
        restore_verified=$false
        effect_status=if($alias -ceq 'E14'){'pending_known_pc_trap_field_mutation_only'}else{'pending_manual_native_frame_and_scene_review'}
    }
    if($alias -ceq 'SC02'){
        $controlResult.anchor_seed_phase=$script:sceneAnchorSeedPhase
        $controlResult.anchor_seed_frame=if($script:sceneAnchorSeedPhase -eq 'scene_triangle_anchor_seed'){$frameRows | Where-Object phase -eq 'scene_triangle_anchor_seed' | Select-Object -Last 1}else{$frameRows | Where-Object phase -eq 'natural_baseline' | Select-Object -Last 1}
    }
    $script:touchedAliases[$alias]=$script:baseline[$alias]
    foreach ($override in @($Control.context_overrides)) {
        $script:touchedAliases[$override.alias]=$script:baseline[$override.alias]
    }
    $script:writesStarted=$true
    foreach ($state in @('positive','negative','restore')) {
        if ($state -eq 'restore') {
            $value=$script:baseline[$alias]
        } elseif ($Control.type -eq 'bool') {
            $value=if($Control.$state){'TRUE'}else{'FALSE'}
        } else {
            $value=Get-F32Text $Control.$state ($alias+' '+$state)
        }
        $expected=@{}
        foreach ($c in $controls) { if($c.alias -notin $script:skippedAliases){$expected[$c.alias]=$script:baseline[$c.alias]} }
        $expected[$alias]=$value
        $commands=@(Get-PhaseCommands $Control $value $state $script:baseline $expected)
        [void](Execute (Get-PhaseName $Control $state) $commands $expected $true)
        $frame=$frameRows[$frameRows.Count-1]
        $readback=$phaseRows[$phaseRows.Count-1]
        $controlResult.phases+=@(@{
            state=$state
            value=$value
            frame_sha256=$frame.sha256
            frame_sequence=$frame.sequence
            raw_alias_readbacks=$readback.proofs
        })
        if ($state -eq 'restore' -and $alias -in @('E43','E44','E45')) {
            $after=Read-ExactClip $alias
            if ($after.bits -cne $script:exactBaseline[$alias].bits) { throw ('bitwise clip restore mismatch '+$alias) }
            $controlResult.restore_exact_bits=$after.bits
        } elseif($state -eq 'restore' -and $Control.type -eq 'f32') {
            $controlResult.restore_source_default_bits=$script:exactBaseline[$alias].bits
        }
    }
    $controlResult.restore_verified=$true
    $targetRows.Add($controlResult)
    $script:completedControls.Add($Control)
}
try {
    if ($Slot -ne 62190 -or $plan.control_count -ne 28 -or $controls.Count -ne 30) { throw 'wrong native batch or reserved slot' }
    if ($script:maxRawFrames -ne 90 -or $script:plannedMaxFrames -gt $script:maxRawFrames -or $script:plannedMaxFrames -ne (1+$plan.controls.Count*3+3)) { throw 'invalid bounded capture plan' }
    $knownAliases=@{};foreach($control in $controls){if($knownAliases.ContainsKey([string]$control.alias)){throw ('duplicate declared alias '+$control.alias)};$knownAliases[[string]$control.alias]=$true}
    foreach($control in $plan.controls){foreach($override in @($control.context_overrides)){if($override.alias -match '=' -or !$knownAliases.ContainsKey([string]$override.alias) -or $override.value -isnot [bool]){throw ('invalid context override alias/value '+$control.alias+': '+$override.alias)}}}
    $plannedNames=[Collections.Generic.List[string]]::new();foreach($control in $plan.controls){foreach($state in @('positive','negative','restore')){$plannedNames.Add((Get-PhaseName $control $state))}}
    foreach($fixedName in @('natural_baseline','scene_triangle_anchor_seed','terminal_restore','post_restore_readback','emergency_restore')){$plannedNames.Add($fixedName)}
    if(@($plannedNames | Sort-Object -Unique).Count -ne $plannedNames.Count){throw 'phase command/frame receipt namespace is not unique'}
    if ([IO.Path]::GetFullPath($ExpectedSlotExe) -ine [IO.Path]::GetFullPath((Join-Path $stage.exe_dir 'Burnout_PC.exe'))) { throw 'wrong private image path' }
    if ((Get-FileHash -LiteralPath $ExpectedSlotExe -Algorithm SHA256).Hash.ToLowerInvariant() -cne $ExpectedSha256) { throw 'wrong immutable executable hash' }
    if ($stage.slot -ne 62190 -or $stage.exe_sha256 -cne $ExpectedSha256) { throw 'wrong STAGING pin' }
    if ((Get-FileHash -LiteralPath $stage.profile -Algorithm SHA256).Hash.ToLowerInvariant() -cne $stage.profile_sha256) { throw 'wrong private profile hash' }

    for ($i=0;$i -lt 256;$i++) {
        $keys[$i]=[Threading.EventWaitHandle]::new($false,[Threading.EventResetMode]::ManualReset,('Local\BurnoutPC_DebugKey_{0:X2}_{1}' -f $i,$Slot))
        $keys[$i].Reset()|Out-Null
    }
    @{status='ready';slot=$Slot;driver_pid=$PID;event_count=256;planned_max_frames=$script:plannedMaxFrames;max_raw_frames=$script:maxRawFrames;source_commit=$plan.candidate.b5_commit}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $RunDir 'DRIVER_READY.json') -Encoding utf8

    while ([DateTime]::UtcNow -lt $deadline -and !$owner) {
        $matches=[Collections.Generic.List[object]]::new()
        foreach ($p in @(Get-Process -Name Burnout_PC -ErrorAction SilentlyContinue)) {
            try {
                if ($p.StartTime.ToUniversalTime() -lt $started) { continue }
                $c=Get-CimInstance Win32_Process -Filter ('ProcessId='+$p.Id)
                if ($c.ExecutablePath -and [IO.Path]::GetFullPath($c.ExecutablePath) -ieq [IO.Path]::GetFullPath($ExpectedSlotExe)) {
                    $matches.Add(@{Process=$p;Handle=$p.Handle;Pid=$p.Id;Ticks=$p.StartTime.ToUniversalTime().Ticks;Path=[IO.Path]::GetFullPath($c.ExecutablePath)})
                }
            } catch {}
        }
        if ($matches.Count -gt 1) { throw 'multiple exact private image processes' }
        if ($matches.Count -eq 1) { $owner=$matches[0] } else { Start-Sleep -Milliseconds 100 }
    }
    if (!$owner) { throw 'no new exact private process' }
    if (!$owner.Handle -or $owner.Process.HasExited) { throw 'no retained exact process handle' }
    $script:logAccepted=$true
    $frameEvent=[Threading.EventWaitHandle]::new($false,[Threading.EventResetMode]::ManualReset,('Local\BurnoutPC_FrameRequest_{0}_{1}' -f $owner.Pid,$Slot))

    [void](Wait-Line '^\[GameStateModule::OnProfileLoaded\].* rank=-?\d+ ' 0 150)
    $expectedProgress=Get-Content -Raw -LiteralPath (Join-Path $PackageRoot 'CURRENT_SAVE_EXPECTED_PROGRESS.json')|ConvertFrom-Json
    # Freeze one complete accepted snapshot of this private slot's log for the fixture gate.
    # The archived normal reference is informational; no live profile/log hash is read or pinned.
    $privateFixtureLogSnapshot=(Lines).ToArray()
    $profileGate=Test-BrnPrivateFixtureProgress $privateFixtureLogSnapshot $expectedProgress (Get-FileHash -LiteralPath $stage.profile -Algorithm SHA256).Hash.ToLowerInvariant()
    $profileGate|ConvertTo-Json -Depth 12|Set-Content -LiteralPath (Join-Path $RunDir 'PRIVATE_FIXTURE_LOAD_GATE.json') -Encoding utf8
    if (!$profileGate.pass) { throw ('private fixture load gate failed: '+($profileGate.problems -join '; ')) }
    [void](Wait-Line '^\[motion\] n \d+ pos .* mph (?:[1-9]\d|[1-9]\d{2,})(?:\.\d+)? gear ' 0 150)
    Start-Sleep -Seconds 12
    Own

    $phaseFile=Join-Path $stage.cwd 'q62190.cfg'
    $script:phaseHash=(Get-FileHash -LiteralPath $phaseFile -Algorithm SHA256).Hash.ToLowerInvariant()
    $cursor=(Lines).Count
    Console $true
    Type-Setup
    Console $false
    $natural=Read-Values $cursor
    foreach ($c in $controls) { $script:baseline[$c.alias]=$natural.values[$c.alias] }

    $logSnapshot=(Lines).ToArray()
    foreach($control in $plan.controls | Where-Object type -eq 'f32' | Where-Object { $_.path_attestation -eq 'scene_component' }){
        try {
            $proof=Get-ExactSceneDefaultProof $control $natural.values[$control.alias] $logSnapshot
            $script:baseline[$control.alias]=$proof.value
            $script:exactBaseline[$control.alias]=$proof
        } catch {
            $script:skippedAliases+= $control.alias
            $script:skippedControls+=@{id=$control.id;alias=$control.alias;state='pending';reason=('exact source-default provenance unavailable; no setter attempted: '+$_.Exception.Message)}
        }
    }

    foreach ($alias in @('E43','E44','E45')) {
        try {
            $read=Read-ExactClip $alias
            if ($read.finite) {
                $script:exactBaseline[$alias]=$read
                $display=ConvertTo-FiniteF32 $natural.values[$alias] ($alias+' rounded display')
                $exact=ConvertTo-FiniteF32 $read.value ($alias+' exact read')
                if ([Math]::Abs([double]$display-[double]$exact) -gt 0.000501 -and $display -ne $exact) {
                    $script:exactBaseline.Remove($alias)
                } else {
                    $script:baseline[$alias]=$read.value
                }
            }
        } catch {
            $script:exactBaseline.Remove($alias)
            Say ('exact clip restore pin unavailable; skip only that float: '+$alias+' '+$_.Exception.Message)
        }
    }
    @{schema=2;owner_pid=$owner.Pid;owner_start_ticks=[string]$owner.Ticks;exe_sha256=$ExpectedSha256;
      values=$script:baseline;exact_f32_baselines=$script:exactBaseline;readbacks=$natural.proofs;
      source_commit=$plan.candidate.b5_commit;debug_ini_log_snapshot_lines=$logSnapshot.Count} |
        ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $RunDir 'NATURAL_BASELINE.json') -Encoding utf8
    Capture-PhaseRaw @{name='natural_baseline'}

    $script:sceneAnchorSeedPhase='natural_baseline'


    foreach ($control in $plan.controls) {
        if (!(Test-RestorableBaseline $control $script:baseline $script:exactBaseline)) {
            $script:skippedAliases+= $control.alias
            $script:skippedControls+=@{id=$control.id;alias=$control.alias;state='pending';reason='natural value lacks a safe exact same-run restore; no write attempted'}
            continue
        }
        if($control.alias -ceq 'SC02' -and $script:baseline['SC02'] -ceq 'TRUE'){
            $script:touchedAliases['SC02']=$script:baseline['SC02'];$script:writesStarted=$true
            $seedExpected=@{};foreach($c in $controls){$seedExpected[$c.alias]=$script:baseline[$c.alias]};$seedExpected['SC02']='FALSE'
            [void](Execute 'scene_triangle_anchor_seed' @('set SC02 FALSE') $seedExpected $true)
            $script:sceneAnchorSeedPhase='scene_triangle_anchor_seed'
        }
        Apply-Target $control
    }

    $terminal=@{}
    foreach ($alias in $script:touchedAliases.Keys) { $terminal[$alias]=$script:baseline[$alias] }
    if ($terminal.Count) {
        $expectedValues=@{}
        foreach ($c in $controls) { if($c.alias -notin $script:skippedAliases){$expectedValues[$c.alias]=$script:baseline[$c.alias]} }
        [void](Execute 'terminal_restore' (Commands-For $terminal) $expectedValues $true)
    }
    $expectedValues=@{}
    foreach ($c in $controls) { if($c.alias -notin $script:skippedAliases){$expectedValues[$c.alias]=$script:baseline[$c.alias]} }
    [void](Execute 'post_restore_readback' @() $expectedValues $true)

    foreach ($alias in @('E43','E44','E45')) {
        if ($script:exactBaseline.ContainsKey($alias) -and (Read-ExactClip $alias).bits -cne $script:exactBaseline[$alias].bits) {
            throw ('terminal exact clip restore mismatch '+$alias)
        }
    }
    $script:terminalRestoreVerified=$true
    if($frameRows.Count -gt $script:maxRawFrames -or $frameRows.Count -gt $script:plannedMaxFrames){throw 'raw frame budget exceeded including terminal frames'}
    $null=Complete-NativeBatchCaptureAudit -RunDir $RunDir -Rows $frameRows.ToArray() -Slot $Slot -MaxFrames $script:maxRawFrames
    Save-Result 'machine_complete_awaiting_independent_pixels'
    $resultPath=Join-Path $RunDir 'driver-result.json'
    & (Join-Path $PackageRoot 'Request-HarnessPhaseDone.ps1') -ProcessId $owner.Pid -Slot $Slot -ExpectedImagePath $owner.Path -ExpectedStartUtc $owner.Process.StartTime.ToUniversalTime().ToString('o') -WitnessPath $resultPath -WitnessSha256 (Get-FileHash -LiteralPath $resultPath -Algorithm SHA256).Hash.ToLowerInvariant() -ReceiptPath (Join-Path $RunDir 'PHASE_DONE_REQUEST.json')
    Say ('RESULT DONE; targets='+$script:completedControls.Count+' skipped='+$script:skippedControls.Count+' frames='+$frameRows.Count)
} catch {
    $reason=$_.Exception.Message
    $script:cleanupMode=$true
    $script:cleanupDeadline=[DateTime]::UtcNow.AddSeconds(25)
    if ($owner -and $script:writesStarted -and !$script:terminalRestoreVerified) {
        try {
            $cleanup=@{}
            foreach ($alias in $script:touchedAliases.Keys) { $cleanup[$alias]=$script:baseline[$alias] }
            if ($cleanup.Count) {
                $expectedValues=@{}
                foreach ($c in $controls) { if($c.alias -notin $script:skippedAliases){$expectedValues[$c.alias]=$script:baseline[$c.alias]} }
                [void](Execute 'emergency_restore' (Commands-For $cleanup) $expectedValues $false)
            }
            foreach ($alias in @('E43','E44','E45')) {
                if ($script:exactBaseline.ContainsKey($alias) -and (Read-ExactClip $alias).bits -cne $script:exactBaseline[$alias].bits) {
                    throw ('emergency exact clip restore mismatch '+$alias)
                }
            }
            $script:terminalRestoreVerified=$true
        } catch { Say ('emergency restore failed: '+$_.Exception.Message) }
    }
    if ($owner) { Save-Result 'fail' $reason }
    Say ('RESULT FAIL '+$reason)
    if ($owner) {
        try {
            $resultPath=Join-Path $RunDir 'driver-result.json'
            & (Join-Path $PackageRoot 'Request-HarnessPhaseDone.ps1') -ProcessId $owner.Pid -Slot $Slot -ExpectedImagePath $owner.Path -ExpectedStartUtc $owner.Process.StartTime.ToUniversalTime().ToString('o') -WitnessPath $resultPath -WitnessSha256 (Get-FileHash -LiteralPath $resultPath -Algorithm SHA256).Hash.ToLowerInvariant() -ReceiptPath (Join-Path $RunDir 'PHASE_DONE_REQUEST.json')
        } catch { Say ('phase-stop request failed: '+$_.Exception.Message) }
    }
    exit 1
} finally {
    foreach ($k in $keys.Values) { try { $k.Reset()|Out-Null; $k.Dispose() } catch {} }
    if ($frameEvent) { $frameEvent.Reset()|Out-Null; $frameEvent.Dispose() }
}


