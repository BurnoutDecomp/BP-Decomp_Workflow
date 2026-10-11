# Prepared only: one42-entry native witness on private slot15. Slot16 belongs to
# the parallel Traffic108 case. Loading/running this case is reserved for root.
if ($Slot -ne 15) { throw 'debug_menu_physical_route_batch requires private -Slot 15.' }

$loPhysicalDefaults = [ordered]@{
    'Draw catchup targets'='FALSE'; 'Draw simple traffic'='FALSE'
    'Draw physical traffic'='FALSE'; 'Draw joints'='FALSE'; 'Draw box-triangle tests'='FALSE'
    'Allow breaking joints'='FALSE'; 'Max joint swing angle'='30'; 'Max joint swing velocity'='10'
    'Max joint twist angle'='15'; 'Max joint twist velocity'='10'
    'Joint swing break velocity'='2'; 'Joint twist break velocity'='2'; 'Joint linear break speed'='10'
    'Draw traffic air rams'='FALSE'; 'Air ram rendering scale'='5'
    'Draw driver controls'='FALSE'; 'Allow traffic freezing'='TRUE'
}
$loRouteDefaults = [ordered]@{
    'Draw AI section map'='FALSE'; 'High detail map'='FALSE'; 'Map colour mode'='Plain'
    'Draw cars in map'='FALSE'; 'Draw master route in map'='FALSE'; 'Draw car routes in map'='FALSE'
    'Draw car info in map'='FALSE'; 'Draw A* in map'='FALSE'; 'Draw event block sections'='FALSE'
    'Draw dead ends in map'='FALSE'; 'Only draw one car'='FALSE'; 'Car Index'='0'
    'Map scale'='0.1'; 'Map offset X'='580'; 'Map offset Y'='450'
    'Draw Portals'='FALSE'; 'Draw Portal IDs'='FALSE'; 'Draw Portal Geometry'='FALSE'
    'Draw HNG as planes'='FALSE'; 'Player section data only'='FALSE'; 'Show AI section info'='FALSE'
    'Section Index'='0'
}
$laPhases = @(
    @{Name='baseline'; Physical=@{}; Route=@{}}
    @{Name='physical-simple'; Physical=@{'Draw simple traffic'='TRUE';'Draw catchup targets'='TRUE'}; Route=@{}}
    @{Name='physical-full'; Physical=@{'Draw simple traffic'='FALSE';'Draw catchup targets'='FALSE';
        'Draw physical traffic'='TRUE';'Draw joints'='TRUE';'Draw driver controls'='TRUE'}; Route=@{}}
    @{Name='physical-box'; Physical=@{'Draw physical traffic'='FALSE';'Draw joints'='FALSE';
        'Draw driver controls'='FALSE';'Draw box-triangle tests'='TRUE'}; Route=@{}}
    @{Name='physical-air'; Physical=@{'Draw box-triangle tests'='FALSE';'Draw traffic air rams'='TRUE';
        'Air ram rendering scale'='10'}; Route=@{}}
    @{Name='physical-tune'; Physical=@{'Draw physical traffic'='TRUE';'Draw joints'='TRUE';
        'Draw driver controls'='TRUE';'Air ram rendering scale'='2.5';'Allow breaking joints'='TRUE';
        'Max joint swing angle'='45';'Max joint swing velocity'='20';'Max joint twist angle'='30';
        'Max joint twist velocity'='25';'Joint swing break velocity'='3';'Joint twist break velocity'='3.5';
        'Joint linear break speed'='15';'Allow traffic freezing'='FALSE'}; Route=@{}}
    @{Name='route-plain'; RestorePhysical=$true; Physical=@{}; Route=@{'Draw AI section map'='TRUE'}}
    @{Name='route-type'; Physical=@{}; Route=@{'High detail map'='TRUE';'Map colour mode'='Type';
        'Draw cars in map'='TRUE';'Draw master route in map'='TRUE';'Draw car routes in map'='TRUE';
        'Draw car info in map'='TRUE'}}
    @{Name='route-speed'; Physical=@{}; Route=@{'Map colour mode'='Speed';'Map scale'='0.2';
        'Map offset X'='600';'Map offset Y'='470';'Draw A* in map'='TRUE';
        'Draw event block sections'='TRUE';'Draw dead ends in map'='TRUE';
        'Only draw one car'='TRUE';'Car Index'='1'}}
    @{Name='route-world-filtered'; Physical=@{}; Route=@{'Draw AI section map'='TRUE';'Map scale'='0.05';
        'Draw cars in map'='FALSE';'Draw master route in map'='FALSE';'Draw A* in map'='FALSE';
        'Draw event block sections'='FALSE';'Draw dead ends in map'='FALSE';'Draw Portals'='TRUE';
        'Draw Portal IDs'='TRUE';'Draw Portal Geometry'='TRUE';'Draw HNG as planes'='TRUE';
        'Player section data only'='TRUE';'Show AI section info'='TRUE';'Section Index'='1'}}
    @{Name='route-world-all'; Physical=@{}; Route=@{'Player section data only'='FALSE'}}
    @{Name='physical-reset'; RestorePhysical=$true; RestoreRoute=$true; Physical=@{}; Route=@{}}
    @{Name='cleanup'; RestorePhysical=$true; RestoreRoute=$true; Physical=@{}; Route=@{}}
)

@{
    Name='debug_menu_physical_route_batch'
    SourceRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
    RequiredSlot=15
    Area='debug-menu'
    Bug='The18 Physical traffic and24 Route Map registrations must reach native storage; submitted overlays require separate frame review.'
    Frames=$true
    ProfileFixture='rival_hunt_profile.sav'
    PhysicalDefaults=$loPhysicalDefaults
    RouteDefaults=$loRouteDefaults
    Phases=$laPhases
    Run=@{SkipIntro=$true;AcceptGap=1.0;SkipTrainingTip=$true;MaxSeconds=150;MinFreeGB=20;
        Drive=$true;DriveDelay=27.0;DriveSeconds=15.0;MotionProbe=$true;
        Teleport='3040.7,-5.8,-1937.9,180';StartEvent=$true;EventFsm=$true;FrameEvery=360}
    DiagEnv='BRN_DEBUG_UI_TRACE=1,BRN_IM2D_TRACE=1,BRN_TRAFFIC_DIAG=1,BRN_FRAME_DUMP_ARM=0,BRN_FRAME_DUMP_MAX=96'
    Setup={
        param($ctx)
        if($ctx.Slot -ne 15) { throw 'Private physical/route witness must use slot15.' }
        $lsSlotDir=Join-Path $ctx.Root 'build/game_slots/15'
        New-Item -ItemType Directory -Force $lsSlotDir | Out-Null
        $lsRelative='../../'+$ctx.RunDir.Substring(([string]$ctx.Root).TrimEnd('\').Length+1).Replace('\','/')
        $lsPhysical='Physical traffic/'
        $lsRoute='AI/Route Map/' # ARTIST vtable820CDFC4 slot4 ->82767678 ->"AI"
        $loState=[ordered]@{}
        foreach($lrItem in $ctx.Case.PhysicalDefaults.GetEnumerator()) {$loState[$lsPhysical+$lrItem.Key]=$lrItem.Value}
        foreach($lrItem in $ctx.Case.RouteDefaults.GetEnumerator()) {$loState[$lsRoute+$lrItem.Key]=$lrItem.Value}
        if($loState.Count -ne 39 -or $ctx.Case.Phases.Count -ne 13) {throw 'Expected39 native variables and13 grouped phases.'}

        $laSnapshots=@()
        for($liPhase=0;$liPhase -lt $ctx.Case.Phases.Count;++$liPhase) {
            $lrPhase=$ctx.Case.Phases[$liPhase]
            $laLines=@()
            if($liPhase -eq 0) {
                $laLines+=@('component "Physical traffic"','component "AI/Route Map"',
                    'alias prreset "Physical traffic/Reset traffic on water"',
                    'alias prplus "AI/Route Map/+100 Sections"','alias prminus "AI/Route Map/-100 Sections"',
                    ('save "'+$lsRelative+'/registered.txt"'))
                foreach($lrItem in $loState.GetEnumerator()) {$laLines+=('set "'+$lrItem.Key+'" '+$lrItem.Value)}
                for($liBinding=1;$liBinding -lt $ctx.Case.Phases.Count;++$liBinding) {
                    $laLines+=('bind F'+$liBinding+' exec "../game_slots/15/pr-'+$ctx.Case.Phases[$liBinding].Name+'.txt"')
                }
            }
            if($lrPhase.RestorePhysical) {
                foreach($lrItem in $ctx.Case.PhysicalDefaults.GetEnumerator()) {
                    $loState[$lsPhysical+$lrItem.Key]=$lrItem.Value
                    $laLines+=('set "'+$lsPhysical+$lrItem.Key+'" '+$lrItem.Value)
                }
            }
            if($lrPhase.RestoreRoute) {
                foreach($lrItem in $ctx.Case.RouteDefaults.GetEnumerator()) {
                    $loState[$lsRoute+$lrItem.Key]=$lrItem.Value
                    $laLines+=('set "'+$lsRoute+$lrItem.Key+'" '+$lrItem.Value)
                }
            }
            foreach($lrItem in $lrPhase.Physical.GetEnumerator()) {
                $loState[$lsPhysical+$lrItem.Key]=$lrItem.Value
                $laLines+=('set "'+$lsPhysical+$lrItem.Key+'" '+$lrItem.Value)
            }
            foreach($lrItem in $lrPhase.Route.GetEnumerator()) {
                $loState[$lsRoute+$lrItem.Key]=$lrItem.Value
                $laLines+=('set "'+$lsRoute+$lrItem.Key+'" '+$lrItem.Value)
            }
            if($lrPhase.Name -eq 'route-world-all') {
                $laLines+=@('call prplus',('save "'+$lsRelative+'/route-plus-saved.txt"'),
                    'call prminus',('save "'+$lsRelative+'/route-minus-saved.txt"'))
            }
            if($lrPhase.Name -eq 'physical-reset') {$laLines+='call prreset'}
            $laLines+=('save "'+$lsRelative+'/'+$lrPhase.Name+'-saved.txt"')
            $lsFile=Join-Path $ctx.RunDir ('pr-'+$lrPhase.Name+'.txt')
            Set-Content -LiteralPath $lsFile -Value $laLines -Encoding ascii
            Copy-Item -LiteralPath $lsFile -Destination (Join-Path $lsSlotDir ([IO.Path]::GetFileName($lsFile)))
            $loCopy=[ordered]@{}
            foreach($lrItem in $loState.GetEnumerator()) {$loCopy[$lrItem.Key]=$lrItem.Value}
            $laSnapshots+=@{Name=$lrPhase.Name;File=$lrPhase.Name+'-saved.txt';Values=$loCopy}
        }
        $laSnapshots | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $ctx.RunDir 'expected-states.json') -Encoding ascii
        $laSteps=@('wait:CarSelectManager: Exit state is finished','key:192',
            'cmd:exec "../game_slots/15/pr-baseline.txt"','key:192','sleep:6','note:baseline')
        for($liPhase=1;$liPhase -lt $ctx.Case.Phases.Count;++$liPhase) {
            $laSteps+=@(('key:'+(111+$liPhase)),'sleep:6',('note:'+$ctx.Case.Phases[$liPhase].Name))
        }
        $lsSteps=Join-Path $ctx.RunDir 'debug-menu-steps.txt'
        Set-Content -LiteralPath $lsSteps -Value $laSteps -Encoding ascii
        $lsHelper=Join-Path $ctx.Root 'tools/tests/tools/VW_DEFORM_debugkeys.ps1'
        $laArgs=@('-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$lsHelper`"",'-GameLog',"`"$($ctx.GameLog)`"",
            '-OutDir',"`"$($ctx.RunDir)`"",'-Slot','15','-StepsFile',"`"$lsSteps`"",'-TimeoutSec','145')
        return Start-Process powershell -ArgumentList $laArgs -PassThru -WindowStyle Hidden
    }
    Checks=@(
        @{Kind='NewAsserts';Name='no new assert families'}
        @{Kind='LogCount';Name='no exceptions';Pattern='\[EXCEPTION\]';Max=0}
        @{Kind='Mark';Name='driving scene prerequisite';Phase='DRIVING'}
        @{Kind='Script';Name='private slot and complete grouped console sequence';Script={
            param($ctx)
            $lsFile=Join-Path $ctx.RunDir 'vw_deform_keys.log'
            $lsText=if(Test-Path $lsFile){Get-Content $lsFile -Raw}else{''}
            $laMissing=@($ctx.Case.Phases | Where-Object {$lsText -notmatch ('note:'+[regex]::Escape($_.Name)+' ')})
            return @{Pass=$ctx.Case.RequiredSlot -eq 15 -and $lsText -match 'RESULT DONE' -and $laMissing.Count -eq 0;
                Detail='13 grouped phases; missing '+(($laMissing | ForEach-Object {$_.Name}) -join ', ')}
        }}
        @{Kind='Script';Name='all42 original entries exist in the native registry';Script={
            param($ctx)
            $lsFile=Join-Path $ctx.RunDir 'registered.txt'
            $lsText=if(Test-Path $lsFile){Get-Content $lsFile -Raw}else{''}
            $lrInventory=Get-Content (Join-Path $ctx.Case.SourceRoot 'progress/debug_menu/entries.json') -Raw | ConvertFrom-Json
            $laEntries=@($lrInventory.entries | Where-Object {$_.function -in @(
                'BrnPhysics::Vehicle::PhysicalTrafficManagerDebugComponent::OnActivate','BrnAI::RouteMapDebugComponent::OnActivate')})
            $loAliases=@{'Reset traffic on water'='prreset';'+100 Sections'='prplus';'-100 Sections'='prminus'}
            $laMissing=@();$laCoverage=@()
            foreach($lrEntry in $laEntries) {
                $lsPrefix=if($lrEntry.function -like 'BrnAI::*'){'/AI/Route Map/'}else{'/Physical traffic/'}
                $lsPath=$lsPrefix+$lrEntry.caption
                $lsPattern=if($lrEntry.kind -eq 'function'){
                    '(?m)^ALIAS '+$loAliases[$lrEntry.caption]+' "'+[regex]::Escape($lsPath)+'"'
                }else{'(?m)^SET "'+[regex]::Escape($lsPath)+'" '}
                $lbRegistered=$lsText -match $lsPattern
                if(!$lbRegistered){$laMissing+=$lrEntry.id}
                $lsConsumer=if($lrEntry.caption -in @('Allow breaking joints','Joint swing break velocity',
                    'Joint twist break velocity','Joint linear break speed')){'unclassified_x360_reader'}else{'not_yet_witnessed'}
                $laCoverage+=@{id=$lrEntry.id;caption=$lrEntry.caption;kind=$lrEntry.kind;path=$lsPath;
                    native_registered=$lbRegistered;consumer_status=$lsConsumer;consumer_evidence=@()}
            }
            @{source_entries=$laEntries.Count;native_registered=($laCoverage | Where-Object {$_.native_registered}).Count;
                variable_entries=39;callback_entries=3;entries=$laCoverage;runtime_consumer_verified=0;
                note='Native registration is not a consumer or visual verdict.'} | ConvertTo-Json -Depth 7 |
                Set-Content -LiteralPath (Join-Path $ctx.RunDir 'native-coverage.json') -Encoding ascii
            $liPhysical=@($laEntries | Where-Object {$_.function -like 'BrnPhysics::*'}).Count
            $liRoute=@($laEntries | Where-Object {$_.function -like 'BrnAI::*'}).Count
            return @{Pass=$liPhysical -eq 18 -and $liRoute -eq 24 -and $laMissing.Count -eq 0;
                Detail="source=$liPhysical+$liRoute native variables39 + callback aliases3; missing "+($laMissing -join ', ')}
        }}
        @{Kind='Script';Name='native cell edits and source-default restoration';Script={
            param($ctx)
            $lsExpected=Join-Path $ctx.RunDir 'expected-states.json'
            if(!(Test-Path $lsExpected)){return @{Pass=$false;Detail='missing expected snapshot plan'}}
            $laMissing=@();$liChecked=0
            foreach($lrSnapshot in @(Get-Content $lsExpected -Raw | ConvertFrom-Json)) {
                $lsFile=Join-Path $ctx.RunDir $lrSnapshot.File
                $lsText=if(Test-Path $lsFile){Get-Content $lsFile -Raw}else{''}
                foreach($lrValue in $lrSnapshot.Values.PSObject.Properties) {
                    ++$liChecked
                    $lrMatch=[regex]::Match($lsText,'(?im)^SET "/'+[regex]::Escape($lrValue.Name)+'" "([^"]*)"')
                    $lbMatch=$lrMatch.Success
                    if($lbMatch -and $lrValue.Value -in @('TRUE','FALSE')) {$lbMatch=$lrMatch.Groups[1].Value -eq $lrValue.Value}
                    elseif($lbMatch -and $lrValue.Name -eq 'AI/Route Map/Map colour mode') {
                        $lbMatch=$lrMatch.Groups[1].Value -ceq [string]$lrValue.Value
                    }
                    elseif($lbMatch) {
                        $ldActual=0.0;$ldExpected=[double]::Parse([string]$lrValue.Value,[cultureinfo]::InvariantCulture)
                        $lbMatch=[double]::TryParse($lrMatch.Groups[1].Value,[Globalization.NumberStyles]::Float,
                            [cultureinfo]::InvariantCulture,[ref]$ldActual) -and [math]::Abs($ldActual-$ldExpected) -lt 0.00001
                    }
                    if(!$lbMatch){$laMissing+=($lrSnapshot.Name+'/'+$lrValue.Name)}
                }
            }
            return @{Pass=$liChecked -eq 507 -and $laMissing.Count -eq 0;
                Detail="$liChecked native field reads across13 stages including cleanup; mismatches "+($laMissing -join ', ')}
        }}
        @{Kind='Script';Name='original route callbacks change the native section index';Script={
            param($ctx)
            $laMissing=@()
            foreach($lrExpected in @(@{File='route-plus-saved.txt';Value=101},@{File='route-minus-saved.txt';Value=1})) {
                $lsFile=Join-Path $ctx.RunDir $lrExpected.File
                $lsText=if(Test-Path $lsFile){Get-Content $lsFile -Raw}else{''}
                if($lsText -notmatch ('(?m)^SET "/AI/Route Map/Section Index" "'+$lrExpected.Value+'"')) {$laMissing+=$lrExpected.File}
            }
            return @{Pass=$laMissing.Count -eq 0;Detail='source callbacks +100 then-100:1 ->101 ->1; missing '+($laMissing -join ', ')}
        }}
        @{Kind='Script';Name='bounded phase frames retained by reference';Script={
            param($ctx)
            $lsLog=Join-Path $ctx.RunDir 'vw_deform_keys.log'
            $laLines=if(Test-Path $lsLog){@(Get-Content $lsLog)}else{@()}
            $laFrames=@(Get-ChildItem -LiteralPath $ctx.FrameDir -Filter '*.bmp' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime)
            $laManifest=@();$laMissing=@()
            foreach($lrPhase in $ctx.Case.Phases) {
                $lsNote=$laLines | Where-Object {$_ -match ('note:'+[regex]::Escape($lrPhase.Name)+' ')} | Select-Object -First 1
                if(!$lsNote -or $laFrames.Count -eq 0){$laMissing+=$lrPhase.Name;continue}
                $ltNote=$laFrames[0].LastWriteTime.Date+[timespan]::Parse(($lsNote -split ' ')[0],[cultureinfo]::InvariantCulture)
                if(($ltNote-$laFrames[0].LastWriteTime).TotalHours -lt -12){$ltNote=$ltNote.AddDays(1)}
                $lrFrame=$laFrames | Where-Object {$_.LastWriteTime -le $ltNote -and ($ltNote-$_.LastWriteTime).TotalSeconds -lt 5} | Select-Object -Last 1
                if(!$lrFrame){$laMissing+=$lrPhase.Name;continue}
                $laManifest+=@{phase=$lrPhase.Name;frame=$lrFrame.FullName;bytes=$lrFrame.Length;
                    sha256=(Get-FileHash -LiteralPath $lrFrame.FullName -Algorithm SHA256).Hash;
                    note_time=$ltNote.ToString('o');age_seconds=($ltNote-$lrFrame.LastWriteTime).TotalSeconds}
            }
            $laManifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $ctx.RunDir 'phase-frames.json') -Encoding ascii
            return @{Pass=$laFrames.Count -le 96 -and $laManifest.Count -eq 13 -and $laMissing.Count -eq 0;
                Detail="native frames=$($laFrames.Count) cap96; phase frames=$($laManifest.Count)/13; missing "+($laMissing -join ', ')+'; references only, no bitmap copies'}
        }}
        @{Kind='Script';Name='native overlay pixels reviewed; consumer coverage counted separately';Script={
            param($ctx)
            $lsReview=Join-Path $ctx.RunDir 'witness-review.json'
            if(!(Test-Path $lsReview)) {return @{Pass=$false;Detail='UNVERIFIED: inspect phase-frames.json and actual pixels, then write witness-review.json using the prepared schema. Registry/boot alone cannot pass this check.'}}
            $lrReview=Get-Content $lsReview -Raw | ConvertFrom-Json
            $laRequired=@('baseline','physical-simple','physical-full','physical-box','route-plain','route-type',
                'route-speed','route-world-filtered','route-world-all','cleanup')
            $lsFrames=Join-Path $ctx.RunDir 'phase-frames.json'
            $laFrames=if(Test-Path $lsFrames){@(Get-Content $lsFrames -Raw | ConvertFrom-Json)}else{@()}
            $laMissing=@($laRequired | Where-Object {
                $lsPhase=$_
                $lrFrame=$laFrames | Where-Object {$_.phase -eq $lsPhase} | Select-Object -First 1
                @($lrReview.phases | Where-Object {$_.phase -eq $lsPhase -and $_.verdict -eq 'pass' -and $_.evidence
                    -and $lrFrame -and $_.frame -eq $lrFrame.frame -and $_.frame_sha256 -eq $lrFrame.sha256}).Count -ne 1
            })
            $lbBound=$lrReview.case -eq $ctx.Case.Name -and $lrReview.run_dir -eq $ctx.RunDir
            $liConsumers=0
            $lsCoverage=Join-Path $ctx.RunDir 'native-coverage.json'
            if($lbBound -and (Test-Path $lsCoverage)) {
                $lrCoverage=Get-Content $lsCoverage -Raw | ConvertFrom-Json
                foreach($lrEntry in $lrCoverage.entries) {
                    $laReviews=@($lrReview.entries | Where-Object {$_.id -eq $lrEntry.id -and $_.consumer_status -eq 'verified' -and $_.consumer_evidence})
                    if($laReviews.Count -eq 1 -and $lrEntry.consumer_status -ne 'unclassified_x360_reader') {
                        ++$liConsumers
                        $lrEntry.consumer_status='verified'
                        $lrEntry.consumer_evidence=$laReviews[0].consumer_evidence
                    }
                }
                $lrCoverage.runtime_consumer_verified=$liConsumers
                $lrCoverage | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $lsCoverage -Encoding ascii
            }
            return @{Pass=$lbBound -and $lrReview.verdict -eq 'pass' -and $laMissing.Count -eq 0;
                Detail="reviewed core overlays; unique manually witnessed consumers=$liConsumers/42; conditional airram/joint creation/reset and unclassified break cells remain separately reported; missing "+($laMissing -join ', ')}
        }}
    )
}
