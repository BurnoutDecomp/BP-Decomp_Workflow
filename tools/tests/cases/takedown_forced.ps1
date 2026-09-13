# takedown_forced -- ONE TAKEDOWN, END TO END, ON A SCRIPTED DRIVE.
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case takedown_forced
#
# THE CHAIN this case measures, link by link (each link has its own check below):
#   1. GameStateModule::PreWorldUpdate arms the harness knob BRN_FORCE_TAKEDOWN=<seconds>: once the
#      current mode has been IN_PROGRESS that long it runs the console's own "Force takedown" debug
#      action (TakedownManagerDebugComponent::ForceTakedownCallback -- aggressor car 0, victim
#      car 1, STANDARD), which arms maRaceCarData[0].mbWaitingOnTakedown.
#   2. TakedownManager::Update's victim-crash sweep confirms that pending event (victim active, not
#      crashing, above the minimum takedown speed) and calls ProcessTakedownEvent, which
#        a. posts the takedown camera (game action E_ACTION_SET_TAKEDOWN_CAMERA_STATE) when the
#           player is the aggressor in an offline mode,
#        b. posts E_ACTION_ON_PLAYER_TAKEDOWN for the AI module, and
#        c. appends the TakedownEvent to the output buffer's takedown queue -- ONLY while a game
#           mode is running, which is why this case starts an event rather than free-burning.
#   3. GameStateModule::ProcessTakedownEvents scores it (rival tally / training tip / telemetry).
#   4. The director's arbitrator hands the frame to E_STATE_TAKEDOWN (container state 3) -- the
#      takedown camera.
#
# THE SPOT. Teleport is the road outside the junkyard exit, which is the Road Rage junction 480861;
# -StartEvent starts that event so a mode is IN_PROGRESS and rivals exist to be taken down.
#
# THE WITNESSES (all real tags in the tree; none is per-frame):
#   [td] HARNESS force-takedown fired (car 0 -> car 1)      GameStateModule_gTD_00.cpp (BRN_FORCE_TAKEDOWN)
#   [td] <n> takedown event(s) this frame                   the same file, once per frame the queue is non-empty
#   [ai-evt] action 14 ON_PLAYER_TAKEDOWN                   BrnAIModule_Events.cpp, first 8 only
#   [crashcam] container current state -> 3 (...)           ArbitratorStateContainer::SetCurrentState (BRN_CRASHCAM_DIAG)
#   [UI-gate] hud message sent n=<len>                      BrnGuiHudMessageDirector_gUI_01.cpp (BRN_PROP_DIAG)
#
# flow_run wipes BRN_* out of the environment, so DiagEnv below is the only way to set either knob.
@{
  Name    = 'takedown_forced'
  Area    = 'takedown'
  Bug     = 'takedown: prove one takedown end to end -- forced event -> classified -> counted -> GUI/HUD -> takedown camera state -> AI'
  Frames  = $false
  Run     = @{
    Drive           = $true
    MotionProbe     = $true
    SkipIntro       = $true      # the console -skipvideos latch
    AcceptGap       = 1.0        # harness pump latency, not a game gate
    Teleport        = '3040.7,-5.8,-1937.9,180'   # the road outside the junkyard exit == Road Rage junction 480861
    StartEvent      = $true
    EventFsm        = $true
    SkipTrainingTip = $true
    MaxSeconds      = 120        # boot + junkyard + event start + the 12 s force delay + the camera
  }
  DiagEnv = 'BRN_FORCE_TAKEDOWN=12,BRN_CRASHCAM_DIAG=1,BRN_PROP_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }

    # LINK 1 -- the harness actually pulled the trigger (a mode was IN_PROGRESS for 12 s).
    @{ Kind = 'LogMatch';   Name = 'forced takedown was posted'
       Pattern = '\[td\] HARNESS force-takedown fired'; Expect = $true }

    # LINK 2c/3 -- THE TAKEDOWN WAS DETECTED AND COUNTED: the pending event survived the
    # confirmation sweep, reached the output takedown queue and was drained by
    # ProcessTakedownEvents. The witness prints the queue length, so >= 1 is the detection.
    @{ Kind = 'LogValue';   Name = 'a takedown was detected and counted'
       Pattern = '\[td\] (?<n>\d+) takedown event\(s\) this frame'; Group = 'n'; Agg = 'max'; Min = 1 }

    # LINK 3b -- THE GUI/HUD LEG (added this wave, with the GUI call site).
    # There is NO log tag on the takedown GUI-event path itself: neither the producer
    # (BrnGameModule::TranslateTakedownsToGuiEvents, which pushes GUI event 363/364) nor the
    # consumer (HudMessageAnalyzer::Update case 363 -> HandleTakedown ->
    # ConstructTakedownMessage -> TriggerMessage) prints anything. The witness that CAN be
    # scored is the console's own, one rung downstream and NOT behind a BRN_ knob:
    # InGameMessagesComponent::StartMessage prints
    #   HUD MSGS : STARTING MESSAGE NAMED "<ID>"
    # with the id un-compressed (so upper-case: "GameWrecked" logs as "GAMEWRECKED "). Every
    # takedown line HandleTakedown can raise is in one of these families (BrnGuiHudMessageAnalyzer
    # _wB_res.cpp): TDGd* (the type + chain tables, incl. TDGdShutD), TDBdGeneral, DTGotScalp,
    # DTScalped, AggDr* and the Pbk*Dn payback lines. Naming them is what makes this a takedown
    # witness rather than "some hud message happened" -- a bare "a message was published"
    # check passes on GAMEWRECKED and STUNTPARTJMP, which is exactly how the first cut of this
    # check went green on a run where the takedown never reached the HUD at all.
    # The [UI-gate] publish counter (BRN_PROP_DIAG, BrnGuiHudMessageDirector_gUI_01.cpp) is
    # carried only as the DENOMINATOR in the failure detail: it says whether the hud message
    # path was alive at all, which separates "the takedown leg is broken" from "the whole HUD
    # message path is dead".
    @{ Kind = 'Script'; Name = 'the takedown reached the HUD message path (a takedown hud message started)'
       Script = {
         param($ctx)
         $laLines  = $ctx.LogLines
         $lsTdRe   = 'HUD MSGS : STARTING MESSAGE NAMED "(TDGD|TDBD|DTGOTSCALP|DTSCALPED|AGGDR|PBKGD|PBKBD)'
         $laTd     = @($laLines | Where-Object { $_ -match $lsTdRe })
         $laAny    = @($laLines | Where-Object { $_ -match 'HUD MSGS : STARTING MESSAGE NAMED' })
         $laSent   = @($laLines | Where-Object { $_ -match '\[UI-gate\] hud message sent' })
         $lsMissing = @($laLines | Where-Object { $_ -match 'Unable to find message : (TDGd|TDBd|DTGot|DTScalped|AggDr|Pbk)' }) -join ' | '
         if ($laTd.Count -gt 0) {
           return @{ Pass = $true; Detail = ("{0} takedown hud message(s) started; first: {1}" -f $laTd.Count, "$($laTd[0])".Trim()) }
         }
         $lsWhat = if ($laAny.Count -gt 0) { ($laAny | ForEach-Object { "$_".Trim() }) -join ' | ' } else { '(none)' }
         $lsWhy = if ($lsMissing) {
           'the message was built but the director REJECTED its id: ' + $lsMissing
         } elseif ($laSent.Count -eq 0) {
           'and NO hud message was published at all ([UI-gate] count 0) -- the whole hud message path is dead, not just the takedown leg (or BRN_PROP_DIAG is unset)'
         } else {
           ("and the hud message path IS alive ({0} [UI-gate] publish(es)) -- so the takedown specifically never built a message: either GUI event 363 was never produced/dispatched, or HandleTakedown parked it (mbTakedownMessagePending) waiting for the crash-bar START_TAKEDOWN event that only the takedown camera state posts" -f $laSent.Count)
         }
         return @{ Pass = $false; Detail = ("no takedown hud message started; messages that did start: {0} -- {1}" -f $lsWhat, $lsWhy) }
       } }

    # LINK 2b -- the world/AI side saw it (OnPlayerTakedown; player is the aggressor).
    @{ Kind = 'LogMatch';   Name = 'the AI module received ON_PLAYER_TAKEDOWN'
       Pattern = '\[ai-evt\] action 14 ON_PLAYER_TAKEDOWN'; Expect = $true }

    # LINK 4 -- THE TAKEDOWN CAMERA STATE WAS ENTERED. Container EState 3 == E_STATE_TAKEDOWN
    # (BrnDirectorArbitratorStateContainer.h), the state ArbStateRoaming hands off to on
    # GameState::mbTakedownActive.
    @{ Kind = 'LogMatch';   Name = 'arbitrator entered the takedown camera state (EState 3)'
       Pattern = '\[crashcam\] container current state -> 3\b'; Expect = $true }

    # The takedown camera must not be a one-way door: whatever state the container ends in, the
    # run must still be DRIVING at the end (the Mark check above) -- recorded here as the count of
    # state switches, which is 0 only if SetCurrentState never ran at all (a dead arbitrator).
    @{ Kind = 'LogCount';   Name = 'the arbitrator switched state at least once'
       Pattern = '\[crashcam\] container current state ->'; Min = 1 }
  )
}
