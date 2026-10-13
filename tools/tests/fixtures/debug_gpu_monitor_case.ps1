param([bool]$AsGraph = $false, [bool]$Visible = $true)

$lCase = & (Join-Path $PSScriptRoot '../cases/baseline_boot_drive.ps1')
$lMode = if (-not $Visible) { 'hidden' } elseif ($AsGraph) { 'graph' } else { 'table' }
$lCase.Name = "debug_gpu_monitors_$lMode"
$lCase.Area = 'debug-menu'
$lCase.Bug = 'GPU switches had no registered or measured render passes'
$lCase.GpuGraph = $AsGraph
$lCase.GpuVisible = $Visible
$lCase.Run.MaxSeconds = 100
$lCase.Run.FrameEvery = 360
# The native writer caps this capture at 24 frames, even if rendering is uncapped.
$lCase.Run.MinFreeGB = 8
$lCase.Frames = $true
$lCase.DiagEnv = 'BRN_DEBUG_UI_TRACE=1,BRN_GPU_MONITOR_TRACE=1,BRN_FRAME_DUMP_MAX=24'
$lCase.ProfileFixture = 'build/game/Memcard/Profile.sav'
$lCase.Setup = {
    param($ctx)
    if ($ctx.Slot -le 0) { throw 'GPU monitor cases require an isolated slot.' }
    $lDir = Join-Path $ctx.Root ("build/game_slots/" + $ctx.Slot)
    New-Item -ItemType Directory -Force $lDir | Out-Null
    $lPath = Join-Path $lDir 'config.ini'
    if (Test-Path -LiteralPath $lPath) {
        Copy-Item -LiteralPath $lPath -Destination (Join-Path $ctx.RunDir 'slot_config.before.ini')
    }
    $lConfig = [IO.File]::ReadAllText((Join-Path $ctx.Root 'build/game/config.ini'))
    $lConfig = $lConfig -replace '(?m)^Width=.*$', 'Width=1280'
    $lConfig = $lConfig -replace '(?m)^Height=.*$', 'Height=720'
    $lConfig = $lConfig -replace '(?m)^Fullscreen=.*$', 'Fullscreen=0'
    $lConfig = $lConfig -replace '(?m)^VSync=.*$', 'VSync=1'
    $lVisible = "$($ctx.Case.GpuVisible)".ToLowerInvariant()
    $lGraph = "$($ctx.Case.GpuGraph)".ToLowerInvariant()
    $lConfig = $lConfig -replace '(?im)^Core/Debug/Performance/GPU Monitors/(Draw GPU monitors|Draw As Graph)=.*\r?\n?', ''
    $lSettings = "Core/Debug/Performance/GPU Monitors/Draw GPU monitors=$lVisible`r`nCore/Debug/Performance/GPU Monitors/Draw As Graph=$lGraph`r`n"
    $lDebugHeader = New-Object Text.RegularExpressions.Regex('(?im)^\[Debug\][ \t]*\r?$')
    if ($lDebugHeader.IsMatch($lConfig)) {
        # GetPrivateProfileSection reads the existing section; a duplicate header
        # would leave these settings outside the section the game actually sees.
        $lConfig = $lDebugHeader.Replace($lConfig, "[Debug]`r`n$lSettings", 1)
    } else {
        $lConfig += "`r`n[Debug]`r`n$lSettings"
    }
    [IO.File]::WriteAllText($lPath, $lConfig, (New-Object Text.UTF8Encoding($false)))
    Copy-Item -LiteralPath $lPath -Destination (Join-Path $ctx.RunDir 'config.used.ini')
}
$lCase.Checks += @(
    @{ Kind='Script'; Name='bounded frame capture produced evidence'; Script={
        param($ctx)
        $lFrames = @(Get-ChildItem -LiteralPath $ctx.FrameDir -Filter 'bb_*.bmp' -File -ErrorAction SilentlyContinue)
        $lBytes = ($lFrames | Measure-Object -Property Length -Sum).Sum
        return @{ Pass=($lFrames.Count -ge 1 -and $lFrames.Count -le 24);
                  Detail=("{0} frames, {1:N1} MiB; native maximum 24" -f $lFrames.Count, ($lBytes / 1MB)) }
    } }
    @{ Kind='LogCount'; Name='no engine assertions'; Pattern='\[ASSERT \d+\]'; Max=0 }
    @{ Kind='LogCount'; Name='GPU settings applied through real debug bindings';
       Pattern='\[debug-ini\] applied core/debug/performance/gpu monitors/(draw gpu monitors|draw as graph)='; Min=2 }
    @{ Kind='LogCount'; Name='native GPU query packets completed';
       Pattern='\[gpu-monitors\].*status=valid'; Min=3 }
    @{ Kind='LogValue'; Name='GPU frame has a measured nonzero cost';
       Pattern='\[gpu-monitors\].*status=valid.*totalMs=(?<cost>[0-9.]+)'; Group='cost'; Agg='max'; Min=0.000001 }
)
if ($Visible) {
    $lKind = if ($AsGraph) { 'bar' } else { 'row' }
    $lCase.Checks += @(
        @{ Kind='LogCount'; Name="selected $lMode overlay executed";
           Pattern="\[gpu-overlay\] visible=1 mode=$lMode monitored="; Min=1 }
        @{ Kind='LogValue'; Name="WorldOpaque GPU cost reached actual $lMode draw callback";
           Pattern="\[gpu-overlay-$lKind\] name=WorldOpaque value=(?<cost>[0-9.]+)"; Group='cost'; Agg='max'; Min=0.000001 }
    )
} else {
    $lCase.Checks += @(
        @{ Kind='LogCount'; Name='visibility switch disabled the overlay';
           Pattern='\[gpu-overlay\] visible=0'; Min=1 }
        @{ Kind='LogCount'; Name='hidden overlay emitted no graph or table callbacks';
           Pattern='\[gpu-overlay-(bar|row)\]'; Max=0 }
    )
}
return $lCase
