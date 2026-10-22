param(
    [Parameter(Mandatory=$true)][string]$LogPath,
    [Parameter(Mandatory=$true)][string]$PlanPath,
    [Parameter(Mandatory=$true)][string]$OutputPath,
    [Parameter()][string]$PvsReceiptPath,
    [switch]$RequirePvsReceipts
)

if ([string]::IsNullOrWhiteSpace($PvsReceiptPath)) {
    $PvsReceiptPath=Join-Path (Split-Path -Parent $OutputPath) 'traffic-pvs-phase-receipts.json'
}

# Every native-readback value is copied from the game's original
# ScriptInterface::OutputMessage stream. Expected control states are checked by
# the case after this observation file is written; the PVS diagnostic receipt is
# parsed separately and never treated as a storage/readback value.
# the case after this observation file is written; they are never substituted
# into these observations.

$laProblems = [System.Collections.Generic.List[string]]::new()
$laActionObservations = @()
$laMarkerObservations = @()
$laProbeObservations = @()
$laLogLines = @()
$laSourceLineNumbers = [System.Collections.Generic.List[int]]::new()
$laIgnoredDiagnosticLines = [System.Collections.Generic.List[int]]::new()
$laPvsDiagnosticLines = [System.Collections.Generic.List[int]]::new()
$laPvsDiagnosticRecords = [System.Collections.Generic.List[object]]::new()
$laPvsMalformedLines = [System.Collections.Generic.List[object]]::new()
$laPvsProblems = [System.Collections.Generic.List[string]]::new()
$laPvsPairs = [System.Collections.Generic.List[object]]::new()
$loPvsPhaseReceipt = $null
$laPlan = $null

function Convert-PvsUnsigned([string]$Text, [UInt64]$Maximum) {
    try {
        $luValue = [UInt64]::Parse($Text, [System.Globalization.NumberStyles]::None,
            [System.Globalization.CultureInfo]::InvariantCulture)
    } catch {
        return [pscustomobject]@{ Valid=$false; Value=[UInt64]0 }
    }
    if ($luValue -gt $Maximum) { return [pscustomobject]@{ Valid=$false; Value=[UInt64]0 } }
    return [pscustomobject]@{ Valid=$true; Value=$luValue }
}

function Convert-PvsIdList([string]$Text) {
    $laValues = [System.Collections.Generic.List[int]]::new()
    if ($Text.Length -eq 0) { return [pscustomobject]@{ Valid=$true; Values=@() } }
    foreach ($lsToken in $Text.Split(',')) {
        $lrValue = Convert-PvsUnsigned $lsToken ([UInt64]65535)
        if (!$lrValue.Valid) { return [pscustomobject]@{ Valid=$false; Values=@() } }
        $laValues.Add([int]$lrValue.Value)
    }
    return [pscustomobject]@{ Valid=$true; Values=$laValues.ToArray() }
}

function Convert-PvsCellMap([string]$Text) {
    $laValues = [System.Collections.Generic.List[object]]::new()
    if ($Text.Length -eq 0) { return [pscustomobject]@{ Valid=$true; Values=@() } }
    foreach ($lsToken in $Text.Split(';')) {
        $lrToken = [regex]::Match($lsToken, '^([0-9]+):([0-9]+),([0-9]+)$')
        if (!$lrToken.Success) { return [pscustomobject]@{ Valid=$false; Values=@() } }
        $lrHull = Convert-PvsUnsigned $lrToken.Groups[1].Value ([UInt64]65535)
        $lrColumn = Convert-PvsUnsigned $lrToken.Groups[2].Value ([UInt64]4294967295)
        $lrRow = Convert-PvsUnsigned $lrToken.Groups[3].Value ([UInt64]4294967295)
        if (!$lrHull.Valid -or !$lrColumn.Valid -or !$lrRow.Valid) {
            return [pscustomobject]@{ Valid=$false; Values=@() }
        }
        $laValues.Add([ordered]@{
            hull_id=[int]$lrHull.Value
            column=[UInt32]$lrColumn.Value
            row=[UInt32]$lrRow.Value
        })
    }
    return [pscustomobject]@{ Valid=$true; Values=$laValues.ToArray() }
}

function Convert-PvsFloat([string]$Text) {
    try {
        $lfValue = [double]::Parse($Text, [System.Globalization.NumberStyles]::Float,
            [System.Globalization.CultureInfo]::InvariantCulture)
    } catch {
        return [pscustomobject]@{ Valid=$false; Value=[double]0 }
    }
    if ([double]::IsNaN($lfValue) -or [double]::IsInfinity($lfValue)) {
        return [pscustomobject]@{ Valid=$false; Value=[double]0 }
    }
    return [pscustomobject]@{ Valid=$true; Value=$lfValue }
}

if (!(Test-Path -LiteralPath $LogPath)) { $laProblems.Add("missing game log: $LogPath") }
if (!(Test-Path -LiteralPath $PlanPath)) { $laProblems.Add("missing readback plan: $PlanPath") }

if ($laProblems.Count -eq 0) {
    $laPlan = Get-Content -LiteralPath $PlanPath -Raw | ConvertFrom-Json
    $laSourceLines = [IO.File]::ReadAllLines($LogPath)
    $laFilteredLines = [System.Collections.Generic.List[string]]::new()
    $lsPvsFloatPattern = '[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?'
    $lsPvsSetPattern = '^\[PC-PVS-DIAG\]\[SET\] phase=(baseline|on|off) epoch=([0-9]+) set_call=([0-9]+) decision_frame=([01]) frames_since_decision=([0-9]+) running_worst_case=([01]) data_ready=([01]) pvs_present=([01]) consumed_by_draw_seq=([0-9]+) active_count=([0-9]+) active_ids=\[([0-9,]*)\] added_ids=\[([0-9,]*)\] removed_ids=\[([0-9,]*)\]$'
    $lsPvsDrawPattern = '^\[PC-PVS-DIAG\]\[DRAW\] phase=(baseline|on|off) epoch=([0-9]+) draw_seq=([0-9]+) decision_frame=([01]) frames_since_decision=([0-9]+) running_worst_case=([01]) draw_toggle=([01]) data_ready=([01]) pvs_present=([01]) cells_x=([0-9]+) cells_z=([0-9]+) total_cells=([0-9]+) draw_rows=([0-9]+) box_calls=([0-9]+) mapping_count=([0-9]+) box_origin=([0-9]+),([0-9]+) box_size=(' + $lsPvsFloatPattern + '),(' + $lsPvsFloatPattern + ') id_cell=\[((?:[0-9]+:[0-9]+,[0-9]+(?:;[0-9]+:[0-9]+,[0-9]+)*)?)\]$'
    # PVS records are parsed and removed from marker/pv intervals, but every
    # original line and one-based source line number is retained in its receipt.
    for ($liSourceLine = 0; $liSourceLine -lt $laSourceLines.Count; ++$liSourceLine) {
        $lsSourceLine = $laSourceLines[$liSourceLine]
        if ($lsSourceLine.StartsWith('[PC-PVS-DIAG]', [StringComparison]::Ordinal)) {
            $liOriginalLine = $liSourceLine + 1
            $lrMatch = [regex]::Match($lsSourceLine, $lsPvsSetPattern)
            if ($lrMatch.Success) {
                $lrEpoch = Convert-PvsUnsigned $lrMatch.Groups[2].Value ([UInt64]::MaxValue)
                $lrSetCall = Convert-PvsUnsigned $lrMatch.Groups[3].Value ([UInt64]::MaxValue)
                $lrFrames = Convert-PvsUnsigned $lrMatch.Groups[5].Value ([UInt64]4294967295)
                $lrConsumed = Convert-PvsUnsigned $lrMatch.Groups[9].Value ([UInt64]::MaxValue)
                $lrActiveCount = Convert-PvsUnsigned $lrMatch.Groups[10].Value ([UInt64]4294967295)
                $lrActiveIds = Convert-PvsIdList $lrMatch.Groups[11].Value
                $lrAddedIds = Convert-PvsIdList $lrMatch.Groups[12].Value
                $lrRemovedIds = Convert-PvsIdList $lrMatch.Groups[13].Value
                if (!$lrEpoch.Valid -or !$lrSetCall.Valid -or !$lrFrames.Valid -or !$lrConsumed.Valid -or
                    !$lrActiveCount.Valid -or !$lrActiveIds.Valid -or !$lrAddedIds.Valid -or !$lrRemovedIds.Valid) {
                    $laPvsMalformedLines.Add([ordered]@{source_line=$liOriginalLine;raw_line=$lsSourceLine;reason='SET numeric/list field is invalid'})
                } else {
                    $laPvsDiagnosticRecords.Add([ordered]@{
                        kind='SET';phase=$lrMatch.Groups[1].Value;epoch=$lrEpoch.Value;set_call=$lrSetCall.Value
                        decision_frame=[int]$lrMatch.Groups[4].Value;frames_since_decision=[UInt32]$lrFrames.Value
                        running_worst_case=[int]$lrMatch.Groups[6].Value;data_ready=[int]$lrMatch.Groups[7].Value
                        pvs_present=[int]$lrMatch.Groups[8].Value;consumed_by_draw_seq=$lrConsumed.Value
                        active_count=[UInt32]$lrActiveCount.Value;active_ids=@($lrActiveIds.Values)
                        added_ids=@($lrAddedIds.Values);removed_ids=@($lrRemovedIds.Values)
                        source_line=$liOriginalLine;raw_line=$lsSourceLine
                    })
                }
            } else {
                $lrMatch = [regex]::Match($lsSourceLine, $lsPvsDrawPattern)
                if ($lrMatch.Success) {
                    $lrEpoch = Convert-PvsUnsigned $lrMatch.Groups[2].Value ([UInt64]::MaxValue)
                    $lrDrawSeq = Convert-PvsUnsigned $lrMatch.Groups[3].Value ([UInt64]::MaxValue)
                    $lrFrames = Convert-PvsUnsigned $lrMatch.Groups[5].Value ([UInt64]4294967295)
                    $lrCellsX = Convert-PvsUnsigned $lrMatch.Groups[10].Value ([UInt64]4294967295)
                    $lrCellsZ = Convert-PvsUnsigned $lrMatch.Groups[11].Value ([UInt64]4294967295)
                    $lrTotal = Convert-PvsUnsigned $lrMatch.Groups[12].Value ([UInt64]4294967295)
                    $lrRows = Convert-PvsUnsigned $lrMatch.Groups[13].Value ([UInt64]4294967295)
                    $lrBoxCalls = Convert-PvsUnsigned $lrMatch.Groups[14].Value ([UInt64]4294967295)
                    $lrMapCount = Convert-PvsUnsigned $lrMatch.Groups[15].Value ([UInt64]4294967295)
                    $lrOriginX = Convert-PvsUnsigned $lrMatch.Groups[16].Value ([UInt64]4294967295)
                    $lrOriginY = Convert-PvsUnsigned $lrMatch.Groups[17].Value ([UInt64]4294967295)
                    $lrStepX = Convert-PvsFloat $lrMatch.Groups[18].Value
                    $lrStepY = Convert-PvsFloat $lrMatch.Groups[19].Value
                    $lrMap = Convert-PvsCellMap $lrMatch.Groups[20].Value
                    if (!$lrEpoch.Valid -or !$lrDrawSeq.Valid -or !$lrFrames.Valid -or
                        !$lrCellsX.Valid -or !$lrCellsZ.Valid -or !$lrTotal.Valid -or !$lrRows.Valid -or
                        !$lrBoxCalls.Valid -or !$lrMapCount.Valid -or !$lrOriginX.Valid -or !$lrOriginY.Valid -or
                        !$lrStepX.Valid -or !$lrStepY.Valid -or !$lrMap.Valid) {
                        $laPvsMalformedLines.Add([ordered]@{source_line=$liOriginalLine;raw_line=$lsSourceLine;reason='DRAW numeric/map field is invalid'})
                    } else {
                        $laPvsDiagnosticRecords.Add([ordered]@{
                            kind='DRAW';phase=$lrMatch.Groups[1].Value;epoch=$lrEpoch.Value;draw_seq=$lrDrawSeq.Value
                            decision_frame=[int]$lrMatch.Groups[4].Value;frames_since_decision=[UInt32]$lrFrames.Value
                            running_worst_case=[int]$lrMatch.Groups[6].Value;draw_toggle=[int]$lrMatch.Groups[7].Value
                            data_ready=[int]$lrMatch.Groups[8].Value;pvs_present=[int]$lrMatch.Groups[9].Value
                            cells_x=[UInt32]$lrCellsX.Value;cells_z=[UInt32]$lrCellsZ.Value
                            total_cells=[UInt32]$lrTotal.Value;draw_rows=[UInt32]$lrRows.Value
                            box_calls=[UInt32]$lrBoxCalls.Value;mapping_count=[UInt32]$lrMapCount.Value
                            box_origin_x=[UInt32]$lrOriginX.Value;box_origin_y=[UInt32]$lrOriginY.Value
                            box_size_x=[double]$lrStepX.Value;box_size_y=[double]$lrStepY.Value
                            id_cell=@($lrMap.Values);source_line=$liOriginalLine;raw_line=$lsSourceLine
                        })
                    }
                } else {
                    $laPvsMalformedLines.Add([ordered]@{source_line=$liOriginalLine;raw_line=$lsSourceLine;reason='unknown or malformed PVS diagnostic'})
                }
            }
            $laPvsDiagnosticLines.Add($liOriginalLine)
            continue
        }
    }
    # These exact native renderer diagnostics can interleave on another thread.
    # These grammars are not values of the traffic case's bool/numeric/enum
    # cells. Keep their original log positions and reject other unexpected output.
    $lsRendererDiagnostic = '^\[lionfx\] Render: emitters live=\d+ cell=\d+ inactive=\d+ culled=\d+ \(range=\d+ frustum=\d+ near=\d+\) drawn=\d+ particles=\d+ nocull=[01]$'
    $lsMeshDiagnostic = '^\[FLAG PC bring-up\] MESH lists:(?: \[\d+\]=\d+)+$'
    $lsDispatchDiagnostic = '^\[lionfx\] Dispatch: batches=\d+ vb=[0-9A-Fa-f]{16} white=\d+\.\d{3}$'
    $lsBlendDiagnostic = '^\[lionblend\] call=\d+ layer=-?\d+->-?\d+ t=-?\d+\.\d{4} diff\(s12/v4/c3\)=\d+/\d+/\d+' +
        ' life=-?\d+\.\d{4}\|-?\d+\.\d{4}->-?\d+\.\d{4} size=-?\d+\.\d{4}\|-?\d+\.\d{4}->-?\d+\.\d{4}' +
        ' rate=-?\d+\.\d{3}\|-?\d+\.\d{3}->-?\d+\.\d{3} vel\.y=-?\d+\.\d{4}\|-?\d+\.\d{4}->-?\d+\.\d{4}' +
        ' col0=[0-9A-Fa-f]{8}\|[0-9A-Fa-f]{8}->[0-9A-Fa-f]{8} flags=[0-9A-Fa-f]{8}\|[0-9A-Fa-f]{8}->[0-9A-Fa-f]{8}$'
    for ($liSourceLine = 0; $liSourceLine -lt $laSourceLines.Count; ++$liSourceLine) {
        $lsSourceLine = $laSourceLines[$liSourceLine]
        # Valid and malformed PVS-prefixed lines are retained in the separate
        # receipt and excluded from native OutputMessage marker/pv intervals.
        if ($laPvsDiagnosticLines.Contains($liSourceLine + 1)) { continue }
        if ($lsSourceLine -match $lsRendererDiagnostic -or $lsSourceLine -match $lsMeshDiagnostic -or
            $lsSourceLine -match $lsDispatchDiagnostic -or $lsSourceLine -match $lsBlendDiagnostic) {
            $laIgnoredDiagnosticLines.Add($liSourceLine + 1)
        } else {
            $laFilteredLines.Add($lsSourceLine)
            $laSourceLineNumbers.Add($liSourceLine + 1)
        }
    }
    $laLogLines = $laFilteredLines.ToArray()

    # A PVS diagnostic prefix is never silently treated as an output value.
    # Only the exact SET/DRAW record grammars above enter the typed phase receipt.
    $laPvsRecords = @($laPvsDiagnosticRecords | Sort-Object { [int]$_.source_line })
    $laPvsSets = @($laPvsRecords | Where-Object {$_.kind -eq 'SET'})
    $laPvsDraws = @($laPvsRecords | Where-Object {$_.kind -eq 'DRAW'})
    foreach($lrMalformed in $laPvsMalformedLines) {
        $laPvsProblems.Add("malformed PVS diagnostic at source line $($lrMalformed.source_line): $($lrMalformed.reason)")
    }
    if($RequirePvsReceipts -and $laPvsSets.Count -ne 3) {$laPvsProblems.Add("expected three PVS SET records, found $($laPvsSets.Count)")}
    if($RequirePvsReceipts -and $laPvsDraws.Count -ne 3) {$laPvsProblems.Add("expected three PVS DRAW records, found $($laPvsDraws.Count)")}

    $laExpectedPvsPhases=@('baseline','on','off')
    $liRequiredPvsPairs=if($RequirePvsReceipts){3}else{0}
    $liPreviousPvsDrawLine=0
    $luPreviousPvsEpoch=[UInt64]0
    $luPreviousPvsSetCall=[UInt64]0
    $laExpectedWorstCaseIds=@(98,99,100,101,102,119,120,121,122,123,140,141,142,143,144)
    for($liPvsPhase=0;$liPvsPhase -lt $liRequiredPvsPairs;++$liPvsPhase) {
        if($liPvsPhase -ge $laPvsSets.Count -or $liPvsPhase -ge $laPvsDraws.Count) {continue}
        $lrSet=$laPvsSets[$liPvsPhase]
        $lrDraw=$laPvsDraws[$liPvsPhase]
        $lsExpectedPhase=$laExpectedPvsPhases[$liPvsPhase]
        $laPairProblems=[System.Collections.Generic.List[string]]::new()
        if($lrSet.phase -cne $lsExpectedPhase -or $lrDraw.phase -cne $lsExpectedPhase) {
            $laPairProblems.Add("phase order expected $lsExpectedPhase")
        }
        if($lrSet.epoch -ne $lrDraw.epoch) {$laPairProblems.Add('SET/DRAW epoch mismatch')}
        if($lrSet.consumed_by_draw_seq -ne $lrDraw.draw_seq) {$laPairProblems.Add('SET consumption/draw sequence mismatch')}
        if($lrDraw.draw_seq -ne ($liPvsPhase+1)) {$laPairProblems.Add('draw sequence is not the bounded 1,2,3 order')}
        if($lrSet.epoch -eq 0 -or $lrSet.set_call -eq 0) {$laPairProblems.Add('SET epoch/set-call ordinal is zero')}
        if($lrSet.source_line -ge $lrDraw.source_line -or $lrSet.source_line -le $liPreviousPvsDrawLine) {
            $laPairProblems.Add('SET/DRAW source-line order is invalid')
        }
        if($liPvsPhase -gt 0 -and ($lrSet.epoch -le $luPreviousPvsEpoch -or $lrSet.set_call -le $luPreviousPvsSetCall)) {
            $laPairProblems.Add('publication epoch/set-call order is not increasing')
        }
        $liExpectedWorstCase=if($lsExpectedPhase -eq 'on'){1}else{0}
        if($lrSet.running_worst_case -ne $liExpectedWorstCase -or $lrDraw.running_worst_case -ne $liExpectedWorstCase) {
            $laPairProblems.Add('Running Worst Case toggle does not match phase')
        }
        if($lrSet.data_ready -ne 1 -or $lrSet.pvs_present -ne 1 -or
           $lrDraw.data_ready -ne 1 -or $lrDraw.pvs_present -ne 1 -or $lrDraw.draw_toggle -ne 1) {
            $laPairProblems.Add('TrafficData/PVS readiness or Draw Active Hulls toggle is false')
        }
        if($lrSet.active_count -gt 72 -or @($lrSet.active_ids).Count -ne $lrSet.active_count -or
           @($lrSet.active_ids | Sort-Object -Unique).Count -ne $lrSet.active_count) {
            $laPairProblems.Add('SET active IDs/count are invalid or non-unique')
        }
        if(@($lrSet.added_ids).Count -gt 72 -or @($lrSet.removed_ids).Count -gt 72 -or
           @($lrSet.added_ids | Sort-Object -Unique).Count -ne @($lrSet.added_ids).Count -or
           @($lrSet.removed_ids | Sort-Object -Unique).Count -ne @($lrSet.removed_ids).Count) {
            $laPairProblems.Add('SET delta ID list exceeds capacity or contains duplicate IDs')
        }
        if($lsExpectedPhase -eq 'baseline' -and $lrSet.active_count -eq 0) {
            $laPairProblems.Add('baseline SET has no active hulls')
        }
        if($lrDraw.box_origin_x -ne 80 -or $lrDraw.box_origin_y -ne 80 -or
           $lrDraw.cells_x -le 0 -or $lrDraw.cells_z -le 0 -or $lrDraw.total_cells -le 0 -or $lrDraw.draw_rows -le 0) {
            $laPairProblems.Add('DRAW PVS dimensions/origin are invalid')
        } elseif(([UInt64]$lrDraw.cells_x * [UInt64]$lrDraw.cells_z) -ne [UInt64]$lrDraw.total_cells -or
                 [UInt32][Math]::Floor([double]$lrDraw.total_cells/[double]$lrDraw.cells_x) -ne $lrDraw.draw_rows) {
            $laPairProblems.Add('DRAW PVS dimension product/row count is inconsistent')
        }
        if($lrDraw.box_calls -ne $lrSet.active_count -or $lrDraw.mapping_count -ne $lrSet.active_count -or
           @($lrDraw.id_cell).Count -ne $lrSet.active_count) {
            $laPairProblems.Add('DRAW box/map count does not match SET active count')
        }
        if($lrDraw.box_size_x -le 0 -or $lrDraw.box_size_y -le 0) {
            $laPairProblems.Add('DRAW box size is not positive')
        }
        $laSetIds=@($lrSet.active_ids)
        if($lrDraw.cells_x -gt 0) {
            for($liHull=0;$liHull -lt [Math]::Min($laSetIds.Count,@($lrDraw.id_cell).Count);++$liHull) {
                $lrCell=$lrDraw.id_cell[$liHull]
                $luExpectedColumn=[UInt32]([UInt64]$laSetIds[$liHull] % [UInt64]$lrDraw.cells_x)
                $luExpectedRow=[UInt32][Math]::Floor([double]$laSetIds[$liHull]/[double]$lrDraw.cells_x)
                if($lrCell.hull_id -ne $laSetIds[$liHull] -or
                   $lrCell.column -ne $luExpectedColumn -or $lrCell.row -ne $luExpectedRow -or
                   $lrCell.column -ge $lrDraw.cells_x -or $lrCell.row -ge $lrDraw.cells_z) {
                    $laPairProblems.Add("DRAW cell map differs from original ID modulo/division at index $liHull")
                    break
                }
            }
        }
        if($lsExpectedPhase -eq 'on' -and (($laSetIds -join ',') -cne ($laExpectedWorstCaseIds -join ','))) {
            $laPairProblems.Add('ON active IDs differ from the exact 15-hull source set')
        }
        $lrPair=[ordered]@{
            phase=$lsExpectedPhase;epoch=$lrSet.epoch;set_call=$lrSet.set_call;draw_seq=$lrDraw.draw_seq
            set_source_line=$lrSet.source_line;draw_source_line=$lrDraw.source_line
            set=$lrSet;draw=$lrDraw;status=if($laPairProblems.Count -eq 0){'pass'}else{'fail'}
            problems=@($laPairProblems)
        }
        $laPvsPairs.Add($lrPair)
        foreach($lsPairProblem in $laPairProblems) {$laPvsProblems.Add("$lsExpectedPhase PVS receipt: $lsPairProblem")}
        $liPreviousPvsDrawLine=$lrDraw.source_line
        $luPreviousPvsEpoch=$lrSet.epoch
        $luPreviousPvsSetCall=$lrSet.set_call
    }
    $lsPvsReceiptStatus='not_requested'
    if($RequirePvsReceipts) {
        foreach($lsPvsProblem in $laPvsProblems) {$laProblems.Add($lsPvsProblem)}
        $lsPvsReceiptStatus=if($laPvsProblems.Count -eq 0){'pass'}else{'fail'}
    }
    $loPvsPhaseReceipt=[ordered]@{
        schema=1;source_log=$LogPath
        source_log_sha256=if(Test-Path -LiteralPath $LogPath){(Get-FileHash -LiteralPath $LogPath -Algorithm SHA256).Hash.ToLowerInvariant()}else{$null}
        required=[bool]$RequirePvsReceipts;expected_phase_order=$laExpectedPvsPhases;status=$lsPvsReceiptStatus
        set_count=$laPvsSets.Count;draw_count=$laPvsDraws.Count
        diagnostic_source_lines=@($laPvsDiagnosticLines);records=$laPvsRecords
        malformed_lines=@($laPvsMalformedLines);pairs=@($laPvsPairs);problems=@($laPvsProblems)
        runtime_consumer_verified=0;screenshot_same_frame_verified=$false
    }

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
# to the original game log. PVS records and malformed prefixed lines are retained
# separately; required mode fails closed, while default mode reports not_requested.
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

if($null -eq $loPvsPhaseReceipt) {
    if($RequirePvsReceipts) {$laPvsProblems.Add('PVS receipt parser did not run because log or plan input was missing')}
    $loPvsPhaseReceipt=[ordered]@{
        schema=1;source_log=$LogPath;source_log_sha256=$null;expected_phase_order=@('baseline','on','off')
        required=[bool]$RequirePvsReceipts;status=if($RequirePvsReceipts){'fail'}else{'not_requested'}
        set_count=0;draw_count=0;diagnostic_source_lines=@();records=@();malformed_lines=@()
        pairs=@();problems=@($laPvsProblems);runtime_consumer_verified=0;screenshot_same_frame_verified=$false
    }
}
$lsStatus = if ($laProblems.Count -eq 0) { 'pass' } else { 'fail' }
$loObservation = [ordered]@{
    case = 'debug_menu_traffic_batch'
    source_log = $LogPath
    source_log_sha256 = if (Test-Path -LiteralPath $LogPath) { (Get-FileHash -LiteralPath $LogPath -Algorithm SHA256).Hash.ToLowerInvariant() } else { $null }
    ignored_native_diagnostic_lines = @($laIgnoredDiagnosticLines)
    pvs_phase_receipt_file = $PvsReceiptPath
    pvs_phase_receipt_status = $loPvsPhaseReceipt.status
    pvs_phase_pair_count = @($loPvsPhaseReceipt.pairs).Count
    pvs_diagnostic_source_lines = @($laPvsDiagnosticLines)
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
$lsPvsReceiptDirectory=Split-Path -Parent $PvsReceiptPath
if($lsPvsReceiptDirectory -and !(Test-Path -LiteralPath $lsPvsReceiptDirectory)) {
    New-Item -ItemType Directory -Force -Path $lsPvsReceiptDirectory | Out-Null
}
[System.IO.File]::WriteAllText($PvsReceiptPath, ($loPvsPhaseReceipt | ConvertTo-Json -Depth 12), [System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllText($OutputPath, ($loObservation | ConvertTo-Json -Depth 8), [System.Text.UTF8Encoding]::new($false))
[pscustomobject]@{
    Pass = $lsStatus -eq 'pass'
    Detail = "status=$lsStatus probes=$($laProbeObservations.Count)/$(if($laPlan){@($laPlan.probes).Count}else{0}) markers=$($laMarkerObservations.Count)/$(if($laPlan){@($laPlan.phase_markers).Count}else{0}) actions=$($laActionObservations.Count)/$(if($laPlan){@($laPlan.action_alias_queries).Count}else{0}); problems=$($laProblems.Count)"
    OutputPath = $OutputPath
}
