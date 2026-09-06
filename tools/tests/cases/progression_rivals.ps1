# progression_rivals -- the rival leg of the progression subsystem: UnlockRivals / UpdateRivals /
# AddRivalToWorld, plus the takedown hook OnTakedownTo.
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case progression_rivals
#
# THE CHAIN (console): CarSelectManager::UpdateExitState raises ProgressionManager::mbUpdateRivals
# (X360 +0x20971) on EVERY junkyard exit -- that writer is live on PC. ProgressionManager::
# PreWorldUpdate @0x823A4F68 drains it through UpdateRivals @0x82396298, which posts game action
# 195 (E_ACTION_REMOVE_ALL_RIVALS -> RaceCarEntityModule::RemoveAllRivalsFromWorld) once per pass
# and then walks the authored rival table one rival per frame, handing every rival the profile
# holds in state UNLOCKED or FLEEING to AddRivalToWorld @0x8238B0A8 (game action 196,
# E_ACTION_ADD_RIVAL, 176 bytes). The pass ends by clearing the request byte.
#
# RED (before the fix): UpdateRivals had no body, so every log since the PreWorldUpdate landing
# carried the park line below on a plain boot+drive and mbUpdateRivals stayed set for ever.
# GREEN: the park line is gone and the drain's own witness fires with the counts the profile
# actually holds. A FRESH profile holds ZERO rivals, so posted=0 is a correct GREEN -- what this
# case measures is that the LEG RAN and the request byte was consumed, which is exactly the bug.
#
# WITNESSES (opt-in via BRN_PROGRESSION_RIVALS, all first-N capped, none per-frame):
#   [rivals] update: profileRivals=<n> unlocked=<n> posted=<n> authoredRivals=<n>
#                                          UpdateRivals -- printed once per completed drain
#   [rivals] unlock: medals=<n> index=<n> rival=<id> car=<id>    UnlockRivals, on a real unlock
#   [rivals] takedownTo: type=<n> carType=<n> tip=<n> requested=<0|1>   OnTakedownTo
@{
  Name    = 'progression_rivals'
  Area    = 'progression'
  Bug     = 'progression: unlocked rivals never reach the world -- UpdateRivals/AddRivalToWorld unported, mbUpdateRivals never consumed'
  Frames  = $false
  Run     = @{
    Drive       = $true
    MotionProbe = $true
    MaxSeconds  = 55
    SkipIntro   = $true
    AcceptGap   = 1.0
    Teleport    = '3040.7,-5.8,-1937.9,180'   # the road outside the junkyard exit (baseline's)
  }
  DiagEnv = 'BRN_PROGRESSION_RIVALS=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions';  Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }

    # THE BUG, half 1: PreWorldUpdate must no longer report the leg as missing.
    @{ Kind = 'LogCount';   Name = 'PreWorldUpdate no longer parks UpdateRivals'
       Pattern = 'PreWorldUpdate: UpdateRivals\(\) is NOT reconstructed'; Max = 0 }

    # THE BUG, half 2: the drain must actually RUN and COMPLETE. The witness is printed only on the
    # frame the pass clears mbUpdateRivals, so its presence is proof the request byte was consumed.
    @{ Kind = 'LogMatch';   Name = 'UpdateRivals drained the request (witness fired)'
       Pattern = '\[rivals\] update: profileRivals=\d+ unlocked=\d+ posted=\d+ authoredRivals=\d+'
       Expect  = $true }

    # The authored rival table must be the one the drain walked (a 0 here would mean the pass
    # ended because ProgressionData was empty, not because it did the work).
    @{ Kind = 'LogValue';   Name = 'the drain walked the authored rival table (authoredRivals > 0)'
       Pattern = '\[rivals\] update: .*authoredRivals=(?<n>\d+)'; Group = 'n'; Agg = 'last'; Min = 1 }

    # Consistency: a rival the profile has NOT unlocked can never be posted to the world, so
    # posted <= unlocked on every drain. Scored over every witness line in the run.
    @{ Kind = 'Script';     Name = 'posted <= unlocked on every drain'; Script = {
        param($ctx)
        $lines = @($ctx.LogLines | Where-Object { $_ -match '\[rivals\] update: profileRivals=(?<p>\d+) unlocked=(?<u>\d+) posted=(?<n>\d+)' })
        if ($lines.Count -eq 0) { return @{ Pass = $false; Detail = 'no [rivals] update: line' } }
        $bad = 0; $last = ''
        foreach ($l in $lines) {
          if ($l -match 'unlocked=(?<u>\d+) posted=(?<n>\d+)') {
            if ([int]$Matches.n -gt [int]$Matches.u) { $bad++ }
          }
          $last = $l
        }
        return @{ Pass = ($bad -eq 0)
                  Detail = ("{0} drain(s), {1} inconsistent; last: {2}" -f $lines.Count, $bad, $last.Trim()) }
      } }
  )
}
