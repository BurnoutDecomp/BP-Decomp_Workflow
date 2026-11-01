function Get-BrnObservedGameProcesses {
    $filter = "Name LIKE 'Burnout%.exe' OR Name='TUB_Burnout_PC_External.exe' OR Name='BrnGame.exe'"
    $native = @(Get-CimInstance Win32_Process -Filter $filter -ErrorAction Stop)
    $rows = [Collections.Generic.List[object]]::new()
    foreach ($row in $native) {
        $pidValue = [int]$row.ProcessId
        if ([string]::IsNullOrWhiteSpace([string]$row.ExecutablePath)) {
            throw "game PID $pidValue has no readable executable path"
        }
        $path = [IO.Path]::GetFullPath([string]$row.ExecutablePath)
        if (!(Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "game PID $pidValue executable is missing: $path"
        }
        $process = Get-Process -Id $pidValue -ErrorAction Stop
        $ticks = [string]$process.StartTime.ToUniversalTime().Ticks
        $rows.Add([pscustomobject]@{
            process_id = $pidValue
            name = [string]$row.Name
            image_path = $path
            start_ticks = $ticks
            image_sha256 = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
        })
    }
    # Emit each row as an individual pipeline object so the owner filter sees each PID.
    return $rows.ToArray()
}

function Assert-BrnConcurrentOwnerSet {
    param(
        [Parameter(Mandatory=$true)][object]$Stage,
        [int]$OwnedPid = 0,
        [string]$Phase = 'runtime',
        [string]$ReceiptPath = '',
        [string]$AppendPath = ''
    )
    $expected = $Stage.allowed_concurrent_game
    $packageArea = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot)).TrimEnd('\')
    $authorized = $null
    if ($null -ne $expected) {
        foreach ($name in @('process_id','image_path','start_ticks','private_root')) {
            if ($null -eq $expected.PSObject.Properties[$name]) { throw "allowed_concurrent_game is missing $name" }
        }
        if ([int]$expected.process_id -le 0 -or [string]$expected.start_ticks -notmatch '^\d+$') {
            throw 'allowed_concurrent_game PID/start ticks are invalid'
        }
        $root = [IO.Path]::GetFullPath([string]$expected.private_root).TrimEnd('\')
        $image = [IO.Path]::GetFullPath([string]$expected.image_path)
        if (!$root.StartsWith($packageArea + '\',[StringComparison]::OrdinalIgnoreCase)) {
            throw "allowed concurrent game private_root is outside the batch scratch area: $root"
        }
        if (!$image.StartsWith($root + '\',[StringComparison]::OrdinalIgnoreCase)) {
            throw "allowed concurrent game image is outside its declared private_root: $image"
        }
        if ([IO.Path]::GetFileName($image) -notin @('Burnout_PC.exe','TUB_Burnout_PC_External.exe','BrnGame.exe')) {
            throw "unsupported allowed concurrent game image name: $image"
        }
        if ($null -eq ('BrnPrivateFileIdentity' -as [type])) { . (Join-Path $PSScriptRoot 'PathGuards.ps1') }
        [void](Assert-BrnNoReparsePath $root 'allowed concurrent private root' -RequireLeaf)
        [void](Assert-BrnNoReparsePath $image 'allowed concurrent game image' -RequireLeaf)
        $authorized = [ordered]@{
            process_id = [int]$expected.process_id
            image_path = $image
            start_ticks = [string]$expected.start_ticks
            private_root = $root
        }
    }

    $observed = @(Get-BrnObservedGameProcesses | Where-Object { $_.process_id -ne $OwnedPid })
    if ($observed.Count -gt 1) { throw "more than one other game is alive ($($observed.Count)); no process was stopped" }
    if ($observed.Count -eq 1) {
        if ($null -eq $authorized) { throw 'an unlisted other game is alive; no process was stopped' }
        $actual = $observed[0]
        if ($actual.process_id -ne $authorized.process_id -or
            $actual.image_path -ine $authorized.image_path -or
            [string]$actual.start_ticks -cne $authorized.start_ticks) {
            throw 'the live other game does not match the declared Root-private PID/path/start-time identity'
        }
    }
    $result = [ordered]@{
        pass = $true
        phase = $Phase
        sample_utc = [DateTime]::UtcNow.ToString('o')
        owned_pid_excluded = $OwnedPid
        observed_other_game_count = $observed.Count
        observed_other_games = @($observed)
        authorized_concurrent_game = $authorized
        exact_identity_checked = ($observed.Count -eq 0 -or $null -ne $authorized)
        maximum_other_games = 1
        no_process_stopped = $true
        runner_helper_other_game_count_is_not_used = $true
    }
    if (![string]::IsNullOrWhiteSpace($ReceiptPath)) {
        if (Test-Path -LiteralPath $ReceiptPath) { throw "refusing to overwrite $ReceiptPath" }
        $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $ReceiptPath -Encoding utf8
    }
    if (![string]::IsNullOrWhiteSpace($AppendPath)) {
        $line = ($result | ConvertTo-Json -Depth 8 -Compress) + [Environment]::NewLine
        [IO.File]::AppendAllText([IO.Path]::GetFullPath($AppendPath),$line,[Text.UTF8Encoding]::new($false))
    }
    return [pscustomobject]$result
}



