# Sound and Challenge source recovery

Two specialist batches passed a combined independent source review and the
shipping build. Their game behavior remains pending; this publication adds no
verified/original-noop verdicts to the inventory.

Sound restores the original embedded owner's Construct/Register calls, typed
LogNull/LogOutput sinks and Console registration/routing. Nine Global controls
bind the real SubmixesEffect storage, with original defaults, ranges and steps.
The existing Emitters/Debug and Passbys&Reverb/Show Static fields are registered.
This recovers 11 of 136 OnActivate sites plus Console; 125 activation sites,
seven missing bodies, statistics drawing and audition chains remain unresolved.
The former local const mixer values prevented menu edits reaching the consumers.
DecFIGS declares mutable globals, corroborated by ARTIST data placement.

The general log pointer now has the original StrStreamBase interface so it can
select real null/TTY sinks. Diagnostic helper pointer/reference changes only
propagate that type; native file queue/durability behavior is unchanged.
The shipping source list mounts the existing LogOutput body. Both SoundLogicModule
forward declarations match their actual struct home, fixing the integration ABI.
ARTIST RootSoundModule::Destruct has no DebugComponent::Destruct call; none is added.

Challenge's Start Challenge callback now matches ARTIST's single +14 byte store
instead of asserting. No challenge-start action is invented. The inspected cache
has no reader for that latch or Challenge Index; this scan does not exclude code
outside the cache. The five original bindings and complete-all chain are reviewed.

Validation:

- Sound: 43/43 production-body checks after integration; pre-change HEAD is
  missing five recovered bodies. The fixture tests construction, real sink routing,
  shared mixer addresses/metadata and the full SubmixesEffect update bodies.
- Challenge: 18/18 production-body checks; pre-change 16/18 exposes the missing
  latch store and invented trap. Checks cover real bindings, completion iteration,
  achievement notification, local completion bits and unlock check.
- Canonical per-TU compile and faithfulness gates pass. Final shipping build
  `scratch/DEBUG_MENU_1011/build/20261011_171131_debug-hud-sound-linked.log`
  compiles/links 2,950 TUs with zero warnings/errors.
- Combined fresh-eyes review: Sound VERDICT: pass; Challenge VERDICT: pass.
  Both are bounded source verdicts, explicitly excluding game/audio certification.

Original evidence and review packets:

- `scratch/DEBUG_MENU_1011/sound/REVIEW.md`, `HANDOFF.md`, original constructor
  disassembly, raw data/vtable checks and postmortem packets. The constructor
  export hole at 826A1230 is recovered from the unpacked ARTIST image through
  existing ppcdis/x360rd tools. Root Construct 826AF350, InstallConsole 826893B0,
  OnActivate 826D5CB0 and SubmixesEffect bodies are assembly reviewed.
- `scratch/DEBUG_MENU_1011/page_audit/report.md` and `coverage.json` identify
  all five Challenge sites, callback 82817350, embedded owner initialization and
  registration, consumer chains and no-reader scan limits.
- `b5-decomp/tests/run_sound_debug_menu.py` and
  `b5-decomp/tests/run_challenge_debug_menu.py` reproduce the production checks.

Next: isolate game checks with copied profiles, share setup across related
controls, inspect actual mixer/output/completion effects, and only then record
supported inventory dispositions. Source presence and saved settings alone do
not certify audible behavior or profile completion.

Source commit: `b5-decomp e9a1ad21`. Verified inventory remains 13; original-noop
remains 2; pending remains 1,339 static registration sites. Dynamic rows remain
additional enumeration work.

Sound follow-up: the complete 137-site page, grouped checks and shared native
witnesses are now published in [batch 6](SOUND_BATCH_20261011.md). The counts
and unresolved Sound bodies above describe this earlier source checkpoint.
