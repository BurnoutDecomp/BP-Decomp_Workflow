# profile_test.ps1 -- validates the autosave-warning popup + intro-video sequencing.
#
# With the faithful fix, BF_PROFILE now BLOCKS on the SAVELOAD_AUTOSAVE_WARNING prompt
# ([BootProfile] stage 3 -> 4 = RUNNING, then it DWELLS instead of going 4 -> 5). The
# user must answer CONTINUE. This harness:
#   1. boots to the title, press-start, selects BURNOUT PARADISE (-> BF_PROFILE)
#   2. waits for the profile RUNNING dwell, screenshots the popup
#   3. sends ENTER (CONTINUE) to dismiss it, confirms stage 4 -> 5
#   4. screenshots the intro video to confirm NO popup overlap
#   5. sends ONE ENTER to confirm it skips only the video (no double-fire)

param(
    [string]$OutDir = "scratch\profile_shots",
    [switch]$LeaveRunning
)
$ErrorActionPreference = 'Stop'

# ⛔ ONE HARNESS AT A TIME. This script kills every Burnout_PC on the box, so running it
# beside another harness destroys that harness's measurement -- and the victim reads the
# damage as a crash in the build under test. See _box_lock.ps1 for the measured history.
. "$PSScriptRoot\_box_lock.ps1"
Enter-BoxLock -Label "profile_test"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$exe  = Join-Path $root "build\game\Burnout_PC.exe"
$log  = Join-Path $root "build\game\BrnGame.log"
if (-not (Test-Path $exe)) { throw "exe not found: $exe" }
$outPath = Join-Path $root $OutDir
New-Item -ItemType Directory -Force $outPath | Out-Null
Get-ChildItem $outPath -Filter *.png -ErrorAction SilentlyContinue | Remove-Item -Force

Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class PT
{
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
    [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte s, uint f, UIntPtr e);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr CreateEvent(IntPtr a, bool m, bool i, string n);
    [DllImport("kernel32.dll")] public static extern bool SetEvent(IntPtr h);
    public struct RECT { public int Left, Top, Right, Bottom; }
}
"@
$evAccept = [PT]::CreateEvent([IntPtr]::Zero, $false, $false, "Local\BurnoutPC_Input_Accept")

function FG([IntPtr]$h) {
    for ($i=0; $i -lt 5; $i++) {
        if ([PT]::GetForegroundWindow() -eq $h) { break }
        [PT]::keybd_event(0x12,0,0,[UIntPtr]::Zero); [PT]::SetForegroundWindow($h) | Out-Null
        [PT]::keybd_event(0x12,0,2,[UIntPtr]::Zero); [PT]::ShowWindow($h,5) | Out-Null
        Start-Sleep -Milliseconds 200
    }
    Start-Sleep -Milliseconds 300
}
function Shot([System.Diagnostics.Process]$p, [string]$n) {
    $p.Refresh(); $h = $p.MainWindowHandle
    if ($h -eq [IntPtr]::Zero) { Write-Host "  [shot] $n -- no window"; return }
    FG $h
    $r = New-Object PT+RECT; [PT]::GetWindowRect($h,[ref]$r) | Out-Null
    $w = $r.Right-$r.Left; $ht = $r.Bottom-$r.Top
    if ($w -le 0 -or $ht -le 0) { Write-Host "  [shot] $n -- zero size"; return }
    $bmp = New-Object System.Drawing.Bitmap($w,$ht); $g = [System.Drawing.Graphics]::FromImage($bmp)
    try { $g.CopyFromScreen($r.Left,$r.Top,0,0,(New-Object System.Drawing.Size($w,$ht)))
          $bmp.Save((Join-Path $outPath "$n.png"),[System.Drawing.Imaging.ImageFormat]::Png); Write-Host "  [shot] $n" }
    catch { Write-Host "  [shot] $n -- $($_.Exception.Message)" }
    finally { $g.Dispose(); $bmp.Dispose() }
}
function Key([System.Diagnostics.Process]$p, [byte]$vk, [string]$lbl) {
    $p.Refresh(); if ($p.HasExited) { Write-Host "  [key] $lbl -- exited"; return }
    $h = $p.MainWindowHandle
    if ($h -ne [IntPtr]::Zero) {
        for ($i=0;$i -lt 5;$i++){ if([PT]::GetForegroundWindow() -eq $h){break}
            [PT]::keybd_event(0x12,0,0,[UIntPtr]::Zero); [PT]::SetForegroundWindow($h)|Out-Null
            [PT]::keybd_event(0x12,0,2,[UIntPtr]::Zero); [PT]::ShowWindow($h,5)|Out-Null; Start-Sleep -Milliseconds 200 }
        Start-Sleep -Milliseconds 150
    }
    [PT]::keybd_event($vk,0,0,[UIntPtr]::Zero); Start-Sleep -Milliseconds 250; [PT]::keybd_event($vk,0,2,[UIntPtr]::Zero)
    if ($vk -eq 0x0D) { [PT]::SetEvent($evAccept) | Out-Null }
    Write-Host "  [key] $lbl"; Start-Sleep -Milliseconds 400
}
# Wait for the Nth occurrence of a pattern (line count), so repeated cues (e.g. aux INSTANTIATED)
# are disambiguated by position.
function WaitLog([System.Diagnostics.Process]$p, [string]$pat, [int]$to, [string]$lbl, [int]$minCount=1) {
    for ($t=0; $t -lt $to; $t++) {
        if ($p.HasExited) { return $false }
        if (Test-Path $log) {
            $c = (Select-String -Path $log -Pattern $pat -AllMatches).Count
            if ($c -ge $minCount) { Write-Host "  [cue] $lbl"; return $true }
        }
        Start-Sleep -Seconds 1
    }
    Write-Host "  [cue] TIMEOUT $lbl ($pat)"; return $false
}

Get-Process Burnout_PC -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
if (Test-Path $log) { Remove-Item $log -Force }
Write-Host "[profile_test] launching"
$env:BRN_INPUT_ALLOW_BACKGROUND = "1"
$p = Start-Process -FilePath $exe -WorkingDirectory (Split-Path $exe) -PassThru
$VK_RETURN = 0x0D; $VK_END = 0x23

Start-Sleep -Seconds 5
Key $p $VK_END "END (assert release)"

if (WaitLog $p "PlayMovie: consume channel-41 'Title_Screen02'" 120 "title requested") {
    WaitLog $p "resources-ready \(567\)" 30 "title composed" | Out-Null
    Start-Sleep -Seconds 5
    Shot $p "p10_title"
    Key $p $VK_RETURN "ENTER (press start)"
    WaitLog $p "'B5MenuItem' -> splice" 20 "menu transin" | Out-Null
    Start-Sleep -Seconds 3
    Shot $p "p11_menu"
    Key $p $VK_RETURN "ENTER (select BURNOUT PARADISE)"
    if (-not (WaitLog $p "MemoryCard: OnEnter" 15 "BF_PROFILE entered")) {
        Key $p $VK_RETURN "ENTER (select retry)"
        WaitLog $p "MemoryCard: OnEnter" 20 "BF_PROFILE entered (retry)" | Out-Null
    }
    # BF_PROFILE reaches RUNNING (stage 3 -> 4) and now BLOCKS on the autosave-warning popup.
    if (WaitLog $p "\[BootProfile\] stage 3 -> 4" 30 "profile RUNNING (popup)") {
        Start-Sleep -Seconds 3   # let the SAVELOAD_AUTOSAVE_WARNING prompt render + settle
        Shot $p "p20_autosave_popup"
        Start-Sleep -Seconds 2
        Shot $p "p20b_autosave_popup"
        # Confirm it is DWELLING (must NOT have advanced to stage 4 -> 5 without input).
        $advanced = Test-Path $log
        if ($advanced) { $advanced = (Select-String -Path $log -Pattern "\[BootProfile\] stage 4 -> 5" -Quiet) }
        Write-Host "  [check] advanced-without-input = $advanced (expect False = popup blocks)"
        # Answer CONTINUE.
        Key $p $VK_RETURN "ENTER (CONTINUE / dismiss popup)"
        if (WaitLog $p "\[BootProfile\] stage 4 -> 5" 15 "popup dismissed -> LEAVING") {
            WaitLog $p "CompleteLoading: OnEnter" 15 "BF_COMPLOAD entered" | Out-Null
            WaitLog $p "\[Movie\] prepared VIDEOS\\intro\.vp6" 20 "intro prepared" | Out-Null
            Start-Sleep -Seconds 2
            Shot $p "p30_intro_video"   # must show ONLY the video, no popup overlap
            Start-Sleep -Seconds 2
            Shot $p "p30b_intro_video"
            # ONE ENTER: should skip ONLY the video (no double-fire onto a hidden menu).
            Key $p $VK_RETURN "ENTER (skip intro)"
            WaitLog $p "InGame: OnEnter" 30 "reached InGame (stage 5)" | Out-Null
            Start-Sleep -Seconds 3
            Shot $p "p40_after_skip"
        } else {
            Shot $p "p30_stuck_popup"
        }
    }
}
Start-Sleep -Seconds 2
Shot $p "p99_final"
if (-not $LeaveRunning) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
Write-Host "`n[profile_test] ---- log tail ----"
if (Test-Path $log) { Get-Content $log -Tail 60 }
Write-Host "[profile_test] shots in $outPath"
