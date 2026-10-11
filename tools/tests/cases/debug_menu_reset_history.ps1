# Observe the original reset axis, vertical line test and intersection spheres
# after a real place-on-track request in free roam. Profile writes stay in a
# private slot. Existing debug-console commands control the overlay.
@{
    Name = 'debug_menu_reset_history'
    Area = 'debug-menu'
    Bug = 'Show place on track info must render the latest real reset history.'
    Frames = $true
    ProfileFixture = 'DISCO_collect_base.sav'
    Run = @{
        Drive = $true
        DriveDelay = 3.0
        DriveSeconds = 1.0
        Teleport = '3040.7,-5.8,-1937.9,180'
        SkipIntro = $true
        AcceptGap = 1.0
        FrameEvery = 360
        MinFreeGB = 24
        MaxSeconds = 80
    }
    DiagEnv = 'BRN_DEBUG_UI_TRACE=1,BRN_RESET_HISTORY_TRACE=1,BRN_FRAME_DUMP_MAX=32'
    Setup = {
        param($ctx)
        $lsRelative = '../../' + $ctx.RunDir.Substring(([string]$ctx.Root).TrimEnd('\').Length + 1).Replace('\','/')
        $lsControl = '"Race Car Entity/Show place on track info"'
        $laOn = @('component "Race Car Entity"', ('set '+$lsControl+' TRUE'),
            ('save "'+$lsRelative+'/on.txt"'),
            ('bind F2 exec "'+$lsRelative+'/hide.txt"'),
            ('bind F3 exec "'+$lsRelative+'/show.txt"'))
        Set-Content -LiteralPath (Join-Path $ctx.RunDir 'activate.txt') -Value $laOn -Encoding ascii
        Set-Content -LiteralPath (Join-Path $ctx.RunDir 'hide.txt') -Value @(
            ('set '+$lsControl+' FALSE'), ('save "'+$lsRelative+'/off.txt"')) -Encoding ascii
        Set-Content -LiteralPath (Join-Path $ctx.RunDir 'show.txt') -Value @(
            ('set '+$lsControl+' TRUE'), ('save "'+$lsRelative+'/restored.txt"')) -Encoding ascii
        $laSteps = @('wait:CarSelectManager: Exit state is finished', 'sleep:5', 'key:192',
            ('cmd:exec "'+$lsRelative+'/activate.txt"'), 'sleep:5', 'note:shown',
            'key:113', 'sleep:5', 'note:hidden',
            'key:114', 'sleep:5', 'note:restored', 'key:192', 'sleep:3', 'note:closed')
        $lsSteps = Join-Path $ctx.RunDir 'debug-menu-steps.txt'
        Set-Content -LiteralPath $lsSteps -Value $laSteps -Encoding ascii
        $lsHelper = Join-Path $ctx.Root 'tools/tests/tools/VW_DEFORM_debugkeys.ps1'
        $laArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$lsHelper`"",
            '-GameLog',"`"$($ctx.GameLog)`"",'-OutDir',"`"$($ctx.RunDir)`"",'-Slot',"$($ctx.Slot)",
            '-StepsFile',"`"$lsSteps`"",'-TimeoutSec','75')
        return Start-Process powershell -ArgumentList $laArgs -PassThru -WindowStyle Hidden
    }
    Checks = @(
        @{ Kind='NewAsserts'; Name='no new assert families' }
        @{ Kind='LogCount'; Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }
        @{ Kind='Script'; Name='real console and F-key sequence completes'; Script={
            param($ctx)
            $lsFile = Join-Path $ctx.RunDir 'vw_deform_keys.log'
            $lsText = if (Test-Path $lsFile) { Get-Content $lsFile -Raw } else { '' }
            return @{ Pass=($lsText -match 'RESULT DONE'); Detail=($lsText -split "`r?`n" | Where-Object { $_ -match 'note:|RESULT' }) -join ' | ' }
        } }
        @{ Kind='Script'; Name='original control is writable and can be hidden/restored'; Script={
            param($ctx)
            $laMissing = @()
            foreach ($lsFile in @('on.txt','off.txt','restored.txt')) {
                $lsPath = Join-Path $ctx.RunDir $lsFile
                $lsValue = if ($lsFile -eq 'off.txt') { 'FALSE' } else { 'TRUE' }
                $lsText = if (Test-Path $lsPath) { Get-Content $lsPath -Raw } else { '' }
                if ($lsText -notmatch ('(?m)^SET "/Race Car Entity/Show place on track info" "'+$lsValue+'"')) { $laMissing += $lsFile }
            }
            return @{ Pass=($laMissing.Count -eq 0); Detail='missing correct saved states: '+($laMissing -join ', ') }
        } }
        @{ Kind='Script'; Name='renderer receives real line, intersections and reset transform'; Script={
            param($ctx)
            $laShown = @($ctx.LogLines | Where-Object { $_ -match '\[reset-history\] shown count=([1-9]\d*) .*lineStart=\([^,]+,([^,]+),[^)]+\) lineEnd=\([^,]+,([^,]+),[^)]+\)' } | ForEach-Object {
                [math]::Abs([double]::Parse($Matches[2],[cultureinfo]::InvariantCulture)-[double]::Parse($Matches[3],[cultureinfo]::InvariantCulture))
            })
            $liHidden = @($ctx.LogLines | Where-Object { $_ -match '\[reset-history\] hidden' }).Count
            return @{ Pass=(@($laShown | Where-Object { [math]::Abs($_-100) -lt 0.01 }).Count -ge 2 -and $liHidden -ge 1); Detail="valid line-height samples=$($laShown -join ',') hide transitions=$liHidden" }
        } }
        @{ Kind='LogCount'; Name='recovered geometry reaches the renderer dispatch';
            Pattern='\[debug3d-bank\] dispatch draws=2 vertices=200'; Min=1 }
        @{ Kind='Script'; Name='retain shown and hidden frames for visual review'; Script={
            param($ctx)
            $lsHelper = Join-Path $ctx.RunDir 'vw_deform_keys.log'
            if (!(Test-Path $lsHelper)) { return @{ Pass=$false; Detail='missing key log' } }
            $laFrames = @(Get-ChildItem -LiteralPath $ctx.FrameDir -Filter '*.bmp' | Sort-Object LastWriteTime)
            $laCopied = @()
            foreach ($lsName in @('shown','hidden','restored')) {
                $lsNote = Get-Content $lsHelper | Where-Object { $_ -match ('note:'+$lsName+' ') } | Select-Object -First 1
                if (!$lsNote -or $laFrames.Count -eq 0) { continue }
                $ltNote = $laFrames[0].LastWriteTime.Date + [timespan]::Parse(($lsNote -split ' ')[0],[cultureinfo]::InvariantCulture)
                $lrFrame = $laFrames | Where-Object { $_.LastWriteTime -le $ltNote -and ($ltNote-$_.LastWriteTime).TotalSeconds -lt 5 } | Select-Object -Last 1
                if ($lrFrame) { Copy-Item -LiteralPath $lrFrame.FullName -Destination (Join-Path $ctx.RunDir ($lsName+'.bmp')); $laCopied += $lsName }
            }
            return @{ Pass=($laCopied.Count -eq 3); Detail='retained '+($laCopied -join ', ')+'; inspect pixels before claiming visual parity' }
        } }
        @{ Kind='Script'; Name='shown and restored frames contain visible wire geometry'; Script={
            param($ctx)
            Add-Type -AssemblyName System.Drawing
            $laCounts=@()
            $lfAreaScale=1.0
            foreach ($lsName in @('shown','hidden','restored')) {
                $lsFile=Join-Path $ctx.RunDir ($lsName+'.bmp')
                if (!(Test-Path -LiteralPath $lsFile)) { return @{ Pass=$false; Detail='missing '+$lsName+' frame' } }
                $lrBitmap=[Drawing.Bitmap]::FromFile($lsFile)
                try {
                    # This fixture's lower scene, excluding the console and bottom FPS text.
                    # Post-fx tints white wires, so allow their measured RGB spread.
                    $liCount=0
                    $lfAreaScale=($lrBitmap.Width*$lrBitmap.Height)/(1280.0*720.0)
                    for ($liY=[int]($lrBitmap.Height*31/72); $liY -lt [int]($lrBitmap.Height*8/9); ++$liY) {
                        for ($liX=[int]($lrBitmap.Width*5/16); $liX -lt $lrBitmap.Width; ++$liX) {
                            $lrPixel=$lrBitmap.GetPixel($liX,$liY)
                            $liMin=[math]::Min($lrPixel.R,[math]::Min($lrPixel.G,$lrPixel.B))
                            $liMax=[math]::Max($lrPixel.R,[math]::Max($lrPixel.G,$lrPixel.B))
                            if ($liMin -ge 200 -and $liMax-$liMin -le 45) { ++$liCount }
                        }
                    }
                    $laCounts += $liCount
                } finally { $lrBitmap.Dispose() }
            }
            $liMargin=[int](3000*$lfAreaScale)
            return @{ Pass=($laCounts[0] -gt $laCounts[1]+$liMargin -and $laCounts[2] -gt $laCounts[1]+$liMargin);
                Detail="bright scene pixels shown/hidden/restored=$($laCounts -join '/') required excess=$liMargin; fixture-specific visibility witness" }
        } }
    )
}
