# Real production GameData -> GameTalk -> GUI -> normal boot regression.
# All original baseline checks remain. Root owns the strict job/staging/launch.
$case = & (Join-Path 'D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\swarm_gui17_prerequisites_f01_20261028\fixture\harness_reference' 'tools/tests/cases/baseline_boot_drive.ps1')
$case.Name = 'gui_actual_gametalk_startup_whole_chain'
$case.Area = 'gui-lifecycle'
$case.Bug = 'GameData skipped original GameTalk stage7; GUI stage0 registered through null singleton'
$case.ProfileFixture = Join-Path $PSScriptRoot 'Profile.seed.sav'
$case.ProfileFixtureSha256 = '7066c0d47fb007022a75bfea7d92e752cbafdc4d30ef10116fb238a3df781884'
$case.Run.TitleStart = $true
$case.Run.MaxSeconds = 80
$case.Run.StrictGameOwnership = $true
$case.Checks += @(
  @{ Kind='LogCount'; Name='actual GameData GameTalk owner completed startup exactly once';
     Pattern='\[GameData\] GameTalk ready owner=[0-9A-Fa-fx]+ manager=[0-9A-Fa-fx]+'; Min=1; Max=1 }
  @{ Kind='Script'; Name='real owner and real singleton existed before GUI registration'; Script={
    param($ctx)
    $ready = @($ctx.LogLines | Select-String '\[GameData\] GameTalk ready owner=([0-9A-Fa-fx]+) manager=([0-9A-Fa-fx]+)')
    if($ready.Count -ne 1){return @{Pass=$false;Detail=('startup witnesses='+$ready.Count)}}
    $ownerText=$ready[0].Matches[0].Groups[1].Value -replace '^0x',''
    $managerText=$ready[0].Matches[0].Groups[2].Value -replace '^0x',''
    $owner=[UInt64]::Parse($ownerText,[Globalization.NumberStyles]::HexNumber)
    $manager=[UInt64]::Parse($managerText,[Globalization.NumberStyles]::HexNumber)
    $all=[string]::Join("`n",$ctx.LogLines)
    $readyAt=$all.IndexOf('[GameData] GameTalk ready owner=')
    $guiAt=$all.IndexOf('loading stage 2 (GUIModule)')
    return @{Pass=($owner -ne 0 -and $manager -ne 0 -and $owner -ne $manager -and $guiAt -gt $readyAt);
      Detail=('owner='+$ownerText+' singleton='+$managerText+' readyAt='+$readyAt+' guiAt='+$guiAt)}
  } }
  @{ Kind='LogCount'; Name='no repeat of first native GUI registration exception';
     Pattern='\[EXCEPTION\]|GameTalkManager::RegisterMessageHandler \+.*\[rva'; Max=0 }
)
$case
