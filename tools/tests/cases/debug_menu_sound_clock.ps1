# Focused follow-up to the large Sound batch: real statistics, held reset and graph.
@{
    Name='debug_menu_sound_clock'
    Area='debug-menu'
    Bug='Sound statistics must use the original timebase, render its history and honor held reset.'
    Frames=$true
    ProfileFixture='DISCO_collect_base.sav'
    Run=@{ SkipIntro=$true; AcceptGap=1.0; MaxSeconds=75; MinFreeGB=22;
           FrameEvery=240 }
    DiagEnv='BRN_DEBUG_UI_TRACE=1,BRN_FRAME_DUMP_MAX=40'
    Setup={
        param($ctx)
        $lsSlotDir=Join-Path $ctx.Root ('build/game_slots/'+$ctx.Slot)
        New-Item -ItemType Directory -Force $lsSlotDir | Out-Null
        $lsRelative='../../'+$ctx.RunDir.Substring(([string]$ctx.Root).TrimEnd('\').Length+1).Replace('\','/')
        $lsPrefix='Sound Module/Sound/Statistics/'
        $laPhases=@{
            'clock-config'=@('component "Sound Module/Sound"',
                'set "Sound Module/Sound/Console" 2',
                ('set "'+$lsPrefix+'Main Screen Turn On" TRUE'),
                ('set "'+$lsPrefix+'Main Screen Reset" FALSE'),
                ('set "'+$lsPrefix+'Draw Mixer Graph" FALSE'))
            'clock-graph'=@(('set "'+$lsPrefix+'Draw Mixer Graph" TRUE'))
            'clock-reset'=@(('set "'+$lsPrefix+'Main Screen Reset" TRUE'))
            'clock-refill'=@(('set "'+$lsPrefix+'Main Screen Reset" FALSE'))
            'clock-hide'=@(('set "'+$lsPrefix+'Main Screen Turn On" FALSE'),
                ('set "'+$lsPrefix+'Main Screen Reset" FALSE'),
                ('set "'+$lsPrefix+'Draw Mixer Graph" FALSE'))
        }
        foreach($lrBind in @(@('F5','clock-graph'),@('F6','clock-reset'),@('F7','clock-refill'),@('F8','clock-hide'))) {
            $laPhases['clock-config']+=('bind '+$lrBind[0]+' exec "../game_slots/'+$ctx.Slot+'/'+$lrBind[1]+'.txt"')
        }
        foreach($lsPhase in @($laPhases.Keys)) {
            $laPhases[$lsPhase]+=('save "'+$lsRelative+'/'+$lsPhase+'-saved.txt"')
            $lsFile=Join-Path $ctx.RunDir ($lsPhase+'.txt')
            Set-Content -LiteralPath $lsFile -Encoding ascii -Value $laPhases[$lsPhase]
            Copy-Item -LiteralPath $lsFile -Destination (Join-Path $lsSlotDir ($lsPhase+'.txt'))
        }
        $lsSteps=Join-Path $ctx.RunDir 'steps.txt'
        Set-Content -LiteralPath $lsSteps -Encoding ascii -Value @(
            'wait:CarSelectManager: Exit state is finished','key:192',
            ('cmd:exec "../game_slots/'+$ctx.Slot+'/clock-config.txt"'),'key:192',
            'sleep:4','note:statistics','key:116','sleep:4','note:graph',
            'key:117','sleep:3','note:held-reset','key:118','sleep:4','note:refilled',
            'key:119','sleep:3','note:hidden')
        $lsHelper=Join-Path $ctx.Root 'tools/tests/tools/VW_DEFORM_debugkeys.ps1'
        $laArgs=@('-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$lsHelper`"",'-GameLog',"`"$($ctx.GameLog)`"",
            '-OutDir',"`"$($ctx.RunDir)`"",'-Slot',"$($ctx.Slot)",'-StepsFile',"`"$lsSteps`"",'-TimeoutSec','70')
        return Start-Process powershell -ArgumentList $laArgs -PassThru -WindowStyle Hidden
    }
    Checks=@(
        @{ Kind='NewAsserts'; Name='no new assert families' }
        @{ Kind='LogCount'; Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }
        @{ Kind='Script'; Name='complete statistics graph reset refill and hide sequence'; Script={
            param($ctx)
            $lsFile=Join-Path $ctx.RunDir 'vw_deform_keys.log'
            $lsText=if(Test-Path $lsFile) { Get-Content $lsFile -Raw } else { '' }
            return @{Pass=$lsText -match 'RESULT DONE';Detail=($lsText -split "`r?`n" | Where-Object { $_ -match 'note:|RESULT' }) -join ' | '}
        } }
        @{ Kind='Script'; Name='held reset and visibility reach real saved menu cells'; Script={
            param($ctx)
            $laExpected=@{
                'clock-config-saved.txt'=@('TRUE','FALSE','FALSE')
                'clock-graph-saved.txt'=@('TRUE','FALSE','TRUE')
                'clock-reset-saved.txt'=@('TRUE','TRUE','TRUE')
                'clock-refill-saved.txt'=@('TRUE','FALSE','TRUE')
                'clock-hide-saved.txt'=@('FALSE','FALSE','FALSE')
            }
            $laNames=@('Main Screen Turn On','Main Screen Reset','Draw Mixer Graph')
            $laMissing=@()
            foreach($lsFile in $laExpected.Keys) {
                $lsPath=Join-Path $ctx.RunDir $lsFile
                $lsText=if(Test-Path $lsPath) { Get-Content $lsPath -Raw } else { '' }
                for($li=0;$li -lt 3;$li++) {
                    $lsPattern='(?m)^SET "/Sound Module/Sound/Statistics/'+[regex]::Escape($laNames[$li])+'" "'+$laExpected[$lsFile][$li]+'"'
                    if($lsText -notmatch $lsPattern) { $laMissing+=($lsFile+'/'+$laNames[$li]) }
                }
            }
            return @{Pass=$laMissing.Count -eq 0;Detail='mismatched cells '+($laMissing -join ', ')}
        } }
        @{ Kind='Script'; Name='retain statistics graph held-reset refill and hidden pixels'; Script={
            param($ctx)
            $lsFile=Join-Path $ctx.RunDir 'vw_deform_keys.log'
            if(!(Test-Path $lsFile)) { return @{Pass=$false;Detail='missing sequence log'} }
            $laFrames=@(Get-ChildItem -LiteralPath $ctx.FrameDir -Filter '*.bmp' | Sort-Object LastWriteTime)
            $laCopied=@()
            foreach($lsName in @('statistics','graph','held-reset','refilled','hidden')) {
                $lsNote=Get-Content $lsFile | Where-Object { $_ -match ('note:'+$lsName+' ') } | Select-Object -First 1
                if(!$lsNote -or $laFrames.Count -eq 0) { continue }
                $ltNote=$laFrames[0].LastWriteTime.Date+[timespan]::Parse(($lsNote -split ' ')[0],[cultureinfo]::InvariantCulture)
                $lrFrame=$laFrames | Where-Object { $_.LastWriteTime -le $ltNote -and ($ltNote-$_.LastWriteTime).TotalSeconds -lt 5 } | Select-Object -Last 1
                if($lrFrame) { Copy-Item -LiteralPath $lrFrame.FullName -Destination (Join-Path $ctx.RunDir ($lsName+'.bmp'));$laCopied+=$lsName }
            }
            return @{Pass=$laCopied.Count -eq 5;Detail='retained '+($laCopied -join ', ')+'; pixels and timing values require review'}
        } }
    )
}
