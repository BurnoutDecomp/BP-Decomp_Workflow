# Selected GameState and graphics consumers

The next checkpoint restores runtime connections needed by the debug controls.
It is committed and pushed on an isolated branch; the delivered normal executable
is still the visually inspected `f98a8cb5b` build. Final totals remain
35 verified, seven original no-ops and 1,313 pending sites.

## Checkpoint

`codex/debug-menu-selected-consumer-integration` at
`5b4d44e905ad5f3a6bfd90a4d83436debf1119a9` combines 11 changed files over
`f98a8cb5b7868e8a06563c0b4ea4a75cf352e103`:

- GameState: poll native pad output before the original frame-step query; reuse
  that snapshot in the GUI; connect pause/step and streaming-pause events,
  live world-streaming status, player pose and landmark drawing, loading-event
  translations, the wait countdown and the mode preparation/finish latch.
- Graphics: restore the original occlusion construction, query batching and
  conditional draw callers, plus dispatch continuation. These callers remain
  behind a disabled host selection while their allocator provider is recovered.

The GameState source checkpoint is `de53dc62ea165a11fcbcd5b250d9d8231d9cdcc9`.
Its author reports canonical compilation and 19 input, 84 consumer and 81 preparation
fixture checks. The aggregate evidence is being frozen for a fresh combined
review. These selected GameState consumers affect the running route; the complete
original Construct/Prepare/PreWorld lifecycle remains unactivated.

The graphics source checkpoint is `b49d37a5c730c8b0a39fd0ed82198e7509f01072`.
Its fresh source review passes and two canonical TUs compile. Capacity, provider
compatibility, lifetime, native activation and menu effects remain open.

## Next gates

One full private build is running against the unchanged 2,975-file shipping list.
Fresh GameState review and behavior-specific native checks must pass before
normal delivery. A clean build or startup alone will not promote entry verdicts.

Frozen source preimages, postimages and cherry-pick identities are retained in
`scratch/DEBUG_MENU_1011/selected_consumers_integration_20261015/source_manifest.json`.
The [machine-readable checkpoint](selected_consumers_20261015.json) records the
exact identities and review boundaries.
