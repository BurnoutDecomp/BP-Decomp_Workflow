# Source45 native startup baseline independent review

**VERDICT: pass for this bounded private startup, current-profile load, world entry and relocated-driving baseline.** This is not a Replay recording/playback test or general gameplay parity. Source45 B5 `e3d773c6cc9020ddf1e5f867a7cdadf094348192`, build workflow `eae680840642ae417662a2b9408344f76e7fffcf`, staged executable SHA-256 `e0635b4d424d589409ee13b0b5c32d3850e778c8edec74dfc46eae8500f90992`; corrected reviewed manifest `9a3163f0ae068fae75928787b7b4bda7fed7af0f4dccf08090a1d8bcff608d70`. I independently hashed the staged exe and current manifest. The run owner was PID 61208, slot 62185, start 2026-10-30T19:46:55.7559897Z.

The original result has **18 case checks plus the strict terminal check, all passing**, with zero raw `[ASSERT n]` and zero `[EXCEPTION]` lines. The actual corrected capture checker was rerun read-only on the retained evidence and passed. The raw log has GameTalk owner at one-based line 160, FLApt allocation at 392, EA movie prepared 515, EA completion 588, Criterion prepared 593, Criterion completion 598, legal title stage 7 at 626, profile stage 3→4 at 834, car select 4294 and world exit streaming completion 5870. A GAMEWRECKED message appears at 13269. Decoder/event order is observed; no claim is made that every video frame or unrelated UI behavior was tested.

The single-link private profile binding records SHA-256 `d7062394d301297191063dbf1c30cddd312ad28dae4e1f0e280bbbf796d09241`. The gate's zero-based retained raw indices 892/1150/1249 match the log exactly: nonnew deserialization; same shared profile with 202 medals, 120 events, spawn car A7E60F1A40508000 and catalog 85; and loaded PUSMC02/rank 5/catalog 85. I personally saw that the profile-ready image is black apart from the green debug squares; the profile claim rests on these log lines, not that image. No live user save was read during this review.

I personally viewed all ten phase images in `source45_frames.jpg`. The table lists actual content and raw ACK line numbers (one-based); exact full frame hashes, ACK strings, owner, request cursors and every input hash are in `SOURCE45_NATIVE_REVIEW.json`.

| Label | Frame | ACK line | Visible content |
| --- | --- | ---: | --- |
| ea_movie_2s | bb_001292.bmp | 537 | EA symbol. |
| ea_movie_5s | bb_001789.bmp | 539 | Glowing circular EA franchise movie imagery. |
| criterion_movie_2s | bb_003137.bmp | 596 | Criterion wordmark and light effect. |
| title_ready | bb_004007.bmp | 641 | Burnout Paradise title and start prompt. |
| profile_ready | bb_004380.bmp | 900 | Black screen with three green debug squares. |
| car_select | bb_005629.bmp | 4725 | Carson Annihilator car-select view with an information dialog. |
| world_exit | bb_005944.bmp | 6531 | Car in the world with music HUD. |
| drive_8s | bb_006437.bmp | 9017 | Rear car view on road with HUD. |
| drive_15s | bb_006950.bmp | 11393 | Rear car view approaching a junction. |
| drive_25s | bb_008177.bmp | 14932 | Damaged car and WRECKED overlay. |

Each of ten frame hashes matches `CAPTURES.json`; each exact PID/slot/sequence/present ACK occurs once and the corrected checker verifies the fresh cursor, prior phase marker and owner joins. Criterion 5s and drive 35s captures were not taken. The labels' timing reflects the helper's measured observation, not an independently timestamped log event.

`Get-DriveSegment` rerun on the raw log yields 236.781 m path, 234.639 m net, 109 samples 41–149, teleported=true, no later respawns in the measured segment, and one wreck. This uses the disclosed supporting place-on-track setup, not an organic route. The original terminal-status file hash matches its original receipt, which reports the exact owned phase stop, input reset, process and helper cleanup, fixture restoration and exit 0. These are retained harness attestations; the actual elapsed time cannot independently prove all gameplay or future stability.

Protection receipts show 5,622 read-only asset handles held at launch and exit, private one-link profile binding, matching before/after hashes for all 15 normal runtime payloads, normal config `b3f43dfebc363955ea612d4ea13f5d60e74adcd8f539c3ec08eb5aa509a7684d`, and unchanged normal profile D706…; asset-handle and cleanup claims are receipt evidence, not independently observed live handles. The earlier prelaunch FAIL and other historical failed/zero-site runs remain unchanged and are not reclassified. No game was launched, source or registry changed, or publication performed in this review.
