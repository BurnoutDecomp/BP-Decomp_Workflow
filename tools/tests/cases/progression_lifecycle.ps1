# progression_lifecycle -- the progression manager's MISSING OUTER LIFECYCLE PAIR.
#
# Run it:   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case progression_lifecycle
#
# THE HOLE (console truth). GameStateModule::Construct @0x82380388 calls
#   BrnProgression::ProgressionManager::Construct @0x8237A5F8 (call #14 of its 50, right after
#   ModeManager::Construct) with (&mCarSelectManager, &mStreetManager, theTrainingManager,
#   &mStuntManager); GameStateModule::Prepare @0x8239E578 stage 20 calls
#   ProgressionManager::Prepare @0x8239DC38 (= LoadAIData + Profile::Construct), and stage 8
#   calls ProgressionManager::ApplyVehicleList @0x82359A20. NONE of those three existed on PC,
#   so every back-pointer Construct installs (mpStreetManager / mpStuntManager /
#   mpTrainingManager / mpCarSelectManager) read NULL for the whole run, mpAISectionData was
#   never bound, the landmark -> AI-section table had no producer
#   (ComputeLandmarkAISectionIndices @0x82370008), and the preset-race list was empty
#   (ProcessLoadedPresetRaces @0x8236FDF8).
#
# WITNESSES (opt-in, BRN_PROGRESSION_LIFECYCLE=1, one line each per boot):
#   [lifecycle] construct: street=<0|1> stunt=<0|1> training=<0|1> carselect=<0|1> ...
#   [lifecycle] prepare:   aiSections=<0|1> stage=<n>
#   [lifecycle] prepare2:  presetRaces=<n> roamingSections=<n> landmarkAI=<n> vehicles=<0|1>
#                          ach=<0|1> street=<0|1> stunt=<0|1> training=<0|1>
#
# RED (before the fix): none of the three lines exists at all -- there is no Construct and no
# Prepare to print them, which is exactly the bug. Every witness check therefore fails.
# GREEN: all three fire with the pointers installed and the three counts non-zero.
#
# Scenario = the baseline's (plain boot + drive). Everything this case measures happens during
# GameStateModule::Construct/Prepare/Prepare2, i.e. before DRIVING; the drive leg is only there
# so the run is a real one and `baseline_boot_drive`'s own bar (the car moved) still applies.
@{
  Name    = 'progression_lifecycle'
  Area    = 'progression'
  Bug     = 'ProgressionManager::Construct @0x8237A5F8 / ::Prepare @0x8239DC38 / ::ApplyVehicleList @0x82359A20 have no PC body -- every Construct back-pointer is NULL, mpAISectionData unbound, landmark AI-section table and preset races empty'
  Frames  = $false
  Run     = @{
    Drive       = $true
    MotionProbe = $true
    MaxSeconds  = 50
    SkipIntro   = $true
    AcceptGap   = 1.0
    Teleport    = '3040.7,-5.8,-1937.9,180'   # the road outside the junkyard exit (baseline's)
  }
  DiagEnv = 'BRN_PROGRESSION_LIFECYCLE=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }

    # --- Construct: the four back-pointers the console installs there ---
    @{ Kind = 'LogMatch'; Name = 'Construct installed street/stunt/training/carselect'
       Pattern = '\[lifecycle\] construct: street=1 stunt=1 training=1 carselect=1' }

    # --- Prepare: LoadAIData ran to completion and bound mpAISectionData ---
    @{ Kind = 'LogMatch'; Name = 'Prepare bound the AI sections resource'
       Pattern = '\[lifecycle\] prepare: aiSections=1' }

    # --- Prepare2's callees: the three tables that had no producer ---
    # HACK_SetupRaces @0x82366968 builds exactly 5 preset races ("Hack 01".."Hack 05").
    @{ Kind = 'LogValue'; Name = 'preset races processed (console builds 5)'
       Pattern = '\[lifecycle\] prepare2: presetRaces=(?<n>\d+)'; Group = 'n'; Agg = 'last'; Min = 5 }
    # 18 districts x <= 8 roaming locations; the shipped TriggerData has 139 roaming locations.
    @{ Kind = 'LogValue'; Name = 'roaming sections mapped'
       Pattern = 'roamingSections=(?<n>\d+)'; Group = 'n'; Agg = 'last'; Min = 1 }
    # The landmark -> AI-section cache FindLandmarkAISectionIndex reads: one entry per authored
    # landmark (the shipped TriggerData reports 105).
    @{ Kind = 'LogValue'; Name = 'landmark AI-section table filled'
       Pattern = 'landmarkAI=(?<n>\d+)'; Group = 'n'; Agg = 'last'; Min = 100 }

    # --- the whole install set, read back after Prepare2 ---
    @{ Kind = 'LogMatch'; Name = 'every back-pointer installed by the end of Prepare2'
       Pattern = '\[lifecycle\] prepare2: .*vehicles=1 ach=1 street=1 stunt=1 training=1' }

    # The baseline's own bar: the boot really is a boot.
    @{ Kind = 'Script'; Name = 'the car moved'; Script = {
        param($ctx)
        $l = ($ctx.MarksText -split "`n") | Where-Object { $_ -match '^DRIVE\s+' } | Select-Object -First 1
        if (-not $l) { return @{ Pass = $false; Detail = 'no DRIVE line in marks.txt' } }
        $ok = ($l -match 'path=(?<p>[\d.,]+)m') -and ([double](($Matches.p) -replace ',', '.') -gt 20)
        return @{ Pass = $ok; Detail = $l.Trim() }
      } }
  )
}
