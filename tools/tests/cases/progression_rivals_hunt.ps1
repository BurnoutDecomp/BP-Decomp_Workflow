# progression_rivals_hunt -- A ROAMING RIVAL IS TAKEN DOWN IN FREE ROAM AND MOVES TO BEATEN.
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case progression_rivals_hunt
#
# THE GAP. progression_rivals proves the rival ADD leg (UpdateRivals -> AddRivalToWorld -> game action
# 196 -> RaceCarEntityModule::AddRivalCar), but no run has ever logged the WIN leg's own line,
# "Moving rival to beaten state:". Taking a roaming rival down in free roam is the only way to beat
# one, and the accel-only harness cannot hunt a car that drives its own route.
#
# THE CHAIN this case measures (every link is console code except the one harness arm):
#   1. The fixture's profile holds an UNLOCKED rival; the junkyard exit drains mbUpdateRivals and
#      AddRivalToWorld posts action 196                                  -> [rivals] add: ... posted=196
#   2. The rival roams out of range until the player is within 350 m (RaceCar::ShouldBeInRange, free-
#      roam arm); the 1 Hz range pass attaches it to an active slot     -> [ignition] attach slot N type=1
#   3. BRN_FORCE_RIVAL_TAKEDOWN=<s> (GameStateModule_gTD_00.cpp): with NO game mode running, once a
#      loaded rival slot has been active <s> seconds, the player's slot is armed as the aggressor of
#      a STANDARD takedown of that slot (the "Force takedown" debug action's arming + the two car ids)
#                                                                        -> [rival-hunt] HARNESS force-takedown fired
#   4. TakedownManager::ProcessQueuedTakedowns confirms it (player active, not crashing, above
#      KF_MIN_TAKEDOWN_SPEED 50 mph) -> ProcessTakedownEvent's free-burn arm: ShutdownAction (120) +
#      ProgressionManager::OnPursuitWon(victim slot's rival id)
#   5. OnPursuitWon -> DefeatRivalAndUnlockCar                         -> Moving rival to beaten state: <id>
#      then posts the rival state change (197, 120 bytes) and the FORCED autosave (55, 1 byte)
#                                                                        -> [rival-hunt] takedown tick posted action 197 / 55
#
# THE FIXTURE (ProfileFixture, run_case.ps1): tools\tests\fixtures\rival_hunt_profile.sav is the
# harness's returning-player save as of 2026-09-28 (sha1 5a6c35a1...), pinned so the case does not
# depend on whatever build\game\Memcard\Profile.sav holds. Measured on it (progression_rivals run
# scratch\bugtest\runs\progression_rivals\20260928_083941): profileRivals=2 unlocked=1, the unlocked
# rival is 339250 (index 2, district 12, section 782, spawn x=-2836.2 z=463.9). The forced autosave
# writes the slot's save mid-run; run_case restores the original afterwards and keeps what the game
# wrote as <RunDir>\Profile.sav.after. To re-pin: copy a save with at least one UNLOCKED rival over
# the fixture, run progression_rivals with it, and update the spawn/teleport below from its
# `[rivals] add:` line.
#
# THE SPOT. Teleport is the Burning Route junction 481548's grid (29 m from that rival's spawn), so
# the rival is inside the 350 m in-range distance on the first range pass after the teleport. The
# teleport fires during the junkyard-exit drive, so the player then SITS until the throttle starts
# and the rival drives out of range first (measured RED run 20260928_084612: in at 53 m, out at
# 401 m before the player reached 50 mph). The console then brings the rival back beside the moving
# player (out->in at 341 m, reset-pump AI pose at the player's speed, 56 m away at 125 mph) -- that
# second encounter is the window. The harness re-arms once a second of rival time (forty at most)
# until the tick posts 197, because a slow or crashing aggressor is dropped by the console's own
# confirmation sweep. Physics runs differ boot to boot: a run in which the rival never comes back
# while the player is fast is a scenario miss, not a verdict on the win leg (read [rival-hunt] /
# [range] lines before calling it).
@{
  Name           = 'progression_rivals_hunt'
  Area           = 'progression'
  Bug            = 'progression: a roaming rival has never been beaten -- "Moving rival to beaten state" never logged; prove free-roam takedown -> OnPursuitWon -> 197 + forced autosave'
  Frames         = $false
  ProfileFixture = 'rival_hunt_profile.sav'
  Run            = @{
    Drive       = $true
    MotionProbe = $true
    MaxSeconds  = 80
    SkipIntro   = $true
    AcceptGap   = 1.0
    Teleport    = '-2844.4,114.4,491.8,159'   # junction 481548 grid, 29 m from rival 339250's spawn
  }
  DiagEnv = 'BRN_FORCE_RIVAL_TAKEDOWN=1,BRN_PROGRESSION_RIVALS=1,BRN_TD_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families (incl. "Could not find rival")' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }

    # LINK 1 -- the fixture's rival was handed to the world.
    @{ Kind = 'LogMatch';   Name = 'the fixture rival was added (action 196)'
       Pattern = '\[rivals\] add: .* posted=196'; Expect = $true }

    # LINK 2 -- the scenario precondition: an AI car was attached to an active slot (in range).
    @{ Kind = 'LogMatch';   Name = 'a rival came in range (AI car attached to an active slot)'
       Pattern = '\[ignition\] attach slot \d+ type=1\b'; Expect = $true }

    # LINK 3 -- the harness saw the rival slot and pulled the trigger.
    @{ Kind = 'LogMatch';   Name = 'the free-roam rival takedown was armed'
       Pattern = '\[rival-hunt\] HARNESS force-takedown fired'; Expect = $true }

    # LINK 5 -- THE BUG: the win leg's own console line.
    @{ Kind = 'LogMatch';   Name = 'Moving rival to beaten state: (the win leg ran)'
       Pattern = 'Moving rival to beaten state: \d+'; Expect = $true }

    # LINKS 1..5 in order, the rival ids agree, and the two OnPursuitWon posts follow the beaten line.
    @{ Kind = 'Script'; Name = 'add -> beaten -> action 197 -> action 55, same rival id'
       Script = {
         param($ctx)
         $la = $ctx.LogLines
         $liAdd = -1; $liBeaten = -1; $li197 = -1; $li55 = -1
         $lsHuntId = ''; $lsBeatenId = ''
         for ($i = 0; $i -lt $la.Count; $i++) {
           $l = $la[$i]
           if ($liAdd -lt 0 -and $l -match '\[rivals\] add: .* posted=196') { $liAdd = $i }
           if (-not $lsHuntId -and $l -match '\[rival-hunt\] HARNESS force-takedown fired .*rivalId=(\d+)') { $lsHuntId = $Matches[1] }
           if ($liBeaten -lt 0 -and $l -match 'Moving rival to beaten state: (\d+)') { $liBeaten = $i; $lsBeatenId = $Matches[1] }
           if ($liBeaten -ge 0 -and $li197 -lt 0 -and $l -match '\[rival-hunt\] takedown tick posted action 197 ') { $li197 = $i }
           if ($li197 -ge 0 -and $li55 -lt 0 -and $l -match '\[rival-hunt\] takedown tick posted action 55 ') { $li55 = $i }
         }
         $lsWhere = "add@$liAdd beaten@$liBeaten 197@$li197 55@$li55 huntId=$lsHuntId beatenId=$lsBeatenId"
         if ($liAdd -lt 0)    { return @{ Pass = $false; Detail = "no [rivals] add line; $lsWhere" } }
         if ($liBeaten -lt 0) { return @{ Pass = $false; Detail = "never beaten; $lsWhere" } }
         if ($liBeaten -lt $liAdd) { return @{ Pass = $false; Detail = "beaten before the add; $lsWhere" } }
         if ($li197 -lt 0)    { return @{ Pass = $false; Detail = "no action 197 posted after the beaten line; $lsWhere" } }
         if ($li55 -lt 0)     { return @{ Pass = $false; Detail = "no forced autosave (55) posted after 197; $lsWhere" } }
         if ($lsHuntId -ne $lsBeatenId) { return @{ Pass = $false; Detail = "the beaten rival is not the hunted one; $lsWhere" } }
         return @{ Pass = $true; Detail = $lsWhere }
       } }
  )
}
