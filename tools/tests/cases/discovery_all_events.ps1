# discovery_all_events -- discovering the LAST undiscovered junction of the whole game fires BOTH
# discovery rewards: "every Stunt Run found" (action 203 -> GUI 313 -> "EvryStuntJnc") and "every
# event found" (action 202 -> GUI 312 -> "EvryEventJnc").
#
# Same chain and spot as discovery_all_of_type; the difference is the fixture:
#   py tools\tests\tools\DISCO_profile_patch.py --in <pose save> \
#      --out tools\tests\fixtures\DISCO_all_but_480897.sav --scope all --leave 480897
# i.e. all 120 junctions discovered except 480897. After its discovery
# GameStateModule::CheckForAllEventsBeingFound (called right after the type check) walks the whole
# profile, finds no undiscovered record, and posts action 202 (once per call; the drive-thru
# handler calls it too, so later posts are expected).
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case discovery_all_events
@{
  Name           = 'discovery_all_events'
  Area           = 'progression'
  Bug            = 'discovery rewards: the all-events check was never called from the junction discovery and action 202 had no translator arm'
  Frames         = $false
  ProfileFixture = 'DISCO_all_but_480897.sav'
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

    @{ Kind = 'LogMatch'; Name = 'action 203 posted (14 of 14 Stunt Runs)'
       Pattern = '\[disco\] all-of-type POSTED action 203 \(mode found total payload\) 2 14 14 \d+' }

    @{ Kind = 'Script'; Name = 'type reward then all-events reward: 203 -> 313 -> EvryStuntJnc and 202 -> 312 -> EvryEventJnc'
       Script = {
         param($ctx)
         $la = $ctx.LogLines
         $l203 = -1; $l202 = -1; $lGui313 = -1; $lGui312 = -1; $lHud313 = -1; $lHud312 = -1
         for ($i = 0; $i -lt $la.Count; $i++) {
           $l = $la[$i]
           if ($l203 -lt 0 -and $l -match '\[disco\] all-of-type POSTED action 203') { $l203 = $i }
           if ($l203 -ge 0 -and $l202 -lt 0 -and $l -match '\[disco\] all-events POSTED action 202') { $l202 = $i }
           if ($l203 -ge 0 -and $lGui313 -lt 0 -and $l -match '\[freeroam-gui\] action 203 -> gui 313 ') { $lGui313 = $i }
           if ($l202 -ge 0 -and $lGui312 -lt 0 -and $l -match '\[freeroam-gui\] action 202 -> gui 312 ') { $lGui312 = $i }
           if ($lGui313 -ge 0 -and $lHud313 -lt 0 -and $l -match '\[hudmsg\] director: filter "EvryStuntJnc"') { $lHud313 = $i }
           if ($lGui312 -ge 0 -and $lHud312 -lt 0 -and $l -match '\[hudmsg\] director: filter "EvryEventJnc"') { $lHud312 = $i }
         }
         $lsWhere = "203@$l203 202@$l202 gui313@$lGui313 gui312@$lGui312 hud313@$lHud313 hud312@$lHud312"
         if ($l203 -lt 0 -or $l202 -lt 0) { return @{ Pass = $false; Detail = "missing a reward post; $lsWhere" } }
         if ($l202 -lt $l203) { return @{ Pass = $false; Detail = "202 before 203 (console order is type check first); $lsWhere" } }
         if ($lGui313 -lt 0 -or $lGui312 -lt 0) { return @{ Pass = $false; Detail = "a reward never became a GUI event; $lsWhere" } }
         if ($lHud313 -lt 0 -or $lHud312 -lt 0) { return @{ Pass = $false; Detail = "a reward never reached the HUD message director; $lsWhere" } }
         return @{ Pass = $true; Detail = $lsWhere }
       } }

    @{ Kind = 'Script'; Name = 'Profile.sav rewritten with every junction discovered'
       Script = {
         param($ctx)
         $lsAfter = Join-Path $ctx.RunDir 'Profile.sav.after'
         if (-not (Test-Path $lsAfter)) { return @{ Pass = $false; Detail = 'no Profile.sav.after in the run dir' } }
         $lsTool = Join-Path $ctx.RunDir '..\..\..\..\..\tools\tests\tools\DISCO_profile_patch.py'
         $env:PYTHONUTF8 = '1'
         $lsOut = & 'C:\Python310\python.exe' $lsTool --in $lsAfter --check 480897 2>&1 | Out-String
         $liExit = $LASTEXITCODE
         $laTally = ($lsOut -split "`n") | Where-Object { $_ -match 'discovered\s+(\d+) /\s+(\d+)' }
         $lbAll = $true
         foreach ($t in $laTally) { if ($t -match 'discovered\s+(\d+) /\s+(\d+)' -and $Matches[1] -ne $Matches[2]) { $lbAll = $false } }
         return @{ Pass = ($liExit -eq 0 -and $lbAll -and $laTally.Count -gt 0); Detail = (($lsOut -split "`n")[0].Trim() + " allModesComplete=$lbAll") }
       } }
  )
}
