# net_lan_pause_sound -- the Host opens the pause menu during an online LAN race; both halves capture
# their mixed audio so the "tac tac tac" the user hears on that menu can be measured, not guessed.
#
# Run it (a PAIR case; slots 1/2 clash with build\game_slots\1\config.ini's online server, so):
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_pair.ps1 -Case net_lan_pause_sound -SlotA 3 -SlotB 4
#
# THE STIMULUS. The same online race launch as net_lan_start_mode mode 10 (GUI 193 presets, GUI 257 on a
# preset route, GUI 54 launch). Then the Host's MenuScript waits for the OnlineRace mode-start and that
# mode's E_GMS_IN_PROGRESS, waits 5 s, taps Start (action 46, the pause menu), waits 8 s, taps Start again.
#
# THE MEASUREMENT. BRN_AUDIO_CAPTURE writes each half's submitted mix to
# scratch\audio\net_lan_pause_sound_<Role>.wav (before the harness mute, which only zeroes the mastering
# voice). tools\tests\audio_gating.py reads it and reports the level per 10 ms around the MenuScript marks.
# BRN_AEMS_DIAG adds the capped PresentationEffect Play / PlayStream / voice-state witnesses.
param([string]$Role = '')
. (Join-Path $PSScriptRoot '..\_net_pair_common.ps1')

$lsRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$lsAudioDir = Join-Path $lsRoot 'scratch\audio'
if (-not (Test-Path $lsAudioDir)) { New-Item -ItemType Directory -Force $lsAudioDir | Out-Null }

# BP_PAUSE_REVS=1: hold the throttle for 6 s first, so the car is still moving (and its engine
# winding down) under the menu -- an engine-borne flutter then changes period during the pause.
$lsRevs = if ($env:BP_PAUSE_REVS -eq '1') { 'hold:Accelerate:6;' } else { 'sleep:5;' }
$lsHostScript = 'timeout:300;wait:\[net\] mode-start mode=OnlineRace type=;wait:mode state -> E_GMS_IN_PROGRESS;' + $lsRevs + 'mark:pause;tap:Start;sleep:8;mark:unpause;tap:Start;sleep:5;mark:end'

$lPairRoles = [ordered]@{
  Host  = @{ Other = 'Guest'; Harness = 'BRN_NET_HOST=1,BRN_NET_START_MODE=25:10,BRN_NET_SCRIPT=10:gui:193:10;40:net:54'; MenuScript = $lsHostScript }
  Guest = @{ Other = 'Host';  Harness = 'BRN_NET_JOIN=1'; MenuScript = '' }
}

if ($Role -eq '') {
  return @{
    Name = 'net_lan_pause_sound'
    Area = 'audio'
    Bug  = 'the online race pause menu chops the sound ("tac tac tac")'
    Pair = @{ Roles = @($lPairRoles.Keys); Slots = @(1, 2) }
  }
}
if (-not $lPairRoles.Contains($Role)) { throw "net_lan_pause_sound: unknown -Role '$Role' (Host or Guest)" }
$lR = $lPairRoles[$Role]
$lsCapture = Join-Path $lsAudioDir "net_lan_pause_sound_$Role.wav"

# BP_AUDIO_BUFFERS=<n>: the XAudio2 queue depth for this run (BRN_AUDIO_BUFFERS, diagnostic).
$lsBuffers = if ($env:BP_AUDIO_BUFFERS) { ",BRN_AUDIO_BUFFERS=$($env:BP_AUDIO_BUFFERS)" } else { '' }
$lRun = @{ MaxSeconds = 260; TitleStart = $true; SkipIntro = $true; AcceptGap = 1.0; FrameEvery = 300 }
if ($lR.MenuScript) { $lRun.MenuScript = $lR.MenuScript }

@{
  Name    = "net_lan_pause_sound_$Role"
  Area    = 'audio'
  Bug     = "none -- the $Role half of net_lan_pause_sound (run it through tools\tests\run_pair.ps1)"
  Frames  = $true
  Run     = $lRun
  DiagEnv = "$($lR.Harness),BRN_NET_DELAY=20,BRN_SCREEN_DIAG=1,BRN_AEMS_DIAG=1,BRN_SOUNDLOGIC_DIAG=1,BRN_HUD_SOUND_DIAG=1,BRN_AUDIO_CAPTURE=$lsCapture$lsBuffers"
  Setup   = (& $NetPair.Setup $Role)
  Checks  = @(
    @{ Kind = 'LogCount'; Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';     Name = 'reached DRIVING'; Phase = 'DRIVING' }
  )
}
