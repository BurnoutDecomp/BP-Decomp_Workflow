<#
.SYNOPSIS
  Sync the Google Drive assets, build the decomp game exe, bundle exe + runtime
  DLLs + assets, zip, and publish to the BP work server's download button.

.DESCRIPTION
  Runs on a self-hosted Windows runner from the BP-Decomp_Workflow checkout.

  This repo does NOT build the shippable exe with CMake -- the canonical build is
  the bespoke `cl` response-file driver tools\build\build_game_exe.bat, which
  emits build\game\Burnout_PC.exe (the CMake project's Burnout5 target is not the
  shipped artifact). That driver links a prebuilt FFmpeg (movie player) and Lua
  (FSM VM), so this script ensures both exist first.

  Pipeline:
    1. rclone sync : mirror the current Drive folder locally (only changed files
                     transfer; deletions mirror). The runtime asset folders
                     (SOUND, VIDEOS, LANGUAGE, ...) live here, not in git.
    2. manifest    : fingerprint the synced asset set so each build records
                     exactly which assets it shipped.
    3. deps        : build vendored Lua and FFmpeg if their outputs are missing
                     (both are expensive/rare, so they're skipped when present).
    4. game build  : tools\build\build_game_exe.bat -> build\game\Burnout_PC.exe
                     (also copies FFmpeg DLLs beside the exe + writes a .cgsmap).
    5. bundle      : exe + runtime DLLs + .cgsmap at the root, assets alongside.
    6. zip + upload: POST the zip to /admin/builds with an admin X-Work-Token.

  Prerequisites on the runner (beyond MSVC/CMake): a working FFmpeg build
  toolchain (MSYS2 + Strawberry Perl, per tools\build\build_ffmpeg.bat) IF the
  FFmpeg output isn't already cached under b5-decomp\vendor\ffmpeg-build\, and
  `py` on PATH for the .cgsmap step (optional -- skipped if absent).
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $WorkServer,     # e.g. https://adriwin.fr
    [Parameter(Mandatory)] [string] $WorkToken,      # an admin X-Work-Token
    [Parameter(Mandatory)] [string] $RcloneRemote,   # e.g. gdrive:BurnoutParadiseAssets
    [string] $CommitSha = "",
    [string] $Branch = "",
    [string] $AssetsDir = "C:\bp-build\assets",       # persistent across runs -> incremental sync
    [switch] $ForceFfmpeg,                            # rebuild FFmpeg even if cached
    [switch] $ForceLua                               # rebuild Lua even if cached
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Repo root = parent of this script's ci\ folder.
$Root = Split-Path -Parent $PSScriptRoot
$GameOut = Join-Path $Root "build\game"
$ExePath = Join-Path $GameOut "Burnout_PC.exe"
$FfmpegLib = Join-Path $Root "b5-decomp\vendor\ffmpeg-build\avcodec.lib"
$LuaLib = Join-Path $Root "b5-decomp\vendor\lua\lua515.lib"

function Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Invoke-Batch($path) {
    # Run a .bat and surface its exit code (the drivers do `exit /b <err>`).
    & cmd.exe /c "`"$path`""
    if ($LASTEXITCODE -ne 0) { throw "$([System.IO.Path]::GetFileName($path)) failed ($LASTEXITCODE)" }
}

# --- 1. Sync assets from Drive -------------------------------------------------
Step "Syncing assets from $RcloneRemote"
New-Item -ItemType Directory -Force -Path $AssetsDir | Out-Null
# --fast-list keeps Drive API calls down; sync mirrors adds/edits/deletes.
& rclone sync $RcloneRemote $AssetsDir --fast-list --transfers 8 --checkers 16
if ($LASTEXITCODE -ne 0) { throw "rclone sync failed ($LASTEXITCODE)" }

# --- 2. Asset manifest hash ----------------------------------------------------
Step "Fingerprinting assets"
$lines = Get-ChildItem -Path $AssetsDir -Recurse -File | Sort-Object FullName | ForEach-Object {
    $rel = $_.FullName.Substring($AssetsDir.Length).TrimStart('\','/').Replace('\','/')
    $hash = (Get-FileHash -Path $_.FullName -Algorithm MD5).Hash.ToLower()
    "$rel`:$hash"
}
$joined = ($lines -join "`n")
$sha = [System.Security.Cryptography.SHA256]::Create()
$assetManifestHash = ([System.BitConverter]::ToString(
    $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($joined))
) -replace '-', '').ToLower()
Write-Host "    $($lines.Count) asset files, manifest $($assetManifestHash.Substring(0,12))"

# --- 3. Dependencies: Lua + FFmpeg (skip when already built) -------------------
if ($ForceLua -or -not (Test-Path $LuaLib)) {
    Step "Building vendored Lua"
    Invoke-Batch (Join-Path $Root "tools\build\build_lua.bat")
} else {
    Write-Host "==> Lua up to date ($LuaLib)" -ForegroundColor DarkGray
}
if ($ForceFfmpeg -or -not (Test-Path $FfmpegLib)) {
    Step "Building FFmpeg (needs MSYS2 + Strawberry Perl on PATH)"
    Invoke-Batch (Join-Path $Root "tools\build\build_ffmpeg.bat")
} else {
    Write-Host "==> FFmpeg up to date ($FfmpegLib)" -ForegroundColor DarkGray
}

# --- 4. Build the game exe -----------------------------------------------------
Step "Building game exe"
Invoke-Batch (Join-Path $Root "tools\build\build_game_exe.bat")
if (-not (Test-Path $ExePath)) { throw "build succeeded but $ExePath is missing" }
Write-Host "    exe: $ExePath"

# --- 5. Bundle: exe + runtime DLLs + cgsmap at root, assets alongside ----------
Step "Assembling bundle"
$staging = Join-Path $Root "build\bundle"
if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
New-Item -ItemType Directory -Force -Path $staging | Out-Null
Copy-Item $ExePath -Destination $staging
# FFmpeg runtime DLLs that build_game_exe.bat copies next to the exe.
Get-ChildItem -Path $GameOut -Filter *.dll -File | Copy-Item -Destination $staging
# Assert call-stack resolver map (small, handy for triaging crash reports).
$cgsmap = Join-Path $GameOut "Burnout_PC.cgsmap"
if (Test-Path $cgsmap) { Copy-Item $cgsmap -Destination $staging }
# Game data folders (from Drive) land at the bundle root, next to the exe.
Copy-Item -Path (Join-Path $AssetsDir '*') -Destination $staging -Recurse -Force

# --- 6. Zip --------------------------------------------------------------------
Step "Zipping"
$zip = Join-Path $Root "build\burnout-build.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
$sevenZip = Get-Command 7z -ErrorAction SilentlyContinue
if ($sevenZip) {
    & 7z a -tzip -mx=5 $zip (Join-Path $staging '*') | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "7z failed ($LASTEXITCODE)" }
} else {
    # Compress-Archive is fine for modest bundles; install 7-Zip for large/fast zips.
    Compress-Archive -Path (Join-Path $staging '*') -DestinationPath $zip -CompressionLevel Optimal
}
$size = (Get-Item $zip).Length
Write-Host "    $zip ($([math]::Round($size / 1MB, 1)) MB)"

# --- 7. Publish ----------------------------------------------------------------
Step "Publishing to $WorkServer"
if (-not $CommitSha) { $CommitSha = (& git rev-parse HEAD).Trim() }
$short = if ($CommitSha) { $CommitSha.Substring(0, [Math]::Min(12, $CommitSha.Length)) } else { "" }
$builtAt = (Get-Date).ToUniversalTime().ToString("o")

# curl.exe streams the multipart body straight from disk -- no whole-file buffering,
# so multi-GB zips upload without exhausting runner memory.
& curl.exe --fail --show-error --silent `
    --retry 3 --retry-delay 5 `
    -H "X-Work-Token: $WorkToken" `
    -F "file=@$zip;type=application/zip" `
    -F "commit_sha=$CommitSha" `
    -F "commit_short=$short" `
    -F "branch=$Branch" `
    -F "asset_manifest_hash=$assetManifestHash" `
    -F "built_at=$builtAt" `
    "$WorkServer/admin/builds"
if ($LASTEXITCODE -ne 0) { throw "publish upload failed ($LASTEXITCODE)" }

Write-Host ""
Step "Published build $short ($([math]::Round($size / 1MB, 1)) MB)"
