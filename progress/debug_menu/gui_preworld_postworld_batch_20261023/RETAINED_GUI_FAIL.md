# Independent GUI PreWorld and validation batch review

VERDICT: fail

The entire two-file proposal has one blocking source defect: `Construct` initializes `mbCollisionWorldInvalid` to `true`, whereas ARTIST's assembly stores zero. The three recovered function bodies and the inbound 493/512 arms have no other identified semantic defect in this review. This verdict covers the exact frozen postimages listed below, against base B5 commit `c1b0e7ef6a181c3cc92f45ac9481a9cbaaeb01db` (parent `20c1d8723951d70a349604c8a7a2ceec7cb28569`). It is a source review of one batch, not approval of active frame integration.

## Blocking finding F1 — P2: initialize the collision-invalid latch to false

Location: `postimage/src/GameSource/Gui/BrnGuiModule.cpp:905` in the reviewed packet.

The added statement is `mbCollisionWorldInvalid = true;`. The attached ARTIST `GuiModule::Construct` export at `0x82518028` contains this register/value chain:

```text
0x82518044  mr        r31, r3             ; GuiModule this
0x825184A8  li        r30, 0
0x82518B64  ori       r10, r10, 0xFC3C    ; r10 = 0x1FC3C = 130108
0x82518B80  stbx      r30, r31, r10       ; mbCollisionWorldInvalid = 0
```

There is no intervening assignment of a different value to the nonvolatile `r30` before this store. The same byte is tested as `!mbCollisionWorldInvalid` in `UpdateCollisionWorldValidation` at `0x82519704..0x82519738` and set/cleared by input event 493 at `0x825290C0..0x825290F4`. This pins the member's identity independently of the constructor pseudocode.

The attached constructor pseudocode says `*(a1 + 130108) = 1;`; that is a decompiler discrepancy. Under AGENTS.md's source ladder, the assembly decides. The packet's `BINDINGS.md` assertion that Construct owns an "invalid=true seed" repeats the wrong value and must be corrected with the source.

A source-level counterexample is a module leaving Construct and disabling boot movie mode before receiving a collision completion: its first movie/network invalidate reaches the restored `!mbCollisionWorldInvalid` assertion with the wrong value; if assertion continuation is permitted, states 7 or 10 can then accept the stale true latch as an invalidate completion. This counterexample is derived from the source and assembly and was not executed.

Required correction: initialize this latch to `false`, retain the ARTIST-attested state/latch/queue initialization, and update the explanatory binding. Do not add a Construct store for `mbTrafficPoolEmptied`: ARTIST does not contain one. No source correction was made by this review.

## Complete batch coverage

All 11 hunks of the 522-line patch were inspected. The full preimage and postimage byte streams were read and the patch was applied to them in memory, reproducing both postimages exactly. The semantic review covers every changed declaration, Construct insertion, PreWorld call and lock, collision/car-pool switch arm, and inbound event arm. Unchanged owners were inspected as dependencies; this is not a blanket correctness endorsement of all unrelated existing GUI code.

### Declarations, Construct and PreWorld

- `BrnGuiModule.h:158..161,335..336`: the virtual override has two IO-stack pointers, GUI output, and ModelIO output, with `void` return. ARTIST's prologue saves `r3=this`, `r4=input stack`, `r5=output stack`, `r6=GUI output`, `r7=model output`; both validator callees take only `this` and GUI output. DecFIGS's virtual/method declarations and the frozen shared base agree. Hex-Rays's return-register residue and spurious extra car-validator arguments were not imported.
- `BrnGuiModule.h:400..455,606..608`: all 13 collision states, all six car-pool states, the state/latch names and types, and the historically misspelled `mCollisonPoolValidationReceiverQueue` match the declaration evidence. These are named host C++ members, not raw console-offset accessors.
- `BrnGuiModule.cpp:904..908,934..939`: both state enums start IDLE; networking request latches are cleared; receiver construction order is event receiver, collision receiver, then GameData receiver. `GuiAccessPointers::GuiEventReceiverQueue` is the existing `EventReceiverQueue<1024,16>`, whose Construct uses its own inline backing and Clear. The wrong invalid-latch value is F1. No traffic-latch constructor store was added.
- `BrnGuiModule.cpp:1889..1910`: monitor start, four assertions in GUI/model/input-stack/output-stack order, one GUI write-lock interval for collision validator -> car validator -> the actual `ProfileHost` manager's `LoadProfileUpgradeData(...,&mEventReceiverQueue)`, unlock, existing movie-resource publisher, shared GUI base PreWorld, monitor stop. This matches ARTIST `0x8251A3D0`.
- Existing movie publication remains a separate lock interval, conditional on the full 64-bit pending resource ID, and publishes event type 4, event id `0x1AFFEED`, pool 11, with the manager's receiver queue. `ID::GetHash()` returns the full `u64`, so the helper's zero check is consistent with ARTIST's `cmpldi`. The base PreWorld receives all four original arguments after the GUI lock is released; the frozen shared base owns its own model/output locks and bridging.

### Collision validator — all states

The table refers to `BrnGuiModule.cpp:1914..2121` and ARTIST `0x82519578`. Every pending-call side effect is retained outside the assertion expressions, including clearing network latches even when assertions are compiled out. State branches wait in place when their guard is false.

| State / source line | Checked transition and side effects |
| --- | --- |
| 0 / 1970 | Always consume movie invalidation and networking-invalidate latch; consume profile invalidation only in boot mode. Boot movie/profile requests print memory, Clear the collision receiver, emit typed swap-out 67 with event id 0 and that receiver, then select 1/4 with movie priority. Outside boot, assert initially valid and exactly one movie/network request, emit output 493 value 0, then select 7/10. |
| 1 / 1999 | Consume-and-assert no network invalidate; wait for response, assert singleton/type 67, transfer the collision resource pointer and descriptor size through `MovieManager::FreeCollisionPoolMemory`, print memory, set invalid=true, movie collision invalid, state 2. No added response Clear. |
| 2 / 2011 | Consume-and-assert no network invalidate; assert invalid; movie validate handshake emits typed swap-in 68 with event id 0 and collision receiver, then Clear, then state 3. |
| 3 / 2021 | Consume-and-assert no network invalidate; singleton/type 68 reply, two original memory prints, invalid=false, movie valid, state 0. |
| 4 / 2033 | Consume-and-assert no movie invalidate, then no network invalidate; singleton/type 67 reply, one memory print, invalid=true, actual ProfileHost manager invalid, state 5. No invented transfer to the movie owner. |
| 5 / 2045 | Same movie/network pending checks, assert invalid; ProfileHost validate handshake emits 68, then Clear, state 6. |
| 6 / 2056 | Same movie/network pending checks; singleton/type 68 reply, one memory print, invalid=false, ProfileHost manager valid, state 0. |
| 7 / 2068 | Consume-and-assert no profile invalidate, then no network invalidate; only an invalid latch completes movie invalidation and moves to 8. |
| 8 / 2077 | Same pending checks, assert invalid; movie validate handshake emits output 493 value 1, state 9. |
| 9 / 2087 | Same pending checks; only a cleared invalid latch makes movie collision valid and returns to 0. |
| 10 / 2096 | Consume-and-assert no profile invalidate, then no movie invalidate; only invalid latch advances to 11. |
| 11 / 2102 | Same profile/movie checks; consume-and-clear networking-validate latch, emit output 493 value 1, state 12. |
| 12 / 2111 | Same profile/movie checks; only a cleared invalid latch returns to 0. |
| default / 2117 | Retains the original `Unhandled state` assertion. |

`ReadResponse` preserves the response-type assertions and singleton requirement. Its common helper reads the already nonempty queue before checking its length; in states 3/6 ARTIST emits the length assertion before reading the type. The read is const and carries no queue mutation; no changed successful-path side effect was found. No source defect is assigned for this local factoring.

### Car-pool validator — all states

The table refers to `BrnGuiModule.cpp:2125..2231` and ARTIST `0x82514228`. Both pool id and per-request event id are 15. In-process records use the existing native-width owning types and typed AddEvent overload.

| State / source line | Checked transition and side effects |
| --- | --- |
| 0 / 2129 | Consume movie car invalidation; boot sets the traffic-empty latch true; nonboot emits game action 13 with exactly one true byte, clears the latch, then wait state 1. |
| 1 / 2144 | Wait for traffic-empty; emit resource-request type 7, receiver `mEventReceiverQueue`, both ids 15; state 2. |
| 2 / 2155 | Wait for reply; assert singleton/type 7/per-event id 15; Clear the queue while retaining payload storage. Any non-success, including IN_USE, retries at state 1. Success passes `false` and all three resource/descriptor lanes to `SetCarPoolValid`, state 3. |
| 3 / 2176 | Consume movie car validation; emit type 8 with same receiver/ids; state 4. |
| 4 / 2187 | Wait for singleton/type 8/per-event id 15 reply; Clear. Boot clears traffic-empty; nonboot posts game action 13 with exactly one false byte, then asserts the old latch is true. State 5 is immediately evaluated in this call via fallthrough. No invented result test or completion. |
| 5 / 2212 | Wait until traffic-empty is false; set all three resource pointers to null and all descriptor lanes to size 0/alignment 1, pass `true` and those values to `SetCarPoolValid`, state 0. |
| default / 2227 | Retains the original `Unhandled state` assertion. |

The existing `BaseEventReceiverQueue::Clear` changes only count/cursors, so reading a response's resource, descriptor and result after Clear matches the original lifetime/byte-storage behavior. The boot-only immediate 4->5->0 fallthrough is retained. The constructor does not preinitialize the traffic latch; state 0 remains its request-side writer as in ARTIST.

### Inbound event arms

- `BrnGuiModule.cpp:2558..2568`, ARTIST `0x825290C0..0x825290F8`: input 493 reads a four-byte enum payload; value 2 sets invalid=true and value 3 clears it. Values 0/1 do not change this inbound latch. These completion values are distinct from validator output requests 0/1.
- `BrnGuiModule.cpp:2571..2586`, ARTIST `0x825290FC..0x82529168`: event 512 reads the one-byte `GuiEventTrafficPoolEmptied` payload, asserts the opposite previous latch before setting true, and asserts the previous true latch before clearing false. The existing dispatch read lock and subsequent subscribed-flow fan-out remain in place.

## Remaining source dependencies — separate from F1

These boundaries are present in the c1 source and are correctly disclosed by the packet. They do not excuse F1, and they do not create additional defects in the bounded function recovery.

1. **No selected GUI PreWorld phase.** `BrnGameModule.cpp:5230..5248` contains the recovered `DoUpdate_GuiPreWorld` helper and calls the GUI virtual inside it. A c1 source-tree search finds its declaration and definition, but no active call to the helper. This proposal does not modify GameMain. Restoring an override is a prerequisite; it does not prove any native frame work executes.
2. **World completion producer still absent.** `GameBridgeWorldToGui.cpp:744..755` still defers the collision-world completion tail. Its existing traffic bridge at `896..902` forwards event 512, but that is not a producer for input collision event 493 values 2/3. Movie/network collision states waiting for those acknowledgements must not receive completion credit.
3. **Output-side networking request handler still absent.** ARTIST `HandleEventsPostBaseModuleUpdate` at `0x82507800` walks GUI output event 493 values 0/1, asserts state 0/11 and sets the networking invalidate/validate latches. The current selected GUI implementation has a partial PC flow-output stand-in but lacks that collision arm and the original typed handler invocation. The restored validators correctly consume the named latches; this packet does not restore their producer.
4. **PC profile-collision stand-in still consumes pending requests.** The frozen preimage at `BrnGuiModule.cpp:3463..3471` (postimage `3850..3858`) directly consumes pending profile invalidate/validate and marks the manager complete. It must be reconciled before selecting native PreWorld to avoid competing request consumers. This existing stand-in is outside the proposed recovery, not proof of real pool reclamation.

No compilation, fixture, CI, native game, harness or IDA process was executed. No source, production file, Git index, ledger or commit was changed. Only this new sibling review directory was written. There is no compilation, runtime, gameplay, pool-memory or complete-frame-behavior credit.

## Integrity and provenance

- All 29 frozen packet files matched the packet manifest, including byte counts, line-ending counts and final-newline flags. The packet manifest's own SHA-256 is `a30a15adf8f76dfe3d589501cc3706febcae235ded01a5d7cd8029fb7d4704d6`.
- All 13 source preimages match their exact c1 Git objects. The patch reconstructs the two complete postimages byte-for-byte in memory; no checkout/source file was patched.
- All six attached ARTIST JSON files are byte-identical to the corresponding original `.ida-exports/BURNOUT_X360_ARTIST.XEX/` exports. All excerpted DecFIGS declarations were compared with the original dwarf-dump file. Exact-c1 contract excerpt lines were checked against the original Git objects.
- The existing graph was used only as a read-only navigation aid. It supplied no verdict evidence and was not regenerated or written.
- `REVIEWED_INPUTS.json` records every frozen file plus the additional pinned c1 dependencies, original ARTIST exports, DecFIGS file and repository guidance used here. Its SHA-256 is `1813ae82db9236287bca78bb81678b83766d022019e532290dcaec1fa2e9d114`.
- Frozen packet tree digest: `cac38dc2aa26d912061b13669c8ebdc4998729398095d3316fc7e8e62581bcc5`. Definition: SHA-256 of UTF-8 records `sha256 + two spaces + packet-relative-path + LF`, sorted by packet-relative-path, for every frozen file including MANIFEST.json.
- `INTEGRITY.json` and `SHA256SUMS.txt` seal the final report and reviewed-input manifest. This report does not embed its own hash.

### Complete frozen source/evidence hashes

All paths below are relative to the reviewed packet. SHA-256 hashes cover complete files, not excerpts.

| Path | Bytes | SHA-256 |
| --- | ---: | --- |
| `BINDINGS.md` | 5426 | `14d1008705b43c936d4005d2d2ddc0181ca2a9a3970ef959b1791e9a7e34938f` |
| `MANIFEST.json` | 9225 | `a30a15adf8f76dfe3d589501cc3706febcae235ded01a5d7cd8029fb7d4704d6` |
| `MANIFEST.preimage.json` | 4056 | `9666e08872377c89be0b32bed8d03fed3a079a8d3b5476f2e7e4aa76f5c0c773` |
| `PATCH.diff` | 28576 | `dfbc17c2c852facde998052a49642c437d49068360de33a82194600fd1309d77` |
| `REPORT.md` | 2615 | `3ce544155307b48a41a6f0dc51a55085404e6421bbb663c3c50cf0db0f77acb9` |
| `REVIEW_REQUEST.md` | 1469 | `34da18adb92527762afec3cc5ad12568a9348ea444e6ab04cec9783365798eb7` |
| `evidence/artist/0x82507800.json` | 10429 | `b5389250c99db447bd926b511c707965f08d1a72de5d720d4fd449d49644c4a3` |
| `evidence/artist/0x82514228.json` | 23439 | `024e9e9a7450e677d7908a94fb3c062674d847352d63e3a55040cd5946d3e934` |
| `evidence/artist/0x82518028.json` | 65673 | `56172f53827407f695132a0fefaee59a31b96618c9c51574b230ed03358afd41` |
| `evidence/artist/0x82519578.json` | 65696 | `7f07d8b819fcca97ff3269e16c0d0d98b0031ad42b816dca904f7acdce41a422` |
| `evidence/artist/0x8251A3D0.json` | 9996 | `5891bebcddcfd2a789b99ee3223bc6615788755959f5ec03d08243eb5b29d8f4` |
| `evidence/artist/0x82527A58.json` | 184859 | `e6dd401b6e921876d669f7ba8fb5931eafea44bdff4945ed20f7d4720b9b8faa` |
| `evidence/c1_source_contracts.md` | 33115 | `9dff1432bc50ea6318ac9ccedc3b6691c3714b9919cdb6851c1726cb62d9bb8b` |
| `evidence/decfigs_gui_validation_shape.txt` | 3696 | `3a06d0576e3464b10d514777e97e38f2479456285fd3d4c0a99d60e1a14350e3` |
| `postimage/src/GameSource/Gui/BrnGuiModule.cpp` | 284815 | `e1c920cbeeb2da9bb1bd197018270593fd527d06c8001f3df842ce848954ffcd` |
| `postimage/src/GameSource/Gui/BrnGuiModule.h` | 48738 | `b2520bbe64f041d234fba1239f43058d47722b71490c5c59143bd484c477b93e` |
| `preimage/src/GameShared/GameClasses/Gui/CgsGuiModule.cpp` | 9766 | `8efa6b2ad1fa0b89f061c9119ea913137e31224cad50cff15ded55dfb2150ffa` |
| `preimage/src/GameShared/GameClasses/Gui/CgsGuiModule.h` | 8487 | `5cc9999f6dd929b898c86e608ce7ec288c415be652d81b5714dbf96876b7b626` |
| `preimage/src/GameShared/GameClasses/Gui/Model/CgsModelModule.cpp` | 12518 | `37df9bd0bd83a03c8dfe31d8de185515590f12593894cd54ebc4aac6e802dcf6` |
| `preimage/src/GameShared/GameClasses/Gui/Model/CgsModelModule.h` | 3824 | `67a30b99bf127fa64e946d36810709373a721b5405f08d1e28c3cf20db4f3f6e` |
| `preimage/src/GameShared/GameClasses/Gui/Model/CgsModelModuleIO.h` | 9721 | `b8985d03f6f8a27fb2c860f9b33f064ed0a1bbb94cd7efc6cd9f0b4bc3b95ac4` |
| `preimage/src/GameShared/GameClasses/Gui/Model/CgsModelModuleIO_OutputBuffer.cpp` | 7526 | `c2377d0b4d526c2e712961ad8c1ec74802b94ddb44f8fc24ab0aed73d734567a` |
| `preimage/src/GameSource/Gui/BrnGuiEventTypeDefs.h` | 189219 | `5ce6c86484e7ff07793d4690d0fabd16d3e143ae431ff0048502f0633b315a7e` |
| `preimage/src/GameSource/Gui/BrnGuiModule.cpp` | 264447 | `f1f03be11f44cd610e5be8727a1d5112e59037e98045c20c1411d145ff0b501f` |
| `preimage/src/GameSource/Gui/BrnGuiModule.h` | 45770 | `0c0438b73be1ef61407c4c3fc72976db3b6db97680b17eb9a69594959ded6ed3` |
| `preimage/src/GameSource/Gui/BrnGuiMovieManager.cpp` | 46902 | `167153e8e30c9be6a8d9eca6a00a8ba34e677c4eccef76e9293db0c9102d323a` |
| `preimage/src/GameSource/Gui/BrnGuiMovieManager.h` | 16907 | `a68995d69739e72546476af2c417f449cc10c52ee1650471f13b81074b8be40d` |
| `preimage/src/GameSource/Gui/BrnGuiProfile.cpp` | 81406 | `2d13e72716efa4d57cdf7b179d616a94d3f7d9ff702d7ef09801223dc11d0e55` |
| `preimage/src/GameSource/Gui/BrnGuiProfile.h` | 26770 | `4ac5fc13ac90115ced5c01518a953c9eff43ca9aa41da2d2c3cf21a16b4bcffd` |

### Additional c1 source dependencies

The following full-file hashes are for local Git object reads at the exact base commit, not possibly changing working-tree files. The source-contract report and targeted declaration/owner reads establish the scope of inspection.

| Git path | Bytes | SHA-256 |
| --- | ---: | --- |
| `src/GameShared/GameClasses/Gui/CgsGuiModuleIO.h` | 12342 | `3b6c468fd88bdf43e8b76c8594f42923a071992eb1e8cc63c1b05b96566fee57` |
| `src/GameShared/GameClasses/Gui/CgsGuiShared.h` | 4936 | `f52b8be59ac8a84ab17d8e4d5c372b78012a8e6328fb90e6eda270e7b28d78a8` |
| `src/GameShared/GameClasses/Module/CgsBaseEventReceiverQueue.cpp` | 3379 | `e504a7a89dd8f14af90c25f41f1637f6ff4c55ee0ef9930eb2c0c153f1f1ffd7` |
| `src/GameShared/GameClasses/Module/CgsBaseEventReceiverQueue.h` | 3423 | `830b43174ec48b743d6ed7f86140b37b6c0ac91e2189ac5edab89d971c341acf` |
| `src/GameShared/GameClasses/Module/CgsVariableEventQueue.h` | 39881 | `3c4da2211eddabcd7c31d97bc7a6a69e6c2a3222598fa0618bca428694d04e60` |
| `src/GameShared/GameClasses/System/Resource/CgsResourceID.h` | 2033 | `077aeec9d66a58478f0c2d901169d6ec3ce476bbf507ca93c6a694c49efc169a` |
| `src/GameShared/GameClasses/System/Resource/CgsResourceIOEvents.h` | 24902 | `7ebcc245c929506838b3c32a7efc4f022b36e3349f25147445a219c2860b4461` |
| `src/GameSource/Game/BrnGameModule.cpp` | 362652 | `4b0d29208323919933f7638cc82734b378df6f798d5eae83efefc7adb15a1d6b` |
| `src/GameSource/Game/GameBridgeGUIToX_wBT_01.cpp` | 5835 | `db412e330abe02bac6cc58eda7b8cb5a264fe9a0b9bb34ea0936737bf867a9a9` |
| `src/GameSource/Game/GameBridgeWorldToGui.cpp` | 62196 | `d7b5c3a1f9d9029f341c6d9c5b75fdb301d995e825380d0444ffdd3f158ac342` |
| `src/GameSource/Gui/BrnGuiDemangledEventTypes.h` | 98124 | `2908bf4f6d55bdaf95bfec0b12d02021b982c9ae795d4261a3a12a15e8afe4ae` |
| `src/GameSource/Gui/BrnGuiPerfmons.h` | 3321 | `f9950403f98a5c4b73a75ce2928ae06cce78c199d8ea2685abbf137bf7a8b534` |
| `src/GameSource/Gui/BrnGuiProfileHost.h` | 899 | `afaa7079956a1d7d7e57b1f0409943b0b8a83ca1adb4c9e72c74ce2ad1300973` |
| `src/GameSource/Resource/BrnResourceAllocator.h` | 10015 | `2fed58be46518a67805851974e617d84ee385e3799d17891b8582a52fe49455b` |
| `src/GameSource/Resource/SharedIO/BrnGameDataEvents.h` | 14764 | `a200ed1801ba6d0b9b1c4eeb50de136107ffa3ac0915cccbc6a463a9c01ab56b` |

Original DecFIGS shape file: `references/DecFIGS/dwarfdump/GameSource/Gui/BrnGuiModule.h`, 24,377 bytes, SHA-256 `cf3cf65a44ac135fa961481d5f1a3edefb61b619af0e46916e712ccf09272809`. Original ARTIST full-file hashes equal the six packet ARTIST rows above and are separately recorded with their absolute paths in `REVIEWED_INPUTS.json`.
