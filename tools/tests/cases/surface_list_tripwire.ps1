# surface_list_tripwire -- a live boot halts once on "Surface list appears to be corrupt"
# (RaceCarEntityModule::CheckForResetOnTrackConditions, the reset-on-track watchdog's dev
# tripwire), although the world entity module's own bind of the same surface list resolves
# 20 surfaces in the same log.
#
# THE BUG, stated as a line in the log. The tripwire re-resolves the surfacelist class onto a
# collection key the console keeps in a global. That global reads 0 straight out of the image
# because a CRT static initialiser writes it at startup (StringToKey("340654"), the same key the
# world module's bind loads), and the PC body carried the 0. Key 0 selects the class's default
# collection, which has no "Surfaces" attribute, so the lookup fell through to the zeroed
# DefaultDataArea RefSpec and the leading quad of the surface built over it was all zero.
#
# THE WITNESSES.
#   RED  = "[ASSERT n] Surface list appears to be corrupt", and no resolved witness line.
#   GREEN = the tripwire prints "entry=resolved ... sane=1" once and the assert never fires,
#           while the world module's bind still reports its 20 surfaces (the data did not move).
#
# Scenario: boot only, console -skipvideos latch on (the watchdog runs from the first DRIVING
# frame, which the boot reaches inside the window).
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case surface_list_tripwire -ExpectFail -Label pre-fix
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case surface_list_tripwire -Label post-fix
@{
  Name    = 'surface_list_tripwire'
  Area    = 'world'
  Bug     = 'live boot halts on "Surface list appears to be corrupt" (the watchdog resolved the surface list on collection key 0)'
  Frames  = $false
  FreshProfile = $false
  Run     = @{
    MaxSeconds = 45              # boot only: the watchdog runs as soon as DRIVING starts
    SkipIntro  = $true           # the console -skipvideos latch
    AcceptGap  = 1.0
  }
  DiagEnv = ''
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }

    # The data is there: the world module's bind of the same list resolves.
    @{ Kind = 'LogMatch'; Name = 'the world module bound the surface list with surfaces'
       Pattern = '\[skid-bind\] WorldEntityModule::PrepareSurfaceList: key=[0-9A-F]+ boundCollectionKey=[0-9A-F]+ Num_Surfaces=[1-9]' }

    # The watchdog ran and its lookup resolved (the once-per-process verdict line).
    @{ Kind = 'LogMatch'; Name = 'the watchdog tripwire resolved its entry and judged the list sane'
       Pattern = '\[reset-watchdog\] surface-list tripwire: entry=resolved .* sane=1' }

    # THE BUG.
    @{ Kind = 'LogCount'; Name = 'no "Surface list appears to be corrupt" assert'
       Pattern = '\[ASSERT \d+\] Surface list appears to be corrupt'; Max = 0 }
  )
}
