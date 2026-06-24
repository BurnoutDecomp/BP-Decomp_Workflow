#!/usr/bin/env pwsh
# Compatibility entry point. The implementation lives under tools/build/.
& "$PSScriptRoot\build\build_tools.ps1" @args
exit $LASTEXITCODE
