$ErrorActionPreference='Stop'
if($PSVersionTable.PSVersion.Major -lt 7){throw 'PowerShell7 required'}
$n=$PSScriptRoot
$stage=Get-Content -Raw -LiteralPath (Join-Path $n 'STAGING.json')|ConvertFrom-Json
$case=& (Join-Path $n 'Case.ps1')
if($case.Checks.Count -ne 16 -or $case.Run.SkipIntro -ne $false -or !$case.Run.TitleStart -or !$case.Run.StrictGameOwnership -or !$case.Run.AllowConcurrentGames -or $case.Run.MaxSeconds -ne 450 -or $case.Run.MaxLogMB -ne 128){throw 'Unbypassed baseline contract differs'}
if($stage.slot -ne 62173 -or $stage.normal_deployment -ne $false -or $stage.source -ne '22e673523a69a7a710d53a2bbba61efa0824700c' -or $stage.exe_sha256 -ne 'ccdbfa54ca4f51a776f525ccd3760ff020307cbb33b509a700237f841bc21b54'){throw 'Wrong private candidate'}
foreach($file in @('Case.ps1','AuthoredCase.ps1','BaselineCase.ps1','Capture.ps1','runtime_harness/tools/tests/run_case.ps1','runtime_harness/tools/diagnostics/flow_run.ps1')){
 $tokens=$null;$errors=$null;[Management.Automation.Language.Parser]::ParseFile((Join-Path $n $file),[ref]$tokens,[ref]$errors)|Out-Null
 if($errors.Count){throw ('Parse error '+$file)}
}
if((Get-PSDrive D).Free -lt 1610612736){throw 'D free space below1.5GiB bounded launch floor'}
$out=@{verdict='pass';checks=16;runtime_checks_expected_with_terminal=17;slot=62173;skip_intro=$false;strict_owned_runtime=$true;normal_deployment=$false;source=$stage.source;exe_sha256=$stage.exe_sha256}
$out|ConvertTo-Json|Set-Content -LiteralPath (Join-Path (Split-Path $n -Parent) 'OFFLINE_PREFLIGHT.json')
$out|ConvertTo-Json -Compress
