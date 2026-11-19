# Sound diagnostics

Depth for [`../SKILL.md`](../SKILL.md). Every variable here is opt-in, not in the X360
binary, and reaches the game only through a case's `DiagEnv` (or `flow_run.ps1 -DiagEnv`),
because `flow_run.ps1` clears every other `BRN_*` variable. Paths are under `b5-decomp/src/`;
the header or file named is where each witness documents what it prints. Grep the variable
in b5-decomp before relying on a line format: witnesses get renamed.

## Measurement

| Variable | File | What it gives |
|---|---|---|
| `BRN_AUDIO_CAPTURE=<wav>` | `GameShared/GameClasses/System/PC/CgsAudioOutputPC.cpp` | the final mix (primary and engine fills) before the mastering volume, as 16-bit PCM; logs `[Audio] capture -> <path>`; header patched every 32 packets |
| `BRN_AUDIO_CAPTURE_ENGINE=<wav>` | same | the engine fill alone, before it is mixed |
| `BRN_ENGINE_MIX_DIAG=1` | same | `[engine-mix] line= rms= peak=` about every half second |
| any of the three above | same | also `[audio-output] prelimit peak= overrange= ... starved=`: device-callback timing (a starved voice is an audible click) |
| `BRN_AUDIO_MUTE=1` | same; set by `flow_run.ps1` unless `-Audio` | mastering voice at 0; each device open logs `master volume=` |

The capture is a presence and level oracle. Read its rate and channel count from the
`[Audio] XAudio2 opened` lines when a run re-opened the device: the header keeps the first.

## Logic witnesses

| Variable | File | Witnesses |
|---|---|---|
| `BRN_SOUNDLOGIC_DIAG=1` | `GameSource/Sound/Module/LogicModule/BrnSoundLogicModule.cpp` | `[snd-logic]`: the sound module's dispatch |
| `BRN_MUSIC_DIAG=1` | `GameSource/Sound/Global/BrnMusicEffect.cpp` (and the GUI side) | `[music]`, `[trax]`: the music effect and EA Trax selection |
| `BRN_SPEECH_DIAG=1` | `GameSource/Sound/Global/BrnSpeechEffect.cpp`, `GameSource/GameState/TrainingManager/BrnTrainingManager.cpp` | `[speech]`: voice-over requests and playback |
| `BRN_HUD_SOUND_DIAG=1` | `GameSource/Sound/Global/BrnHudSoundDiag.h` | `[hud-sound-attach]`, `[hud-sound-msg]` and siblings: HUD and FX effects |
| `BRN_STREAM_DIAG=1` | `GameShared/GameClasses/Sound/CgsStreamDiag.h` | `[sndstream]`: the streaming request ring, stream voices, the stream-buffer records |
| `BRN_DMIX_DIAG=1` (2 adds the per-channel table) | `GameShared/GameClasses/Sound/Logic/CgsDMixDiag.h` | `[dmix]`: the dynamic mixer's endpoints, inputs and outputs |
| `BRN_AEMS_DIAG=1` | `GameShared/GameClasses/Sound/Playback/AEMS/CgsAemsFactory.cpp` | AEMS and presentation playback witnesses |
| `BRN_ENGINE_DIAG=1` | `GameSource/Sound/Vehicles/BrnEngineAudioDiag.h` | `[engine-attach]`, `[engine-asset]`, `[engine-registry]`, `[engine-param]`, `[car-audio]`: the player engine chain |
| `BRN_AI_SOUND_DIAG=1` | `GameSource/Sound/Vehicles/BrnAISoundDiag.h` | `[ai-sound-load]`, `[ai-sound-attach]`, `[ai-sound-detach]`, `[ai-sound-engine]`: rival engines |
| `BRN_GINSU_DIAG=1` | `GameShared/GameClasses/Sound/Playback/Plugins/Ginsu/GinsuPlayer.cpp`, `GameSource/Sound/Vehicles/Engines/BrnDualGinsuEffect.cpp` | `[ginsu]`, `[ginsu-prep]`: the engine synthesiser and its content |
| `BRN_RWAC_PARAM_DIAG=1` | `GameShared/GameClasses/Sound/Playback/RWAC/CgsGenericRwacVoice.cpp` | `[rwac-param]`: each voice parameter pushed into a plug-in attribute, with a clamp marker |
| `BRN_VEHICLE_AUDIO_AUDIT=1` | `GameSource/GameState/GameStateModule_gUI_00.cpp` | once per process: the vehicle list's engine and exhaust banks against the disk |

## Control knobs (they change what runs: name every one you used in the report)

| Variable | File | Effect |
|---|---|---|
| `BRN_DEBUG_JUNKYARD_CAR=<id or name>` | `GameSource/GameState/GameStateModule_gUI_00.cpp` | posts the console's own car-select event in the junkyard |
| `BRN_DEBUG_PLAYER_CAR=<id or name>` | same | swaps the player car mid-drive through a harness path |
| `BRN_MUSIC_FORCE_TYPE=<n>` | `GameSource/Sound/Global/BrnMusicEffect.cpp` | forces the music type (a control run for the capture) |
| `BRN_ATOMIKA_VO_INTERVAL=<seconds>` | `GameSource/GameState/TrainingManager/BrnTrainingManager.cpp` | overrides the console's spacing between tip voice-overs |
| `BRN_MOVIE_AUDIO_PC=1` | `GameSource/Gui/BrnGuiMovieManager.cpp` | turns on the PC movie-audio stand-in; the console path plays the movie's sound through the music effect, and with both on both play |

## Example

`tools/tests/cases/net_lan_pause_sound.ps1` combines the capture with `BRN_SCREEN_DIAG`,
`BRN_AEMS_DIAG`, `BRN_SOUNDLOGIC_DIAG` and `BRN_HUD_SOUND_DIAG` around scripted menu taps.
Its header names an `audio_gating.py` level-analysis script that is not in the
repository, so measure the WAV with Python's `wave` module.
