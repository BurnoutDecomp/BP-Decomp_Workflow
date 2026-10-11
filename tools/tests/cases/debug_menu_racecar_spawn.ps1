# One private LAN host exercises the original online-lobby spawn consumer.
# BPH_TEST_FORCE_ONLINE_SPAWN=0 tests the default retaining path; default is forced.
$lbForce=$env:BPH_TEST_FORCE_ONLINE_SPAWN -ne '0'
$lsForce=if ($lbForce) { 'TRUE' } else { 'FALSE' }
$liForce=if ($lbForce) { 1 } else { 0 }
@{
    Name='debug_menu_racecar_spawn'
    Area='debug-menu'
    Bug='The lobby spawn toggle must reach both original consumers; dormant ram rows must retain their original behavior.'
    ProfileFixture='DISCO_collect_base.sav'
    Run=@{ SkipIntro=$true; AcceptGap=1.0; MaxSeconds=110;
           Drive=$true; DriveDelay=3.0; DriveSeconds=1.0;
           Teleport='3040.7,-5.8,-1937.9,180'; MotionProbe=$true }
    DiagEnv='BRN_NET_HOST=1,BRN_NET_DELAY=65,BRN_DEBUG_UI_TRACE=1,BRN_RACECAR_RAM_TRACE=1'
    Setup={
        param($ctx)
        $env:BP_LAN='1'
        $env:BP_LAN_NAME='DebugSpawnObserver'
        Remove-Item Env:\BP_LAN_XUID -ErrorAction SilentlyContinue
        $lsRelative='../../'+$ctx.RunDir.Substring(([string]$ctx.Root).TrimEnd('\').Length+1).Replace('\','/')
        $lsToggle='"Race Car Entity/Force Online Freeburn Spawn Position"'
        Set-Content -LiteralPath (Join-Path $ctx.RunDir 'activate.txt') -Encoding ascii -Value @(
            'component "Race Car Entity"',('set '+$lsToggle+' '+$lsForce),
            'set "Race Car Entity/Magnitude" 42','call "Race Car Entity/Apply Ram"',
            ('save "'+$lsRelative+'/before-lobby.txt"'),
            ('bind F2 exec "'+$lsRelative+'/ram100.txt"'))
        Set-Content -LiteralPath (Join-Path $ctx.RunDir 'ram100.txt') -Encoding ascii -Value @(
            'set "Race Car Entity/Magnitude" 100','call "Race Car Entity/Apply Ram"',
            ('save "'+$lsRelative+'/ram100-saved.txt"'))
        Set-Content -LiteralPath (Join-Path $ctx.RunDir 'restore.txt') -Encoding ascii -Value @(
            ('set '+$lsToggle+' FALSE'),'set "Race Car Entity/Magnitude" 0',
            ('save "'+$lsRelative+'/restored.txt"'))
        $lsSteps=Join-Path $ctx.RunDir 'debug-menu-steps.txt'
        Set-Content -LiteralPath $lsSteps -Encoding ascii -Value @(
            'wait:CarSelectManager: Exit state is finished','sleep:3','key:192',
            ('cmd:exec "'+$lsRelative+'/activate.txt"'),'sleep:1','key:113','sleep:1','key:192',
            'wait:\[net\] world online grid mode=15','sleep:2','key:192',
            ('cmd:exec "'+$lsRelative+'/restore.txt"'),'sleep:1','key:192','note:restored')
        $lsHelper=Join-Path $ctx.Root 'tools/tests/tools/VW_DEFORM_debugkeys.ps1'
        $laArgs=@('-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$lsHelper`"",'-GameLog',"`"$($ctx.GameLog)`"",
            '-OutDir',"`"$($ctx.RunDir)`"",'-Slot',"$($ctx.Slot)",'-StepsFile',"`"$lsSteps`"",'-TimeoutSec','105')
        return Start-Process powershell -ArgumentList $laArgs -PassThru -WindowStyle Hidden
    }.GetNewClosure()
    Checks=@(
        @{ Kind='NewAsserts'; Name='no new assert families' }
        @{ Kind='LogCount'; Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }
        @{ Kind='Script'; Name='real console sequence completes'; Script={
            param($ctx)
            $lsPath=Join-Path $ctx.RunDir 'vw_deform_keys.log'
            $lsText=if(Test-Path $lsPath) { Get-Content $lsPath -Raw } else { '' }
            return @{ Pass=$lsText -match 'RESULT DONE'; Detail=($lsText -split "`r?`n" | Where-Object { $_ -match 'note:|RESULT' }) -join ' | ' }
        } }
        @{ Kind='Script'; Name='original toggle and Magnitude are writable and restored'; Script={
            param($ctx)
            $laExpected=@(@('before-lobby.txt',$lsForce,'42'),@('ram100-saved.txt',$lsForce,'100'),@('restored.txt','FALSE','0'))
            $laMissing=@()
            foreach($lrExpected in $laExpected) {
                $lsPath=Join-Path $ctx.RunDir $lrExpected[0]
                $lsText=if(Test-Path $lsPath) { Get-Content $lsPath -Raw } else { '' }
                if($lsText -notmatch ('(?m)^SET "/Race Car Entity/Force Online Freeburn Spawn Position" "'+$lrExpected[1]+'"') -or
                   $lsText -notmatch ('(?m)^SET "/Race Car Entity/Magnitude" "'+$lrExpected[2]+'(?:\.0+)?"')) { $laMissing+=$lrExpected[0] }
            }
            return @{ Pass=$laMissing.Count -eq 0; Detail='missing correct saved states: '+($laMissing -join ', ') }
        }.GetNewClosure() }
        @{ Kind='LogCount'; Name='original ram callback invoked at Magnitude 42'; Pattern='\[debug-racecar-ram\] latched=1 magnitude=42'; Min=1 }
        @{ Kind='LogCount'; Name='original ram callback invoked again at Magnitude 100'; Pattern='\[debug-racecar-ram\] latched=1 magnitude=100'; Min=1 }
        @{ Kind='LogCount'; Name='local lobby respawn decision follows debug value';
           Pattern=('\[net\] world online grid mode=15 cars=1 lobby=1 localGrid=0 respawnLocal='+$liForce); Min=1 }
        @{ Kind='Script'; Name='selected lobby transform follows original debug spawn table'; Script={
            param($ctx)
            $lsRx='\[net\] debug-spawn lobby=1 force='+$liForce+' local=1 respawn='+$liForce+' grid=0 position=\(([-0-9.e+]+),([-0-9.e+]+),([-0-9.e+]+)\)'
            $lsHit=$ctx.LogLines | Where-Object { $_ -match $lsRx } | Select-Object -First 1
            if(!$lsHit) { return @{ Pass=$false; Detail='missing original lobby transform witness' } }
            $null=$lsHit -match $lsRx
            $lfX=[double]::Parse($Matches[1],[cultureinfo]::InvariantCulture)
            $lfZ=[double]::Parse($Matches[3],[cultureinfo]::InvariantCulture)
            $lfExpectedX=3008.169921875
            $lfExpectedZ=-1874.300048828125
            if(!$lbForce) {
                $liAt=[array]::IndexOf($ctx.LogLines,$lsHit)
                $lsPrior=$ctx.LogLines[0..$liAt] | Where-Object { $_ -match '\[motion\] n \d+ pos ([-0-9.e+]+) ([-0-9.e+]+) ([-0-9.e+]+)' } | Select-Object -Last 1
                if(!$lsPrior) { return @{ Pass=$false; Detail='missing pre-lobby physics position' } }
                $null=$lsPrior -match '\[motion\] n \d+ pos ([-0-9.e+]+) ([-0-9.e+]+) ([-0-9.e+]+)'
                $lfExpectedX=[double]::Parse($Matches[1],[cultureinfo]::InvariantCulture)
                $lfExpectedZ=[double]::Parse($Matches[3],[cultureinfo]::InvariantCulture)
            }
            return @{ Pass=([math]::Abs($lfX-$lfExpectedX) -lt 1 -and [math]::Abs($lfZ-$lfExpectedZ) -lt 1); Detail=$lsHit.Trim() }
        }.GetNewClosure() }
        @{ Kind='Script'; Name='lobby placement reaches the actual player physics'; Script={
            param($ctx)
            $liAt=-1
            $lfX=0.0; $lfZ=0.0
            for($li=0; $li -lt $ctx.LogLines.Count; ++$li) {
                if($ctx.LogLines[$li] -match ('\[net\] debug-spawn lobby=1 force='+$liForce+' local=1 respawn='+$liForce+' grid=0 position=\(([-0-9.e+]+),([-0-9.e+]+),([-0-9.e+]+)\)')) {
                    $liAt=$li
                    $lfX=[double]::Parse($Matches[1],[cultureinfo]::InvariantCulture)
                    $lfZ=[double]::Parse($Matches[3],[cultureinfo]::InvariantCulture)
                    break
                }
            }
            if($liAt -lt 0) { return @{ Pass=$false; Detail='missing selected transform' } }
            $lfNearest=[double]::PositiveInfinity
            for($li=$liAt+1; $li -lt $ctx.LogLines.Count; ++$li) {
                if($ctx.LogLines[$li] -match '\[motion\] n \d+ pos ([-0-9.e+]+) ([-0-9.e+]+) ([-0-9.e+]+)') {
                    $lfDx=[double]::Parse($Matches[1],[cultureinfo]::InvariantCulture)-$lfX
                    $lfDz=[double]::Parse($Matches[3],[cultureinfo]::InvariantCulture)-$lfZ
                    $lfNearest=[math]::Min($lfNearest,[math]::Sqrt($lfDx*$lfDx+$lfDz*$lfDz))
                }
            }
            return @{ Pass=$lfNearest -lt 5; Detail="closest post-lobby player physics sample is $lfNearest m from the selected transform" }
        }.GetNewClosure() }
    )
}
