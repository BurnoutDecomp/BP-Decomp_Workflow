# xenia_prompt_capture.ps1 -- boot the ORIGINAL X360 build in Xenia and capture the
# title -> menu -> autosave-prompt sequence (ground truth for the PC recon).
param([string]$OutDir = "scratch\xenia_truth", [int]$BootSeconds = 75)
$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$outPath = Join-Path $root $OutDir
New-Item -ItemType Directory -Force $outPath | Out-Null
Add-Type -AssemblyName System.Drawing
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class XCap {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern void keybd_event(byte v, byte s, uint f, UIntPtr e);
  public struct RECT { public int Left, Top, Right, Bottom; }
  public static IntPtr FindByPid(uint target) {
    IntPtr found = IntPtr.Zero;
    EnumWindows((h,l)=>{ uint pid; GetWindowThreadProcessId(h, out pid);
      if(pid==target && IsWindowVisible(h)){ RECT r; GetWindowRect(h,out r); if((r.Right-r.Left)>400 && (r.Bottom-r.Top)>300){ found=h; return false; } }
      return true; }, IntPtr.Zero);
    return found;
  }
}
"@
$dir = "D:\Emulation\Emulators\Xenia\Xenia Burnout 5 v6"
$xex = Join-Path $dir "Burnout_tcartwright\BURNOUT_X360_ARTIST.XEX"
Get-Process xenia_burnout5 -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
$p = Start-Process -FilePath (Join-Path $dir "xenia_burnout5.exe") -ArgumentList "`"$xex`"" -WorkingDirectory $dir -PassThru
Write-Host "[xenia] pid=$($p.Id), booting $BootSeconds s"

function Get-Win { for($i=0;$i-lt40;$i++){ $h=[XCap]::FindByPid([uint32]$p.Id); if($h -ne [IntPtr]::Zero){return $h}; Start-Sleep -Milliseconds 500 }; return [IntPtr]::Zero }
function FG([IntPtr]$h) {
  for ($t = 0; $t -lt 5; $t++) {
    if ([XCap]::GetForegroundWindow() -eq $h) { break }
    [XCap]::keybd_event(0x12,0,0,[UIntPtr]::Zero); [XCap]::SetForegroundWindow($h) | Out-Null; [XCap]::keybd_event(0x12,0,2,[UIntPtr]::Zero)
    Start-Sleep -Milliseconds 200
  }
}
function Shot([string]$name) {
  $h = Get-Win
  if ($h -eq [IntPtr]::Zero) { Write-Host "  [shot] $name -- no window"; return }
  FG $h
  Start-Sleep -Milliseconds 400
  $r = New-Object XCap+RECT; [XCap]::GetWindowRect($h,[ref]$r) | Out-Null
  $w=$r.Right-$r.Left; $ht=$r.Bottom-$r.Top
  $bmp = New-Object System.Drawing.Bitmap($w,$ht); $g=[System.Drawing.Graphics]::FromImage($bmp)
  try { $g.CopyFromScreen($r.Left,$r.Top,0,0,(New-Object System.Drawing.Size($w,$ht))); $f=Join-Path $outPath "$name.png"; $bmp.Save($f,[System.Drawing.Imaging.ImageFormat]::Png); Write-Host "  [shot] $f" }
  finally { $g.Dispose(); $bmp.Dispose() }
}
function Key([byte]$vk, [string]$label) {
  $h = Get-Win; FG $h
  Start-Sleep -Milliseconds 200
  [XCap]::keybd_event($vk,0,0,[UIntPtr]::Zero); Start-Sleep -Milliseconds 120; [XCap]::keybd_event($vk,0,2,[UIntPtr]::Zero)
  Write-Host "  [key] $label"
}

Start-Sleep -Seconds $BootSeconds
Shot "x_00_boot"
# skip any remaining logo/attract with Start (Tab), then shoot the title
Key 0x09 "TAB (start)"
Start-Sleep -Seconds 6
Shot "x_01_title"
Key 0x09 "TAB (press start)"
Start-Sleep -Seconds 6
Shot "x_02_menu"
Key 0x41 "A (menu accept)"
Start-Sleep -Seconds 3
Shot "x_03_prompt"
Start-Sleep -Seconds 2
Shot "x_04_prompt_b"
Start-Sleep -Seconds 2
Shot "x_05_prompt_c"
Key 0x41 "A (continue)"
Start-Sleep -Seconds 4
Shot "x_06_after_accept"
Start-Sleep -Seconds 6
Shot "x_07_intro"
Get-Process xenia_burnout5 -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "[xenia] done"
