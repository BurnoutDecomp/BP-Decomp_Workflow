# hud_shot_pw.ps1 -- boot to FBURN_MAIN and capture in-game frames with
# PrintWindow(PW_RENDERFULLCONTENT), NO foreground changes (the ALT+SetForegroundWindow
# dance deterministically freezes the in-game Present -- proven by CPU probing).
param([string]$OutDir = "scratch\hud_shots_pw")
$ErrorActionPreference = 'Stop'

# ⛔ ONE HARNESS AT A TIME. This script kills every Burnout_PC on the box, so running it
# beside another harness destroys that harness's measurement -- and the victim reads the
# damage as a crash in the build under test. See _box_lock.ps1 for the measured history.
. "$PSScriptRoot\_box_lock.ps1"
Enter-BoxLock -Label "hud_shot_pw"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
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
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint f);
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
function Dwell([int]$secs) { for ($d=0; $d -lt $secs; $d++) { [HB]::SetEvent($evAssert) | Out-Null; Start-Sleep -Seconds 1 } }
function ShotPW([System.Diagnostics.Process]$p, [string]$n) {
    $p.Refresh(); $h = $p.MainWindowHandle
    if ($h -eq [IntPtr]::Zero) { Write-Host "  [shot] $n -- no window"; return }
    $r = New-Object HB+RECT; [HB]::GetWindowRect($h,[ref]$r) | Out-Null
    $w = $r.Right-$r.Left; $ht = $r.Bottom-$r.Top
    if ($w -le 0 -or $ht -le 0) { return }
    $bmp = New-Object System.Drawing.Bitmap($w,$ht)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    try {
        $dc = $g.GetHdc()
        # PW_RENDERFULLCONTENT (2): DWM-composed content incl. D3D swapchains, no focus needed.
        $ok = [HB]::PrintWindow($h, $dc, 2)
        $g.ReleaseHdc($dc)
        $bmp.Save((Join-Path $outPath "$n.png"),[System.Drawing.Imaging.ImageFormat]::Png)
        Write-Host "  [shot] $n (PrintWindow=$ok)"
    } catch { Write-Host "  [shot] $n -- $($_.Exception.Message)" }
    finally { $g.Dispose(); $bmp.Dispose() }
}

Get-Process Burnout_PC -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
if (Test-Path $log) { Remove-Item $log -Force }
$env:BRN_INPUT_ALLOW_BACKGROUND = "1"
Write-Host "[pw_check] launching"
$p = Start-Process -FilePath $exe -WorkingDirectory (Split-Path $exe) -PassThru

if (WaitLog $p "import-load: complete 'Title_Screen02'" 120 "title requested") {
    WaitLog $p "resources-ready \(567\)" 30 "title composed" | Out-Null
    Start-Sleep -Seconds 5
    ShotPW $p "p00_title"
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
        Dwell 4
        ShotPW $p "p10_ingame_hud"
        Dwell 5
        ShotPW $p "p11_ingame_hud_b"
        Dwell 10
        ShotPW $p "p12_ingame_hud_c"
    }
}
Start-Sleep -Seconds 1
Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
Write-Host "[pw_check] shots in $outPath"
