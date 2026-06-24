<#
  tools/build/build_tools.ps1 - build the project's buildable tools into build/tools/.

    build/tools/yap/         YAP.exe + its Qt6 runtime (windeployqt drops the DLLs + plugins)
    build/tools/volatility/  Volatility.Cli.exe (+ its content, e.g. tools/dxc)

  The rest of tools/ are Python scripts (no build step). Intermediate CMake output lives in
  build/_obj/ so build/tools/ holds only the runnable binaries.

  YAP needs Qt6 (Core). The Qt prefix is resolved in this order:
    1. -QtPrefix <path>
    2. $env:QT6_DIR
    3. $env:CMAKE_PREFIX_PATH
    4. auto-detect the newest  C:\Qt\6.*\msvc*_64

  Usage:
    pwsh tools/build/build_tools.ps1                       # build both (auto-detect Qt)
    pwsh tools/build/build_tools.ps1 -QtPrefix C:\Qt\6.7.0\msvc2022_64
    pwsh tools/build/build_tools.ps1 -SkipYap             # volatility only
    pwsh tools/build/build_tools.ps1 -SkipVolatility      # YAP only
#>
param(
    [string]$QtPrefix = "",
    [switch]$SkipYap,
    [switch]$SkipVolatility
)
$ErrorActionPreference = "Stop"

$Root     = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$OutTools = Join-Path $Root "build\tools"
$ObjDir   = Join-Path $Root "build\_obj"
New-Item -ItemType Directory -Force -Path $OutTools | Out-Null

# ---- volatility (C# / .NET 9) ---------------------------------------------------------
if (-not $SkipVolatility) {
    Write-Host "==== Building volatility ====" -ForegroundColor Cyan
    $volProj = Join-Path $Root "tools\volatility\src\Volatility.Cli\Volatility.Cli.csproj"
    $volOut  = Join-Path $OutTools "volatility"
    # Framework-dependent publish (the user already has the .NET SDK). Single-file/trim are turned
    # off here so the reflection-driven resource registration can't be trimmed away at runtime; the
    # csproj's single-file/trimmed settings remain available for a standalone release publish.
    dotnet publish $volProj -c Release -o $volOut --nologo -p:PublishSingleFile=false -p:PublishTrimmed=false
    if ($LASTEXITCODE -ne 0) { throw "volatility build failed (exit $LASTEXITCODE)." }
    Write-Host "volatility -> $volOut\Volatility.Cli.exe" -ForegroundColor Green
}

# ---- YAP (C++ / Qt6 / CMake) ----------------------------------------------------------
if (-not $SkipYap) {
    Write-Host "==== Building YAP ====" -ForegroundColor Cyan
    if (-not $QtPrefix) {
        if ($env:QT6_DIR)               { $QtPrefix = $env:QT6_DIR }
        elseif ($env:CMAKE_PREFIX_PATH) { $QtPrefix = $env:CMAKE_PREFIX_PATH }
        else {
            $cand = Get-ChildItem "C:\Qt\6.*\msvc*_64" -Directory -ErrorAction SilentlyContinue |
                    Sort-Object Name -Descending | Select-Object -First 1
            if ($cand) { $QtPrefix = $cand.FullName }
        }
    }
    if (-not $QtPrefix -or -not (Test-Path $QtPrefix)) {
        throw "Qt6 not found. Pass -QtPrefix <path> (e.g. C:\Qt\6.7.0\msvc2022_64), set `$env:QT6_DIR, or install Qt under C:\Qt."
    }
    Write-Host "Qt6 prefix: $QtPrefix"

    $yapSrc   = Join-Path $Root "tools\yap"
    $yapBuild = Join-Path $ObjDir "yap"
    cmake -S $yapSrc -B $yapBuild -G "Visual Studio 17 2022" -A x64 "-DCMAKE_PREFIX_PATH=$QtPrefix"
    if ($LASTEXITCODE -ne 0) { throw "YAP CMake configure failed (exit $LASTEXITCODE)." }
    cmake --build $yapBuild --config Release
    if ($LASTEXITCODE -ne 0) { throw "YAP build failed (exit $LASTEXITCODE)." }

    $yapRelease = Join-Path $yapBuild "Release"
    $yapOut     = Join-Path $OutTools "yap"
    if (Test-Path $yapOut) { Remove-Item $yapOut -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $yapOut | Out-Null
    # YAP.exe + the Qt6 runtime windeployqt placed beside it (Qt6Core.dll, platforms\, etc.).
    Copy-Item (Join-Path $yapRelease "*") $yapOut -Recurse -Force -Exclude *.ilk,*.exp,*.lib
    Write-Host "YAP -> $yapOut\YAP.exe" -ForegroundColor Green
}

Write-Host "==== Tools built into $OutTools ====" -ForegroundColor Cyan
