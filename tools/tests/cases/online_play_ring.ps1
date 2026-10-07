# online_play_ring -- lane SCRON, stub wave S34 (2026-10-07). Issue BurnoutDecomp/b5-decomp#34.
#
# ON_PLAY (BrnGui::OnlinePlay) sits on the OFFLINE crash-nav tab ring between CN_SETTINGS and
# CN_MAP_MAIN. Until this wave it was a link stub with a PC escape hatch; now it is the real
# screen, which only takes TOGGLE_LEFT/RIGHT and GO_BACK once its apt movie and components are up.
# This run tabs onto ON_PLAY and off again, offline, and must end back in the game:
#   Start (action 45)        -> pause menu (driver details)
#   LB twice                 -> CN_MAP_MAIN, then ON_PLAY
#   RB                       -> back off ON_PLAY onto CN_MAP_MAIN
#   LB, then Stop (action 50)-> ON_PLAY again, then GO_BACK out of the pause menu from ON_PLAY
#
# Screen transitions are read from the BRN_SCREEN_DIAG witness in CgsScriptedFsm.cpp:
#   [screen] ENTER '<state>' (from '<state>') seq ...   (ids are blank-padded to 12)
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case online_play_ring
@{
  Name    = 'online_play_ring'
  Area    = 'gui'
  Bug     = 'BurnoutDecomp/b5-decomp#34 -- the real OnlinePlay must keep the offline tab ring usable'
  ProfileFixture = 'scratch\gameplay_wave\profile_backup\Profile.sav.pose250700'
  Run     = @{
    Drive          = $true
    MaxSeconds     = 80
    SkipIntro      = $true
    AcceptGap      = 1.0
    Teleport       = '3040.7,-5.8,-1937.9,180'
    ThrottleScript = '0:accel,3:none'
    MenuTapAt      = '10:Start,50:Stop'
    ShoulderAt     = '15:L:1.0,22:L:1.0,32:R:1.0,40:L:1.0'
  }
  DiagEnv = 'BRN_SCREEN_DIAG=1'
  Checks  = @(
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'LogMatch';   Name = 'tabbed onto ON_PLAY'; Pattern = "\[screen\] ENTER 'ON_PLAY\s*'" }
    @{ Kind = 'LogMatch';   Name = 'the stub is gone (no un-reconstructed OnlinePlay log)';
       Pattern = 'OnlinePlay::OnEnter\[escape hatch'; Expect = $false }
    @{ Kind = 'LogMatch';   Name = 'tabbed off ON_PLAY with RB'; Pattern = "\[screen\] ENTER '[A-Z_]+\s*' \(from 'ON_PLAY\s*'\)" }
    @{ Kind = 'Script'; Name = 'entered ON_PLAY twice and left it twice, ending outside it'; Script = {
        param($ctx)
        $liIn = 0; $liOut = 0; $lsLast = ''
        foreach ($l in $ctx.LogLines) {
          if ($l -match "\[screen\] ENTER '(?<to>[A-Z_0-9]+)\s*' \(from '(?<from>[^']*?)\s*'\)") {
            if ($Matches.to -eq 'ON_PLAY') { $liIn++ }
            if ($Matches.from -eq 'ON_PLAY') { $liOut++ }
            $lsLast = $Matches.to
          }
        }
        return @{ Pass = ($liIn -ge 2 -and $liOut -ge 2 -and $lsLast -ne 'ON_PLAY');
                  Detail = "entered=$liIn left=$liOut last screen state='$lsLast'" } } }
  )
}
