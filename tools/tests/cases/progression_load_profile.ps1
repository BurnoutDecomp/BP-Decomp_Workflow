# progression_load_profile -- a returning player's progression state is restored by
# ProgressionManager::OnLoadProfile (via GameStateModule::OnProfileLoaded), not by the
# PreWorldUpdate rank-only stand-in it replaced; and the loaded save's prop zones do not churn.
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case progression_load_profile
#
# PORTED 2026-10-06 (GW4 PROOF) from the never-committed 09-28 case (scratch\gameplay_wave\backup_full)
# onto upstream's load path (b5 f935feb8). The 09-28 `[load-profile-prog] rank= maxCars= cars=
# updateRivals= medalsUpdate=` witness does not exist upstream; its rank and car total are read from
# upstream's always-on `[GameStateModule::OnProfileLoaded] ... rank=<n> maxCars=<n>` line instead,
# and the two request flags are proven by their effects (a [medals] pass and a [rivals] update after
# the load).
#
# THE CHAIN. The save load reaches GameStateModule::OnProfileLoaded, which calls
# ProgressionManager::OnLoadProfile: the rank cache is copied from the saved licence rank and the
# medal, rival and drive-thru passes are re-requested. The next PreWorldUpdate then runs
# UpdatePlayerMedals against a cache that already holds the saved rank, so no rank-up happens and
# ClearMedalsOnRankUp cannot wipe the saved medals; and it runs UpdateRivals because OnLoadProfile
# raised mbUpdateRivalsRequested, so the rivals reach the world BEFORE the junkyard exit.
#
# WITNESSES:
#   [GameStateModule::OnProfileLoaded] junkyard=.. spawnCar=.. profileCar=.. rank=.. maxCars=..   always on
#   [medals] total=.. rank=.. profileRank=.. winsToNext=.. action200=1 events=..   BRN_PROGRESSION_MEDALS
#   [rivals] update: profileRivals=.. unlocked=.. posted=.. authoredRivals=..      BRN_PROGRESSION_RIVALS
#   "=== CarSelectManager: Start Exit state."     the junkyard exit (message-filter bit 0 log)
#   PROPS Loading zone: <id>                     message-filter bit 0, uncapped (the churn guard; see
#                                                returning_player_spawn.ps1 for the 09-28 RED/GREEN)
@{
  Name           = 'progression_load_profile'
  ProfileFixture = 'rival_hunt_profile.sav'
  Area           = 'progression'
  Bug            = 'returning player: OnLoadProfile must restore the saved rank, request the medal + rival passes before the junkyard exit, and the prop zones must not churn'
  Frames         = $false
  Run            = @{
    Drive       = $true
    MotionProbe = $true
    MaxSeconds  = 55
    SkipIntro   = $true
    AcceptGap   = 1.0
    Teleport    = '3040.7,-5.8,-1937.9,180'   # the road outside the junkyard exit (progression_rivals')
  }
  DiagEnv = 'BRN_PROGRESSION_MEDALS=1,BRN_PROGRESSION_RIVALS=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions';  Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }

    # The stand-in is gone: its log line must never appear.
    @{ Kind = 'LogCount';   Name = 'the PreWorldUpdate rank stand-in is gone'
       Pattern = 'standing in for OnLoadProfile'; Max = 0 }

    @{ Kind = 'LogValue';   Name = 'OnProfileLoaded restored a saved rank (>= 0)'
       Pattern = '\[GameStateModule::OnProfileLoaded\] .* rank=(?<v>-?\d+)'; Group = 'v'; Agg = 'first'; Min = 0 }
    @{ Kind = 'LogValue';   Name = 'the max-car count was re-seeded (> 0)'
       Pattern = '\[GameStateModule::OnProfileLoaded\] .* maxCars=(?<v>-?\d+)'; Group = 'v'; Agg = 'first'; Min = 1 }

    # Medals survive the boot. Every [medals] pass after the load must keep the loaded rank (a rank
    # change there is a rank-up, and a rank-up runs ClearMedalsOnRankUp) and see a populated event
    # list; at least one pass must run after the load (OnLoadProfile raised the medals request).
    # Passes BEFORE the load are reported, not failed: upstream runs the start-of-game legs of
    # PreWorldUpdate in the loading spine before the deserialise (console seat), and the medals pass
    # there works on the default profile, which the load then overwrites.
    @{ Kind = 'Script';     Name = 'the loaded rank holds and medals are not re-ranked after the load'; Script = {
        param($ctx)
        $lines = @($ctx.LogLines)
        $iLoad = -1; $rank = 0
        for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -match '\[GameStateModule::OnProfileLoaded\] .* rank=(?<r>-?\d+)') { $iLoad = $i; $rank = [int]$Matches.r; break } }
        if ($iLoad -lt 0) { return @{ Pass = $false; Detail = 'no OnProfileLoaded line (fresh profile, or the load never ran)' } }
        $before = 0; $after = 0; $afterBad = 0; $last = ''
        for ($i = 0; $i -lt $lines.Count; $i++) {
          if ($lines[$i] -notmatch '\[medals\] total=\S+ rank=(?<r>-?\d+) .*events=(?<e>\d+)') { continue }
          if ($i -lt $iLoad) { $before++ }
          else { $after++; $last = $lines[$i].Trim(); if ([int]$Matches.r -ne $rank -or [int]$Matches.e -eq 0) { $afterBad++ } }
        }
        return @{ Pass = ($after -gt 0 -and $afterBad -eq 0)
                  Detail = ("loaded rank {0}; {1} pass(es) before the load (info), {2} after ({3} off-rank or empty); last: {4}" -f $rank, $before, $after, $afterBad, $last) }
      } }

    # The rivals pass OnLoadProfile requested completes after the load and before the junkyard exit.
    @{ Kind = 'Script';     Name = '[rivals] update fires after the load and before the junkyard exit'; Script = {
        param($ctx)
        $lines = @($ctx.LogLines)
        $iLoad = -1; $iRivals = -1; $iExit = -1
        for ($i = 0; $i -lt $lines.Count; $i++) {
          if ($iLoad -lt 0 -and $lines[$i] -match '\[GameStateModule::OnProfileLoaded\] junkyard=') { $iLoad = $i }
          if ($iLoad -ge 0 -and $iRivals -lt 0 -and $lines[$i] -match '\[rivals\] update: profileRivals=') { $iRivals = $i }
          if ($iExit -lt 0 -and $lines[$i] -match '=== CarSelectManager: Start Exit state\.') { $iExit = $i }
        }
        if ($iLoad -lt 0) { return @{ Pass = $false; Detail = 'no OnProfileLoaded line' } }
        if ($iRivals -lt 0) { return @{ Pass = $false; Detail = 'no [rivals] update: line after the load' } }
        $pass = ($iExit -lt 0 -or $iRivals -lt $iExit)
        return @{ Pass = $pass; Detail = ("OnProfileLoaded line {0}; first [rivals] update after it at {1}; first junkyard exit at {2}" -f ($iLoad + 1), ($iRivals + 1), $(if ($iExit -lt 0) { 'none' } else { $iExit + 1 })) }
      } }

    @{ Kind = 'Script';     Name = 'prop zones do not churn (no zone loaded more than 6 times)'; Script = {
        param($ctx)
        $counts = @{}
        foreach ($l in $ctx.LogLines) {
          if ($l -match 'PROPS Loading zone: (?<z>\d+)') { $counts[$Matches.z] = 1 + [int]$counts[$Matches.z] }
        }
        if ($counts.Count -eq 0) { return @{ Pass = $false; Detail = 'no PROPS Loading zone line' } }
        $top = $counts.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 1
        return @{ Pass = ($top.Value -le 6); Detail = ("{0} zones loaded; busiest zone {1} x{2}" -f $counts.Count, $top.Key, $top.Value) }
      } }
  )
}
