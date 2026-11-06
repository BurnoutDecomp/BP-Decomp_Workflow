# audio_presentation -- PresentationEffect::Play @0x826F78D8 and UpdateParams @0x826D2938 drive the
# interface sounds. A menu action resolves to an entry, Play starts a voice, and the voice goes live
# and comes back to rest with no assert.
#
# Run it:  powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case audio_presentation -Slot 25
#
# Witness: [FLAG PC witness] [presentation] behind BRN_AEMS_DIAG (capped, off by default). The run is
# muted; this proves the logic ran, not what it sounds like. PlayStream's online-entrance leg is not
# reached by a TitleStart run: it needs the online free-burn lobby.
@{
  Name    = 'audio_presentation'
  Area    = 'sound'
  Bug     = 'Play and UpdateParams diverged from the console: no PlayStream, no game-mode watch, a doubled voice age'
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
  DiagEnv = 'BRN_AEMS_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'LogCount';   Name = 'a menu action resolved to an entry'
       Pattern = '\[presentation\] resolve action=\d+ found=1'; Min = 1 }
    @{ Kind = 'LogCount';   Name = 'Play ran on a resident arm'
       Pattern = '\[presentation\] play content=[01] splice=\d+ mixer=\d+'; Min = 1 }
    @{ Kind = 'LogCount';   Name = 'a voice went live'
       Pattern = '\[presentation\] voice=\d state=[1-6] age=\d+'; Min = 1 }
    @{ Kind = 'LogCount';   Name = 'a voice came back to rest'
       Pattern = '\[presentation\] voice=\d state=(0|7) age=\d+'; Min = 1 }
    @{ Kind = 'LogCount';   Name = 'no Play or UpdateParams assert'
       Pattern = '\[ASSERT \d+\].*(IsValid|IsAlive|lpLogicModule|mpBrnLogicInputBuffer|lpGameModeInterface|lpStreamingStateMan|Not locked for reading)'; Max = 0 }
    @{ Kind = 'LogCount';   Name = 'no missing slot factory'
       Pattern = '\[ASSERT \d+\].*Could not find Slot Factory'; Max = 0 }
  )
}
