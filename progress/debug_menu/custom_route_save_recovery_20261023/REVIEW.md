# Independent route save/load source review

VERDICT: pass

The two exact postimages support the requested recovery against ARTIST assembly and DecFIGS declaration shape. This is a source verdict for removing the two transfer traps, restoring saved-table construction/count resets, and defining the three saved-event getters. Compile, actual-body fixtures and native save/overwrite/reload remain pending. No behavior or completion claim is made, and this verdict does not depend on the parallel fixture work.

Reviewed packet: `route_save_transfer_recovery_20261023`; manifest SHA-256 `a7565ec6029412e4dc8f59adad101e60fe5890e3f7f6dc68f021ef57c137d709`. All 29 entries match. The complete cpp/h preimages match their base Git blob IDs; all six diff hunks reproduce the exact complete postimages in memory. I read the full postimages, all ten supplied original assembly listings, the DecFIGS shape, and the relevant captured cache/type/caller definitions. POSTMORTEM was treated as the author's self-check, not as proof.

## Transfer contract

Both original transfer prologues pin `this`, cache and parameters to `r3/r4/r5`; DecFIGS confirms the pointer and const signatures. Live event stride is `0x2C` (44), saved event stride `0x90` (144). The postimages use those existing named record types without layout or format-version changes.

`SetFromGameParams` follows ARTIST `82507448..82507568`: its signed round bound is the live `miNumRounds`, and its signed landmark bound is each live event's current count. Each live GetLandmark returns a two-byte LandmarkIndex; the assembly loads it with `lhz` and calls the cache with `this/index/out` in `r3/r4/r5`. The captured cache declaration accepts that actual wrapper type. The postimage copies `SatNavIconInfo::GetCgsId()` whole, matching the original eight-byte load/store from info `+0x10`; there is no 32-bit identity truncation.

After the landmark loop, the original snapshots the count before the event-start lookup, then reads event ID after that lookup. The postimage preserves this order. It passes the live light-trigger ID to `GetPresetEventDisplayInfo`; original `824F8838` matches the table's `+0x10` word. It takes the returned junction word at `+0x14`, then calls saved Event::Construct with `eventID, junctionID, landmark IDs, count` in the original order.

`SetToGameParams` follows ARTIST `82507570..8250768C`: the round bound comes from the saved count, the landmark bound from each saved event. Saved GetLandmark returns its full eight-byte ID in one GPR, passed as cache `r4`, with the output pointer in `r5`. The original reads output halfword `+0x20` and stores two-byte landmark indices. The postimage's signed halfword accessor and LandmarkIndex constructor preserve those same 16 bits, including high-bit indices; it does not substitute an ID fragment or a 32-bit index array. It snapshots the count before `GetEventStartInfoFromJunctionID`, which original `824F8988` matches against `+0x14`, then supplies returned light-trigger `+0x10` to the existing live Event::Construct.

No round clamp, count normalization, fallback identity or new null guard has been invented. Both directions skip negative/zero loop counts as the signed original comparisons do, and retain the original count-based bounds. They construct only the visited event records and only copy the active landmark prefix. Other event slots, unused landmark bytes and record padding remain untouched by these transfer bodies.

The ten tail transfers match the original scalar store set **and order** in both directions:

| Order | Field | Live offset | Saved offset | Width |
|---:|---|---:|---:|---:|
| 1 | game mode | `1B8` | `5A0` | 4 |
| 2 | rounds | `1D0` | `5B0` | 4 |
| 3 | vehicle class | `1D4` | `5B4` | 4 |
| 4 | runner crashes | `1D8` | `5B8` | 4 |
| 5 | boost type | `1C4` | `5A4` | 4 |
| 6 | vehicle choice | `1C8` | `5A8` | 4 |
| 7 | infinite boost | `1DC` | `5BC` | 1 |
| 8 | traffic | `1DD` | `5BD` | 1 |
| 9 | traffic checking | `1DE` | `5BE` | 1 |
| 10 | time limit | `1CC` | `5AC` | 4 |

The live record's previous mode (`1BC`), security (`1C0`) and ranked byte (`1DF`) are outside that saved format and are not written on load. Named enum casts preserve the existing four-byte value fields; saved-event getter return widths and constness match DecFIGS. The new getters expose event ID `+88`, junction `+80` and count `+84`, precisely the original inlined loads.

## Construction and integration

ARTIST `824FF7AC..824FF868` initializes ten events in each of ten created and ten received routes. Every event receives only event ID, junction and count zero stores, in that order. The new route Construct invokes the existing saved-event Construct with `(0,0,nullptr,0)`: its zero count avoids any landmark read/write, matching the inlined original and preserving all 128 landmark-array bytes per event. No whole-record memset is added.

Each route's original defaults are mode 10, rounds 1, class 9, runner crashes 3, boost/vehicle choice/time zero, and all three booleans true. The postimage writes those defaults in original order. The containing Construct initializes both tables, clears counts at profile `7308/730C`, then performs the existing tail flag writes; moving the default-camera assignment after the flags follows original `824FF888`. Created base `8`, received base `3988`, route stride `5C0`, saved-event stride `90`, and the existing persistent layout pins remain unchanged. DecFIGS confirms the declared helper and nested field shapes; ARTIST decides the physical offsets.

The recovered bodies are reached by the existing code. Original `SetCreatedOnlineGameOptions` at `82482630..82482664` selects `this + 8 + index*5C0`, calls SetFromGameParams with the same cache/params, then increments the created count only when appending. The unchanged postimage accessor does the same; overwrite retains its count. AddReceived still shifts nine route records and saves into slot zero, with its capped count. The existing created/received getters forward to SetToGameParams.

The captured OnlineGameOptionsSummary source and original `824A8C58`/`8249DB78` show both new-slot selection and confirmed overwrite reaching SetCreatedOnlineGameOptions, followed by the autosave request. Save-menu previews reach GetCreatedOnlineGameOptions. This establishes real caller integration at source level; it does not demonstrate a native round trip or certify other dependencies. In particular, existing cache lookups retain their own trigger-data/miss behavior; that behavior was not changed here.

## Crash evidence and limits

Both supplied attachment hashes match the packet bindings. The emergency log reports exception `0x80000003` at module RVA `63D5A0`, names SetCreatedOnlineGameOptions `+A0`, and shows HandleControllerInputSaveOptions in the call chain. The two preimage transfer bodies explicitly execute `__debugbreak()`, consistent with that reported route. The packet's installed-image instruction attribution is not a separately supplied image-byte capture; this review does not turn it into an independently verified executable or exact other-PC commit claim. The attached logs do not identify that PC's exact source commit.

Only this new sibling review was written. No C++, fixture, build, CI, native/game, harness or IDA execution occurred; no source, Git/index/refs or original evidence was modified; no subagent was spawned. The separate hosted fixture proposal/results require their own review and do not delay this supported source verdict.

Exact reviewed postimages:

- `BrnGuiOptionsDataProfile.cpp`: `24e5c47cdbcf3018ab669a71df5bbafe324adccc4abe5d4b64b32255edcf9e80`
- `BrnGuiOptionsDataProfile.h`: `51553ee0e1d4a7a8214c93b7be91c58852441ae3c310e355c6de88f7bd2bc1ce`

`REVIEWED_INPUTS.json` records all reviewed hashes, base blob checks and complete diff reconstruction. `INTEGRITY.sha256` and its sidecar seal this source review.
