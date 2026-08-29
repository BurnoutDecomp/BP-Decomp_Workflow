# saveicon_capture.ps1 -- drive past the autosave popup (press Continue) and burst-capture
# the top-left corner over the following seconds to catch the SaveIcon_mc spinner while the
# profile save is in flight (event 355 -> ShowSaveIcon). Reuses popup_capture's PID-window harness.
param([string]$OutDir = "scratch\saveicon_cap")
$ErrorActionPreference = 'Stop'

# ⛔ ONE HARNESS AT A TIME. This script kills every Burnout_PC on the box, so running it
# beside another harness destroys that harness's measurement -- and the victim reads the
# damage as a crash in the build under test. See _box_lock.ps1 for the measured history.
. "$PSScriptRoot\_box_lock.ps1"
Enter-BoxLock -Label "saveicon_capture"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$exe  = Join-Path $root "build\game\Burnout_PC.exe"
$log  = Join-Path $root "build\game\BrnGame.log"
$outPath = Join-Path $root $OutDir
New-Item -ItemType Directory -Force $outPath | Out-Null
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class Cap2 {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern void keybd_event(byte v, byte s, uint f, UIntPtr e);
  [DllImport("kernel32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr CreateEvent(IntPtr a, bool m, bool i, string n);
  [DllImport("kernel32.dll")] public static extern bool SetEvent(IntPtr h);
  public struct RECT { public int Left, Top, Right, Bottom; }
  public static IntPtr FindByPid(uint target) {
    IntPtr found = IntPtr.Zero;
    EnumWindows((h,l)=>{ uint pid; GetWindowThreadProcessId(h, out pid);
      if(pid==target && IsWindowVisible(h)){ RECT r; GetWindowRect(h,out r); if((r.Right-r.Left)>200 && (r.Bottom-r.Top)>150){ found=h; return false; } }
      return true; }, IntPtr.Zero);
    return found;
  }
}
"@
$evAccept = [Cap2]::CreateEvent([IntPtr]::Zero,$false,$false,"Local\BurnoutPC_Input_Accept")
$script:GamePid = 0
function Find-Win { for($i=0;$i-lt40;$i++){ if($script:GamePid -ne 0){ $h=[Cap2]::FindByPid([uint32]$script:GamePid); if($h -ne [IntPtr]::Zero){return $h} }; Start-Sleep -Milliseconds 250 }; return [IntPtr]::Zero }
function Fg($h){ for($t=0;$t-lt3;$t++){ [Cap2]::keybd_event(0x12,0,0,[UIntPtr]::Zero); [Cap2]::SetForegroundWindow($h)|Out-Null; [Cap2]::keybd_event(0x12,0,2,[UIntPtr]::Zero); [Cap2]::ShowWindow($h,5)|Out-Null; Start-Sleep -Milliseconds 120 } }
function Shot($name){
  $h = Find-Win; if($h -eq [IntPtr]::Zero){ Write-Host "  [shot] $name -- no window"; return }
  Fg $h; Start-Sleep -Milliseconds 250
  $r = New-Object Cap2+RECT; [Cap2]::GetWindowRect($h,[ref]$r)|Out-Null
  $w=$r.Right-$r.Left; $ht=$r.Bottom-$r.Top; if($w -le 0 -or $ht -le 0){ return }
  $bmp=New-Object System.Drawing.Bitmap($w,$ht); $g=[System.Drawing.Graphics]::FromImage($bmp)
  try{ $g.CopyFromScreen($r.Left,$r.Top,0,0,(New-Object System.Drawing.Size($w,$ht))); $bmp.Save((Join-Path $outPath "$name.png"),[System.Drawing.Imaging.ImageFormat]::Png); Write-Host "  [shot] $name ($w x $ht)" }
  finally{ $g.Dispose(); $bmp.Dispose() }
}
function SendEnter($label){ $h=Find-Win; Fg $h; [Cap2]::keybd_event(0x0D,0,0,[UIntPtr]::Zero); Start-Sleep -Milliseconds 200; [Cap2]::keybd_event(0x0D,0,2,[UIntPtr]::Zero); [Cap2]::SetEvent($evAccept)|Out-Null; Write-Host "  [key] $label"; Start-Sleep -Milliseconds 400 }
function WaitLog($pat,$sec,$label){ for($t=0;$t-lt$sec;$t++){ if((Test-Path $log) -and (Select-String -Path $log -Pattern $pat -Quiet)){ Write-Host "  [cue] $label"; return $true }; Start-Sleep -Seconds 1 }; Write-Host "  [cue] TIMEOUT $label"; return $false }

Get-Process Burnout_PC -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1; if(Test-Path $log){ Remove-Item $log -Force }
$env:BRN_INPUT_ALLOW_BACKGROUND = "1"
$p = Start-Process -FilePath $exe -WorkingDirectory (Split-Path $exe) -PassThru
$script:GamePid = $p.Id
Write-Host "[saveicon_capture] pid=$($p.Id)"
Start-Sleep -Seconds 5; SendEnter "END-noop" | Out-Null
WaitLog "resources-ready \(567\)" 90 "title" | Out-Null
Start-Sleep -Seconds 5; SendEnter "press-start"
Start-Sleep -Seconds 3; SendEnter "select BURNOUT PARADISE"
WaitLog "aux: faithful: INSTANTIATED" 30 "popup up" | Out-Null
Start-Sleep -Seconds 3
Shot "00_popup"
SendEnter "Continue (dismiss popup -> profile save)"
# Burst the following ~24s to catch the top-left autosave spinner while the profile writes.
for($i=1;$i-le24;$i++){ Shot ("save_{0:d2}" -f $i); Start-Sleep -Milliseconds 700 }
# Surface any save-icon / autosave activity the log recorded during the window.
if(Test-Path $log){ Write-Host "--- log save/icon lines ---"; Select-String -Path $log -Pattern "save","autosave","SaveIcon","355","profile" -SimpleMatch | Select-Object -Last 20 | ForEach-Object { Write-Host $_.Line } }
Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
Write-Host "[saveicon_capture] done -> $outPath"
