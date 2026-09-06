# progression_profile -- progression "not connected" wave 2026-09-06, lane `profile`.
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case progression_profile
#
# WHAT IS BEING MEASURED. Six BrnProgression::Profile members had PC callers and no body:
#   Profile::HasPlayerCompletedFreeburnChallenge @0x82371338
#   Profile::CompleteFreeburnChallenge          @0x82371368
#   Profile::GetMugshotInfo                     @0x82371290
#   Profile::LockOrUnlockMugshot                @0x823711C0
#   Profile::DeleteMugshot                      @0x82371018
#   Profile::GetGameModeTypeCompletedAmountSinceTheStart @0x82354B98
# Their console callers (BrnGameState::ChallengeManager*, GameStateImageManagerBase) are NOT in
# the shipped mount list, and the sixth one's caller (OnEventFinishUpdateProfile) only runs when an
# event is WON -- neither is reachable inside a 60 s harness scenario. The lane's stimulus is
# therefore the profile's own SELFTEST: `BRN_PROGRESSION_PROFILE_SELFTEST=1` makes
# Profile::Construct (the boot seam ProgressionManager::Prepare2 runs once) exercise
#   Has -> Complete -> Has                              for one synthetic freeburn-challenge id, and
#   AddMugshot -> GetMugshotInfo -> Lock -> Unlock -> DeleteMugshot -> GetMugshotInfo(out of range)
# for one gallery-0 mugshot, then print ONE line with the result of every step. Default OFF; it is
# named as a selftest in the log and it runs on the FRESH profile the harness parks (FreshProfile),
# so nothing the player owns is touched.
#
# WITNESS (opt-in, once per boot, two lines -- [FLAG PC witness], not in the X360 binary):
#   [profile] selftest challenge=<ok|FAIL> mugshot=<ok|FAIL>
#   [profile] selftest detail has0=.. count=.. has1=.. | file=.. num=.. lock0=.. lock1=.. lock2=.. del=.. numAfter=.. avail=..
#
# RED (before the lane): the six bodies do not exist, so no selftest can run and NEITHER line is in
# the log -- a LogMatch that cannot be evaluated fails, on purpose (tools/tests/README.md).
# GREEN: `challenge=ok mugshot=ok`, the detail line's step values are the console's, the boot still
# reaches DRIVING and no new assert family appears.
#
# WHY MaxSeconds > 60: this case needs FreshProfile (the profile the selftest mutates must be a
# parked throw-away one), and the first-boot path is the long one. 70 s is the shortest value that
# reached DRIVING on this box; the case does no driving work of its own.
@{
  Name    = 'progression_profile'
  Area    = 'progression'
  Bug     = 'progression wave -- Profile freeburn-challenge / mugshot / since-the-start services had no body'
  Frames  = $false
  FreshProfile = $true
  Run     = @{
    Drive       = $true
    MaxSeconds  = 70
    SkipIntro   = $true
    AcceptGap   = 1.0
    Teleport    = '3040.7,-5.8,-1937.9,180'   # the road outside the junkyard exit (baseline's)
  }
  DiagEnv = 'BRN_PROGRESSION_PROFILE_SELFTEST=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions';   Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }

    # THE BUG. Both halves must report ok; either half missing (no line at all) fails.
    @{ Kind = 'LogMatch';   Name = 'freeburn-challenge trio ran (Has/Complete/Has)'
       Pattern = '\[profile\] selftest challenge=ok'; Expect = $true }
    @{ Kind = 'LogMatch';   Name = 'mugshot chain ran (Add/Get/Lock/Unlock/Delete)'
       Pattern = '\[profile\] selftest challenge=\S+ mugshot=ok'; Expect = $true }

    # The step values, so a body that merely returns something cannot pass:
    #   has0=0  -- the synthetic id is not complete before CompleteFreeburnChallenge
    #   count=1 -- CompleteFreeburnChallenge returns the array's NEW length (X360 lwz 0x3E80(r28))
    #   has1=1  -- and Contains now finds it
    @{ Kind = 'LogMatch';   Name = 'challenge steps: has0=0 count=1 has1=1'
       Pattern = '\[profile\] selftest detail has0=0 count=1 has1=1'; Expect = $true }
    #   file>=0 -- AddMugshot claimed a file id from the gallery-0 available-id bit array
    #   lock0=0 lock1=1 lock2=0 -- LockOrUnlockMugshot toggles MugshotInfo::mbLocked (+0x32)
    #   del=file -- DeleteMugshot returns the freed file id (X360 lhz 0x30 -> r27 -> r3)
    #   numAfter=0 -- and the gallery is empty again
    #   avail=1 -- the file id went back into the available bit array (X360 SetBit)
    @{ Kind = 'LogMatch';   Name = 'mugshot steps: lock toggles, delete frees the file id'
       Pattern = 'lock0=0 lock1=1 lock2=0 del=(?<d>\d+) numAfter=0 avail=1'; Expect = $true }
  )
}
