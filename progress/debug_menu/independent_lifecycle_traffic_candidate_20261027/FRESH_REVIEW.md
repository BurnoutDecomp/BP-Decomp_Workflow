# Independent shared-Construct resolution review

VERDICT: pass

This pass covers the **30 bounded child-call deletions** and their caller classification in the exact sealed resolution packet. It does not approve the central empty-base alternative, either unclosed source exception, any destructor change, native first-object initialization or complete native lifecycle. The earlier central-adoption failure/defer remains in force. No menu-feature disposition is added.

B5 source is pinned to `f6cd2852addd952327576d7cf614be3ff1606b30`, tree `35c5c2eaabd6e3aa3f5f5f06767134e818260272`; identity metadata was independently read from workflow `9b0cfc8afe7fa247866464df5a781456d8b2991a`. No physical source, Git or ledger was changed.

| Exact reviewed artifact | SHA256 |
| --- | --- |
| Seal, 331 entries | `32d3160398f4c77a892e84288b59eee1504f4cc27e98cb3b41be229828820a74` |
| Main manifest | `2567f193cddd98666a2d6f9bbea305934e6364df6e3f56c56c336964da537c0d` |
| Reviewer packet | `fe3060e5d92d7d0c35d3b9f6787a6adeaf580faec46215f126b93a97e3e98933` |
| Source pre/post manifest | `baf8be93051d0229f57b96d882c89c87b89910aaeb8f0d708c3e53dbe00602a8` |
| Exact source delta | `44659c286d93536bc83ee4e9aaf71dd5bf93336f30059a4fd744cbe3a9d717d0` |
| Full current caller map JSON | `0502bf2bc667be14173631f463d9f2637fc58f685414da948975c9044764e483` |

All sealed files match. The review performed 1,954 successful read/hash/source/assembly/raw-byte/data checks and no supplied code evaluation. `ACCEPTED_SOURCE_CALLS.json` retains every accepted SC ID, path, original source line, original caller/branch, raw pre/post SHA256 and Git/line-ending distinctions. The accepted IDs are SC01–SC13, SC15–SC17 and SC19–SC32. SC14 and SC18 remain excluded.

## Positive original and source evidence

The target's complete ARTIST export is the exact canonical `0x8284CB38.json`, SHA256 `f8e89aefa607244646c790a0d7a7fab7c8c3bc603bee5ea1601d783be2120129`. Its executable body is a single `blr`. Its export/ICF name does not establish DebugComponent semantics for unrelated callers.

The 193 xref-owner records exactly match the target export and have 193 unique function-entry addresses. Independent canonical-file comparisons confirm 186 available caller exports and seven missing exports. The available assemblies contain 266 direct linked branches to the target; six additional named address-load references are distinguished from direct calls. Every one of the 266 actual branch words was independently decoded from the retained ID1 image and reaches `8284CB38`. The raw target is `4e800020` plus zero padding. Image SHA256 is `9c15e6b269d6f6e5248038092cd77d48af098d8b3a682e60cc6175bbcb420bad`; its size is 320,888,599 bytes. The complete per-branch word/PC/target roster is in `EVIDENCE.json`.

The named Construct subset has exactly 55 owners: 41 names containing DebugComponent and 14 other names. There are 52 available Construct exports containing 54 direct branches. Sound `826A1230`, AI `82767090` and Sky/EnvironmentSettings `827C7668` remain missing-export metadata. Actual DecFIGS files independently corroborate 38 of the 41 direct-base declarations; Massive, EventScores and DLC have no matching owner-class declaration in the inspected dump. Those missing-declaration cases are not silently relabelled as declaration-proven. Their complete original calls support deleting the added host effect without inventing new declarations or layouts.

The 32 enumerated qualified base-Construct expressions match the exact immutable source paths/lines. Thirty have one original branch joined to the claimed owner export, exact hash, receiver expression and local assembly window. Each full pre/post file differs by deletion of that one literal source line only; reinsertion restores every preimage byte. All other owner code, assertions, defaults, registration, callbacks, list behavior and destructors remain unchanged. Four retained preimages are byte-identical to their Git objects; the other 26 match after CRLF-to-LF conversion only. The pinned Git objects themselves have mixed LF/CRLF policy. Raw identities are preserved separately; no arbitrary text normalization is used.

## Four parent-inline joins

The four non-DebugComponent-named parent routes used by this delta are independently supported by assembly, actual typed source and actual DecFIGS parent/child declarations:

| SC ID | Source child | Original branch / child receiver |
| --- | --- | --- |
| SC04 | CgsNetwork::VersionDisplay | NetworkManager `8289B3F8`; parent `this`, first `mVersionDisplay` member. Subsequent +0xC/+0x10/+0x14/+0x18 writes match the banner state. |
| SC05 | CgsNetwork::PlayerManagerDebugComponent | PlayerManager `828958EC`; r29 = parent +0x2418 (9240), followed by owner pointer +0xC, real Register and child flags/scales. |
| SC11 | BrnGameState::StreetManagerDebugComponent | StreetManager `823359A0`; r29 = parent +0x1DF0 (7664), followed by owner pointer +0x10 and count +0xC. |
| SC17 | PhysicalTrafficManagerDebugComponent | PhysicalTrafficManager `82636DF8`; r29 = parent +0x19C90 (105616), followed by owner pointer +0xC and the child flag/5.0 scale stores. |

These are actual child-body mappings, not assignments made merely because a parent references the ICF target. Additional original parent alias calls—such as the Renderer two-call owner, GUI member candidate, literal-3 sound call and GameTalk member route—remain distinct. They do not expand this source delta. Additional parent source and DWARF files read for the four joins are retained under this review directory with hashes.

## Preserved and deferred boundaries

Sky SC14 remains unchanged because the matching target xref owner lacks an exported caller body. SceneSweeper SC18 remains unchanged because its supplied enclosing `OverlapGenerationModule::Construct` export has no direct target branch; absence does not establish a no-op. Seven missing xref exports remain metadata only. The qualified-expression inventory is not proof that every call through an object, inlined route, indirect reference or wider alias has been classified. It cannot authorize the central replacement.

The exact pinned shared explicit Construct and the distinct C++ default constructor are preserved. The latter still initializes active/list fields in current PC source, but no native first-store origin is inferred from an absent standalone original constructor. No Destruct body/call is changed. Prop teardown F604 remains separate: this packet's PropDebug postimage removes Construct only and retains its base Destruct call; BrnPropManager is outside the delta.

Six deletions overlap the earlier fifth/sixth local Construct proposals. They must be composed once against actual preimages, not applied twice. The three World/Prop/Stunt sites from the fifth author packet were rejoined to their actual bytes here; this report does not replace the separately required fresh review of that earlier authored packet. All prior packet/central copies match their original hashes and the older seals remain unchanged.

Two convenience renderings have nonblocking packaging defects: CURRENT_CALLER_MAP.tsv renders array cells as `System.Object[]`, and FIRST_CONSTRUCTION_AND_DESTRUCT_BOUNDARIES.md has five control bytes plus an unexpanded `$hash`. Those renderings are unsuitable as standalone precise evidence. This verdict uses the complete JSON, canonical exports, source objects and raw instructions. A later human-facing publication should use those intact data or corrected fresh renderings while preserving old sealed packets.

Future hosted actual-body and native lifecycle evidence remains required for delivery. This source pass adds no source-ready feature, original-noop or native credit. No supplied script/test/fixture/case/checker/runner was evaluated; no compiler, game, input or CON was used. Only this new scratch review directory was written.
