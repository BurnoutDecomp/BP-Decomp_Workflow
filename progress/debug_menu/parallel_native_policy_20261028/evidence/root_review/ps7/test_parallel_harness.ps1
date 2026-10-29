param([string]$PacketRoot = $PSScriptRoot)
$ErrorActionPreference = 'Stop'
$results = [Collections.Generic.List[object]]::new()
function Assert-Check([string]$Name, [scriptblock]$Body) {
  try { & $Body; $results.Add(@{name=$Name;pass=$true}) }
  catch { $results.Add(@{name=$Name;pass=$false;error=$_.Exception.Message}); throw "$Name : $($_.Exception.Message)" }
}
function Require($Condition, [string]$Message) { if (-not $Condition) { throw $Message } }
function Parse-Source([string]$Path) {
  $tokens=$null; $errors=$null
  $ast=[Management.Automation.Language.Parser]::ParseFile($Path,[ref]$tokens,[ref]$errors)
  Require ($errors.Count -eq 0) "Parse errors in $Path : $errors"
  return $ast
}
function Find-Function($Ast,[string]$Name) {
  return $Ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $Name},$true)
}
function Roster([int]$Count) {
  @(for($i=1;$i -le $Count;$i++){[pscustomobject]@{ProcessId=100+$i;Name='Burnout_PC.exe';ExecutablePath="D:\private\stage_$i\slot\Burnout_PC.exe"}})
}
function Check-Roster($Ast,[string]$Name,[array]$Games,[int]$Cap,[bool]$Allow,[bool]$Reject,[int]$Expected=-1,[int]$Exclude=0) {
  $script:mockGames=$Games
  function Get-CimInstance { param($ClassName,$Filter,$ErrorAction) foreach($game in $script:mockGames){$game} }
  function Get-OtherGameProcesses { foreach($game in $script:mockGames){$game} }
  $allowConcurrentGames=$Allow
  $MaxConcurrentOtherGames=$Cap
  $exe='D:\private\owned\slot\Burnout_PC.exe'
  $ownedImagePath=$exe
  $definition=Find-Function $Ast $Name
  . ([scriptblock]::Create($definition.Extent.Text))
  $caught=$null;$actual=@()
  try {
    if($Name -eq 'Get-StrictOtherGameProcesses') { $actual=@(& $Name -ExcludePid $Exclude) }
    else { $actual=@(& $Name) }
  } catch { $caught=$_.Exception.Message }
  if($Reject) { Require ($null -ne $caught) 'Expected rejection' }
  else { Require ($null -eq $caught) "Unexpected rejection: $caught"; Require ($actual.Count -eq $Expected) "Expected $Expected processes, got $($actual.Count)" }
}
$caseRel='tools/tests/run_case.ps1';$flowRel='tools/diagnostics/flow_run.ps1'
$case=Parse-Source (Join-Path $PacketRoot "post/$caseRel")
$flow=Parse-Source (Join-Path $PacketRoot "post/$flowRel")
foreach($pair in @(@($caseRel,'Get-CaseStrictOtherGameProcesses'),@($flowRel,'Get-StrictOtherGameProcesses'))) {
  $relative=$pair[0];$fn=$pair[1]
  $old=Parse-Source (Join-Path $PacketRoot "pre/$relative")
  $new=Parse-Source (Join-Path $PacketRoot "post/$relative")
  Assert-Check "$fn baseline one other allowed" { Check-Roster $old $fn (Roster 1) 1 $true $false 1 }
  Assert-Check "$fn baseline two others rejected" { Check-Roster $old $fn (Roster 2) 100 $true $true }
  foreach($count in @(0,1,3,20,100)) {
    Assert-Check "$fn opt-in cap100 roster$count" { Check-Roster $new $fn (Roster $count) 100 $true $false $count }
  }
  Assert-Check "$fn default cap1 rejects2" { Check-Roster $new $fn (Roster 2) 1 $true $true }
  Assert-Check "$fn cap3 accepts3" { Check-Roster $new $fn (Roster 3) 3 $true $false 3 }
  Assert-Check "$fn cap3 rejects4" { Check-Roster $new $fn (Roster 4) 3 $true $true }
  Assert-Check "$fn cap100 rejects101" { Check-Roster $new $fn (Roster 101) 100 $true $true }
  Assert-Check "$fn non-opt-in returns foreign roster for caller refusal" { Check-Roster $new $fn (Roster 3) 1 $false $false 3 }
  Assert-Check "$fn missing path rejects" { $r=Roster 3;$r[1].ExecutablePath=$null;Check-Roster $new $fn $r 100 $true $true }
  Assert-Check "$fn relative path rejects" { $r=Roster 3;$r[1].ExecutablePath='relative\Burnout_PC.exe';Check-Roster $new $fn $r 100 $true $true }
  Assert-Check "$fn owned path rejects" { $r=Roster 3;$r[1].ExecutablePath='d:\PRIVATE\owned\slot\Burnout_PC.exe';Check-Roster $new $fn $r 100 $true $true }
  Assert-Check "$fn duplicate image rejects case-insensitively" { $r=Roster 3;$r[1].ExecutablePath=$r[0].ExecutablePath.ToUpperInvariant();Check-Roster $new $fn $r 100 $true $true }
  Assert-Check "$fn normalized duplicate image rejects" { $r=Roster 3;$r[1].ExecutablePath='D:\private\stage_1\slot\..\slot\Burnout_PC.exe';Check-Roster $new $fn $r 100 $true $true }
  Assert-Check "$fn all other functions byte-identical" {
    foreach($n in $old.FindAll({param($x) $x -is [Management.Automation.Language.FunctionDefinitionAst]},$true)) {
      if($n.Name -ne $fn) { Require ((Find-Function $new $n.Name).Extent.Text -ceq $n.Extent.Text) "Other function changed: $($n.Name)" }
    }
  }
  Assert-Check "$fn all existing strict/private/profile/cleanup if guards unchanged" {
    foreach($n in $old.FindAll({param($x) $x -is [Management.Automation.Language.IfStatementAst]},$true)) {
      if($n.Extent.Text -match 'private paths must be sibling|private GameDir/WorkingDirectory must already exist|private paths require both|AllowConcurrentGames requires|owned_cleanup_complete|Stop-Process|profileRestoreSafe|setupCleanupOk|CreationDate') {
        # Compare conditions rather than bodies: new status metadata is allowed, behavior gates are not.
        foreach($clause in $n.Clauses) {
          $condition=$clause.Item1.Extent.Text
          Require (@($new.FindAll({param($x) $x -is [Management.Automation.Language.IfStatementAst]},$true) | Where-Object { @($_.Clauses | ForEach-Object {$_.Item1.Extent.Text}) -ccontains $condition }).Count -gt 0) "Existing guard lost: $condition"
        }
      }
    }
  }
  Assert-Check "$fn AST parameter default1 range1to100" {
    $parameter=@($new.ParamBlock.Parameters | Where-Object {$_.Name.VariablePath.UserPath -eq 'MaxConcurrentOtherGames'})
    Require ($parameter.Count -eq 1 -and $parameter[0].DefaultValue.Value -eq 1) 'Missing default 1'
    Require ($parameter[0].Extent.Text -match '\[ValidateRange\(1,100\)\]\[int\]') 'Missing integer range'
  }
}
Assert-Check 'private sibling path validation blocks remain byte-identical' {
  foreach($relative in @($caseRel,$flowRel)) {
    $old=Parse-Source (Join-Path $PacketRoot "pre/$relative");$new=Parse-Source (Join-Path $PacketRoot "post/$relative")
    $a=@($old.FindAll({param($n) $n -is [Management.Automation.Language.IfStatementAst]},$true)|Where-Object {$_.Clauses[0].Item1.Extent.Text -ceq '$usingCustomGameDirs'})[0]
    $b=@($new.FindAll({param($n) $n -is [Management.Automation.Language.IfStatementAst]},$true)|Where-Object {$_.Clauses[0].Item1.Extent.Text -ceq '$usingCustomGameDirs'})[0]
    Require ($a.Extent.Text -ceq $b.Extent.Text) "Private path validation changed: $relative"
  }
}
Assert-Check 'flow monitor excludes owned PID while validating all remaining paths' {
  $r=Roster 3;$r[0].ProcessId=900;$r[0].ExecutablePath='D:\private\owned\slot\Burnout_PC.exe'
  Check-Roster $flow 'Get-StrictOtherGameProcesses' $r 100 $true $false 2 900
}
Assert-Check 'case forwarding AST explicitly overwrites copied Run cap with effective value' {
  $assigns=$case.FindAll({param($n) $n -is [Management.Automation.Language.AssignmentStatementAst]},$true)
  $forward=@($assigns | Where-Object {$_.Left.Extent.Text -ceq '$lArgs[''MaxConcurrentOtherGames'']'})
  Require ($forward.Count -eq 1 -and $forward[0].Right.Extent.Text -ceq '$MaxConcurrentOtherGames') 'Forwarding wrong'
  $copy=@($case.FindAll({param($n) $n -is [Management.Automation.Language.ForEachStatementAst]},$true) | Where-Object {$_.Extent.Text -match 'foreach \(\$k in \$lRun.Keys\)'})
  Require ($copy.Count -eq 1 -and $copy[0].Extent.StartOffset -lt $forward[0].Extent.StartOffset) 'Run copy must precede override'
  Require ($case.Extent.Text.Contains("'tools\diagnostics\flow_run.ps1') @lArgs")) 'Expected actual splatted flow call'
}
Assert-Check 'every existing helper call remains at original phase and owned PID exclusion' {
  foreach($relative in @($caseRel,$flowRel)) {
    $old=Parse-Source (Join-Path $PacketRoot "pre/$relative");$new=Parse-Source (Join-Path $PacketRoot "post/$relative")
    foreach($name in @('Get-CaseStrictOtherGameProcesses','Get-StrictOtherGameProcesses')) {
      $a=@($old.FindAll({param($n) $n -is [Management.Automation.Language.CommandAst]},$true) | Where-Object {$_.GetCommandName() -eq $name})
      $b=@($new.FindAll({param($n) $n -is [Management.Automation.Language.CommandAst]},$true) | Where-Object {$_.GetCommandName() -eq $name})
      Require ($a.Count -eq $b.Count) "$name call count changed"
      for($i=0;$i -lt $a.Count;$i++) { Require ($a[$i].Extent.Text -ceq $b[$i].Extent.Text) "$name call args changed" }
    }
  }
}
# Execute source-extracted option validation in child PowerShell processes: source uses exit.
$engine=(Get-Process -Id $PID).Path
$worker=Join-Path $PacketRoot 'option-worker.ps1'
foreach($kind in @('case','flow')) {
  $ast=if($kind -eq 'case'){$case}else{$flow}
  $text=$ast.Extent.Text
  if($kind -eq 'case') {
    $start=$text.IndexOf('$allowConcurrentGames = $false')
    $finish=$text.IndexOf('if ($RunsRoot -eq "")')
    $validation=$text.Substring($start,$finish-$start)
    $privateGuard=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.IfStatementAst]},$true)|Where-Object {$_.Clauses[0].Item1.Extent.Text -like '*-not $NoRun -and $allowConcurrentGames*'})[0].Extent.Text
    $setup='$lRun = @{AllowConcurrentGames=[bool]::Parse($env:TEST_ALLOW);StrictGameOwnership=[bool]::Parse($env:TEST_STRICT)}; if($env:TEST_RUN_CAP){$lRun.MaxConcurrentOtherGames=[int]$env:TEST_RUN_CAP}; $usingCustomGameDirs=[bool]::Parse($env:TEST_PRIVATE)'
  } else {
    $validation=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.IfStatementAst]},$true)|Where-Object {$_.Clauses[0].Item1.Extent.Text -ceq '$MaxConcurrentOtherGames -gt 1 -and -not $AllowConcurrentGames'})[0].Extent.Text
    $privateGuard=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.IfStatementAst]},$true)|Where-Object {$_.Clauses[0].Item1.Extent.Text -like '$AllowConcurrentGames -and (-not $StrictGameOwnership*'})[0].Extent.Text
    $setup='$AllowConcurrentGames=[bool]::Parse($env:TEST_ALLOW);$StrictGameOwnership=[bool]::Parse($env:TEST_STRICT);$usingCustomGameDirs=[bool]::Parse($env:TEST_PRIVATE)'
  }
  $param=$ast.ParamBlock.Extent.Text
  Set-Content -LiteralPath $worker -Value "$param`n$setup`n$validation`n$privateGuard`nWrite-Output ('EFFECTIVE_CAP=' + `$MaxConcurrentOtherGames)`nexit 0" -Encoding utf8
  foreach($scenario in @(
    @{name='default';allow='true';strict='true';private='true';slot=1;expect=1},
    @{name='cap100';cap=100;allow='true';strict='true';private='true';slot=1;expect=100},
    @{name='cap0 rejects';cap=0;allow='true';strict='true';private='true';slot=1;reject=$true},
    @{name='cap101 rejects';cap=101;allow='true';strict='true';private='true';slot=1;reject=$true},
    @{name='cap100 nonoptin rejects';cap=100;allow='false';strict='true';private='true';slot=1;reject=$true},
    @{name='cap100 nonstrict rejects';cap=100;allow='true';strict='false';private='true';slot=1;reject=$true},
    @{name='cap100 slot0 rejects';cap=100;allow='true';strict='true';private='true';slot=0;reject=$true},
    @{name='cap100 nonprivate rejects';cap=100;allow='true';strict='true';private='false';slot=1;reject=$true},
    @{name='nonoptin default unchanged';allow='false';strict='true';private='false';slot=0;expect=1}
  )) {
    Assert-Check "$kind option validation $($scenario.name)" {
      $env:TEST_ALLOW=$scenario.allow;$env:TEST_STRICT=$scenario.strict;$env:TEST_PRIVATE=$scenario.private;$env:TEST_RUN_CAP=''
      $args=@('-NoProfile','-File',$worker,'-Slot',[string]$scenario.slot)
      if($kind -eq 'case'){$args+=@('-Case','fixture')}
      if($scenario.ContainsKey('cap')){$args+=@('-MaxConcurrentOtherGames',[string]$scenario.cap)}
      $savedPreference=$ErrorActionPreference
      try { $ErrorActionPreference='Continue'; $output=(& $engine @args 2>&1 | Out-String);$code=$LASTEXITCODE }
      finally { $ErrorActionPreference=$savedPreference }
      if($scenario.reject){Require ($code -ne 0) "Expected reject: $output"}
      else {Require ($code -eq 0 -and $output -match "EFFECTIVE_CAP=$($scenario.expect)\b") "Bad effective cap/exit: $code $output"}
    }
  }
  if($kind -eq 'case') {
    foreach($pair in @(@(20,$null,20),@(20,100,100),@(101,$null,-1))) {
      Assert-Check "case Run cap=$($pair[0]) CLI=$($pair[1])" {
        $env:TEST_ALLOW='true';$env:TEST_STRICT='true';$env:TEST_PRIVATE='true';$env:TEST_RUN_CAP=[string]$pair[0]
        $args=@('-NoProfile','-File',$worker,'-Case','fixture','-Slot','1')
        if($null -ne $pair[1]){$args+=@('-MaxConcurrentOtherGames',[string]$pair[1])}
        $savedPreference=$ErrorActionPreference
      try { $ErrorActionPreference='Continue'; $output=(& $engine @args 2>&1 | Out-String);$code=$LASTEXITCODE }
      finally { $ErrorActionPreference=$savedPreference }
        if($pair[2] -eq -1){Require ($code -ne 0) 'Invalid Run cap accepted'}
        else {Require ($code -eq 0 -and $output -match "EFFECTIVE_CAP=$($pair[2])\b") "Run/CLI override failed: $output"}
      }
    }
  }
}
Remove-Item -LiteralPath $worker
$results | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $PacketRoot 'test-results.json') -Encoding utf8
Write-Host ("PASS {0}/{0}; no game launched" -f $results.Count)


