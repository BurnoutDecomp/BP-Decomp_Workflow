---
name: debug-menu-campaign
description: >-
  User-invoked only: the debug-menu parity campaign, making every debug-menu entry of the
  original behave exactly like the X360 ARTIST build, including genuine original no-ops and
  broken leftovers, never earlier-build behaviour. Covers what counts as a final disposition
  (verified, original-noop, original-broken) and what does not (recovered or compiled source,
  a source audit, a value that changed, a failed aggregate run), the registry
  (progress/debug_menu/entries.json, verdicts.json, per-cohort ROOT_DECISION.json), finding an
  entry (debug-menu.cmd, tools/debug_menu/search.py --query), regenerating the inventory
  (tools/re/debug_menu_inventory.py), and the evidence a disposition needs. Load only when
  the user explicitly asks to resume or work the debug-menu campaign.
disable-model-invocation: true
---

Stop unless the user explicitly asked, in their own words, to resume or work the debug-menu campaign. Nothing in it (recovery, agents, builds, game launches) restarts on its own.

# Debug-menu campaign

**End state:** every debug-menu entry behaves like the X360 ARTIST build, including genuine
original no-ops and broken leftovers. Never invent earlier-build behaviour to make such an
entry useful. Resume from the registry and live git, status and evidence, not from a chat
narrative; the stop record is `DEBUG_MENU_HANDOFF.md` (repository root) and the chronology
`progress/debug_menu/README.md`.

Not for: an ordinary gameplay bug (`diagnose-parity-bug`); writing or running a harness case
(`bug-test`); reconstructing a TU (`reconstruct-tu`).

## What counts

A **final disposition** is a row in `progress/debug_menu/verdicts.json` whose `state` is:

- `verified`: the original output is proven in the right scene, bounded by its recorded
  scene, input, consumer and evidence. It is not a promise that the subsystem or every
  parameter value is correct.
- `original-noop`: the original registration and storage exist, and the original code
  proves the control is inert (full reader and xref closure of its storage cell).
- `original-broken`: the original code proves an authentic broken leftover.

`tools/re/debug_menu_inventory.py` accepts exactly these plus `pending`, and refuses a
non-pending verdict without `evidence` and `notes`.

**Not a disposition**, however much work it took: recovered, integrated or compiled source;
a source audit or a reviewed source cohort; a ledger `done` or `reviewed` (status.json says
nothing about menu behaviour); a field readback or a Boolean that changed; a counter that
moved without its visible consumer; a boot, a no-assert run or a harness "seat ok" line; a
key tap without its event consumer; a planned scene; a registration label. An aggregate run
that FAILED stays FAIL: accept individual sites from it only on independently joined
evidence, and never call it a whole-suite pass.

## The registry

| File | What it is |
|---|---|
| `progress/debug_menu/entries.json` | generated inventory: one row per original registration site, stable id `<registration function>#NNNN`, caption, menu path, kind, original call address and export, `state`; `summary.states` holds the current counts |
| `progress/debug_menu/verdicts.json` | the hand-maintained decisions keyed by site id: `state`, `notes`, `evidence` (paths), optional source, exe and native-case fields; they survive regeneration |
| `progress/debug_menu/assembly_registrations.json` | assembly supplements for registrations the exporter missed |
| `progress/debug_menu/<cohort>_<date>/` | one cohort's evidence: `ROOT_DECISION.json` (accepted ids, ids already credited and not recounted, ids still pending, counts before and after, effect scope, failed attempts preserved, new asserts and exceptions, source and exe identity), README, reviews |

The machine registry is the answer for an individual entry; prose never overrides it. A
site id is a registration site, not necessarily one visible row: some sites generate several
rows, aliases or repeated entries.

## Working a cohort

1. **Group** related sites (same component, consumer or scene) into one cohort, but keep
   per-site limits in every record.
2. **Find each entry**: `debug-menu.cmd --query "<words>"` (PC source registrations;
   `--include-reference` adds ARTIST-only entries, `--json` for scripts). In the game,
   Ctrl+Space opens the menu.
3. **Establish the original chain** for each site: registration, storage, callback, consumer,
   from the ARTIST assembly and pseudocode (`console-evidence`). An export hole is not absent
   code: `tools/re/ppcdis.py` and `tools/re/x360rd.py` read the image directly, so never
   claim the original bytes are inaccessible because an export or a worker route is missing.
4. **Recover and integrate** missing or wrong code against the assembly (`reconstruct-tu`,
   `diagnose-parity-bug`; mounts per `build-and-link`), then the source checks: compile,
   faithfulness, fresh review, full build.
5. **Prove behaviour** in the right scene (`bug-test`): the original output in a positive
   phase, its absence in a negative phase, then restoration, each joined to the raw input
   and the consumer. Or prove authentic inert or broken behaviour from the original code.
6. **Record**: add the verdict rows (state, notes, evidence paths), regenerate the inventory
   with `python tools/re/debug_menu_inventory.py` (it needs `.ida-exports/`, a local input,
   and fails if a verdict names a site that does not exist), write the cohort folder, land.

What each kind of evidence must show, and the scene problems that wasted the most time:
[references/evidence.md](references/evidence.md).

## Running the game for evidence

- Never let a test touch the normal profile `build/game/Memcard/Profile.sav`. Copy the
  current save into a private harness slot (any slot but 0 has its own Memcard directory;
  `bug-test`) and prove it actually loaded before any input.
- Own exactly what you start: match the process, slot and start time, use scoped input only,
  cap logs and frames, restore the typed baseline, and clean up only owned processes. The
  old global End fallback is retired: never reintroduce global input.
- Before reusing a retained package from scratch, verify its source, build and helper pins
  and its producer and consumer coverage: some are failed or superseded by design, and old
  queue files and graphs are history, not current truth.
- The frozen files under `progress/debug_menu/shutdown_20261101/pending_work/` are unfinished
  and unapproved; they add no credit and are not to be launched as they stand.

## Never

- Never invent earlier-build behaviour, a synthetic event, a transform or a no-op
  classification to settle an entry.
- Never count compiled source, a readback or a passing boot as behaviour.
- Never turn a failed aggregate into a whole-suite pass, or recount a site already credited.
- Never classify a site `original-noop` without full reader and xref closure of its storage.
- Never loosen a scene or pose gate to get a phase to run.
- Never delete an evidence archive or rewrite an original FAIL receipt.
- Never describe a history-only branch consolidation as finished implementation.

## Tools

- `debug-menu.cmd [--query Q] [--include-reference] [--json] [--no-open] [--output FILE]`:
  the finder (`tools/debug_menu/search.py`; `--query` searches without writing the page;
  details in `tools/debug_menu/README.md`).
- `python tools/re/debug_menu_inventory.py [--exports DIR] [--output FILE] [--verdicts FILE] [--assembly-supplements FILE]`:
  regenerates `entries.json` from the ARTIST exports plus the verdicts.
- `tools/re/ppcdis.py <hexaddr> [n]`, `tools/re/x360rd.py <hexaddr> [nbytes]`: the image,
  for export holes and data tables.
- The harness cases named `debug_menu_*` under `tools/tests/cases/` (`bug-test`).

## Read next

- [references/evidence.md](references/evidence.md): evidence per disposition, scene and
  producer rules, the test-protocol failures not to repeat.
- `progress/debug_menu/README.md` and the cohort folders: state and limits per cohort.
- Skills: `console-evidence`, `bug-test`, `reconstruct-tu`, `diagnose-parity-bug`,
  `campaign-conductor`, `campaign-lane`.
