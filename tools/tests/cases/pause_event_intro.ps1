# pause_event_intro -- BurnoutDecomp/b5-decomp#29 "Pausing during event intro": START must not pause
# the game during an event's intro fly-by or its countdown, and must pause it once the race runs.
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case pause_event_intro
#
# GW4 PROOF, 2026-10-06. THE CONSOLE GATE: START (GUI action 45) reaches InGame::HandleControllerInput
# -> PauseGame(true, true) -> PauseAllowed (BrnInGame.cpp), which refuses while any of five GuiCache
# bytes is up: +0xA014 mbEventPreparedForModeStart (GUI 93 sets it, GUI 237 GuiGameModeStarted and
# 322 clear it), +0x4B59 mugshot, +0x13B90 loading screen, +0xA015 mbIsPreRaceFlyByActive
# (PreRaceFlyByState OnEnter sets, OnLeave clears), +0x4B57 junkyard. 237 is posted from action 34
# (E_ACTION_START_PLAYING_MODE), which ModeManager::StartPlayingMode posts at the timer-start latch,
# i.e. at the countdown GO. So: the fly-by is covered by +0xA015 AND +0xA014, the countdown after the
# fly-by leaves by +0xA014 alone, and after GO nothing blocks.
#
# THE SCENARIO (race_lifecycle's junction 480852, race mode 0): teleport to the grid, -StartEvent,
# hold the throttle. A CUE-GATED -MenuScript taps START (each tap is a real GUI action 45 through
# the harness pad channel):
#   window FLYBY      2 s after "PreRaceFlyBy is calling SetOwnerParameters" (fly-by OnEnter), x2
#   window COUNTDOWN  at "mode state -> E_GMS_COUNTDOWN" (+0.3 s), and right after the fly-by's
#                     "PreRaceFlyBy is calling ReleaseResources" (OnLeave), before GO
#   window CONTROL    4 s after "mode state -> E_GMS_IN_PROGRESS": the POSITIVE CONTROL -- the same
#                     tap must pause here, or the case proves nothing about the two windows above
#   then STOP to come back out.
# Each MENUSCRIPT step in marks.txt carries `(log line <n>)` (flow_run, GW4 PROOF), so a pause line
# in BrnGame.log is attributed to the window whose mark precedes it.
#
# PAUSE WITNESSES (always on): `[sim-pause] action 86 -> PAUSED` (the world stopped) and
# `[ddetails] internal state -> <n>` (CrashNavDriverDetails, the START pause screen, ran). Info only:
# `[hud-vis] cmd 148 flag=0` (BRN_HUD_VIS; the event flow posts its own HUD-down commands too).
@{
  Name    = 'pause_event_intro'
  Area    = 'gui/pause'
  Bug     = 'BurnoutDecomp/b5-decomp#29 -- the pause menu could be brought up during an event intro'
  Frames  = $false
  Run     = @{
    Drive           = $true
    Teleport        = '762.2,0.7,-2235.5,259'
    StartEvent      = $true
    EventFsm        = $true
    SkipTrainingTip = $true
    SkipIntro       = $true
    AcceptGap       = 1.0
    ThrottleScript  = '0:accel'
    MaxSeconds      = 85
    MenuScript      = 'timeout:60;wait:PreRaceFlyBy is calling SetOwnerParameters;sleep:2;mark:flyby;tap:Start;sleep:1.5;tap:Start;wait:mode state -> E_GMS_COUNTDOWN;sleep:0.3;mark:countdown;tap:Start;wait:PreRaceFlyBy is calling ReleaseResources;tap:Start;wait:mode state -> E_GMS_IN_PROGRESS;sleep:4;mark:control;tap:Start;sleep:5;mark:unpause;tap:Stop;sleep:2;mark:end'
  }
  DiagEnv = 'BRN_HUD_VIS=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'LogMatch';   Name = 'the event intro ran (mode state -> E_GMS_INTRO)'; Pattern = '\[stunt\] mode state -> E_GMS_INTRO' }
    @{ Kind = 'Script';     Name = 'the menu script reached the end (every window was tapped)'; Script = {
        param($ctx)
        if ($ctx.MarksText -match 'MENUSCRIPT done=(\d+)/(\d+) state=(\S+)') {
          return @{ Pass = ($Matches[1] -eq $Matches[2]); Detail = $Matches[0].Trim() }
        }
        return @{ Pass = $false; Detail = 'marks.txt has no MENUSCRIPT summary line' }
      } }
    @{ Kind = 'Script';     Name = '#29: no pause during the fly-by or the countdown; START pauses after GO'; Script = {
        param($ctx)
        $lMark = @{}
        foreach ($l in ($ctx.MarksText -split "`n")) {
          if ($l -match 'MENUSCRIPT run=\s*[\d.,]+s step \d+ mark (?<m>\w+) \(log line (?<n>\d+)\)') { $lMark[$Matches.m] = [int]$Matches.n }
        }
        foreach ($k in @('flyby','countdown','control','unpause')) {
          if (-not $lMark.ContainsKey($k)) { return @{ Pass = $false; Detail = "no MENUSCRIPT mark '$k' with a log line (script stalled, or flow_run predates the log-line stamp)" } }
        }
        $lCount = @{ flyby = 0; countdown = 0; control = 0 }
        $lFirst = @{ flyby = ''; countdown = ''; control = '' }
        for ($i = 0; $i -lt $ctx.LogLines.Count; $i++) {
          $l = $ctx.LogLines[$i]
          if ($l -notmatch '\[sim-pause\] action 86 -> PAUSED|\[ddetails\] internal state -> ') { continue }
          $n = $i + 1
          $w = $null
          if     ($n -gt $lMark.flyby -and $n -le $lMark.countdown) { $w = 'flyby' }
          elseif ($n -gt $lMark.countdown -and $n -le $lMark.control) { $w = 'countdown' }
          elseif ($n -gt $lMark.control -and $n -le $lMark.unpause) { $w = 'control' }
          if ($w) { $lCount[$w]++; if (-not $lFirst[$w]) { $lFirst[$w] = ("line {0}: {1}" -f $n, $l.Trim()) } }
        }
        $ok = ($lCount.flyby -eq 0) -and ($lCount.countdown -eq 0) -and ($lCount.control -gt 0)
        $lsDetail = ("pause lines: flyby={0} countdown={1} control={2} (marks at log lines {3}/{4}/{5}/{6})" -f `
                     $lCount.flyby, $lCount.countdown, $lCount.control, $lMark.flyby, $lMark.countdown, $lMark.control, $lMark.unpause)
        foreach ($w in @('flyby','countdown','control')) { if ($lFirst[$w]) { $lsDetail += ("; first {0}: {1}" -f $w, $lFirst[$w]) } }
        if ($lCount.control -eq 0) { $lsDetail += '; CONTROL FAILED: START never paused even after GO, so this run cannot judge the two intro windows' }
        return @{ Pass = $ok; Detail = $lsDetail }
      } }
    @{ Kind = 'LogCount';   Name = 'info: HUD-down commands (event flow + any pause)'; Pattern = '\[hud-vis\] cmd 148 flag=0' }
  )
}
