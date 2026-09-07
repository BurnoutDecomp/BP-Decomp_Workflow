# minimap_player_arrow -- BurnoutDecomp/b5-decomp#7: "minimap: Player arrow is inverted on one axis".
# The yellow player arrow on the sat-nav pointed the wrong way: mirrored about the map's vertical
# axis, so a car heading north-east was drawn heading north-west.
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case minimap_player_arrow
#
# THE CHAIN (console): BrnGameModule::BridgeWorldVehicleDataToGui @0x823E5768 posts one
# GuiEventUpdateSatNav (199) record per car each frame; its mfRotation is the heading of the car's
# At vector against north (0,0,1) -- acos(dot), then 2pi - acos when cross(north, at) . up < 0,
# i.e. when at.x < 0 (@0x823E5FC0..0x823E6178). MapIconManager::UpdateSatNavIcons @0x82522588
# turns it into the arrow sprite's rotation (pi - heading on the fixed map) and SatNavMapIcon::Update
# publishes that as the apt "_rotation" in degrees. On the fixed map screen-right is world +X and
# screen-down is world +Z, and apt rotates clockwise from screen-up, so an arrow at rotation R points
# along (sin R, -cos R) on screen == (sin R, -cos R) in world (x, z).
#
# WITNESS (opt-in via BRN_SATNAV_DIAG, ~4 Hz, capped):
#   [satnav-arrow] pos=<x>,<z> heading=<rad> apt=<deg> rotate=<0|1>
#     pos     the icon record's world position lane
#     heading the record's mfRotation as the bridge posted it
#     apt     the "_rotation" degrees the arrow sprite receives for it
#
# THE ORACLE is the car itself: between two witness samples the car moved by (dx, dz), so the arrow
# must point along that -- apt == atan2(dx, -dz). No formula from the fix is in the check; a mirrored
# heading fails it by twice the car's angle off the +-Z axis. The scenario therefore CIRCLES (throttle
# pulses under a held left lock) so the headings sweep the compass; a straight run down a +-Z road
# would pass even on the broken build, which is what the off-axis-sample floor below guards.
#
# RED (before the fix): mean error ~90 deg on the circling samples. GREEN: a few degrees.
@{
  Name    = 'minimap_player_arrow'
  Area    = 'ui'
  Bug     = 'BurnoutDecomp/b5-decomp#7 -- minimap player arrow inverted on one axis'
  Frames  = $false
  Run     = @{
    Drive          = $true
    MotionProbe    = $true            # [motion] samples carry the car's At vector (the producer-side check)
    MaxSeconds     = 55
    SkipIntro      = $true
    AcceptGap      = 1.0
    Teleport       = '3040.7,-5.8,-1937.9,180'   # the road outside the junkyard exit (baseline's)
    SteerScript    = '0:none,3:left'             # straight for 3 s, then hold left lock (a circle)
    ThrottleScript = '0:accel,4:none,9:accel,12:none,17:accel,20:none,25:accel,28:none,33:accel'
  }
  DiagEnv = 'BRN_SATNAV_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions';  Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'LogCount';   Name = 'the arrow witness fired'; Pattern = '\[satnav-arrow\] pos='; Min = 20 }
    # THE BUG: the arrow must point where the car goes. Consecutive witness samples give the motion
    # direction (dx, dz) in world XZ; the sprite's apt rotation must be atan2(dx, -dz) on the fixed
    # map. Samples closer than 1.5 m (parked / creeping) say nothing about direction and are skipped;
    # a >20 m step is a placement, not driving.
    @{ Kind = 'Script';     Name = 'arrow apt rotation follows the direction of motion (mean |err| < 25 deg, >= 8 off-axis samples)'; Script = {
        param($ctx)
        $errs = @(); $offAxis = 0; $px = $null
        foreach ($line in $ctx.LogLines) {
          if ($line -match '\[satnav-arrow\] pos=(?<x>-?[\d.]+),(?<z>-?[\d.]+) heading=(?<h>-?[\d.]+) apt=(?<a>-?[\d.]+) rotate=(?<r>\d)') {
            $x = [double]$Matches.x; $z = [double]$Matches.z; $apt = [double]$Matches.a
            if ($null -ne $px) {
              $dx = $x - $px; $dz = $z - $pz
              $d = [math]::Sqrt($dx*$dx + $dz*$dz)
              if ($d -ge 1.5 -and $d -lt 20) {
                $exp = [math]::Atan2($dx, -$dz) * 180.0 / [math]::PI
                $e = ((($apt - $exp) % 360.0) + 540.0) % 360.0 - 180.0
                $errs += [math]::Abs($e)
                # off-axis: the motion is more than 30 deg from the +-Z axis, where a mirror shows
                if ([math]::Abs($dx) -gt 0.5 * $d) { $offAxis++ }
              }
            }
            $px = $x; $pz = $z
          }
        }
        if ($errs.Count -lt 8) { return @{ Pass = $false; Detail = ("only {0} moving samples" -f $errs.Count) } }
        $mean = ($errs | Measure-Object -Average).Average
        $sorted = $errs | Sort-Object
        $median = $sorted[[int][math]::Floor($sorted.Count / 2)]
        $ok = ($mean -lt 25.0) -and ($offAxis -ge 8)
        return @{ Pass = $ok
                  Detail = ("mean|err|={0:N1} deg median={1:N1} deg over {2} moving samples ({3} off-axis)" -f $mean, $median, $errs.Count, $offAxis) }
      } }
    # THE PRODUCER: the posted heading against the car's own At vector from the nearest preceding
    # [motion] sample -- the console's atan2(at.x, at.z) (acos + the cross(north, at).up sign). A
    # mirrored producer reads -heading here.
    @{ Kind = 'Script';     Name = 'posted heading == atan2(at.x, at.z) of the car (mean |err| < 0.25 rad)'; Script = {
        param($ctx)
        $errs = @(); $atx = $null; $off = 0
        foreach ($line in $ctx.LogLines) {
          if ($line -match '\[motion\] n \d+ pos -?[\d.]+ -?[\d.]+ -?[\d.]+ at (?<ax>-?[\d.]+) (?<ay>-?[\d.]+) (?<az>-?[\d.]+) ') {
            $atx = [double]$Matches.ax; $atz = [double]$Matches.az
          }
          elseif ($null -ne $atx -and $line -match '\[satnav-arrow\] pos=[^ ]+ heading=(?<h>-?[\d.]+) ') {
            $h = [double]$Matches.h
            $exp = [math]::Atan2($atx, $atz); if ($exp -lt 0) { $exp += 2.0 * [math]::PI }
            $e = $h - $exp
            while ($e -gt [math]::PI) { $e -= 2.0 * [math]::PI }
            while ($e -lt -[math]::PI) { $e += 2.0 * [math]::PI }
            $errs += [math]::Abs($e)
            if ([math]::Abs($atx) -gt 0.5) { $off++ }
          }
        }
        if ($errs.Count -lt 8) { return @{ Pass = $false; Detail = ("only {0} paired samples" -f $errs.Count) } }
        $mean = ($errs | Measure-Object -Average).Average
        return @{ Pass = (($mean -lt 0.25) -and ($off -ge 8))
                  Detail = ("mean|err|={0:N3} rad over {1} paired samples ({2} off-axis)" -f $mean, $errs.Count, $off) }
      } }
  )
}
