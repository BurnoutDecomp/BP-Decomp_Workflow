<#
Build/check an exact b5 commit on the hosted Windows runner, using the shipping
bat/compile_exe path. No assets, gameplay, publishing, releases or server calls.
The parent gitlink override is intentional, recorded and never committed.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $B5Commit,
    [Parameter(Mandatory)] [string] $WorkflowSha,
    [ValidateRange(1, 8)] [int] $Jobs = 4
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
$ExitCode = 1
$NativeFailureCode = 0
$Receipt = [ordered]@{
    requested_b5_commit = $B5Commit; workflow_sha = $WorkflowSha
    workflow_ref = $env:CANDIDATE_WORKFLOW_REF; runner_label = 'windows-2022'
    runner_name = $env:RUNNER_NAME; image_os = $env:ImageOS; image_version = $env:ImageVersion
    run_id = $env:GITHUB_RUN_ID; run_attempt = $env:GITHUB_RUN_ATTEMPT
    started_utc = [DateTime]::UtcNow.ToString('o'); jobs = $Jobs; validated = $false
    attribution = 'Detached b5 candidate overrides the parent gitlink when different; no commit is made.'
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

    $clPath = (Get-Command cl.exe -CommandType Application).Source
    $linkPath = (Get-Command link.exe -CommandType Application).Source
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
    Assert-CleanTrees

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
    $Receipt.validated = $true
    $ExitCode = 0
} catch {
    if ($NativeFailureCode -ne 0) { $ExitCode = $NativeFailureCode }
    $Receipt.failure = $_.Exception.Message
    Write-Warning $Receipt.failure
} finally {
    $Receipt.native_commands = $NativeCommands.ToArray()
    $Receipt.exit_code = $ExitCode
    $Receipt.finished_utc = [DateTime]::UtcNow.ToString('o')
    $Receipt.outputs = @{}
    foreach ($name in $OutputNames) {
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
