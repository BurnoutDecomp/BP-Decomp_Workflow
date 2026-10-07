# paint_shop -- lane CARSEL, gameplay wave GW4 (census item 6: "no case covers the shop; a palette
# crash was seen earlier").
#
# THE SCENARIO. Returning player on the box save. The car is placed 26 m up the long axis of the
# PAINT SHOP drive-thru bay at (2907.29, 2.62, -1595.18), rot (-pi, 1.0009, -pi), box 10 x 5 x 14
# (read from the shipped TRIGGERS.DAT with scratch\bugtest\drivethru\dtscan.py). That rotation is a
# yaw of pi - 1.0009 = 122.65 deg (same convention as drivethru_gas_station), so the seat is
# centre - 26 * (sin 122.65, cos 122.65) = (2885.4, -1581.2), facing 122.65 deg. Throttle 4 s, coast.
#
# WHAT THE SHOP DOES (DriveThruManager::ProcessDriveThru, PAINT arm): read the car's colour, force
# palette 2, advance the colour by one modulo palette 2's colour count (the read that used to fault
# on an unloaded CarColours palette), post game action 98, store the colour on the profile car,
# request an autosave. RaceCarEntityModule case 98 repaints the player's global race car and
# asserts the palette/colour are in range.
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case paint_shop
#
@{
  Name           = 'paint_shop'
  Area           = 'gamestate/drivethru'
  Bug            = 'GW4 census #6 -- paint shop drive-thru: palette read faulted on an unloaded CarColours resource; no case drove one'
  Frames         = $true
  ProfileFixture = 'scratch\gameplay_wave\profile_backup\Profile.sav.pose250700'
  Run            = @{
    Drive          = $true
    MotionProbe    = $true
    MaxSeconds     = 60
    SkipIntro      = $true
    AcceptGap      = 1.0
    Teleport       = '2885.4,2.8,-1581.2,122.65'
    ThrottleScript = '0:accel,4:none'
    FrameEvery     = 60
  }
  DiagEnv = 'BRN_DRIVETHRU_DIAG=1,BRN_RCEM_ACTION_DIAG=1,BRN_CARSEL_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'LogMatch';   Name = 'the paint shop drive-thru triggered'; Pattern = '\[drivethru\] ENTER type=3 ' }
    @{ Kind = 'LogMatch';   Name = 'palette 2 was read from a loaded CarColours resource (colour count > 0) and action 98 posted';
       Pattern = '\[drivethru\] POST paint action=98 colour=\d+ palette=2 \(palette colours [1-9]\d*\)' }
    @{ Kind = 'Script'; Name = 'the advanced colour is inside palette 2 (more than one colour, index below the count)'; Script = {
        param($ctx)
        $hit = $ctx.LogLines | Where-Object { $_ -match '\[drivethru\] POST paint action=98 colour=(?<c>\d+) palette=2 \(palette colours (?<n>\d+)\)' } | Select-Object -First 1
        if ($null -eq $hit) { return @{ Pass = $false; Detail = 'no POST paint line' } }
        $null = $hit -match 'colour=(?<c>\d+) palette=2 \(palette colours (?<n>\d+)\)'
        $c = [int]$Matches.c; $n = [int]$Matches.n
        return @{ Pass = ($n -gt 1 -and $c -lt $n); Detail = ("colour {0} of {1} in palette 2" -f $c, $n) }
      } }
    @{ Kind = 'LogMatch'; Name = 'the race-car module consumed action 98 (the repaint arm ran)'; Pattern = '\[rcem-action\] id 98 size ' }
  )
}
