# audio_aems_tick -- AemsFactory::UpdateAEMSPatches @0x826A2C30 runs the live AEMS instances from
# DoUpdate, with the frame's step in milliseconds, and every instance has its patch monitor. Also
# keeps the reverb IR slot and the presentation-effect action table under watch.
#
# Run it:  powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case audio_aems_tick -Slot 15
#
# Witness: [FLAG PC witness] [aems] behind BRN_AEMS_DIAG (capped, off by default). The run's sound
# is real (`Audio`), only the proof by ear is the user's.
@{
  Name    = 'audio_aems_tick'
  Area    = 'sound'
  Bug     = 'UpdateAEMSPatches had no body; the module tick was an Xbox One style audio-thread timer'
  Frames  = $false
  Run     = @{
    Drive          = $true
    TitleStart     = $true
    MotionProbe    = $true
    SkipIntro      = $true
    AcceptGap      = 1.0
    MaxSeconds     = 70
    Teleport       = '3323.9,-2.4,-1793.2,0'
    ThrottleScript = '0:accel'
  }
  DiagEnv = 'BRN_AEMS_DIAG=1,BRN_TRAFFICSND_DIAG=1,BRN_SNDENV_DIAG=1,BRN_ENGINE_MIX_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'LogCount';   Name = 'patch monitors registered'
       Pattern = '\[aems\] monitor \d+ name='; Min = 1 }
    @{ Kind = 'LogCount';   Name = 'the tick runs live instances'
       Pattern = '\[aems\] tick=\d+ stepMs=[\d.]+ instances=[1-9]'; Min = 1 }
    @{ Kind = 'LogValue';   Name = 'step is a frame, in ms'
       Pattern = '\[aems\] tick=\d+ stepMs=(?<v>[\d.]+) instances=[1-9]'; Group = 'v'; Agg = 'max'; Max = 250 }
    @{ Kind = 'LogCount';   Name = 'no patch monitor assert'
       Pattern = '\[ASSERT \d+\].*(lpPatchMonitor|muPatchMonitorCount|lpClassData|lpModule)'; Max = 0 }
    @{ Kind = 'LogCount';   Name = 'presentation table filled'
       Pattern = '\[presentation\] rows=[1-9]'; Min = 1 }
    @{ Kind = 'LogCount';   Name = 'presentation lookups hit the table'
       Pattern = '\[presentation\] resolve action=\d+ found=1'; Min = 1 }
    @{ Kind = 'LogCount';   Name = 'no presentation table assert'
       Pattern = '\[ASSERT \d+\].*(lu16NumActions|leAction|NumOfActions)'; Max = 0 }
    @{ Kind = 'LogCount';   Name = 'no missing slot factory'
       Pattern = '\[ASSERT \d+\].*Could not find Slot Factory'; Max = 0 }
    @{ Kind = 'LogCount';   Name = 'traffic engine voices started (AEMS)'
       Pattern = '\[trafficsnd\] voice started type=engine'; Min = 1 }
  )
}
