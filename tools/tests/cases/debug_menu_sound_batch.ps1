# One shared scenario for the137-site Sound recovery; source checks cover each
# binding, while this run retains native registry, HUD, dump and PCM witnesses.
@{
    Name='debug_menu_sound_batch'
    SourceRoot=[System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
    RunSlot=$Slot
    Area='debug-menu'
    Bug='The complete Sound page must bind its real consumers and draw/update through the original embedded owner.'
    Frames=$true
    ProfileFixture='DISCO_collect_base.sav'
    Run=@{ SkipIntro=$true; AcceptGap=1.0; MaxSeconds=110; MinFreeGB=22;
           Drive=$true; DriveDelay=27.0; DriveSeconds=65.0; MotionProbe=$true;
           Teleport='3040.7,-5.8,-1937.9,180'; FrameEvery=300 }
    DiagEnv="BRN_DEBUG_UI_TRACE=1,BRN_DMIX_DIAG=1,BRN_ENGINE_MIX_DIAG=1,BRN_RWAC_PARAM_DIAG=1,BRN_FRAME_DUMP_MAX=48,BRN_AUDIO_CAPTURE_ENGINE=../game_slots/$Slot/sound-batch-engine.wav"
    Setup={
        param($ctx)
        $lsSlotDir=Join-Path $ctx.Root ('build/game_slots/'+$ctx.Slot)
        New-Item -ItemType Directory -Force $lsSlotDir | Out-Null
        $lsRelative='../../'+$ctx.RunDir.Substring(([string]$ctx.Root).TrimEnd('\').Length+1).Replace('\','/')
        $lsPrefix='Sound Module/Sound/'
        $laFlags=@('Statistics/Main Screen Turn On','Statistics/Draw Mixer Graph',
            'Statistics/Main Screen Reset','Engines/Max Rpm Display',
            'Engines/Hold Car in Place','Engines/Hold Car SPINNING in AIR',
            'Passbys&Reverb/Show Static','Emitters/Debug')
        $laInitial=@(
            'component "Sound Module/Sound"',('set "'+$lsPrefix+'Console" 2'),
            ('save "'+$lsRelative+'/registered.txt"'),
            ('set "'+$lsPrefix+'Statistics/Main Screen Turn On" TRUE'),
            ('set "'+$lsPrefix+'Engines/Max Rpm Display" TRUE'),
            ('set "'+$lsPrefix+'Statistics/Memory Dump" 1'),
            ('set "'+$lsPrefix+'Statistics/Splice Stats Dump" 1'))
        $laPhases=@{
            'sound-config'=$laInitial
            'sound-graph'=@(('set "'+$lsPrefix+'Statistics/Draw Mixer Graph" TRUE'),
                ('set "'+$lsPrefix+'Passbys&Reverb/Show Static" TRUE'),
                ('set "'+$lsPrefix+'Emitters/Debug" TRUE'))
            'sound-mute'=@(('set "'+$lsPrefix+'Global/Master Gain" 0'))
            'sound-restore'=@(('set "'+$lsPrefix+'Global/Master Gain" 4'))
            'sound-hold'=@(('set "'+$lsPrefix+'Engines/Hold Car in Place" TRUE'))
            'sound-spin'=@(('set "'+$lsPrefix+'Engines/Spin Speed Y" 0.1'),
                ('set "'+$lsPrefix+'Engines/Hold Car SPINNING in AIR" TRUE'))
            'sound-reset'=@(('set "'+$lsPrefix+'Statistics/Main Screen Reset" TRUE'))
            'sound-cleanup'=@()
        }
        foreach($lsFlag in $laFlags) { $laPhases['sound-cleanup']+=('set "'+$lsPrefix+$lsFlag+'" FALSE') }
        $laPhases['sound-cleanup']+=@(('set "'+$lsPrefix+'Global/Master Gain" 4'),
            ('set "'+$lsPrefix+'Engines/Spin Speed Y" 0'))
        $laBindings=@{'F2'='sound-graph';'F3'='sound-mute';'F4'='sound-restore';
            'F5'='sound-hold';'F6'='sound-spin';'F7'='sound-reset';'F8'='sound-cleanup'}
        foreach($lsKey in $laBindings.Keys) {
            $laPhases['sound-config']+=('bind '+$lsKey+' exec "../game_slots/'+$ctx.Slot+'/'+$laBindings[$lsKey]+'.txt"')
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
            ('cmd:exec "../game_slots/'+$ctx.Slot+'/sound-config.txt"'),'key:192',
            'sleep:5','note:statistics','key:113','sleep:5','note:graph',
            'key:114','sleep:5','note:muted','key:115','sleep:5','note:restored',
            'key:116','sleep:4','note:held','key:117','sleep:4','note:spinning',
            'key:118','sleep:2','note:reset','key:119','sleep:5','note:cleanup')
        $lsHelper=Join-Path $ctx.Root 'tools/tests/tools/VW_DEFORM_debugkeys.ps1'
        $laArgs=@('-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$lsHelper`"",'-GameLog',"`"$($ctx.GameLog)`"",
            '-OutDir',"`"$($ctx.RunDir)`"",'-Slot',"$($ctx.Slot)",'-StepsFile',"`"$lsSteps`"",'-TimeoutSec','105')
        return Start-Process powershell -ArgumentList $laArgs -PassThru -WindowStyle Hidden
    }
    Checks=@(
        @{ Kind='NewAsserts'; Name='no new assert families' }
        @{ Kind='LogCount'; Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }
        @{ Kind='Script'; Name='one complete Sound console sequence'; Script={
            param($ctx)
            $lsFile=Join-Path $ctx.RunDir 'vw_deform_keys.log'
            $lsText=if(Test-Path $lsFile) { Get-Content $lsFile -Raw } else { '' }
            return @{Pass=$lsText -match 'RESULT DONE';Detail=($lsText -split "`r?`n" | Where-Object { $_ -match 'note:|RESULT' }) -join ' | '}
        } }
        @{ Kind='Script'; Name='all original Sound paths exist in the native registry'; Script={
            param($ctx)
            $lsFile=Join-Path $ctx.RunDir 'registered.txt'
            $lsText=if(Test-Path $lsFile) { Get-Content $lsFile -Raw } else { '' }
            $lrInventory=Get-Content (Join-Path $ctx.Case.SourceRoot 'progress/debug_menu/entries.json') -Raw | ConvertFrom-Json
            $laEntries=@($lrInventory.entries | Where-Object { $_.function -in @('BrnSound::Debug::DebugComponent::OnActivate','BrnSound::Debug::DebugComponent::InstallConsole') })
            $laMissing=@()
            foreach($lrEntry in $laEntries) {
                $lsPath='/Sound Module/Sound/'+$(if($lrEntry.path) { $lrEntry.path+'/' } else { '' })+$lrEntry.caption
                if($lsText -notmatch ('(?m)^SET "'+[regex]::Escape($lsPath)+'" ')) { $laMissing+=$lrEntry.id }
            }
            return @{Pass=$laEntries.Count -eq 137 -and $laMissing.Count -eq 0;
                Detail='137 original registration sites, including duplicate captions; missing '+($laMissing -join ', ')}
        } }
        @{ Kind='LogMatch'; Name='original memory action reaches actual allocator dump'; Pattern='End of DebugAudioMemoryDump\(\)' }
        @{ Kind='Script'; Name='both one-shot dump cells clear and normal flags restore'; Script={
            param($ctx)
            $lsFile=Join-Path $ctx.RunDir 'sound-cleanup-saved.txt'
            $lsText=if(Test-Path $lsFile) { Get-Content $lsFile -Raw } else { '' }
            $laMissing=@()
            foreach($lsName in @('Statistics/Memory Dump','Statistics/Splice Stats Dump')) {
                if($lsText -notmatch ('(?m)^SET "/Sound Module/Sound/'+[regex]::Escape($lsName)+'" "0"')) { $laMissing+=$lsName }
            }
            foreach($lsName in @('Statistics/Main Screen Turn On','Statistics/Main Screen Reset','Statistics/Draw Mixer Graph',
                'Engines/Max Rpm Display','Engines/Hold Car in Place','Engines/Hold Car SPINNING in AIR','Passbys&Reverb/Show Static','Emitters/Debug')) {
                if($lsText -notmatch ('(?m)^SET "/Sound Module/Sound/'+[regex]::Escape($lsName)+'" "FALSE"')) { $laMissing+=$lsName }
            }
            return @{Pass=$laMissing.Count -eq 0;Detail='mismatched final cells '+($laMissing -join ', ')}
        } }
        @{ Kind='Script'; Name='retain shared HUD graph physics and restored captures'; Script={
            param($ctx)
            $lsFile=Join-Path $ctx.RunDir 'vw_deform_keys.log'
            if(!(Test-Path $lsFile)) { return @{Pass=$false;Detail='missing key sequence log'} }
            $laFrames=@(Get-ChildItem -LiteralPath $ctx.FrameDir -Filter '*.bmp' | Sort-Object LastWriteTime)
            $laCopied=@()
            foreach($lsName in @('statistics','graph','muted','restored','held','spinning','reset','cleanup')) {
                $lsNote=Get-Content $lsFile | Where-Object { $_ -match ('note:'+$lsName+' ') } | Select-Object -First 1
                if(!$lsNote -or $laFrames.Count -eq 0) { continue }
                $ltNote=$laFrames[0].LastWriteTime.Date+[timespan]::Parse(($lsNote -split ' ')[0],[cultureinfo]::InvariantCulture)
                $lrFrame=$laFrames | Where-Object { $_.LastWriteTime -le $ltNote -and ($ltNote-$_.LastWriteTime).TotalSeconds -lt 5 } | Select-Object -Last 1
                if($lrFrame) { Copy-Item -LiteralPath $lrFrame.FullName -Destination (Join-Path $ctx.RunDir ($lsName+'.bmp'));$laCopied+=$lsName }
            }
            return @{Pass=$laCopied.Count -eq 8;Detail='retained '+($laCopied -join ', ')+'; inspect pixels for visual verdicts'}
        } }
        @{ Kind='Script'; Name='retain engine-only PCM and measured output for phase analysis'; Script={
            param($ctx)
            $lsSource=Join-Path $ctx.Case.SourceRoot ('build/game_slots/'+$ctx.Case.RunSlot+'/sound-batch-engine.wav')
            if(!(Test-Path -LiteralPath $lsSource)) { return @{Pass=$false;Detail='engine capture was not produced'} }
            $lsTarget=Join-Path $ctx.RunDir 'engine.wav'
            Copy-Item -LiteralPath $lsSource -Destination $lsTarget
            $liSamples=@($ctx.LogLines | Where-Object { $_ -match '\[engine-mix\] line=\d+ rms=' }).Count
            return @{Pass=(Get-Item -LiteralPath $lsTarget).Length -gt 44 -and $liSamples -ge 3;
                Detail="engine PCM retained; measurement windows=$liSamples; phase effects require review"}
        } }
    )
}
