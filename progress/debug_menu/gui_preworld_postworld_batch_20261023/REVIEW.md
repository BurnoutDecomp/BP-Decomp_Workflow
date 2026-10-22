# Combined independent source review: GUI F1 repair and GameState PostWorld producers

VERDICT: pass

INCREMENT 1 VERDICT: pass

INCREMENT 2 WITH METADATA OVERLAY VERDICT: pass

INCREMENT 2 ORIGINAL EXACT-PACKET VERDICT: fail

METADATA OVERLAY VERDICT: pass

COMBINED SOURCE SEMANTICS VERDICT: pass

The GUI repair resolves the sole source defect in the retained complete failed review. Fresh review of the event 43/event 10 increment found no source-code defect. Its original manifest has one inaccurate byte-count field, retained as M1 below. The separately sealed metadata overlay fixes exactly that field against the original payload root. The combined source-and-metadata verdict is **pass for those explicitly composed inputs**; the original inconsistent manifest is preserved and does not receive an independent pass.

Both source increments are bound to B5 commit `568fc5fe498ffc261cbadf35de5440c6988ec862`, tree `d39afbc60cd2850e73841bf9eddb93cf4bd2706f`, whose parent is `c1b0e7ef6a181c3cc92f45ac9481a9cbaaeb01db`. The GUI increment changes two paths, and the producer increment changes five different paths. Their patch target sets do not overlap. This review awards no active wiring, compilation or runtime credit.

## Finding M1 — P3: stale byte count in the producer manifest

Location: `replay_game_state_postworld_event_producers_delta01_20261023/MANIFEST.json:49`, `changed_source_bindings` row for `src/GameSource/Director/DirectorModule/BrnDirectorModuleIOOutputBuffer.hpp`.

The row claims `postimage_bytes: 13716`. The complete frozen postimage is **13855 bytes**. Its actual SHA-256 is `09536e086ffbdbfa5d4380d222aebd1483303a2213bd3a19c8b19c75977e3d7c`, which agrees with both the binding's postimage hash and the `payload_files` row. The latter already records the correct 13855 bytes. Thus the exact packet is internally inconsistent even though its source bytes are identifiable and unchanged.

Resolution: the separate metadata overlay described below corrects only this field and independently seals the corrected manifest. The original source packet, inaccurate manifest and original seal remain unchanged. All seven source postimage hashes remain the hashes listed below. M1 is closed only when that overlay is interpreted against CORRECTION.json's original payload_root.

## Separate metadata overlay: M1 resolved

Overlay: `replay_game_state_postworld_event_metadata_delta02_20261023`. This is a metadata-only addition to the producer packet, distinct from the GUI constructor repair and from source-payload approval.

- The overlay's `INTEGRITY.sha256` file hash is `4c3f5ed31e4118bcc786aa127c1c62c5c8ae7b116f7badf9c380872cc5220f95`; all four listed files match.
- `MANIFEST.original.json` is byte-identical to the original producer manifest, SHA-256 `eb95244c68b31b15beb565a34c757b3ce16e7269b9b1f45f5afcdecd4ddb90fd`.
- Recursive comparison of the complete original/corrected JSON objects finds exactly one differing scalar: `/changed_source_bindings/2/postimage_bytes`, from 13716 to 13855. No row, source hash, payload record, evidence, dependency, patch or other field changes.
- Corrected manifest SHA-256: `23b50e7d102565625b36b493d001675df9a7ce3709e0b0ba03471d62bfa7431b`. Every changed-source postimage byte count/hash and every payload row now verifies against the original producer directory named by `CORRECTION.json.payload_root`.
- The unchanged header's complete SHA-256 remains `09536e086ffbdbfa5d4380d222aebd1483303a2213bd3a19c8b19c75977e3d7c`. Original source-payload seal `ca96f97a1fceaea8442b64cf69fc193cef3bf66a09de10d7194db2b02de1463d` and original SEAL file are preserved. The overlay, rather than that original seal alone, authenticates the corrected metadata.
- The initial combined report and seal that recorded the original exact-packet failure are retained in this review directory as `INITIAL_EXACT_PACKET_REPORT.md`, `INITIAL_EXACT_PACKET_INTEGRITY.json`, `INITIAL_REVIEWED_INPUTS.json` and `INITIAL_EXACT_PACKET_SHA256SUMS.txt`.

| Overlay relative path | Bytes | SHA-256 |
| --- | ---: | --- |
| `CORRECTION.json` | 998 | `f1b704821e5c03cf216fc293756538d524085ee0a48bc5a9251c35f0302c460c` |
| `INTEGRITY.sha256` | 345 | `4c3f5ed31e4118bcc786aa127c1c62c5c8ae7b116f7badf9c380872cc5220f95` |
| `MANIFEST.corrected.json` | 12848 | `23b50e7d102565625b36b493d001675df9a7ce3709e0b0ba03471d62bfa7431b` |
| `MANIFEST.original.json` | 12848 | `eb95244c68b31b15beb565a34c757b3ce16e7269b9b1f45f5afcdecd4ddb90fd` |
| `REVIEW_REQUEST.md` | 783 | `2a003588693d76164b73de2ee8aa9a9f7800abf74d8120de3db7c39b491c541c` |

## Increment 1: F1 repair accepted

Packet: `replay_gui_preworld_validation_repair_delta02_20261023`.

- The exact `INTEGRITY.sha256` file hash matches the requested seal `17a6c752afe519c01522989942dbc023192099dba4e4e0a7254e5058eb120c20`; every listed file matches.
- Both 568 source preimages equal the exact previously reviewed c1 preimages. The supplied `reviewed_postimage` copies equal the original delta01 postimages.
- The complete header postimage is unchanged. The complete corrected C++ postimage equals the original reviewed C++ postimage with exactly one occurrence of `mbCollisionWorldInvalid = true;` changed to `mbCollisionWorldInvalid = false;`, at line 905. No other C++ byte differs.
- This resolves original F1: ARTIST `0x825184A8` loads `r30=0`, and `0x82518B80` stores that value to the collision-invalid member at `this+0x1FC3C`. The corrected binding now explicitly states false and acknowledges the conflicting pseudocode. Its sole changed documentation line is the constructor binding.
- The PreWorld signature, assertions and lock/call order; all 13 collision-validation states; all six car-pool states; response types 67/68; request types 7/8; pool 15; game action 13; inbound 493 values 2/3; and the one-byte 512 latch ordering are byte-identical to the already reviewed bodies.
- The unchanged dependency limits remain: dormant GameMain PreWorld helper, missing world collision completion producer, missing native output-side networking latch handler, and the separate PC profile-collision stand-in that needs reconciliation before activation.
- `RETAINED_FAIL_REVIEW.md` is byte-identical to the original complete independent FAIL report, SHA-256 `4dfb85aaf66554e361198a9aa41717224514afe9730f035951a8def4208394e4`. The original delta01 packet and original independent review remain unchanged. The old report is retained as history; the corrected postimage's source verdict is pass.

## Increment 2: full fresh semantic review accepted

Packet: `replay_game_state_postworld_event_producers_delta01_20261023`.

All 12 patch hunks across all five source paths were reviewed fresh. Applying that patch to the complete exact 568 preimages in memory reproduces all five complete postimages byte-for-byte. All five c1 preimages match their c1 Git objects, all five composition preimages match their 568 Git objects, and the four unaffected baseline paths have identical c1/568 blobs. The composition `BrnGameModule.cpp` also equals the prior reviewed prerequisite's complete proposed postimage, SHA-256 `2bd06339b1d539f03f55ca82aa296ac5b6f715bfad2ae2af99dc081a9fd0391d`.

### Event43 producer and typed Director provider

Source: postimage `BrnGameModule.cpp:1908..1954`, `BrnDirectorModuleIOOutputBuffer.hpp:92..111`, its `.cpp:80..128`, and `BrnDirectorOutputInterface.h:27..29`.

- ARTIST `DoUpdate_GameStatePostWorld`'s prologue establishes the original `this`, two IO stacks, Input/World/GUI/Replay/Director output arguments, with the `BrnUpdateSet` loaded from the caller's stack at `0x823E936C`. DecFIGS's typed `void` signature corroborates the current C++ declaration. The new code does not import Hex-Rays's spurious long parameter list or return-register residue.
- The new Director lookup occurs after the existing World bridge condition and before Replay append, matching ARTIST `0x823E938C..0x823E93E4`. The producer is outside the World bridge's `!(set&0x20)` block, so video mode suppresses the World bridge but does not invent a suppression of the director pause request.
- `lpDirectorOutputBuffer` is a pointer to const OutputBuffer in this function. It therefore selects the new **const/read** typed getter, not the write-lock overload. The existing Director read lock is acquired at source 1932 and remains held through event 43, Replay append, event 10, and camera-state sampling, until source 1984.
- The const typed getter tests `IsBufferLockedForReading()` and returns `&mDirectorOutputInterface`; the mutable overload tests `IsBufferLockedForWriting()` and returns the same member. ARTIST `0x823B3458` tests status bit 4 and returns the interface at console+0x4F0; ARTIST `0x82207848` tests bit 3 and returns the same seat. The new code uses a named C++ member so host pointer/layout widening is respected. DecFIGS exports and dwarf declarations corroborate the names, constness and pointer return shapes. Legacy byte views remain unchanged for existing callers.
- The interface accessors return the existing bool fields `mbPauseRequest` and `mbPauseRequestState`, at console+0x0E/+0x0F. Their shape/names match the DecFIGS dwarf declarations; ARTIST `0x823E9394/0x823E93B0` loads those bytes. No offset cast, alternate interface object, setter side effect or latch clearing was added.
- Only a true pause-request flag emits event 43. The payload is the pause-request-state byte, named through the existing `TrainingPauseStateChangedEvent::mbActivated`. The enum value is 43 and the one-bool event inherits an empty GameEvent base; the existing typed AddEvent overload forwards `sizeof(EventT)`, consistent with ARTIST's `li r5,43; li r6,1`. The code caches the already-read-locked interface pointer rather than invoking the identical read getter twice; it changes no successful-path side effect.

### Replay append and event 10 producer

Source: postimage `BrnGameModule.cpp:1956..1975`.

- Replay's source queue is appended after event 43 and before event 10. Its pre-existing null guard and optional read lock are preserved exactly. This packet does not create a Replay output or select its PostSim phase.
- Event10 is emitted only when `!mbIsLoadingScreenVisible && !mbDiskError` and `(lUpdateSet & 0x4)!=0` differs from the owned `mbControllerDisconnected` latch. This matches ARTIST `0x823E93F8..0x823E942C`. Computing the incoming bit in a local before the guard introduces no memory-side effect.
- The latch is updated before the queue post, matching ARTIST's member store at `0x823E9438` before AddEvent at `0x823E944C`. Both disconnect and reconnect edges are preserved; suppressed frames leave the latch unchanged and no edge event is invented.
- The existing `ControllerDisconnectedEvent::mbDisconnected` payload is exactly one bool. Its enum is 10; the frozen source has a one-byte static assertion and DecFIGS's typed AddGameEvent export at 0x345DFC corroborates `(type 10, size 1)`. ARTIST posts the same type and byte width. Typed PostWorld input access remains under the existing input write lock.
- The source continues to sample PictureParadise after both event seats, release the same locks, and retain the pre-existing video/disk gate for GameState PostWorldUpdate. No caller, monitor, IO-helper destruction, base input ownership or update-set selection was changed by these hunks.

### Owned controller latch and construction

Source: postimage `BrnGameModule.hpp:1134`, `BrnGameModule.cpp:131,676..680`.

The member is the original bool `mbControllerDisconnected`, named by the DecFIGS dwarf declaration and behaviorally identified by ARTIST's compare/store at console`gm+10094116`. Its C++ initializer supplies a defined host starting value. The explicit Construct clear is independently supported by ARTIST's zero register at `0x823C9ED4`, the offset 0x9A0624 materialization at `0x823CAA10/18`, and its store at `0x823CAA94..9C`. The accompanying loading/disk member clears also have direct ARTIST support: `r30=0` at `0x823CB0E4`, followed by stores to+0x9A062D and+0x9A0622 at `0x823CB204/208`. No invented initial true state, synthetic controller status provider or raw member-offset access is present.

### Explicit limits preserved

The exact 568 active caller still builds `lFullModuleUpdateSet` with `ConstructUpdateSetFromFsm()` and passes it unchanged to PostWorld while passing null for Replay PostSim output. The frozen 47-line source excerpt matches the exact 568 Git object. That early helper begins with 0x80/0x88 and only adds or masks 0x40,0x20,0x1,0x400,0x200; it never sets bit 0x4. Its content and the callsite are untouched by the patch. The new event 10 branch therefore receives no active-path behavior credit. The late output-derived update set, Replay phase/lifetime, GUI PreWorld selection and other incomplete frame composition remain dependencies.

## Integrity result

All individual payload hashes and byte counts in packet 2's `payload_files` table match the frozen files. All seven ARTIST/DecFIGS JSON evidence copies equal their original exports; `BrnGameEvents.h` equals the exact 568 Git blob; the active-set excerpt's47 numbered source lines match that blob's declared source owner. The composition base commit/tree/parent are correct. M1 is the one inconsistent `changed_source_bindings.postimage_bytes` value in the original manifest; the separate overlay above corrects it.

Packet2's payload digest `dd6728b23d92068380cba6863e40dd32b655c14aa2b9e456d907b074abaf2f9a` reproduces using its emitted payload-record order, which is case-insensitive path order. Its manifest hash is `eb95244c68b31b15beb565a34c757b3ce16e7269b9b1f45f5afcdecd4ddb90fd`. SHA-256 of `manifest_hash + LF + payload_digest + LF` reproduces the requested integrity seal `ca96f97a1fceaea8442b64cf69fc193cef3bf66a09de10d7194db2b02de1463d`. This validates the frozen bytes and exposes rather than repairs the stale metadata. The SEAL.sha256 file's own byte hash is separately recorded in the input manifest.

Only this new sibling review directory was written by the reviewer. No source, frozen packet, original review, Git index, ledger, commit or production file was modified. No C++ build, fixture, CI, game, native harness or IDA process was run. There is no compilation, active wiring, runtime, gameplay or complete-frame behavior approval.

## Exact complete postimage hashes

These hashes are the accepted source-semantic images for the two nonoverlapping increments; no complete working tree or commit was created.

| Increment | Source path | Complete bytes | SHA-256 |
| --- | --- | ---: | --- |
| increment_1 | `src/GameSource/Gui/BrnGuiModule.cpp` | 284816 | `1ef0d714afef53e9d478faeac33fac43f656c999885c07f21df7a007707dc2ca` |
| increment_1 | `src/GameSource/Gui/BrnGuiModule.h` | 48738 | `b2520bbe64f041d234fba1239f43058d47722b71490c5c59143bd484c477b93e` |
| increment_2 | `src/GameSource/Director/DirectorModule/BrnDirectorModuleIOOutputBuffer.cpp` | 9900 | `652cdd0468599407f526ed299546334ae88f0c23ccf2b5d2b02b7b48c98b077e` |
| increment_2 | `src/GameSource/Director/DirectorModule/BrnDirectorModuleIOOutputBuffer.hpp` | 13855 | `09536e086ffbdbfa5d4380d222aebd1483303a2213bd3a19c8b19c75977e3d7c` |
| increment_2 | `src/GameSource/Director/SharedIO/BrnDirectorOutputInterface.h` | 2253 | `336cb8cc6021a7f46bac71f14e4ae5228962fcd3fff72ce64c5723078a3ce676` |
| increment_2 | `src/GameSource/Game/BrnGameModule.cpp` | 364447 | `cdde690ad876bab5cb5f6231be631869d685166aedb876cbdca7b996a17c1d62` |
| increment_2 | `src/GameSource/Game/BrnGameModule.hpp` | 106513 | `f20b5565cf07ff9f055c60880ef951cd866bd0d4262be96cba3faa274717b7f2` |

## Sealed review inputs

`REVIEWED_INPUTS.json` records all complete source packet files, all five separately sealed metadata-overlay files, the initial combined finding/report, the original delta01 packet and full failed review, the original export copies, additional 568 queue dependencies, original DecFIGS declarations and repository guidance. Its SHA-256 is `eb9840f3d0371eedf44d80cb0567afd4577ae96ee8302acb2ccd4eb60133ccc8`. The combined original-packet-plus-metadata-overlay file digest is `bd67cd96d1f5313f9bbc39a8ccb57af139166830d2d6ae901cdf59c58caac220`, defined as SHA-256 of UTF-8 lines `increment_name/packet_relative_path + TAB + sha256 + LF` sorted by the case-sensitive `(increment_name,path)` tuple, including the separate `metadata_overlay` increment. `INTEGRITY.json` and `SHA256SUMS.txt` seal this final report and input manifest without embedding a self-referential report hash.

### Increment 1 frozen files

| Relative path | Bytes | SHA-256 |
| --- | ---: | --- |
| `BINDINGS.corrected.md` | 5488 | `6e12f24979914b6647e8824e81f3d977d9cc54bc1e765a415d10bd2d40c1f00b` |
| `DELTA_FROM_REVIEWED.diff` | 632 | `74c9687e4c3a7fb4a2eded710c96b9d217b7fc5df39722eb94664ef297cfce66` |
| `INTEGRITY.sha256` | 1115 | `17a6c752afe519c01522989942dbc023192099dba4e4e0a7254e5058eb120c20` |
| `MANIFEST.json` | 1556 | `af8076574a1d0e9171266f1eebfe4f7aa410914ee1b8e0090d62692f61920705` |
| `postimage/src/GameSource/Gui/BrnGuiModule.cpp` | 284816 | `1ef0d714afef53e9d478faeac33fac43f656c999885c07f21df7a007707dc2ca` |
| `postimage/src/GameSource/Gui/BrnGuiModule.h` | 48738 | `b2520bbe64f041d234fba1239f43058d47722b71490c5c59143bd484c477b93e` |
| `preimage/src/GameSource/Gui/BrnGuiModule.cpp` | 264447 | `f1f03be11f44cd610e5be8727a1d5112e59037e98045c20c1411d145ff0b501f` |
| `preimage/src/GameSource/Gui/BrnGuiModule.h` | 45770 | `0c0438b73be1ef61407c4c3fc72976db3b6db97680b17eb9a69594959ded6ed3` |
| `RETAINED_FAIL_REVIEW.md` | 20944 | `4dfb85aaf66554e361198a9aa41717224514afe9730f035951a8def4208394e4` |
| `REVIEW_REQUEST.md` | 868 | `8355fa90c0a4734e0e66cc1ab6c7a6abfaa28a1f5646f66763de9139d8f139b6` |
| `reviewed_postimage/src/GameSource/Gui/BrnGuiModule.cpp` | 284815 | `e1c920cbeeb2da9bb1bd197018270593fd527d06c8001f3df842ce848954ffcd` |
| `reviewed_postimage/src/GameSource/Gui/BrnGuiModule.h` | 48738 | `b2520bbe64f041d234fba1239f43058d47722b71490c5c59143bd484c477b93e` |

### Increment 2 frozen files

| Relative path | Bytes | SHA-256 |
| --- | ---: | --- |
| `DEPENDENCIES.md` | 1938 | `35dc1c754f0dcba0ee6722b90fc1593a0af870babf03e260336b545464efc0f6` |
| `evidence/artist/Construct_823C9EA8.json` | 86405 | `3f4af6d4f0208f7e7745d6da9e7ecf78aff365c6db8578dc604e4c2dddcfd898` |
| `evidence/artist/DirectorOutput_ReadGetter_823B3458.json` | 4385 | `300b42393587effe29f45239a578ae33283bcd2e518c1c797dd8fb0afb8750d5` |
| `evidence/artist/DirectorOutput_WriteGetter_82207848.json` | 4385 | `a203ec1767afd1aa1fadc2e9aa84dc5e5eb54f4a68972817789993db81687fa3` |
| `evidence/artist/DoUpdate_GameStatePostWorld_823E92A8.json` | 17407 | `88000060b731ce74c2cbdeb2bc027c9ec45501b2f33a5d06c56180f7c2282937` |
| `evidence/decfigs/ControllerDisconnectedEventAdd_345DFC.json` | 2452 | `47b6d5dbb01a75e29c5faff2036a083c82fe9679578d034b5371f2b223005daa` |
| `evidence/decfigs/DirectorOutputGetter_33E0D0.json` | 5780 | `67aaa420ace239d75f2dbceb757369e5a6cb6476e21e300c70384dc49279dcdb` |
| `evidence/decfigs/GameStatePostWorld_30E848.json` | 46356 | `a88cab75c8a1e9eaa6f8e2d02685e769e6c597b7c91476229b24f2bc55e1daad` |
| `evidence/source_shapes/active_update_set_boundary.txt` | 2954 | `8ee42f5aca6fb07bafae54c51d589a6b02a6b64a6b317cc64b390c8468a95cb1` |
| `evidence/source_types/BrnGameEvents.h` | 90421 | `ee208ff1c221593baee41448cd2db9faa96639e4bf3ad18b07bb927255f22c29` |
| `MANIFEST.json` | 12848 | `eb95244c68b31b15beb565a34c757b3ce16e7269b9b1f45f5afcdecd4ddb90fd` |
| `PATCH.diff` | 11999 | `47d9b083095bd37bedd21419b3d20e4520671469e9c8ae32eb16ed9b354b0eef` |
| `postimage/src/GameSource/Director/DirectorModule/BrnDirectorModuleIOOutputBuffer.cpp` | 9900 | `652cdd0468599407f526ed299546334ae88f0c23ccf2b5d2b02b7b48c98b077e` |
| `postimage/src/GameSource/Director/DirectorModule/BrnDirectorModuleIOOutputBuffer.hpp` | 13855 | `09536e086ffbdbfa5d4380d222aebd1483303a2213bd3a19c8b19c75977e3d7c` |
| `postimage/src/GameSource/Director/SharedIO/BrnDirectorOutputInterface.h` | 2253 | `336cb8cc6021a7f46bac71f14e4ae5228962fcd3fff72ce64c5723078a3ce676` |
| `postimage/src/GameSource/Game/BrnGameModule.cpp` | 364447 | `cdde690ad876bab5cb5f6231be631869d685166aedb876cbdca7b996a17c1d62` |
| `postimage/src/GameSource/Game/BrnGameModule.hpp` | 106513 | `f20b5565cf07ff9f055c60880ef951cd866bd0d4262be96cba3faa274717b7f2` |
| `preimage/src/GameSource/Director/DirectorModule/BrnDirectorModuleIOOutputBuffer.cpp` | 9321 | `1f0ca4433eae06e9dfb2cc56c50cece2226ee66d4a34601eb8dec811c8720ca8` |
| `preimage/src/GameSource/Director/DirectorModule/BrnDirectorModuleIOOutputBuffer.hpp` | 13296 | `f8ae10de5bcbb1c883a27e84ccb2f9ddacda3099f7edd3ae7eb4869590c8f331` |
| `preimage/src/GameSource/Director/SharedIO/BrnDirectorOutputInterface.h` | 2028 | `939dca2d92fe2db716f8a32c9808181dc8779352c789be5694664ac2229cbf66` |
| `preimage/src/GameSource/Game/BrnGameModule.cpp` | 363178 | `2bd06339b1d539f03f55ca82aa296ac5b6f715bfad2ae2af99dc081a9fd0391d` |
| `preimage/src/GameSource/Game/BrnGameModule.hpp` | 106426 | `a9ef7e82370913f60c8dd4629a85cc469c01a8613387c2626caf803e288fdc94` |
| `preimage_c1/src/GameSource/Director/DirectorModule/BrnDirectorModuleIOOutputBuffer.cpp` | 9321 | `1f0ca4433eae06e9dfb2cc56c50cece2226ee66d4a34601eb8dec811c8720ca8` |
| `preimage_c1/src/GameSource/Director/DirectorModule/BrnDirectorModuleIOOutputBuffer.hpp` | 13296 | `f8ae10de5bcbb1c883a27e84ccb2f9ddacda3099f7edd3ae7eb4869590c8f331` |
| `preimage_c1/src/GameSource/Director/SharedIO/BrnDirectorOutputInterface.h` | 2028 | `939dca2d92fe2db716f8a32c9808181dc8779352c789be5694664ac2229cbf66` |
| `preimage_c1/src/GameSource/Game/BrnGameModule.cpp` | 362652 | `4b0d29208323919933f7638cc82734b378df6f798d5eae83efefc7adb15a1d6b` |
| `preimage_c1/src/GameSource/Game/BrnGameModule.hpp` | 106426 | `a9ef7e82370913f60c8dd4629a85cc469c01a8613387c2626caf803e288fdc94` |
| `REVIEW_REQUEST.md` | 1443 | `c8c120732faf480db5591ae73a6e8280b0b30c91227eee8d06a6af4e84571bc2` |
| `SEAL.sha256` | 258 | `555765c83a64a0d1444ba01eb3a889906dc065d2df0dd541be5e6326d37c684b` |
| `SOURCE_POSTMORTEM.md` | 1940 | `60f7b7e68fa3122b9d5244dcf67eddd1aa078bdb8845e7e81a7898eb2eab90a8` |
