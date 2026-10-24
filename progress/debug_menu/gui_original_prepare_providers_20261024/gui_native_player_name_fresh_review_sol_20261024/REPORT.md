# Fresh source review: original player-name provider

VERDICT: pass

CANONICAL_SOURCE_VERDICT: pass

SOURCE_COMPOSITION_VERDICT: pass

ORIGINAL_HELPER_AND_FRAME_ACTIVATION: not_approved

The complete queue-taking `GuiModule::UpdatePlayerName` overload, declaration and two explicit dependencies pass this bounded source review. No source defect was found. Both original branches and their diagnostics/copy semantics are recovered. The existing PC fallback and selected caller remain unchanged. The actual PC platform provider's success-with-empty-offline-name behavior is an explicit adoption boundary, not a reason to rewrite the target branch.

## Exact composition

| Binding | Identity |
| --- | --- |
| Source | `36ae3ffed6e8fb3ea89ca91947647aa9465c8658` |
| Shipping workflow | `1c7766f9da14ef677bac273e16921196ea58f9fc` |
| Prepare author overlay seal | `1bd837d613dc24e6fed9d51fd14d88a4e3de3e6ce16f3c37c221850cdc04674f` |
| Aux binding author overlay seal | `16714abbdf362cd764d92e60cbd30a1b6a293257d1420ab3b3673fcc0302edde` |
| New author seal SHA256 | `3a3e614375b586e54c345ac54a19d9ed487d7004057af32448c844601b03c656` |
| New manifest SHA256 | `253ce52586d9af2bb47f23f730b0701d1f33b72cee507b5ac4d6b2deb65d33aa` |
| New author bindings SHA256 | `a617de8b86b794b0ff5fe4181bdb03e58511c53cb258f749ddd53ee9616fce9d` |
| Patch SHA256 | `d0ea9f16acfe9ac1b68a701c354030b639767b8f9047b026139c5b86cbdcfb83` |
| Hypothetical final tree | `fbcf4b56f8f7fe0035fc08913635ec38a8036555` |

| Path | Before SHA256 | After SHA256 | After Git blob |
| --- | --- | --- | --- |
| `src/GameSource/Gui/BrnGuiModule.cpp` | `e08112c074a8fcf85f1d1a5461342b4a3b28490804549e3e1d182ffd2abac2fb` | `b3e749afa72aa158a4692e07fee5c18908e2a1d455591a3f50980b7934af2311` | `05311804a7dd52f8640132b6d4a9d5a33e4e5c7b` |
| `src/GameSource/Gui/BrnGuiModule.h` | `2f2256b8a6879610199df6d7d51741838a8ae2df4c56e13645d51249325abc1f` | `64573852bfab0c5ddfb95f532adb7b57b16f55b46434007a670ad37e033c59fd` | `0bb6546497bc12f784ca44cfb86419693e7ba87e` |

The ordered overlays were independently reconstructed from exact Git preimages. The new preimages match their final bytes. Both prior independent source reviews remain bound by their exact seals (`8a0bd089...` Prepare, `51716da4...` Aux). This proposal retains the Sku getter postimage as the third changed path relative to 36ae. [BINDINGS.json](BINDINGS.json) contains full hashes, all final blobs and all 65 captured inputs. The hypothetical tree was calculated in reviewer memory; no Git object/index/ref or checkout was written.

Both source deltas are insertion-only: 3806 bytes in the module implementation, 167 in the header. Every previous byte line remains. The whole current fallback, Construct with Aux binding, complete original Prepare, old no-argument Prepare, zero/two-argument Update and flow-output caller bodies were also compared directly and are byte-identical.

## Actual target caller and parameter

ARTIST Update saves its r10 View input argument in `arg_4C` at `82527A70`. Case507 reloads that record into r31 (`82529184`), locks it (`8252918C`), obtains its actual View-state queue, and preserves the original diagnostic/accessor sequence. It passes the queue address as r4 (`825291BC/C0`), its actual GUI module as r3 (`825291C4`), calls the helper directly (`825291C8`) and unlocks the View input (`825291D0`). This is a real caller-owned queue, not a GUI output alias or fabricated queue.

The helper does not use the incoming queue. Its prologue retains `this` and overwrites r4 with the local name buffer at `824F0D4C` before XUserGetName; no incoming r4 read precedes that overwrite. DecFIGS `BrnGuiModule.h:743` nevertheless declares the queue-taking void, nonvirtual method. The proposed private overload at postimage header388 preserves that shape. Actual current `ViewIO::InputBuffer::ViewStateQueue` aliases `GuiEventQueueBase<65536,16>`; the named large-queue alias uses that same specialization (`CgsGuiEvent.h:220`). The real accessor returns its contained queue by reference under a write-lock assertion (`CgsGuiViewModuleIO.cpp:101`). Future caller recovery must preserve those accessor/lock effects even though this callee does not read the parameter.

The new body accepts the pointer and discards it; it adds no queue read, write, mirror, lock or publication. This review does not select that caller or replace the full ten-argument target Update.

## Complete body audit

The new method begins at postimage `BrnGuiModule.cpp:2601`.

| Branch | Direct target evidence | Proposed behavior |
| --- | --- | --- |
| API call/result | `824F0D44..5C` | Read the actual SystemUserProfile index; use local name buffer and API limit16; branch on a32-bit zero/nonzero result. |
| Success | `824F0D60..DAC` | Add `PLAYER_NAME_STRING_ID`, format `''%s''` into32 bytes, explicitly zero quoted byte31, add `PLAYER_NAME_STRING_ID_Q`. |
| First default | `824F0DB8..EF8` | Find `DEFAULTPLAYERNAME`; missing-string assertion at original line1216 continues; unsigned length>=27 diagnoses through StringUtils line55; copy27 bytes; add the live plain-name id. |
| Quoted default | `824F0EFC..FFC` | Find `DEFAULTPLAYERNAMEQUOTED`; missing-string assertion at original line1222 continues; unsigned length>=31 diagnoses at StringUtils line55; copy31 bytes; explicitly zero quoted byte31; add the quoted live id. |

The four original literal keys already existed in the TU and remain unchanged. Both32-byte local buffers retain the target initialization policy. The first fallback gains no byte27 terminator, early return or null-success guard; the target continues from its diagnostic into length/copy operations. The length messages retain the actual source text or `<NULLSTRING>` and original paths/line metadata. Success AddString results are ignored as in the target. No forced fallback, persona, readiness flag or output-owner split is introduced.

The user index is the actual `mSystemUserProfile.GetUserIndex()` (`CgsGuideIntegration.h:69`), matching the target's load at module+`0xE7BA0` and the DWARF uint32 accessor. The language manager is read through the real shared access bundle, as target `+0xF5718` specifies. Existing Construct installs that bundle pointer from the actual View's language manager at postimage1078. The new method creates no manager/cache owner.

## Providers, ownership and selected PC behavior

The added C declaration exactly matches the selected `extern "C" u32 XUserGetName(u32,char*,u32)` implementation at `CgsXboxLivePC.cpp:588` and another existing real declaration in `CgsGuideIntegration.cpp:17`. `types.hpp:11` defines u32 as uint32_t. The formatter include selects the actual `CgsCore::SPrintf(char*,u32,const char*,...)` declaration and implementation; no adapter or guessed calling convention is introduced. The32-byte quote buffer is also explicitly terminated by the caller as the target requires.

The real LanguageManager AddString at `CgsLanguageManager.cpp:156` hashes the supplied id, removes an existing dynamic entry, allocates `ByteLength+1` in its language heap, copies through `CgsUnicode::CopyN`, allocates the real hash node, stores the **copied** pointer, inserts it and records it in the dynamic-owner list. ARTIST `828647F8`, especially `828648E0..82864940`, confirms allocation/copy/node ownership. The selected Unicode definitions actually scan to the terminator (`CgsUnicode.cpp:489`) and copy/terminate the destination (`361..405`). Thus both local buffers may expire on return; AddString does not retain them as borrowed pointers. The fallback database strings remain read-only source text. The plain/quoted live keys also match the actual GuiCache accessors; those return string ids, not the rendered names (`BrnGuiCache.cpp:3003,3009`). This is no separate output mirror.

The existing PC XUserGetName implementation copies either the stable shared LAN identity or an empty offline string and returns success. Its real CopyName bounds the copy and writes a terminator; the shared identity has static lifetime. Empty UTF8 is accepted by the actual validator. Consequently a future call of the new original overload would take the success branch offline, publishing an empty plain name and four apostrophes for the quoted name. That differs from the current no-argument PC helper's deliberate default-name path. The proposal correctly leaves that platform policy and the old fallback untouched; adopting it into a native frame remains a separate decision.

The selected caller at postimage `BrnGuiModule.cpp:3566` still invokes the no-argument fallback in the existing channel40/507 PC seam. Its surrounding checks and the complete fallback body at2678 are identical to the preimage. No current callback/dispatcher/frame entry is changed to call the queue-taking overload.

The required real provider implementation files already appear in the exact shipping roster: module, formatter, platform provider, Unicode and LanguageManager. The raw roster contains two identical LanguageManager rows (3418/4912); the actual compile driver normalizes paths and deduplicates them at `compile_exe.py:88..108`. It selects one canonical provider input. This is pre-existing roster behavior, not a new mount or duplicate provider proposal. Both raw rows and the actual driver are retained, rather than assuming a raw-row count proved provider selection.

## Acceptance limits and method

VERDICT pass is source-only. Activation, compilation/linking, language-heap/table readiness, actual platform user/identity policy, GUI control behavior and native/gameplay readiness are not approved. The full target Update still needs its ten explicit arguments including the replay byte, genuine borrowed output/callback ownership, caller IO stacks/locks/retries, base/post-base order and exactly-once migration of current manual consumers. The earlier common-Construct change retains its own active-when-composed boundary; this new proposal does not add another entry selection. No raw big-endian PC schema, Apt engine, online identity or full-lifecycle certificate is implied.

[STATIC_CHECKS.json](STATIC_CHECKS.json) records 121 reviewer-owned static checks, all passing. They bind the 27-file manifest, original primary exports, exact source/provider/workflow objects, ordered overlays, full-body preservation, declaration/caller ABI, both branches, ownership, provider selection and PC boundary. Direct primary assembly and provider-body reads supplied the semantic review; check counts and author receipts were not treated as parity proof.

Only reviewer-owned source/byte/hash/tree scripts ran. No author/provider/fixture import or execution, compiler, build/test, CI, game/input, IDB or normal delivery action ran. Source, refs/index, earlier packets/reviews, normal configurations/profiles/logs and the ledger were unchanged. An unmatched parenthesis in the new reviewer script was corrected before any audit ran. An early raw-mount uniqueness assumption was corrected against the actual driver deduplication before sealing; it was not a source finding. Root retains sole integration/publication/launch ownership.
