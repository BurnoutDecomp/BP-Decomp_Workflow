# One native scenario for the 108-site Traffic page. Source/CPU evidence covers
# individual bindings; retained frames and traffic records witness grouped effects.
# Keep world overlays in small groups: ARTIST's fixed render bank can overflow
# when every overlay is enabled together. The player-hull readout also requires
# a live hull, so turn it off before the original Turn traffic off control.
@{
    Name='debug_menu_traffic_batch'
    SourceRoot=[System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
    RunSlot=$Slot
    Area='debug-menu'
    Bug='Original Traffic controls must reach their embedded owner, telemetry and recovered drawing paths.'
    Frames=$true
    PhaseNames=@('hud','lanes','lane-curves','lane-links','lane-junctions',
        'vehicles','vehicle-details','params','param-fuzzy','param-links',
        'picking','killzones','off','cleanup')
    ReadoutPaths=@('Stats/Over budget-ness','Stats/Active params','Stats/Free params',
        'Stats/Purgatory params','Stats/Active hulls','Traffic Jams/Player slow driving time',
        'Traffic Jams/Player in same hull time','FINAL density scale','Crash Control/Crash score',
        'Crash Control/Final value','Crash Control/Player Idle Time','Crash Control/Showtime Timer',
        'Crash Control/Showtime Next Spike','Crash Control/Showtime Mis Bounce Time',
        'Junction FUP Detection/Junction FUP')
    CallbackPaths=@('Air Rams/Fire!','KillZones/Fire KillZone!','Kill traffic near player',
        'Reload Behaviour Data','Picking/Pick vehicle')
    ProfileFixture='DISCO_collect_base.sav'
    Run=@{ SkipIntro=$true; AcceptGap=1.0; MaxSeconds=125; MinFreeGB=20;
           Drive=$true; DriveDelay=27.0; DriveSeconds=90.0; MotionProbe=$true;
           Teleport='3040.7,-5.8,-1937.9,180'; FrameEvery=360 }
    DiagEnv='BRN_DEBUG_UI_TRACE=1,BRN_TRAFFIC_TRACK=1,BRN_FRAME_DUMP_MAX=96'
    Setup={
        param($ctx)
        $lsSlotDir=Join-Path $ctx.Root ('build/game_slots/'+$ctx.Slot)
        New-Item -ItemType Directory -Force $lsSlotDir | Out-Null
        $lsRelative='../../'+$ctx.RunDir.Substring(([string]$ctx.Root).TrimEnd('\').Length+1).Replace('\','/')
        $lsPrefix='Traffic/'
        $laHud=@('DRAWING 2/Draw active hulls','DRAWING 2/Draw player hull id','Performance/Render special perfmons')
        $laLanes=@('DRAWING/Render Segments','DRAWING/Render Sections','DRAWING/Render Section Curves',
            'DRAWING/Render Splitters','DRAWING/Render Neighbours','DRAWING/Render Junctions',
            'DRAWING/Render Stop Lines','DRAWING/Render Start Grids')
        $laVehicles=@('DRAWING/Render Vehicles','DRAWING/Render non-collidable vehicles',
            'DRAWING/Render collidable vehicles','DRAWING/Render phys vehicle state',
            'DRAWING/Render vehicle manoeuvres','DRAWING 2/Show Vehicle IDs',
            'DRAWING 2/Show Nearest Vehicle ID','DRAWING 2/Draw front artic points',
            'DRAWING 2/Draw rear artic points','DRAWING 2/Draw axles','DRAWING 2/Draw horns')
        $laParams=@('DRAWING/Render Params','DRAWING/Render lerped param positions',
            'DRAWING/Render param behaviours','DRAWING/Render param slow data',
            'DRAWING/Render param fuzzy scores','DRAWING/Render param trails','DRAWING/Render Param-Vehicle Links',
            'DRAWING/Render Param-Param Links','DRAWING 2/Draw AI Avoidance',
            'DRAWING 2/Draw AI Avoidance BrainPain','DRAWING 2/Render Stuck detection',
            'Show vehicle swerving debug')
        $laKillzones=@('DRAWING 2/Render ALL kill zones','DRAWING 2/Render recent kill zones')
        $laAllFlags=@($laHud+$laLanes+$laVehicles+$laParams+$laKillzones+@('Picking/Enable Picking'))
        $laGroups=@(
            @{Name='hud';Flags=@()}
            @{Name='lanes';Flags=@($laLanes[0],$laLanes[1])}
            @{Name='lane-curves';Flags=@($laLanes[2])}
            @{Name='lane-links';Flags=@($laLanes[3],$laLanes[4])}
            @{Name='lane-junctions';Flags=@($laLanes[5],$laLanes[6],$laLanes[7])}
            @{Name='vehicles';Flags=@($laVehicles[0..3]);Stopped=$true}
            @{Name='vehicle-details';Flags=@($laVehicles[4..10]);Stopped=$true}
            @{Name='params';Flags=@($laParams[0..3])}
            @{Name='param-fuzzy';Flags=@($laParams[4])}
            @{Name='param-links';Flags=@($laParams[5..11])}
            @{Name='picking';Flags=@('Picking/Enable Picking');Command='call "Traffic/Picking/Pick vehicle"'}
            @{Name='killzones';Flags=$laKillzones;Command='call "Traffic/KillZones/Fire KillZone!"'}
            @{Name='off';Flags=@();TrafficOff=$true}
            @{Name='cleanup';Flags=@()}
        )
        $laWorldFlags=@($laLanes+$laVehicles+$laParams+$laKillzones+@('Picking/Enable Picking'))
        if(($laGroups.Name -join ',') -ne ($ctx.Case.PhaseNames -join ',')) { throw 'Traffic phase names drifted.' }
        for($liPhase=0;$liPhase -lt $laGroups.Count;++$liPhase) {
            $lrGroup=$laGroups[$liPhase]
            $lsPhase=if($liPhase -eq 0) {'traffic-config'} else {'traffic-'+$lrGroup.Name}
            $laLines=@()
            if($liPhase -eq 0) {
                $laLines+='component "Traffic"'
                # SAVE omits original read-only cells; aliases resolve them without editing them.
                for($liReadout=0;$liReadout -lt $ctx.Case.ReadoutPaths.Count;++$liReadout) {
                    $laLines+=('alias tr'+$liReadout+' "Traffic/'+$ctx.Case.ReadoutPaths[$liReadout]+'"')
                }
                for($liCallback=0;$liCallback -lt $ctx.Case.CallbackPaths.Count;++$liCallback) {
                    $laLines+=('alias tf'+$liCallback+' "Traffic/'+$ctx.Case.CallbackPaths[$liCallback]+'"')
                }
                $laLines+=('save "'+$lsRelative+'/registered.txt"')
                foreach($lsName in $laHud) {$laLines+=('set "'+$lsPrefix+$lsName+'" TRUE')}
            }
            foreach($lsName in $laWorldFlags) {$laLines+=('set "'+$lsPrefix+$lsName+'" FALSE')}
            if($lrGroup.Name -in @('off','cleanup')) {
                foreach($lsName in $laHud) {$laLines+=('set "'+$lsPrefix+$lsName+'" FALSE')}
            }
            $laLines+=('set "Traffic/Turn traffic off" '+$(if($lrGroup.TrafficOff) {'TRUE'} else {'FALSE'}))
            $laLines+=('set "Traffic/Stop traffic moving" '+$(if($lrGroup.Stopped) {'TRUE'} else {'FALSE'}))
            foreach($lsName in $lrGroup.Flags) {$laLines+=('set "'+$lsPrefix+$lsName+'" TRUE')}
            if($lrGroup.Command) {$laLines+=$lrGroup.Command}
            # Rebind the same function key after each stage; all stages share one boot.
            if($liPhase+1 -lt $laGroups.Count) {
                $laLines+=('bind F2 exec "../game_slots/'+$ctx.Slot+'/traffic-'+$laGroups[$liPhase+1].Name+'.txt"')
            }
            $laLines+=('save "'+$lsRelative+'/'+$lsPhase+'-saved.txt"')
            $lsFile=Join-Path $ctx.RunDir ($lsPhase+'.txt')
            Set-Content -LiteralPath $lsFile -Encoding ascii -Value $laLines
            Copy-Item -LiteralPath $lsFile -Destination (Join-Path $lsSlotDir ($lsPhase+'.txt'))
        }
        $lsSteps=Join-Path $ctx.RunDir 'steps.txt'
        $laSteps=@(
            'wait:CarSelectManager: Exit state is finished','key:192',
            ('cmd:exec "../game_slots/'+$ctx.Slot+'/traffic-config.txt"'),'key:192',
            'sleep:5','note:hud')
        foreach($lsName in $ctx.Case.PhaseNames | Select-Object -Skip 1) {
            $laSteps+=@('key:113','sleep:5',('note:'+$lsName))
        }
        Set-Content -LiteralPath $lsSteps -Encoding ascii -Value $laSteps
        $lsHelper=Join-Path $ctx.Root 'tools/tests/tools/VW_DEFORM_debugkeys.ps1'
        $laArgs=@('-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$lsHelper`"",'-GameLog',"`"$($ctx.GameLog)`"",
            '-OutDir',"`"$($ctx.RunDir)`"",'-Slot',"$($ctx.Slot)",'-StepsFile',"`"$lsSteps`"",'-TimeoutSec','120')
        return Start-Process powershell -ArgumentList $laArgs -PassThru -WindowStyle Hidden
    }
    Checks=@(
        @{ Kind='NewAsserts'; Name='no new assert families' }
        @{ Kind='LogCount'; Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }
        @{ Kind='Script'; Name='complete grouped Traffic console sequence'; Script={
            param($ctx)
            $lsFile=Join-Path $ctx.RunDir 'vw_deform_keys.log'
            $lsText=if(Test-Path $lsFile) { Get-Content $lsFile -Raw } else { '' }
            return @{Pass=$lsText -match 'RESULT DONE';Detail=($lsText -split "`r?`n" | Where-Object { $_ -match 'note:|RESULT' }) -join ' | '}
        } }
        @{ Kind='Script'; Name='all literal Traffic variable paths exist in the native registry'; Script={
            param($ctx)
            $lsFile=Join-Path $ctx.RunDir 'registered.txt'
            $lsText=if(Test-Path $lsFile) { Get-Content $lsFile -Raw } else { '' }
            $lrInventory=Get-Content (Join-Path $ctx.Case.SourceRoot 'progress/debug_menu/entries.json') -Raw | ConvertFrom-Json
            $laSites=@($lrInventory.entries | Where-Object { $_.function -eq 'BrnTraffic::DebugComponent::OnActivate' })
            $laVariables=@($laSites | Where-Object { $_.kind -eq 'variable' -and $_.caption })
            $laMissing=@()
            foreach($lrEntry in $laVariables) {
                $lsPath='/Traffic/'+$(if($lrEntry.path) { $lrEntry.path+'/' } else { '' })+$lrEntry.caption
                $lbPresent=$lsText -match ('(?m)^SET "'+[regex]::Escape($lsPath)+'" ')
                $liReadout=[array]::IndexOf($ctx.Case.ReadoutPaths,$lsPath.Substring(9))
                if($liReadout -ge 0) {$lbPresent=$lsText -match ('(?m)^ALIAS tr'+$liReadout+' "'+[regex]::Escape($lsPath)+'"')}
                if(!$lbPresent) { $laMissing+=$lrEntry.id }
            }
            for($liCallback=0;$liCallback -lt $ctx.Case.CallbackPaths.Count;++$liCallback) {
                $lsPath='/Traffic/'+$ctx.Case.CallbackPaths[$liCallback]
                if($lsText -notmatch ('(?m)^ALIAS tf'+$liCallback+' "'+[regex]::Escape($lsPath)+'"')) {$laMissing+=$lsPath}
            }
            return @{Pass=$laSites.Count -eq 108 -and $laVariables.Count -eq 102 -and $laMissing.Count -eq 0;
                Detail='108 source sites; checked102 literal native variables (15 read-only aliases) and5 callback aliases; dynamic asset caption needs separate evidence; missing '+($laMissing -join ', ')}
        } }
        @{ Kind='LogMatch'; Name='actual traffic population and transforms are sampled'; Pattern='\[traffic-track\] t=.* id=\d+ pos=\(' }
        @{ Kind='Script'; Name='grouped controls restore their original off state'; Script={
            param($ctx)
            $lsFile=Join-Path $ctx.RunDir 'traffic-cleanup-saved.txt'
            $lsText=if(Test-Path $lsFile) { Get-Content $lsFile -Raw } else { '' }
            $laNames=@('Turn traffic off','Stop traffic moving','DRAWING 2/Draw active hulls',
                'DRAWING 2/Draw player hull id','Performance/Render special perfmons','Picking/Enable Picking')
            $laMissing=@($laNames | Where-Object { $lsText -notmatch ('(?m)^SET "/Traffic/'+[regex]::Escape($_)+'" "FALSE"') })
            return @{Pass=$laMissing.Count -eq 0;Detail='mismatched final cells '+($laMissing -join ', ')}
        } }
        @{ Kind='Script'; Name='retain grouped behavior captures'; Script={
            param($ctx)
            $lsFile=Join-Path $ctx.RunDir 'vw_deform_keys.log'
            if(!(Test-Path $lsFile)) { return @{Pass=$false;Detail='missing key sequence log'} }
            $laFrames=@(Get-ChildItem -LiteralPath $ctx.FrameDir -Filter '*.bmp' | Sort-Object LastWriteTime)
            $laCopied=@()
            foreach($lsName in $ctx.Case.PhaseNames) {
                $lsNote=Get-Content $lsFile | Where-Object { $_ -match ('note:'+$lsName+' ') } | Select-Object -First 1
                if(!$lsNote -or $laFrames.Count -eq 0) { continue }
                $ltNote=$laFrames[0].LastWriteTime.Date+[timespan]::Parse(($lsNote -split ' ')[0],[cultureinfo]::InvariantCulture)
                if(($ltNote-$laFrames[0].LastWriteTime).TotalHours -lt -12) {$ltNote=$ltNote.AddDays(1)}
                $lrFrame=$laFrames | Where-Object { $_.LastWriteTime -le $ltNote -and ($ltNote-$_.LastWriteTime).TotalSeconds -lt 5 } | Select-Object -Last 1
                if($lrFrame) { Copy-Item -LiteralPath $lrFrame.FullName -Destination (Join-Path $ctx.RunDir ($lsName+'.bmp'));$laCopied+=$lsName }
            }
            return @{Pass=$laCopied.Count -eq $ctx.Case.PhaseNames.Count;Detail='retained '+($laCopied -join ', ')+'; pixels and phase traffic samples require review'}
        } }
    )
}
