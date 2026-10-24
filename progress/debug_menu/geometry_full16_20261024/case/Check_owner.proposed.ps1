param(
    [Parameter(Mandatory=$true)][string[]]$LogLines,
    [Parameter(Mandatory=$true)][string]$RunDir,
    [Parameter(Mandatory=$true)][object]$Binding,
    [Parameter(Mandatory=$true)][string]$Group
)
$ErrorActionPreference = 'Stop'
$fail = [Collections.Generic.List[string]]::new()
function Need([bool]$Condition,[string]$Message) { if (!$Condition) { $script:fail.Add($Message) } }
$ownerPath = Join-Path $RunDir 'geometry-input-owner.json'
$manifestPath = Join-Path $RunDir 'geometry-witnesses.json'
$terminalPath = Join-Path $RunDir 'flow/terminal-status.json'
$keyLogPath = Join-Path $RunDir 'geometry-keys.log'
Need (Test-Path -LiteralPath $ownerPath -PathType Leaf) 'missing direct-process input owner receipt'
Need (Test-Path -LiteralPath $manifestPath -PathType Leaf) 'missing typed geometry evidence manifest'
Need (Test-Path -LiteralPath $terminalPath -PathType Leaf) 'missing flow_run terminal status'
Need (Test-Path -LiteralPath $keyLogPath -PathType Leaf) 'missing bounded input helper log'
if ((Test-Path -LiteralPath $ownerPath) -and (Test-Path -LiteralPath $terminalPath)) {
    $owner = Get-Content -LiteralPath $ownerPath -Raw | ConvertFrom-Json
    $terminal = Get-Content -LiteralPath $terminalPath -Raw | ConvertFrom-Json
    Need ([int]$owner.slot -eq [int]$Binding.slot) 'helper slot differs from the reviewed private slot'
    Need ([string]$owner.exe_sha256 -ceq [string]$Binding.execution_exe_sha256) 'helper adopted a different executable hash'
    Need ([string]$owner.image -ieq (Join-Path $Binding.private_stage_root 'slot/Burnout_PC.exe')) 'helper adopted a different executable path'
    Need ([int]$owner.pid -eq [int]$terminal.owned_pid -and
        $owner.image -ieq $terminal.owned_image -and
        [DateTime]::Parse($owner.start_utc).ToUniversalTime().Ticks -eq [DateTime]::Parse($terminal.owned_start_utc).ToUniversalTime().Ticks) 'helper and flow_run PID/image/start identities differ'
    Need ($terminal.success -eq $true -and $terminal.owned_cleanup_complete -eq $true -and
        $terminal.input_reset_complete -eq $true -and $terminal.foreign_game -eq $false -and
        $terminal.first_assert_stop -eq $false) 'strict owned native terminal outcome is incomplete'
}
$alive = @(Get-CimInstance Win32_Process -Filter "Name LIKE 'Burnout%.exe' OR Name='TUB_Burnout_PC_External.exe'")
Need ($alive.Count -eq 0) 'game process still exists after flow_run returned'
if (Test-Path -LiteralPath $keyLogPath) {
    $keyText = Get-Content -LiteralPath $keyLogPath -Raw
    Need ($keyText -match '(?m)RESULT (?:DONE|DEFERRED):?') 'helper has no bounded terminal marker'
    Need ($keyText -notmatch 'RESULT FAIL:') 'helper reported a guarded-input failure'
}
if (Test-Path -LiteralPath $manifestPath) {
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    Need ($manifest.group -ceq $Group -and [int]$manifest.site_count -eq 16) 'geometry manifest group/site count differs'
    Need ([int]$manifest.frame_count -le 96) 'geometry frame manifest exceeds the96-frame cap'
}
@{Pass=($fail.Count -eq 0);Detail=$(if($fail.Count){$fail -join '; '}else{'exact helper PID/image/start matches flow owner; no foreign game remains; slot, executable and bounded frame receipt match'})}
