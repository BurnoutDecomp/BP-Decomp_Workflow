# Debug-menu evidence

Depth for [`../SKILL.md`](../SKILL.md). These rules come from the campaign's stop record
(`DEBUG_MENU_HANDOFF.md`) and its cohort decisions under `progress/debug_menu/`; every
cohort folder shows them applied.

## What a disposition needs

### `verified`

- **The original chain**: registration, storage, callback and consumer, read from the ARTIST
  assembly and pseudocode, with DecFIGS for declaration shape and LegacySrc for style only.
  The Apt runtime keeps its x64 exception (`console-evidence`).
- **The source** that implements it, if anything changed: commits, compile, faithfulness
  scan, a fresh independent review, a full shipping build.
- **The build under test**, identified exactly (source commit and exe hash) in the cohort
  record, not in a summary.
- **The scene genuinely present**: the real producer the consumer reads (attached rivals for
  an AI control, real collisions for a scrape or collision control, real deformation updates,
  the real GUI or HUD message route), not a stand-in.
- **Raw records for each phase**, each joined to the input that caused it and the consumer
  that produced the output (frames, log lines, native acknowledgements):
  - positive: the output appears;
  - negative: it is absent;
  - restore: the typed value and the output return to the baseline.
- **No new asserts or exceptions** in the run, and the failures of earlier attempts kept.
- **The limit**: what the evidence does not cover (other parameter values, other scenes,
  hardware, audibility).

### `original-noop`

- Proof from the original binary that the control is inert: an empty callback, or a storage
  cell with no reader anywhere (full reader and xref closure, including reads through other
  addresses). Adjacent active flags, or a working subsystem nearby, do not establish a reader.
- The original registration and storage semantics stay in our tree; no earlier-build
  consumer is restored. No native visibility claim is needed.
- A partial reader closure is not a disposition: it stays `pending`.

### `original-broken`

- Proof from the original code that the control is broken as shipped (a reader that can
  never fire, a consumer that misuses the value), reproduced faithfully and never "fixed".

## Scenes and producers

- A control whose consumer needs a producer needs that producer running in every phase,
  repeated in each relevant phase. Visible traffic is not a passby lifecycle; a key tap is
  not an event-consumer witness; a counter that changes is not the geometry it counts.
- A scene that needs a location uses the original's own post-exit teleport or control path,
  or a genuinely synchronised fixture. Never loosen a pose gate or invent a transform. The
  harness's "seat ok" text alone does not prove placement. A scene guard that stops before
  activation correctly yields zero targets and zero credit.
- Timing joins the real event, not an earlier proxy: a profile gate must wait for the
  profile-loaded notification, not a step that happens before it.
- Physical controllers, hardware-specific graphics, audibility, and multi-PC or multi-peer
  cases need their own real validation; a desktop harness run does not cover them.

## Test-protocol failures not to repeat

Each of these cost a run and none is a game feature: overlong native aliases; missing or
late profile-load evidence; activating a sound INI before the audio core (RWAC) existed;
Boolean and enum conversion mistakes; schema mismatches between a runner and its checker;
stale scene and motion receipts; a frame-acknowledgement parser anchored so that it missed
audio-prefixed records. Fix the harness, rerun, and never count the fix as progress.

## Reporting

Keep these distinct in every update: recovery (code exists), registration coverage,
compilation, field readback, and behaviour. Conflating them is what made the campaign's
earlier reports unreliable: a successful boot or an assert-free run can still hide broken
counters, inactive render consumers, missing producers, lost persistence and multiplayer
cleanup gaps. There is no defensible global implementation percentage beyond the
disposition counts in `progress/debug_menu/entries.json`.

## Recording

- `verdicts.json`, one row per site id: `state`, `notes` (the bounded effect and its limit),
  `evidence` (repo paths: the cohort folder, the case, the fixture), plus optional source,
  exe and native-case fields.
- Regenerate `entries.json` with `python tools/re/debug_menu_inventory.py`; it validates the
  states, refuses a verdict for a missing site, and refuses a non-pending verdict without
  evidence and notes.
- The cohort folder's `ROOT_DECISION.json` lists the accepted ids, the ids already credited
  (not recounted), the ids still pending, the counts before and after, the effect scope,
  whether the failed attempts were preserved, and the new asserts and exceptions.
- Cohort archives and raw captures are evidence: never delete one, and never rewrite an
  original FAIL receipt. Keep captures capped.
