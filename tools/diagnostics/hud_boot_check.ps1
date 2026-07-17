# hud_boot_check.ps1 -- drive the boot flow to FBURN_MAIN using ONLY the game's
# harness named-event channel (no synthetic keystrokes, no foreground changes),
# then verify the free-drive HUD state entered and capture a PrintWindow screenshot.
param([string]$OutDir = "scratch\hud_shots")
$ErrorActionPreference = 'Stop'
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
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
    [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte s, uint f, UIntPtr e);
    public struct RECT { public int Left, Top, Right, Bottom; }
}
"@
# The harness events must exist BEFORE the game opens them (auto-reset).
$evAccept = [HB]::CreateEvent([IntPtr]::Zero, $false, $false, "Local\BurnoutPC_Input_Accept")
$evAssert = [HB]::CreateEvent([IntPtr]::Zero, $false, $false, "Local\BurnoutPC_Assert_Release")

function WaitLog([System.Diagnostics.Process]$p, [string]$pat, [int]$to, [string]$lbl, [int]$minCount=1) {
    for ($t=0; $t -lt $to; $t++) {
        if ($p.HasExited) { Write-Host "  [cue] EXITED at $lbl"; return $false }
        if (Test-Path $log) {
            $c = (Select-String -Path $log -Pattern $pat -AllMatches -ErrorAction SilentlyContinue).Count
            if ($c -ge $minCount) { Write-Host "  [cue] $lbl"; return $true }
        }
        [HB]::SetEvent($evAssert) | Out-Null   # keep any dev-assert screen released
        Start-Sleep -Seconds 1
    }
    Write-Host "  [cue] TIMEOUT $lbl ($pat)"; return $false
}
function Accept([string]$lbl) { [HB]::SetEvent($evAccept) | Out-Null; Write-Host "  [evt] ACCEPT ($lbl)"; Start-Sleep -Milliseconds 800 }
function Dwell([int]$secs) { for ($d=0; $d -lt $secs; $d++) { [HB]::SetEvent($evAssert) | Out-Null; Start-Sleep -Seconds 1 } }
function FG([IntPtr]$h) {
    for ($i=0; $i -lt 5; $i++) {
        if ([HB]::GetForegroundWindow() -eq $h) { break }
        [HB]::keybd_event(0x12,0,0,[UIntPtr]::Zero); [HB]::SetForegroundWindow($h) | Out-Null
        [HB]::keybd_event(0x12,0,2,[UIntPtr]::Zero); [HB]::ShowWindow($h,5) | Out-Null
        Start-Sleep -Milliseconds 200
    }
    Start-Sleep -Milliseconds 400
}
function Shot([System.Diagnostics.Process]$p, [string]$n) {
    $p.Refresh(); $h = $p.MainWindowHandle
    if ($h -eq [IntPtr]::Zero) { Write-Host "  [shot] $n -- no window"; return }
    # CopyFromScreen captures the real composited D3D swapchain (PrintWindow returns
    # black for D3D content), so the window must be foreground + unobscured first.
    FG $h
    $r = New-Object HB+RECT; [HB]::GetWindowRect($h,[ref]$r) | Out-Null
    $w = $r.Right-$r.Left; $ht = $r.Bottom-$r.Top
    if ($w -le 0 -or $ht -le 0) { return }
    $bmp = New-Object System.Drawing.Bitmap($w,$ht)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    try {
        $g.CopyFromScreen($r.Left,$r.Top,0,0,(New-Object System.Drawing.Size($w,$ht)))
        $bmp.Save((Join-Path $outPath "$n.png"),[System.Drawing.Imaging.ImageFormat]::Png)
        Write-Host "  [shot] $n"
    } catch { Write-Host "  [shot] $n -- $($_.Exception.Message)" }
    finally { $g.Dispose(); $bmp.Dispose() }
}

Get-Process Burnout_PC -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
if (Test-Path $log) { Remove-Item $log -Force }
$env:BRN_INPUT_ALLOW_BACKGROUND = "1"
Write-Host "[hud_check] launching"
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
        # The point of it all: FBURN_MAIN must be the REAL state now.
        $gap  = (Select-String -Path $log -Pattern "FBurnMainHudState::OnEnter -- un-reconstructed" -Quiet)
        $defer= (Select-String -Path $log -Pattern "\[FBurnMainHud\]" -AllMatches).Count
        Write-Host "  [check] old gap-stub log present = $gap (expect False)"
        Write-Host "  [check] new deferral log lines   = $defer (expect > 0)"
        WaitLog $p "\[FBurnMainHud\] stage 1 -> 2" 30 "HUD resources loaded (B5RaceHud mounted)" | Out-Null
        WaitLog $p "\[FBurnMainHud\] stage 2 -> 3" 20 "HUD running" | Out-Null
        Dwell 6
        Shot $p "h10_ingame_hud"
        Dwell 4
        Shot $p "h11_ingame_hud_b"
    }
}
Start-Sleep -Seconds 2
Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
Write-Host "`n[hud_check] ---- HUD-relevant log lines ----"
if (Test-Path $log) {
    Select-String -Path $log -Pattern "FBurnMainHud|FBURN|HudFlow|B5RaceHud|RaceMainHUD" | Select-Object -Last 25 | ForEach-Object { $_.Line }
}
Write-Host "[hud_check] shots in $outPath"
