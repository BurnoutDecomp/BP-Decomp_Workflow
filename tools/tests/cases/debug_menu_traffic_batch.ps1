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
           Teleport='3040.7,-5.8,-1937.9,180'; FrameEvery=180 }
    DiagEnv='BRN_DEBUG_UI_TRACE=1,BRN_TRAFFIC_TRACK=1,BRN_FRAME_DUMP_MAX=96'
    Setup={
        param($ctx)
        if($ctx.Slot -le 0) {throw 'Traffic batch requires a private slot for its config and scripts.'}
        $lsSlotDir=Join-Path $ctx.Root ('build/game_slots/'+$ctx.Slot)
        New-Item -ItemType Directory -Force $lsSlotDir | Out-Null

        # Slot staging omits config.ini. Preserve the user's base config and the
        # prior slot copy, then change only the bounded capture display values.
        $lsSlotConfig=Join-Path $lsSlotDir 'config.ini'
        $lsSourceConfig=Join-Path $ctx.Root 'build/game/config.ini'
        if(!(Test-Path -LiteralPath $lsSourceConfig)) {throw "Missing user config source: $lsSourceConfig"}
        if(Test-Path -LiteralPath $lsSlotConfig) {
            Copy-Item -LiteralPath $lsSlotConfig -Destination (Join-Path $ctx.RunDir 'slot_config.before.ini') -Force
        } else {
            'slot config absent before setup' | Set-Content -LiteralPath (Join-Path $ctx.RunDir 'slot_config.before.absent.txt') -Encoding ascii
        }
        Copy-Item -LiteralPath $lsSourceConfig -Destination (Join-Path $ctx.RunDir 'config.source.ini') -Force
        $lsConfigText=[IO.File]::ReadAllText($lsSourceConfig)
        foreach($lrDisplaySetting in @(@{Name='Width';Value='1280'},@{Name='Height';Value='720'},
                                       @{Name='Fullscreen';Value='0'},@{Name='VSync';Value='1'})) {
            $lsPattern='(?m)^'+[regex]::Escape($lrDisplaySetting.Name)+'=.*$'
            if([regex]::Matches($lsConfigText,$lsPattern).Count -ne 1) {
                throw "Expected exactly one $($lrDisplaySetting.Name) in the user config."
            }
            $lsConfigText=[regex]::Replace($lsConfigText,$lsPattern,
                ($lrDisplaySetting.Name+'='+$lrDisplaySetting.Value),1)
        }
        [IO.File]::WriteAllText($lsSlotConfig,$lsConfigText,[Text.UTF8Encoding]::new($false))
        $lsUsedConfig=Join-Path $ctx.RunDir 'config.used.ini'
        Copy-Item -LiteralPath $lsSlotConfig -Destination $lsUsedConfig -Force
        [ordered]@{source_path=$lsSourceConfig;source_sha256=(Get-FileHash -LiteralPath (Join-Path $ctx.RunDir 'config.source.ini') -Algorithm SHA256).Hash;
            used_path=$lsSlotConfig;used_sha256=(Get-FileHash -LiteralPath $lsUsedConfig -Algorithm SHA256).Hash;
            display=@{Width=1280;Height=720;Fullscreen=0;VSync=1}} |
            ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $ctx.RunDir 'config-manifest.json') -Encoding ascii

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

        $lrInventory=Get-Content -LiteralPath (Join-Path $ctx.Case.SourceRoot 'progress/debug_menu/entries.json') -Raw | ConvertFrom-Json
        $laSites=@($lrInventory.entries | Where-Object {$_.function -eq 'BrnTraffic::DebugComponent::OnActivate'})
        $laVariables=@($laSites | Where-Object {$_.kind -eq 'variable'})
        $laLiteralVariables=@($laVariables | Where-Object {$_.caption})
        $laDynamicVariables=@($laVariables | Where-Object {!$_.caption})
        $laFunctions=@($laSites | Where-Object {$_.kind -eq 'function'})
        if($laSites.Count -ne 108 -or $laVariables.Count -ne 103 -or $laLiteralVariables.Count -ne 102 -or
           $laDynamicVariables.Count -ne 1 -or $laFunctions.Count -ne 5) {
            throw "Traffic identity inventory changed: sites=$($laSites.Count), variables=$($laVariables.Count), literal=$($laLiteralVariables.Count), dynamic=$($laDynamicVariables.Count), functions=$($laFunctions.Count)."
        }

        $laVariablePaths=@()
        foreach($lrEntry in $laLiteralVariables) {
            $lsRelativePath=if($lrEntry.path) {$lrEntry.path+'/'+$lrEntry.caption} else {$lrEntry.caption}
            $laVariablePaths+=@{entry=$lrEntry;relative_path=$lsRelativePath;full_path=$lsPrefix+$lsRelativePath}
        }
        if($ctx.Case.ReadoutPaths.Count -ne 15) {throw 'Expected15 explicit live readout paths.'}
        foreach($lsReadoutPath in $ctx.Case.ReadoutPaths) {
            if(@($laVariablePaths | Where-Object {$_.relative_path -ceq $lsReadoutPath}).Count -ne 1) {
                throw "Readout path is not unique in the literal inventory: $lsReadoutPath"
            }
        }

        $laActionQueries=@()
        for($liAction=0;$liAction -lt $laFunctions.Count;++$liAction) {
            $lrEntry=$laFunctions[$liAction]
            $lsRelativePath=if($lrEntry.path) {$lrEntry.path+'/'+$lrEntry.caption} else {$lrEntry.caption}
            $lsExpectedPath=$lsPrefix+$lsRelativePath
            $laActionQueries+=@{id=$lrEntry.id;caption=$lrEntry.caption;alias=('tf'+$liAction);
                lookup_path=$lsExpectedPath;expected_resolved_path=('/'+$lsExpectedPath)}
        }
        $laDerivedCallbackPaths=@($laActionQueries | ForEach-Object {$_.lookup_path.Substring(8)} | Sort-Object)
        $laExpectedCallbackPaths=@($ctx.Case.CallbackPaths | Sort-Object)
        if(($laDerivedCallbackPaths -join '|') -cne ($laExpectedCallbackPaths -join '|')) {
            throw 'Traffic action paths drifted from the five case callbacks.'
        }
        $lrMarkerAction=$laActionQueries | Where-Object {$_.lookup_path -eq 'Traffic/Picking/Pick vehicle'} | Select-Object -First 1
        if(!$lrMarkerAction) {throw 'Missing existing Pick vehicle action for non-invoking phase markers.'}
        $laPhaseMarkers=@()
        for($liMarker=0;$liMarker -lt $laGroups.Count;++$liMarker) {
            $laPhaseMarkers+=@{phase=$laGroups[$liMarker].Name;alias=('tm'+$liMarker.ToString('00'));
                expected_resolved_path=$lrMarkerAction.expected_resolved_path}
        }

        $loControlState=[ordered]@{}
        foreach($lsName in $laAllFlags) {$loControlState[$lsPrefix+$lsName]='FALSE'}
        $loControlState[$lsPrefix+'Turn traffic off']='FALSE'
        $loControlState[$lsPrefix+'Stop traffic moving']='FALSE'
        $laSnapshots=@()
        $laReadbackProbes=@()
        for($liPhase=0;$liPhase -lt $laGroups.Count;++$liPhase) {
            $lrGroup=$laGroups[$liPhase]
            $lsPhase=if($liPhase -eq 0) {'traffic-config'} else {'traffic-'+$lrGroup.Name}
            $laLines=@()
            if($liPhase -eq 0) {
                $laLines+='component "Traffic"'
                foreach($lrAction in $laActionQueries) {
                    $laLines+=('alias '+$lrAction.alias+' "'+$lrAction.lookup_path+'"')
                }
                foreach($lrMarker in $laPhaseMarkers) {
                    $laLines+=('alias '+$lrMarker.alias+' "'+$lrMarkerAction.lookup_path+'"')
                }
                foreach($lrAction in $laActionQueries) {$laLines+=('ALIAS '+$lrAction.alias)}
                foreach($lsName in $laHud) {
                    $laLines+=('set "'+$lsPrefix+$lsName+'" TRUE')
                    $loControlState[$lsPrefix+$lsName]='TRUE'
                }
            }
            foreach($lsName in $laWorldFlags) {
                $laLines+=('set "'+$lsPrefix+$lsName+'" FALSE')
                $loControlState[$lsPrefix+$lsName]='FALSE'
            }
            if($lrGroup.Name -in @('off','cleanup')) {
                foreach($lsName in $laHud) {
                    $laLines+=('set "'+$lsPrefix+$lsName+'" FALSE')
                    $loControlState[$lsPrefix+$lsName]='FALSE'
                }
            }
            $lsTurnTrafficOff=if($lrGroup.TrafficOff) {'TRUE'} else {'FALSE'}
            $lsStopTrafficMoving=if($lrGroup.Stopped) {'TRUE'} else {'FALSE'}
            $laLines+=('set "Traffic/Turn traffic off" '+$lsTurnTrafficOff)
            $laLines+=('set "Traffic/Stop traffic moving" '+$lsStopTrafficMoving)
            $loControlState[$lsPrefix+'Turn traffic off']=$lsTurnTrafficOff
            $loControlState[$lsPrefix+'Stop traffic moving']=$lsStopTrafficMoving
            foreach($lsName in $lrGroup.Flags) {
                $laLines+=('set "'+$lsPrefix+$lsName+'" TRUE')
                $loControlState[$lsPrefix+$lsName]='TRUE'
            }
            if($lrGroup.Command) {$laLines+=$lrGroup.Command}
            # Rebind the same function key after each stage; all stages share one boot.
            if($liPhase+1 -lt $laGroups.Count) {
                $laLines+=('bind F2 exec "../game_slots/'+$ctx.Slot+'/traffic-'+$laGroups[$liPhase+1].Name+'.txt"')
            }

            $lrPhaseMarker=$laPhaseMarkers[$liPhase]
            $laLines+=('ALIAS '+$lrPhaseMarker.alias)
            foreach($lrVariablePath in $laVariablePaths) {
                $lrEntry=$lrVariablePath.entry
                $laLines+=('ALIAS pv "'+$lrVariablePath.full_path+'"')
                $laLines+='ALIAS pv'
                $laLines+='pv'
                $laReadbackProbes+=@{probe_key=$lrGroup.Name+'|field|'+$lrEntry.id;phase=$lrGroup.Name;
                    role='field';id=$lrEntry.id;caption=$lrEntry.caption;lookup_path=$lrVariablePath.full_path;
                    expected_resolved_path=('/'+$lrVariablePath.full_path);is_readout=($ctx.Case.ReadoutPaths -contains $lrVariablePath.relative_path)}
            }
            $laLines+=('ALIAS '+$lrPhaseMarker.alias)
            $lsFile=Join-Path $ctx.RunDir ($lsPhase+'.txt')
            Set-Content -LiteralPath $lsFile -Encoding ascii -Value $laLines
            Copy-Item -LiteralPath $lsFile -Destination (Join-Path $lsSlotDir ($lsPhase+'.txt'))
            $loExpectedCopy=[ordered]@{}
            foreach($lrExpected in $loControlState.GetEnumerator()) {$loExpectedCopy[$lrExpected.Key]=$lrExpected.Value}
            $laSnapshots+=@{Name=$lrGroup.Name;Values=$loExpectedCopy}
        }

        $laSnapshots | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $ctx.RunDir 'expected-states.json') -Encoding ascii
        $laAliasNames=@($laActionQueries | ForEach-Object {$_.alias})+@('pv')+@($laPhaseMarkers | ForEach-Object {$_.alias})
        if($laAliasNames.Count -ne 20 -or $laAliasNames.Count -gt 40) {throw 'Traffic readback aliases exceed the original40-slot table.'}
        $loReadbackPlan=[ordered]@{schema=1;case=$ctx.Case.Name;alias_capacity=40;aliases_used=$laAliasNames;
            source_site_count=108;source_variable_count=103;literal_variable_count=102;dynamic_variable_count=1;
            action_count=5;phase_count=14;variables_per_phase=102;field_probe_count=1428;
            dynamic_variables=@($laDynamicVariables | ForEach-Object {@{id=$_.id;caption_expression=$_.caption_expression;
                path_expression=$_.path_expression;caption_resolution=$_.caption_resolution}});
            phase_markers=$laPhaseMarkers;action_alias_queries=$laActionQueries;probes=$laReadbackProbes}
        $loReadbackPlan | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $ctx.RunDir 'native-readback-plan.json') -Encoding ascii

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
        @{ Kind='Script'; Name='private-slot display config is bounded and archived'; Script={
            param($ctx)
            $lsSource=Join-Path $ctx.RunDir 'config.source.ini'
            $lsUsed=Join-Path $ctx.RunDir 'config.used.ini'
            $lsManifest=Join-Path $ctx.RunDir 'config-manifest.json'
            if(!(Test-Path $lsSource) -or !(Test-Path $lsUsed) -or !(Test-Path $lsManifest)) {
                return @{Pass=$false;Detail='missing archived source/used slot config or manifest'}
            }
            $lrManifest=Get-Content $lsManifest -Raw | ConvertFrom-Json
            $lsUsedText=[IO.File]::ReadAllText($lsUsed)
            $laExpected=@(@{Name='Width';Value='1280'},@{Name='Height';Value='720'},
                @{Name='Fullscreen';Value='0'},@{Name='VSync';Value='1'})
            $laMissing=@($laExpected | Where-Object {$lsUsedText -notmatch ('(?m)^'+[regex]::Escape($_.Name)+'='+[regex]::Escape($_.Value)+'\r?$')})
            $lbHashes=(Get-FileHash -LiteralPath $lsSource -Algorithm SHA256).Hash -eq $lrManifest.source_sha256 -and
                (Get-FileHash -LiteralPath $lsUsed -Algorithm SHA256).Hash -eq $lrManifest.used_sha256
            $lsBefore=Join-Path $ctx.RunDir 'slot_config.before.ini'
            $lsBeforeAbsent=Join-Path $ctx.RunDir 'slot_config.before.absent.txt'
            $lbBeforeArchived=(Test-Path $lsBefore) -xor (Test-Path $lsBeforeAbsent)
            return @{Pass=$lbHashes -and $laMissing.Count -eq 0 -and
                $lbBeforeArchived -and [regex]::Matches($lsUsedText,'(?m)^Width=1280\r?$').Count -eq 1 -and
                [regex]::Matches($lsUsedText,'(?m)^Height=720\r?$').Count -eq 1 -and
                [regex]::Matches($lsUsedText,'(?m)^Fullscreen=0\r?$').Count -eq 1 -and
                [regex]::Matches($lsUsedText,'(?m)^VSync=1\r?$').Count -eq 1;
                Detail="source_sha256=$($lrManifest.source_sha256) used_sha256=$($lrManifest.used_sha256) prior_slot_archived=$lbBeforeArchived missing display keys=$($laMissing.Name -join ', ')"}
        } }
        @{ Kind='Script'; Name='complete grouped Traffic console sequence'; Script={
            param($ctx)
            $lsFile=Join-Path $ctx.RunDir 'vw_deform_keys.log'
            $laLines=if(Test-Path $lsFile) {@(Get-Content $lsFile)} else {@()}
            $laNotes=@()
            foreach($lsPhase in $ctx.Case.PhaseNames) {
                $laMatches=@($laLines | Where-Object {$_ -match ('note:'+([regex]::Escape($lsPhase))+' \(log line [0-9]+\)')})
                if($laMatches.Count -ne 1) {$laNotes+=$lsPhase}
            }
            $laObserved=@($laLines | ForEach-Object {
                if($_ -match 'note:([^ ]+) \(log line [0-9]+\)') {$Matches[1]}
            } | Where-Object {$_})
            $lbOrder=($laObserved -join '|') -ceq ($ctx.Case.PhaseNames -join '|')
            $lbDone=@($laLines | Where-Object {$_ -match 'RESULT DONE$'}).Count -eq 1
            return @{Pass=$lbDone -and $laNotes.Count -eq 0 -and $lbOrder;
                Detail="phases=$($laObserved.Count)/14 ordered=$lbOrder RESULT_DONE=$lbDone; missing/duplicate $($laNotes -join ', ')"}
        } }
        @{ Kind='Script'; Name='108-site identity and native path/value readback'; Script={
            param($ctx)
            $lsPlanPath=Join-Path $ctx.RunDir 'native-readback-plan.json'
            $lsObservationPath=Join-Path $ctx.RunDir 'native-readback.json'
            $lsReadbackHelper=Join-Path $ctx.Case.SourceRoot 'tools/tests/tools/debug_menu_traffic_readback.ps1'
            if(!(Test-Path $lsPlanPath) -or !(Test-Path $lsReadbackHelper)) {
                return @{Pass=$false;Detail='missing native readback plan/helper'}
            }
            $loReadbackRun=& $lsReadbackHelper -LogPath $ctx.Log -PlanPath $lsPlanPath -OutputPath $lsObservationPath
            $loReadback=if(Test-Path $lsObservationPath) {Get-Content $lsObservationPath -Raw | ConvertFrom-Json} else {$null}
            if(!$loReadback) {return @{Pass=$false;Detail='missing native-readback.json'} }
            $lrInventory=Get-Content (Join-Path $ctx.Case.SourceRoot 'progress/debug_menu/entries.json') -Raw | ConvertFrom-Json
            $laSites=@($lrInventory.entries | Where-Object { $_.function -eq 'BrnTraffic::DebugComponent::OnActivate' })
            $laVariables=@($laSites | Where-Object { $_.kind -eq 'variable' })
            $laLiteralVariables=@($laVariables | Where-Object {$_.caption})
            $laDynamicVariables=@($laVariables | Where-Object {!$_.caption})
            $laFunctions=@($laSites | Where-Object {$_.kind -eq 'function'})
            $laMissing=@()
            $laCoverage=@()
            foreach($lrEntry in $laSites) {
                $lsExpectedPath=$null
                $lsObservedPath=$null
                $lbRegistered=$false
                if($lrEntry.kind -eq 'function') {
                    $laObservation=@($loReadback.action_aliases | Where-Object {$_.id -eq $lrEntry.id})
                    if($laObservation.Count -eq 1) {
                        $lsExpectedPath=$laObservation[0].expected_resolved_path
                        $lsObservedPath=$laObservation[0].observed_resolved_path
                        $lbRegistered=$laObservation[0].unique -and $laObservation[0].path_matches
                    }
                } elseif($lrEntry.caption) {
                    $lsRelativePath=if($lrEntry.path) {$lrEntry.path+'/'+$lrEntry.caption} else {$lrEntry.caption}
                    $lsExpectedPath='/Traffic/'+$lsRelativePath
                    $laObservation=@($loReadback.probes | Where-Object {$_.phase -eq 'hud' -and $_.role -eq 'field' -and $_.id -eq $lrEntry.id})
                    if($laObservation.Count -eq 1) {
                        $lsObservedPath=$laObservation[0].observed_resolved_path
                        $lbRegistered=$laObservation[0].path_matches -and $laObservation[0].value_present
                    }
                }
                if($lrEntry.caption -and !$lbRegistered) {$laMissing+=$lrEntry.id}
                $lsConsumerStatus=if(!$lrEntry.caption){'dynamic_caption_unresolved'}else{'not_yet_witnessed'}
                $laCoverage+=@{id=$lrEntry.id;kind=$lrEntry.kind;caption=$lrEntry.caption;expected_path=$lsExpectedPath;
                    observed_path=$lsObservedPath;native_registered=$lbRegistered;consumer_status=$lsConsumerStatus;
                    consumer_evidence=@();dynamic_caption_expression=$lrEntry.caption_expression;dynamic_path_expression=$lrEntry.path_expression}
            }
            $laFields=@($loReadback.probes | Where-Object {$_.role -eq 'field'})
            $laReadouts=@($loReadback.probes | Where-Object {$_.is_readout})
            $loPlan=Get-Content $lsPlanPath -Raw | ConvertFrom-Json
            $lbComplete=$loReadbackRun.Pass -and $loReadback.status -eq 'pass' -and $laSites.Count -eq 108 -and
                $laVariables.Count -eq 103 -and $laLiteralVariables.Count -eq 102 -and $laDynamicVariables.Count -eq 1 -and
                $laFunctions.Count -eq 5 -and $laFields.Count -eq 1428 -and $laReadouts.Count -eq 210 -and
                $laCoverage.Count -eq 108 -and @($loReadback.action_aliases).Count -eq 5 -and
                @($loReadback.phase_markers).Count -eq 14 -and @($loPlan.aliases_used).Count -eq 20
            @{source_site_count=$laSites.Count;variable_count=$laVariables.Count;literal_variable_count=$laLiteralVariables.Count;
                dynamic_variable_count=$laDynamicVariables.Count;function_count=$laFunctions.Count;literal_variable_reads=$laFields.Count;
                readout_reads=$laReadouts.Count;action_alias_queries=@($loReadback.action_aliases).Count;
                phase_marker_count=@($loReadback.phase_markers).Count;aliases_used=@($loPlan.aliases_used);
                readback_complete=$lbComplete;entries=$laCoverage;runtime_consumer_verified=0;
                note='Native path/value queries prove storage/readability only. One dynamic caption remains unresolved; consumer verification requires manual evidence.'} |
                ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $ctx.RunDir 'native-coverage.json') -Encoding ascii
            $lsProblems=if(@($loReadback.problems).Count){'; '+(@($loReadback.problems) -join ', ')}else{''}
            return @{Pass=$lbComplete -and $laMissing.Count -eq 0;
                Detail="sites=$($laSites.Count) variables=$($laVariables.Count) literal=$($laLiteralVariables.Count) dynamic=$($laDynamicVariables.Count) functions=$($laFunctions.Count) reads=$($laFields.Count)/1428 readouts=$($laReadouts.Count)/210 actions=$(@($loReadback.action_aliases).Count)/5 markers=$(@($loReadback.phase_markers).Count)/14; missing $($laMissing -join ', ')$lsProblems"}
        } }
        @{ Kind='LogMatch'; Name='actual traffic population and transforms are sampled'; Pattern='\[traffic-track\] t=.* id=\d+ pos=\(' }
        @{ Kind='Script'; Name='actual traffic controls match the grouped phase plan'; Script={
            param($ctx)
            $lsExpectedPath=Join-Path $ctx.RunDir 'expected-states.json'
            $lsObservationPath=Join-Path $ctx.RunDir 'native-readback.json'
            if(!(Test-Path $lsExpectedPath) -or !(Test-Path $lsObservationPath)) {return @{Pass=$false;Detail='missing control expectations or native observations'}}
            $laExpected=Get-Content $lsExpectedPath -Raw | ConvertFrom-Json
            $loReadback=Get-Content $lsObservationPath -Raw | ConvertFrom-Json
            $laMissing=@();$liChecked=0
            foreach($lrPhase in $laExpected) {
                foreach($lrValue in $lrPhase.Values.PSObject.Properties) {
                    ++$liChecked
                    $laActual=@($loReadback.probes | Where-Object {$_.phase -eq $lrPhase.Name -and $_.lookup_path -eq $lrValue.Name})
                    if($laActual.Count -ne 1 -or !$laActual[0].path_matches -or !$laActual[0].value_present -or
                       $laActual[0].actual_value -cne [string]$lrValue.Value) {$laMissing+=($lrPhase.Name+'/'+$lrValue.Name)}
                }
            }
            return @{Pass=$liChecked -eq 546 -and $laMissing.Count -eq 0;
                Detail="actual GetValueAsString control reads checked=$liChecked/546; mismatches $($laMissing -join ', ')"}
        } }
        @{ Kind='Script'; Name='cleanup sets the touched Traffic controls to the case off state'; Script={
            param($ctx)
            $laExpected=Get-Content (Join-Path $ctx.RunDir 'expected-states.json') -Raw | ConvertFrom-Json
            $lrCleanup=$laExpected | Where-Object {$_.Name -eq 'cleanup'} | Select-Object -First 1
            $lsObservationPath=Join-Path $ctx.RunDir 'native-readback.json'
            if(!$lrCleanup -or !(Test-Path $lsObservationPath)) {return @{Pass=$false;Detail='missing cleanup plan/readback'} }
            $loReadback=Get-Content $lsObservationPath -Raw | ConvertFrom-Json
            $laWrong=@()
            foreach($lrValue in $lrCleanup.Values.PSObject.Properties) {
                $laActual=@($loReadback.probes | Where-Object {$_.phase -eq 'cleanup' -and $_.lookup_path -eq $lrValue.Name})
                if([string]$lrValue.Value -cne 'FALSE' -or $laActual.Count -ne 1 -or
                   !$laActual[0].path_matches -or !$laActual[0].value_present -or $laActual[0].actual_value -cne 'FALSE') {
                    $laWrong+=$lrValue.Name
                }
            }
            return @{Pass=$laWrong.Count -eq 0;Detail="explicit cleanup false checks=$($lrCleanup.Values.PSObject.Properties.Count); mismatches $($laWrong -join ', ')"}
        } }
        @{ Kind='Script'; Name='retain grouped behavior captures'; Script={
            param($ctx)
            $lsFile=Join-Path $ctx.RunDir 'vw_deform_keys.log'
            if(!(Test-Path $lsFile)) { return @{Pass=$false;Detail='missing key sequence log'} }
            $laFrames=@(Get-ChildItem -LiteralPath $ctx.FrameDir -Filter '*.bmp' -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime)
            $laCopied=@()
            $laPhaseFrames=@()
            foreach($lsName in $ctx.Case.PhaseNames) {
                $lsNote=Get-Content $lsFile | Where-Object { $_ -match ('note:'+$lsName+' ') } | Select-Object -First 1
                if(!$lsNote -or $laFrames.Count -eq 0) { continue }
                $ltNote=$laFrames[0].LastWriteTime.Date+[timespan]::Parse(($lsNote -split ' ')[0],[cultureinfo]::InvariantCulture)
                if(($ltNote-$laFrames[0].LastWriteTime).TotalHours -lt -12) {$ltNote=$ltNote.AddDays(1)}
                $lrFrame=$laFrames | Where-Object { $_.LastWriteTime -le $ltNote -and ($ltNote-$_.LastWriteTime).TotalSeconds -lt 5 } | Select-Object -Last 1
                if($lrFrame) {
                    $lsDestination=Join-Path $ctx.RunDir ($lsName+'.bmp')
                    Copy-Item -LiteralPath $lrFrame.FullName -Destination $lsDestination
                    $laCopied+=$lsName
                    $laPhaseFrames+=@{phase=$lsName;frame=$lsDestination;source_frame=$lrFrame.FullName;
                        sha256=(Get-FileHash -LiteralPath $lsDestination -Algorithm SHA256).Hash}
                }
            }
            $laPhaseFrames | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $ctx.RunDir 'phase-frames.json') -Encoding ascii
            $liUniqueSourceFrames=@($laPhaseFrames | ForEach-Object {$_.source_frame} | Select-Object -Unique).Count
            return @{Pass=$laCopied.Count -eq $ctx.Case.PhaseNames.Count -and $laFrames.Count -le 96 -and
                    $liUniqueSourceFrames -eq $ctx.Case.PhaseNames.Count;
                Detail="retained=$($laCopied.Count)/14 unique_source_frames=$liUniqueSourceFrames/14 source_frames=$($laFrames.Count)/96 phases=$($laCopied -join ', '); pixels/consumers remain gated on manual review"}
        } }
        @{ Kind='Script'; Name='manual Traffic consumer and visual witness review required'; Script={
            param($ctx)
            $lsReviewPath=Join-Path $ctx.RunDir 'traffic-witness-review.json'
            $lsCoveragePath=Join-Path $ctx.RunDir 'native-coverage.json'
            $lsFramesPath=Join-Path $ctx.RunDir 'phase-frames.json'
            if(!(Test-Path $lsReviewPath) -or !(Test-Path $lsCoveragePath) -or !(Test-Path $lsFramesPath)) {
                return @{Pass=$false;Detail='UNVERIFIED: inspect every retained phase image and traffic evidence, then author traffic-witness-review.json with phase verdicts and per-site consumer dispositions. Native storage/value reads cannot pass this gate.'}
            }
            $lrReview=Get-Content $lsReviewPath -Raw | ConvertFrom-Json
            $lrCoverage=Get-Content $lsCoveragePath -Raw | ConvertFrom-Json
            $laPhaseFrames=@(Get-Content $lsFramesPath -Raw | ConvertFrom-Json)
            $laPhaseMissing=@();$laEntryMissing=@();$liVerified=0
            if($lrReview.case -ne $ctx.Case.Name -or $lrReview.run_dir -ne $ctx.RunDir) {
                return @{Pass=$false;Detail='review packet is not bound to this exact case/run directory'}
            }
            foreach($lsPhase in $ctx.Case.PhaseNames) {
                $laFrame=@($laPhaseFrames | Where-Object {$_.phase -eq $lsPhase})
                $laVerdict=@($lrReview.phases | Where-Object {$_.phase -eq $lsPhase -and $_.verdict -eq 'pass' -and $_.evidence})
                $lbFrameValid=$laFrame.Count -eq 1 -and (Test-Path -LiteralPath $laFrame[0].frame) -and
                    (Get-FileHash -LiteralPath $laFrame[0].frame -Algorithm SHA256).Hash -eq $laFrame[0].sha256
                if($laFrame.Count -ne 1 -or $laVerdict.Count -ne 1 -or
                   !$lbFrameValid -or
                   $laVerdict[0].frame -ne $laFrame[0].frame -or $laVerdict[0].frame_sha256 -ne $laFrame[0].sha256) {$laPhaseMissing+=$lsPhase}
            }
            foreach($lrEntry in $lrCoverage.entries) {
                $laDisposition=@($lrReview.entries | Where-Object {$_.id -eq $lrEntry.id})
                if($laDisposition.Count -ne 1 -or !$laDisposition[0].consumer_status -or !$laDisposition[0].evidence) {
                    $laEntryMissing+=$lrEntry.id;continue
                }
                $lsStatus=[string]$laDisposition[0].consumer_status
                if($lrEntry.dynamic_caption_expression -and $lsStatus -ne 'dynamic_caption_unresolved') {
                    $laEntryMissing+=$lrEntry.id;continue
                }
                if($lsStatus -notin @('verified','unclassified','not_yet_witnessed','dynamic_caption_unresolved')) {
                    $laEntryMissing+=$lrEntry.id;continue
                }
                $lrEntry.consumer_status=$lsStatus
                $lrEntry.consumer_evidence=[string]$laDisposition[0].evidence
                if($lsStatus -eq 'verified') {++$liVerified}
            }
            $laExtra=@($lrReview.entries | Where-Object {$_.id -notin @($lrCoverage.entries | ForEach-Object {$_.id})})
            $lrCoverage.runtime_consumer_verified=$liVerified
            $lrCoverage | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $lsCoveragePath -Encoding ascii
            return @{Pass=$lrReview.verdict -eq 'pass' -and $laPhaseMissing.Count -eq 0 -and
                    $laEntryMissing.Count -eq 0 -and $laExtra.Count -eq 0;
                Detail="review_verdict=$($lrReview.verdict); manual phase verdicts=$($ctx.Case.PhaseNames.Count-$laPhaseMissing.Count)/14; site dispositions=$(108-$laEntryMissing.Count-$laExtra.Count)/108; manually evidenced consumers=$liVerified; missing phases=$($laPhaseMissing -join ', ') sites=$($laEntryMissing -join ', ') extra=$($laExtra.Count)"}
        } }
    )
}
