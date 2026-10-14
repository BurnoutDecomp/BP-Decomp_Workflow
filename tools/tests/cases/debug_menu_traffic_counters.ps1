# Reuse the full phase/storage stimulus, with acceptance scoped to four Stats
# readouts. Other Traffic effects keep their separate per-entry review gates.
$counterCase = & (Join-Path $PSScriptRoot 'debug_menu_traffic_batch.ps1')
$counterCase.Name = 'debug_menu_traffic_counters'
$counterCase.Bug = 'Traffic Stats must read the live param/free/purgatory/hull containers after the shared Stack repair.'
$manualName = 'manual Traffic consumer and visual witness review required'
if (@($counterCase.Checks | Where-Object { $_.Name -eq $manualName }).Count -ne 1) {
    throw 'Expected exactly one whole-page manual review gate in the shared stimulus.'
}
$counterCase.Checks = @($counterCase.Checks | Where-Object { $_.Name -ne $manualName })
$counterCase.Checks += @(
    @{ Kind='LogCount'; Name='counter consumer has no engine assertions'; Pattern='\[ASSERT \d+\]'; Max=0 }
    @{ Kind='Script'; Name='four live Traffic counters preserve the real container accounting'; Script={
        param($ctx)
        $observationPath = Join-Path $ctx.RunDir 'native-readback.json'
        if (!(Test-Path -LiteralPath $observationPath)) {
            return @{Pass=$false;Detail='missing actual native readback'}
        }
        $observations = Get-Content -LiteralPath $observationPath -Raw | ConvertFrom-Json
        if ($observations.status -ne 'pass') {
            return @{Pass=$false;Detail='native readback parser did not pass'}
        }
        $suffixes = @('0003','0004','0005','0006')
        $captions = @('Active params','Free params','Purgatory params','Active hulls')
        $rows = @()
        $problems = @()
        foreach ($phase in $ctx.Case.PhaseNames) {
            $values = @()
            $lines = @()
            for ($index=0; $index -lt 4; ++$index) {
                $identity = 'BrnTraffic::DebugComponent::OnActivate#'+$suffixes[$index]
                $matches = @($observations.probes | Where-Object { $_.phase -eq $phase -and $_.id -eq $identity })
                $parsed = 0
                if ($matches.Count -ne 1 -or !$matches[0].path_matches -or !$matches[0].value_present -or
                    !$matches[0].is_readout -or $matches[0].observed_resolved_path -cne ('/Traffic/Stats/'+$captions[$index]) -or
                    ![int]::TryParse([string]$matches[0].actual_value,[ref]$parsed)) {
                    $problems += ($phase+'/'+$identity)
                    continue
                }
                $values += $parsed
                $lines += $matches[0].value_log_line
            }
            if ($values.Count -ne 4) { continue }
            $sentinel = @($values | Where-Object { $_ -eq -1 }).Count -eq 4
            if ($sentinel) {
                if ($phase -ne $ctx.Case.PhaseNames[0]) { $problems += ($phase+'/late constructor sentinel') }
            } elseif ($values[0] -lt 0 -or $values[1] -lt 0 -or $values[2] -lt 0 -or
                      $values[0]+$values[1]+$values[2] -ne 400 -or $values[3] -lt 0 -or $values[3] -gt 72) {
                $problems += ($phase+'/invalid live container accounting')
            }
            $rows += [ordered]@{phase=$phase;active=$values[0];free=$values[1];purgatory=$values[2];hulls=$values[3];
                constructor_sentinel=$sentinel;value_log_lines=$lines}
        }
        $live = @($rows | Where-Object { !$_.constructor_sentinel })
        $populated = @($live | Where-Object { $_.active -gt 0 -and $_.free -lt 400 -and $_.hulls -gt 0 })
        $drained = @($live | Where-Object { $_.phase -eq 'cleanup' -and $_.active -eq 0 -and
            $_.free -eq 400 -and $_.purgatory -eq 0 -and $_.hulls -eq 0 })
        $activeValues = @($live | ForEach-Object { $_.active } | Select-Object -Unique)
        $nonemptyPurgatory = @($live | Where-Object { $_.purgatory -gt 0 }).Count
        $pass = $rows.Count -eq 14 -and $problems.Count -eq 0 -and $populated.Count -gt 0 -and
            $drained.Count -eq 1 -and $activeValues.Count -gt 1
        [ordered]@{scope='four Traffic Stats readouts only';pass=$pass;source_log_sha256=$observations.source_log_sha256;
            readback_sha256=(Get-FileHash -LiteralPath $observationPath -Algorithm SHA256).Hash;
            counter_reads=4*$rows.Count;rows=$rows;nonempty_purgatory_phases=$nonemptyPurgatory;problems=$problems} |
            ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $ctx.RunDir 'counter-witness.json') -Encoding ascii
        return @{Pass=$pass;Detail="actual counter reads=$($rows.Count*4)/56; populated=$($populated.Count); cleanup drained=$($drained.Count); changing active counts=$($activeValues.Count); nonempty purgatory=$nonemptyPurgatory; problems=$($problems -join ', ')"}
    } }
)
return $counterCase
