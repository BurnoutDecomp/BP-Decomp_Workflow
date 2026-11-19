# How `work reconcile-from-files` decides

Depth for [`../SKILL.md`](../SKILL.md). The authority is the code:
`tools/work/reconcile_from_files.py` (`target_for_tu`, `classify_files`, the marker regexes
at its top). Re-read it before relying on a detail here.

## Inputs

- The committed blobs of the b5-decomp commit the parent's index records
  (`git rev-parse :b5-decomp`), files under `src/` and `vendor/` ending `.cpp`, `.h`,
  `.hpp` or `.inl`. Uncommitted edits and an unrecorded pointer are invisible to it.
- `progress/status.json` (the rows it may change), `progress/tu_index.json` (the TU set and
  each TU's functions), `progress/class_homes.json` (homes for `class:` TUs).
- No server call and no dependence on `ledger.sqlite`.

## Decision per TU, in order

1. Already `external`, or a vendor TU: `external`.
2. The TU's own note declares it unfinished (a partial count such as "12 of 20 done", or
   an explicitly shipped stub or floor that was deferred): `blocked`, note kept.
3. Any of its functions carries an explicit reconstruction trap: a `CGS_ASSERT(false, ...)`
   whose text says not reconstructed, link stub, or deferred, or a comment attached to the
   definition such as "DELIBERATELY NOT BODIED" or "body intentionally not reconstructed":
   `blocked`.
4. `class:` TU: its home file from `class_homes.json` decides (a skeleton home means `todo`;
   a real home means `done`, and an incomplete sibling class in the same file does not taint
   it). With no home: `done` only if every non-thunk function is defined somewhere, else `todo`.
5. `module:` TU: `done` only if every non-thunk function is defined somewhere, else `todo`.
6. Path TU: a corrected path named in its note, else the mirrored file
   `b5-decomp/src/<tu id>` with any source suffix:
   - complete: `done` (a `.cpp` TU whose only file is a header needs every body there);
   - carries an incomplete marker: `blocked`, with a note saying so;
   - skeleton (no line but comments, braces, preprocessor lines, namespaces or trap calls
     such as `__debugbreak`): `todo`;
   - no file: `done` only if every function has an exact qualified definition elsewhere
     (a misattributed path), else `todo`.

Side effects on function rows: a TU that ends `done` sets each of its functions to
`reviewed`. That is why `reviewed` is the default and carries no information. A TU leaving
`done` for `in_progress` or `blocked` sets its functions to `recovered`.

## Promote-only (the default) versus `--allow-demote`

Promote-only keeps the existing state when the files would demote it: `done` stays unless
the target is `done` or `external`; `external` stays; `blocked` moves only to `done` or
`external`; otherwise the higher rank wins. The exception is explicit contradictory evidence
(steps 2 and 3, or a partial file): that demotes even in promote-only mode. It also keeps
rows for TUs an older index had. `--allow-demote` projects exactly the current index and
lets the files demote or remove rows.

## Blind spots

- **Narrow markers.** The incomplete-file markers are specific phrases ("TODO: Implement",
  "committed file is partial", "needs finishing", "skeleton, not faithful", ...) plus the
  invention-accommodation phrases (`LocateMovieRoot`, "our converted", "converter
  accommodation"). A bare TODO, FIXME, "guessed" or "placeholder" does not trip it. Rule:
  a file with author TODOs is not done, whatever reconcile says.
- **Engine stubs.** A `return null;` or `{}` body standing in for engine code is
  `work faithfulness`'s `engine_stub`, not a reconcile signal.
- **Trap stubs as definitions.** "Every function defined somewhere" counts a plain trap
  body without explanatory text as a definition, as `tools/re/hasbody.py` does. Open the file.
- **Path misattribution.** A TU id can carry a wrong path (a `Unity/..` segment, a class
  homed under another basename); step 6 then finds no file and falls back to definitions.

## History behind the rules

- **Phantom done, both directions (2026-06).** An older `work submit` compiled whatever
  `.cpp` was modified when the TU's own file did not exist, so TUs were recorded `done` with
  no source, while TUs with real committed files sat at `todo`. The tell was a `status.json`
  change with no b5-decomp change. Since then `work submit` requires a recorded `dest_path`
  or explicit `--files`, and this reconcile anchors status to the committed files.
- **Phantom reviewed, later.** Functions stayed `reviewed` while their bodies were
  `CGS_ASSERT(false, "NOT RECONSTRUCTED")` traps under a path-misattributed TU id, and
  `hasbody.py` reported a body because a trap is a definition: two indicators, both wrong.
  Explicit traps of that form are now step 3.
- **False positives.** The first version demoted any file containing TODO, FIXME, guessed
  or placeholder, so complete reconstructions whose comments said "placeholder names" or
  "bodies are guessed (inlined)" fell to `in_progress`. The markers were narrowed. If a
  complete file still trips a marker, the comment is wrong: reword it, then re-submit.
- **Server event history lost.** A ledger and server rebuild reset the server database and
  overwrote its only backup, so the recorded events were replaced by a git-derived
  projection. Hence hard rule 1 in the skill.
