# radio_dj -- free roam plays the radio (an EA Trax song streamed and decoded) and DJ Atomika's
# free-burn voice-over is requested and played.
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case radio_dj
#
# GW4 PROOF, 2026-10-06. THE CHAINS (all in the tree, none proven live before this case):
#   MUSIC  MusicEffect::UpdateParams computes the music type each frame -> SelectSong picks a song
#          from the playlist masks -> MusicStream::Queue -> StreamingStateManager -> an RWAC
#          player-play with a SOUND\STREAMS\*.SNS path -> the stream decoder -> PCM.
#   DJ     TrainingManager::Update (free roam, not in Picture Paradise): once the profile's in-car
#          time since the last tip passes 600 s (console constant) and free burn has run 5 s,
#          PlayNewAtomikaFreeburnVO requests the next unseen tip 128..235 -> game action 148 ->
#          sound message 0x22 -> SpeechEffect::PlayFirstTimeTip's Atomika arm -> PlayStream ->
#          the stream -> SpeechEffect::UpdateVoiceParams ("VOICE PLAYING").
#
# BRN_AUDIO_MUTE (set by flow_run on every run) is ONE SetVolume(0) on the mastering voice
# (CgsAudioOutputPC.cpp): every decoder, stream and effect still runs, so this case measures the
# logic and the decoded PCM, not the speakers.
#
# WITNESSES:
#   [music] type a -> b / select song i/n type=t stream='<name>' ...       BRN_MUSIC_DIAG
#   [speech] RequestTraining type=<128..235> -> PlayNewAtomikaFreeburnVO picked   BRN_SPEECH_DIAG
#   [speech] freeburn-vo gate: sinceLastTip=.. need>600 freeBurnTime=..    BRN_SPEECH_DIAG (gate closed)
#   [speech] atomika-freeburn type=.. / play REQUESTED cs=.. / VOICE PLAYING cs=..   BRN_SPEECH_DIAG
#   BRN_SOUND_PCM_TRACE=<file> (upstream's read-only PCM attribution, CgsSoundPcmTrace.h):
#     wave-source player=<p> sample=<s> spec=<n> path=<SOUND\STREAMS\X.SNS | RAM>
#     wave-pcm player=<p> ... rms=<r> peak=<k>     (first non-silent decoded buffer of that player)
#   The trace file is written to scratch\gameplay_wave4\PROOF\radio_dj_pcm.txt (the game truncates
#   it at start) and the PCM check copies it into the run dir.
$lsPcmTrace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..\scratch\gameplay_wave4\PROOF\radio_dj_pcm.txt'))
@{
  Name    = 'radio_dj'
  Area    = 'audio/music'
  Bug     = 'GW4 proof -- the radio (EA Trax stream) and DJ Atomika speech had never been witnessed live'
  Frames  = $false
  Run     = @{
    Drive       = $true
    MotionProbe = $true
    MaxSeconds  = 85
    SkipIntro   = $true
    AcceptGap   = 1.0
    Teleport    = '3040.7,-5.8,-1937.9,180'   # the baseline road outside the junkyard exit
  }
  DiagEnv = ('BRN_MUSIC_DIAG=1,BRN_SPEECH_DIAG=1,BRN_SOUND_PCM_TRACE=' + $lsPcmTrace)
  PcmTrace = $lsPcmTrace
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }

    # ---- the radio ----
    @{ Kind = 'LogMatch';   Name = 'MusicEffect selected a song'; Pattern = '\[music\] select song \d+/\d+ ' }
    # At boot the type flips to 14 before the playlist masks exist (11x "the playlist masks are
    # empty" on every run so far, before the first "playlist masks updated"); once the masks are
    # published a selection must never come up empty.
    @{ Kind = 'Script';     Name = 'no NO SONG SELECTABLE once the playlist masks exist'; Script = {
        param($ctx)
        $liMasks = -1; $liBefore = 0; $liAfter = 0
        for ($i = 0; $i -lt $ctx.LogLines.Count; $i++) {
          $l = $ctx.LogLines[$i]
          if ($liMasks -lt 0 -and $l -match '\[music\]\s+playlist masks updated') { $liMasks = $i }
          elseif ($l -match '\[music\] NO SONG SELECTABLE') { if ($liMasks -lt 0) { $liBefore++ } else { $liAfter++ } }
        }
        if ($liMasks -lt 0) { return @{ Pass = $false; Detail = 'the playlist masks were never published' } }
        return @{ Pass = ($liAfter -eq 0); Detail = ("masks published at log line {0}; NO SONG SELECTABLE {1}x before (boot, info), {2}x after" -f ($liMasks + 1), $liBefore, $liAfter) }
      } }
    @{ Kind = 'Script';     Name = 'the selected EA Trax song streamed and decoded to non-silent PCM'; Script = {
        param($ctx)
        $lsTrace = $ctx.Case.PcmTrace
        $lsLocal = Join-Path $ctx.RunDir 'pcm_trace.txt'
        if ((Test-Path $lsTrace) -and -not (Test-Path $lsLocal)) {
          $lRunStart = $null
          if ($ctx.MarksText -match 'RUNSTART (\S+)') { try { $lRunStart = [datetime]::Parse($Matches[1]) } catch { } }
          if ($null -eq $lRunStart -or (Get-Item $lsTrace).LastWriteTime -ge $lRunStart) { Copy-Item $lsTrace $lsLocal -Force }
        }
        if (-not (Test-Path $lsLocal)) { return @{ Pass = $false; Detail = "no PCM trace for this run ($lsTrace)" } }
        $lsSong = $null
        foreach ($l in $ctx.LogLines) { if ($l -match "\[music\] select song \d+/\d+ type=\d+ stream='(?<s>[^']+)'") { $lsSong = $Matches.s; break } }
        if (-not $lsSong) { return @{ Pass = $false; Detail = 'no [music] select song line' } }
        $lsFile = ($lsSong + '.SNS').ToUpperInvariant()
        $lPlayers = @{}
        $lsHit = ''
        foreach ($l in [IO.File]::ReadAllLines($lsLocal)) {
          if ($l -match '^wave-source player=(?<p>\S+) .* path=(?<f>\S+)\s*$') { if ($Matches.f.ToUpperInvariant() -eq $lsFile) { $lPlayers[$Matches.p] = 1 } }
          elseif ($l -match '^wave-pcm player=(?<p>\S+) .* rms=(?<r>[0-9.eE+-]+)' -and $lPlayers.ContainsKey($Matches.p)) {
            if ([double]::Parse($Matches.r, [Globalization.CultureInfo]::InvariantCulture) -gt 0) { $lsHit = $l.Trim(); break }
          }
        }
        return @{ Pass = [bool]$lsHit; Detail = ("song '{0}' -> {1}: {2}" -f $lsSong, $lsFile, $(if ($lsHit) { $lsHit } else { 'no non-silent wave-pcm for that stream' })) }
      } }

    # ---- the DJ ----
    @{ Kind = 'Script';     Name = 'DJ Atomika: a free-burn VO was picked, requested, voiced and decoded'; Script = {
        param($ctx)
        $lsPicked = $ctx.LogLines | Where-Object { $_ -match '\[speech\] RequestTraining type=(1(2[89]|[3-9]\d)|2([0-2]\d|3[0-5])) -> PlayNewAtomikaFreeburnVO picked' } | Select-Object -First 1
        $lsArm    = $ctx.LogLines | Where-Object { $_ -match '\[speech\] atomika-freeburn type=\d+ idx=\d+ items=\d+ valid=1' } | Select-Object -First 1
        $lsReq    = $ctx.LogLines | Where-Object { $_ -match '\[speech\] play REQUESTED cs=[1-9]\d* firsttimetip=1' } | Select-Object -First 1
        $lsVoice  = $ctx.LogLines | Where-Object { $_ -match '\[speech\] VOICE PLAYING cs=' } | Select-Object -First 1
        $lsGate   = $ctx.LogLines | Where-Object { $_ -match '\[speech\] freeburn-vo gate:' } | Select-Object -Last 1
        # The ContentSpec the speech effect requested is the wave-source spec of its stream.
        $lsPcm = ''
        $lsLocal = Join-Path $ctx.RunDir 'pcm_trace.txt'
        if ($lsReq -and $lsReq -match 'cs=(?<cs>\d+)' -and (Test-Path $lsLocal)) {
          $lsCs = $Matches.cs; $lPlayers = @{}; $lsPath = ''
          foreach ($l in [IO.File]::ReadAllLines($lsLocal)) {
            if ($l -match ('^wave-source player=(?<p>\S+) .* spec=' + $lsCs + ' path=(?<f>\S+)')) { $lPlayers[$Matches.p] = 1; $lsPath = $Matches.f }
            elseif ($l -match '^wave-pcm player=(?<p>\S+) .* rms=(?<r>[0-9.eE+-]+)' -and $lPlayers.ContainsKey($Matches.p)) {
              if ([double]::Parse($Matches.r, [Globalization.CultureInfo]::InvariantCulture) -gt 0) { $lsPcm = ("{0} rms={1}" -f $lsPath, $Matches.r); break }
            }
          }
        }
        $ok = [bool]$lsPicked -and [bool]$lsArm -and [bool]$lsReq -and [bool]$lsVoice -and [bool]$lsPcm
        $lsDetail = ("picked={0} atomikaArm={1} requested={2} voicePlaying={3} decoded={4}" -f [bool]$lsPicked, [bool]$lsArm, [bool]$lsReq, [bool]$lsVoice, $(if ($lsPcm) { $lsPcm } else { 'no' }))
        if ($lsPicked) { $lsDetail += '; ' + $lsPicked.Trim() }
        if (-not $lsPicked -and $lsGate) { $lsDetail += '; gate closed: ' + $lsGate.Trim() }
        return @{ Pass = $ok; Detail = $lsDetail }
      } }
    @{ Kind = 'LogCount';   Name = 'info: [speech] play DROPPED lines'; Pattern = '\[speech\] play DROPPED' }
  )
}
