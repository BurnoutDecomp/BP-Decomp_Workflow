function Assert-NativeBatchFrame {
    param([string]$Path,[int]$Count,[int]$Slot,[int]$MaxFrames=90)
    if ($Count -lt 1 -or $Count -gt $MaxFrames) { throw "raw frame cap exceeded: $Count not in 1..$MaxFrames" }
    if (!(Test-Path -LiteralPath $Path -PathType Leaf)) { throw "missing captured frame: $Path" }
    $bytes = [IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -le 54 -or $bytes.Length -gt 3686454 -or $bytes[0] -ne 66 -or $bytes[1] -ne 77) {
        throw "invalid BMP or frame byte cap exceeded: $Path"
    }
    $width = [BitConverter]::ToInt32($bytes,18)
    $height = [Math]::Abs([BitConverter]::ToInt32($bytes,22))
    if ($width -ne 1280 -or $height -ne 720) { throw ("wrong native frame size: {0}x{1}" -f $width,$height) }
    return [pscustomobject]@{
        path=[IO.Path]::GetFullPath($Path)
        sha256=(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
        bytes=$bytes.Length
        width=$width
        height=$height
        max_bytes=3686454
        slot=$Slot
        ordinal=$Count
    }
}
function Complete-NativeBatchCaptureAudit {
    param([string]$RunDir,[object[]]$Rows,[int]$Slot,[int]$MaxFrames=90)
    $problems = [Collections.Generic.List[string]]::new()
    if ($Rows.Count -gt $MaxFrames) { $problems.Add("raw frame count $($Rows.Count) exceeds $MaxFrames") }
    $seen = @{}
    foreach ($row in $Rows) {
        if ($row.slot -ne $Slot) { $problems.Add("wrong frame slot in $($row.phase)") }
        if ($row.sequence -lt 1 -or $row.sequence -gt $MaxFrames) { $problems.Add("out-of-range frame sequence in $($row.phase)") }
        if ($seen.ContainsKey([int]$row.sequence)) { $problems.Add("duplicate frame sequence $($row.sequence)") }
        $seen[[int]$row.sequence] = $true
        if (!(Test-Path -LiteralPath $row.path -PathType Leaf)) { $problems.Add("missing frame file $($row.path)"); continue }
        $actual = (Get-FileHash -LiteralPath $row.path -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -cne [string]$row.sha256) { $problems.Add("frame SHA changed $($row.phase)") }
        try {
            $check = Assert-NativeBatchFrame -Path $row.path -Count ([int]$row.sequence) -Slot $Slot -MaxFrames $MaxFrames
            if ($check.sha256 -cne [string]$row.sha256) { $problems.Add("frame bytes changed $($row.phase)") }
        } catch { $problems.Add($_.Exception.Message) }
    }
    $audit = [ordered]@{
        schema=1
        pass=($problems.Count -eq 0)
        slot=$Slot
        max_raw_frames=$MaxFrames
        max_bmp_bytes=3686454
        expected_width=1280
        expected_height=720
        frame_count=$Rows.Count
        unique_sequences=($seen.Count -eq $Rows.Count)
        frames=@($Rows | ForEach-Object { [ordered]@{phase=$_.phase;sequence=$_.sequence;pid=$_.pid;slot=$_.slot;path=$_.path;sha256=$_.sha256;bytes=$_.bytes;width=$_.width;height=$_.height} })
        problems=@($problems.ToArray())
        note="Integrity and budget only; no visual or control verdict."
    }
    $path = Join-Path $RunDir 'CAPTURE_AUDIT.json'
    if (Test-Path -LiteralPath $path) { throw 'refusing to overwrite CAPTURE_AUDIT.json' }
    $audit | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $path -Encoding utf8
    if (!$audit.pass) { throw ('capture audit failed: ' + ($problems -join '; ')) }
    return $audit
}
