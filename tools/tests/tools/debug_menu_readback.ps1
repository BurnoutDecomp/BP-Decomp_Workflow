param(
    [Parameter(Mandatory=$true)][string]$LogPath,
    [Parameter(Mandatory=$true)][string]$PlanPath,
    [Parameter(Mandatory=$true)][string]$OutputPath
)

# Parse only native ScriptInterface::OutputMessage lines from BrnGame.log. The
# plan contains identities and paths, never expected values. Each phase is
# bracketed by two queries of its own native action alias; all pv path/value
# outputs must fall inside exactly one such observed interval.

$laProblems = [System.Collections.Generic.List[string]]::new()
$laActionObservations = @()
$laMarkerObservations = @()
$laProbeObservations = @()
$laLogLines = @()
$laSourceLineNumbers = [System.Collections.Generic.List[int]]::new()
$laIgnoredDiagnosticLines = [System.Collections.Generic.List[int]]::new()
$laPlan = $null

if (!(Test-Path -LiteralPath $LogPath)) { $laProblems.Add("missing game log: $LogPath") }
if (!(Test-Path -LiteralPath $PlanPath)) { $laProblems.Add("missing readback plan: $PlanPath") }

if ($laProblems.Count -eq 0) {
    $laPlan = Get-Content -LiteralPath $PlanPath -Raw | ConvertFrom-Json
    $laSourceLines = [IO.File]::ReadAllLines($LogPath)
    $laFilteredLines = [System.Collections.Generic.List[string]]::new()
    # These native renderer diagnostics can interleave on another thread.
    # Their grammars are not values of this case's bool/numeric/enum cells.
    # Keep their raw line positions and reject every other unexpected output.
    $lsRendererDiagnostic = '^\[lionfx\] Render: emitters live=\d+ cell=\d+ inactive=\d+ culled=\d+ \(range=\d+ frustum=\d+ near=\d+\) drawn=\d+ particles=\d+ nocull=[01]$'
    $lsMeshDiagnostic = '^\[FLAG PC bring-up\] MESH lists:(?: \[\d+\]=\d+)+$'
    $lsDispatchDiagnostic = '^\[lionfx\] Dispatch: batches=\d+ vb=[0-9A-Fa-f]{16} white=\d+\.\d{3}$'
    $lsBlendDiagnostic = '^\[lionblend\] call=\d+ layer=-?\d+->-?\d+ t=-?\d+\.\d{4} diff\(s12/v4/c3\)=\d+/\d+/\d+' +
        ' life=-?\d+\.\d{4}\|-?\d+\.\d{4}->-?\d+\.\d{4} size=-?\d+\.\d{4}\|-?\d+\.\d{4}->-?\d+\.\d{4}' +
        ' rate=-?\d+\.\d{3}\|-?\d+\.\d{3}->-?\d+\.\d{3} vel\.y=-?\d+\.\d{4}\|-?\d+\.\d{4}->-?\d+\.\d{4}' +
        ' col0=[0-9A-Fa-f]{8}\|[0-9A-Fa-f]{8}->[0-9A-Fa-f]{8} flags=[0-9A-Fa-f]{8}\|[0-9A-Fa-f]{8}->[0-9A-Fa-f]{8}$'
    for ($liSourceLine = 0; $liSourceLine -lt $laSourceLines.Count; ++$liSourceLine) {
        $lsSourceLine = $laSourceLines[$liSourceLine]
        if ($lsSourceLine -match $lsRendererDiagnostic -or $lsSourceLine -match $lsMeshDiagnostic -or
            $lsSourceLine -match $lsDispatchDiagnostic -or $lsSourceLine -match $lsBlendDiagnostic) {
            $laIgnoredDiagnosticLines.Add($liSourceLine + 1)
        } else {
            $laFilteredLines.Add($lsSourceLine)
            $laSourceLineNumbers.Add($liSourceLine + 1)
        }
    }
    $laLogLines = $laFilteredLines.ToArray()

    $laActionAliases = @($laPlan.action_alias_queries)
    $laActionNames = @($laActionAliases | ForEach-Object { [string]$_.alias })
    if (@($laActionNames | Select-Object -Unique).Count -ne $laActionNames.Count) {
        $laProblems.Add('duplicate action alias in plan')
    }

    foreach ($lrAction in $laActionAliases) {
        $lsPrefix = [string]$lrAction.alias + ': '
        $laMatches = @()
        for ($liLine = 0; $liLine -lt $laLogLines.Count; ++$liLine) {
            if ($laLogLines[$liLine].StartsWith($lsPrefix, [StringComparison]::Ordinal)) {
                $laMatches += @{ LineIndex=$liLine; Path=$laLogLines[$liLine].Substring($lsPrefix.Length) }
            }
        }

        $lbUnique = $laMatches.Count -eq 1
        $lsObservedPath = if ($lbUnique) { [string]$laMatches[0].Path } else { $null }
        $lbPathMatches = $lbUnique -and $lsObservedPath -ceq [string]$lrAction.expected_resolved_path
        if (!$lbUnique) {
            $laProblems.Add("action alias $($lrAction.alias): expected one resolved-path line, found $($laMatches.Count)")
        } elseif (!$lbPathMatches) {
            $laProblems.Add("action alias $($lrAction.alias): resolved path mismatch '$lsObservedPath'")
        }

        $laActionObservations += [ordered]@{
            id = $lrAction.id
            alias = $lrAction.alias
            expected_resolved_path = $lrAction.expected_resolved_path
            observed_resolved_path = $lsObservedPath
            unique = $lbUnique
            path_matches = $lbPathMatches
            log_line = if ($lbUnique) { $laMatches[0].LineIndex + 1 } else { $null }
        }
    }

    $laPhaseMarkers = @($laPlan.phase_markers)
    $laPhaseNames = @($laPhaseMarkers | ForEach-Object { [string]$_.phase })
    $laMarkerAliases = @($laPhaseMarkers | ForEach-Object { [string]$_.alias })
    if ($laPhaseMarkers.Count -ne [int]$laPlan.phase_count) {
        $laProblems.Add("phase marker count: expected $($laPlan.phase_count), found $($laPhaseMarkers.Count)")
    }
    if (@($laPhaseNames | Select-Object -Unique).Count -ne $laPhaseNames.Count) {
        $laProblems.Add('duplicate phase name in marker plan')
    }
    if (@($laMarkerAliases | Select-Object -Unique).Count -ne $laMarkerAliases.Count) {
        $laProblems.Add('duplicate phase marker alias in plan')
    }

    $laUsedAliases = @($laPlan.aliases_used | ForEach-Object { [string]$_ })
    if (@($laUsedAliases | Select-Object -Unique).Count -ne $laUsedAliases.Count) {
        $laProblems.Add('duplicate alias in aliases_used')
    }
    $laExpectedAliases = @('prreset','prplus','prminus','pv') + $laMarkerAliases
    $lsUsedAliasSet = (@($laUsedAliases | Sort-Object) -join '|')
    $lsExpectedAliasSet = (@($laExpectedAliases | Sort-Object) -join '|')
    if ($laUsedAliases.Count -gt [int]$laPlan.alias_capacity) {
        $laProblems.Add("alias capacity exceeded: used $($laUsedAliases.Count), capacity $($laPlan.alias_capacity)")
    }
    if ($laUsedAliases.Count -ne 17 -or $laPlan.alias_capacity -ne 40 -or
        @($laActionNames | Select-Object -Unique).Count -ne 3 -or $lsUsedAliasSet -cne $lsExpectedAliasSet) {
        $laProblems.Add('expected the bounded alias set: three action aliases, pv, and thirteen phase markers (17 of 40)')
    }

    $laAllMarkerRows = @()
    foreach ($lrMarker in $laPhaseMarkers) {
        $lsPrefix = [string]$lrMarker.alias + ': '
        $laMatches = @()
        for ($liLine = 0; $liLine -lt $laLogLines.Count; ++$liLine) {
            if ($laLogLines[$liLine].StartsWith($lsPrefix, [StringComparison]::Ordinal)) {
                $laMatches += @{ LineIndex=$liLine; Path=$laLogLines[$liLine].Substring($lsPrefix.Length) }
                $laAllMarkerRows += @{ LineIndex=$liLine; Alias=[string]$lrMarker.alias }
            }
        }

        $lbPair = $laMatches.Count -eq 2
        $lbPathsMatch = $lbPair -and
            $laMatches[0].Path -ceq [string]$lrMarker.expected_resolved_path -and
            $laMatches[1].Path -ceq [string]$lrMarker.expected_resolved_path
        $lbOrderValid = $lbPair -and $laMatches[0].LineIndex -lt $laMatches[1].LineIndex
        if (!$lbPair) {
            $laProblems.Add("phase $($lrMarker.phase): expected two native marker lines for $($lrMarker.alias), found $($laMatches.Count)")
        } elseif (!$lbPathsMatch) {
            $laProblems.Add("phase $($lrMarker.phase): marker resolved path mismatch")
        }

        $laMarkerObservations += [ordered]@{
            phase = $lrMarker.phase
            alias = $lrMarker.alias
            expected_resolved_path = $lrMarker.expected_resolved_path
            observed_resolved_paths = @($laMatches | ForEach-Object { $_.Path })
            unique_pair = $lbPair
            paths_match = $lbPathsMatch
            begin_log_line = if ($lbPair) { $laMatches[0].LineIndex + 1 } else { $null }
            end_log_line = if ($lbPair) { $laMatches[1].LineIndex + 1 } else { $null }
            order_valid = $lbOrderValid
        }
    }

    $lrBaselineMarker = $laMarkerObservations | Where-Object { $_.phase -ceq 'baseline' } | Select-Object -First 1
    if ($lrBaselineMarker -and $lrBaselineMarker.begin_log_line) {
        foreach ($lrActionObs in $laActionObservations) {
            if ($lrActionObs.log_line -and $lrActionObs.log_line -ge $lrBaselineMarker.begin_log_line) {
                $laProblems.Add("action alias $($lrActionObs.alias): query must precede the baseline phase marker")
            }
        }
    }

    # PS5.1 Sort-Object's named-property adapter does not sort Hashtable keys.
    $laAllMarkerRows = @($laAllMarkerRows | Sort-Object { [int]$_.LineIndex })
    $laExpectedMarkerSequence = @()
    foreach ($lrMarker in $laPhaseMarkers) {
        $laExpectedMarkerSequence += [string]$lrMarker.alias
        $laExpectedMarkerSequence += [string]$lrMarker.alias
    }
    if ($laAllMarkerRows.Count -ne $laExpectedMarkerSequence.Count) {
        $laProblems.Add("native phase marker output count: expected $($laExpectedMarkerSequence.Count), found $($laAllMarkerRows.Count)")
    }
    $liMarkerCompare = [Math]::Min($laAllMarkerRows.Count, $laExpectedMarkerSequence.Count)
    for ($liMarker = 0; $liMarker -lt $liMarkerCompare; ++$liMarker) {
        if ($laAllMarkerRows[$liMarker].Alias -cne $laExpectedMarkerSequence[$liMarker]) {
            $laProblems.Add("native phase marker order mismatch at marker output $($liMarker + 1)")
            break
        }
    }

    $laExpectedProbes = @($laPlan.probes)
    $laProbeKeys = @($laExpectedProbes | ForEach-Object { [string]$_.probe_key })
    if (@($laProbeKeys | Select-Object -Unique).Count -ne $laProbeKeys.Count) {
        $laProblems.Add('duplicate probe key in plan')
    }
    $laFieldPlans = @($laExpectedProbes | Where-Object { $_.role -eq 'field' })
    $laCallbackPlans = @($laExpectedProbes | Where-Object { $_.role -like 'callback-*' })
    if ($laFieldPlans.Count -ne 507 -or $laCallbackPlans.Count -ne 2 -or $laExpectedProbes.Count -ne 509) {
        $laProblems.Add("plan probe shape: expected 507 fields plus 2 callback reads, found $($laFieldPlans.Count)+$($laCallbackPlans.Count)")
    }
    foreach ($lrMarker in $laPhaseMarkers) {
        $laPhasePlan = @($laExpectedProbes | Where-Object { [string]$_.phase -ceq [string]$lrMarker.phase })
        $liExpectedPhaseCount = [int]$laPlan.variables_per_phase
        if ([string]$lrMarker.phase -ceq 'route-world-all') { $liExpectedPhaseCount += 2 }
        if ($laPhasePlan.Count -ne $liExpectedPhaseCount) {
            $laProblems.Add("plan phase $($lrMarker.phase): expected $liExpectedPhaseCount probes, found $($laPhasePlan.Count)")
        }
    }

    $laContainedPvLines = [System.Collections.Generic.HashSet[int]]::new()
    foreach ($lrMarker in $laPhaseMarkers) {
        $laMarkerObs = @($laMarkerObservations | Where-Object { $_.phase -ceq [string]$lrMarker.phase })
        if ($laMarkerObs.Count -ne 1 -or !$laMarkerObs[0].unique_pair) { continue }
        $liStartLine = [int]$laMarkerObs[0].begin_log_line - 1
        $liEndLine = [int]$laMarkerObs[0].end_log_line - 1
        if ($liStartLine -ge $liEndLine) {
            $laProblems.Add("phase $($lrMarker.phase): native marker interval is reversed or empty")
            continue
        }

        $laPhaseExpected = @($laExpectedProbes | Where-Object { [string]$_.phase -ceq [string]$lrMarker.phase })
        $liIntervalOutputCount = $liEndLine - $liStartLine - 1
        $liExpectedIntervalOutputCount = 2 * $laPhaseExpected.Count
        if ($liIntervalOutputCount -ne $liExpectedIntervalOutputCount) {
            $laProblems.Add("phase $($lrMarker.phase): expected $liExpectedIntervalOutputCount output lines inside native markers, found $liIntervalOutputCount")
        }
        $laPhasePvLines = @()
        for ($liLine = $liStartLine + 1; $liLine -lt $liEndLine; ++$liLine) {
            if ($laLogLines[$liLine].StartsWith('pv: ', [StringComparison]::Ordinal)) {
                $laPhasePvLines += $liLine
                [void]$laContainedPvLines.Add($liLine)
            }
        }

        if ($laPhasePvLines.Count -ne $laPhaseExpected.Count) {
            $laProblems.Add("phase $($lrMarker.phase): expected $($laPhaseExpected.Count) native pv path outputs, found $($laPhasePvLines.Count)")
        }

        $liPairs = [Math]::Min($laPhasePvLines.Count, $laPhaseExpected.Count)
        for ($liProbe = 0; $liProbe -lt $liPairs; ++$liProbe) {
            $lrPlanProbe = $laPhaseExpected[$liProbe]
            $liPathLine = $laPhasePvLines[$liProbe]
            $lsObservedPath = $laLogLines[$liPathLine].Substring(4)
            $liExpectedPathLine = $liStartLine + 1 + (2 * $liProbe)
            if ($liPathLine -ne $liExpectedPathLine) {
                $laProblems.Add("$($lrPlanProbe.probe_key): native path/value outputs are not in the planned phase order")
            }
            $lbPathMatches = $lsObservedPath -ceq [string]$lrPlanProbe.expected_resolved_path
            $liValueLine = $liPathLine + 1
            $lsRawValue = $null
            $lbValuePresent = $false

            if ($liValueLine -ge $liEndLine) {
                $laProblems.Add("$($lrPlanProbe.probe_key): missing value output inside phase marker interval")
            } elseif ($laLogLines[$liValueLine].StartsWith('pv: ', [StringComparison]::Ordinal) -or
                (@($laMarkerAliases | Where-Object { $laLogLines[$liValueLine].StartsWith(([string]$_)+': ', [StringComparison]::Ordinal) }).Count -gt 0)) {
                $laProblems.Add("$($lrPlanProbe.probe_key): missing no-argument value output before the next query/marker")
            } else {
                $lsRawValue = [string]$laLogLines[$liValueLine]
                $lbValuePresent = $lsRawValue.Length -gt 0
                if (!$lbValuePresent) { $laProblems.Add("$($lrPlanProbe.probe_key): empty GetValueAsString output") }
            }

            if (!$lbPathMatches) {
                $laProblems.Add("$($lrPlanProbe.probe_key): resolved path mismatch '$lsObservedPath'")
            }

            $laProbeObservations += [ordered]@{
                probe_key = $lrPlanProbe.probe_key
                phase = $lrPlanProbe.phase
                role = $lrPlanProbe.role
                id = $lrPlanProbe.id
                caption = $lrPlanProbe.caption
                lookup_path = $lrPlanProbe.lookup_path
                expected_resolved_path = $lrPlanProbe.expected_resolved_path
                observed_resolved_path = $lsObservedPath
                actual_value = $lsRawValue
                path_matches = $lbPathMatches
                value_present = $lbValuePresent
                path_log_line = $liPathLine + 1
                value_log_line = if ($lbValuePresent) { $liValueLine + 1 } else { $null }
            }
        }
    }

    $laAllPvLines = @()
    for ($liLine = 0; $liLine -lt $laLogLines.Count; ++$liLine) {
        if ($laLogLines[$liLine].StartsWith('pv: ', [StringComparison]::Ordinal)) { $laAllPvLines += $liLine }
    }
    if ($laAllPvLines.Count -ne $laExpectedProbes.Count) {
        $laProblems.Add("total pv output count: expected $($laExpectedProbes.Count), found $($laAllPvLines.Count)")
    }
    foreach ($liPvLine in $laAllPvLines) {
        if (!$laContainedPvLines.Contains([int]$liPvLine)) {
            $laProblems.Add("pv output at log line $($liPvLine + 1) is outside all native phase marker intervals")
        }
    }

    # Exact error text emitted by the original ScriptInterface command paths.
    # Do not classify arbitrary application logs or expected values as errors.
    $laErrorPattern = '^(Alias too long\. Max [0-9]+|Invalid alias name - no spaces|Too many aliases|Unknown alias value|expecting at least 1 parameter|Alias not found|Expected 1 parameters|Variable not found|Function not found|Expected 2 parameters|Variable .+ not found|Variable .+ is read only|Unknown command|Component not found|invalid function key: F1-F12|line too long or missing LF at end of file\. aborting!|Cannot open .+)$'
    $laCommandErrors = @($laLogLines | Where-Object { $_ -match $laErrorPattern })
    foreach ($lsError in $laCommandErrors) { $laProblems.Add("script command error: $lsError") }
}

# Parsing uses filtered positions internally; exported evidence always points at
# the original, unchanged game log, including diagnostics between probe outputs.
foreach ($lrAction in $laActionObservations) {
    if ($lrAction.log_line) { $lrAction.log_line = $laSourceLineNumbers[[int]$lrAction.log_line - 1] }
}
foreach ($lrMarker in $laMarkerObservations) {
    if ($lrMarker.begin_log_line) { $lrMarker.begin_log_line = $laSourceLineNumbers[[int]$lrMarker.begin_log_line - 1] }
    if ($lrMarker.end_log_line) { $lrMarker.end_log_line = $laSourceLineNumbers[[int]$lrMarker.end_log_line - 1] }
}
foreach ($lrProbe in $laProbeObservations) {
    if ($lrProbe.path_log_line) { $lrProbe.path_log_line = $laSourceLineNumbers[[int]$lrProbe.path_log_line - 1] }
    if ($lrProbe.value_log_line) { $lrProbe.value_log_line = $laSourceLineNumbers[[int]$lrProbe.value_log_line - 1] }
}
$lsStatus = if ($laProblems.Count -eq 0) { 'pass' } else { 'fail' }
$loObservation = [ordered]@{
    case = 'debug_menu_physical_route_batch'
    source_log = $LogPath
    source_log_sha256 = if (Test-Path -LiteralPath $LogPath) { (Get-FileHash -LiteralPath $LogPath -Algorithm SHA256).Hash.ToLowerInvariant() } else { $null }
    ignored_native_diagnostic_lines = @($laIgnoredDiagnosticLines)
    plan_file = $PlanPath
    status = $lsStatus
    alias_capacity = if ($laPlan) { $laPlan.alias_capacity } else { $null }
    aliases_used = if ($laPlan) { @($laPlan.aliases_used) } else { @() }
    expected_phase_marker_count = if ($laPlan) { @($laPlan.phase_markers).Count } else { 0 }
    observed_phase_marker_count = $laMarkerObservations.Count
    phase_markers = $laMarkerObservations
    expected_probe_count = if ($laPlan) { @($laPlan.probes).Count } else { 0 }
    observed_probe_count = $laProbeObservations.Count
    expected_action_alias_count = if ($laPlan) { @($laPlan.action_alias_queries).Count } else { 0 }
    observed_action_alias_count = $laActionObservations.Count
    action_aliases = $laActionObservations
    probes = $laProbeObservations
    problems = @($laProblems)
}

$lsOutputDirectory = Split-Path -Parent $OutputPath
if ($lsOutputDirectory -and !(Test-Path -LiteralPath $lsOutputDirectory)) {
    New-Item -ItemType Directory -Force -Path $lsOutputDirectory | Out-Null
}
$lsJson = $loObservation | ConvertTo-Json -Depth 8
[System.IO.File]::WriteAllText($OutputPath, $lsJson, [System.Text.UTF8Encoding]::new($false))

[pscustomobject]@{
    Pass = $lsStatus -eq 'pass'
    Detail = "status=$lsStatus probes=$($laProbeObservations.Count)/$(if($laPlan){@($laPlan.probes).Count}else{0}) markers=$($laMarkerObservations.Count)/$(if($laPlan){@($laPlan.phase_markers).Count}else{0}); problems=$($laProblems.Count)"
    OutputPath = $OutputPath
}
