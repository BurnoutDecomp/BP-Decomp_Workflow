# drivethru_gas_station -- the gas-station refill, end to end, plus its free-roam HUD messages.
#
# THE SCENARIO. The player car is placed 26 m short of the GAS STATION drive-thru bay id 221845 and
# told to hold the throttle for 4 s, then coast (the same shape as drivethru_body_shop). The bay is
# GenericRegion sub-type 1 (GAS_STATION) at (1490.98, 2.05, -2181.22), rot (-pi, 0.6667, -pi), box
# 15.06 x 5.00 x 24.81, not one-way -- read out of the shipped build\game\TRIGGERS.DAT (region
# index 4668; id word 221845) with scratch\gameplay_wave\FREE\gasscan.py, the same reader as
# scratch\bugtest\drivethru\dtscan.py. That rotation is a yaw of pi - 0.6667 = 141.8 deg, so the
# box's long (local Z) axis points along (0.618, 0, -0.786); the start point is 26 m back along
# it, (1474.9, 2.2, -2160.8), facing 141.8 deg (the teleport heading is degrees clockwise from +Z).
# FLAG: this approach is computed from the region box, not driven yet -- if the car hits a wall
# before the bay, re-aim from the [motion] samples of the first run.
#
# WHAT IT MEASURES
#   (a) the refill chain: the manager's ENTER (type 1, id 221845) -> its POST of action 100 -> the
#       bridge's action 100 -> GUI 366 -> the race-car module's GAS REFILL line, whose boost after
#       the refill must not be below the boost before it.
#   (b) the free-roam translator: junkyard 99 -> GUI 79 on the boot, and drive-thru discovered
#       104 -> GUI 314 (type 1) only when the profile had not found this station before.
#   plus: no NEW assert family, no exception.
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case drivethru_gas_station
#
@{
  Name    = 'drivethru_gas_station'
  Area    = 'ui'
  Bug     = 'gas-station refill (trigger 221845) was never witnessed; free-roam HUD messages were not translated'
  Frames  = $false
  Run     = @{
    Drive          = $true
    MotionProbe    = $true
    MaxSeconds     = 60
    SkipIntro      = $true      # the console -skipvideos latch
    AcceptGap      = 1.0        # harness pump latency, not a game gate
    Teleport       = '1474.9,2.2,-2160.8,141.8'   # 26 m up the bay's long axis, facing into it
    ThrottleScript = '0:accel,4:none'             # roll in, then coast
  }
  # BRN_DRIVETHRU_DIAG arms the manager's GATE/ENTER/POST rungs; BRN_FREEROAM_DIAG arms the
  # `[freeroam-gui] action A -> gui G (detail)` line.
  DiagEnv = 'BRN_DRIVETHRU_DIAG=1,BRN_FREEROAM_DIAG=1'
  Checks  = @(
    @{ Kind='Mark';       Name='reached DRIVING'; Phase='DRIVING' }

    # ---- (a) the refill chain ---------------------------------------------------------------
    @{ Kind='LogMatch'; Name='the gas station 221845 triggered'; Pattern='\[drivethru\] ENTER type=1 id=221845\b' }
    @{ Kind='LogMatch'; Name='the manager posted gas action 100'; Pattern='\[drivethru\] POST gas action=100' }
    @{ Kind='LogMatch'; Name='the bridge translated action 100 to GUI 366'; Pattern='\[drivethru\] BRIDGE action=100 -> gui 366' }
    @{ Kind='Script'; Name='the refill ran and did not lower the boost'; Script = {
        param($ctx)
        $hit = $ctx.LogLines | Where-Object { $_ -match '\[drivethru\] GAS REFILL boost (?<b>-?[\d.eE+-]+) -> (?<a>-?[\d.eE+-]+)' } | Select-Object -First 1
        if ($null -eq $hit) { return @{ Pass = $false; Detail = 'no [drivethru] GAS REFILL line' } }
        $null = $hit -match '\[drivethru\] GAS REFILL boost (?<b>-?[\d.eE+-]+) -> (?<a>-?[\d.eE+-]+)'
        $inv = [System.Globalization.CultureInfo]::InvariantCulture
        $before = [double]::Parse($Matches['b'], $inv); $after = [double]::Parse($Matches['a'], $inv)
        return @{ Pass = ($after -ge $before -and $after -gt 0); Detail = ("boost {0} -> {1} (want after >= before and > 0)" -f $before, $after) }
    } }

    # ---- (b) the free-roam HUD messages -----------------------------------------------------
    @{ Kind='LogMatch'; Name='junkyard action 99 translated to GUI 79'; Pattern='\[freeroam-gui\] action 99 -> gui 79 ' }
    # A station published by the boot SETUP (the profile already knows it) must not post 104; an
    # unknown one must post 104 -> 314 with type 1 (GAS_STATION) after its ENTER.
    @{ Kind='Script'; Name='a first visit posts drive-thru discovered 104 -> GUI 314 (type 1); a known station does not'; Script = {
        param($ctx)
        $lines = $ctx.LogLines
        $enterAt = -1
        for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -match '\[drivethru\] ENTER type=1 id=221845\b') { $enterAt = $i; break } }
        if ($enterAt -lt 0) { return @{ Pass = $false; Detail = 'no [drivethru] ENTER type=1 id=221845 line: the station never triggered' } }
        $known = $false
        for ($i = 0; $i -lt $enterAt; $i++) { if ($lines[$i] -match '\[drivethru\] SETUP rec id=221845\b') { $known = $true; break } }
        $posted = @()
        for ($i = $enterAt; $i -lt $lines.Count; $i++) { if ($lines[$i] -match '\[freeroam-gui\] action 104 -> gui 314 \((\d+)\)') { $posted += [int]$Matches[1] } }
        if ($known) {
          return @{ Pass = ($posted.Count -eq 0); Detail = ("station already known at boot; 104 -> 314 lines after ENTER: {0} (want 0)" -f $posted.Count) }
        }
        return @{ Pass = ($posted.Count -ge 1 -and $posted[0] -eq 1); Detail = ("station discovered this run; 104 -> 314 lines after ENTER: {0}, first type {1} (want >= 1, type 1)" -f $posted.Count, $(if ($posted.Count) { $posted[0] } else { '-' })) }
    } }

    # ---- the usual floor --------------------------------------------------------------------
    @{ Kind='NewAsserts'; Name='no NEW assert families' }
    @{ Kind='LogCount';   Name='no exceptions'; Pattern='\[EXCEPTION\]'; Max=0 }
  )
}
