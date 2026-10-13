param(
    [Parameter(Mandatory=$true)][string]$LogPath,
    [Parameter(Mandatory=$true)][string]$PlanPath,
    [Parameter(Mandatory=$true)][string]$OutputPath
)

# Every actual value in this file is copied from the game's original
# ScriptInterface::OutputMessage stream. Expected control states are checked by
# the case after this observation file is written; they are never substituted
# into these observations.

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
    # These exact native renderer diagnostics can interleave on another thread.
    # These grammars are not values of the traffic case's bool/numeric/enum
    # cells. Keep their original log positions and reject other unexpected output.
    $lsRendererDiagnostic = '^\[lionfx\] Render: emitters live=\d+ cell=\d+ inactive=\d+ culled=\d+ \(range=\d+ frustum=\d+ near=\d+\) drawn=\d+ particles=\d+ nocull=[01]$'
    $lsMeshDiagnostic = '^\[FLAG PC bring-up\] MESH lists:(?: \[\d+\]=\d+)+$'
    $lsDispatchDiagnostic = '^\[lionfx\] Dispatch: batches=\d+ vb=[0-9A-Fa-f]{16} white=\d+\.\d{3}$'
    for ($liSourceLine = 0; $liSourceLine -lt $laSourceLines.Count; ++$liSourceLine) {
        $lsSourceLine = $laSourceLines[$liSourceLine]
        if ($lsSourceLine -match $lsRendererDiagnostic -or $lsSourceLine -match $lsMeshDiagnostic -or
            $lsSourceLine -match $lsDispatchDiagnostic) {
            $laIgnoredDiagnosticLines.Add($liSourceLine + 1)
        } else {
            $laFilteredLines.Add($lsSourceLine)
            $laSourceLineNumbers.Add($liSourceLine + 1)
        }
    }
    $laLogLines = $laFilteredLines.ToArray()

    $laActions = @($laPlan.action_alias_queries)
    $laActionAliases = @($laActions | ForEach-Object { [string]$_.alias })
    if ($laActions.Count -ne [int]$laPlan.action_count -or
        @($laActionAliases | Select-Object -Unique).Count -ne $laActionAliases.Count) {
        $laProblems.Add("action alias plan shape: expected $($laPlan.action_count) unique actions, found $($laActions.Count)")
    }
    foreach ($lrAction in $laActions) {
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

    $laMarkers = @($laPlan.phase_markers)
    $laPhaseNames = @($laMarkers | ForEach-Object { [string]$_.phase })
    $laMarkerAliases = @($laMarkers | ForEach-Object { [string]$_.alias })
    if ($laMarkers.Count -ne [int]$laPlan.phase_count -or
        @($laPhaseNames | Select-Object -Unique).Count -ne $laPhaseNames.Count -or
        @($laMarkerAliases | Select-Object -Unique).Count -ne $laMarkerAliases.Count) {
        $laProblems.Add('phase marker plan must contain one unique alias for every phase')
    }

    $laUsedAliases = @($laPlan.aliases_used | ForEach-Object { [string]$_ })
    $laExpectedAliases = @($laActionAliases + @('pv') + $laMarkerAliases)
    $lsUsedAliasSet = (@($laUsedAliases | Sort-Object) -join '|')
    $lsExpectedAliasSet = (@($laExpectedAliases | Sort-Object) -join '|')
    if (@($laUsedAliases | Select-Object -Unique).Count -ne $laUsedAliases.Count -or
        $laUsedAliases.Count -ne 20 -or $laPlan.alias_capacity -ne 40 -or
        $laUsedAliases.Count -gt [int]$laPlan.alias_capacity -or $lsUsedAliasSet -cne $lsExpectedAliasSet) {
        $laProblems.Add('expected five action aliases, pv, and fourteen phase markers (20 of 40)')
    }

    $laAllMarkerRows = @()
    foreach ($lrMarker in $laMarkers) {
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
        if (!$lbPair) {
            $laProblems.Add("phase $($lrMarker.phase): expected two native marker lines for $($lrMarker.alias), found $($laMatches.Count)")
        } elseif (!$lbPathsMatch) {
            $laProblems.Add("phase $($lrMarker.phase): marker path mismatch")
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
        }
    }

    $lrHudMarker = $laMarkerObservations | Where-Object { $_.phase -ceq 'hud' } | Select-Object -First 1
    if ($lrHudMarker -and $lrHudMarker.begin_log_line) {
        foreach ($lrActionObs in $laActionObservations) {
            if ($lrActionObs.log_line -and $lrActionObs.log_line -ge $lrHudMarker.begin_log_line) {
                $laProblems.Add("action alias $($lrActionObs.alias): query must precede the hud phase marker")
            }
        }
    }

    # PS5.1's named-property adapter does not sort Hashtable keys reliably.
    $laAllMarkerRows = @($laAllMarkerRows | Sort-Object { [int]$_.LineIndex })
    $laExpectedMarkerSequence = @()
    foreach ($lrMarker in $laMarkers) {
        $laExpectedMarkerSequence += [string]$lrMarker.alias
        $laExpectedMarkerSequence += [string]$lrMarker.alias
    }
    if ($laAllMarkerRows.Count -ne $laExpectedMarkerSequence.Count) {
        $laProblems.Add("native marker output count: expected $($laExpectedMarkerSequence.Count), found $($laAllMarkerRows.Count)")
    }
    $liMarkerCompare = [Math]::Min($laAllMarkerRows.Count, $laExpectedMarkerSequence.Count)
    for ($liMarker = 0; $liMarker -lt $liMarkerCompare; ++$liMarker) {
        if ($laAllMarkerRows[$liMarker].Alias -cne $laExpectedMarkerSequence[$liMarker]) {
            $laProblems.Add("native marker order mismatch at marker output $($liMarker + 1)")
            break
        }
    }

    $laExpectedProbes = @($laPlan.probes)
    $laProbeKeys = @($laExpectedProbes | ForEach-Object { [string]$_.probe_key })
    if (@($laProbeKeys | Select-Object -Unique).Count -ne $laProbeKeys.Count) {
        $laProblems.Add('duplicate probe key in plan')
    }
    if ($laExpectedProbes.Count -ne [int]$laPlan.field_probe_count -or
        $laPlan.field_probe_count -ne 1428 -or $laPlan.literal_variable_count -ne 102 -or
        $laPlan.phase_count -ne 14) {
        $laProblems.Add("plan probe shape: expected 102 literal variables across 14 phases, found $($laExpectedProbes.Count) probes")
    }

    $laContainedPvLines = [System.Collections.Generic.HashSet[int]]::new()
    foreach ($lrMarker in $laMarkers) {
        $laMarkerObs = @($laMarkerObservations | Where-Object { $_.phase -ceq [string]$lrMarker.phase })
        if ($laMarkerObs.Count -ne 1 -or !$laMarkerObs[0].unique_pair) { continue }
        $liStartLine = [int]$laMarkerObs[0].begin_log_line - 1
        $liEndLine = [int]$laMarkerObs[0].end_log_line - 1
        if ($liStartLine -ge $liEndLine) {
            $laProblems.Add("phase $($lrMarker.phase): native marker interval is reversed or empty")
            continue
        }

        $laPhaseExpected = @($laExpectedProbes | Where-Object { [string]$_.phase -ceq [string]$lrMarker.phase })
        $liIntervalCount = $liEndLine - $liStartLine - 1
        $liExpectedIntervalCount = 2 * $laPhaseExpected.Count
        if ($laPhaseExpected.Count -ne 102 -or $liIntervalCount -ne $liExpectedIntervalCount) {
            $laProblems.Add("phase $($lrMarker.phase): expected 102 probes/204 output lines, found $($laPhaseExpected.Count)/$liIntervalCount")
        }
        $laPhasePvLines = @()
        for ($liLine = $liStartLine + 1; $liLine -lt $liEndLine; ++$liLine) {
            if ($laLogLines[$liLine].StartsWith('pv: ', [StringComparison]::Ordinal)) {
                $laPhasePvLines += $liLine
                [void]$laContainedPvLines.Add($liLine)
            }
        }
        if ($laPhasePvLines.Count -ne $laPhaseExpected.Count) {
            $laProblems.Add("phase $($lrMarker.phase): expected $($laPhaseExpected.Count) pv path outputs, found $($laPhasePvLines.Count)")
        }

        $liPairs = [Math]::Min($laPhasePvLines.Count, $laPhaseExpected.Count)
        for ($liProbe = 0; $liProbe -lt $liPairs; ++$liProbe) {
            $lrPlanProbe = $laPhaseExpected[$liProbe]
            $liPathLine = $laPhasePvLines[$liProbe]
            $liExpectedPathLine = $liStartLine + 1 + (2 * $liProbe)
            if ($liPathLine -ne $liExpectedPathLine) {
                $laProblems.Add("$($lrPlanProbe.probe_key): output is missing, extra, or out of planned order")
            }
            $lsObservedPath = $laLogLines[$liPathLine].Substring(4)
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
            if (!$lbPathMatches) { $laProblems.Add("$($lrPlanProbe.probe_key): resolved path mismatch '$lsObservedPath'") }

            $laProbeObservations += [ordered]@{
                probe_key = $lrPlanProbe.probe_key
                phase = $lrPlanProbe.phase
                role = $lrPlanProbe.role
                is_readout = [bool]$lrPlanProbe.is_readout
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

    # Original ScriptInterface error text: fail closed on alias, path, and command failures.
    $laErrorPattern = '^(Alias too long\. Max [0-9]+|Invalid alias name - no spaces|Too many aliases|Unknown alias value|expecting at least 1 parameter|Alias not found|Expected 1 parameters|Variable not found|Function not found|Expected 2 parameters|Variable .+ not found|Variable .+ is read only|Unknown command|Component not found|invalid function key: F1-F12|line too long or missing LF at end of file\. aborting!|Cannot open .+)$'
    $laCommandErrors = @($laLogLines | Where-Object { $_ -match $laErrorPattern })
    foreach ($lsError in $laCommandErrors) { $laProblems.Add("script command error: $lsError") }
}

# Parsing uses filtered positions internally; exported evidence always points
# to the original game log, including the two explicitly whitelisted diagnostics.
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
    case = 'debug_menu_traffic_batch'
    source_log = $LogPath
    source_log_sha256 = if (Test-Path -LiteralPath $LogPath) { (Get-FileHash -LiteralPath $LogPath -Algorithm SHA256).Hash.ToLowerInvariant() } else { $null }
    ignored_native_diagnostic_lines = @($laIgnoredDiagnosticLines)
    plan_file = $PlanPath
    status = $lsStatus
    alias_capacity = if ($laPlan) { $laPlan.alias_capacity } else { $null }
    aliases_used = if ($laPlan) { @($laPlan.aliases_used) } else { @() }
    phase_marker_count = $laMarkerObservations.Count
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
[System.IO.File]::WriteAllText($OutputPath, ($loObservation | ConvertTo-Json -Depth 8), [System.Text.UTF8Encoding]::new($false))
[pscustomobject]@{
    Pass = $lsStatus -eq 'pass'
    Detail = "status=$lsStatus probes=$($laProbeObservations.Count)/$(if($laPlan){@($laPlan.probes).Count}else{0}) markers=$($laMarkerObservations.Count)/$(if($laPlan){@($laPlan.phase_markers).Count}else{0}) actions=$($laActionObservations.Count)/$(if($laPlan){@($laPlan.action_alias_queries).Count}else{0}); problems=$($laProblems.Count)"
    OutputPath = $OutputPath
}
