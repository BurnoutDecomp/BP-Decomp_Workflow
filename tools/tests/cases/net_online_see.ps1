# Run through run_pair.ps1 against a running b5-decomp-server. Reuse the real
# Freeburn car-position oracle; separate LAN windows exclude local discovery.
param([string]$Role = '')
$lCase = & (Join-Path $PSScriptRoot 'net_lan_see.ps1') -Role $Role
if ($Role -eq '') {
    $lCase.Name = 'net_online_see'
    $lCase.Bug = 'none -- actual Freeburn car synchronisation through the Rust relay'
    return $lCase
}
$lOriginalSetup = $lCase.Setup
$lsRole = $Role
$lCase.Name = "net_online_see_$Role"
$lCase.Setup = {
    param($ctx)
    if (-not $env:BP_ONLINE_SERVER -or -not $env:BP_ONLINE_KEY) {
        throw 'net_online_see requires BP_ONLINE_SERVER and BP_ONLINE_KEY for the running server'
    }
    & $lOriginalSetup $ctx | Out-Null
    $env:BP_LAN_PORT = if ($lsRole -eq 'Host') { '27830' } else { '27850' }
}.GetNewClosure()
$lCase.Checks += @{ Kind = 'LogMatch'; Name = 'authenticated online relay connected';
    Pattern = '\[net\] online server connected: authenticated encrypted relay, protocol=2'; Expect = $true }
return $lCase
