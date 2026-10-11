# Real menu setup, then the existing opt-in event-start harness and shared captures.
@{
    Name='debug_menu_markedman_takedown'
    Area='debug-menu'
    Bug='Marked Man tunables must reach rival/grid/ramp consumers; Takedown overlays must read the real cached snapshot.'
    Frames=$true
    ProfileFixture='DISCO_collect_base.sav'
    Run=@{ SkipIntro=$true; AcceptGap=1.0; MaxSeconds=105; MinFreeGB=22;
           Drive=$true; DriveDelay=55.0; DriveSeconds=40.0; StartEvent=$true;
           MotionProbe=$true;
           Teleport='1634.3,-1.9,-2284.1,292'; EventFsm=$true;
           SkipTrainingTip=$true; FrameEvery=240 }
    DiagEnv="BRN_DEBUG_UI_TRACE=1,BRN_MM_DIAG=1,BRN_TAKEDOWN_DEBUG_TRACE=1,BRN_FRAME_DUMP_MAX=48,BRN_START_EVENT_READY_FILE=../game_slots/$Slot/dm-start-ready.txt"
    Setup={
        param($ctx)
        $lsRelative='../../'+$ctx.RunDir.Substring(([string]$ctx.Root).TrimEnd('\').Length+1).Replace('\','/')
        $lsSlotDir=Join-Path $ctx.Root ('build/game_slots/'+$ctx.Slot)
        New-Item -ItemType Directory -Force $lsSlotDir | Out-Null
        $lsReady=Join-Path $lsSlotDir 'dm-start-ready.txt'
        if(Test-Path -LiteralPath $lsReady) { Remove-Item -LiteralPath $lsReady }
        $laFiles=@{
            'dm-config.txt'=@(
                'component "Gameplay/Mode Manager"','component "Gameplay/TakedownManager"',
                'set "Gameplay/Mode Manager/Marked man tweaks/Min opponent count" 1',
                'set "Gameplay/Mode Manager/Marked man tweaks/Max opponent count" 1',
                'set "Gameplay/Mode Manager/Marked man tweaks/Min ramp time" 11',
                'set "Gameplay/Mode Manager/Marked man tweaks/Max ramp time" 17',
                'set "Gameplay/Mode Manager/Show mode info" TRUE',
                'set "Gameplay/TakedownManager/Show vulnerability" TRUE',
                'set "Gameplay/TakedownManager/Show revenge takedown info" TRUE',
                'set "Gameplay/TakedownManager/Show last takedown info" TRUE',
                ('save "'+$lsRelative+'/configured.txt"'),
                ('bind F6 exec "../game_slots/'+$ctx.Slot+'/dm-hide.txt"'),
                'bind F7 call "Gameplay/TakedownManager/Force takedown"',
                ('bind F8 exec "../game_slots/'+$ctx.Slot+'/dm-restore.txt"'),
                ('save "../game_slots/'+$ctx.Slot+'/dm-start-ready.txt"'))
            'dm-hide.txt'=@(
                'set "Gameplay/Mode Manager/Show mode info" FALSE',
                'set "Gameplay/TakedownManager/Show vulnerability" FALSE',
                'set "Gameplay/TakedownManager/Show revenge takedown info" FALSE',
                'set "Gameplay/TakedownManager/Show last takedown info" FALSE',
                ('save "'+$lsRelative+'/hidden.txt"'))
            'dm-restore.txt'=@(
                'set "Gameplay/Mode Manager/Show mode info" TRUE',
                'set "Gameplay/TakedownManager/Show vulnerability" TRUE',
                'set "Gameplay/TakedownManager/Show revenge takedown info" TRUE',
                'set "Gameplay/TakedownManager/Show last takedown info" TRUE',
                ('save "'+$lsRelative+'/restored.txt"'))
            'dm-cleanup.txt'=@(
                'set "Gameplay/Mode Manager/Marked man tweaks/Min opponent count" 2',
                'set "Gameplay/Mode Manager/Marked man tweaks/Max opponent count" 4',
                'set "Gameplay/Mode Manager/Marked man tweaks/Min ramp time" 5',
                'set "Gameplay/Mode Manager/Marked man tweaks/Max ramp time" 5',
                'set "Gameplay/Mode Manager/Show mode info" FALSE',
                'set "Gameplay/TakedownManager/Show vulnerability" FALSE',
                'set "Gameplay/TakedownManager/Show revenge takedown info" FALSE',
                'set "Gameplay/TakedownManager/Show last takedown info" FALSE',
                ('save "'+$lsRelative+'/cleanup.txt"'))
        }
        foreach($lsFile in $laFiles.Keys) {
            Set-Content -LiteralPath (Join-Path $ctx.RunDir $lsFile) -Encoding ascii -Value $laFiles[$lsFile]
            Copy-Item -LiteralPath (Join-Path $ctx.RunDir $lsFile) -Destination (Join-Path $lsSlotDir $lsFile)
        }
        $lsSteps=Join-Path $ctx.RunDir 'steps.txt'
        Set-Content -LiteralPath $lsSteps -Encoding ascii -Value @(
            'wait:CarSelectManager: Exit state is finished','key:192',
            ('cmd:exec "../game_slots/'+$ctx.Slot+'/dm-config.txt"'),'key:192','note:configured',
            'wait:\[stunt\] mode state -> E_GMS_IN_PROGRESS','note:in-progress',
            'sleep:3','note:before-force','key:118','sleep:3','note:forced',
            'sleep:8','note:visible','key:117','sleep:3','note:hidden',
            'key:119','sleep:3','note:restored','sleep:3','key:192',
            ('cmd:exec "../game_slots/'+$ctx.Slot+'/dm-cleanup.txt"'),'key:192','note:cleanup')
        $lsHelper=Join-Path $ctx.Root 'tools/tests/tools/VW_DEFORM_debugkeys.ps1'
        $laArgs=@('-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$lsHelper`"",'-GameLog',"`"$($ctx.GameLog)`"",
            '-OutDir',"`"$($ctx.RunDir)`"",'-Slot',"$($ctx.Slot)",'-StepsFile',"`"$lsSteps`"",'-TimeoutSec','100')
        return Start-Process powershell -ArgumentList $laArgs -PassThru -WindowStyle Hidden
    }
    Checks=@(
        @{ Kind='NewAsserts'; Name='no new assert families' }
        @{ Kind='LogCount'; Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }
        @{ Kind='Script'; Name='real console and closed-console control sequence completes'; Script={
            param($ctx)
            $lsFile=Join-Path $ctx.RunDir 'vw_deform_keys.log'
            $lsText=if(Test-Path $lsFile) { Get-Content $lsFile -Raw } else { '' }
            return @{ Pass=$lsText -match 'RESULT DONE'; Detail=($lsText -split "`r?`n" | Where-Object { $_ -match 'note:|RESULT' }) -join ' | ' }
        } }
        @{ Kind='Script'; Name='all four live tunables are saved and defaults restored'; Script={
            param($ctx)
            $laLabels=@('Min opponent count','Max opponent count','Min ramp time','Max ramp time')
            $laExpected=@{'configured.txt'=@(1,1,11,17); 'cleanup.txt'=@(2,4,5,5)}
            $laMissing=@()
            foreach($lsFile in $laExpected.Keys) {
                $lsPath=Join-Path $ctx.RunDir $lsFile
                $lsText=if(Test-Path $lsPath) { Get-Content $lsPath -Raw } else { '' }
                for($li=0;$li -lt 4;$li++) {
                    $lsPattern='(?m)^SET "/Gameplay/Mode Manager/Marked man tweaks/'+$laLabels[$li]+'" "([-0-9.]+)"'
                    if($lsText -notmatch $lsPattern -or [double]::Parse($Matches[1],[cultureinfo]::InvariantCulture) -ne $laExpected[$lsFile][$li]) { $laMissing+=($lsFile+'/'+$laLabels[$li]) }
                }
            }
            return @{ Pass=$laMissing.Count -eq 0; Detail='mismatched backing fields: '+($laMissing -join ', ') }
        } }
        @{ Kind='Script'; Name='actual start consumes edited rival and ramp settings'; Script={
            param($ctx)
            $lsStart=$ctx.LogLines | Where-Object { $_ -match '\[mm-start\] MARKED MAN rankRatio ([-0-9.e+]+) maxOpponents (\d+) numRivals (\d+) startLocations (\d+) maxRampTimer ([-0-9.e+]+)' } | Select-Object -First 1
            if(!$lsStart) { return @{Pass=$false; Detail='missing SurvivorMode::Start witness'} }
            $null=$lsStart -match 'rankRatio ([-0-9.e+]+) maxOpponents (\d+) numRivals (\d+) startLocations (\d+) maxRampTimer ([-0-9.e+]+)'
            $lfRank=[double]::Parse($Matches[1],[cultureinfo]::InvariantCulture)
            $lfRamp=[double]::Parse($Matches[5],[cultureinfo]::InvariantCulture)
            $lbPass=[int]$Matches[2] -eq 1 -and [int]$Matches[3] -eq 1 -and [int]$Matches[4] -eq 2 -and [math]::Abs($lfRamp-(17-6*$lfRank)) -lt 0.002
            return @{ Pass=$lbPass; Detail=$lsStart+'; expected ramp='+[string](17-6*$lfRank) }
        } }
        @{ Kind='LogMatch'; Name='event entered progress after configured harness start'; Pattern='\[stunt\] mode state -> E_GMS_IN_PROGRESS' }
        @{ Kind='LogCount'; Name='one explicitly opted-in event-start injection'; Pattern='HARNESS-ONLY START INJECTION'; Min=1; Max=1 }
        @{ Kind='LogValue'; Name='actual ramp clock advances'; Pattern='\[mm-pre\] .* state 2 dt (?<n>[0-9.]+)'; Group='n'; Agg='max'; Min=0.001 }
        @{ Kind='LogMatch'; Name='real cached snapshot reaches enabled world overlay'; Pattern='\[BRN_TAKEDOWN_DEBUG_TRACE\].* slots=[1-9]\d* .* player-active=1 player-slot=0 toggles=7' }
        @{ Kind='LogMatch'; Name='vulnerability produces real sphere submissions'; Pattern='\[BRN_TAKEDOWN_DEBUG_TRACE\].* vulnerability-(?:shunt-slam|recent-contact)=[1-9]\d* .* geometry-submissions=[1-9]\d*' }
        @{ Kind='Script'; Name='retain visible hidden and restored captures for inspection'; Script={
            param($ctx)
            $lsFile=Join-Path $ctx.RunDir 'vw_deform_keys.log'
            if(!(Test-Path $lsFile)) { return @{Pass=$false;Detail='missing key log'} }
            $laFrames=@(Get-ChildItem -LiteralPath $ctx.FrameDir -Filter '*.bmp' | Sort-Object LastWriteTime)
            $laCopied=@()
            foreach($lsName in @('visible','hidden','restored')) {
                $lsNote=Get-Content $lsFile | Where-Object { $_ -match ('note:'+$lsName+' ') } | Select-Object -First 1
                if(!$lsNote -or $laFrames.Count -eq 0) { continue }
                $ltNote=$laFrames[0].LastWriteTime.Date+[timespan]::Parse(($lsNote -split ' ')[0],[cultureinfo]::InvariantCulture)
                $lrFrame=$laFrames | Where-Object { $_.LastWriteTime -le $ltNote -and ($ltNote-$_.LastWriteTime).TotalSeconds -lt 4 } | Select-Object -Last 1
                if($lrFrame) { Copy-Item -LiteralPath $lrFrame.FullName -Destination (Join-Path $ctx.RunDir ($lsName+'.bmp'));$laCopied+=$lsName }
            }
            return @{Pass=$laCopied.Count -eq 3;Detail='retained '+($laCopied -join ', ')+'; manual visual verdict still required'}
        } }
    )
}
