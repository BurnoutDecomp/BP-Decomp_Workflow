# Cold saved-route profile handoff boundary

Status: evidence-only boundary packet; no source patch is proposed.

Base: `d3ec7d2dd65a37b489d1dbf61a53b9ce030385ee` (physical parent `edca934dc502f71f64ad873cdd386afe5e3eeeb2`). The inspected profile and `OnlineGameOptions` source blobs are unchanged from `edca934`; `bindings.json` records each blob ID and SHA-256. This packet is independent of and does not modify the stored-inbox proposal.

## Finding

The saved profile and the menu use separate `OptionsDataProfile` instances. ARTIST `ProfileManager::ReadProfileData` copies the live `GuiCache` options block into `ProfileManager::mStoredData` before storage I/O. On a successful load, ARTIST `ReportTaskCompleted` validates that stored image, calls `NotifyOtherModulesLoadComplete` on the **stored** options block, posts event 19 as a one-byte completion event, and mirrors only the new-profile flag into `GuiCache`. It does not copy the stored route arrays or counters into the live cache.

The create-match helpbar and Option0 gate read the live `GuiCache` profile counters. ARTIST and DecFIGS-backed declarations show those are not the same object as `mStoredData.mOptionsDataProfile`. The traced original producer and route-array writer callers do not establish another stored-to-live transfer owner. Consequently, this packet does not propose a copy or event-specific bridge: that would add behavior without an ARTIST owner or call chain.

This is an unresolved original behavior boundary, not a verified no-op. The event-19 producer is proven to send one byte, but this packet does not identify every possible event-19 subscriber or prove an exhaustive whole-image search for arbitrary writes. A future change needs original evidence for a receiver/owner that adopts the stored route arrays.

## Retained case B

The copied disk profile has `created_count=1`; the case report records a successful boot read and profile validation. In the same retained run, the create-match helpbar reports `used=2`, matching the two-item branch when the live counts do not enable Load. The run report also records `ON_GAME_OPT` followed by `ON_SEL_ROUTE`, and later route readiness is the default route (`count=1`, landmark `4671`), not the copied saved route (`count=8`, different landmarks). These observations are consistent with the source boundary, but the log does not directly sample live count memory. The harness field `saved_route_list_visible` is only a post-tap marker; it is not proof that the saved-list page opened.

Original run source was `af18caf8a9e02428cfaa4705599e2b1ca9ea7377`, binary `e9fc6246dece`. The retained report, acceptance JSON, excerpt and full-log SHA are recorded in `bindings.json`.

## Packet contents

- `evidence/artist/`: raw ARTIST exports for the original profile load, completion, route consumers, route writers and callbacks. Use the assembly for call/offset evidence; the decompiler prototype is not authoritative.
- `evidence/decfigs/`: relevant declaration shapes for `OptionsDataProfile`, `ProfileStoredData`, `GuiCache` and save/load metadata.
- `evidence/pc_d3ec/`: exact current source snapshots for the bounded chain and UI readers/writers.
- `evidence/retained_case_b/`: the retained failure report, acceptance JSON and relevant line-numbered game-log excerpt.
- `evidence/source_hashes.tsv`: SHA-256 and byte count for each packet evidence file except the hash manifest itself.
- `bindings.json`: base/blob bindings, ARTIST symbol/xref bindings, DecFIGS source bindings, retained-run provenance and evidence hashes.
- `evidence/original_live_stored_trace.md`: the detailed call/ownership trace and limits.

No production files, Git refs/index, build, tests, CI or game input were changed or run for this packet.
