# trophy_car_screen -- gameplay wave GW2 (2026-09-28), lane TROPHY.
#
# The trophy car award screen (screen-flow state TRPHY_UNLOCK, BrnGui::OfflineTrophyCarUnlock)
# was a header-only shell: InGame could send "TO_TRPHY_UNL", but nothing in the state loaded the
# "BrnTrophyCarUnlock" movie or ever sent ADVANCE. This case drives the whole chain once:
#
#   BRN_PROGRESSION_COMPLETION_SEEDTROPHY=freeroam (the opt-in stimulus progression_completion.ps1
#   also uses, in its delayed mode) appends ONE TrophyUnlockAction (CARBEAGT, NUM_MEDELS) once the
#   player car has been active outside the junkyard for 8 s of sim time ->
#   ProgressionManager::SendTrophyUnlockUpdate posts game action 204 -> the translator raises
#   GUI 375 (GuiEventTrophyCarUnlock) -> GuiCache latches the type + car (RecEvent case 375) ->
#   InGame arms its 3.5 s countdown and, outside a game mode, sends "TO_TRPHY_UNL" ->
#   OfflineTrophyCarUnlock: enter -> movie 225 -> ... -> ADVANCE -> leave.
#
# Witnesses (both opt-in, bounded):
#   [race-flow] action 204 -> gui 375 ...     BRN_RACEFLOW_DIAG (the translator arm)
#   [trophy] screen enter|movie|advance|leave BRN_TROPHY_DIAG   (the state's own steps)
#
# DEPENDENCY: the screen reads GuiCache::GetTrophyCarID(), whose member + RecEvent case 375 are
# a request to the GuiCache owner. Without them the car id is 0 and the "kCGSID_NULL !=
# mTrophyCarID" assert shows up as a NEW assert family (the first check goes RED).
#
# WHY THE DELAY: GUI 375 reaches InGame only while the screen flow's INGAME state is live and
# observing it. With the seed on the first PreWorldUpdate (value 1) the 375 was raised before
# FSM\BRNSCREENFSM.BUNDLE had even loaded, so the event had no observer and was dropped (run
# 20260928_113506: 375 at line 1338, the screen FSM bundle at 1362, then junkyard car select).
# On the console a trophy car is awarded while driving, so InGame is live when 375 arrives.
#
# The screen's OnLeave marks the unlock sequence seen on the profile, so the run uses a pinned
# fixture profile and never touches the slot's own Profile.sav.
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case trophy_car_screen
@{
  Name           = 'trophy_car_screen'
  Area           = 'gui'
  Bug            = 'trophy car award screen (TRPHY_UNLOCK) was a shell: never loaded its movie, never ADVANCEd'
  Frames         = $false
  ProfileFixture = 'rival_hunt_profile.sav'
  Run            = @{
    Drive       = $true
    MaxSeconds  = 80    # seed ~8 s after the junkyard exit, 3.5 s countdown, ~8 s of screen
    SkipIntro   = $true
    AcceptGap   = 1.0
    Teleport    = '3040.7,-5.8,-1937.9,180'   # the road outside the junkyard exit (baseline's)
  }
  DiagEnv = 'BRN_PROGRESSION_COMPLETION_SEEDTROPHY=freeroam,BRN_RACEFLOW_DIAG=1,BRN_TROPHY_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families (incl. "kCGSID_NULL != mTrophyCarID")' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }

    # LINK 0 -- the stimulus waited for free roam (after the junkyard car select finished).
    @{ Kind = 'LogMatch';   Name = 'the trophy seed fired in its free-roam mode'
       Pattern = '\[completion\] HARNESS STIMULUS \(BRN_PROGRESSION_COMPLETION_SEEDTROPHY=freeroam\)' }
    @{ Kind = 'Script'; Name = 'the seed fired after the junkyard exit finished'
       Script = {
         param($ctx)
         $la = $ctx.LogLines
         $liExit = -1; $liSeed = -1
         for ($i = 0; $i -lt $la.Count; $i++) {
           if ($liExit -lt 0 -and $la[$i] -match 'CarSelectManager: Exit state is finished') { $liExit = $i }
           if ($liSeed -lt 0 -and $la[$i] -match '\[completion\] HARNESS STIMULUS') { $liSeed = $i }
         }
         if ($liSeed -lt 0) { return @{ Pass = $false; Detail = "seed never fired; exit@$liExit" } }
         if ($liExit -lt 0) { return @{ Pass = $false; Detail = "no junkyard exit line (message filter off?); seed@$liSeed" } }
         return @{ Pass = ($liExit -lt $liSeed); Detail = "exit@$liExit seed@$liSeed" }
       } }

    # LINK 1 -- the seeded trophy left the progression queue as GUI 375.
    @{ Kind = 'LogMatch';   Name = 'action 204 -> GUI 375 (GuiEventTrophyCarUnlock) was raised'
       Pattern = '\[race-flow\] action 204 -> gui 375' }

    # LINK 2 -- InGame's countdown ran out and the screen flow entered TRPHY_UNLOCK.
    @{ Kind = 'LogMatch';   Name = 'OfflineTrophyCarUnlock::OnEnter ran'
       Pattern = '\[trophy\] screen enter' }

    # LINK 3 -- the cache arrived, the four apt banks + the car loaded, the movie started.
    @{ Kind = 'LogMatch';   Name = 'the BrnTrophyCarUnlock movie (resource 225) was played'
       Pattern = '\[trophy\] screen movie 225' }

    # LINK 4 -- the presentation ran to TRANSOUT_COMPLETE and sent ADVANCE, then left.
    @{ Kind = 'LogMatch';   Name = 'the screen sent ADVANCE'
       Pattern = '\[trophy\] screen advance' }
    @{ Kind = 'LogMatch';   Name = 'OfflineTrophyCarUnlock::OnLeave ran'
       Pattern = '\[trophy\] screen leave' }

    # The four links in order, and the screen entered exactly once.
    @{ Kind = 'Script'; Name = '375 -> enter -> movie -> advance -> leave, one entry'
       Script = {
         param($ctx)
         $la = $ctx.LogLines
         $li375 = -1; $liEnter = -1; $liMovie = -1; $liAdvance = -1; $liLeave = -1; $liEnters = 0
         for ($i = 0; $i -lt $la.Count; $i++) {
           $l = $la[$i]
           if ($li375 -lt 0 -and $l -match '\[race-flow\] action 204 -> gui 375') { $li375 = $i }
           if ($l -match '\[trophy\] screen enter') { $liEnters++; if ($liEnter -lt 0) { $liEnter = $i } }
           if ($liMovie -lt 0 -and $l -match '\[trophy\] screen movie 225') { $liMovie = $i }
           if ($liAdvance -lt 0 -and $l -match '\[trophy\] screen advance') { $liAdvance = $i }
           if ($liLeave -lt 0 -and $l -match '\[trophy\] screen leave') { $liLeave = $i }
         }
         $lsWhere = "375@$li375 enter@$liEnter movie@$liMovie advance@$liAdvance leave@$liLeave enters=$liEnters"
         if ($li375 -lt 0)   { return @{ Pass = $false; Detail = "GUI 375 never raised; $lsWhere" } }
         if ($liEnter -lt 0) { return @{ Pass = $false; Detail = "375 raised but the screen was never entered (InGame countdown?); $lsWhere" } }
         if (-not ($li375 -lt $liEnter -and $liEnter -lt $liMovie -and $liMovie -lt $liAdvance -and $liAdvance -lt $liLeave)) {
           return @{ Pass = $false; Detail = "out of order or incomplete; $lsWhere" }
         }
         if ($liEnters -ne 1) { return @{ Pass = $false; Detail = "screen entered $liEnters times; $lsWhere" } }
         return @{ Pass = $true; Detail = $lsWhere }
       } }
  )
}
