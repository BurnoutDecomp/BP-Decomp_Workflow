param([Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{40}$')][string]$B5Commit)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$source=Join-Path $root 'b5-decomp'
$out=Join-Path $root 'build/candidate/artifacts/gui-audio-trigger-wire'
$control='4c7c6ba2f97533315d5663d22499042cb007df31'
if ($env:ImageOS -cne 'win22' -or $env:CANDIDATE_RUNNER_ENVIRONMENT -cne 'github-hosted' -or $env:BRN_EXE_JOBS -cne '4') {
    throw 'Audio wire requires GitHub-hosted Windows2022 / Jobs4.'
}
if ((& git -C $source rev-parse HEAD) -cne $B5Commit -or $LASTEXITCODE -ne 0) { throw 'Audio candidate checkout differs.' }
if (Test-Path -LiteralPath $out) { throw 'Audio artifact folder must be fresh.' }
$pins=@{
    'tests/run_gui_audio_trigger_wire.py'='2c1194052336fee29e71f358045ace23e61f5d49245c9eeeea3616f69cbe781c'
    'tests/GuiAudioTriggerWire.cpp'='d00c1cdc3b85239a06eb0b430c347959978b64d3eef4400ee38ff2df4f2b90e8'
    'tests/fxgs_common.py'='6230372da7ef60e446a165470a61850964b7b7498576eaec93dbb58555ae9033'
}
function LfHash([string]$path) {
    $text=[Text.Encoding]::UTF8.GetString([IO.File]::ReadAllBytes($path)).Replace("`r`n","`n")
    return [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($text))).ToLowerInvariant()
}
$workflowGitlink=(@(& git -C $root ls-tree HEAD -- b5-decomp) -join "`n")
if ($LASTEXITCODE -ne 0 -or $workflowGitlink -cnotmatch '\A160000 commit ([0-9a-f]{40})\tb5-decomp\z') { throw 'Audio workflow source gitlink is invalid.' }
$expectedParentStatus=if($Matches[1] -cne $B5Commit){' M b5-decomp'}else{''}
function Assert-Clean {
    $parentStatus=(@(& git -C $root status --porcelain=v1 --untracked-files=all --ignore-submodules=none) -join "`n")
    if ($LASTEXITCODE -ne 0 -or $parentStatus -cne $expectedParentStatus) { throw 'Audio parent status differs from its exact intentional gitlink override.' }
    if ((& git -C $source rev-parse HEAD) -cne $B5Commit -or $LASTEXITCODE -ne 0) { throw 'Audio source revision changed.' }
    if ((& git -C $source status --porcelain=v1 --untracked-files=all) -or $LASTEXITCODE -ne 0) { throw 'Audio B5 source is dirty.' }
}
Assert-Clean
foreach($p in $pins.Keys) { if ((LfHash (Join-Path $source $p)) -cne $pins[$p]) { throw "Audio harness differs: $p" } }
& git -C $source fetch --recurse-submodules=no --no-tags --depth=1 origin $control
if ($LASTEXITCODE -ne 0) { throw 'Audio exact baseline fetch failed.' }
$hadNoDefault=Test-Path -LiteralPath Env:NoDefaultCurrentDirectoryInExePath
$oldNoDefault=[Environment]::GetEnvironmentVariable('NoDefaultCurrentDirectoryInExePath','Process')
try {
    Remove-Item -LiteralPath Env:NoDefaultCurrentDirectoryInExePath -ErrorAction SilentlyContinue
    & py -3 -B (Join-Path $source 'tests/run_gui_audio_trigger_wire.py') --candidate-rev $B5Commit --baseline-rev $control --output-dir $out
    if ($LASTEXITCODE -ne 0) { throw 'Audio fixture did not pass all three executed modes.' }
} finally {
    if($hadNoDefault) { Set-Item -LiteralPath Env:NoDefaultCurrentDirectoryInExePath -Value ([string]$oldNoDefault) }
    else { Remove-Item -LiteralPath Env:NoDefaultCurrentDirectoryInExePath -ErrorAction SilentlyContinue }
}
$fixture=Get-Content -LiteralPath (Join-Path $out 'fixture.json') -Raw | ConvertFrom-Json
if($fixture.status -cne 'pass' -or $fixture.candidate_revision -cne $B5Commit -or $fixture.baseline_revision -cne $control -or
   !$fixture.witnesses.candidate_pass -or !$fixture.witnesses.baseline_negative_expected -or !$fixture.witnesses.id_only_negative_expected) { throw 'Audio fixture binding/witnesses differ.' }
$rows=@{}
foreach($mode in @('candidate','baseline','id_only')) {
    $folder=Join-Path $out $mode
    $result=Get-Content -LiteralPath (Join-Path $folder 'result.json') -Raw | ConvertFrom-Json
    $exit=if($mode -ceq 'candidate'){0}else{1}
    $rev=if($mode -ceq 'baseline'){$control}else{$B5Commit}
    if($result.mode -cne $mode -or $result.source_tree -cne $rev -or $result.process_exit_code -ne $exit -or
       $result.assertion_count -ne 0 -or $result.numeric.checks -le 0 -or
       ($mode -ceq 'candidate' -and $result.numeric.failures -ne 0) -or
       ($mode -cne 'candidate' -and $result.numeric.failures -le 0)) { throw "Audio executed result differs: $mode" }
    $exe=Join-Path $folder 'regression.exe'
    if((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant() -cne $result.executable_sha256) { throw "Audio executable hash differs: $mode" }
    $stdout=Get-Content -LiteralPath (Join-Path $folder 'run.stdout.txt') -Raw
    $marker=if($mode -ceq 'baseline'){'EXPECTED_BASELINE_NEGATIVE id=201 size=112 cache201=1 message=128 assertions=0'}elseif($mode -ceq 'id_only'){'EXPECTED_ID_ONLY_NEGATIVE id=457 size=112 message=116 payload_match=0 assertions=0'}else{$null}
    if($marker -and [regex]::Matches($stdout,'(?m)^'+[regex]::Escape($marker)+'\r?$').Count -ne 1) { throw "Audio exact failure control absent: $mode" }
    $rows[$mode]=@{revision=$rev;checks=$result.numeric.checks;failures=$result.numeric.failures;assertions=0;exit_code=$result.process_exit_code;executable_sha256=$result.executable_sha256}
}
foreach($p in $pins.Keys) { if ((LfHash (Join-Path $source $p)) -cne $pins[$p]) { throw "Audio harness changed: $p" } }
Assert-Clean
@{schema=1;status='pass';candidate=$B5Commit;baseline=$control;workflow=(& git -C $root rev-parse HEAD);runner='windows-2022';jobs=4;
  harness_lf_pins=$pins;variants=$rows;fixture_sha256=(Get-FileHash -LiteralPath (Join-Path $out 'fixture.json') -Algorithm SHA256).Hash.ToLowerInvariant();
  limits='Source-extracted audio/inbox owner fixture; no audible playback, whole GUI lifecycle or native debug-site certification.'} |
    ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $out 'hosted-receipt.json') -Encoding utf8
Write-Output 'GUI audio trigger wire: candidate and both executed failure controls pass.'
