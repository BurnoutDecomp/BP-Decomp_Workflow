# minimap_drivethru_blips -- BurnoutDecomp/b5-decomp#9: "minimap: no blips" (no icons for events,
# drive-throughs, the junkyard ...). The sat-nav drew the map tile and the player arrow only.
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case minimap_drivethru_blips
#
# THE CHAIN (console), drive-thru half: GameStateModule::PreWorldUpdate drains the progression
# manager's drive-thru-data dirty byte and, when it was set, runs SendSetUpAllDriveThrusMessage:
# every DISCOVERED drive-thru region -> one DriveThruInfo {x, z, id, type} -> game action 45.
# BrnGameModule::TranslateGameActionsToGuiEvents turns action 45 into GuiEventUpdateSatNav (199)
# records of icon type 7/8/9/10/11/12, posted once at the end of the drain; GuiCache::RecEvent's
# case-199 drive-thru arm stores them (dedupe by id, 15 canned position overrides) in its
# drive-through table; MapIconManager::UpdateWorldIcons appends the in-view ones (plus the nearest
# junkyard / body shop volunteers) to the icon set every sat-nav frame, and the icon pass drives an
# apt SatNavMapIcon into the matching state (41 junkyard, 43 body shop, 44 gas, 45 paint).
# Events half: GuiCache::Construct seeds the sat-nav event filter ENABLED (filter 6 == all modes);
# the freeburn HUD mirrors it into the id-204 enable event that raises the renderer's
# mbRenderEventStarts, without which RenderIconsForSatNav returns before drawing any event icon.
#
# THE SCENARIO reuses drivethru_body_shop's approach: 26 m short of the River City BODY SHOP bay,
# throttle held, so the run (a) publishes whatever the profile already discovered at boot and
# (b) either DISCOVERS this shop live (dirty byte re-raised, table re-published) or, on a profile that
#     already knows it, drives onto a shop that the boot publish must already carry.
# The car then sits inside the bay, so that body shop is inside the minimap's view rect.
#
# WITNESSES (all unconditional, bounded, on the existing tags):
#   [drivethru] SETUP rec id=<id> type=<t> pos=(x,z)   the producer, per published record
#   [drivethru] SETUP: posted action 45 with N ...      the producer, per publish
#   [drivethru] BRIDGE: action 45 -> gui 199 with N    the bridge's tail post
#   [satnav-diag] cache 199 drive-thru row R id=<id>   the cache's table append
#   [satnav-icon] slot S type T state ST id=<id> ...   the icon pass (every 300 ticks, all slots)
#   [satnav-diag] event icons: N cached ...            the renderer past its enable gate
#   [drivethru] ENTER type=2 id=<id>                   the manager (BRN_DRIVETHRU_DIAG)
#
# THE ORACLE pairs producer and consumer BY ID: an icon the pass drove into a drive-thru state must
# carry an id the producer published from the region table, and the body shop the car drove
# through (the manager's own ENTER id) must be re-published after the ENTER. Neither check knows
# a formula from the fix. RED (before): none of the SETUP / BRIDGE / row / drive-thru-state lines
# exist and the event-icon gate never opens. GREEN: all of them, with matching ids.
# (The ENTER check accepts a boot-time publish: a shop the profile already knows is published once at
#  boot and, exactly like the console, NOT again after its ENTER -- only a new discovery re-publishes.)
@{
  Name    = 'minimap_drivethru_blips'
  Area    = 'ui'
  Bug     = 'BurnoutDecomp/b5-decomp#9 -- minimap: no blips for events / drive-throughs / junkyard'
  Frames  = $true
  Run     = @{
    Drive          = $true
    MotionProbe    = $true
    MaxSeconds     = 60
    SkipIntro      = $true
    AcceptGap      = 1.0
    Teleport       = '917.0,23.9,-1357.0,180'   # 26 m up the body-shop approach lane, facing the bay
    ThrottleScript = '0:accel,4:none'           # roll in; the shop stops the car itself
    FrameEvery     = 60
  }
  DiagEnv = 'BRN_DRIVETHRU_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions';  Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'LogCount';   Name = 'the drive-thru table was published (action 45)'; Pattern = '\[drivethru\] SETUP: posted action 45 with'; Min = 1 }
    @{ Kind = 'LogCount';   Name = 'the bridge posted it as GUI event 199'; Pattern = '\[drivethru\] BRIDGE: action 45 -> gui 199 with'; Min = 1 }
    @{ Kind = 'LogCount';   Name = 'the GUI cache stored at least one drive-thru row'; Pattern = '\[satnav-diag\] cache 199 drive-thru row'; Min = 1 }
    @{ Kind = 'LogCount';   Name = 'the renderer passed its event-icon enable gate'; Pattern = '\[satnav-diag\] event icons:'; Min = 1 }
    # THE BUG: the icon pass must drive a pool slot into a drive-thru state, and that slot's id must
    # be one the producer read off the region table.
    @{ Kind = 'Script';     Name = 'a drive-thru icon is drawn (state 41/43/44/45) with an id the producer published'; Script = {
        param($ctx)
        $published = @{}
        $drawn = @(); $matched = 0
        foreach ($line in $ctx.LogLines) {
          if ($line -match '\[drivethru\] SETUP rec id=(?<id>\d+) type=(?<t>\d+)') { $published[$Matches.id] = [int]$Matches.t }
          elseif ($line -match '\[satnav-icon\] slot \d+ type (?<t>\d+) state (?<s>\d+) id=(?<id>\d+)') {
            $s = [int]$Matches.s
            if ($s -eq 41 -or $s -eq 43 -or $s -eq 44 -or $s -eq 45) {
              $drawn += $Matches.id
              if ($published.ContainsKey($Matches.id)) { $matched++ }
            }
          }
        }
        $ok = ($drawn.Count -ge 1) -and ($matched -eq $drawn.Count)
        return @{ Pass = $ok; Detail = ("{0} drive-thru icon draws, {1} with a published id; {2} ids published" -f $drawn.Count, $matched, $published.Count) }
      } }
    # THE SHOP UNDER THE CAR: the body shop the car drove through (the manager's own ENTER id) must
    # be in the published table -- published at boot when the profile already knows it (the
    # console re-publishes only on a NEW discovery, so an already-known shop rightly gets no second
    # SETUP after its ENTER), or by the discovery re-publish when it did not.
    @{ Kind = 'Script';     Name = 'the shop driven through is in the published drive-thru table'; Script = {
        param($ctx)
        $enterId = $null; $published = @{}
        foreach ($line in $ctx.LogLines) {
          if ($line -match '\[drivethru\] SETUP rec id=(?<id>\d+) ') { $published[$Matches.id] = $true }
          elseif ($null -eq $enterId -and $line -match '\[drivethru\] ENTER type=\d+ id=(?<id>\d+)') { $enterId = $Matches.id }
        }
        if ($null -eq $enterId) { return @{ Pass = $false; Detail = 'no [drivethru] ENTER line -- the car never reached the bay' } }
        return @{ Pass = $published.ContainsKey($enterId); Detail = ("ENTER id={0} published={1} ({2} ids in the table)" -f $enterId, $published.ContainsKey($enterId), $published.Count) }
      } }
  )
}
