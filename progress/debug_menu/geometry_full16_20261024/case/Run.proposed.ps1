param([ValidatePattern('^run_full16_[0-9]{8}_[0-9]{6}$')][string]$RunName = ('run_full16_' + (Get-Date).ToString('yyyyMMdd_HHmmss')))
$ErrorActionPreference = 'Stop'
$packetRoot = $PSScriptRoot
$repoRoot = 'D:\Reverse\BP-Decomp_Workflow'
$bindingPath = Join-Path $packetRoot 'BINDING.json'
$stagePath = Join-Path $packetRoot 'STAGING.json'
$reviewPath = Join-Path $packetRoot 'ROOT_PRELAUNCH_REVIEW.json'
foreach ($path in @($bindingPath,$stagePath,$reviewPath)) { if (!(Test-Path -LiteralPath $path -PathType Leaf)) { throw "Root staging receipt is missing: $path" } }
$binding = Get-Content -LiteralPath $bindingPath -Raw | ConvertFrom-Json
$stage = Get-Content -LiteralPath $stagePath -Raw | ConvertFrom-Json
$review = Get-Content -LiteralPath $reviewPath -Raw | ConvertFrom-Json
$plan = Get-Content -LiteralPath (Join-Path $packetRoot 'CASE_PLAN.json') -Raw | ConvertFrom-Json
foreach ($pair in @(
    @{Path=$bindingPath;Hash=$review.binding_sha256},
    @{Path=$stagePath;Hash=$review.stage_sha256},
    @{Path=$PSCommandPath;Hash=$review.run_script_sha256},
    @{Path=(Join-Path $packetRoot 'Case.proposed.ps1');Hash=$review.case_sha256},
    @{Path=(Join-Path $packetRoot 'TargetedGeometryKeys.proposed.ps1');Hash=$review.helper_sha256},
    @{Path=(Join-Path $packetRoot 'checker.proposed.ps1');Hash=$review.checker_sha256},
    @{Path=(Join-Path $packetRoot 'Check_owner.proposed.ps1');Hash=$review.owner_checker_sha256}
)) {
    if (!(Test-Path -LiteralPath $pair.Path -PathType Leaf) -or
        (Get-FileHash -LiteralPath $pair.Path -Algorithm SHA256).Hash.ToLowerInvariant() -cne [string]$pair.Hash) {
        throw "Prelaunch-reviewed file changed: $($pair.Path)"
    }
}
if ($review.status -cne 'ready' -or $stage.status -cne 'staged_not_launched' -or
    [int]$binding.schema -ne 2 -or $binding.status -cne 'root_reviewed_ready' -or
    !$binding.slot_created_for_this_case -or !$stage.created_for_this_case -or
    [int]$stage.slot -ne [int]$binding.slot -or
    $binding.candidate_source -cne $plan.candidate_source -or
    $binding.candidate_tree -cne $plan.candidate_tree -or
    $binding.base_hosted_workflow_source -cne $plan.base_hosted_workflow_source -or
    $binding.base_hosted_401033_exe_sha256 -cne $plan.base_hosted_401033_exe_sha256 -or
    $binding.probe_patch_sha256 -cne (Get-FileHash -LiteralPath (Join-Path $packetRoot 'source/patch.diff') -Algorithm SHA256).Hash.ToLowerInvariant()) {
    throw 'Root prelaunch state, source, patch, or owned private slot differs.'
}
if ($binding.case_source_bindings_sha256 -cne (Get-FileHash -LiteralPath (Join-Path $packetRoot 'CASE_SOURCE_BINDINGS.json') -Algorithm SHA256).Hash.ToLowerInvariant() -or
    $review.source_bindings_sha256 -cne [string]$binding.case_source_bindings_sha256) { throw 'Case source evidence bindings differ from the reviewed source snapshot.' }
if ($binding.execution_exe_sha256 -cne $binding.hosted_probe_build.exe_sha256 -or
    $binding.execution_exe_sha256 -ceq $binding.base_hosted_401033_exe_sha256 -or
    $binding.hosted_probe_build.status -cne 'success') {
    throw 'The staged image is not the newly hosted diagnostic build; base 6950… image is not admissible.'
}
function Assert-FileHash([string]$Name,[string]$Path,[string]$Expected) {
    if ([string]::IsNullOrWhiteSpace($Path) -or !(Test-Path -LiteralPath $Path -PathType Leaf)) { throw "$Name is missing: $Path" }
    if ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $Expected.ToLowerInvariant()) { throw "$Name hash differs." }
}
function Assert-NormalProtected {
    $roster = @(Get-ChildItem -LiteralPath (Join-Path $repoRoot 'build/game') -Directory -Filter 'Memcard*' |
        ForEach-Object { Join-Path $_.FullName 'Profile.sav' } |
        Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Sort-Object)
    if (($roster -join "`n") -ine (@($stage.normal_profile_roster | Sort-Object) -join "`n")) { throw 'Normal profile membership changed.' }
    foreach ($row in $stage.normal_protected_paths) {
        $file = Get-Item -LiteralPath $row.path
        if ($file.PSIsContainer -or ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
            $file.Length -ne [long]$row.bytes -or
            $file.LastWriteTimeUtc.ToFileTimeUtc().ToString() -cne [string]$row.mtime_utc_filetime_ticks -or
            (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -cne [string]$row.sha256) {
            throw "Normal protected path changed: $($row.path)"
        }
    }
}
Assert-NormalProtected
if (@(Get-CimInstance Win32_Process -Filter "Name LIKE 'Burnout%.exe' OR Name='TUB_Burnout_PC_External.exe'").Count -ne 0) { throw 'Another game process is already running.' }
$b5Root = Join-Path $repoRoot 'b5-decomp'
if ((& git -C $repoRoot rev-parse HEAD) -cne [string]$stage.physical_parent -or
    (& git -C $b5Root rev-parse HEAD) -cne [string]$stage.physical_b5) { throw 'Bound physical Git heads changed.' }
& git -C $b5Root diff --quiet
if ($LASTEXITCODE -ne 0) { throw 'Tracked physical B5 source worktree changed.' }
& git -C $b5Root diff --cached --quiet
if ($LASTEXITCODE -ne 0) { throw 'Tracked physical B5 source index changed.' }
$sourceStatus = @(& git -C $b5Root status --porcelain=v1 --untracked-files=all)
if ($LASTEXITCODE -ne 0 -or ($sourceStatus -join "`n") -cne (@($binding.allowed_b5_status) -join "`n")) { throw 'Bound physical source status changed.' }

$privateRoot = [IO.Path]::GetFullPath([string]$binding.private_stage_root)
if ($privateRoot -ine [IO.Path]::GetFullPath((Join-Path $packetRoot 'stage'))) { throw 'Private stage escaped this packet.' }
$gameDir = Join-Path $privateRoot 'slot'
$working = Join-Path $privateRoot 'data'
Assert-FileHash 'staged executable' (Join-Path $gameDir 'Burnout_PC.exe') ([string]$binding.execution_exe_sha256)
Assert-FileHash 'staged config' (Join-Path $gameDir 'config.ini') ([string]$binding.private_config_sha256)
Assert-FileHash 'hosted build receipt' ([string]$binding.hosted_probe_build.receipt_path) ([string]$binding.hosted_probe_build.receipt_sha256)
Assert-FileHash 'stage receipt' ([string]$binding.stage_receipt) ([string]$binding.stage_receipt_sha256)
if (!(Test-Path -LiteralPath $working -PathType Container)) { throw 'Private run data directory is missing.' }
$roster = @(Get-ChildItem -LiteralPath $gameDir | ForEach-Object { $_.Name } | Sort-Object)
if (($roster -join "`n") -cne (@($stage.launch_file_roster | Sort-Object) -join "`n")) { throw 'Private launch roster changed.' }
foreach ($payload in $stage.payloads.PSObject.Properties) {
    Assert-FileHash ('private payload ' + $payload.Name) (Join-Path $gameDir $payload.Name) ([string]$payload.Value.sha256)
    if ((Get-Item -LiteralPath (Join-Path $gameDir $payload.Name)).Length -ne [long]$payload.Value.bytes) { throw "Private payload size differs: $($payload.Name)" }
}
if (Test-Path -LiteralPath (Join-Path $packetRoot $RunName)) { throw 'This private case run already exists; refusing to overwrite it.' }
foreach ($retained in @('full16.stdout.log','full16.stderr.log','RUN_COMPLETION.json')) {
    if (Test-Path -LiteralPath (Join-Path $packetRoot $retained)) { throw "Retained full16 evidence already exists; refusing to overwrite $retained." }
}
$runDir = Join-Path $packetRoot $RunName
New-Item -ItemType Directory -Path $runDir | Out-Null
$env:GEOMETRY_RUNTIME_BINDING = $bindingPath
$env:GEOMETRY_CASE_GROUP = 'full16'
$runnerArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $repoRoot 'tools/tests/run_case.ps1'),
    '-Case',(Join-Path $packetRoot 'Case.proposed.ps1'),'-RunDir',$runDir,'-GameDir',$gameDir,'-WorkingDirectory',$working,
    '-Slot',([string]$binding.slot),'-LockTimeoutSec','10','-Label',('Full16 geometry controls; source=' + $binding.candidate_source))
$quotedArgs = @($runnerArgs | ForEach-Object { '"' + ([string]$_).Replace('"','\"') + '"' }) -join ' '
$runner = $null
$failure = $null
$caseExitCode = $null
$caseCheckFailed = $false
try {
    $runner = Start-Process -FilePath 'powershell.exe' -ArgumentList $quotedArgs -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $packetRoot 'full16.stdout.log') -RedirectStandardError (Join-Path $packetRoot 'full16.stderr.log')
    $retainedRunnerHandle = $runner.Handle
    $runner.PriorityClass = 'BelowNormal'
    if (!$runner.WaitForExit(310000)) { throw 'Single-game full16 runner exceeded the310-second bound; inspect exact owned processes.' }
    if ($null -eq $runner.ExitCode) { throw 'The full16 runner exit code is unavailable.' }
    $caseExitCode = [int]$runner.ExitCode
    if ($caseExitCode -notin @(0,1)) { throw "The full16 case runner failed before a reviewable case result (exit $caseExitCode)." }
    if ($caseExitCode -eq 1) { $caseCheckFailed = $true }
} catch { $failure = $_.Exception.Message }
finally {
    Remove-Item Env:GEOMETRY_RUNTIME_BINDING -ErrorAction SilentlyContinue
    Remove-Item Env:GEOMETRY_CASE_GROUP -ErrorAction SilentlyContinue
    $games = @(Get-CimInstance Win32_Process -Filter "Name LIKE 'Burnout%.exe' OR Name='TUB_Burnout_PC_External.exe'")
    $runnerExited = $false
    if ($runner) { try { $runner.Refresh(); $runnerExited = $runner.HasExited } catch {} }
    if ($games.Count -ne 0) { $failure = 'Game exit is unconfirmed; private config is not restored.' }
    if (!$runnerExited) { $failure = 'Owned case runner exit is unconfirmed; private config is not restored.' }
    if ($games.Count -eq 0 -and $runnerExited) {
        Copy-Item -LiteralPath (Join-Path $privateRoot 'config.seed.ini') -Destination (Join-Path $gameDir 'config.ini') -Force
    }
    Assert-NormalProtected
    [ordered]@{status=$(if($failure){'native_failed'}else{'native_finished_pending_root_visual_review'});failure=$failure;case_exit_code=$caseExitCode;case_checks_failed=$caseCheckFailed;remaining_games=$games.Count;normal_protected_unchanged=$true;utc=[DateTime]::UtcNow.ToString('o')} |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $packetRoot 'RUN_COMPLETION.json') -Encoding UTF8
}
if ($failure) { throw $failure }
