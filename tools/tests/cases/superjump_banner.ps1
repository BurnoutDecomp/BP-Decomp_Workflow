# superjump_banner -- a super jump posts its HUD banner: game action 57 -> GUI 216.
#
# THE CHAIN. On take-off StuntManager::UpdateJumps posts action 56 (OnJumpStart, the camera
# request) and arms mbShowJumpNameNextFrame; the next frame it posts action 57 (ShowJumpName,
# the jump's 8-byte stunt-element key). TranslateGameActionsToGuiEvents turns 57 into
# GuiEventJumpStarted (GUI 216), and HudMessageAnalyzer case 216 triggers the "SuperJump" HUD
# message. Before the free-roam translator the 57 arm did not exist on this build, so the banner
# never showed. If the car crashes while attempting a jump for the first time, the same manager
# later posts action 265 -> GUI 549 ("JumpFailed"); that half is not forced here.
#
# THE SCENARIO. The super jump camera_shake_smash has taken on every fresh-profile run
# (`[jump-ladder] action=56 OnJumpStart posted cut=305 type=1 firstTime=1`): a straight road at
# x ~ 3013..3028 running +Z into a ramp near z = -262. Its run-up was read from the [motion]
# samples of scratch\bugtest\runs\camera_shake_smash\20260906_153338 (car at
# (3013.2, -9.28, -839.3) heading ~1.7 deg, 580 m before take-off). The car is placed there and
# holds the throttle to the end; the take-off gate is 40 mph.
#
# RUN LENGTH IS LOAD-BEARING: the fresh-profile boot reaches DRIVING at ~64 s and the car needs
# ~35 s more (6 s drive delay + ~29 s run-up) to reach the ramp. At MaxSeconds 100 the run ended
# at z = -345, 83 m short of take-off, and only generic trigger type 19 had been crossed; at 140
# the jump takes off at z ~ -256 (117 mph) with ~40 s to spare.
#
# FRESH PROFILE IS LOAD-BEARING: StuntManager declines a jump the profile has already done
# (`take-off DECLINED ... doneBefore=1`), and the shipped Memcard\Profile.sav may carry it.
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case superjump_banner
#
@{
  Name    = 'superjump_banner'
  Area    = 'ui'
  Bug     = 'free-roam HUD messages: the super-jump banner (action 57 -> GUI 216) was never translated'
  Frames  = $false
  FreshProfile = $true
  Run     = @{
    Drive       = $true
    MotionProbe = $true
    MaxSeconds  = 140
    SkipIntro   = $true
    AcceptGap   = 1.0
    Teleport    = '3013.2,-9.0,-839.3,1.7'   # 580 m of straight road before the ramp
  }
  # BRN_FREEROAM_DIAG arms the `[freeroam-gui] action A -> gui G (detail)` line. The
  # `[jump-ladder]` take-off rung is unconditional.
  DiagEnv = 'BRN_FREEROAM_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions';   Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }

    # The precondition: the jump was taken (without it the rest says nothing).
    @{ Kind = 'LogMatch';   Name = 'the super jump took off'
       Pattern = '\[jump-ladder\] action=56 OnJumpStart posted .*firstTime=1' }

    # THE ARM: the jump name reached the GUI, after the take-off.
    @{ Kind = 'Script'; Name = 'action 57 -> GUI 216 follows the take-off'; Script = {
        param($ctx)
        $lines = $ctx.LogLines
        $takeoff = -1; $banner = -1
        for ($i = 0; $i -lt $lines.Count; $i++) {
          if ($takeoff -lt 0 -and $lines[$i] -match '\[jump-ladder\] action=56 OnJumpStart posted') { $takeoff = $i }
          if ($takeoff -ge 0 -and $lines[$i] -match '\[freeroam-gui\] action 57 -> gui 216 ') { $banner = $i; break }
        }
        if ($takeoff -lt 0) { return @{ Pass = $false; Detail = 'no take-off line' } }
        if ($banner -lt 0) { return @{ Pass = $false; Detail = "take-off at log line $takeoff, no [freeroam-gui] action 57 -> gui 216 after it" } }
        return @{ Pass = $true; Detail = ("take-off at log line {0}, action 57 -> gui 216 at log line {1}" -f $takeoff, $banner) }
    } }

    # Every boot enters the junkyard, so the junkyard arm runs too.
    @{ Kind = 'LogMatch';   Name = 'junkyard action 99 translated to GUI 79'
       Pattern = '\[freeroam-gui\] action 99 -> gui 79 ' }
  )
}
