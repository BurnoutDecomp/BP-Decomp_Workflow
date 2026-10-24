# Proposal only. Direct event handles are sent only to the exact fresh staged process.
param(
    [Parameter(Mandatory=$true)][string]$GameLog,
    [Parameter(Mandatory=$true)][string]$OutDir,
    [Parameter(Mandatory=$true)][string]$FrameDir,
    [Parameter(Mandatory=$true)][string]$PlanPath,
    [Parameter(Mandatory=$true)][string]$StepsFile,
    [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9_./-]{1,70}$')][string]$RunRelativePath,
    [Parameter(Mandatory=$true)][ValidateSet('full16')][string]$Group,
    [Parameter(Mandatory=$true)][ValidatePattern('^geom_[A-Za-z0-9_]+$')][string]$SetupCommand,
    [Parameter(Mandatory=$true)][string]$ExpectedImage,
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{64}$')][string]$ExpectedExeSha256,
    [Parameter(Mandatory=$true)][string]$StartedAfterUtc,
    [Parameter(Mandatory=$true)][ValidateRange(1,65535)][int]$Slot,
    [ValidateRange(30,238)][int]$TimeoutSec=238
)
$ErrorActionPreference = 'Stop'
$timerStart = [DateTime]::UtcNow
$launchFloor = [DateTime]::Parse($StartedAfterUtc).ToUniversalTime()
$image = [IO.Path]::GetFullPath($ExpectedImage)
$helperLog = Join-Path $OutDir 'geometry-keys.log'
$ownerPath = Join-Path $OutDir 'geometry-input-owner.json'
$manifestPath = Join-Path $OutDir 'geometry-witnesses.json'
$keys = @{}
$owner = $null
$script:logCursor = [long]0
$script:logLines = [Collections.Generic.List[string]]::new()
$script:lastDiagnosticRows = @{}
$script:framesWritten = 0
$script:baselineCapture = $null
$script:frameRequestSequence = 0
$script:frameRequestEvent = $null
$script:siteResults = @{}
$script:deferred = @{}
$script:trianglePreflight = $null
$script:sweeperPreflight = $null
$planRoot = Get-Content -LiteralPath $PlanPath -Raw | ConvertFrom-Json
if ($planRoot.groups.$Group.controls.Count -ne 16) { throw 'CASE_PLAN full16 does not contain16 controls.' }
$groupPlan = $planRoot.groups.$Group
$controls = @($groupPlan.controls)
$controlBySite = @{}
$controlByAlias = @{}
foreach ($control in $controls) {
    $controlBySite[[string]$control.site_id] = $control
    $controlByAlias[[string]$control.alias] = $control
}
$aliasPaths = @{}
foreach ($control in $controls) {
    $aliasPaths[[string]$control.alias] = [string]$control.path
    if ($control.paired_alias) { $aliasPaths[[string]$control.paired_alias] = [string]$control.paired_path }
}
$aliasPaths['TrSweep'] = 'World/Collision/Test swept sphere collision'
$baselines = @{}
$currentValues = @{}
$siteStates = [Collections.Generic.List[object]]::new()
$supportStates = [Collections.Generic.List[object]]::new()
$siteResults = @{}
$deferred = @{}
$eligibleSteps = [Collections.Generic.List[object]]::new()
$actualAliasCursor = 0

function Say([string]$Text) {
    Add-Content -LiteralPath $helperLog -Value ('{0} {1}' -f [DateTime]::UtcNow.ToString('o'),$Text) -Encoding UTF8
}
function Check-Deadline {
    if (([DateTime]::UtcNow - $script:timerStart).TotalSeconds -gt $TimeoutSec) { throw 'Bounded geometry helper timed out; no further stimulus.' }
}
function Assert-Owner {
    Check-Deadline
    if ($null -eq $script:owner) { throw 'No exact staged process has been adopted.' }
    $p = [Diagnostics.Process]::GetProcessById([int]$script:owner.pid)
    $p.Refresh()
    $actualImage = $p.MainModule.FileName
    if ($p.HasExited -or !$actualImage -or [IO.Path]::GetFullPath($actualImage) -ine $image -or
        $p.StartTime.ToUniversalTime().Ticks.ToString() -cne $script:owner.start_utc_ticks) {
        throw 'PID/image/start ownership changed; no further stimulus.'
    }
    $games = @(Get-CimInstance Win32_Process -Filter "Name LIKE 'Burnout%.exe' OR Name='TUB_Burnout_PC_External.exe'")
    if ($games.Count -ne 1 -or [int]$games[0].ProcessId -ne [int]$script:owner.pid -or
        !$games[0].ExecutablePath -or [IO.Path]::GetFullPath($games[0].ExecutablePath) -ine $image) {
        throw 'A foreign game appeared or the exact game owner changed; no further stimulus.'
    }
}
function Pump-Log {
    if (!(Test-Path -LiteralPath $GameLog -PathType Leaf)) { return }
    $fs = [IO.File]::Open($GameLog,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete)
    $reader = $null
    try {
        if ($fs.Length -lt $script:logCursor) { $script:logCursor = 0; $script:logLines.Clear() }
        $fs.Position = $script:logCursor
        $reader = [IO.StreamReader]::new($fs,[Text.Encoding]::UTF8,$true,4096,$true)
        $text = $reader.ReadToEnd()
        $script:logCursor = $fs.Position
    } finally { if ($reader) { $reader.Dispose() }; $fs.Dispose() }
    if ([string]::IsNullOrEmpty($text)) { return }
    if ($text -match '(?m)^(?:Component not found|Unknown alias value|Alias not found|Variable not found|Unknown command|Cannot open .+|line too long or missing LF.+)\r?$' -or
        $text -match '\[ASSERT \d+\]|\[EXCEPTION\]') { throw 'Live alias/script/assert/exception failure; stop all further stimulus.' }
    foreach ($line in [regex]::Split($text,'\r?\n')) {
        if ($line.Length -gt 0) { $script:logLines.Add($line) }
    }
}
function Log-Count { return $script:logLines.Count }
function Tap-BoundedPause([int]$Milliseconds) {
    $until = [DateTime]::UtcNow.AddMilliseconds($Milliseconds)
    do { Assert-Owner; Start-Sleep -Milliseconds 100 } while ([DateTime]::UtcNow -lt $until)
}
function Get-Key([int]$Code) {
    if (!$script:keys.ContainsKey($Code)) {
        Assert-Owner
        $script:keys[$Code] = [Threading.EventWaitHandle]::new($false,[Threading.EventResetMode]::ManualReset,
            ('Local\BurnoutPC_DebugKey_{0:X2}_{1}' -f $Code,$Slot))
        $script:keys[$Code].Reset() | Out-Null
    }
    return $script:keys[$Code]
}
function Tap-Key([int]$Code,[bool]$Shift=$false) {
    Assert-Owner
    $key = Get-Key $Code
    $shiftKey = Get-Key 16
    if ($Shift) { $shiftKey.Set() | Out-Null }
    try {
        Start-Sleep -Milliseconds 20
        $key.Set() | Out-Null
        Start-Sleep -Milliseconds 60
    } finally { $key.Reset() | Out-Null; $shiftKey.Reset() | Out-Null }
    Start-Sleep -Milliseconds 60
}
function Type-Text([string]$Text) {
    foreach ($ch in $Text.ToCharArray()) {
        $n = [int]$ch
        if ($n -ge 97 -and $n -le 122) { Tap-Key ($n - 32) }
        elseif ($n -ge 65 -and $n -le 90) { Tap-Key $n $true }
        elseif ($n -ge 48 -and $n -le 57) { Tap-Key $n }
        else {
            switch ($ch) {
                ' ' { Tap-Key 32 }
                '/' { Tap-Key 191 }
                '"' { Tap-Key 222 $true }
                '.' { Tap-Key 190 }
                '-' { Tap-Key 189 }
                '_' { Tap-Key 189 $true }
                default { throw "Unsupported console character: $ch" }
            }
        }
    }
}
function Wait-LogRegex([string]$Pattern,[int]$Seconds=120) {
    $until = [DateTime]::UtcNow.AddSeconds($Seconds)
    while ([DateTime]::UtcNow -lt $until) {
        Assert-Owner; Pump-Log
        if ([regex]::IsMatch(($script:logLines -join "`n"),$Pattern,[Text.RegularExpressions.RegexOptions]::Multiline)) { return }
        Start-Sleep -Milliseconds 200
    }
    throw "Timed out waiting for game log cue: $Pattern"
}
function Read-AliasValue([string]$Name,[string]$Path,[int]$AfterIndex,[int]$Seconds=8) {
    $label = $Name + ': /' + $Path.TrimStart('/')
    $until = [DateTime]::UtcNow.AddSeconds($Seconds)
    while ([DateTime]::UtcNow -lt $until) {
        Assert-Owner; Pump-Log
        for ($i=[math]::Max(0,$AfterIndex); $i -lt $script:logLines.Count; ++$i) {
            if ($script:logLines[$i].Trim() -cne $label) { continue }
            $j = $i + 1
            while ($j -lt $script:logLines.Count -and [string]::IsNullOrWhiteSpace($script:logLines[$j])) { ++$j }
            if ($j -lt $script:logLines.Count) {
                return [pscustomobject]@{Name=$Name;Path=$Path;Text=$script:logLines[$j].Trim();LogIndex=$j+1}
            }
        }
        Start-Sleep -Milliseconds 100
    }
    throw "No fresh actual alias readback for $Name ($Path)."
}
function Parse-Scalar([string]$Text,[string]$Kind) {
    if ($Kind -eq 'bool') {
        if ($Text -cnotin @('TRUE','FALSE')) { throw "Expected boolean alias readback, got '$Text'." }
        return ($Text -ceq 'TRUE')
    }
    $value = 0.0
    if (![double]::TryParse($Text,[Globalization.NumberStyles]::Float,[Globalization.CultureInfo]::InvariantCulture,[ref]$value)) {
        throw "Expected numeric alias readback, got '$Text'."
    }
    if ($Kind -eq 'int') { return [int][math]::Round($value) }
    return [double]$value
}
function Format-Scalar($Value,[string]$Kind) {
    if ($Kind -eq 'bool') { return $(if ([bool]$Value) {'TRUE'} else {'FALSE'}) }
    if ($Kind -eq 'int') { return ([int]$Value).ToString([Globalization.CultureInfo]::InvariantCulture) }
    return ([double]$Value).ToString('0.######',[Globalization.CultureInfo]::InvariantCulture)
}
function Scalar-Equal($Actual,$Expected,[string]$Kind) {
    if ($Kind -eq 'bool') { return ([bool]$Actual -eq [bool]$Expected) }
    return ([math]::Abs([double]$Actual - [double]$Expected) -le 0.0005)
}
function Get-WitnessRows {
    Pump-Log
    $rows = [Collections.Generic.List[object]]::new()
    for ($i=0; $i -lt $script:logLines.Count; ++$i) {
        $line = $script:logLines[$i]
        if ($line -notmatch '\[geometry-witness\]') { continue }
        $fields = @{}
        foreach ($m in [regex]::Matches($line,'(\w+)=([^ ]+)')) { $fields[$m.Groups[1].Value] = $m.Groups[2].Value }
        $rows.Add([pscustomobject]@{Fields=$fields;Line=$line;LogIndex=$i+1})
    }
    return @($rows.ToArray())
}
function Find-Field([hashtable]$Fields,[string]$Name) {
    if (!$Fields.ContainsKey($Name)) { return $null }
    return [string]$Fields[$Name]
}
function Wait-OwnerRow([string]$OwnerName,[int]$Seconds=20,[scriptblock]$Predicate={param($r) $true},[int]$AfterIndex=0,[bool]$RequireFresh=$false) {
    $until = [DateTime]::UtcNow.AddSeconds($Seconds)
    $last = $null
    while ([DateTime]::UtcNow -lt $until) {
        Assert-Owner
        foreach ($row in (Get-WitnessRows)) {
            if ($row.Fields['owner'] -ceq $OwnerName) {
                $last = $row
                if ($RequireFresh -and $row.LogIndex -le $AfterIndex) { continue }
                if (& $Predicate $row) { return $row }
            }
        }
        Start-Sleep -Milliseconds 200
    }
    if ($RequireFresh) { return $null }
    return $last
}
function Get-FieldForAlias([string]$Alias) {
    switch ($Alias) {
        'TrWorld' { return 'draw_world' }
        'TrAabb'  { return 'draw_aabbs' }
        'TrDist'  { return 'soup_distance' }
        'TrEdge'  { return 'draw_edges' }
        'TrSweep' { return 'sweep_test' }
        'SpX'     { return 'pos_x' }
        'SpY'     { return 'pos_y' }
        'SpZ'     { return 'pos_z' }
        'SpRad'   { return 'radius' }
        'SpVX'    { return 'vel_x' }
        'SpVY'    { return 'vel_y' }
        'SpVZ'    { return 'vel_z' }
        'MapLvl'  { return 'requested_levels' }
        'SwDyn'   { return 'draw_dynamic' }
        'SwFrz'   { return 'draw_frozen' }
        'SwDist'  { return 'draw_distance' }
        default { throw "No typed witness field mapping for alias $Alias." }
    }
}
function Get-OwnerForSite([string]$SiteId) {
    if ($SiteId -match 'TriangleCollisionDebugComponent') { return 'triangle' }
    if ($SiteId -match 'SceneSweeperDebugComponent') { return 'sweeper' }
    throw "Unknown owner for site $SiteId"
}
function Get-TargetValue($Control,[string]$State) {
    $base = $script:baselines[[string]$Control.alias]
    if ($Control.kind -eq 'bool') {
        if ($State -ceq 'positive' -and $null -ne $Control.PSObject.Properties['positive']) { return [bool]$Control.positive }
        if ($State -ceq 'negative' -and $null -ne $Control.PSObject.Properties['negative']) { return [bool]$Control.negative }
        return [bool]$base
    }
    if ($State -ceq 'restore') { return $base }
    if ($Control.kind -eq 'int') {
        $min = [int]$Control.min; $max = [int]$Control.max
        if ($State -ceq 'positive') { return [int]$(if ([int]$base -lt $max) {[int]$base+1} else {[int]$base-1}) }
        $negative = if ([int]$base -eq $max) {[int]$base-2} elseif ([int]$base -eq $min) {[int]$base+2} else {[int]$base-1}
        if ($negative -lt $min -or $negative -gt $max -or $negative -eq $base) { throw 'No distinct valid negative map level exists.' }
        return [int]$negative
    }
    if ($State -ceq 'positive' -and $null -ne $Control.PSObject.Properties['positive']) { return [double]$Control.positive }
    if ($State -ceq 'negative' -and $null -ne $Control.PSObject.Properties['negative']) { return [double]$Control.negative }
    $step = [double]$Control.step
    if ($State -ceq 'positive') { return [double]$base + $step }
    return [double]$base - $step
}
function Witness-Matches([object]$Row,$Control,$Target) {
    $field = Get-FieldForAlias ([string]$Control.alias)
    $actualText = Find-Field $Row.Fields $field
    if ($null -eq $actualText) { return $false }
    if ($Control.kind -eq 'bool') {
        $wantedBit = if ([bool]$Target) {'1'} else {'0'}
        return ($actualText -ceq $wantedBit)
    }
    $actual = 0.0
    if (![double]::TryParse($actualText,[Globalization.NumberStyles]::Float,[Globalization.CultureInfo]::InvariantCulture,[ref]$actual)) { return $false }
    if ($Control.alias -ceq 'MapLvl') {
        return ([int]$actual -eq [int]$Target -and [int]$Row.Fields['map_levels'] -eq [int]$Target)
    }
    return (Scalar-Equal $actual $Target 'float')
}
function Wait-ControlWitness($Control,$Target,[string]$OwnerName,[int]$AfterIndex,[bool]$RequireFresh,[int]$Seconds=6) {
    $until = [DateTime]::UtcNow.AddSeconds($Seconds)
    while ([DateTime]::UtcNow -lt $until) {
        Assert-Owner
        $rows = @(Get-WitnessRows | Where-Object { $_.Fields['owner'] -ceq $OwnerName })
        if ($RequireFresh) { $rows = @($rows | Where-Object { $_.LogIndex -gt $AfterIndex }) }
        $matches = @($rows | Where-Object { Witness-Matches $_ $Control $Target })
        if ($matches.Count -gt 0) { return $matches[-1] }
        Start-Sleep -Milliseconds 100
    }
    throw "Typed owner did not report $($Control.alias) at requested value $(Format-Scalar $Target $Control.kind)."
}
function Get-CurrentFrames {
    if (!(Test-Path -LiteralPath $FrameDir -PathType Container)) { return @() }
    return @(Get-ChildItem -LiteralPath $FrameDir -File -Filter 'bb_*.bmp' | Sort-Object Name)
}
function Get-FrameRequestEvent {
    Assert-Owner
    if ($null -eq $script:frameRequestEvent) {
        $name = 'Local\BurnoutPC_FrameRequest_{0}_{1}' -f ([int]$script:owner.pid),$Slot
        $script:frameRequestEvent = [Threading.EventWaitHandle]::new($false,[Threading.EventResetMode]::ManualReset,$name)
        if ($script:frameRequestEvent.SafeWaitHandle.IsInvalid) { throw 'Could not create the PID/slot-scoped frame request event.' }
    }
    return $script:frameRequestEvent
}
function Capture-State([string]$Label,[DateTime]$StartedUtc) {
    $request = Get-FrameRequestEvent
    $sequence = $script:frameRequestSequence + 1
    $startIndex = Log-Count
    Say ('FRAME_REQUEST label=' + $Label + ' pid=' + $script:owner.pid + ' slot=' + $Slot + ' sequence=' + $sequence)
    $request.Reset() | Out-Null
    Assert-Owner
    if (!$request.Set()) { throw 'Could not signal the private frame request.' }
    $until = [DateTime]::UtcNow.AddSeconds(12)
    $ack = $null
    while ([DateTime]::UtcNow -lt $until) {
        Assert-Owner; Pump-Log
        for ($i=$startIndex; $i -lt $script:logLines.Count; ++$i) {
            if ($script:logLines[$i] -match '^\[frame-request\] pid=(\d+) slot=(\d+) seq=(\d+) present=(\d+) file=(bb_\d{6}\.bmp)$') {
                if ([int]$Matches[1] -ne [int]$script:owner.pid -or [int]$Matches[2] -ne $Slot -or [int]$Matches[3] -ne $sequence) {
                    throw 'Frame request acknowledgement belongs to a different process, slot, or sequence.'
                }
                $ack = [pscustomobject]@{Pid=[int]$Matches[1];Slot=[int]$Matches[2];Sequence=[int]$Matches[3];Present=[int]$Matches[4];Name=[string]$Matches[5];LogIndex=$i+1}
                break
            }
        }
        if ($null -ne $ack) { break }
        Start-Sleep -Milliseconds 100
    }
    if ($null -eq $ack) { throw "The exact game did not acknowledge requested frame $sequence for $Label." }
    if ($request.WaitOne(0)) { throw 'Game acknowledged a frame without retiring the named request event.' }
    $framePath = Join-Path $FrameDir $ack.Name
    $fileDeadline = [DateTime]::UtcNow.AddSeconds(3)
    while (!(Test-Path -LiteralPath $framePath -PathType Leaf) -and [DateTime]::UtcNow -lt $fileDeadline) { Assert-Owner; Start-Sleep -Milliseconds 50 }
    if (!(Test-Path -LiteralPath $framePath -PathType Leaf)) { throw "Acknowledged frame file is missing: $($ack.Name)" }
    $frame = Get-Item -LiteralPath $framePath
    if ($frame.Length -le 54) { throw "Acknowledged frame is incomplete: $($ack.Name)" }
    $allFrames = @(Get-CurrentFrames)
    if ($allFrames.Count -gt 96) { throw 'Frame dump exceeded the hard96-frame case cap.' }
    $script:framesWritten = $allFrames.Count
    $sha = (Get-FileHash -LiteralPath $framePath -Algorithm SHA256).Hash.ToLowerInvariant()
    $script:frameRequestSequence = $sequence
    Say ('FRAME_ACK label=' + $Label + ' present=' + $ack.Present + ' file=' + $ack.Name + ' sha256=' + $sha)
    return [ordered]@{label=$Label;requested_utc=$StartedUtc.ToString('o');pid=$ack.Pid;slot=$ack.Slot;sequence=$ack.Sequence;present=$ack.Present;ack_log_index=$ack.LogIndex;frames=@([ordered]@{name=$frame.Name;sha256=$sha;bytes=$frame.Length;mtime_utc=$frame.LastWriteTimeUtc.ToString('o')})}
}
function Write-Manifest([string]$Status,[string]$Reason='') {
    $sites = @()
    foreach ($control in $controls) {
        $id = [string]$control.site_id
        if ($script:siteResults.ContainsKey($id)) { $sites += $script:siteResults[$id] }
        else { $sites += [ordered]@{site_id=$id;alias=$control.alias;caption=$control.caption;status='deferred_prerequisite';reason=$(if($script:deferred.ContainsKey($id)){$script:deferred[$id]}else{'not scheduled'});states=@()} }
    }
    [ordered]@{
        schema=1;status=$Status;reason=$Reason;group=$Group;candidate_source=$planRoot.candidate_source
        candidate_tree=$planRoot.candidate_tree;probe_patch_sha256=$planRoot.probe_patch_sha256
        execution_exe_sha256=$ExpectedExeSha256;slot=$Slot;site_count=16
        site_state_action_count=$script:siteStates.Count;frame_count=$script:framesWritten
        baseline_capture=$script:baselineCapture
        preflight=[ordered]@{triangle_owner=$script:trianglePreflight;sweeper_owner=$script:sweeperPreflight}
        support_states=@($script:supportStates.ToArray());sites=$sites
        visual_review='awaiting Root image review; this file does not assign inventory status'
        lazy_sphere_state='source-initialized position is retained as the original component owns it; no offset reset is attempted'
    } | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
}
function Defer-WithoutStimulus([string]$Reason) {
    Write-Manifest 'deferred_prerequisites' $Reason
    Say ('RESULT DEFERRED: ' + $Reason)
}

try {
    if ($SetupCommand -notmatch '^geom_[A-Za-z0-9_]+$') { throw 'Unsafe setup command name.' }
    $lines = @(Get-Content -LiteralPath $StepsFile | Where-Object { $_ -match '^(SITE|SUPPORT)\|' })
    $siteLines = @($lines | Where-Object { $_ -match '^SITE\|' })
    $supportLines = @($lines | Where-Object { $_ -match '^SUPPORT\|' })
    if ($siteLines.Count -ne 48 -or $supportLines.Count -ne 2) { throw 'Schedule is not the exact48-site-state+2-support full16 plan.' }
    foreach ($line in $siteLines) {
        $parts = $line -split '\|',4
        if ($parts.Count -ne 4 -or !$controlBySite.ContainsKey($parts[1]) -or $controlBySite[$parts[1]].alias -cne $parts[3] -or $parts[2] -cnotin @('positive','negative','restore')) {
            throw "Malformed or unbound site schedule row: $line"
        }
    }

    Say ('WAIT expected_image=' + $image + ' started_after=' + $launchFloor.ToString('o'))
    while ($true) {
        Check-Deadline
        $games = @(Get-CimInstance Win32_Process -Filter "Name LIKE 'Burnout%.exe' OR Name='TUB_Burnout_PC_External.exe'")
        if ($games.Count -gt 1) { throw 'Multiple/foreign game processes before adoption.' }
        if ($games.Count -eq 1) {
            $c = $games[0]
            if (!$c.ExecutablePath -or [IO.Path]::GetFullPath($c.ExecutablePath) -ine $image) { throw 'Foreign game present before adoption.' }
            $p = [Diagnostics.Process]::GetProcessById([int]$c.ProcessId)
            if ($p.StartTime.ToUniversalTime() -lt $launchFloor) { throw 'Expected image belongs to a stale process.' }
            if ((Get-FileHash -LiteralPath $image -Algorithm SHA256).Hash.ToLowerInvariant() -cne $ExpectedExeSha256) { throw 'Staged image hash changed.' }
            $script:owner = [ordered]@{pid=$p.Id;image=$image;start_utc=$p.StartTime.ToUniversalTime().ToString('o');
                start_utc_ticks=$p.StartTime.ToUniversalTime().Ticks.ToString();exe_sha256=$ExpectedExeSha256;slot=$Slot;
                helper_start_utc=$timerStart.ToString('o');launch_floor_utc=$launchFloor.ToString('o')}
            $script:owner | ConvertTo-Json | Set-Content -LiteralPath $ownerPath -Encoding UTF8
            break
        }
        Start-Sleep -Milliseconds 200
    }
    while (!(Test-Path -LiteralPath $GameLog -PathType Leaf) -or (Get-Item -LiteralPath $GameLog).LastWriteTimeUtc -lt $launchFloor) { Assert-Owner; Start-Sleep -Milliseconds 200 }
    Pump-Log
    Wait-LogRegex 'CarSelectManager: streaming complete -- signalling StreamingFinished' 180
    Wait-LogRegex 'CarSelectManager: Exit state is finished' 180
    $setupFloor = Log-Count
    Tap-Key 192
    Type-Text ('exec ' + $SetupCommand)
    Tap-Key 13
    Tap-BoundedPause 350
    Tap-Key 192

    # Capture all original alias values before any site control is changed.
    $initial = @{}
    foreach ($control in $controls) {
        $r = Read-AliasValue ([string]$control.alias) ([string]$control.path) $setupFloor
        $v = Parse-Scalar $r.Text ([string]$control.kind)
        $initial[[string]$control.alias] = $v
        $baselines[[string]$control.alias] = $v
        $currentValues[[string]$control.alias] = $v
    }
    if ($aliasPaths.ContainsKey('MapMem')) {
        $r = Read-AliasValue 'MapMem' 'World/Collision/Spacial map memory use' $setupFloor
        $initial['MapMem'] = Parse-Scalar $r.Text 'int'
        $baselines['MapMem'] = $initial['MapMem']
    }
    $baselines['TrSweep'] = [bool]$initial['TrSweep']

    # First eligibility pass: only component-owned observations may open a site.
    $triangleRow = Wait-OwnerRow 'triangle' 20
    $script:trianglePreflight = $triangleRow
    $triangleReady = $false
    if ($triangleRow -and [int]$triangleRow.Fields['soup_lists'] -gt 0) { $triangleReady = $true }
    if (!$triangleReady) {
        $triangleRow = Wait-OwnerRow 'triangle' 10 { param($r) [int]$r.Fields['soup_lists'] -gt 0 }
        if ($triangleRow -and [int]$triangleRow.Fields['soup_lists'] -gt 0) { $triangleReady = $true; $script:trianglePreflight=$triangleRow }
    }
    $sweeperRow = Wait-OwnerRow 'sweeper' 20
    $script:sweeperPreflight = $sweeperRow
    $dynamicReady = ($null -ne $sweeperRow -and [int]$sweeperRow.Fields['owner_ready'] -eq 1 -and [int]$sweeperRow.Fields['dynamic_intervals'] -gt 0)
    $inactiveReady = ($null -ne $sweeperRow -and [int]$sweeperRow.Fields['owner_ready'] -eq 1 -and [int]$sweeperRow.Fields['inactive_intervals'] -gt 0)
    if (!$dynamicReady -or !$inactiveReady) {
        $sweeperRow = Wait-OwnerRow 'sweeper' 10 { param($r) [int]$r.Fields['owner_ready'] -eq 1 -and [int]$r.Fields['dynamic_intervals'] -gt 0 -and [int]$r.Fields['inactive_intervals'] -gt 0 }
        if ($sweeperRow) {
            $script:sweeperPreflight = $sweeperRow
            $dynamicReady = ([int]$sweeperRow.Fields['owner_ready'] -eq 1 -and [int]$sweeperRow.Fields['dynamic_intervals'] -gt 0)
            $inactiveReady = ([int]$sweeperRow.Fields['owner_ready'] -eq 1 -and [int]$sweeperRow.Fields['inactive_intervals'] -gt 0)
        }
    }

    $eligibleSiteIds = @{}
    foreach ($control in $controls) {
        $id = [string]$control.site_id
        if ($control.site_id -match 'TriangleCollisionDebugComponent') {
            if ($triangleReady) { $eligibleSiteIds[$id] = $true } else { $deferred[$id] = 'Triangle owner did not report a nonempty live soup list before stimulus.' }
        } elseif ($id -match '#0001$') {
            if ($dynamicReady) { $eligibleSiteIds[$id] = $true } else { $deferred[$id] = 'Typed dynamic interval list is empty or owner dispatch is absent.' }
        } elseif ($id -match '#0002$') {
            if ($inactiveReady) { $eligibleSiteIds[$id] = $true } else { $deferred[$id] = 'Typed inactive/frozen interval list is empty or owner dispatch is absent.' }
        } else {
            if ($dynamicReady -or $inactiveReady) { $eligibleSiteIds[$id] = $true } else { $deferred[$id] = 'Both typed SceneSweeper interval lists are empty or owner dispatch is absent.' }
        }
    }
    if ($eligibleSiteIds.Count -eq 0) {
        Defer-WithoutStimulus 'No required live owner dataset was nonempty; no site input was sent.'
        exit 0
    }

    # Read-only source initialization uses the genuine component owner and is retained for later sites.
    if ($triangleReady) {
        $supportStart = Log-Count
        Say 'SUPPORT sweep-test=TRUE begin: initialize the original lazy sphere position'
        Tap-Key 113 # F2: support_on.txt, which rebinds F2 to readback.txt
        $supportRead = Read-AliasValue 'TrSweep' $aliasPaths['TrSweep'] $supportStart
        if ($supportRead.Text -cne 'TRUE') { throw 'Support sweep toggle did not read back TRUE.' }
        $currentValues['TrSweep'] = $true
        $supportChanged = !$baselines['TrSweep']
        $initRow = Wait-OwnerRow 'triangle' 8 { param($r) [int]$r.Fields['sweep_test'] -eq 1 } $supportStart $supportChanged
        if (!$initRow -or [int]$initRow.Fields['soup_lists'] -lt 1) { throw 'No live nonempty triangle owner row after lazy sphere initialization.' }
        Tap-Key 113 # F2 is now the original alias readback script.
        $readStart = Log-Count
        foreach ($alias in @('SpX','SpY','SpZ','SpRad','SpVX','SpVY','SpVZ')) {
            $control = $controlByAlias[$alias]
            $r = Read-AliasValue $alias ([string]$control.path) $readStart
            $baselines[$alias] = Parse-Scalar $r.Text 'float'
            $field = Get-FieldForAlias $alias
            if ($alias -in @('SpX','SpY','SpZ')) {
                if (!(Scalar-Equal $baselines[$alias] ([double]$initRow.Fields[$field]) 'float')) { throw "Lazy source value for $alias disagrees between alias and typed owner." }
            } elseif (!(Scalar-Equal $baselines[$alias] $initial[$alias] 'float')) {
                throw "Non-position source value $alias changed during lazy initialization."
            }
            $currentValues[$alias] = $baselines[$alias]
        }
        $supportStates.Add([ordered]@{name='sweep-test support on';value=$supportRead.Text;owner_sample=$initRow.Fields.sample;purpose='source-authored lazy initialization; not a site credit'})
        $supportFrame = Capture-State 'SUPPORT-triangle-sweep-test-on' ([DateTime]::UtcNow)
        $supportStates[$supportStates.Count-1] = [ordered]@{name='sweep-test support on';value=$supportRead.Text;owner_sample=$initRow.Fields.sample;capture=$supportFrame;purpose='source-authored lazy initialization; not a site credit'}
    }

    # Validate captured baselines against source-owned constructor defaults where the plan pins one.
    foreach ($control in $controls) {
        $id = [string]$control.site_id
        if (!$eligibleSiteIds.ContainsKey($id) -or $null -eq $control.PSObject.Properties['baseline_expected']) { continue }
        if ([math]::Abs([double]$baselines[[string]$control.alias] - [double]$control.baseline_expected) -gt 0.0005) {
            throw "Captured baseline for $($control.alias) differs from the current source constructor value."
        }
    }
    foreach ($control in $controls) {
        if ($control.kind -eq 'int' -and $eligibleSiteIds.ContainsKey([string]$control.site_id)) {
            if ([int]$baselines[[string]$control.alias] -lt [int]$control.min -or [int]$baselines[[string]$control.alias] -gt [int]$control.max) {
                throw 'Captured spatial-map level is outside the original registered range1..8.'
            }
        }
    }

    # Filter only by the source owner gates. No call opens an empty list or invents a physics input.
    $events = [Collections.Generic.List[object]]::new()
    foreach ($line in $lines) {
        $parts = $line -split '\|',4
        if ($parts[0] -ceq 'SUPPORT') {
            if ($triangleReady -and $parts[2] -ceq 'TRUE') { continue } # already applied for the typed lazy-init preflight
            if ($triangleReady) { $events.Add([pscustomobject]@{Kind='SUPPORT';Alias=$parts[1];State=$parts[2];Purpose=$parts[3]}) }
            continue
        }
        $id = $parts[1]
        if ($eligibleSiteIds.ContainsKey($id)) { $events.Add([pscustomobject]@{Kind='SITE';SiteId=$id;State=$parts[2];Alias=$parts[3]}) }
    }
    if ($events.Count -lt 1) { Defer-WithoutStimulus 'No eligible schedule rows remained after owner gates.'; exit 0 }
    $siteEvents = @($events | Where-Object { $_.Kind -ceq 'SITE' })
    if (@($siteEvents | Group-Object SiteId | Where-Object { $_.Count -ne 3 }).Count -ne 0) { throw 'Every exercised site must have positive, negative and restore rows.' }

    # Prebuild the entire site chain. Each file emits one actual alias readback, then rebinds F1 to the next site.
    $relativeRun = $RunRelativePath.Replace('\','/')
    $actionByEvent = @{}
    $siteOrdinal = 0
    foreach ($event in $events) {
        if ($event.Kind -ne 'SITE') { continue }
        ++$siteOrdinal
        $control = $controlBySite[[string]$event.SiteId]
        $target = Get-TargetValue $control ([string]$event.State)
        $valueText = Format-Scalar $target ([string]$control.kind)
        $fileName = ('action_{0:D2}.txt' -f $siteOrdinal)
        $filePath = Join-Path $OutDir $fileName
        $commands = [Collections.Generic.List[string]]::new()
        $commands.Add(('set "' + $control.alias + '" ' + $valueText))
        $commands.Add(('alias "' + $control.alias + '"'))
        $commands.Add([string]$control.alias)
        if ($control.paired_alias) { $commands.Add(('alias "' + $control.paired_alias + '"')); $commands.Add([string]$control.paired_alias) }
        $next = $siteOrdinal + 1
        if ($next -le $siteEvents.Count) { $commands.Add(('bind F1 exec "' + $relativeRun + '/action_' + ('{0:D2}' -f $next) + '.txt"')) }
        Set-Content -LiteralPath $filePath -Value $commands -Encoding ascii
        $actionByEvent[([string]$event.SiteId + '|' + [string]$event.State)] = [pscustomobject]@{Control=$control;Target=$target;TargetText=$valueText;File=$fileName;Ordinal=$siteOrdinal}
    }
    $restoreText = Format-Scalar $baselines['TrSweep'] 'bool'
    Set-Content -LiteralPath (Join-Path $OutDir 'support_restore.txt') -Value @(
        ('set "TrSweep" ' + $restoreText),'alias "TrSweep"','TrSweep'
    ) -Encoding ascii

    # Capture baseline before the first site value changes.
    $baselineCapture = Capture-State 'baseline-before-first-site' ([DateTime]::UtcNow)
    $script:baselineCapture = $baselineCapture
    $siteResultsForCapture = @{}
    foreach ($control in $controls) {
        $id = [string]$control.site_id
        $siteResultsForCapture[$id] = [ordered]@{site_id=$id;alias=$control.alias;caption=$control.caption;status=$(if($eligibleSiteIds.ContainsKey($id)){'machine_evidence_awaiting_root_visual_review'}else{'deferred_prerequisite'});reason=$(if($deferred.ContainsKey($id)){$deferred[$id]}else{''});baseline=(Format-Scalar $baselines[[string]$control.alias] ([string]$control.kind));visual_intent=$control.visual;states=@()}
    }
    foreach ($control in $controls) { $siteResults[[string]$control.site_id] = $siteResultsForCapture[[string]$control.site_id] }

    $cursor = Log-Count
    $lastSiteIndex = -1
    foreach ($event in $events) {
        Assert-Owner
        if ($event.Kind -ceq 'SUPPORT') {
            $started = [DateTime]::UtcNow
            if ($event.State -ceq 'TRUE') {
                Say ('SUPPORT sweep-test=TRUE begin: ' + $event.Purpose)
                Tap-Key 113
                $read = Read-AliasValue 'TrSweep' $aliasPaths['TrSweep'] $cursor
                if ($read.Text -cne 'TRUE') { throw 'The sphere support toggle failed its actual alias readback.' }
                $cursor = $read.LogIndex
                $row = Wait-OwnerRow 'triangle' 8 { param($r) [int]$r.Fields['sweep_test'] -eq 1 -and [int]$r.Fields['soup_lists'] -gt 0 }
                if (!$row) { throw 'Triangle owner did not retain the nonempty map with the source sweep enabled.' }
                $capture = Capture-State 'SUPPORT-sweep-test-on' $started
                $supportStates.Add([ordered]@{name='sweep-test-on';value='TRUE';owner_sample=$row.Fields.sample;capture=$capture;purpose=$event.Purpose})
                $cursor = Log-Count
                Tap-Key 113
                foreach ($alias in @('SpX','SpY','SpZ','SpRad','SpVX','SpVY','SpVZ')) {
                    $control = $controlByAlias[$alias]
                    $read = Read-AliasValue $alias ([string]$control.path) $cursor
                    $actual = Parse-Scalar $read.Text 'float'
                    if (!(Scalar-Equal $actual $baselines[$alias] 'float')) { throw "Source-initialized baseline changed while re-reading $alias." }
                    $cursor = $read.LogIndex
                }
            } else {
                Say ('SUPPORT sweep-test=baseline begin: ' + $event.Purpose)
                $supportRestoreStart = Log-Count
                Tap-Key 114
                $read = Read-AliasValue 'TrSweep' $aliasPaths['TrSweep'] $cursor
                $expected = Format-Scalar $baselines['TrSweep'] 'bool'
                if ($read.Text -cne $expected) { throw 'Support cleanup did not restore the captured original sweep-toggle value.' }
                $supportRestoreChanged = ([bool]$currentValues['TrSweep'] -ne [bool]$baselines['TrSweep'])
                $currentValues['TrSweep'] = [bool]$baselines['TrSweep']
                $cursor = $read.LogIndex
                $expectedSweepBit = if ($expected -ceq 'TRUE') {'1'} else {'0'}
                $row = Wait-OwnerRow 'triangle' 6 { param($r) $r.Fields['sweep_test'] -ceq $expectedSweepBit } $supportRestoreStart $supportRestoreChanged
                if ($supportRestoreChanged -and !$row) { throw 'Triangle owner did not report the restored support toggle after its change.' }
                $capture = Capture-State 'SUPPORT-sweep-test-restored' $started
                $supportStates.Add([ordered]@{name='sweep-test-restored';value=$expected;owner_sample=$(if($row){$row.Fields.sample}else{''});capture=$capture;purpose=$event.Purpose})
                $cursor = Log-Count
            }
            continue
        }

        $entry = $actionByEvent[([string]$event.SiteId + '|' + [string]$event.State)]
        $control = $entry.Control
        $target = $entry.Target
        $expectedText = $entry.TargetText
        $oldValue = $currentValues[[string]$control.alias]
        $changed = !(Scalar-Equal $oldValue $target ([string]$control.kind))
        $stateStart = [DateTime]::UtcNow
        Say ('SITE ' + $event.SiteId + ' STATE ' + $event.State + ' BEGIN alias=' + $event.Alias + ' expected=' + $expectedText)
        $beforeKey = Log-Count
        Tap-Key 112 # F1 is rebound by each action file to the next scheduled site row.
        $read = Read-AliasValue ([string]$control.alias) ([string]$control.path) $beforeKey
        $actual = Parse-Scalar $read.Text ([string]$control.kind)
        if (!(Scalar-Equal $actual $target ([string]$control.kind))) { throw "Actual $($control.alias) readback '$($read.Text)' differs from requested '$expectedText'." }
        $cursor = $read.LogIndex
        $ownerName = Get-OwnerForSite ([string]$event.SiteId)
        $ownerRow = Wait-ControlWitness $control $target $ownerName $beforeKey $changed 6
        if ($ownerName -ceq 'triangle' -and [int]$ownerRow.Fields['soup_lists'] -lt 1) { throw 'Nonempty soup gate disappeared during a dependent Triangle site.' }
        if ($ownerName -ceq 'sweeper') {
            if ([int]$ownerRow.Fields['owner_ready'] -ne 1) { throw 'SceneSweeper typed owner disappeared during its site.' }
            if ($control.alias -ceq 'SwDyn' -and [int]$ownerRow.Fields['dynamic_intervals'] -lt 1) { throw 'Dynamic intervals became empty during the site.' }
            if ($control.alias -ceq 'SwFrz' -and [int]$ownerRow.Fields['inactive_intervals'] -lt 1) { throw 'Inactive intervals became empty during the site.' }
            if ($control.alias -ceq 'SwDist' -and ([int]$ownerRow.Fields['dynamic_intervals'] + [int]$ownerRow.Fields['inactive_intervals']) -lt 1) { throw 'Both interval lists became empty during draw-distance testing.' }
        }
        $paired = $null
        if ($control.alias -ceq 'MapLvl') {
            $levels = Wait-ControlWitness $control $target 'triangle' $beforeKey $changed 8
            if ([int]$levels.Fields['map_levels'] -ne [int]$target) { throw 'Live spatial map did not rebuild to the requested level.' }
            $mapReadStart = Log-Count
            Tap-Key 113 # F2 was rebound to the original alias readback script after lazy setup.
            $mem = Read-AliasValue 'MapMem' $aliasPaths['MapMem'] $mapReadStart
            $paired = Parse-Scalar $mem.Text 'int'
            $cursor = $mem.LogIndex
        }
        $capture = Capture-State (($event.SiteId + '/' + $event.State)) $stateStart
        $currentValues[[string]$control.alias] = $target
        $field = Get-FieldForAlias ([string]$control.alias)
        $stateRecord = [ordered]@{
            state=[string]$event.State;requested=$expectedText;actual=$read.Text;baseline=(Format-Scalar $baselines[[string]$control.alias] ([string]$control.kind))
            owner=$ownerName;owner_sample=$ownerRow.Fields.sample;owner_log_index=$ownerRow.LogIndex;owner_tuple_changed=$changed
            paired_memory_use=$paired;capture=$capture;site_evidence='awaiting Root visual comparison'
        }
        $siteResults[[string]$event.SiteId].states = @($siteResults[[string]$event.SiteId].states) + @($stateRecord)
        $siteStates.Add([ordered]@{site_id=[string]$event.SiteId;state=[string]$event.State;alias=[string]$control.alias;field=$field;actual=$read.Text;capture=$capture;owner_sample=$ownerRow.Fields.sample})
        Say ('SITE ' + $event.SiteId + ' STATE ' + $event.State + ' END frame_count=' + $capture.frames.Count + ' owner_sample=' + $ownerRow.Fields.sample)
        $cursor = Log-Count
    }

    # The source lazy sphere coordinates are deliberately retained; only registered controls are restored.
    foreach ($control in $controls) {
        $id = [string]$control.site_id
        if (!$eligibleSiteIds.ContainsKey($id)) { continue }
        $stateRows = @($siteResults[$id].states)
        if ($stateRows.Count -ne 3 -or $stateRows[-1].state -cne 'restore') { throw "Site $id did not complete its distinct restore state." }
        if (!(Scalar-Equal (Parse-Scalar $stateRows[-1].actual ([string]$control.kind)) $baselines[[string]$control.alias] ([string]$control.kind))) { throw "Site $id did not restore its captured alias value." }
    }
    $trSweepExpected = Format-Scalar $baselines['TrSweep'] 'bool'
    if ($triangleReady) {
        $finalCursor = Log-Count
        Tap-Key 113
        $trSweepFinal = Read-AliasValue 'TrSweep' $aliasPaths['TrSweep'] $finalCursor
        if ($trSweepFinal.Text -cne $trSweepExpected) { throw 'Final test-toggle state differs from the captured original.' }
    }
    Write-Manifest 'machine_evidence_ready_for_root_visual_review'
    Say ('RESULT DONE site_actions=' + $siteStates.Count + ' frames=' + $script:framesWritten + ' deferred_sites=' + $deferred.Count)
    exit 0
} catch {
    Say ('RESULT FAIL: ' + $_.Exception.Message)
    Write-Manifest 'helper_failed' $_.Exception.Message
    exit 1
} finally {
    if ($frameRequestEvent) { try { $frameRequestEvent.Reset() | Out-Null; $frameRequestEvent.Dispose() } catch {} }
    foreach ($handle in $keys.Values) { try { $handle.Reset() | Out-Null; $handle.Dispose() } catch {} }
}
