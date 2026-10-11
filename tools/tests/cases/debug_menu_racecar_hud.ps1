# Real console controls followed by closed-console captures of each original HUD.
@{
    Name='debug_menu_racecar_hud'
    Area='debug-menu'
    Bug='Race-car HUD controls must reach the original state/statistics readers and render readable text.'
    Frames=$true
    ProfileFixture='DISCO_collect_base.sav'
    Run=@{ SkipIntro=$true; AcceptGap=1.0; MaxSeconds=140; MinFreeGB=23;
           Drive=$true; DriveDelay=20.0; DriveSeconds=10.0; MotionProbe=$true;
           Teleport='3040.7,-5.8,-1937.9,180'; FrameEvery=300 }
    DiagEnv='BRN_DEBUG_UI_TRACE=1,BRN_RACECAR_HUD_TRACE=1,BRN_FRAME_DUMP_MAX=60'
    Setup={
        param($ctx)
        $lsRelative='../../'+$ctx.RunDir.Substring(([string]$ctx.Root).TrimEnd('\').Length+1).Replace('\','/')
        $laControls=@('Render car damage state','Render car streaming state','Show average speed','Show player engine state','Traffic Related')
        $laScripts=@{ 'activate'='Show average speed'; 'engine'='Show player engine state';
            'damage'='Render car damage state'; 'streaming'='Render car streaming state';
            'traffic'='Traffic Related'; 'hidden'=''; 'restored'='Show average speed'; 'cleanup'='' }
        foreach($lsName in $laScripts.Keys) {
            $laLines=@()
            if($lsName -eq 'activate') { $laLines+='component "Race Car Entity"' }
            foreach($lsControl in $laControls) {
                $lsValue=if($lsControl -eq $laScripts[$lsName]) { 'TRUE' } else { 'FALSE' }
                $laLines+=('set "Race Car Entity/'+$lsControl+'" '+$lsValue)
            }
            $laLines+=('save "'+$lsRelative+'/'+$lsName+'-saved.txt"')
            if($lsName -eq 'activate') {
                $laLines+=@(
                    ('bind F2 exec "'+$lsRelative+'/engine.txt"'),('bind F3 exec "'+$lsRelative+'/damage.txt"'),
                    ('bind F4 exec "'+$lsRelative+'/streaming.txt"'),('bind F5 exec "'+$lsRelative+'/traffic.txt"'),
                    ('bind F6 exec "'+$lsRelative+'/hidden.txt"'),('bind F7 call "Race Car Entity/Reset average speed"'),
                    ('bind F8 exec "'+$lsRelative+'/restored.txt"'))
            }
            Set-Content -LiteralPath (Join-Path $ctx.RunDir ($lsName+'.txt')) -Encoding ascii -Value $laLines
        }
        $lsSteps=Join-Path $ctx.RunDir 'debug-menu-steps.txt'
        Set-Content -LiteralPath $lsSteps -Encoding ascii -Value @(
            'wait:CarSelectManager: Exit state is finished','key:192',('cmd:exec "'+$lsRelative+'/activate.txt"'),
            'key:192','sleep:16','note:average','key:118','sleep:3','note:reset',
            'key:113','sleep:5','note:engine','key:114','sleep:5','note:damage',
            'key:115','sleep:5','note:streaming','key:116','sleep:5','note:traffic',
            'key:117','sleep:5','note:hidden','key:119','sleep:5','note:restored',
            'key:192',('cmd:exec "'+$lsRelative+'/cleanup.txt"'),'key:192','note:cleanup')
        $lsHelper=Join-Path $ctx.Root 'tools/tests/tools/VW_DEFORM_debugkeys.ps1'
        $laArgs=@('-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$lsHelper`"",'-GameLog',"`"$($ctx.GameLog)`"",
            '-OutDir',"`"$($ctx.RunDir)`"",'-Slot',"$($ctx.Slot)",'-StepsFile',"`"$lsSteps`"",'-TimeoutSec','135')
        return Start-Process powershell -ArgumentList $laArgs -PassThru -WindowStyle Hidden
    }
    Checks=@(
        @{ Kind='NewAsserts'; Name='no new assert families' }
        @{ Kind='LogCount'; Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }
        @{ Kind='Script'; Name='real console and closed-console F-key sequence completes'; Script={
            param($ctx)
            $lsFile=Join-Path $ctx.RunDir 'vw_deform_keys.log'
            $lsText=if(Test-Path $lsFile) { Get-Content $lsFile -Raw } else { '' }
            return @{ Pass=$lsText -match 'RESULT DONE'; Detail=($lsText -split "`r?`n" | Where-Object { $_ -match 'note:|RESULT' }) -join ' | ' }
        } }
        @{ Kind='Script'; Name='each HUD registry state and final restoration are saved'; Script={
            param($ctx)
            # SAVE reads the actual registered fields. Together with glyph submissions
            # and the retained images, this avoids depending on the trace-line budget.
            $laControls=@('Render car damage state','Render car streaming state','Show average speed','Show player engine state','Traffic Related')
            $laStates=@{ 'activate'='Show average speed'; 'engine'='Show player engine state';
                'damage'='Render car damage state'; 'streaming'='Render car streaming state';
                'traffic'='Traffic Related'; 'hidden'=''; 'restored'='Show average speed'; 'cleanup'='' }
            $laMissing=@()
            foreach($lsState in $laStates.Keys) {
                $lsFile=Join-Path $ctx.RunDir ($lsState+'-saved.txt')
                $lsText=if(Test-Path $lsFile) { Get-Content $lsFile -Raw } else { '' }
                foreach($lsName in $laControls) {
                    $lsValue=if($lsName -eq $laStates[$lsState]) { 'TRUE' } else { 'FALSE' }
                    if($lsText -notmatch ('(?m)^SET "/Race Car Entity/'+[regex]::Escape($lsName)+'" "'+$lsValue+'"')) {
                        $laMissing+=($lsState+'/'+$lsName)
                    }
                }
            }
            return @{ Pass=$laMissing.Count -eq 0; Detail='40 saved field checks; mismatches: '+($laMissing -join ', ') }
        } }
        @{ Kind='Script'; Name='actual glyph submissions cover all six original readouts'; Script={
            param($ctx)
            $laSeen=@($ctx.LogLines | Where-Object { $_ -match '\[racecar-hud-text\] kind=(\d+) vertices=([1-9]\d*)' } | ForEach-Object { [int]$Matches[1] })
            $laMissing=@(1,2,4,8,16,32 | Where-Object { $_ -notin $laSeen })
            return @{ Pass=$laMissing.Count -eq 0; Detail='missing HUD glyph kinds: '+($laMissing -join ', ') }
        } }
        @{ Kind='Script'; Name='average speed accumulates nonzero samples and reset clears both original fields'; Script={
            param($ctx)
            $liPositive=@($ctx.LogLines | Where-Object { $_ -match '\[racecar-hud\] mask=4 samples=([1-9]\d*) average_mps=([-0-9.e+]+)' -and [double]::Parse($Matches[2],[cultureinfo]::InvariantCulture) -gt 0.1 }).Count
            $liReset=@($ctx.LogLines | Where-Object { $_ -match '\[racecar-hud-reset\] samples_before=([1-9]\d*) samples_after=0 average_after=0' }).Count
            return @{ Pass=$liPositive -ge 1 -and $liReset -eq 1; Detail="nonzero average samples=$liPositive original reset witnesses=$liReset" }
        } }
        @{ Kind='Script'; Name='retain visible HUD and hidden frames for pixel inspection'; Script={
            param($ctx)
            $lsHelper=Join-Path $ctx.RunDir 'vw_deform_keys.log'
            if(!(Test-Path $lsHelper)) { return @{ Pass=$false; Detail='missing key log' } }
            $laFrames=@(Get-ChildItem -LiteralPath $ctx.FrameDir -Filter '*.bmp' | Sort-Object LastWriteTime)
            $laCopied=@()
            foreach($lsName in @('average','reset','engine','damage','streaming','traffic','hidden','restored')) {
                $lsNote=Get-Content $lsHelper | Where-Object { $_ -match ('note:'+$lsName+' ') } | Select-Object -First 1
                if(!$lsNote -or $laFrames.Count -eq 0) { continue }
                $ltNote=$laFrames[0].LastWriteTime.Date+[timespan]::Parse(($lsNote -split ' ')[0],[cultureinfo]::InvariantCulture)
                $lrFrame=$laFrames | Where-Object { $_.LastWriteTime -le $ltNote -and ($ltNote-$_.LastWriteTime).TotalSeconds -lt 4 } | Select-Object -Last 1
                if($lrFrame) { Copy-Item -LiteralPath $lrFrame.FullName -Destination (Join-Path $ctx.RunDir ($lsName+'.bmp')); $laCopied+=$lsName }
            }
            return @{ Pass=$laCopied.Count -eq 8; Detail='retained '+($laCopied -join ', ')+'; inspect actual text before a visual verdict' }
        } }
    )
}
