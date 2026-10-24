# Fresh source review: original GUI Prepare and Sku getter

VERDICT: pass

CANONICAL_SOURCE_VERDICT: pass

SOURCE_COMPOSITION_VERDICT: pass

NATIVE_ACTIVATION: not_approved

This verdict covers the three source postimages in the immutable `gui_original_entry_lifecycle_36ae_20261024` packet. The complete three-argument Prepare, its virtual declaration, and the missing genuine Sku getter pass this bounded source review. No source defect was found in those insertions. The packet's description of the pending Update has an ABI documentation error, retained and corrected below. This is an unactivated checkpoint; compilation, linking, lifecycle integration and runtime readiness have not been established.

## Exact binding and preservation

| Input | Identity |
| --- | --- |
| Base source | `36ae3ffed6e8fb3ea89ca91947647aa9465c8658` |
| Shipping workflow | `1c7766f9da14ef677bac273e16921196ea58f9fc` |
| Private comparison only | `43ff84778bf12a6bf5883b3416bacfd4370d2486` |
| Author seal SHA256 | `1bd837d613dc24e6fed9d51fd14d88a4e3de3e6ce16f3c37c221850cdc04674f` |
| Author manifest SHA256 | `5d042d8b6f87fed8f9716dd7b6d8b89faa192df12ace7cc0a381065a2d4e8042` |
| Author bindings SHA256 | `1f9566039974ed67524b1df2838017acd98fdb820e2d807ae3ff9989703c7778` |
| Proposal patch SHA256 | `b91de204b744bfc680d5b6780e6a642a865c376f8c1e4ef31d8df80cf80e5a44` |
| Hypothetical composed tree | `8ebf0e7263b87c97f8d47c515ec32bcd0ef83fb1` |

The tree identity was calculated by hashing Git tree bytes in reviewer memory, replacing only the three specified blobs. No Git object, index, ref or checkout was written. [BINDINGS.json](BINDINGS.json) binds all 342 captured inputs, the exact source/workflow object bytes, before/after blobs and the arithmetic used for preservation.

| Source path | Postimage Git blob | Postimage SHA256 | Inserted bytes |
| --- | --- | --- | ---: |
| `src/GameSource/Gui/BrnGuiModule.cpp` | `73c35ab80e93fb94ae98fcb177109b60f38ae123` | `654c9880c4be21a8cc977e3644c490c20bcdefca6c6bfee355daa0dc6455da72` | 6873 |
| `src/GameSource/Gui/BrnGuiModule.h` | `30ee2daa02e6bea442c737fe925fbb6bfb413e2a` | `2f2256b8a6879610199df6d7d51741838a8ae2df4c56e13645d51249325abc1f` | 457 |
| `src/GameShared/GameClasses/Language/CgsSku.cpp` | `501237eab73c997704e8b55b357715f31875d40c` | `8b713a28113b25e16ca96ba59d80e48cc80e28f75bd101801a3e4b72348eddef` | 242 |

Each postimage is a single insertion into its exact36ae preimage. Removing the insertion restores every original byte, including old constructors, no-argument Prepare, zero/two-argument Update, helpers, fields and includes. No caller, shipping mount, asset layout, build setting, global readiness flag or existing native allocation changed. The private43ff bytes are independently bound comparison evidence, not substituted source.

## Primary ABI and stage audit

ARTIST Prepare `82518D68` separates `this` in r3, GUI output in r4, GameData input in r5, and GameData output in r6. The prologue saves these at `82518D74/78/7C/84`. The output is locked/published/unlocked through r26 at `82518E74..94`; the saved input reaches MovieManager at `825191D8` and WorldDataController at `8251944C`; output r23 supplies allocator-list access and MovieManager's r5. Loading caller `823EF348/34C/354/358/360` independently passes these three explicit arguments and dispatches the original virtual slot. The older DecFIGS two-argument Prepare declaration does not override that target evidence.

The public virtual declaration at postimage `BrnGuiModule.h:322` matches the three-argument definition at `BrnGuiModule.cpp:1284`. It is a distinct overload, with no incorrect `override`. Its virtual status is supported by the actual indirect caller and DecFIGS's virtual declaration. There is no new original Update declaration. No host vtable offset correspondence is certified by this review.

| Stage | ARTIST span | Reviewed behavior and release store |
| ---: | --- | --- |
| 0 | `82518E54..94` | Real Tool.GUI handler; lock caller output, copy serialiser event595, unlock. No release store. |
| 1 | `82518E9C..82519024` | Release1; original pool/config/allocator helper, including continuing invalid-list diagnostic and both alignment16 calls. |
| 2 | `82519028..48` | Release2; full shared Prepare; retry false. |
| 3 | `8251904C..98` | Release3; HUD Prepare with actual manager pointer; analyzer access adoption only after success. |
| 4 | `825190A0..E8` | Release4; SCREEN Prepare with manager reference; streaming CURRENT after success. |
| 5 | `825190EC..82519124` | Release5; OVERLAY Prepare and retry. |
| 6 | `82519128..78` | Release6; existing FSM provider adopts the real Model and FSM heap, matching the inline stage. |
| 7 | `8251917C..D0` | Release8; prepare manager, install manager/channel10/contained serialiser, then test result. |
| 8 | `825191D4..82519204` | Release9; actual asynchronous MovieManager IO overload and current Sku language. |
| 9 | `82519208..0C` | Release10 and prepare9 stores only. No calibration work invented. |
| 10 | `82519210..8251931C` | Release12; four debug registrations, actual receiver clear, three assert-and-continue profile/keyboard calls, two network-request byte resets. |
| 11 | `82519320..58` | Release13; contained ProfileManager, FSM heap and bank65 linear allocator; retry false. |
| 12 | `8251935C..C4` | Release14; original listener/helper diagnostic continues on failure. |
| 13 | `825193C8..82519444` | No release store; locale fonts must finish before the existing basic-resource wait. |
| 14 | `82519448..68` | No release store; actual asynchronous WorldDataController on the saved GameData input. |
| 15 | `8251946C..84` | Prepare15/release0; the sole true return. |

All sixteen cases, their fallthrough, nine normal failure gates, invalid-state false return and release-store gaps agree. The three stage10 failures preserve original diagnostic lines519/523/525 and continue. Invalid state retains line608. The code never substitutes the PC `mbPrepared` or manager-pump flags for the original return contract.

## Providers, native types and lifetimes

The stage1 helper at postimage `BrnGuiModule.cpp:1188` uses the real GameData output and AllocatorList methods: pool ids8/9/0/10/11/11/12; banks32/38/31/38/44/42/66; then alignment16 for44 and66. The const output accessor returns the actual list pointer. The exact shipping include order selects the real RenderWare general/linear allocator definitions, whose public `IResourceAllocator` inheritance supports the calls; no cast or shadow allocator is added. The selected vendor headers and bounded earlier-header inventory are retained.

The shared Prepare is a real staged Model/Sku/View/manager owner (`CgsGuiModule.cpp:42`), rather than a replacement success function. The HUD/SCREEN/OVERLAY definitions have the pointer/reference signatures used by the new body and retain their real state-machine/state allocations. FSM Prepare at `BrnGuiFsmController.cpp:85` performs the model/heap adoption present inline in target stage6. The ProfileHost getter at header15 returns its actual contained ProfileManager; the existing Construct binds that manager to the real cache/system profile/language owner at postimage `BrnGuiModule.cpp:1085`.

The custom renderer Prepare is actually defined in `src/GameSource/Gui/CustomRenderer/BrnCustomRenderer.cpp:286`, not solely in the manager-named TU listed in the author's provider inventory. I captured and inspected that exact36ae definition and its shipping mount. It prepares the real base and components. `CgsGuiViewModule.cpp:574` installs the manager into the View, calls its real text/language/replay setters and mirrors it into the contained render handler. The new caller preserves installation even when Prepare returns false. Existing component/platform behavior has not received a new whole-subsystem parity certificate.

MovieManager's three-argument asynchronous overload (`BrnGuiMovieManager.cpp:336`) posts its genuine GameData request and waits for its receiver. The world owner at `BrnGuiWorldDataController.cpp:154` likewise requests and waits through its actual queues and resource handles. Stage13 reuses the unchanged StateLoadingHelper/provider in `BrnGuiCache.cpp:707`, with actual resource-state waits. The checkpoint neither invokes the synchronous PC movie fallback nor manufactures completion of pending resources.

The genuine GameTalk singleton/registration definitions and void callback type match the selected registration. ARTIST callback `824F10D8` confirms StartHook/StopHook/StopMenuHook, comparison lengths9/8/12, fixed32 copy, and actual start/stop flags. This chain still requires real GameTalk singleton, allocator and transport initialization. Stage12's already-existing PC `XNotifyCreateListener` returns a real closable kernel event (`CgsXboxLivePC.cpp:530`); it supplies no Xbox notification stream. No notification parity is granted.

Event595 has one full native `BaseSerialiser*` (`BrnGuiDemangledEventTypes.h:1226`). The existing header-defined AddGuiOutEvent copies `sizeof(T)` into its real queue (`CgsGuiModuleIO.h:123`; `CgsVariableEventQueue.h:428,465`). Thus the local registration record can expire after publication; the contained serialiser remains the owner. ARTIST `8250BCE4..F4` confirms target id595/four-byte pointer payload. The native source widens the pointer naturally, without a console byte shell. Real consumer `GameBridgeGUIToX.cpp:56` reads the same pointer and calls the genuine RequestInterface registration; its definition at `BrnReplayRequestInterface.cpp:57` reads the real id and stores into the canonical slot. ARTIST `823CCEB8..C4` and `821F34A0` support that consumer chain. The optional explicit AddGuiOutEvent instantiation TU remains unmounted; the actual inline definition supplies the calling TU, so no second mount is needed.

The missing `Sku::GetLanguage() const` body at postimage `CgsSku.cpp:82` returns only the existing `meLanguage`. Its existing header declaration, DecFIGS `CgsSku.h:127`, target inline load `825191F4`, shared Construct's Sku seat `82857020..2C`, Sku Construct `828607F0` and SetLanguage `82860F20` agree on that owner and value. No duplicate field or alternate language policy is introduced. Both modified C++ TUs were already shipping mounts.

## Retained documentation erratum R1

The author `REPORT.md:3,61`, `BINDINGS.json.remaining_campaign_work`, the seal's nine-argument field name and older map describe a pending nine-argument original Update. The actual ARTIST function has **ten explicit arguments**: the preceding nine plus a trailing replay-enable byte. `82527B90` loads `arg_67`; GameData input/output are preceding `arg_54/arg_5C`, used at `82529AF4/82529AEC`. Regular caller `823F09AC/09C4` supplies true, while loading caller `823EF378/394` supplies false. These reads/stores are independently retained in this review.

This is a documentation/next-owner ABI error, not a defect in the three inserted Prepare/getter source blocks. No original nine-argument Update declaration/body is added by this patch. The older map and author packet remain unchanged; they must not be used to approve a missing trailing argument. A future Update/Construct/caller packet requires its own review.

## Activation and acceptance boundary

Activation is not approved. In particular:

- Current Construct clears the shared access bundle and leaves `mpAptAux` null; the selected old PC Prepare fills it at postimage `BrnGuiModule.cpp:1520`. The original Construct binding must be recovered before replacing that old entry. This method adds no late fixup.
- Original borrowed GUI output is a `CgsGuiModuleIO::OutputBuffer*` in DecFIGS, while the existing PC projection is a VariableEventQueue pointer. Its ownership/callback lifetime migration remains pending; the new body leaves it alone.
- The loading owner must retain live GUI/GameData records, caller locks, retries and the Update-set0x40 leg. The regular frame owner must supply the correct ten-argument Update, including its replay-enable value. Existing selected no/two-argument PC entries/callers are preserved.
- ARTIST Update creates ViewIO output (`82527CC0`) then ModelIO input (`82527CD8`), calls the full shared Update once (`8252A314`), performs post-base work, then destroys Model input (`8252A39C`) before View output (`8252A3A8`). This complete caller-owned lifetime has not been integrated here.
- Existing manual input/cache/manager/observer/model/resource/view/output consumers and allocations must be reconciled exactly once when migrating. Running both preparations or adding another shared tick would not be authorized by this source pass.
- GameData banks, GameTalk, flow/APT preparation, system handles and teardown require their real lifecycle owners. No initialization, readiness, renderer/control, raw big-endian PC schema, Xenos, asset, online or native acceptance credit follows from this checkpoint. Earlier event62 and other packets retain their own independent verdicts and activation boundaries.

## Method

[STATIC_CHECKS.json](STATIC_CHECKS.json) records 497 reviewer-owned static checks, all passing. They bind the155-file author manifest, exact Git objects, private comparison, shipping inputs, primary export copies, insertion preservation, declarations, stage stores/order, selected providers and pointer-copy chain. I also read the primary assembly and selected bodies directly; counts and author receipts were not treated as parity proof.

Only reviewer-owned file/hash/text/tree calculations were executed. No author script, fixture, provider, C++ compiler, build, test, CI, game, input, IDB or normal delivery operation was run. Source, refs/index, earlier packets, earlier reports, normal configuration/profiles/logs and the control ledger were not changed. Read attempts using an incorrect guessed custom-renderer path and a default CP1252 decode were corrected; neither was source evidence or a source defect. An early reviewer string check was made whitespace-tolerant before sealing; the final checks have no failures. Root retains all integration/publication/launch decisions.
