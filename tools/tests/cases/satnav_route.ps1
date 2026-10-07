# satnav_route -- BurnoutDecomp/b5-decomp#25 (sat-nav): the tracker asks the game for a route.
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case satnav_route
#
# THE CHAIN (console): a GuiEventSetTracker (GUI 232) with two or more landmarks reaches
# GuiTracker::RecEvent, which arms mbRouteDataPending. The next GuiModule::Update runs
# GuiTracker::Update: it builds a CalculateRoute for leg [miNumRouteInfoReceived] (tracker record
# n -> record n+1, each end filled by ContructRouteNodeFromTrackedItem from the landmark's
# GuiCache::GetLandmarkInfoFromIndex record) and posts it as GUI out event 494.
# BrnGameModule::BridgeGuiToGameState repacks 494 into game event 84 (LandmarkRouteRequestEvent).
#
# THE LEVER: every offline event carries 0 or 1 checkpoints (measured over all 120 events of
# PROGRESSION.DAT), so no offline tracked set ever owes a route leg; multi-landmark sets come from
# the online route screens. BRN_SATNAV_ROUTE_TEST=<a>:<b> (PC test hook in
# BrnGuiTracker_wY_00.cpp, off by default) takes the landmarks at positions a and b of the
# trigger data's landmark list, turns each into its LandmarkIndex (the landmark's trigger-REGION
# index, which is what GetLandmarkInfoFromIndex matches) and publishes the pair through the real
# GuiCache::UpdateTrackerInfo once the free-roam HUD is up (+~2 s): the offline RefreshMapState
# publisher with a two-landmark list. (Published during loading, as the first cut did, the 494 is
# cleared before BrnGameModule's in-game-only DoUpdate_GameStatePostWorld ever bridges it.)
#
# THE DATA (retail TRIGGERS.DAT, 105 landmarks, regions 4670..4774 in list order):
#   list 0 -> region 4670, CgsID 557321   list 1 -> region 4671, CgsID 557289
# The first run passed 0,1 straight through as LandmarkIndex values: no landmark owns region 0
# or 1, every lookup missed ("Unable to find landmark with index: 0"), and the route carried
# residue ids.
#
# THE REPLY: GameStateModule::ProcessGameEvents case 84 (ProcessGameEventsLandmarkRouteRequestBringUp)
# hands event 84 to SendRouteRequestAction with owner E_OWNER_GUI (1), which resolves both ends to AI
# sections and posts action 50; the AI module queues it for the route planner; the E_OWNER_GUI
# route response comes back in the world output, and BrnGameModule::BridgeWorldRouteInformationToGui
# turns it into a 211 route record handed straight to GuiTracker::RecEvent. A two-landmark set owes
# one leg, so that one record completes it: GenerateRouteData raises mbHasRoute and
# IsRouteInfoAvailable() goes true (a route of >= 2 points). No second leg is ever requested.
#
# WITNESSES (BRN_SATNAV_DIAG, plus BRN_ROUTE_INFO_DIAG for the section pair):
#   [satnav] TEST HOOK list positions <a>,<b> publishes landmarks <region a>,<region b>
#   [satnav-tracker] GuiCache::UpdateTrackerInfo -> GuiTracker::RecEvent(232) items=2 ...
#   [satnav] route requested leg <n> types <t0>,<t1> landmarks <id0>,<id1> junctions <j0>,<j1>
#   [satnav] event 84 -> SendRouteRequestAction owner GUI leg <n>
#   [route-info] SendRouteRequestAction owner 1 event <n> sections <s0> -> <s1>
#   [satnav] route reply 211 leg <n> points <p> distance <d> routeInfoAvailable <0|1>
@{
  Name    = 'satnav_route'
  Area    = 'ui/satnav'
  Bug     = 'BurnoutDecomp/b5-decomp#25 -- GuiTracker::Update never ran, so the sat-nav never asked for a route'
  Frames  = $false
  Run     = @{
    Drive       = $true
    MotionProbe = $true
    MaxSeconds  = 50
    SkipIntro   = $true
    AcceptGap   = 1.0
    Teleport    = '3040.7,-5.8,-1937.9,180'   # the road outside the junkyard exit (baseline's)
    ThrottleScript = '0:accel'
  }
  DiagEnv = 'BRN_SATNAV_DIAG=1,BRN_SATNAV_ROUTE_TEST=0:1,BRN_ROUTE_INFO_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'LogCount';   Name = 'the test hook published list 0,1 as regions 4670,4671 once';
       Pattern = '\[satnav\] TEST HOOK list positions 0,1 publishes landmarks 4670,4671'; Min = 1; Max = 1 }
    @{ Kind = 'LogCount';   Name = 'every landmark lookup hit'; Pattern = 'Unable to find landmark with index'; Max = 0 }
    @{ Kind = 'LogMatch';   Name = 'the two-landmark set reached GuiTracker::RecEvent(232)';
       Pattern = '\[satnav-tracker\] GuiCache::UpdateTrackerInfo -> GuiTracker::RecEvent\(232\) items=2 current=0 entireRoute=1' }
    # GuiTracker::Update requests leg 0 of the set exactly once (the pending flag drops after the
    # post; the one 211 reply completes a two-landmark set instead of re-arming it).
    @{ Kind = 'LogCount';   Name = 'GUI 494 posted once for leg 0'; Pattern = '\[satnav\] route requested leg 0 '; Min = 1; Max = 1 }
    @{ Kind = 'LogCount';   Name = 'no second leg is ever requested'; Pattern = '\[satnav\] route requested leg 1 '; Max = 0 }
    @{ Kind = 'Script';     Name = 'both ends are LANDMARK ends with two distinct non-zero landmark ids'; Script = {
        param($ctx)
        foreach ($line in $ctx.LogLines) {
          if ($line -match '\[satnav\] route requested leg 0 types (?<t0>-?\d+),(?<t1>-?\d+) landmarks (?<a>\d+),(?<b>\d+) junctions (?<j0>\d+),(?<j1>\d+)') {
            $ok = ($Matches.t0 -eq '0') -and ($Matches.t1 -eq '0') -and ($Matches.a -ne '0') -and ($Matches.b -ne '0') `
                  -and ($Matches.a -ne $Matches.b) -and ($Matches.j0 -eq '0') -and ($Matches.j1 -eq '0')
            return @{ Pass = $ok; Detail = ("types {0},{1} landmarks {2},{3} junctions {4},{5}" -f `
                      $Matches.t0, $Matches.t1, $Matches.a, $Matches.b, $Matches.j0, $Matches.j1) }
          }
        }
        return @{ Pass = $false; Detail = 'no [satnav] route requested leg 0 line' }
      } }
    @{ Kind = 'LogMatch';   Name = 'leg 0 runs from landmark 557321 to landmark 557289';
       Pattern = '\[satnav\] route requested leg 0 types 0,0 landmarks 557321,557289 junctions 0,0' }
    # THE REPLY. Case 84 reaches SendRouteRequestAction once, with the GUI as owner.
    @{ Kind = 'LogCount';   Name = 'event 84 -> SendRouteRequestAction (owner GUI) once for leg 0';
       Pattern = '\[satnav\] event 84 -> SendRouteRequestAction owner GUI leg 0\s*$'; Min = 1; Max = 1 }
    @{ Kind = 'Script';     Name = 'the GUI route question resolved both landmarks to valid AI sections'; Script = {
        param($ctx)
        foreach ($line in $ctx.LogLines) {
          if ($line -match '\[route-info\] SendRouteRequestAction owner 1 event 0 sections (?<s0>\d+) -> (?<s1>\d+)') {
            $ok = ([int]$Matches.s0 -ne 32767) -and ([int]$Matches.s1 -ne 32767)
            return @{ Pass = $ok; Detail = ("sections {0} -> {1}" -f $Matches.s0, $Matches.s1) }
          }
        }
        return @{ Pass = $false; Detail = 'no [route-info] SendRouteRequestAction owner 1 line' }
      } }
    # BridgeWorldRouteInformationToGui hands the tracker one 211 record for leg 0 and the route
    # becomes available (GenerateRouteData ran: >= 2 points, mbHasRoute raised).
    @{ Kind = 'LogCount';   Name = 'exactly one 211 route reply'; Pattern = '\[satnav\] route reply 211 leg '; Min = 1; Max = 1 }
    @{ Kind = 'Script';     Name = 'the leg-0 reply carries a real route and IsRouteInfoAvailable() is true'; Script = {
        param($ctx)
        foreach ($line in $ctx.LogLines) {
          if ($line -match '\[satnav\] route reply 211 leg (?<leg>\d+) points (?<p>\d+) distance (?<d>[-0-9.eE+]+) routeInfoAvailable (?<a>\d)') {
            $lfD = [double]::Parse($Matches.d, [System.Globalization.CultureInfo]::InvariantCulture)
            $ok = ($Matches.leg -eq '0') -and ([int]$Matches.p -ge 2) -and ($lfD -gt 0.0) -and ($Matches.a -eq '1')
            return @{ Pass = $ok; Detail = ("leg {0} points {1} distance {2} available {3}" -f $Matches.leg, $Matches.p, $Matches.d, $Matches.a) }
          }
        }
        return @{ Pass = $false; Detail = 'no [satnav] route reply 211 line' }
      } }
  )
}
