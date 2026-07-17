# popup_capture.ps1 -- drive to the autosave popup and capture it by WINDOW TITLE
# (Process.MainWindowHandle reads 0 intermittently; FindWindow by title is robust).
param([string]$OutDir = "scratch\popup_cap", [switch]$LeaveRunning)
$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$exe  = Join-Path $root "build\game\Burnout_PC.exe"
$log  = Join-Path $root "build\game\BrnGame.log"
$outPath = Join-Path $root $OutDir
New-Item -ItemType Directory -Force $outPath | Out-Null
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public static class Cap {
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
$evAccept = [Cap]::CreateEvent([IntPtr]::Zero,$false,$false,"Local\BurnoutPC_Input_Accept")
$script:GamePid = 0
function Find-Win { for($i=0;$i-lt40;$i++){ if($script:GamePid -ne 0){ $h=[Cap]::FindByPid([uint32]$script:GamePid); if($h -ne [IntPtr]::Zero){return $h} }; Start-Sleep -Milliseconds 250 }; return [IntPtr]::Zero }
function Shot($name){
  $h = Find-Win
  if($h -eq [IntPtr]::Zero){ Write-Host "  [shot] $name -- window not found"; return }
  for($t=0;$t-lt5;$t++){ [Cap]::keybd_event(0x12,0,0,[UIntPtr]::Zero); [Cap]::SetForegroundWindow($h)|Out-Null; [Cap]::keybd_event(0x12,0,2,[UIntPtr]::Zero); [Cap]::ShowWindow($h,5)|Out-Null; Start-Sleep -Milliseconds 200 }
  Start-Sleep -Milliseconds 400
  $r = New-Object Cap+RECT; [Cap]::GetWindowRect($h,[ref]$r)|Out-Null
  $w=$r.Right-$r.Left; $ht=$r.Bottom-$r.Top
  if($w -le 0 -or $ht -le 0){ Write-Host "  [shot] $name -- zero-size"; return }
  $bmp=New-Object System.Drawing.Bitmap($w,$ht); $g=[System.Drawing.Graphics]::FromImage($bmp)
  try{ $g.CopyFromScreen($r.Left,$r.Top,0,0,(New-Object System.Drawing.Size($w,$ht))); $f=Join-Path $outPath "$name.png"; $bmp.Save($f,[System.Drawing.Imaging.ImageFormat]::Png); Write-Host "  [shot] $f ($w x $ht)" }
  catch{ Write-Host "  [shot] $name -- $($_.Exception.Message)" }
  finally{ $g.Dispose(); $bmp.Dispose() }
}
function SendEnter($label){ $h=Find-Win; for($t=0;$t-lt5;$t++){ [Cap]::keybd_event(0x12,0,0,[UIntPtr]::Zero); [Cap]::SetForegroundWindow($h)|Out-Null; [Cap]::keybd_event(0x12,0,2,[UIntPtr]::Zero); Start-Sleep -Milliseconds 150 }; [Cap]::keybd_event(0x0D,0,0,[UIntPtr]::Zero); Start-Sleep -Milliseconds 250; [Cap]::keybd_event(0x0D,0,2,[UIntPtr]::Zero); [Cap]::SetEvent($evAccept)|Out-Null; Write-Host "  [key] $label"; Start-Sleep -Milliseconds 400 }
function WaitLog($pat,$sec,$label){ for($t=0;$t-lt$sec;$t++){ if((Test-Path $log) -and (Select-String -Path $log -Pattern $pat -Quiet)){ Write-Host "  [cue] $label"; return $true }; Start-Sleep -Seconds 1 }; Write-Host "  [cue] TIMEOUT $label"; return $false }

Get-Process Burnout_PC -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1; if(Test-Path $log){ Remove-Item $log -Force }
$env:BRN_INPUT_ALLOW_BACKGROUND = "1"
$p = Start-Process -FilePath $exe -WorkingDirectory (Split-Path $exe) -PassThru
$script:GamePid = $p.Id
Write-Host "[popup_capture] pid=$($p.Id)"
Start-Sleep -Seconds 5; SendEnter "END-release-noop" | Out-Null
WaitLog "resources-ready \(567\)" 90 "title composed" | Out-Null
Start-Sleep -Seconds 5
SendEnter "ENTER press-start"
WaitLog "'B5MenuItem' -> splice" 20 "menu up" | Out-Null
Start-Sleep -Seconds 3
SendEnter "ENTER select BURNOUT PARADISE"
WaitLog "MemoryCard: OnEnter" 20 "BF_PROFILE" | Out-Null
WaitLog "aux: faithful: INSTANTIATED" 30 "aux popup up" | Out-Null
Start-Sleep -Seconds 3
Shot "popup_wrapfix"
Start-Sleep -Seconds 2
Shot "popup_wrapfix_b"
if(-not $LeaveRunning){ Start-Sleep -Seconds 1; Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
Write-Host "[popup_capture] done -> $outPath"
