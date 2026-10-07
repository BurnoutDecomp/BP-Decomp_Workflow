# satnav_route_frames -- BurnoutDecomp/b5-decomp#25 (sat-nav): what the player sees with a route set.
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case satnav_route_frames
#
# The satnav_route lever (BRN_SATNAV_ROUTE_TEST=0:1, see satnav_route.ps1) with frames: the
# tracker gets the two-landmark set once the free-roam HUD is up, the route reply arrives, then the
# car coasts to a stop and the pause map opens (-PauseAt / -PauseTarget map). Frames every 60
# presents: the minimap before/after the reply, then the big map with the set tracked.
# BRN_MAPTEXT_DIAG adds the crash-nav icon pool witness ([maptext] crashnav slot N type T state S):
# a tracked landmark (icon type 4) shows a tracked/finish state there.
#
# This is a LOOK case: the gate checks only prove the route was set before the map opened.
@{
  Name    = 'satnav_route_frames'
  Area    = 'ui/satnav'
  Bug     = 'BurnoutDecomp/b5-decomp#25 -- sat-nav route set: minimap + big map frames'
  Frames  = $true
  Run     = @{
    Drive          = $true
    MaxSeconds     = 60
    SkipIntro      = $true
    AcceptGap      = 1.0
    Teleport       = '3040.7,-5.8,-1937.9,180'   # the road outside the junkyard exit (baseline's)
    ThrottleScript = '0:accel,3:none'
    PauseAt        = '14'
    PauseTarget    = 'map'
    FrameEvery     = 60
  }
  DiagEnv = 'BRN_SATNAV_DIAG=1,BRN_SATNAV_ROUTE_TEST=0:1,BRN_ROUTE_INFO_DIAG=1,BRN_MAPTEXT_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'LogCount';   Name = 'the leg-0 route reply arrived once'; Pattern = '\[satnav\] route reply 211 leg 0 '; Min = 1; Max = 1 }
    @{ Kind = 'Script';     Name = 'the route was set before the map claimed the icon manager'; Script = {
        param($ctx)
        $liReply = -1; $liMap = -1
        for ($i = 0; $i -lt $ctx.LogLines.Count; $i++) {
          $line = $ctx.LogLines[$i]
          if ($liReply -lt 0 -and $line -match '\[satnav\] route reply 211 leg 0 ') { $liReply = $i }
          if ($liMap -lt 0 -and $line -match '\[maptext\] crashnav slot ') { $liMap = $i }
        }
        $ok = ($liReply -ge 0) -and ($liMap -gt $liReply)
        return @{ Pass = $ok; Detail = ("reply at log line {0}, first crash-nav slot line {1}" -f ($liReply + 1), ($liMap + 1)) }
      } }
  )
}
