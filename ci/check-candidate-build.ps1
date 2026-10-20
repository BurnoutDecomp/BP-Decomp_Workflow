<#
Build/check an exact b5 commit on the hosted Windows runner, using the shipping
bat/compile_exe path. No assets, gameplay, publishing, releases or server calls.
The parent gitlink override is intentional, recorded and never committed.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $B5Commit,
    [Parameter(Mandatory)] [string] $WorkflowSha,
    [ValidateRange(1, 8)] [int] $Jobs = 4,
    [switch] $RunRegressions,
    [switch] $RunAptLifetime,
    [switch] $RunHudRegressions,
    [switch] $RunResourceRegressions,
    [switch] $RunGuiIORegressions
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_OS -ne 'Windows' -or
    $env:CANDIDATE_RUNNER_ENVIRONMENT -ne 'github-hosted') {
    throw 'Candidate builds run only on the GitHub-hosted Windows runner.'
}

$Root = Split-Path -Parent $PSScriptRoot
$SourceRoot = Join-Path $Root 'b5-decomp'
$WorkRoot = Join-Path $Root 'build/candidate'
$ArtifactRoot = Join-Path $WorkRoot 'artifacts'
$GameOut = Join-Path $Root 'build/game'
New-Item -ItemType Directory -Force -Path $ArtifactRoot | Out-Null
$NativeCommands = [System.Collections.Generic.List[object]]::new()
$RuntimeOutputs = @{}
$ExitCode = 1
$NativeFailureCode = 0
$Receipt = [ordered]@{
    requested_b5_commit = $B5Commit; workflow_sha = $WorkflowSha
    workflow_ref = $env:CANDIDATE_WORKFLOW_REF; runner_label = 'windows-2022'
    runner_name = $env:RUNNER_NAME; image_os = $env:ImageOS; image_version = $env:ImageVersion
    run_id = $env:GITHUB_RUN_ID; run_attempt = $env:GITHUB_RUN_ATTEMPT
    started_utc = [DateTime]::UtcNow.ToString('o'); jobs = $Jobs; validated = $false
    attribution = 'Detached b5 candidate overrides the parent gitlink when different; no commit is made.'
    regressions = @{ requested = [bool]($RunRegressions -or $RunAptLifetime -or $RunHudRegressions -or $RunResourceRegressions -or $RunGuiIORegressions); status = 'not_requested'; inputs = @{}; negative_controls = @{}; gui_io_status = 'not_requested'; hud_status = 'not_requested'; remaining_status = 'not_requested' }
}
$OutputNames = @('Burnout_PC.exe', 'Burnout_PC.map', 'Burnout_PC.cgsmap', 'Burnout_PC.exe.provenance.json')

function Invoke-Native([string] $Command, [string[]] $Arguments, [string] $LogName) {
    & $Command @Arguments 2>&1 | Tee-Object -FilePath (Join-Path $ArtifactRoot $LogName) -Append | Out-Host
    $code = $LASTEXITCODE
    $script:NativeCommands.Add(@{ command = $Command; arguments = $Arguments; exit_code = $code })
    if ($code -ne 0) {
        $script:NativeFailureCode = $code
        throw "$Command failed with native exit code $code; see $LogName"
    }
}
function Get-GitText([string[]] $GitArguments) {
    $lines = & git @GitArguments 2>&1
    $code = $LASTEXITCODE
    $script:NativeCommands.Add(@{ command = 'git'; arguments = $GitArguments; exit_code = $code })
    if ($code -ne 0) {
        $script:NativeFailureCode = $code
        throw "git failed with native exit code ${code}: $($lines -join ' ')"
    }
    return ($lines -join "`n").TrimEnd()
}
function Assert-CleanTrees {
    if ((Get-GitText @('-C', $Root, 'rev-parse', 'HEAD')) -ne $WorkflowSha) { throw 'Workflow checkout changed.' }
    $sourceStatus = Get-GitText @('-C', $SourceRoot, 'status', '--porcelain=v1', '--untracked-files=all', '--ignore-submodules=none')
    if ($sourceStatus) { throw "Candidate source/dependencies changed: $sourceStatus" }
    if ((Get-GitText @('-C', $SourceRoot, 'rev-parse', 'HEAD')) -ne $B5Commit -or
        (Get-GitText @('-C', $SourceRoot, 'rev-parse', '--abbrev-ref', 'HEAD')) -ne 'HEAD') {
        throw 'Candidate must remain at the requested detached commit.'
    }
    $parentStatus = Get-GitText @('-C', $Root, 'status', '--porcelain=v1', '--untracked-files=all', '--ignore-submodules=none')
    $expectedStatus = if ($Receipt.gitlink_overridden) { ' M b5-decomp' } else { '' }
    if ($parentStatus -cne $expectedStatus) { throw "Unexpected parent changes: $parentStatus" }
    $Receipt.source_status = $sourceStatus
    $Receipt.parent_status = $parentStatus
}
function Get-FileRecord([string] $Path) {
    return @{ bytes = (Get-Item -LiteralPath $Path).Length; sha256 = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
}

Push-Location $Root
try {
    foreach ($sha in @($B5Commit, $WorkflowSha)) {
        if ($sha -cnotmatch '\A[0-9a-fA-F]{40}\z') { throw 'Both inputs must be exact 40-hex commit SHAs.' }
    }
    $B5Commit = $B5Commit.ToLowerInvariant()
    $WorkflowSha = $WorkflowSha.ToLowerInvariant()
    $Receipt.parent_head = Get-GitText @('rev-parse', 'HEAD')
    if ($Receipt.parent_head -ne $WorkflowSha) { throw 'Checkout does not match the workflow SHA.' }
    if (Get-GitText @('status', '--porcelain=v1', '--untracked-files=all', '--ignore-submodules=none')) {
        throw 'Parent checkout must start clean.'
    }
    $gitlink = Get-GitText @('ls-tree', 'HEAD', '--', 'b5-decomp')
    if ($gitlink -notmatch '\A160000 commit ([0-9a-f]{40})\tb5-decomp\z') { throw 'Expected the b5-decomp gitlink.' }
    $Receipt.parent_gitlink = $Matches[1]
    $Receipt.gitlink_overridden = $Receipt.parent_gitlink -ne $B5Commit

    # Same two-level dependency selection as the publisher; no recursive test trees.
    Invoke-Native git @('config', '--global', 'core.longpaths', 'true') 'source.log'
    Invoke-Native git @('config', '--global', 'url.https://github.com/.insteadOf', 'git@github.com:') 'source.log'
    Invoke-Native git @('submodule', 'update', '--init', '--checkout', 'b5-decomp') 'source.log'
    Invoke-Native git @('-C', $SourceRoot, 'fetch', '--recurse-submodules=no', '--no-tags', '--depth=1', 'origin', $B5Commit) 'source.log'
    if ((Get-GitText @('-C', $SourceRoot, 'cat-file', '-t', $B5Commit)) -ne 'commit') { throw 'Candidate is not a commit object.' }
    Invoke-Native git @('-C', $SourceRoot, 'checkout', '--detach', $B5Commit) 'source.log'
    Invoke-Native git @('-C', $SourceRoot, 'submodule', 'update', '--init', '--checkout', 'vendor/EABase', 'vendor/EASTL', 'vendor/EAThread') 'source.log'
    $Receipt.b5_head = Get-GitText @('-C', $SourceRoot, 'rev-parse', 'HEAD')
    $Receipt.required_submodules = Get-GitText @('-C', $SourceRoot, 'submodule', 'status', '--', 'vendor/EABase', 'vendor/EASTL', 'vendor/EAThread')
    Assert-CleanTrees

    $clPath = (Get-Command cl.exe -CommandType Application -All | Select-Object -First 1).Source
    $linkPath = Join-Path (Split-Path -Parent $clPath) 'link.exe'
    if ((Get-Command link.exe -CommandType Application -All | Select-Object -First 1).Source -ne $linkPath) {
        throw 'The linker on PATH must belong to the selected MSVC compiler.'
    }
    $clVersion = [Diagnostics.FileVersionInfo]::GetVersionInfo($clPath)
    if ($env:VSCMD_ARG_TGT_ARCH -ne 'x64' -or $env:VSINSTALLDIR -notmatch '\\2022\\' -or $clVersion.FileMajorPart -ne 19) {
        throw 'Expected the Windows 2022 / Visual Studio 2022 MSVC x64 toolchain.'
    }
    $Receipt.toolchain = @{
        cl_path = $clPath; cl_version = $clVersion.FileVersion; cl_sha256 = (Get-FileRecord $clPath).sha256
        link_path = $linkPath; link_version = [Diagnostics.FileVersionInfo]::GetVersionInfo($linkPath).FileVersion
        link_sha256 = (Get-FileRecord $linkPath).sha256
        vc_tools_version = $env:VCToolsVersion; vs_install_dir = $env:VSINSTALLDIR
        windows_sdk_version = $env:WindowsSDKVersion; ucrt_version = $env:UCRTVersion
    }
    $Receipt.build_inputs = @{}
    foreach ($path in @('.github/workflows/build-candidate.yml', 'ci/check-candidate-build.ps1', 'tools/build/build_game_exe.bat', 'tools/build/compile_exe.py', 'tools/build/msvc_flags.txt', 'tools/build/msvc_includes.txt')) {
        $Receipt.build_inputs[$path] = Get-FileRecord (Join-Path $Root $path)
    }
    Invoke-Native py @('-3', '--version') 'toolchain.log'

    # Independent IO fixtures run before the exe gate; their receipts survive
    # a separate compile/link failure and cannot mark the candidate validated.
    if ($RunGuiIORegressions) {
        $Receipt.regressions.status = 'running'
        $Receipt.regressions.gui_io_status = 'running'
        Remove-Item -LiteralPath Env:NoDefaultCurrentDirectoryInExePath -ErrorAction SilentlyContinue
        foreach ($relative in @('tests/run_gui_model_io.py', 'tests/GuiModelIO.cpp',
                                'tests/run_gui_interpreter_io.py', 'tests/GuiInterpreterIO.cpp')) {
            $Receipt.regressions.inputs[$relative] = Get-FileRecord (Join-Path $SourceRoot $relative)
        }
        $guiIORoot = Join-Path $ArtifactRoot 'gui-io-regressions'
        $guiIOFixtures = @(
            @{ name = 'model'; runner = 'tests/run_gui_model_io.py'; tag = 'GuiModelIO'; checks = 377 },
            @{ name = 'interpreter'; runner = 'tests/run_gui_interpreter_io.py'; tag = 'GuiInterpreterIO'; checks = 169 }
        )
        foreach ($fixture in $guiIOFixtures) {
            $fixtureDir = Join-Path $guiIORoot $fixture.name
            Invoke-Native py @('-3', '-B', (Join-Path $SourceRoot $fixture.runner), '--output-dir', $fixtureDir) 'regressions.log'
            $result = Get-Content -Raw -LiteralPath (Join-Path $fixtureDir 'result.json') | ConvertFrom-Json
            $log = Get-Content -Raw -LiteralPath (Join-Path $fixtureDir 'run.stdout.txt')
            $witness = [regex]::Escape($fixture.tag) + ':\s+' + $fixture.checks + ' checks, 0 failures'
            if ($result.process_exit_code -ne 0 -or $null -eq $result.numeric -or
                $result.numeric.checks -ne $fixture.checks -or $result.numeric.failures -ne 0 -or $log -notmatch $witness) {
                throw "GUI IO fixture $($fixture.name) did not execute its expected numeric checks."
            }
        }
        $guiIOControls = @(
            @{ name = 'model-base-only'; runner = 'tests/run_gui_model_io.py'; flag = '--base-only'; witness = 'FAIL queue is constructed, empty and aligned' },
            @{ name = 'model-retain-view'; runner = 'tests/run_gui_model_io.py'; flag = '--retain-view-events'; witness = 'FAIL queue is constructed, empty and aligned' },
            @{ name = 'interpreter-old-capacity'; runner = 'tests/run_gui_interpreter_io.py'; flag = '--old-capacity'; witness = 'FAIL (ARTIST output event capacity|event record beyond the old)' },
            @{ name = 'interpreter-clear-input'; runner = 'tests/run_gui_interpreter_io.py'; flag = '--clear-input-on-destruct'; witness = 'FAIL input Destruct leaves its complete populated queue unchanged' }
        )
        foreach ($control in $guiIOControls) {
            $controlDir = Join-Path $guiIORoot $control.name
            $logName = 'gui-io-negative-' + $control.name + '.log'
            & py -3 -B (Join-Path $SourceRoot $control.runner) $control.flag --output-dir $controlDir 2>&1 |
                Tee-Object -FilePath (Join-Path $ArtifactRoot $logName) | Out-Host
            $code = $LASTEXITCODE
            $NativeCommands.Add(@{ command = 'py'; arguments = @('-3', '-B', (Join-Path $SourceRoot $control.runner), $control.flag, '--output-dir', $controlDir); exit_code = $code; expected_failure = $true })
            $result = Get-Content -Raw -LiteralPath (Join-Path $controlDir 'result.json') | ConvertFrom-Json
            $log = Get-Content -Raw -LiteralPath (Join-Path $controlDir 'run.stdout.txt')
            if ($code -eq 0 -or $result.process_exit_code -eq 0 -or $null -eq $result.numeric -or
                $result.numeric.checks -lt 1 -or $result.numeric.failures -lt 1 -or $log -notmatch $control.witness) {
                throw "GUI IO negative control $($control.name) failed before its intended behavior witness."
            }
            $Receipt.regressions.negative_controls['gui-io-' + $control.name] = @{ status = 'expected_behavior_failure'; exit_code = $code; log = $logName }
        }
        $Receipt.regressions.gui_io_status = 'pass'
        $Receipt.regressions.status = 'partial_gui_io_pass'
        Assert-CleanTrees
    }

    # HUD fixtures are independent of native GUI platform linking. Preserve
    # execution receipts before the exe gate, without validating a partial candidate.
    if ($RunHudRegressions) {
        $Receipt.regressions.status = 'running'
        $Receipt.regressions.hud_status = 'running'
        Remove-Item -LiteralPath Env:NoDefaultCurrentDirectoryInExePath -ErrorAction SilentlyContinue
        foreach ($relative in @('tests/run_fxgs_hud_crashes.py', 'tests/FxGsHudCrashes.cpp',
                                'tests/run_fxgs_online_roadrage_hud.py', 'tests/FxGsOnlineRoadRageHud.cpp',
                                'tests/fxgs_common.py')) {
            $Receipt.regressions.inputs[$relative] = Get-FileRecord (Join-Path $SourceRoot $relative)
        }
        $hudRoot = Join-Path $ArtifactRoot 'hud-regressions'
        $hudFixtures = @(
            @{ name = 'crashes'; runner = 'tests/run_fxgs_hud_crashes.py'; tag = 'FxGsHudCrashes'; checks = 38 },
            @{ name = 'road-rage'; runner = 'tests/run_fxgs_online_roadrage_hud.py'; tag = 'FxGsOnlineRoadRageHud'; checks = 19 }
        )
        foreach ($fixture in $hudFixtures) {
            $fixtureDir = Join-Path $hudRoot $fixture.name
            Invoke-Native py @('-3', '-B', (Join-Path $SourceRoot $fixture.runner), '--output-dir', $fixtureDir) 'regressions.log'
            $result = Get-Content -Raw -LiteralPath (Join-Path $fixtureDir 'result.json') | ConvertFrom-Json
            $log = Get-Content -Raw -LiteralPath (Join-Path $fixtureDir 'run.stdout.txt')
            $witness = [regex]::Escape($fixture.tag) + ':\s+' + $fixture.checks + ' checks, 0 failures'
            if ($result.process_exit_code -ne 0 -or $null -eq $result.numeric -or
                $result.numeric.checks -ne $fixture.checks -or $result.numeric.failures -ne 0 -or $log -notmatch $witness) {
                throw "HUD fixture $($fixture.name) did not execute its expected numeric checks."
            }
        }
        $hudControls = @(
            @{ name = 'legacy-team-predicate'; runner = 'tests/run_fxgs_online_roadrage_hud.py'; flag = '--legacy-team-predicate'; checks = 19; witness = 'FAIL: 164 first team != 1 remains eligible' },
            @{ name = 'omit-team-tail'; runner = 'tests/run_fxgs_hud_crashes.py'; flag = '--omit-team-tail'; checks = 38; witness = 'FAIL: team-change tail posts ordered 254 records outside mode-specific arms' }
        )
        foreach ($control in $hudControls) {
            $controlDir = Join-Path $hudRoot $control.name
            $logName = 'hud-negative-' + $control.name + '.log'
            & py -3 -B (Join-Path $SourceRoot $control.runner) $control.flag --output-dir $controlDir 2>&1 |
                Tee-Object -FilePath (Join-Path $ArtifactRoot $logName) | Out-Host
            $code = $LASTEXITCODE
            $NativeCommands.Add(@{ command = 'py'; arguments = @('-3', '-B', (Join-Path $SourceRoot $control.runner), $control.flag, '--output-dir', $controlDir); exit_code = $code; expected_failure = $true })
            $result = Get-Content -Raw -LiteralPath (Join-Path $controlDir 'result.json') | ConvertFrom-Json
            $log = Get-Content -Raw -LiteralPath (Join-Path $controlDir 'run.stderr.txt')
            if ($code -eq 0 -or $result.process_exit_code -eq 0 -or $null -eq $result.numeric -or
                $result.numeric.checks -ne $control.checks -or $result.numeric.failures -lt 1 -or -not $log.Contains($control.witness)) {
                throw "HUD negative control $($control.name) failed before its intended behavior witness."
            }
            $Receipt.regressions.negative_controls['hud-' + $control.name] = @{ status = 'expected_behavior_failure'; exit_code = $code; log = $logName }
        }
        $Receipt.regressions.hud_status = 'pass'
        $Receipt.regressions.status = 'partial_selected_fixtures_pass'
        Assert-CleanTrees
    }

    # Proven publisher prerequisites: release FFmpeg, NuGet XAudio2, vendored Lua.
    $ffmpeg = Join-Path $SourceRoot 'vendor/ffmpeg-build'
    $archive = Join-Path $WorkRoot 'ffmpeg-build.zip'
    Invoke-Native gh @('release', 'download', 'ffmpeg-prebuilt', '--repo', 'BurnoutDecomp/FFmpeg-Xenia-new', '-p', 'ffmpeg-build.zip', '-O', $archive) 'dependencies.log'
    Expand-Archive -LiteralPath $archive -DestinationPath $ffmpeg -Force
    if (-not (Test-Path -LiteralPath (Join-Path $ffmpeg 'bin/avcodec.lib'))) { throw 'Prebuilt FFmpeg import library is missing.' }
    Invoke-Native cmd.exe @('/d', '/c', ('"{0}"' -f (Join-Path $Root 'tools/build/fetch_xaudio2_redist.bat'))) 'dependencies.log'
    $lua = Join-Path $SourceRoot 'vendor/lua/lua515.lib'
    if (-not (Test-Path -LiteralPath $lua)) {
        Invoke-Native cmd.exe @('/d', '/c', ('"{0}"' -f (Join-Path $Root 'tools/build/build_lua.bat'))) 'lua.log'
    }
    $Receipt.dependencies = @{
        ffmpeg_release = 'BurnoutDecomp/FFmpeg-Xenia-new/ffmpeg-prebuilt'
        archive = Get-FileRecord $archive; lua = Get-FileRecord $lua
        xaudio2_version = (Get-Content -LiteralPath (Join-Path $SourceRoot 'vendor/xaudio2redist/VERSION.txt') -Raw).Trim()
        xaudio2_header = Get-FileRecord (Join-Path $SourceRoot 'vendor/xaudio2redist/include/xaudio2Redist.h')
    }
    # Match the shipping bat's two runtime staging sources. Include exactly these
    # DLLs in the build artifact so a playable install has the matching binaries.
    $ffmpegDlls = @(Get-ChildItem -LiteralPath (Join-Path $ffmpeg 'bin') -Filter '*.dll' -File)
    if ($ffmpegDlls.Count -eq 0) { throw 'Prebuilt FFmpeg runtime DLLs are missing.' }
    $runtimeFiles = @($ffmpegDlls) + @(Get-Item -LiteralPath (Join-Path $SourceRoot 'vendor/xaudio2redist/bin/x64/xaudio2_9redist.dll'))
    foreach ($file in $runtimeFiles) {
        if ($RuntimeOutputs.ContainsKey($file.Name)) { throw "Duplicate runtime name: $($file.Name)" }
        $RuntimeOutputs[$file.Name] = Get-FileRecord $file.FullName
    }
    $Receipt.expected_runtime_outputs = $RuntimeOutputs
    Assert-CleanTrees

    # Source-body fixtures need their own dependencies, not a successful shipping
    # link. Retain their results independently of native platform-provider failures.
    if ($RunRegressions -or $RunAptLifetime -or $RunResourceRegressions) {
        $Receipt.regressions.status = 'running'
        $Receipt.regressions.remaining_status = 'running'
        $Receipt.regressions.coverage = 'Selected production-body fixtures with IO/heap doubles; callback wiring is source-only. No game or end-to-end parity claim.'
        foreach ($relative in @('tests/run_profile_delivery.py', 'tests/ProfileDelivery.cpp',
                                'tests/run_fxgs2_gui_iface.py', 'tests/FxGs2GuiIface.cpp',
                                'tests/fxgs_common.py')) {
            $Receipt.regressions.inputs[$relative] = Get-FileRecord (Join-Path $SourceRoot $relative)
        }
        # The fixture executables live in temporary directories and must resolve
        # their own current directory. Nothing invokes the game or window input.
        Remove-Item -LiteralPath Env:NoDefaultCurrentDirectoryInExePath -ErrorAction SilentlyContinue
        if ($RunRegressions) {
            foreach ($runner in @('tests/run_profile_delivery.py', 'tests/run_fxgs2_gui_iface.py')) {
                Invoke-Native py @('-3', '-B', (Join-Path $SourceRoot $runner)) 'regressions.log'
            }
        }
        if ($RunAptLifetime) {
            foreach ($relative in @('tests/run_pc_bundle_ownership.py', 'tests/PCBundleOwnership.cpp')) {
                $Receipt.regressions.inputs[$relative] = Get-FileRecord (Join-Path $SourceRoot $relative)
            }
            $aptRunner = Join-Path $SourceRoot 'tests/run_pc_bundle_ownership.py'
            Invoke-Native py @('-3', '-B', $aptRunner) 'regressions.log'
            $controls = @(
                @{ flag = '--omit-apt-retain'; witness = 'FAIL\s+(Apt pin holds every member|logical unload preserves)' },
                @{ flag = '--require-new-apt-resources'; witness = 'FAIL[^\r\n]*(reload|lead|acquire)' }
            )
            $helpArguments = @('-3', '-B', $aptRunner, '--help')
            $aptHelp = & py @helpArguments 2>&1
            $helpCode = $LASTEXITCODE
            $NativeCommands.Add(@{ command = 'py'; arguments = $helpArguments; exit_code = $helpCode })
            if ($helpCode -ne 0) { throw 'APT runner capability check failed.' }
            if (($aptHelp -join "`n") -match '--legacy-free-state-offset') {
                $Receipt.regressions.inputs['tests/pc_apt_callback_fixture.h'] = Get-FileRecord (Join-Path $SourceRoot 'tests/pc_apt_callback_fixture.h')
                $controls += @{ flag = '--legacy-free-state-offset'; witness = 'FAIL[^\r\n]*(FreeAnimation|state|offset|const)' }
            }
            foreach ($control in $controls) {
                $logName = 'apt-negative' + $control.flag + '.log'
                $logPath = Join-Path $ArtifactRoot $logName
                & py -3 -B $aptRunner $control.flag 2>&1 | Tee-Object -FilePath $logPath | Out-Host
                $controlCode = $LASTEXITCODE
                $NativeCommands.Add(@{ command = 'py'; arguments = @('-3', '-B', $aptRunner, $control.flag); exit_code = $controlCode; expected_failure = $true })
                $controlLog = Get-Content -Raw -LiteralPath $logPath
                if ($controlCode -eq 0 -or $controlLog -notmatch $control.witness) {
                    throw "APT negative control $($control.flag) did not expose its intended runtime ownership/GUI failure."
                }
                $Receipt.regressions.negative_controls[$control.flag] = @{ status = 'expected_behavior_failure'; exit_code = $controlCode; log = $logName }
            }
        }
        if ($RunResourceRegressions) {
            foreach ($relative in @('tests/run_pool_create_protocol.py', 'tests/PoolCreateProtocol.cpp',
                                    'tests/run_pc_resource_shuttle.py', 'tests/PCResourceShuttle.cpp',
                                    'tests/run_game_data_pool_hierarchy.py', 'tests/GameDataPoolHierarchy.cpp',
                                    'tests/run_pc_gui_pool_acquire.py', 'tests/PCGuiPoolAcquire.cpp')) {
                $Receipt.regressions.inputs[$relative] = Get-FileRecord (Join-Path $SourceRoot $relative)
            }
            $resourceRoot = Join-Path $ArtifactRoot 'resource-regressions'
            $poolRunner = Join-Path $SourceRoot 'tests/run_pool_create_protocol.py'
            $poolPositive = Join-Path $resourceRoot 'pool-positive'
            Invoke-Native py @('-3', '-B', $poolRunner, '--output-dir', $poolPositive) 'regressions.log'
            $poolResult = Get-Content -Raw -LiteralPath (Join-Path $poolPositive 'result.json') | ConvertFrom-Json
            if (@($poolResult.results).Count -ne 2) { throw 'Pool fixture must execute both protocol and layout modes.' }
            foreach ($mode in @('protocol', 'layout')) {
                $modeResult = @($poolResult.results | Where-Object mode -eq $mode)
                $modeLog = Get-Content -Raw -LiteralPath (Join-Path $poolPositive "$mode/run.stdout.txt")
                if ($modeResult.Count -ne 1 -or -not $modeResult[0].compiled -or $modeResult[0].exit_code -ne 0 -or
                    $modeLog -notmatch 'PoolCreateProtocol:\s+[1-9][0-9]* checks, 0 failures; mode=') {
                    throw "Pool positive fixture did not execute successfully in $mode mode."
                }
            }
            $resourceFixtures = @(
                @{ runner = 'tests/run_pc_resource_shuttle.py'; tag = 'PCResourceShuttle'; name = 'shuttle'; checks = 14 },
                @{ runner = 'tests/run_pc_gui_pool_acquire.py'; tag = 'PCGuiPoolAcquire'; name = 'gui-acquire'; checks = 27 }
            )
            foreach ($fixture in $resourceFixtures) {
                $fixtureDir = Join-Path $resourceRoot $fixture.name
                Invoke-Native py @('-3', '-B', (Join-Path $SourceRoot $fixture.runner), '--output-dir', $fixtureDir) 'regressions.log'
                $fixtureResult = Get-Content -Raw -LiteralPath (Join-Path $fixtureDir 'result.json') | ConvertFrom-Json
                $fixtureLog = Get-Content -Raw -LiteralPath (Join-Path $fixtureDir 'run.stdout.txt')
                $fixtureWitness = [regex]::Escape($fixture.tag) + ':\s+' + $fixture.checks + ' checks, 0 failures'
                if ($fixtureResult.process_exit_code -ne 0 -or $null -eq $fixtureResult.numeric -or
                    $fixtureResult.numeric.checks -ne $fixture.checks -or $fixtureResult.numeric.failures -ne 0 -or
                    $fixtureLog -notmatch $fixtureWitness) {
                    throw "Resource fixture $($fixture.name) did not execute its expected positive numeric checks."
                }
            }
            Invoke-Native py @('-3', '-B', (Join-Path $SourceRoot 'tests/run_game_data_pool_hierarchy.py'),
                '--output-dir', (Join-Path $resourceRoot 'game-data-hierarchy')) 'regressions.log'
            $poolControls = @(
                @{ name = 'tag10'; mode = 'protocol'; witness = 'FAIL[^\r\n]*tag10' },
                @{ name = 'event-sentinel'; mode = 'protocol'; witness = 'FAIL[^\r\n]*(tag.?-1|unacquire|sentinel)' },
                @{ name = 'batch-count'; mode = 'layout'; witness = 'FAIL[^\r\n]*(Entry carve|guard|batch)' },
                @{ name = 'shared-buffer'; mode = 'protocol'; witness = 'FAIL[^\r\n]*(formatting buffers|isolated message|shared buffer)' }
            )
            foreach ($control in $poolControls) {
                $controlDir = Join-Path $resourceRoot ('pool-negative-' + $control.name)
                $controlLogName = 'pool-negative-' + $control.name + '.log'
                & py -3 -B $poolRunner --negative $control.name --output-dir $controlDir 2>&1 |
                    Tee-Object -FilePath (Join-Path $ArtifactRoot $controlLogName) | Out-Host
                $controlCode = $LASTEXITCODE
                $NativeCommands.Add(@{ command = 'py'; arguments = @('-3', '-B', $poolRunner, '--negative', $control.name, '--output-dir', $controlDir); exit_code = $controlCode; expected_failure = $true })
                $controlResult = Get-Content -Raw -LiteralPath (Join-Path $controlDir 'result.json') | ConvertFrom-Json
                if (@($controlResult.results).Count -ne 1 -or -not $controlResult.results[0].compiled) {
                    throw "Pool negative control $($control.name) failed before behavioral execution."
                }
                $controlLog = Get-Content -Raw -LiteralPath (Join-Path $controlDir ($control.mode + '/run.stdout.txt'))
                if ($controlCode -eq 0 -or $controlResult.results[0].exit_code -eq 0 -or
                    $controlLog -notmatch 'PoolCreateProtocol:\s+[1-9][0-9]* checks, [1-9][0-9]* failures; mode=' -or
                    $controlLog -notmatch $control.witness) {
                    throw "Pool negative control $($control.name) did not expose its intended behavior failure."
                }
                $Receipt.regressions.negative_controls['pool-' + $control.name] = @{ status = 'expected_behavior_failure'; exit_code = $controlCode; log = $controlLogName }
            }
        }

        Assert-CleanTrees
        $Receipt.regressions.remaining_status = 'pass'
        $Receipt.regressions.status = 'partial_selected_fixtures_pass'
    }

    # Never accept a cached or prior exe/map/stamp as proof of this link.
    foreach ($name in $OutputNames) {
        $path = Join-Path $GameOut $name
        if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
    }
    $env:BRN_EXE_JOBS = [string]$Jobs
    $env:BRN_EXE_HASH_DEPS = '1'
    Invoke-Native cmd.exe @('/d', '/c', ('"{0}"' -f (Join-Path $Root 'tools/build/build_game_exe.bat'))) 'build.log'
    foreach ($name in $OutputNames) {
        $path = Join-Path $GameOut $name
        if (-not (Test-Path -LiteralPath $path) -or (Get-Item -LiteralPath $path).Length -eq 0) { throw "Build output is missing or empty: $name" }
    }
    foreach ($name in $RuntimeOutputs.Keys) {
        $path = Join-Path $GameOut $name
        if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or
            (Get-FileRecord $path).sha256 -ne $RuntimeOutputs[$name].sha256) {
            throw "Staged runtime DLL does not match its dependency: $name"
        }
    }
    $cgsmap = Join-Path $GameOut 'Burnout_PC.cgsmap'
    $reader = [IO.BinaryReader]::new([IO.File]::OpenRead($cgsmap))
    try {
        $count = $reader.ReadUInt32(); $offset = $reader.ReadUInt32()
        $base = $reader.ReadUInt32(); $version = $reader.ReadUInt32()
        if ($count -eq 0 -or $offset -ne 16 -or $base -ne 0 -or $version -ne 1 -or $reader.BaseStream.Length -ne (16L + 128L * $count)) {
            throw 'Cgsmap is empty or incomplete.'
        }
    } finally { $reader.Dispose() }
    $provenance = Get-Content -LiteralPath (Join-Path $GameOut 'Burnout_PC.exe.provenance.json') -Raw | ConvertFrom-Json -AsHashtable
    $exe = Get-FileRecord (Join-Path $GameOut 'Burnout_PC.exe')
    if ($provenance.b5_head -ne $B5Commit -or $provenance.parent_head -ne $WorkflowSha -or
        $provenance.exe_sha256 -ne $exe.sha256 -or $provenance.b5_dirty -isnot [bool] -or $provenance.b5_dirty -ne $false -or
        $provenance.parent_dirty -isnot [bool] -or $provenance.parent_dirty -ne $Receipt.gitlink_overridden) {
        throw 'Provenance does not match the candidate, workflow, clean source and actual exe.'
    }
    Assert-CleanTrees
    if ($Receipt.regressions.requested) { $Receipt.regressions.status = 'pass' }
    $Receipt.validated = $true
    $ExitCode = 0
} catch {
    if ($Receipt.regressions.gui_io_status -eq 'running') { $Receipt.regressions.gui_io_status = 'fail' }
    if ($Receipt.regressions.hud_status -eq 'running') { $Receipt.regressions.hud_status = 'fail' }
    if ($Receipt.regressions.remaining_status -eq 'running') { $Receipt.regressions.remaining_status = 'fail' }
    if ($Receipt.regressions.status -eq 'running') { $Receipt.regressions.status = 'fail' }
    if ($NativeFailureCode -ne 0) { $ExitCode = $NativeFailureCode }
    $Receipt.failure = $_.Exception.Message
    Write-Warning $Receipt.failure
} finally {
    $Receipt.native_commands = $NativeCommands.ToArray()
    $Receipt.exit_code = $ExitCode
    $Receipt.finished_utc = [DateTime]::UtcNow.ToString('o')
    $Receipt.outputs = @{}
    foreach ($name in (@($OutputNames) + @($RuntimeOutputs.Keys))) {
        $path = Join-Path $GameOut $name
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            Copy-Item -LiteralPath $path -Destination (Join-Path $ArtifactRoot $name)
            $Receipt.outputs[$name] = Get-FileRecord $path
        }
    }
    $Receipt | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $ArtifactRoot 'input-receipt.json') -Encoding utf8
    Pop-Location
}
exit $ExitCode
