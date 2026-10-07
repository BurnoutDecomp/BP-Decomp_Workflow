# discovery_collect_autosave -- smashing a billboard requests a profile autosave and the save is
# rewritten: action 58 -> GUI 217/218 + GUI 356 -> GuiModule autosave latch -> Profile.sav.
#
# THE CHAIN (all console code):
#   1. StuntManager posts action 58 (E_ACTION_ON_STUNT_ELEMENT_COMPLETE) for the smashed billboard.
#   2. TranslateGameActionsToGuiEvents case 58 posts the stunt-info event (217 or 218) and then a
#      one-byte GuiAutosaveRequestEvent (GUI 356, byte 0)    -> [disco] action 58 -> gui N + gui 356
#   3. GuiModule::Update case 356 raises the autosave latch; the tail saves once the 60 s throttle
#      allows                                                 -> [profile-save] autosave requested
#   4. ProfileManager::Autosave writes Memcard\Profile.sav  -> <RunDir>\Profile.sav.after differs
#      from the fixture.
# Before this lane the GUI 356 post was parked in case 58, so a collect never asked for a save.
#
# ISOLATING THE COLLECT'S REQUEST. The junkyard exit posts its own autosave request (action 55,
# logged `[profile-save] action 55 -> gui 356` under BRN_PROP_DIAG), and the latch fires the first
# save at t = 60 s whoever asked. So the car is held on the handbrake on the deck until that first
# save has happened (first input + 36 s; the first save lands near first input + 31 s), and only
# then drives into the board. The verdict needs: first save A1 -> collect C with NO action-55
# request between them -> a second save A2 after C (60 s throttle after A1). Only the collect's
# GUI 356 can have armed A2 (the periodic autosave is 300 s). Hence MaxSeconds 135, not 90.
#
# THE FIXTURE: tools\tests\fixtures\DISCO_collect_base.sav, a copy of the box's pose save
# (scratch\gameplay_wave\profile_backup\Profile.sav.pose250700).
# THE SPOT: billboard region 463537 on the deck at (2993, 15.7, -1763.7); teleport to the far end
# of the deck facing +X (the gateui r9 billboard run), handbrake to settle, accelerate into the board.
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case discovery_collect_autosave
@{
  Name           = 'discovery_collect_autosave'
  Area           = 'progression'
  Bug            = 'collect path: the GUI 356 autosave request after a billboard/smash collect was parked (include-fork note)'
  Frames         = $false
  ProfileFixture = 'DISCO_collect_base.sav'
  Run            = @{
    Drive          = $true
    MotionProbe    = $true
    MaxSeconds     = 135
    SkipIntro      = $true
    AcceptGap      = 1.0
    Teleport       = '2958,12.5,-1764,90'
    TeleportArm    = 2
    ThrottleScript = '0:accel,1.2:handbrake,36:accel'
  }
  DiagEnv = 'BRN_DISCO_DIAG=1,BRN_PROP_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }

    @{ Kind = 'LogMatch'; Name = 'a collect posted the autosave request (action 58 -> gui 356)'
       Pattern = '\[disco\] action 58 -> gui 21[78] \+ gui 356 autosave request' }

    @{ Kind = 'Script'; Name = 'save A1 -> collect (no action-55 request since A1) -> save A2; Profile.sav rewritten'
       Script = {
         param($ctx)
         $la = $ctx.LogLines
         $liA1 = -1; $liCollect = -1; $liA2 = -1; $li55 = -1
         for ($i = 0; $i -lt $la.Count; $i++) {
           $l = $la[$i]
           if ($liA1 -lt 0) {
             if ($l -match '\[profile-save\] autosave requested') { $liA1 = $i }
             continue
           }
           if ($liCollect -lt 0) {
             if ($l -match '\[profile-save\] action 55 -> gui 356') { $li55 = $i }
             if ($l -match '\[disco\] action 58 -> gui 21[78] \+ gui 356') { $liCollect = $i }
             continue
           }
           if ($l -match '\[profile-save\] action 55 -> gui 356' -and $liA2 -lt 0) { $li55 = $i }
           if ($l -match '\[profile-save\] autosave requested') { $liA2 = $i; break }
         }
         $lsWhere = "A1@$liA1 collect@$liCollect A2@$liA2 last55@$li55"
         if ($liA1 -lt 0) { return @{ Pass = $false; Detail = "no first autosave; $lsWhere" } }
         if ($liCollect -lt 0) { return @{ Pass = $false; Detail = "no collect after the first autosave (scenario miss: held too short/long?); $lsWhere" } }
         if ($li55 -gt $liA1) { return @{ Pass = $false; Detail = "an action-55 request between A1 and A2 makes A2 ambiguous; $lsWhere" } }
         if ($liA2 -lt 0) { return @{ Pass = $false; Detail = "the collect's request never produced a save; $lsWhere" } }
         $lsAfter = Join-Path $ctx.RunDir 'Profile.sav.after'
         $lsFixture = Join-Path $ctx.RunDir '..\..\..\..\..\tools\tests\fixtures\DISCO_collect_base.sav'
         if (-not (Test-Path $lsAfter)) { return @{ Pass = $false; Detail = "no Profile.sav.after; $lsWhere" } }
         $lsA = (Get-FileHash $lsAfter -Algorithm SHA1).Hash
         $lsF = (Get-FileHash $lsFixture -Algorithm SHA1).Hash
         if ($lsA -eq $lsF) { return @{ Pass = $false; Detail = "Profile.sav.after equals the fixture; $lsWhere" } }
         return @{ Pass = $true; Detail = ("{0}; Profile.sav.after sha1 {1} != fixture {2}" -f $lsWhere, $lsA.Substring(0,12), $lsF.Substring(0,12)) }
       } }
  )
}
