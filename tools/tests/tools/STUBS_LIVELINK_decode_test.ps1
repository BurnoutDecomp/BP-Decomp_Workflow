# STUBS_LIVELINK_decode_test.ps1 -- build and run the AttribSys live-link decoder unit test.
#
#   powershell -ExecutionPolicy Bypass -File tools\tests\tools\STUBS_LIVELINK_decode_test.ps1
#
# Compiles STUBS_LIVELINK_decode_test.cpp (which compiles attriblivelink.cpp into itself) with the
# canonical exe flags/includes, links the real attribute hash + the vendor EASTL red-black tree,
# runs it, and exits with its status. Output dir: scratch\stubs_wave\LIVELINK\decode_test.
$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
$out = Join-Path $root 'scratch\stubs_wave\LIVELINK\decode_test'
New-Item -ItemType Directory -Force $out | Out-Null

function Read-List($p) {
  Get-Content $p | Where-Object { $_.Trim() -ne '' -and -not $_.TrimStart().StartsWith('#') }
}
$flags = (Read-List (Join-Path $root 'tools\build\msvc_flags.txt')) -join ' '
$incs = (Read-List (Join-Path $root 'tools\build\msvc_includes.txt') | ForEach-Object { '/I"' + (Join-Path $root $_.Trim()) + '"' }) -join ' '
$srcs = @(
  'tools\tests\tools\STUBS_LIVELINK_decode_test.cpp',
  'b5-decomp\src\SDKs\Packages\AttribSys\1.2.1.2\AttribSys\runtime\common\attribhash64.cpp',
  'b5-decomp\vendor\EASTL\source\red_black_tree.cpp'
) | ForEach-Object { '"' + (Join-Path $root $_) + '"' }
$exe = Join-Path $out 'livelink_decode_test.exe'
$bat = Join-Path $out 'build.bat'
$lines = @(
  '@echo off',
  ('call "' + (Join-Path $root 'tools\build\msvc_env.bat') + '" >nul 2>&1'),
  'if errorlevel 1 exit /b 200',
  ('cl ' + $flags + ' ' + $incs + ' ' + ($srcs -join ' ') + ' /Fe"' + $exe + '" /link /SUBSYSTEM:CONSOLE'),
  'exit /b %ERRORLEVEL%'
)
[System.IO.File]::WriteAllText($bat, ($lines -join "`r`n") + "`r`n")
Push-Location $out
try {
  & cmd /c $bat | Select-String -NotMatch '^\s*$' | Select-Object -Last 15 | ForEach-Object { Write-Host "  | $_" }
  $code = $LASTEXITCODE
} finally { Pop-Location }
if ($code -ne 0) { Write-Host "[livelink-test] BUILD FAILED ($code)"; exit 1 }
& $exe
$rc = $LASTEXITCODE
Write-Host "[livelink-test] exit $rc"
exit $rc
