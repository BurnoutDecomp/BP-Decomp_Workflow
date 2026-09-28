# ai_angles_long_jump -- issue #31: the AI angle helpers must stay quiet when the player car falls
# a long way (a long jump, or a debug fly far above the road).
#
# THE CHAIN. Every AIDriver (the player's own included) runs SteeringFan::UpdateWeightings ->
# GenerateFanVectors on its round-robin turn. GenerateFanVectors flattens AICar::GetUsefulDirection
# to (x,z) and normalises it with no zero guard, then measures the fan's base angle with
# FindSignedAngleBetween2DVectors. Issue #31's log has 134 "NAN error in
# AIDriver::FindSignedAngleBetween2DVectors" asserts and then the racing-line hermite cascade
# (Bad interp / Bad in interp / NAN in iterative hermite ...) the NaN fan targets fed, with the car
# dropping ~26 m straight down at a fixed (x,z). Two defects made that: GetUsefulDirection gated
# on the 3D velocity (a vertical fall returned (0,-1,0), a zero-length (x,z) heading), and
# FindUnsignedAngleBetween2DVectors reached the arc-cosine for a NaN dot (the console returns 0.0
# there, which sends FindSignedAngleBetween2DVectors down its zero early-out before either assert).
#
# THE SCENARIO. flow_run's -Jump recipe: ten launches up the measured bridge-crest ramp at
# x~3028 (20..62 m/s), every one a real long jump, in one boot. BRN_AIR_DIAG=1 prints one `[air]`
# line per flight (duration, peak, distance), so "the car really flew" is a check, not a claim.
# (A teleport into the air is no stimulus: RequestPlaceOnTrack's +-50 m line test finds nothing
# above ~50 m and reverts to the reset ring buffer, seating the car back on the road.)
#
# WHY NO `degenerate` LINE IS EXPECTED. AICar::GetUsefulDirection gates both arms on a Y-zeroed
# copy (velocity, then facing), so a car whose speed is mostly vertical reports its facing and
# the fan's flattened heading always has length. The pre-flatten build returned
# Normalize((0,-v,0)) for a vertical fall -- the zero-length heading the issue log shows.
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case ai_angles_long_jump
#
@{
  Name    = 'ai_angles_long_jump'
  Area    = 'ai'
  Bug     = 'issue #31: AI angle helpers assert (NaN) after a long fall / long jump'
  Frames  = $false
  Run     = @{
    Drive       = $true
    MotionProbe = $true
    MaxSeconds  = 110
    SkipIntro   = $true
    AcceptGap   = 1.0
    Jump        = $true                 # ten ramp launches, 20..62 m/s, 7 s apart
  }
  DiagEnv = 'BRN_AI_NAN=1,BRN_AIR_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions';   Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }

    # The probe is live (positive control), the car flew, and no flight fed a zero-length heading.
    @{ Kind = 'LogMatch';   Name = 'ai-nan probe live (first control line)'
       Pattern = '\[ai-nan\] first\(control\) '; Expect = $true }
    @{ Kind = 'LogValue';   Name = 'the car really flew (longest [air] flight >= 1.5 s)'
       Pattern = '\[air\] car \d+ .* dur (?<d>[\d.]+) '; Group = 'd'; Agg = 'max'; Min = 1.5 }
    @{ Kind = 'LogCount';   Name = 'no zero-length (x,z) heading reached the fan'
       Pattern = '\[ai-nan\] degenerate '; Max = 0 }

    # THE BUG: neither angle assert and none of the racing-line cascade it fed.
    @{ Kind = 'LogCount';   Name = 'no FindSignedAngleBetween2DVectors NaN asserts'
       Pattern = '\[ASSERT \d+\] NAN error in AIDriver::FindSignedAngleBetween2DVectors'; Max = 0 }
    @{ Kind = 'LogCount';   Name = 'no racing-line hermite / interp asserts'
       Pattern = '\[ASSERT \d+\] (Bad interp|Bad in interp|NAN rsult in simple hermite|''Error'' is a NAN in iterative hermite|NAN in iterative hermite)'; Max = 0 }
  )
}
