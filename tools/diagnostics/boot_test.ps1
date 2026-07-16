# boot_test.ps1 -- the scripted boot/menu validation loop.

#
# Launches build\game\Burnout_PC.exe, captures foreground pixels at scripted
# points, drives scripted key presses (menu accept/navigate), then stops the process
# and prints the tail of build\game\BrnGame.log.
#
# Usage (from the repo root):
#   powershell -ExecutionPolicy Bypass -File tools\diagnostics\boot_test.ps1 `
#       [-OutDir scratch\boot_shots] [-SettleSeconds 25]
#
# Gotchas (from the project handoffs):
#   * Kill Burnout_PC.exe BEFORE building -- the exe lock silently breaks the link.
#   * Dev asserts pause the sim ("press END to continue" in the log); the script sends
#     END a few times after launch so an assert cannot hang the run.
#   * Verify by SCREENSHOT, not just the log, for menu-render regressions.

param(
    [string]$OutDir = "scratch\boot_shots",
    [int]$SettleSeconds = 25,
    [int]$MenuDwellSeconds = 6,
    [switch]$LeaveRunning   # diagnostics: keep the game alive at the end (skip the kill)
)

$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$exe  = Join-Path $root "build\game\Burnout_PC.exe"
$log  = Join-Path $root "build\game\BrnGame.log"
if (-not (Test-Path $exe)) { throw "exe not found: $exe (run tools\build\build_game_exe.bat first)" }
$outPath = Join-Path $root $OutDir
New-Item -ItemType Directory -Force $outPath | Out-Null

Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class BootTestNative
{
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hwnd, out RECT rect);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hwnd);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hwnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern IntPtr CreateEvent(IntPtr attributes, bool manualReset, bool initialState, string name);
    [DllImport("kernel32.dll", SetLastError=true)] public static extern bool SetEvent(IntPtr handle);
    public struct RECT { public int Left, Top, Right, Bottom; }

    // Process.MainWindowHandle intermittently reads 0 for the game (no owned visible
    // top-level at query time); resolve the window by PID instead (the robust pattern
    // from scratch/popup_capture.ps1).
    public delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    public static IntPtr FindByPid(uint target) {
        IntPtr found = IntPtr.Zero;
        EnumWindows((h,l)=>{ uint pid; GetWindowThreadProcessId(h, out pid);
            if(pid==target && IsWindowVisible(h)){ RECT r; GetWindowRect(h,out r); if((r.Right-r.Left)>200 && (r.Bottom-r.Top)>150){ found=h; return false; } }
            return true; }, IntPtr.Zero);
        return found;
    }
}
"@

# Resolve the game window: MainWindowHandle first, EnumWindows-by-PID fallback.
function Get-GameWindow([System.Diagnostics.Process]$proc) {
    $proc.Refresh()
    $hwnd = $proc.MainWindowHandle
    if ($hwnd -ne [IntPtr]::Zero) { return $hwnd }
    return [BootTestNative]::FindByPid([uint32]$proc.Id)
}

$script:HarnessInputEvents = @{
    0x0D = [BootTestNative]::CreateEvent([IntPtr]::Zero, $false, $false, "Local\BurnoutPC_Input_Accept")
    0x1B = [BootTestNative]::CreateEvent([IntPtr]::Zero, $false, $false, "Local\BurnoutPC_Input_Stop")
    0x28 = [BootTestNative]::CreateEvent([IntPtr]::Zero, $false, $false, "Local\BurnoutPC_Input_Next")
    0x26 = [BootTestNative]::CreateEvent([IntPtr]::Zero, $false, $false, "Local\BurnoutPC_Input_Prev")
}

function Foreground-Window([IntPtr]$hwnd) {
    # CopyFromScreen needs the game to be foregrounded and unobscured. Force foreground
    # (ALT-tap unlock, same as Send-Key) and let DWM refresh before capturing.
    for ($try = 0; $try -lt 5; $try++) {
        if ([BootTestNative]::GetForegroundWindow() -eq $hwnd) { break }
        [BootTestNative]::keybd_event(0x12, 0, 0, [UIntPtr]::Zero)      # ALT down
        [BootTestNative]::SetForegroundWindow($hwnd) | Out-Null
        [BootTestNative]::keybd_event(0x12, 0, 2, [UIntPtr]::Zero)      # ALT up
        # DO NOT call ShowWindow($hwnd, 5) here: a cross-process ShowWindow(SW_SHOW) on the
        # game window resolves through the launcher's STARTUPINFO show-state and HIDES it
        # (WS_VISIBLE drops, every later capture sees "no window"). Root-caused 2026-07-16.
        Start-Sleep -Milliseconds 200
    }
    Start-Sleep -Milliseconds 300   # let DWM composite a fresh frame into the surface
}

function Take-Shot([System.Diagnostics.Process]$proc, [string]$name) {
    $hwnd = Get-GameWindow $proc
    if ($hwnd -eq [IntPtr]::Zero) { Write-Host "  [shot] $name -- no window yet"; return }
    Foreground-Window $hwnd
    $rect = New-Object BootTestNative+RECT
    [BootTestNative]::GetWindowRect($hwnd, [ref]$rect) | Out-Null
    $w = $rect.Right - $rect.Left; $h = $rect.Bottom - $rect.Top
    if ($w -le 0 -or $h -le 0) { Write-Host "  [shot] $name -- zero-size window"; return }
    $bmp = New-Object System.Drawing.Bitmap($w, $h)
    $gfx = [System.Drawing.Graphics]::FromImage($bmp)
    try {
        # Capture the actual foreground pixels. PrintWindow(PW_RENDERFULLCONTENT) can
        # return only the window-class background while a D3D9 swap chain is actively
        # presenting, producing a plausible-looking but false blank-video result.
        $gfx.CopyFromScreen($rect.Left, $rect.Top, 0, 0, (New-Object System.Drawing.Size($w, $h)))
        $file = Join-Path $outPath "$name.png"
        $bmp.Save($file, [System.Drawing.Imaging.ImageFormat]::Png)
        Write-Host "  [shot] $file"
    }
    catch {
        # A locked/disconnected Windows desktop can make CopyFromScreen report an
        # invalid display handle even though the game window and validation run are
        # healthy. Keep driving the state/log harness and report the missing frame.
        Write-Host "  [shot] $name -- capture unavailable: $($_.Exception.Message)"
    }
    finally {
        $gfx.Dispose()
        $bmp.Dispose()
    }
}

function Send-Key([System.Diagnostics.Process]$proc, [byte]$vk, [string]$label) {
    $proc.Refresh()
    if ($proc.HasExited) { Write-Host "  [key] $label -- game already exited"; return }
    $hwnd = Get-GameWindow $proc
    if ($hwnd -ne [IntPtr]::Zero) {
        # The game's input leaf gates GetAsyncKeyState on GetForegroundWindow(), and a
        # background script cannot always steal foreground (Windows foreground lock).
        # The ALT-tap unlocks SetForegroundWindow; verify + retry until it sticks.
        for ($try = 0; $try -lt 5; $try++) {
            if ([BootTestNative]::GetForegroundWindow() -eq $hwnd) { break }
            [BootTestNative]::keybd_event(0x12, 0, 0, [UIntPtr]::Zero)      # ALT down
            [BootTestNative]::SetForegroundWindow($hwnd) | Out-Null
            [BootTestNative]::keybd_event(0x12, 0, 2, [UIntPtr]::Zero)      # ALT up
            # (no ShowWindow here -- see Foreground-Window: it HIDES the game window)
            Start-Sleep -Milliseconds 200
        }
        if ([BootTestNative]::GetForegroundWindow() -ne $hwnd) {
            Write-Host "  [key] $label -- WARNING: window not foreground (input may be gated)"
        }
        Start-Sleep -Milliseconds 150
    }
    if ($script:HarnessInputEvents.ContainsKey([int]$vk)) {
        # Named-event channel ONLY for the mapped actions: sending the real keystroke AND
        # the event double-fires the action when a game frame lands between the key-up and
        # the SetEvent (two pressed edges from one Send-Key -- the "one ENTER accepted the
        # menu AND skipped the video" artifact). One SetEvent == exactly one pressed edge.
        [BootTestNative]::SetEvent($script:HarnessInputEvents[[int]$vk]) | Out-Null
    } else {
        [BootTestNative]::keybd_event($vk, 0, 0, [UIntPtr]::Zero)
        Start-Sleep -Milliseconds 250
        [BootTestNative]::keybd_event($vk, 0, 2, [UIntPtr]::Zero)   # KEYEVENTF_KEYUP
    }
    Write-Host "  [key] $label"
    Start-Sleep -Milliseconds 400
}

# Wait until the game log contains a marker (log-cued pacing -- each boot's timing
# shifts with the synchronous loads, so wall-clock scripting keeps missing windows).
function Wait-ForLog([System.Diagnostics.Process]$proc, [string]$pattern, [int]$timeoutSec, [string]$label) {
    for ($t = 0; $t -lt $timeoutSec; $t++) {
        if ($proc.HasExited) { return $false }
        if ((Test-Path $log) -and (Select-String -Path $log -Pattern $pattern -Quiet)) {
            Write-Host "  [cue] $label"
            return $true
        }
        Start-Sleep -Seconds 1
    }
    Write-Host "  [cue] TIMEOUT waiting for '$label' ($pattern)"
    return $false
}

# ---- run ------------------------------------------------------------------------
Get-Process Burnout_PC -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
if (Test-Path $log) { Remove-Item $log -Force }

Write-Host "[boot_test] launching $exe"
# The input leaf honours BRN_INPUT_ALLOW_BACKGROUND (a FLAG'd PC test hook): the game
# accepts the harness's injected key state without needing the desktop foreground, so
# the script no longer fights the user's focus (and runs reliably unattended).
$env:BRN_INPUT_ALLOW_BACKGROUND = "1"
$proc = Start-Process -FilePath $exe -WorkingDirectory (Split-Path $exe) -PassThru

$VK_END = 0x23; $VK_RETURN = 0x0D; $VK_DOWN = 0x28

# Release the known Construct-time dev assert, then pace on log cues.
Start-Sleep -Seconds 5
Send-Key $proc $VK_END "END (assert release)"

if (Wait-ForLog $proc "\[Movie\] prepared VIDEOS\\EAFranchise\.vp6" 60 "EA intro prepared") {
    Start-Sleep -Milliseconds 500
    Take-Shot $proc "boot_10_ea_video"
    Start-Sleep -Seconds 1
    Take-Shot $proc "boot_10b_ea_video"
}
if (Wait-ForLog $proc "\[Movie\] prepared VIDEOS\\Criterion\.vp6" 60 "Criterion intro prepared") {
    Start-Sleep -Milliseconds 500
    Take-Shot $proc "boot_11_criterion_video"
    Start-Sleep -Seconds 1
    Take-Shot $proc "boot_11b_criterion_video"
}
# The overlay flow FSM loads during boot (RunFsm{BrnOverlay -> OVERLAY} at the GUIMODULE stage).
Wait-ForLog $proc "BRNOVERLAY\.BUNDLE' -> loaded" 30 "overlay FSM loaded" | Out-Null
if (Wait-ForLog $proc "\[BootLegal\] stage 1 -> 2" 90 "title requested") {
    # Give the title time to compose + fade in, then shoot it.
    Wait-ForLog $proc "resources-ready \(567\)" 30 "title composed" | Out-Null
    Start-Sleep -Seconds 6
    Take-Shot $proc "boot_20_title"

    Send-Key $proc $VK_RETURN "ENTER (press start)"
    # The menu blip fires when the selection menu transitions in; accept only after it.
    Wait-ForLog $proc "'B5MenuItem' -> splice" 20 "menu transin" | Out-Null
    Start-Sleep -Seconds 4
    Take-Shot $proc "boot_21_menu"

    Send-Key $proc $VK_RETURN "ENTER (menu accept)"
    if (-not (Wait-ForLog $proc "MemoryCard: OnEnter" 15 "BF_PROFILE entered")) {
        Send-Key $proc $VK_RETURN "ENTER (menu accept retry)"
    }
    if (Wait-ForLog $proc "MemoryCard: OnEnter" 20 "BF_PROFILE entered (retry)") {
        # BootProfile owns the save/load prompt while the profile task runs. It is
        # a BLOCKING stage since the real SaveLoadSystem::Bootup landed: the autosave-
        # warning prompt waits for CONTINUE (the console waits for the A press), so the
        # harness must accept it -- capture the prompt first, then send the accept.
        Wait-ForLog $proc "aux: faithful: INSTANTIATED" 30 "profile prompt up" | Out-Null
        Start-Sleep -Seconds 3   # let ShowMessage resolve the text + glyphs into the prompt
        Take-Shot $proc "boot_22_profile"
        Send-Key $proc $VK_RETURN "ENTER (autosave prompt CONTINUE)"
        if (Wait-ForLog $proc "CompleteLoading: OnEnter" 30 "BF_COMPLOAD entered") {
            # The post-title intro montage is 116s; a press skips it (the state's
            # unload-or-stop handler posts StopVideo).
            Wait-ForLog $proc "\[Movie\] prepared VIDEOS\\intro\.vp6" 30 "intro video prepared" | Out-Null
            Start-Sleep -Seconds 2
            Take-Shot $proc "boot_23a_compload_intro"
            Start-Sleep -Seconds 3
            Take-Shot $proc "boot_23_compload_intro"
            Send-Key $proc $VK_RETURN "ENTER (skip intro)"
            # Stage 5 posts BrnScreenFsm@LOADING (SCREEN flow) + BrnFBFsm (HUD flow).
            if (Wait-ForLog $proc "BRNSCREENFSM\.BUNDLE' -> loaded" 60 "SCREEN FSM loaded") {
                Wait-ForLog $proc "BRNFBFSM\.BUNDLE' -> loaded" 30 "freeburn HUD FSM loaded" | Out-Null
                Start-Sleep -Seconds 5
                Take-Shot $proc "boot_24_screen_loading"
                # ScreenLoading waits on the world-load-complete event (137); if the game
                # side posts it, the FSM moves LOADING -> INGAME. Give it a window, then
                # try the pause path (ESC -> InGame::HandleControllerInput).
                Start-Sleep -Seconds 8
                Take-Shot $proc "boot_25_ingame"
                Send-Key $proc 0x1B "ESC (pause probe)"
                Start-Sleep -Seconds 3
                Take-Shot $proc "boot_26_pause_probe"
            } else {
                Take-Shot $proc "boot_24_stuck_handoff"
            }
        } else {
            Take-Shot $proc "boot_23_stuck_profile"
        }
    } else {
        Take-Shot $proc "boot_22_stuck_legal"
    }
}
Start-Sleep -Seconds 3
Take-Shot $proc "boot_30_final"
if ($LeaveRunning) {
    Write-Host "[boot_test] -LeaveRunning: game stays up (pid $($proc.Id))"
} else {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
}

Write-Host "`n[boot_test] ---- BrnGame.log tail ----"
if (Test-Path $log) { Get-Content $log -Tail 80 } else { Write-Host "(no log written)" }
Write-Host "[boot_test] done. shots in $outPath"
