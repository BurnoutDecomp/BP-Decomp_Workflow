# hud_visibility -- lane `hud`, bug-test wave 2026-09-06.
#
# BUG: "ingame HUD (not sure if visibility logic is faithful)". The console shows and
# hides each HUD element through a specific GUI-event chain; this build carries a
# SELECTIVE stand-in for part of it (the channel-41 bridge in BrnGuiModule.cpp), so an
# element can stay on screen when the console has hidden it, or never come back.
#
# WITNESS (opt-in, BRN_HUD_VIS=1):
#   [hud-vis] <element> show|hide|absent by <reason>   -- BrnCustomRenderer.cpp, printed
#       ONLY when a custom-render component's render-enabled flag CHANGES. <reason> is
#       `evt=<gui event id>` / `prepare` / `render`. Elements: netplayerimage, satnav
#       (the minimap), mainmap, crashnavicons, boostbar, abovecar, progressbar,
#       blackbar, ingamemessage (the ticker), creditstext.
#   [hud-vis] cmd 148 flag=0|1 ch=42                   -- BrnGuiModule.cpp, the
#       GuiEventShowHideHud command as it leaves the internal-state channel. flag=1 is
#       InGame::OnEnter (HUD up), flag=0 is OpenMainMap / OpenEventMap /
#       OpenDriverDetails / ShutDownHudComponents (HUD down). This is the PAUSE
#       BOUNDARY in the log.
#
# THE CONSOLE TABLE the checks below encode (X360 ARTIST):
#   junkyard / car select      minimap OFF, boost bar OFF   (FBurnMainHudState never ran
#                              its ENGINE_ON arm: UpdateWFInit @0x8247C710)
#   freeburn DRIVING           minimap ON,  boost bar ON    (UpdateWFInit engine-on arm:
#                              {12,213,...,show=1} + PostCommand16<214>(1))
#   main map / pause           minimap OFF, boost bar OFF   (InGame::OpenMainMap
#                              @0x824DA610 posts {1,148,12,0} -> FBurnMainHudState::
#                              UpdatePermenant case 148 -> "PAUSE" -> OnLeave
#                              @0x82480B88 posts the 213 hide + 214/215 = 0)
#   back out of the map        minimap ON,  boost bar ON    (InGame::OnEnter re-posts
#                              {1,148,12,1}, the HUD flow re-enters FBurnMain)
#   always, once prepared      black bar + ticker ENABLED   (CustomRendererManager::
#                              Prepare @0x82444140: SetAllRenderingState(false) then
#                              SetComponentRenderable(0/7/8, true))
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case hud_visibility -ExpectFail -Label pre-fix
#
# ⭐⭐ SHORTENED 2026-09-06 (lane harness2). WHAT CHANGED AND WHAT DID NOT.
#   The Run block below now carries `SkipIntro` and `AcceptGap`, and a smaller `MaxSeconds`.
#   Nothing else about the scenario moved and NO CHECK was touched.
#     SkipIntro  passes the CONSOLE's own "-skipvideos" command-line latch (BrnMain.cpp:434 ->
#                BootVideos::Update's soft-reboot exit) so the EA-Franchise and Criterion VP6
#                logos are not played. It is not a harness bypass and it is not new game code.
#     AcceptGap  is HARNESS latency, not a game gate: the Accept pump used to press every 3.0 s
#                at car select, and the junkyard leg of a returning boot was measurably two
#                consecutive pump periods long (carsel 16.5s -> livery 19.9s -> accept 23.0s).
#   MEASURED, same build, same scenario: boot-to-DRIVING 23.0 s -> 16.2 s.
#   MaxSeconds is cut by that saving plus the slack this case's own schedule shows it never used.
#   FLOOR: PauseAt 20 / UnpauseAt 32 are DRIVING-relative, so this case cannot be shorter than
#   boot(16) + DriveDelay(6) + 32 + a tail for the resume to be observed.
#
@{
  Name    = 'hud_visibility'
  Area    = 'gui'
  Bug     = 'ingame HUD -- is the show/hide logic faithful to the console?'
  Frames  = $false
  Run     = @{
    Drive       = $true
    MaxSeconds  = 60
    SkipIntro  = $true      # the console -skipvideos latch (see the banner)
    AcceptGap  = 1.0        # harness pump latency, not a game gate
    Teleport    = '3040.7,-5.8,-1937.9,180'
    PauseAt     = '20'
    PauseTarget = 'map'
    UnpauseAt   = '32'
  }
  DiagEnv = 'BRN_HUD_VIS=1'
  Checks  = @(
    # `Known` = the shared known_asserts.txt VERBATIM plus ONE pause-only family this case is
    # the only run in the wave to reach (the sound lane's CgsVoice.cpp:334 voice detach). See
    # the header of that file for why it is a copy and not an edit of the shared list.
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families';
       Known = 'C:\Users\Niaz\burnout-pr\BP-Decomp_Workflow\tools\tests\known_asserts_hud.txt' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }

    @{ Kind = 'LogMatch';   Name = 'the [hud-vis] witness ran'; Pattern = '\[hud-vis\] ' }
    @{ Kind = 'LogMatch';   Name = 'the HUD-down command was issued (the pause happened)';
       Pattern = '\[hud-vis\] cmd 148 flag=0' }
    @{ Kind = 'LogMatch';   Name = 'the channel-41 witness ran'; Pattern = '\[hud-vis\] ch41 type=' }

    # The console's channel-41 arm -- EventInterpreterModule::ProcessOutEvents @0x8285E1D0
    # case ')' -- forwards EVERY record to the view queue:
    #     AddEvent(viewQueue, record + record[2], record[1], record[0]);
    # There is no id filter in the binary. A record this build drops never reaches
    # ViewModule::ProcessIncomingViewEvents @0x8285FCE8, whose per-event tail forward
    # (`if (*v10) (*(**v10 + 16))(*v10, v8, v9)`) is the ONLY way a GUI state's view-state
    # record reaches BrnGui::CustomRendererManager::RecvEvent -- so the HUD element that
    # record controls never changes state at all.
    @{ Kind = 'LogCount';   Name = 'no channel-41 record is dropped (console: no id filter)';
       Pattern = '\[hud-vis\] ch41 .*bridged=0'; Max = 0 }

    # ...and being on the view queue is only half of it. ViewModule::ProcessIncomingViewEvents
    # @0x8285FCE8 ends its loop body with `if (*v10) (*(**v10 + 16))(*v10, v8, v9)` -- EVERY
    # view event, handled or not, goes to the manager's virtual RecvEvent. These two ids are
    # the ones the pre-fix build dropped, and each drives a HUD element:
    #   258 GuiEventNetworkPlayerImage  -> slot 0 NetworkPlayerImageRenderer (the licence photo)
    #   559 GuiEventSetHoveredEventIcon -> slot 3 CrashNavIconRenderer (the hovered map icon)
    @{ Kind = 'LogMatch'; Name = 'player-image record 258 reaches the custom-renderer manager';
       Pattern = '\[hud-vis\] view->mgr type=258' }
    @{ Kind = 'LogMatch'; Name = 'hovered-icon record 559 reaches the custom-renderer manager';
       Pattern = '\[hud-vis\] view->mgr type=559' }

    @{ Kind = 'Script'; Name = 'HUD element visibility matches the console table'; Script = {
        param($ctx)

        $ev = @()
        foreach ($l in $ctx.LogLines) {
          if ($l -match '\[hud-vis\] cmd 148 flag=(?<f>[01])') {
            $ev += ,@{ K = 'cmd'; F = [int]$Matches.f; L = $l.Trim() }
          } elseif ($l -match '\[hud-vis\] (?<e>\w+) (?<s>show|hide|absent) by (?<r>\S+)') {
            $ev += ,@{ K = 'vis'; E = $Matches.e; S = $Matches.s; R = $Matches.r; L = $l.Trim() }
          }
        }
        if ($ev.Count -eq 0) {
          return @{ Pass = $false; Detail = 'no [hud-vis] lines -- the witness never ran (BRN_HUD_VIS not reaching the game?)' }
        }

        # Phase boundaries, anchored from the END of the stream. The boot path posts several
        # 148 pairs of its own before the car is driving (InGame::OnEnter's flag=1 and the
        # junkyard-exit ShutDownHudComponents flag=0 -- measured 4 commands before the pause on
        # run 20260906_104450), so "the first flag=0" is NOT the pause. The scenario taps the
        # pause once and unpauses once, so the pause cycle is always the LAST one in the log:
        #   on2 = the last  flag=1                 -- back out of the map
        #   off = the last  flag=0 before on2      -- InGame::OpenMainMap, the pause
        #   on1 = the last  flag=1 before off      -- the HUD-up the drive is running under
        $on1 = -1; $off = -1; $on2 = -1
        for ($i = $ev.Count - 1; $i -ge 0; $i--) {
          if ($ev[$i].K -ne 'cmd') { continue }
          if ($on2 -lt 0) { if ($ev[$i].F -eq 1) { $on2 = $i }; continue }
          if ($off -lt 0) { if ($ev[$i].F -eq 0) { $off = $i }; continue }
          if ($on1 -lt 0) { if ($ev[$i].F -eq 1) { $on1 = $i }; break }
        }
        # ...and the FIRST flag=1, which is InGame::OnEnter on the junkyard-exit path: nothing
        # HUD-ish may be on screen before it (car select / livery / the junkyard).
        $boot1 = -1
        for ($i = 0; $i -lt $ev.Count; $i++) {
          if ($ev[$i].K -eq 'cmd' -and $ev[$i].F -eq 1) { $boot1 = $i; break }
        }

        $stateAt = {
          param($stream, $elem, $upto)
          $s = 'hide'
          for ($i = 0; $i -lt $stream.Count -and $i -le $upto; $i++) {
            if ($stream[$i].K -eq 'vis' -and $stream[$i].E -eq $elem) {
              if ($stream[$i].S -eq 'absent') { return 'absent' }
              $s = $stream[$i].S
            }
          }
          return $s
        }
        $reachedIn = {
          param($stream, $elem, $a, $b, $want)
          for ($i = [Math]::Max(0, $a); $i -le $b -and $i -lt $stream.Count; $i++) {
            if ($stream[$i].K -eq 'vis' -and $stream[$i].E -eq $elem -and $stream[$i].S -eq $want) { return $true }
          }
          return $false
        }

        $fail = @()
        $note = @()

        if ($on1 -lt 0) { $fail += 'no "[hud-vis] cmd 148 flag=1" -- the in-game HUD was never requested' }
        if ($off -lt 0) { $fail += 'no "[hud-vis] cmd 148 flag=0" after the HUD came up -- the pause never reached the GUI' }

        if ($boot1 -ge 0) {
          foreach ($e in @('satnav','boostbar','mainmap','crashnavicons')) {
            $s = & $stateAt $ev $e ($boot1 - 1)
            if ($s -eq 'show') { $fail += ('car-select: ' + $e + ' is SHOW before the first HUD-up command (console: hidden)') }
            else { $note += ('carsel ' + $e + '=' + $s) }
          }
        }

        if ($on1 -ge 0 -and $off -ge 0) {
          foreach ($e in @('satnav','boostbar')) {
            $s = & $stateAt $ev $e ($off - 1)
            if ($s -ne 'show') { $fail += ('driving: ' + $e + ' is ' + $s + ' just before the pause (console: show)') }
            else { $note += ('drive ' + $e + '=show') }
          }
        }

        if ($off -ge 0) {
          $end = $(if ($on2 -ge 0) { $on2 } else { $ev.Count - 1 })
          foreach ($e in @('satnav','boostbar')) {
            if (-not (& $reachedIn $ev $e $off $end 'hide')) {
              $fail += ('pause: ' + $e + ' never went HIDE after the HUD-down command (console: FBurnMainHudState::OnLeave hides it)')
            } else { $note += ('pause ' + $e + '=hide') }
          }
          # ...and the map screen itself comes up in their place: CrashNavMap::CheckForLoadComplete
          # posts GuiEventShowHideSatNav(E_MAPTYPE_MAIN, show) -> RecvEvent case 213 sub-mode 0
          # enables slot 2 (MainMap) and mirrors the resolved enable onto slot 3 (CrashNavIcons).
          foreach ($e in @('mainmap','crashnavicons')) {
            if (-not (& $reachedIn $ev $e $off $end 'show')) {
              $fail += ('pause: ' + $e + ' never went SHOW with the main map open (console: the 213 MAIN arm enables slots 2+3)')
            } else { $note += ('pause ' + $e + '=show') }
          }
        }

        if ($on2 -ge 0) {
          foreach ($e in @('mainmap','crashnavicons')) {
            if (-not (& $reachedIn $ev $e $on2 ($ev.Count - 1) 'hide')) {
              $fail += ('unpause: ' + $e + ' never went HIDE again after the map was closed')
            } else { $note += ('unpause ' + $e + '=hide') }
          }
          foreach ($e in @('satnav','boostbar')) {
            if (-not (& $reachedIn $ev $e $on2 ($ev.Count - 1) 'show')) {
              $fail += ('unpause: ' + $e + ' never went SHOW again after the HUD-up command (console: the HUD flow re-enters FBurnMain)')
            } else { $note += ('unpause ' + $e + '=show') }
          }
        } elseif ($off -ge 0) {
          $fail += 'no second "[hud-vis] cmd 148 flag=1" -- the HUD was never asked back after the map'
        }

        foreach ($e in @('blackbar','ingamemessage')) {
          $s = & $stateAt $ev $e ($ev.Count - 1)
          if ($s -eq 'absent') { $note += ($e + ' absent (component not embedded)') }
          elseif ($s -ne 'show') { $fail += ($e + ' ends ' + $s + ' (console: Prepare enables it and nothing disables it)') }
          else { $note += ($e + '=show') }
        }

        $detail = ($note -join '; ')
        if ($fail.Count -gt 0) { $detail = ($fail -join ' | ') + '  [seen: ' + $detail + ']' }
        return @{ Pass = ($fail.Count -eq 0); Detail = $detail }
      } }
  )
}
