# progression_completion -- progression wave 2026-09-06, lane "completion".
#
# THREE console legs that reward completion never ran on PC, because the bodies were never
# reconstructed and their seats were parked:
#
#   1. ProgressionManager::SendTrophyUnlockUpdate  @0x823892B8
#      PreWorldUpdate polls mQueueOfTrophyCarUnLocks and, while it is non-empty, posts the TAIL
#      element as game action 204 (E_ACTION_TROPHY_UNLOCK, 16 B) and Erases it.
#      UnlockCarFromTrophy (BrnProgressionManager_Unlocks.cpp) Appends into that queue TODAY, so
#      before this lane the queue could only ever FILL -- every trophy car the player earned sat
#      in a 12-slot array that nothing drained, and the twelfth would have hit "Array container
#      out of space".
#   2. ProgressionManager::UnlockDerivedCarCollection @0x8237AD70 (+ DerivedCarArray::
#      DEBUG_PrintArray @0x8236ACE8) -- the paint-shop / derived-car unlock.
#      CarSelectManager::StartCarModificationState @0x82387410 builds the selected car's
#      colour-livery family and hands it to the progression layer; that whole tail was parked,
#      so entering the modification screen unlocked none of the car's livery versions.
#   3. ProgressionManager::CheckForAllModeTypeCompletion @0x82389698 (+ GetEventCountForType
#      @0x8236F9D8 / GetEventTypeUniqueWinCount @0x82370758) -- PreWorldUpdate's 2 s hold.
#      Not reachable in a 60 s harness scenario (it needs the player to be at the last authored
#      rank and to win an event), so it is proved by its BODY landing + the un-park, not here.
#
# WHAT THIS CASE MEASURES (both legs are on the ordinary boot -> junkyard -> DRIVING path):
#
#   [completion] derived: base=<id> entries=<n> unlocked=<k> owned=<o>
#       ProgressionManager::UnlockDerivedCarCollection, once per call. Emitted where the console
#       computes it. RED: absent, and the CarSelectManager park line is in the log instead.
#
#   [completion] trophy posted id=<car> type=<t> queueLeft=<n>
#       ProgressionManager::SendTrophyUnlockUpdate, once per posted record. The queue is primed
#       by an OPT-IN HARNESS STIMULUS (BRN_PROGRESSION_COMPLETION_SEEDTROPHY=1, default off,
#       ProgressionManager::DEBUG_HarnessSeedTrophyQueue) because nothing a 60 s free-burn run
#       can do earns a trophy car: the console's own producer, OnTrophyUnlock -> UnlockCarFromTrophy,
#       needs a completed trophy CATEGORY. The stimulus only Appends one record to the transient
#       queue -- it writes nothing to the profile and unlocks no car. queueLeft=0 is the drain.
#
# Both witnesses are opt-in behind BRN_PROGRESSION_COMPLETION=1 and are bounded (first 16 lines).
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case progression_completion
@{
  Name    = 'progression_completion'
  Area    = 'progression'
  Bug     = 'progression wave (completion): trophy-car unlocks queue forever and never post; derived/paint cars never unlock'
  Frames  = $false
  Run     = @{
    Drive       = $true
    MaxSeconds  = 50
    SkipIntro   = $true
    AcceptGap   = 1.0
    Teleport    = '3040.7,-5.8,-1937.9,180'   # the road outside the junkyard exit (baseline's)
  }
  DiagEnv = 'BRN_PROGRESSION_COMPLETION=1,BRN_PROGRESSION_COMPLETION_SEEDTROPHY=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }

    # ---- leg 2: the derived-car collection ------------------------------------------------
    @{ Kind = 'LogMatch';   Name = 'UnlockDerivedCarCollection ran on the junkyard car'
       Pattern = '\[completion\] derived: base=' }
    @{ Kind = 'LogCount';   Name = 'the StartCarModificationState derived-livery park is GONE'
       Pattern = 'StartCarModificationState: the derived-livery collection is NOT reconstructed'; Max = 0 }

    # ---- leg 1: the trophy-car unlock queue -----------------------------------------------
    @{ Kind = 'LogMatch';   Name = 'SendTrophyUnlockUpdate posted the queued trophy car (action 204)'
       Pattern = '\[completion\] trophy posted id=\d+ type=\d+ queueLeft=' }
    @{ Kind = 'LogValue';   Name = 'the queue actually DRAINED (queueLeft reaches 0)'
       Pattern = '\[completion\] trophy posted id=\d+ type=\d+ queueLeft=(?<n>\d+)'; Group = 'n'; Agg = 'min'; Max = 0 }
    @{ Kind = 'LogCount';   Name = 'the PreWorldUpdate SendTrophyUnlockUpdate park is GONE'
       Pattern = 'SendTrophyUnlockUpdate\(\) is NOT reconstructed'; Max = 0 }

    # ---- leg 3 + the P4 seat: the parks this lane retired ---------------------------------
    @{ Kind = 'LogCount';   Name = 'the PreWorldUpdate CheckForAllModeTypeCompletion park is GONE'
       Pattern = 'CheckForAllModeTypeCompletion\(\) is NOT reconstructed'; Max = 0 }
  )
}
