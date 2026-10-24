param([Parameter(Mandatory=$true)][hashtable]$Context)
$ErrorActionPreference = 'Stop'
$fail = [Collections.Generic.List[string]]::new()
function Need([bool]$Condition,[string]$Message) { if (!$Condition) { $script:fail.Add($Message) } }
function Read-Scalar([string]$Text,[string]$Kind) {
    if ($Kind -eq 'bool') {
        if ($Text -cnotin @('TRUE','FALSE')) { throw "Bad boolean witness '$Text'." }
        return ($Text -ceq 'TRUE')
    }
    $value = 0.0
    if (![double]::TryParse($Text,[Globalization.NumberStyles]::Float,[Globalization.CultureInfo]::InvariantCulture,[ref]$value)) { throw "Bad numeric witness '$Text'." }
    if ($Kind -eq 'int') { return [int][math]::Round($value) }
    return [double]$value
}
function Same-Value($A,$B,[string]$Kind) {
    if ($Kind -eq 'bool') { return ([bool]$A -eq [bool]$B) }
    return ([math]::Abs([double]$A - [double]$B) -le 0.0005)
}
function Find-Diagnostic([string]$Owner,[string]$Sample) {
    $match = @($Context.LogLines | Where-Object { $_ -match ('\[geometry-witness\] owner=' + [regex]::Escape($Owner) + ' sample=' + [regex]::Escape($Sample) + ' ') })
    if ($match.Count -ne 1) { return $null }
    $fields = @{}
    foreach ($m in [regex]::Matches($match[0],'(\w+)=([^ ]+)')) { $fields[$m.Groups[1].Value] = $m.Groups[2].Value }
    return $fields
}
function Field-ForAlias([string]$Alias) {
    switch ($Alias) {
        'TrWorld' { return 'draw_world' }
        'TrAabb' { return 'draw_aabbs' }
        'TrDist' { return 'soup_distance' }
        'TrEdge' { return 'draw_edges' }
        'TrSweep' { return 'sweep_test' }
        'SpX' { return 'pos_x' }
        'SpY' { return 'pos_y' }
        'SpZ' { return 'pos_z' }
        'SpRad' { return 'radius' }
        'SpVX' { return 'vel_x' }
        'SpVY' { return 'vel_y' }
        'SpVZ' { return 'vel_z' }
        'MapLvl' { return 'requested_levels' }
        'SwDyn' { return 'draw_dynamic' }
        'SwFrz' { return 'draw_frozen' }
        'SwDist' { return 'draw_distance' }
        default { throw "Unknown alias in visual case manifest: $Alias" }
    }
}
$runDir = $Context.RunDir
$manifestPath = Join-Path $runDir 'geometry-witnesses.json'
$keyLogPath = Join-Path $runDir 'geometry-keys.log'
$plan = Get-Content -LiteralPath (Join-Path $Context.Case.CaseDir 'CASE_PLAN.json') -Raw | ConvertFrom-Json
$keyText = if (Test-Path -LiteralPath $keyLogPath) { Get-Content -LiteralPath $keyLogPath -Raw } else { '' }
Need (($keyText -match '(?m)RESULT DONE ') -or ($keyText -match '(?m)RESULT DEFERRED:')) 'no helper completion/defer marker'
Need ($keyText -notmatch '(?m)RESULT FAIL:') 'helper stopped on a guarded failure'
if (!(Test-Path -LiteralPath $manifestPath -PathType Leaf)) { return @{Pass=$false;Detail='missing machine witness manifest'} }
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
Need ($manifest.status -cin @('machine_evidence_ready_for_root_visual_review','deferred_prerequisites')) 'unknown evidence-manifest status'
Need ($manifest.candidate_source -ceq $plan.candidate_source -and $manifest.candidate_tree -ceq $plan.candidate_tree) 'manifest candidate identity differs'
Need ($manifest.probe_patch_sha256 -ceq $plan.probe_patch_sha256) 'manifest diagnostic patch differs'
Need ($manifest.execution_exe_sha256 -ceq [string]$Context.Case.Binding.execution_exe_sha256) 'manifest executable differs from reviewed staged binary'
Need ([int]$manifest.frame_count -le 96) 'more than96 frames were captured'
$ownerPath = Join-Path $runDir 'geometry-input-owner.json'
if (!(Test-Path -LiteralPath $ownerPath -PathType Leaf)) { $fail.Add('missing frame-request PID/slot owner'); return @{Pass=$false;Detail=$fail -join '; '} }
$owner = Get-Content -LiteralPath $ownerPath -Raw | ConvertFrom-Json
$captures = [Collections.Generic.List[object]]::new()
if ($manifest.baseline_capture) { $captures.Add($manifest.baseline_capture) }
foreach ($support in $manifest.support_states) { if ($support.capture) { $captures.Add($support.capture) } }
foreach ($siteRow in $manifest.sites) { foreach ($stateRow in $siteRow.states) { if ($stateRow.capture) { $captures.Add($stateRow.capture) } } }
foreach ($capture in $captures) {
    Need ([int]$capture.pid -eq [int]$owner.pid -and [int]$capture.slot -eq [int]$owner.slot) 'frame request came from a different game PID/slot'
    Need ([int]$capture.sequence -ge 1 -and [int]$capture.present -ge 0) 'frame request acknowledgement has an invalid sequence/present'
    $framesForCapture = @($capture.frames)
    Need ($framesForCapture.Count -eq 1) ('each state must have exactly one requested fresh frame: '+$capture.label)
    foreach ($frame in $framesForCapture) {
        Need ($frame.name -ceq ('bb_{0:D6}.bmp' -f [int]$capture.present)) ('frame filename does not match its acknowledged present '+$capture.label)
        $framePath = Join-Path $Context.FrameDir ([string]$frame.name)
        if (!(Test-Path -LiteralPath $framePath -PathType Leaf)) { $fail.Add('missing requested frame '+$frame.name); continue }
        Need ((Get-FileHash -LiteralPath $framePath -Algorithm SHA256).Hash.ToLowerInvariant() -ceq [string]$frame.sha256) ('requested frame hash differs '+$frame.name)
    }
}
$sequences = @($captures | ForEach-Object { [int]$_.sequence } | Sort-Object -Unique)
Need ($sequences.Count -eq $captures.Count -and $sequences.Count -eq [int]$manifest.frame_count) 'named frame request sequence does not account for every captured image exactly once'
for ($i=0; $i -lt $sequences.Count; ++$i) { Need ($sequences[$i] -eq ($i+1)) 'named frame request acknowledgements are not contiguous from1' }
$frameFiles = @(Get-ChildItem -LiteralPath $Context.FrameDir -File -Filter 'bb_*.bmp' -ErrorAction SilentlyContinue)
Need ($frameFiles.Count -eq $captures.Count) 'frame directory contains unrequested or unaccounted BMP files'
$expected = @{}
foreach ($control in $plan.groups.full16.controls) { $expected[[string]$control.site_id] = $control }
$executed = [Collections.Generic.List[object]]::new()
$deferred = [Collections.Generic.List[string]]::new()
foreach ($site in $manifest.sites) {
    if (!$expected.ContainsKey([string]$site.site_id)) { $fail.Add('unrecognized site in manifest '+$site.site_id); continue }
    if ($site.status -ceq 'deferred_prerequisite') { $deferred.Add([string]$site.site_id); continue }
    $control = $expected[[string]$site.site_id]
    Need ($site.status -ceq 'machine_evidence_awaiting_root_visual_review') ('unexpected pre-review site status '+$site.site_id)
    $states = @($site.states)
    Need ($states.Count -eq 3) ('site lacks three separate states '+$site.site_id)
    if ($states.Count -ne 3) { continue }
    Need (($states[0].state -ceq 'positive') -and ($states[1].state -ceq 'negative') -and ($states[2].state -ceq 'restore')) ('state order differs '+$site.site_id)
    $base = Read-Scalar ([string]$site.baseline) ([string]$control.kind)
    $stateValues = @{}
    foreach ($state in $states) {
        $actual = Read-Scalar ([string]$state.actual) ([string]$control.kind)
        $requested = Read-Scalar ([string]$state.requested) ([string]$control.kind)
        Need (Same-Value $actual $requested ([string]$control.kind)) ('alias readback differs from request '+$site.site_id+'/'+$state.state)
        if ($state.state -ceq 'restore') { Need (Same-Value $actual $base ([string]$control.kind)) ('restore state differs from captured baseline '+$site.site_id) }
        $stateValues[$state.state] = $actual
        $frames = @($state.capture.frames)
        Need ($frames.Count -ge 1) ('state has no bounded in-window image '+$site.site_id+'/'+$state.state)
        foreach ($frame in $frames) {
            $framePath = Join-Path $Context.FrameDir ([string]$frame.name)
            if (!(Test-Path -LiteralPath $framePath -PathType Leaf)) { $fail.Add('missing captured frame '+$frame.name); continue }
            $hash = (Get-FileHash -LiteralPath $framePath -Algorithm SHA256).Hash.ToLowerInvariant()
            Need ($hash -ceq [string]$frame.sha256) ('captured image hash differs '+$frame.name)
        }
    }
    $distinctStates = !(Same-Value $stateValues.positive $stateValues.negative ([string]$control.kind))
    Need $distinctStates ('positive and negative requested states are identical '+$site.site_id)
    foreach ($state in $states) {
        $stateActual = Read-Scalar ([string]$state.actual) ([string]$control.kind)
        if ($state.owner -ceq 'triangle') {
            $row = Find-Diagnostic 'triangle' ([string]$state.owner_sample)
            Need ($null -ne $row) ('Triangle owner dispatch sample missing '+$site.site_id)
            if ($row) {
                Need ([int]$row.soup_lists -gt 0) ('Triangle owner soup list became empty '+$site.site_id)
                $field = Field-ForAlias ([string]$control.alias)
                $diagValue = [string]$row[$field]
                if ($control.kind -ceq 'bool') {
                    $expectedBit = if ($stateActual) {'1'} else {'0'}
                    Need ($diagValue -ceq $expectedBit) ('Triangle owner field differs from alias '+$site.site_id+'/'+$state.state)
                } else {
                    Need (Same-Value (Read-Scalar $diagValue 'float') $stateActual 'float') ('Triangle owner field differs from alias '+$site.site_id+'/'+$state.state)
                }
                if ($control.alias -ceq 'MapLvl') { Need ([int]$row.map_levels -eq [int]$state.actual) ('live map level differs '+$site.site_id) }
            }
        } elseif ($state.owner -ceq 'sweeper') {
            $row = Find-Diagnostic 'sweeper' ([string]$state.owner_sample)
            Need ($null -ne $row) ('SceneSweeper owner dispatch sample missing '+$site.site_id)
            if ($row) {
                Need ([int]$row.owner_ready -eq 1) ('SceneSweeper typed owner is absent '+$site.site_id)
                $field = Field-ForAlias ([string]$control.alias)
                $diagValue = [string]$row[$field]
                if ($control.kind -ceq 'bool') {
                    $expectedBit = if ($stateActual) {'1'} else {'0'}
                    Need ($diagValue -ceq $expectedBit) ('SceneSweeper owner field differs from alias '+$site.site_id+'/'+$state.state)
                } else {
                    Need (Same-Value (Read-Scalar $diagValue 'float') $stateActual 'float') ('SceneSweeper owner field differs from alias '+$site.site_id+'/'+$state.state)
                }
                if ($site.site_id -match '#0001$') { Need ([int]$row.dynamic_intervals -gt 0) 'dynamic interval list empty at site #0001' }
                elseif ($site.site_id -match '#0002$') { Need ([int]$row.inactive_intervals -gt 0) 'inactive interval list empty at site #0002' }
                else { Need (([int]$row.dynamic_intervals + [int]$row.inactive_intervals) -gt 0) 'both interval lists empty at site #0003' }
            }
        } else { $fail.Add('unknown typed owner '+$site.site_id) }
    }
    if ($control.alias -ceq 'MapLvl') {
        $mem = @($states | Where-Object { $null -ne $_.paired_memory_use } | ForEach-Object { [int]$_.paired_memory_use })
        Need ($mem.Count -eq 3) 'Num spacial levels lacks paired memory readbacks'
        Need (@($mem | Where-Object { $_ -lt 0 }).Count -eq 0) 'paired spatial-map memory readout is invalid'
    }
    $executed.Add([pscustomobject]@{SiteId=[string]$site.site_id;Frames=@($states | ForEach-Object { @($_.capture.frames | ForEach-Object {$_.name}) })})
}
Need ($manifest.sites.Count -eq 16) 'manifest does not account for all16 registered sites'
$manifestSiteIds = @($manifest.sites | ForEach-Object { [string]$_.site_id } | Sort-Object -Unique)
Need ($manifestSiteIds.Count -eq 16) 'manifest site IDs are not a complete unique16-site set'
if ($fail.Count -gt 0) { return @{Pass=$false;Detail=$fail -join '; '} }
if ($manifest.status -ceq 'deferred_prerequisites') {
    return @{Pass=$false;Detail=('preflight deferred before actions: '+$manifest.reason+'; no site disposition is produced')}
}
if ($executed.Count -eq 0) { return @{Pass=$false;Detail='no site had an eligible live owner dataset'} }
$reviewPath = Join-Path $runDir 'root-visual-judgment.json'
if (!(Test-Path -LiteralPath $reviewPath -PathType Leaf)) {
    $detail = 'machine evidence captured for '+$executed.Count+' sites; Root visual review is still required; deferred='+$deferred.Count
    return @{Pass=$false;Detail=$detail}
}
$review = Get-Content -LiteralPath $reviewPath -Raw | ConvertFrom-Json
$manifestHash = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant()
$reviewerPresent = -not [string]::IsNullOrWhiteSpace([string]$review.reviewer)
$reviewedUtcPresent = -not [string]::IsNullOrWhiteSpace([string]$review.reviewed_utc)
Need ($review.status -ceq 'root_reviewed' -and $review.group -ceq 'full16' -and
    $review.candidate_source -ceq $plan.candidate_source -and $review.manifest_sha256 -ceq $manifestHash -and
    ([IO.Path]::GetFullPath([string]$review.run_dir) -ieq [IO.Path]::GetFullPath($runDir)) -and
    $reviewerPresent -and $reviewedUtcPresent -and
    $review.inventory_status_changed -eq $false) 'Root visual judgment is not bound to this exact run manifest'
Need (@($review.sites).Count -eq 16) 'Root judgment must preserve a row for each of the16 candidate sites'
$declaredDeferred = @($review.deferred_sites | Sort-Object)
$expectedDeferred = @($deferred.ToArray() | Sort-Object)
Need (($declaredDeferred -join "`n") -ceq ($expectedDeferred -join "`n")) 'Root deferred-site list differs from typed owner gates'
foreach ($site in $executed) {
    $decision = @($review.sites | Where-Object { $_.site_id -ceq $site.SiteId })
    Need ($decision.Count -eq 1) ('Root did not judge '+$site.SiteId)
    if ($decision.Count -eq 1) {
        $reviewNotePresent = -not [string]::IsNullOrWhiteSpace([string]$decision[0].note)
        Need ($decision[0].positive -eq $true -and $decision[0].negative -eq $true -and $decision[0].restore -eq $true -and
            $reviewNotePresent) ('Root visual witness incomplete '+$site.SiteId)
    }
}
foreach ($siteId in $expectedDeferred) {
    $decision = @($review.sites | Where-Object { $_.site_id -ceq $siteId })
    Need ($decision.Count -eq 1) ('Root omitted deferred site row '+$siteId)
    if ($decision.Count -eq 1) {
        Need ($null -eq $decision[0].positive -and $null -eq $decision[0].negative -and $null -eq $decision[0].restore -and
            [string]::IsNullOrWhiteSpace([string]$decision[0].note)) ('Deferred site was assigned a visual disposition '+$siteId)
    }
}
if ($fail.Count -gt 0) { return @{Pass=$false;Detail=$fail -join '; '} }
@{Pass=$true;Detail=('Root reviewed '+$executed.Count+' executed site chains; '+$deferred.Count+' gated sites remain without disposition. No inventory status is assigned here.')}
