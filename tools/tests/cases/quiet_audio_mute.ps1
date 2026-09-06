# quiet_audio_mute -- a harness run must make NO SOUND, and must still SIMULATE the audio.
#
# Bug (lane quiet): "mutes the audio by default for test cases". Every case on this box boots a
# real game that opens the machine's default render endpoint at full volume, so a sixteen-case
# sweep is half an hour of Burnout playing out loud over whatever the box's owner is doing.
#
# WHAT IS MEASURED, and why it is a number and not "I could not hear it".
#   The PC output leaf owns exactly one XAudio2 mastering voice (CgsAudioOutputPC.cpp), and the
#   mastering voice's volume is the LAST gain the OS mixer sees -- everything the game produces
#   goes through it. So the honest measurement of "this run was silent" is that voice's own
#   GetVolume() read back from the engine after it is created, which the leaf now prints on the
#   same line it already printed for every Open:
#       [Audio] XAudio2 opened: 48000 Hz, 2 ch (16-bit PCM); master volume=0.000 (BRN_AUDIO_MUTE=1)
#   Check 4 requires EVERY such line in the run to read 0.000 -- Agg='all', because the device is
#   opened and re-opened many times in a boot (movie streams churn the primary fill) and one
#   un-muted re-open is an audible run.
#
#   THE SECOND HALF OF THE CASE IS THE ONE THAT MATTERS FOR EVERY OTHER LANE. Muting must not be
#   "skip audio init": the sound lanes' witnesses, the AEMS bytecode and the engine-note state
#   machines all have to keep running exactly as before, or a mute would silently change what
#   every other case measures. So checks 5 and 6 require the audio SIMULATION to still be doing
#   its work with the master at zero -- the movie-audio decoder still decodes XMA and still loads
#   the stream, and the device is still really opened (a failed Open also produces no sound, and
#   would pass a naive "is it quiet" test).
#
# RED before the fix: the leaf had no volume witness at all and no way to be muted, so check 4
# reads "the witness never fired". GREEN after: 0.000 on every Open, with the decoder lines intact.
@{
  Name    = 'quiet_audio_mute'
  Area    = 'harness'
  Bug     = 'lane quiet -- harness runs play sound out loud on the box'
  Frames  = $false
  Run     = @{
    MaxSeconds = 70
    # ⛔ NO SkipIntro, DELIBERATELY, and it is not laziness about run time. The EA-Franchise and
    #   Criterion VP6 logos are the loudest thing a harness run plays AND the only leg that
    #   exercises the movie-audio decoder, so a case that skipped them would neither hear the
    #   noise it exists to stop nor be able to prove the decode path still ran. Measured on the
    #   RED run 20260906_145938, which DID carry SkipIntro: one XAudio2 open and ZERO
    #   `[MovieAudio] decoded` lines, i.e. check 6 was vacuous.
    AcceptGap  = 1.0
    Drive      = $false
  }
  DiagEnv = ''
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }
    # THE MUTE. Every mastering voice this run creates reports a volume of exactly 0.
    @{ Kind = 'LogValue'; Name = 'every mastering voice is muted';
       Pattern = 'master volume=(?<v>[\d.]+)'; Group = 'v'; Agg = 'all'; Min = 0.0; Max = 0.0 }
    # THE SIMULATION IS UNCHANGED. The device is really open (mute is not "no audio")...
    @{ Kind = 'LogCount'; Name = 'the audio device really opened';
       Pattern = '\[Audio\] XAudio2 opened:'; Min = 1 }
    # ...and the movie-audio path still decodes and loads its stream with the master at zero.
    @{ Kind = 'LogCount'; Name = 'movie audio still decodes (simulation not skipped)';
       Pattern = '\[MovieAudio\] decoded \d+/\d+ XMA frames'; Min = 1 }
    @{ Kind = 'LogCount'; Name = 'no "running muted" degradation (that is a FAILED open, not a mute)';
       Pattern = '\[Audio\].*running muted'; Max = 0 }
  )
}
