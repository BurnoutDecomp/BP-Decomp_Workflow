# junkyard_carousel -- lane CARSEL, gameplay wave GW4 (census item 6, action 69).
#
# THE FEATURE. In the junkyard the car carousel pre-streams the cars the player can reach next:
# every car change posts game action 69 (CarSelectionRequestStreamingAction) carrying the shown car
# plus up to seven neighbours from GameStateModule::GetListOfPlayerSelectableVehicles, and
# RaceCarEntityModule::HandleSelectionRequestStreamingAction hands each missing model to the
# race-car streamer (slots 1..7). The livery screen (EnterModification) posts the same action with
# the car's livery versions.
#
# THE SCENARIO. Returning player on the box save (junkyard 250700, 3 selectable cars). At car select
# the harness taps OptionNext (GUI_RIGHT, action 44) three times, 3.5 s apart, through the real
# screen path: CarSelectVehicle steps its carousel, commits the car (GUI 415 -> game event 4 ->
# CarSelectManager::RequestChangeCar), then the harness accepts into the livery screen and accepts
# again to drive out. A harness menu tap is ONE input update and reaches the screen as DOWN +
# RELEASED, never the PRESSED its carousel arm steps on (measured with the '[carsel] gui input kind='
# witness, runs 20261006_201059 / _201820), so the lever BRN_CARSEL_TAPSTEP=1
# (BrnCarSelectVehicle_Input.cpp) replays such a release as the press.
#
# WITNESSES (BRN_CARSEL_DIAG=1, first-N capped, tagged [FLAG PC witness]):
#   [carsel] carousel action69 car=<id> listIndex=<i> selectable=<n> count=<c> entries: [k]<id>/f<flags>/p<prio>...
#   [carsel] livery action69 car=<id> count=<c> ids: ...
#   [carsel] car change done car=<id> modScreen=<0|1> secondsSinceRequest=<s>
#   STRM: Adding racecar for streaming: car=<slot>, model=<name>   (the streamer, filter bit 0, always on)
#
# A/B: the same case with DiagEnv BRN_CARSEL_NOPRESTREAM=1 withholds the carousel post (the knob is
# in BrnGameStateModule_wG4_00.cpp); tools\tests\tools\CARSEL_carousel_report.py compares the
# secondsSinceRequest of the two sets of run dirs.
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case junkyard_carousel
#
@{
  Name           = 'junkyard_carousel'
  Area           = 'gamestate/carselect'
  Bug            = 'GW4 census #6 -- the junkyard carousel never pre-streams neighbours (action 69 never posted)'
  Frames         = $false
  ProfileFixture = 'scratch\gameplay_wave\profile_backup\Profile.sav.pose250700'
  Run            = @{
    Drive          = $true
    MotionProbe    = $true
    MaxSeconds     = 90
    SkipIntro      = $true          # the console -skipvideos latch
    AcceptGap      = 3.5            # one tap per pump slot; a change is ~1.3 s plus the screen's re-skin
    CarSelectTaps  = 'OptionNext:3'  # GUI_RIGHT (44), stepped through the BRN_CARSEL_TAPSTEP lever
    ThrottleScript = '0:accel,6:none'
  }
  DiagEnv = 'BRN_CARSEL_DIAG=1,BRN_RCEM_ACTION_DIAG=1,BRN_CARSEL_TAPSTEP=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING (the returning save still boots and drives out)'; Phase = 'DRIVING' }

    @{ Kind = 'LogCount'; Name = 'action 69 posted by the carousel on each car change'; Pattern = '\[carsel\] carousel action69 '; Min = 2 }
    @{ Kind = 'LogCount'; Name = 'both car changes completed'; Pattern = '\[carsel\] car change done .*modScreen=0'; Min = 2 }

    @{ Kind = 'Script'; Name = 'every carousel request is well formed (shown car first, flags 5, neighbours from the selectable list)'; Script = {
        param($ctx)
        $laReq = @($ctx.LogLines | Where-Object { $_ -match '\[carsel\] carousel action69 ' })
        if ($laReq.Count -eq 0) { return @{ Pass = $false; Detail = 'no carousel action69 line' } }
        $fail = @()
        foreach ($l in $laReq) {
          if ($l -notmatch 'selectable=(?<n>\d+) count=(?<c>\d+) entries:(?<e>.*)$') { $fail += "unparsed: $l"; continue }
          $n = [int]$Matches.n; $c = [int]$Matches.c; $e = $Matches.e
          $ents = [regex]::Matches($e, '\[(\d+)\](\S+?)/f(\d+)/p(-?\d+)')
          if ($ents.Count -ne $c) { $fail += "count $c but $($ents.Count) entries"; continue }
          if ($c -gt 8) { $fail += "count $c > 8" }
          if ($c -ne [Math]::Min($n, 8)) { $fail += "count $c, want min(selectable $n, 8)" }
          if ($ents[0].Groups[3].Value -ne '5' -or $ents[0].Groups[4].Value -ne '0') { $fail += "entry 0 is not flags 5 / priority 0" }
          $ids = @($ents | ForEach-Object { $_.Groups[2].Value })
          if (($ids | Select-Object -Unique).Count -ne $ids.Count) { $fail += "duplicate car in one request: $($ids -join ',')" }
        }
        $detail = ("{0} request(s); first: {1}" -f $laReq.Count, ($laReq[0] -replace '^.*carousel action69 ', ''))
        if ($fail.Count) { $detail = ($fail -join ' | ') + '  [' + $detail + ']' }
        return @{ Pass = ($fail.Count -eq 0); Detail = $detail }
      } }

    @{ Kind = 'Script'; Name = 'the streaming consumer loads a requested neighbour into a carousel slot (1..7)'; Script = {
        param($ctx)
        $lines = $ctx.LogLines
        $first = -1
        for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -match '\[carsel\] carousel action69 ') { $first = $i; break } }
        if ($first -lt 0) { return @{ Pass = $false; Detail = 'no carousel action69 line' } }
        $req = @{}
        foreach ($m in [regex]::Matches($lines[$first], '\[\d+\](\S+?)/f')) { $req[$m.Groups[1].Value] = $true }
        $adds = @(); $hits = 0
        for ($i = $first + 1; $i -lt $lines.Count; $i++) {
          if ($lines[$i] -match 'STRM: Adding racecar for streaming: car=(?<s>[1-7]), model=VEH_(?<m>[A-Z0-9_]+)') {
            $adds += ("slot {0} {1}" -f $Matches.s, $Matches.m)
            if ($req.ContainsKey($Matches.m)) { $hits++ }
          }
          if ($lines[$i] -match '=== CarSelectManager: Start Exit state') { break }
        }
        return @{ Pass = ($hits -ge 1); Detail = ("{0} slot-1..7 adds before the exit, {1} of them a car the first request named: {2}" -f $adds.Count, $hits, (($adds | Select-Object -First 6) -join '; ')) }
      } }

    @{ Kind = 'LogMatch'; Name = 'action 69 reached RaceCarEntityModule::HandleGameActions (88-byte record)'; Pattern = '\[rcem-action\] id 69 size 88 ' }
    @{ Kind = 'LogMatch'; Name = 'the livery screen posts its livery list (action 69)'; Pattern = '\[carsel\] livery action69 car=\d+ count=[2-8] ' }
  )
}
