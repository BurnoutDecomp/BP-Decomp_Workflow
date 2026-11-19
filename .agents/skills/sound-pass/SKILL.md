---
name: sound-pass
description: >-
  User-invoked only: the sound parity campaign (wrong or idle engine notes, no EA Trax
  music, missing in-game sounds and speech, silent menus). Method: the console's audio
  engine runs on PC, so the usual hole is the game-side dispatch
  (SoundLogicModule::ProcessGameActionQueue and ProcessGuiEvents cases, effect Notify arms,
  a prepare chain nobody calls). Measure with the WAV-capture oracle BRN_AUDIO_CAPTURE
  (BRN_AUDIO_CAPTURE_ENGINE and BRN_ENGINE_MIX_DIAG for the engine alone), never with a log
  line. Harness runs are muted (BRN_AUDIO_MUTE; flow_run -Audio or a case's
  Run = @{ Audio = $true } un-mutes). Per-subsystem BRN_*_DIAG witnesses; car-dependent bugs
  need BRN_DEBUG_JUNKYARD_CAR; rw::audio::core types come from the X360 audio PDB
  (console-evidence). Load only when the user explicitly asks for the sound pass or sound
  parity work.
disable-model-invocation: true
---

Stop unless the user explicitly asked, in their own words, for the sound pass or sound parity work. One sound bug met in passing is `diagnose-parity-bug`.

# Sound pass

Make every sound the original plays play the same way on PC: engines, music, speech, HUD
and menu sounds, effects, ambience.

Not for: a general behaviour difference (`diagnose-parity-bug`); writing or running a case
(`bug-test`); porting sound data (`port-assets`); reconstructing a TU (`reconstruct-tu`).

## The shape of the problem

The console's rwaudiocore engine (mixer, voices, plug-ins) is reconstructed and runs on PC,
mixing through the output leaf
`b5-decomp/src/GameShared/GameClasses/System/PC/CgsAudioOutputPC.cpp` (XAudio2). Above it,
game code posts game actions, GUI events and sound messages; the sound logic module
dispatches them to state managers and effects, which attach voices. When a sound is missing,
the post usually exists and the consumer arm does not: **the dispatch is the usual hole.**

## Method

1. **Reproduce with a measurement.**
   - Put `BRN_AUDIO_CAPTURE=<absolute path>.wav` in the case's `DiagEnv`: `flow_run.ps1`
     clears every `BRN_*` it does not set itself, so a variable exported in your shell never
     reaches the game. It writes the final mix before the mastering volume, so it works on a
     muted run, and patches the WAV header every 32 packets, so a killed run still leaves a
     readable file.
   - Measure RMS per window with Python's `wave` module (and numpy). It is a presence and
     level oracle, not a pitch oracle: a one-second FFT peak did not track engine rpm.
   - EA Trax and the UI sit on top of the engine in the final mix. For the engine alone:
     `BRN_AUDIO_CAPTURE_ENGINE=<wav>`, and `BRN_ENGINE_MIX_DIAG=1` for an `[engine-mix]`
     rms/peak line about every half second (0 means silence).
   - An attach or play witness proves logic ran, not that anything was heard.
2. **Reproduce on the right subject.**
   - The harness accepts the junkyard's default car, so a defect that only hits a car the
     player picks is invisible in a default run. Once, every engine measurement came from
     the one car that worked.
   - `BRN_DEBUG_JUNKYARD_CAR=<VehicleList id or car name>` picks the car through the
     console's own car-select event in the junkyard. `BRN_DEBUG_PLAYER_CAR=<id>` swaps it
     mid-drive through a harness path and can miss junkyard-path bugs. Carousel taps:
     `flow_run.ps1 -CarSelectTaps` (`bug-test`).
   - Fresh and saved profiles play different things (tips already marked seen, selectable
     songs): reproduce with the kind of profile the report came from.
3. **Find the hole, dispatch first.**
   - Compare the console's arms with ours in `SoundLogicModule::ProcessGameActionQueue`,
     `ProcessGuiEvents`, every effect's `Notify` and the state managers. `work audit <tu>`
     reports `MISSING_CASE` and `MISSING_EVENT`; read the assembly for arms the pseudocode folds.
   - Walk producer, bridge, dispatch arm, sound message, effect or state manager, voice, and
     check each link with `python tools/re/hasbody.py <Class::Method>`. A body with no caller
     is common: a prepare chain whose entry nothing calls leaves a whole domain silent. Find
     the caller, not the name.
   - Sound message ids are the `ESoundMessages` enum in
     `b5-decomp/src/GameSource/Sound/Module/LogicModule/BrnMessageData.h`.
   - Payload width: read what the console posts (an `ld`/`std` pair is 8 bytes); a narrower
     record makes the consumer read past it. A GUI record's layout is whatever its producer
     posted (`b5-decomp/src/GameShared/GameClasses/Gui/CgsGuiModule.h`).
   - Before correcting a producer to the console's shape, find every consumer written
     against the old one: a compatibility arm can depend on the wrong producer, and fixing
     one side silences the other.
4. **Data before code.** A sound that never plays may be a bundle that was never converted.
   The loader logs it instead of asserting: a `[stream] LoadBundle` line with -2 and one
   `[FLAG PC bring-up] bundle '...' is not present in this port` line. The porters and the
   manifest are `port-assets`.
5. **Read holes and tables from the image.** `tools/re/ppcdis.py <hexaddr>` for a function
   the export set lacks (take the address from the caller's `bl`); `tools/re/x360rd.py` for
   `.rdata` (corroborate every value a second way).
6. **Fix 1:1** under the `reconstruct-tu` rules. Never invent a level, a priority, a
   fallback or a guard: an invented stream priority once let music refuse a voice-over, and
   an invented `else 1.0f` hid a settings table that was never bound.
7. **Expect two defects on one chain.** Fix one, measure again. Declaring victory after the
   first is how a sound was reported fixed and was not.
8. **Prove it**: RED before, GREEN after, with the capture and the witness, on the affected
   subject (`bug-test`).

Recurring defect shapes, with the dated cases they came from: [references/defect-shapes.md](references/defect-shapes.md).

## Harness muting

- Every harness run is muted: `tools/diagnostics/flow_run.ps1` sets `BRN_AUDIO_MUTE=1`, and
  the PC leaf answers with one `SetVolume(0)` on the XAudio2 mastering voice. The device
  still opens and the whole audio simulation runs unchanged; every device open logs
  `master volume=`, so a silent run is checkable (`tools/tests/cases/quiet_audio_mute.ps1`).
- `flow_run.ps1 -Audio`, or a case's `Run = @{ Audio = $true }`, makes a run audible. A
  hand launch of the exe is audible: only the harness sets the variable.
- The capture never needs un-muting: it taps the mix before the mastering voice.

## Witnesses and types

- Each sound subsystem has an opt-in witness passed through `DiagEnv`; which variable, which
  file prints it and what it measures: [references/witnesses.md](references/witnesses.md).
  A new witness is bounded and gated (`bug-test`), never per-frame and unbounded.
- `rw::audio::core::` types come from the X360 audio PDB in `IDA Files/` (an Xbox 360
  build of another game; a local input): authoritative for the field order, names and
  types of the shared rwaudiocore vocabulary, with pointer widths widened for PC; never for
  Burnout's own `CgsSound` and `BrnSound` shapes, which stay ARTIST plus DecFIGS. The rule
  and the extraction command are in `console-evidence`.

## Where the state lives

- `progress/audio_faithfulness/`: the audio faithfulness audit and the engine phase plans.
- `progress/ONLINE_PAUSE_SOUND_20261105.md`, and the Sound cohorts under `progress/debug_menu/`
  (the debug menu's sound controls belong to `debug-menu-campaign`).
- A worked capture case: `tools/tests/cases/net_lan_pause_sound.ps1`.

## Never

- Never call a sound fixed from a log line: measure the capture on the affected subject.
- Never test a bug about other cars, or about a saved profile, only on the harness default.
- Never invent a gain, priority, fallback or guard to make something audible.
- Never take the X360 audio PDB's shapes for Burnout's own sound classes.
- Never add an unbounded per-frame witness.
- Never keep a fixed-point sample cursor in `long`: MSVC's `long` is 32 bits, so a 16.16
  cursor overflows within a second of audio and indexes negative on the audio thread. Use `s64`.

## Tools

- `tools/diagnostics/flow_run.ps1` (`-Audio`, `-DiagEnv`, `-CarSelectTaps`), through
  `tools/tests/run_case.ps1` (`bug-test`).
- `work audit <tu> [--refresh]`; `python tools/re/hasbody.py <Class::Method> [--status]`.
- `tools/re/ppcdis.py <hexaddr> [n]`, `tools/re/x360rd.py <hexaddr> [nbytes]`.
- Python's `wave` module (and numpy) for RMS per window.

## Read next

- [references/witnesses.md](references/witnesses.md): the diagnostic variables.
- [references/defect-shapes.md](references/defect-shapes.md): the shapes that recur.
- Skills: `bug-test`, `diagnose-parity-bug`, `console-evidence`, `reconstruct-tu`,
  `port-assets`, `debug-menu-campaign`.
