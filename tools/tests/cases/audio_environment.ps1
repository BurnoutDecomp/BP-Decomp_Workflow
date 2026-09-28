# audio_environment -- lane SNDENV (gameplay wave GW2). The player car's environment sound
# effects had constructors and nothing else: the crash / show-time stream, the speed stream,
# the ambience beds and the reverb never prepared, updated or streamed anything. This wave
# bodies CrashStreamEffect (Prepare / UpdateParams / Detach), SpeedStreamEffect (UpdateParams /
# Detach), AmbienceEffect + AmbienceControl (the region map, the tunnel / traffic beds, the
# stream requests and the two-second fade), ReverbEffect::Attach and the in-car stereo.
#
# Run it:  powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case audio_environment
#
# THE SCENARIO is the baseline drive (junkyard exit road, hold the throttle) plus ONE forced
# player crash through the harness's BRN_CRASH_PLAYER lever (the console's own debug-menu
# crash flag; see BrnVehicleManager_UpdateVehiclePhysics.cpp [crash-probe]).
#
# WITNESSES (BRN_SNDENV_DIAG, first 24 per site, all tagged [FLAG PC witness]):
#   [sndenv] crash-stream submix ready    CrashStreamEffect::Prepare built its submix voice
#   [sndenv] crash-stream update          CrashStreamEffect::UpdateParams ran
#   [sndenv] crash-stream edge / play     a show-time or fatal-crash edge (info only: the forced
#                                         crash is not guaranteed to be a FATAL crash)
#   [sndenv] ambience-control select      AmbienceControl chose a region (every 5 s)
#   [sndenv] ambience play region=N       AmbienceEffect requested the bed for region N
#   [sndenv] reverb attach                ReverbEffect::Attach ran
#   [sndenv] speed-stream play / stop     the >75 mph wind stream (info only: speed-dependent)
# ReverbEffect::UpdateParams / ProcessUpdate are NOT bodied yet (they need a reverbparams
# accessor and SoundLogicModule::GetGlobalReverbVoice), so this case cannot see a reverb change.
@{
  Name    = 'audio_environment'
  Area    = 'sound'
  Bug     = 'no crash stream, ambience, speed stream or reverb: the environment effects were constructor-only'
  Frames  = $false
  Run     = @{
    Drive       = $true
    MotionProbe = $true
    SkipIntro   = $true
    AcceptGap   = 1.0
    Teleport    = '3040.7,-5.8,-1937.9,180'   # the road outside the junkyard exit
    CrashPlayer = 1500                         # one forced player crash, ~25 s of physics in
    MaxSeconds  = 75
  }
  DiagEnv = 'BRN_SNDENV_DIAG=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }
    @{ Kind = 'LogCount';   Name = 'no assert from the environment sound files'
       Pattern = '\[ASSERT \d+\].*Sound.Vehicles.Environment'; Max = 0 }

    # PRECONDITION: the forced crash fired (else the crash leg says nothing).
    @{ Kind = 'LogCount';   Name = 'the forced player crash fired'
       Pattern = '\[crash-probe\] frame'; Min = 1 }

    # THE LANE'S PROOF.
    @{ Kind = 'LogCount';   Name = 'crash stream: submix voice ready (Prepare)'
       Pattern = '\[sndenv\] crash-stream submix ready'; Min = 1 }
    @{ Kind = 'LogCount';   Name = 'crash stream: UpdateParams runs'
       Pattern = '\[sndenv\] crash-stream update'; Min = 1 }
    @{ Kind = 'LogCount';   Name = 'ambience control: a region was selected'
       Pattern = '\[sndenv\] ambience-control select'; Min = 1 }
    @{ Kind = 'LogCount';   Name = 'ambience effect: a bed was requested'
       Pattern = '\[sndenv\] ambience play region=\d+'; Min = 1 }
    @{ Kind = 'LogCount';   Name = 'reverb: Attach ran'
       Pattern = '\[sndenv\] reverb attach'; Min = 1 }

    # INFO ONLY (never fail): speed- and crash-kind-dependent legs.
    @{ Kind = 'LogCount';   Name = 'info: crash-stream edges'
       Pattern = '\[sndenv\] crash-stream edge'; Min = 0 }
    @{ Kind = 'LogCount';   Name = 'info: crash-stream takes requested'
       Pattern = '\[sndenv\] crash-stream play'; Min = 0 }
    @{ Kind = 'LogCount';   Name = 'info: speed-stream plays'
       Pattern = '\[sndenv\] speed-stream play'; Min = 0 }
  )
}
