#!/usr/bin/env pwsh
# Compatibility entry point. The implementation lives with the IDA pipeline.
& "$PSScriptRoot\ida\export_db.ps1" @args
exit $LASTEXITCODE
