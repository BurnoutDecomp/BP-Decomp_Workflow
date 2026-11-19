# Sound defect shapes that recur

Depth for [`../SKILL.md`](../SKILL.md). Each shape below was found in the sound pass of
September 2026 and fixed; the code comments at the named functions tell the whole story.
They are here so the next defect of the same shape is recognised in one run, not five.

## Dispatch and callers

- **Missing dispatch arms.** The game-action and GUI-event dispatchers of the sound logic
  module once handled a small fraction of the console's cases, so training speech, EA Trax
  control and HUD stings were posted and died there. First question for any missing
  sound: does the dispatcher have the console's arm for this post?
- **Empty effect bodies.** An effect whose `Notify`, `Attach` or `ProcessUpdate` has no body
  falls through to the base's empty one: every message it should play is swallowed silently.
- **A chain nobody calls.** A manager can be fully reconstructed and mounted and still never
  run because the chain that prepares it (a "prepare on entering gameplay" path) has no
  caller. The AI-vehicle sound domain sat silent that way: the boot-time prepare skips it by
  design, and the later prepare chain was missing. Use `hasbody.py` on every link, then find
  the caller.
- **A unique id that never increments.** A missing override of the logic module's id
  generator left every voice, content and stream buffer sharing ident 0, so a detach matched
  every buffer and the streaming pool ran dry.

## Payloads and keys

- **Record width.** A GUI audio-settings event posted as a 4-byte value where the console
  posts an 8-byte pair made the mixer read its second field past the record, dropping the
  whole SFX bed by about 20 dB. Read the console's `ld`/`std` or `lwz`/`stw` widths.
- **A wire header inside the payload.** A music message's payload carried the GUI record
  header, so the menu-music request latched forever.
- **Half-width keys.** Attribute keys stored as their low 32 bits made every lookup in a
  64-bit keyed collection miss (speech data); the full key comes from the `ori`/`insrdi` pair
  in the assembly.
- **Two different hashes.** Playback names use `Name::MakeHash`
  (`GameShared/GameClasses/Sound/Playback/CgsCommon.h`); resource and trigger ids use
  `CgsResource::ID::HashString` (`GameShared/GameClasses/System/Resource/CgsResourceID.h`, a
  zero-extended CRC32). Check which one a table was built with before matching against it.

## State machines

- **A double store hides an edge.** A state update that wrote its state pair twice in one
  frame meant `HasChangedTo(ATTACHED)` was never seen, so the car-audio streamer never left
  ATTACHING: every car change kept the old sound.
- **Right value, wrong member.** An effect control's `Detach` wrote FINISHED into its attach
  state instead of its detach state, so every control attached once per session and the
  second car of a session kept the first car's engine attributes. Its sibling with a
  byte-identical console body was already right: compare siblings.
- **Invented priorities.** Music stream requests carried an invented priority equal to
  speech's, so a voice-over could be refused for lack of a free state and the intro soft-
  locked; on the console music is lower and speech evicts it.
- **Invented fallbacks.** A missing settings binding was masked by an invented default gain;
  binding the console's table showed the real cause of a low level was elsewhere (the
  dynamic mixer).

## Measurement traps

- The harness's default junkyard car was the one car whose engine worked, so every engine
  measurement passed while players heard idle notes on every other car.
- A log line saying a voice attached was read as "it plays". Measure the capture.
- Two defects sat on one chain twice in a row: the first fix was necessary and not
  sufficient both times.
- A data gap can look like a frozen game: an assert on a missing bundle used to halt the
  process on a dialog; the loader now logs the missing file and replies with a failure.
