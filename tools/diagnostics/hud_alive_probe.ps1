# hud_alive_probe.ps1 -- drive the boot to FBURN_MAIN like hud_boot_check.ps1 but take
# NO screenshots and force NO foreground changes. Instead, sample the process CPU time
# to prove whether the game loop keeps running in-game; then optionally do ONE
# foreground+shot cycle and sample again to test whether the FG dance freezes it.
param([string]$OutDir = "scratch\hud_alive")
$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$exe  = Join-Path $root "build\game\Burnout_PC.exe"
$log  = Join-Path $root "build\game\BrnGame.log"
$outPath = Join-Path $root $OutDir
New-Item -ItemType Directory -Force $outPath | Out-Null

Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class HB
{
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr CreateEvent(IntPtr a, bool m, bool i, string n);
    [DllImport("kernel32.dll")] public static extern bool SetEvent(IntPtr h);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte s, uint f, UIntPtr e);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
    public struct RECT { public int Left, Top, Right, Bottom; }
}
"@
$evAccept = [HB]::CreateEvent([IntPtr]::Zero, $false, $false, "Local\BurnoutPC_Input_Accept")
$evAssert = [HB]::CreateEvent([IntPtr]::Zero, $false, $false, "Local\BurnoutPC_Assert_Release")

function WaitLog([System.Diagnostics.Process]$p, [string]$pat, [int]$to, [string]$lbl) {
    for ($t=0; $t -lt $to; $t++) {
        if ($p.HasExited) { Write-Host "  [cue] EXITED at $lbl"; return $false }
        if (Test-Path $log) {
            if (Select-String -Path $log -Pattern $pat -Quiet -ErrorAction SilentlyContinue) { Write-Host "  [cue] $lbl"; return $true }
        }
        [HB]::SetEvent($evAssert) | Out-Null
        Start-Sleep -Seconds 1
    }
    Write-Host "  [cue] TIMEOUT $lbl ($pat)"; return $false
}
function Accept([string]$lbl) { [HB]::SetEvent($evAccept) | Out-Null; Write-Host "  [evt] ACCEPT ($lbl)"; Start-Sleep -Milliseconds 800 }
function CpuProbe([System.Diagnostics.Process]$p, [string]$lbl, [int]$secs) {
    $samples = @()
    for ($i=0; $i -lt $secs; $i+=3) {
        if ($p.HasExited) { Write-Host "  [cpu] $lbl -- EXITED"; return }
        $p.Refresh()
        $samples += $p.TotalProcessorTime.TotalMilliseconds
        [HB]::SetEvent($evAssert) | Out-Null
        Start-Sleep -Seconds 3
    }
    $deltas = @(); for ($i=1; $i -lt $samples.Count; $i++) { $deltas += [int]($samples[$i]-$samples[$i-1]) }
    Write-Host ("  [cpu] {0}: deltas(ms per 3s) = {1}" -f $lbl, ($deltas -join ', '))
}

Get-Process Burnout_PC -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
if (Test-Path $log) { Remove-Item $log -Force }
$env:BRN_INPUT_ALLOW_BACKGROUND = "1"
Write-Host "[alive_probe] launching"
$p = Start-Process -FilePath $exe -WorkingDirectory (Split-Path $exe) -PassThru

if (WaitLog $p "import-load: complete 'Title_Screen02'" 120 "title requested") {
    WaitLog $p "resources-ready \(567\)" 30 "title composed" | Out-Null
    Start-Sleep -Seconds 5
    Accept "press start"
    WaitLog $p "'B5MenuItem' -> splice" 25 "menu transin" | Out-Null
    Start-Sleep -Seconds 3
    Accept "select BURNOUT PARADISE"
    if (-not (WaitLog $p "MemoryCard: OnEnter" 15 "BF_PROFILE entered")) {
        Accept "retry select"
        WaitLog $p "MemoryCard: OnEnter" 20 "BF_PROFILE entered (retry)" | Out-Null
    }
    if (WaitLog $p "\[BootProfile\] stage 3 -> 4" 30 "profile popup") {
        Start-Sleep -Seconds 3
        Accept "CONTINUE (dismiss popup)"
        WaitLog $p "\[BootProfile\] stage 4 -> 5" 15 "popup dismissed" | Out-Null
        WaitLog $p "\[Movie\] prepared VIDEOS\\intro\.vp6" 25 "intro prepared" | Out-Null
        Start-Sleep -Seconds 3
        Accept "skip intro"
        WaitLog $p "InGame: OnEnter" 30 "InGame entered" | Out-Null
        WaitLog $p "\[FBurnMainHud\] stage 2 -> 3" 40 "HUD running" | Out-Null
        # ---- phase 1: hands off, is the loop alive? ----
        CpuProbe $p "in-game, NO foreground/shot" 24
        # ---- phase 2: one FG dance (the suspected freeze trigger) ----
        $p.Refresh(); $h = $p.MainWindowHandle
        if ($h -ne [IntPtr]::Zero) {
            Write-Host "  [fg] forcing foreground (suspected trigger)"
            [HB]::keybd_event(0x12,0,0,[UIntPtr]::Zero); [HB]::SetForegroundWindow($h) | Out-Null
            [HB]::keybd_event(0x12,0,2,[UIntPtr]::Zero); [HB]::ShowWindow($h,5) | Out-Null
            Start-Sleep -Milliseconds 600
        }
        CpuProbe $p "after the FG dance" 24
    }
}
Start-Sleep -Seconds 1
Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
Write-Host "[alive_probe] done"
