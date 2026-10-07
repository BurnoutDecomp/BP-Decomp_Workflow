# returning_player_spawn -- a loaded save enters the game through OnProfileLoaded, and its prop zones
# do not churn (the 09-28 prop-flicker regression guard).
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case returning_player_spawn
#
# PORTED 2026-10-06 (GW4 PROOF) from the never-committed 09-28 case (scratch\gameplay_wave\backup_full)
# onto upstream's load path (b5 f935feb8). What changed against the 09-28 expectations:
#   - the start-of-game one-shot (SendSetupPlayerCarEvent) DOES run on a loaded save now: upstream
#     moved it to the console's seat, the first loading-scripted frame, BEFORE the profile is
#     deserialised. The check is therefore ORDER, not absence: one-shot < OnProfileLoaded < the
#     junkyard entry (EnterJunkyardAtStartOfGame) < the GUI's game event 78.
#   - the witness is upstream's own, always on: `[GameStateModule::OnProfileLoaded] junkyard=<id>
#     spawnCar=<NAME> profileCar=<NAME> rank=<n> maxCars=<n> savedPos=(x, y, z)`. The 09-28
#     [load-profile] lines and BRN_LOADPROFILE_DIAG no longer exist.
#
# THE CHAIN (console): the memory-card phase ends -> game event 8 (GAME_START) -> ProcessGameEvents
# case 8 -> GameStateModule::OnProfileLoaded: junkyard nearest the profile's saved pose, GetSpawnCar
# (the saved car, PUSMC01 below its unlock rank), EnterJunkyardAtStartOfGame, action 194 (the prop
# world asks for the profile's hit props: event 112 -> action 199), the case-78 latch, RequestUnpause.
#
# THE PROP GUARD. Without the 194 -> 112 -> 199 handshake the player's own prop zone is loaded and
# unloaded every frame and every prop flickers: the 09-28 RED run (returning_player_spawn
# 20260928_090920) loaded zone 23 651 times; the GREEN run (20260928_092824) loaded 10 zones once
# each. `PROPS Loading zone: <id>` is the stock message-filter-bit-0 line (on by default), uncapped,
# so it counts every load.
#
# THE FIXTURE (ProfileFixture, run_case.ps1): tools\tests\fixtures\rival_hunt_profile.sav (sha1
# 5a6c35a1..., byte-identical to the 09-28 scratch\gameplay_wave\LOAD\returning_player_profile.sav):
# version 28, spawn car PUSMC01, wheel 0, saved pose (0,0,0), rank 1.
# WHY junkyard 312262: the five TRIGGERS.DAT junkyards by distance from the origin are 312262 982 m,
# 292521 1386 m, 290890 2113 m, 289762 2304 m, 250700 3588 m; the saved pose is the origin.
#
# NO TELEPORT on purpose: the baseline's teleport targets the road outside 250700, 4 km away. The
# drive is the junkyard exit plus the held throttle.
@{
  Name           = 'returning_player_spawn'
  Area           = 'progression'
  Bug            = 'load path: a loaded save must enter through OnProfileLoaded at the junkyard nearest its pose, and its prop zones must not churn (09-28 prop flicker)'
  Frames         = $false
  ProfileFixture = 'rival_hunt_profile.sav'
  Run            = @{
    Drive       = $true
    MotionProbe = $true
    MaxSeconds  = 55
    SkipIntro   = $true
    AcceptGap   = 1.0
  }
  DiagEnv = 'BRN_PROPPROG_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions';  Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }

    # Exactly one profile delivery, at the junkyard nearest the saved pose, in the saved car.
    @{ Kind = 'Script';     Name = 'one OnProfileLoaded: junkyard 312262, spawn car = profile car'; Script = {
        param($ctx)
        $lines = @($ctx.LogLines | Where-Object { $_ -match '\[GameStateModule::OnProfileLoaded\] junkyard=' })
        if ($lines.Count -ne 1) { return @{ Pass = $false; Detail = ("{0} OnProfileLoaded line(s), want 1" -f $lines.Count) } }
        $l = $lines[0]
        if ($l -notmatch 'junkyard=(?<j>\d+) spawnCar=(?<s>\S+) profileCar=(?<p>\S+) rank=(?<r>-?\d+)') {
          return @{ Pass = $false; Detail = "unparsed: $($l.Trim())" }
        }
        $ok = ($Matches.j -eq '312262') -and ($Matches.s -eq $Matches.p)
        return @{ Pass = $ok; Detail = $l.Trim() }
      } }

    # The boot order upstream proved: one-shot < OnProfileLoaded < event 78. OnProfileLoaded prints
    # its witness at the END of its body, so its EnterJunkyardAtStartOfGame(312262) line comes just
    # BEFORE the OnProfileLoaded line (run 20261006_201051: 1049 / 1050). The one-shot's own
    # junkyard entry (250700, the start's nearest) precedes both and is console order.
    @{ Kind = 'Script';     Name = 'order: one-shot < EnterJunkyardAtStartOfGame(312262) < OnProfileLoaded < event 78'; Script = {
        param($ctx)
        $iShot = -1; $iLoad = -1; $iJy = -1; $i78 = -1
        for ($i = 0; $i -lt $ctx.LogLines.Count; $i++) {
          $l = $ctx.LogLines[$i]
          if     ($iShot -lt 0 -and $l -match '\[GameStateModule::SendSetupPlayerCarEvent\] junkyard=') { $iShot = $i }
          elseif ($iLoad -lt 0 -and $l -match '\[CarSelectManager::EnterJunkyardAtStartOfGame\] junkyard=312262 ') { $iJy = $i }
          elseif ($iLoad -lt 0 -and $l -match '\[GameStateModule::OnProfileLoaded\] junkyard=') { $iLoad = $i }
          elseif ($iLoad -ge 0 -and $i78 -lt 0 -and $l -match '\[jyentry\] game event 78 \(GUI has started game\) received; waiting=1') { $i78 = $i }
        }
        $ok = ($iLoad -ge 0) -and ($iJy -ge 0) -and ($iJy -lt $iLoad) -and ($i78 -gt $iLoad) -and ($iShot -lt $iJy)
        return @{ Pass = $ok; Detail = ("one-shot line {0}, junkyard 312262 entry {1}, OnProfileLoaded {2}, event 78 (waiting=1) {3}" -f ($iShot + 1), ($iJy + 1), ($iLoad + 1), ($i78 + 1)) }
      } }

    # The prop handshake OnProfileLoaded starts (194 -> 112 -> 199) completed.
    @{ Kind = 'LogMatch';   Name = 'prop progression handshake: action 199 posted';
       Pattern = '\[propprog\] action 199 \(prop smash progression\) posted' }

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

    @{ Kind = 'Script';     Name = 'the car moved (> 20 m up to the first respawn)'; Script = {
        param($ctx)
        $s = Get-DriveSegment $ctx.LogLines
        if (-not $s.Known) { return @{ Pass = $false; Detail = ("{0} [motion] sample(s): no car position in this log" -f $s.Samples) } }
        return @{ Pass = ($s.Path -gt 20.0); Detail = ("path={0:f1}m net={1:f1}m samples {2}..{3} respawns={4} wrecks={5}" -f `
                  $s.Path, $s.Net, $s.FromSample, $s.ToSample, $s.Respawns, $s.Wrecks) }
      } }
  )
}
