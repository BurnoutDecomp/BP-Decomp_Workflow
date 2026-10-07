# discovery_all_of_type -- discovering the LAST Stunt Run junction fires the "every Stunt Run found"
# reward: action 203 -> GUI 313 -> HUD message "EvryStuntJnc".
#
# THE CHAIN (all console code):
#   1. GameStateModule::CheckIfPlayerIsAtJunctionWithAnEvent: the player is in junction 480897's
#      traffic-light region in free roam and its profile event is not yet DISCOVERED -> sets the
#      bit, posts the autosave request (action 55) and calls
#   2. GameStateModule::CheckForAllEventsOfATypeFound(profile, queue, STUNT_ATTACK): every Stunt Run
#      junction of the profile is now discovered (14 of 14)            -> [disco] ... POSTED action 203
#   3. TranslateGameActionsToGuiEvents case 203 -> GuiEventAllJunctionsDiscoveredOfType (GUI 313)
#                                                                       -> [freeroam-gui] action 203 -> gui 313
#   4. HudMessageAnalyzer case 313 -> HandleAllJunctionsOfTypeFound -> "EvryStuntJnc"
#                                                                       -> [hudmsg] director: filter "EvryStuntJnc"
#   5. action 55 -> GUI 356 -> GuiModule's autosave latch -> Profile.sav rewritten with the bit set.
#
# THE FIXTURE (ProfileFixture): tools\tests\fixtures\DISCO_stunt_all_but_480897.sav, made from the
# box's pose save (scratch\gameplay_wave\profile_backup\Profile.sav.pose250700) by
#   py tools\tests\tools\DISCO_profile_patch.py --in <pose save> \
#      --out tools\tests\fixtures\DISCO_stunt_all_but_480897.sav --mode 2 --leave 480897
# i.e. 13 of the 14 Stunt Run junctions discovered, junction 480897 (the one 326 m from the junkyard
# drive start) not. Other modes are left as the pose save had them, so no "all events" reward.
#
# THE SPOT: junction 480897's light-trigger STAND teleport (scratch\stuntrace_scout\eventdata\
# stunt_teleports.txt). The teleport fires during the junkyard-exit drive; the car lands inside the
# traffic-light region, which is all the discovery arm needs.
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case discovery_all_of_type
@{
  Name           = 'discovery_all_of_type'
  Area           = 'progression'
  Bug            = 'discovery rewards: CheckForAllEventsOfATypeFound had no body and its call was parked; action 203 had no translator arm'
  Frames         = $false
  ProfileFixture = 'DISCO_stunt_all_but_480897.sav'
  Run            = @{
    Drive       = $true
    MotionProbe = $true
    MaxSeconds  = 90
    SkipIntro   = $true
    AcceptGap   = 1.0
    Teleport    = '2641.5,1.3,-1723.8,169'   # junction 480897, inside its light trigger
  }
  DiagEnv = 'BRN_DISCO_DIAG=1,BRN_FREEROAM_DIAG=1,BRN_HUDMSG_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }

    @{ Kind = 'LogMatch'; Name = 'the type check ran on the discovery and counted 14 of 14 Stunt Runs'
       Pattern = '\[disco\] all-of-type check \(mode found total\) 2 14 14 ' }
    @{ Kind = 'LogMatch'; Name = 'action 203 posted'
       Pattern = '\[disco\] all-of-type POSTED action 203 \(mode found total payload\) 2 14 14 \d+' }
    @{ Kind = 'LogMatch'; Name = 'all-events reward NOT posted (other modes incomplete)'
       Pattern = '\[disco\] all-events POSTED action 202'; Expect = $false }

    @{ Kind = 'Script'; Name = 'action 203 -> GUI 313 (same payload) -> HUD EvryStuntJnc, in order'
       Script = {
         param($ctx)
         $la = $ctx.LogLines
         $liPost = -1; $liGui = -1; $liHud = -1; $lsPayload = ''; $lsGuiPayload = ''
         for ($i = 0; $i -lt $la.Count; $i++) {
           $l = $la[$i]
           if ($liPost -lt 0 -and $l -match '\[disco\] all-of-type POSTED action 203 \(mode found total payload\) 2 \d+ \d+ (\d+)') { $liPost = $i; $lsPayload = $Matches[1] }
           if ($liPost -ge 0 -and $liGui -lt 0 -and $l -match '\[freeroam-gui\] action 203 -> gui 313 \((\d+)\)') { $liGui = $i; $lsGuiPayload = $Matches[1] }
           if ($liGui -ge 0 -and $liHud -lt 0 -and $l -match '\[hudmsg\] director: filter "EvryStuntJnc"') { $liHud = $i }
         }
         $lsWhere = "post@$liPost gui@$liGui hud@$liHud payload=$lsPayload/$lsGuiPayload"
         if ($liPost -lt 0) { return @{ Pass = $false; Detail = "no action 203 post; $lsWhere" } }
         if ($liGui -lt 0)  { return @{ Pass = $false; Detail = "action 203 never became GUI 313; $lsWhere" } }
         if ($lsPayload -ne $lsGuiPayload) { return @{ Pass = $false; Detail = "payload changed in the bridge; $lsWhere" } }
         if ($liHud -lt 0)  { return @{ Pass = $false; Detail = "GUI 313 never reached the HUD message director; $lsWhere" } }
         return @{ Pass = $true; Detail = $lsWhere }
       } }

    @{ Kind = 'Script'; Name = 'Profile.sav rewritten with junction 480897 discovered'
       Script = {
         param($ctx)
         $lsAfter = Join-Path $ctx.RunDir 'Profile.sav.after'
         if (-not (Test-Path $lsAfter)) { return @{ Pass = $false; Detail = 'no Profile.sav.after in the run dir' } }
         $lsTool = Join-Path $ctx.RunDir '..\..\..\..\..\tools\tests\tools\DISCO_profile_patch.py'
         $env:PYTHONUTF8 = '1'
         $lsOut = & 'C:\Python310\python.exe' $lsTool --in $lsAfter --check 480897 2>&1 | Out-String
         $liExit = $LASTEXITCODE
         $lsFirst = ($lsOut -split "`n")[0].Trim()
         $lsTally = (($lsOut -split "`n") | Where-Object { $_ -match 'STUNT_ATTACK' }) -join ''
         # The fixture holds 13 of 14; anything but 14 of 14 means the save was not rewritten by
         # this run's discovery (e.g. another lane's restore landed on the shared save mid-run).
         $lbAll = ($lsTally -match 'discovered\s+14 /\s+14')
         return @{ Pass = ($liExit -eq 0 -and $lbAll); Detail = "$lsFirst |$($lsTally.Trim())" }
       } }
  )
}
