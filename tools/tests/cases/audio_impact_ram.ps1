# audio_impact_ram -- lane SND (gameplay wave GW). Crashes had no impact sounds: the sound logic
# module never read the world -> sound game-event queue, so game event 31 (VehicleImpactEvent)
# never became sound message 19. SoundLogicModule::Update now runs ProcessGameEventQueue and
# ProcessCameraFlags in the console's order.
#
# Run it:  powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case audio_impact_ram
#
# WHO POSTS GAME EVENT 31. Two producers, both race car vs race car:
#   * VehicleManager::HandleRaceCarRaceCarContact posts it OFFLINE, once per contact the
#     classifier ladder (CheckForAllTypesOfImpacts) gives a type other than NONE, when the PLAYER
#     is one of the two cars, neither car is crashing after the verdict, and the player car is
#     still player-driven. This is the producer this case reaches.
#   * VehicleManager::UpdateVehicleImpacts posts it from the vehicle INPUT interface's impact
#     queue, whose only writer is NetworkAggressiveDrivingManager::HandleReceivingMessages: it is
#     the online victim's copy of an impact a network car inflicted. Not reachable offline.
# A ram on TRAFFIC (the old traffic_soak_ram scenario this case used) can never post it: traffic
# contacts are not race-car contacts.
#
# THE SCENARIO is takedown_forced's rival scrum WITHOUT the forced takedown: the road outside the
# junkyard exit (Road Rage junction 480861), -StartEvent starts the event, the player holds the
# throttle, and the rivals catch the player and shunt / slam it. Across the takedown_forced runs of
# 2026-09-20..28 about two thirds carried at least one classified player verdict inside the first
# 16 `[td-contact] verdict` lines (BRN_CRASHCAM_DIAG, capped), mostly `shunt(4)` with a rival as
# aggressor. The run is longer than takedown_forced's to give the scrum more contacts; 3 of 3
# runs on 2026-09-28 posted event 31 (5, 1 and 1 impacts, rivals as aggressor). It is a
# scrum, not a scripted hit: a run with no classified player contact is a scenario miss, and the
# precondition check names it as one.
#
# The checks are split so a red names its side:
#   * `the game state saw an event 31` -- the scenario precondition (`[impact] type`,
#     BRN_BOOST_TICKER_DIAG: a classified player contact reached the game state);
#   * `[snd-logic] impact event 31` count > 0 -- the lane's proof;
#   * the parity check fails only if the GAME STATE saw event 31 and the SOUND module did not.
@{
  Name    = 'audio_impact_ram'
  Area    = 'sound'
  Bug     = 'crashes make no impact sound: game event 31 never reached the sound logic module'
  Frames  = $false
  Run     = @{
    Drive           = $true
    MotionProbe     = $true
    SkipIntro       = $true
    AcceptGap       = 1.0
    Teleport        = '3040.7,-5.8,-1937.9,180'   # the road outside the junkyard exit == Road Rage junction 480861
    StartEvent      = $true
    EventFsm        = $true
    SkipTrainingTip = $true
    MaxSeconds      = 150
  }
  DiagEnv = 'BRN_SOUNDLOGIC_DIAG=1,BRN_BOOST_TICKER_DIAG=1,BRN_CRASHCAM_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }

    # PRECONDITION: the game state consumed at least one event 31 (BRN_BOOST_TICKER_DIAG, first 24).
    # Without it the scrum missed and the checks below say nothing about the sound leg.
    @{ Kind = 'LogCount';   Name = 'the game state saw an event 31 (else the scrum missed)'
       Pattern = '\[impact\] type'; Min = 1 }

    # THE LANE'S PROOF: an impact event came in and sound message 19 went out.
    @{ Kind = 'LogCount';   Name = 'impact event 31 -> sound message 19'
       Pattern = '\[snd-logic\] impact event 31'; Min = 1 }

    # PARITY: every impact the game state consumed must also have reached the sound module (both
    # read the same world queue in the same frame). Both witnesses are first-N capped (24 game
    # state, 32 sound), so the comparison is capped at 24.
    @{ Kind = 'Script'; Name = 'every game-state impact also reached the sound module'
       Script = {
         param($ctx)
         $liGame  = @($ctx.LogLines | Where-Object { $_ -match '\[impact\] type' }).Count
         $liSound = @($ctx.LogLines | Where-Object { $_ -match '\[snd-logic\] impact event 31' }).Count
         if ($liGame -eq 0) {
           return @{ Pass = $true; Detail = ("no [impact] line: the scenario produced no race-car/race-car impact (sound saw {0})" -f $liSound) }
         }
         $liWant = [Math]::Min($liGame, 24)
         return @{ Pass = ($liSound -ge $liWant); Detail = ("game state {0} impact(s), sound {1} (want >= {2})" -f $liGame, $liSound, $liWant) }
       } }

    # INFO: classified player verdicts. The verdict witness stops after 16 player-involved
    # contacts, so a scrum's classified hit often lands after the cap: never gate on it.
    @{ Kind = 'LogCount';   Name = 'info: classified player verdicts (capped witness)'
       Pattern = '\[td-contact\] verdict (0 vs \d+|\d+ vs 0) impact=(?!none)' }
    # INFO: ProcessCameraFlags posted a junkyard sting (the returning-boot junkyard leg can raise
    # JY_FLASH / JY_NEW_CAR_INTRO; not every boot does).
    @{ Kind = 'LogCount';   Name = 'info: [snd-logic] camera-flag stings'; Pattern = '\[snd-logic\] camera ' }
  )
}
