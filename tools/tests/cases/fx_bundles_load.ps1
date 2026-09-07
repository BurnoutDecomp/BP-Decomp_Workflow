# fx_bundles_load -- a live boot halts twice on "LoadBundle failed for a request that did not
# allow failure": once for PostFx/postfxvault.bin (the effects module's AttribSys vault) and
# once for particles.bundle (the one FX bundle), each reported as "pool N: -1 resources".
#
# THE BUG, stated as a line in the log. Both files in the staged data were the untouched X360
# copies: big-endian bnd2 with platform dword 2, which the reconstructed loader treats as inert
# ("-1 resources") and the effects module requests without allowing failure. Both have had
# porters in tools\assets for a while (rules postfx-vault and particles in
# game_data_manifest.toml); they had never been re-run on this box's staged drop. This case
# does not test the porters. It tests that the data the game boots on is the ported data, so
# a regressed stage (a --borrow-dir of a stale drop, a copy rule creeping back) shows up as a
# boot halt on the very next baseline, not as "the sparks have no lifetime" weeks later.
#
# THE WITNESSES.
#   RED  = "[stream] LoadBundle '<file>' -> pool N: -1 resources" for either file, then the
#          "LoadBundle failed" assert.
#   GREEN = both LoadBundle lines report a positive resource count and the assert never fires.
#
# Scenario: boot only, console -skipvideos latch on.
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case fx_bundles_load -ExpectFail -Label pre-fix
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case fx_bundles_load -Label post-fix
@{
  Name    = 'fx_bundles_load'
  Area    = 'effects'
  Bug     = 'live boot halts on "LoadBundle failed" for PostFx/postfxvault.bin and particles.bundle (unported platform-2 copies in the staged data)'
  Frames  = $false
  FreshProfile = $false
  Run     = @{
    MaxSeconds = 45              # boot only: both requests are issued inside the scripted load
    SkipIntro  = $true           # the console -skipvideos latch
    AcceptGap  = 1.0
  }
  DiagEnv = ''
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }

    # The scenario really issued both requests.
    @{ Kind = 'LogMatch'; Name = 'the effects vault was requested'
       Pattern = "\[stream\] LoadBundle 'PostFx/postfxvault\.bin' -> pool \d+:" }
    @{ Kind = 'LogMatch'; Name = 'the FX bundle was requested'
       Pattern = "\[stream\] LoadBundle 'particles\.bundle' -> pool \d+:" }

    # THE BUG. An inert (platform-2) container reports -1 resources.
    @{ Kind = 'LogMatch'; Name = 'the effects vault loaded with resources'
       Pattern = "\[stream\] LoadBundle 'PostFx/postfxvault\.bin' -> pool \d+: [1-9]\d* resources" }
    @{ Kind = 'LogMatch'; Name = 'the FX bundle loaded with resources'
       Pattern = "\[stream\] LoadBundle 'particles\.bundle' -> pool \d+: [1-9]\d* resources" }
    @{ Kind = 'LogCount'; Name = 'no "LoadBundle failed" assert'
       Pattern = '\[ASSERT \d+\] LoadBundle failed for a request that did not allow failure'; Max = 0 }
  )
}
