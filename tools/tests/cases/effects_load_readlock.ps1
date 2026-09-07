# effects_load_readlock -- a live boot stops at "[ASSERT 1] Not locked for writing" inside
# LoadingScriptedState::LoadEffectsModule (scripted-load stage 2), and the assert screen is the
# whole game from then on.
#
# THE BUG, stated as a line in the log. While the effects module is still preparing, the stage
# forwards the effects output buffer's staged requests into the GameData input buffer under a
# READ lock: LockForRead, read the vault-request interface and the resource-request interface,
# UnlockForRead. The console reads both through the CONST accessors (the ones that test the
# read-lock bit). The PC body read them through a non-const pointer, so C++ overload
# resolution picked the WRITE-lock accessors, whose guard is "Not locked for writing" -- true,
# and the assert fires on the first prepare frame of every boot. LoadWorldModule, two functions
# down in the same file, reads through a const alias for exactly this reason.
#
# THE WITNESSES.
#   RED  = "[ASSERT n] Not locked for writing" with BrnEffectsModuleIO_OutputBuffer.cpp in the
#          site, and (on a harness run, which releases asserts) stage 3 only after them.
#   GREEN = stage 2 ran ("LoadEffectsModule -- real"), the effects ladder printed at least once
#          (Prepare was driven and the forward path executed), zero "Not locked for writing"
#          asserts, and the scripted load advanced to stage 3.
#
# Scenario: boot only, console -skipvideos latch on.
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case effects_load_readlock -ExpectFail -Label pre-fix
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case effects_load_readlock -Label post-fix
@{
  Name    = 'effects_load_readlock'
  Area    = 'effects'
  Bug     = 'live boot halts on "Not locked for writing" in LoadEffectsModule (read-lock forward used the write-lock accessors)'
  Frames  = $false
  FreshProfile = $false
  Run     = @{
    MaxSeconds = 45              # boot only: the scripted load is done well inside 20 s
    SkipIntro  = $true           # the console -skipvideos latch
    AcceptGap  = 1.0
  }
  DiagEnv = ''
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }

    # The scenario really drove the effects stage.
    @{ Kind = 'LogMatch'; Name = 'scripted-load stage 2 (LoadEffectsModule) ran'
       Pattern = 'ScriptedLoad: stage 2 \(LoadEffectsModule -- real\)' }
    @{ Kind = 'LogMatch'; Name = 'EffectsModule::Prepare was driven (the effects-load ladder printed)'
       Pattern = '\[effects-load\] EffectsModule::Prepare stage=' }

    # THE BUG. The read-lock forward must not trip the write-lock guard.
    @{ Kind = 'LogCount'; Name = 'no "Not locked for writing" assert'
       Pattern = '\[ASSERT \d+\] Not locked for writing'; Max = 0 }

    # The load advanced past the effects stage.
    @{ Kind = 'LogMatch'; Name = 'scripted-load stage 3 reached'
       Pattern = 'ScriptedLoad: stage 3' }
  )
}
