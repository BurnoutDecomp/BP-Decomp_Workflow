# Independent game IO and allocator initialization review

BATCH_VERDICT: pass

SOURCE_COMPOSITION_VERDICT: pass

Both packets pass for bounded source WIP. No introduced source defect was found in the seven-path composition. The recovered game factory hooks and allocator initialization match their primary evidence, and the retained native allocator reset is preserved. This is not compile, link, mount, allocation, initialization, activation or native-readiness approval for the original preparation pipeline.

## Exact binding

- B5 source: `02c63ea7ed5dfb3b43dbaeb959a2d23f3861db6b`.
- Source tree: `25eb026b366ea48d75c220599edfeb0ce0b47556`.
- Source parent: `d458cd5641a318f8289da22058220f995b6846b5`.
- Paired workflow: `749a1980ff01f762201c3836f61a0830104282f8`; its b5 gitlink names the exact source above.
- Entry: [REVIEW_REQUEST.md](REVIEW_REQUEST.md).

[BINDINGS.json](BINDINGS.json) records complete pre/post SHA-256 values, target Git blobs, packet/evidence/seal checks, selected providers and shipping files. Every postimage matches the exact source commit. Both complete patches reproduce their pre/post files. The source-parent diff contains exactly the seven proposed paths, with no additional path. All seven preimages also match source183, and the factory packet's source702 preimages remain valid at the composition parent.

| Packet | SOURCE_MANIFEST SHA-256 | Patch SHA-256 | Packet SEAL SHA-256 |
| --- | --- | --- | --- |
| game_legacy_io_factories | `e3cc1382d7190e4125bdb8d214f77c07112db66d5f44d2c8e2262618af641099` | `52b5d1cf7c05b5e77999611e4c56cb89d877276b60afc4adec936b09817af233` | `83a1b47e47c025b48bc81e3baaa7fc4f48539cebf4a05dceafd428244ccff3af` |
| allocator_list_original_initialization | `224a8c5f74bf9b20c7c2d38659913dd77c1cd171f913095f6b6af28d6a0223c1` | `3606627b0d683abe664e50b6d68d32740c9b62d989c1243ac11eb0d7afd0cfb8` | `7a9124c05a460d7511f724edccbe1826adc435f49fa2fd4451ea86e81bee9455` |

All 64 evidence entries and 102 seal entries match. The 104 packet files, including both seals, are archived under [inputs](inputs/). Ten frozen ARTIST JSON exports also match the original workspace exports. Seventeen current providers are archived under [providers](providers/), and the seven exact target files under [composed](composed/). Source locations below refer to those snapshots. No new IDB read was performed.

## Game legacy IO factories

PACKET_VERDICT game_legacy_io_factories: pass

The actual game C++ constructor827E5F00 loads the main table address0x820D14A8 into r10 at827E5F58 and installs it at0(this) at827E5F6C. Its raw big-endian words independently decode to the recorded table. Entries0..16 are used; the trailing `Dispatch`/`ResourceInput` text is not interpreted as slots.

| Original slot | Primary target | Verified ABI/effect | Existing typed provider |
| --- | --- | --- | --- |
| +0x28 | 827E3100 | r4 structure → empty Destruct; bool true | DestroyInputDataStructure |
| +0x2C | 827E3128 | r4 structure → empty Destruct; bool true | DestroyOutputDataStructure |
| +0x30 | 827E3150 | r4 input Prepare, then r5 output Prepare; bool AND | PrepareDataStructures |
| +0x34 | 827E31C0 | r4 input Release, then r5 output Release; bool AND | ReleaseDataStructures |
| +0x38 | 827E3090 | Construct/return this object's input at console+0x228 | CreateInputDataStructure |
| +0x3C | 827E30C8 | Construct/return this object's output at console+0x22C | CreateOutputDataStructure |

The destroy hooks ignore their original r3 module receiver but consume the structure argument in r4. That makes827E3100 the template's bool destroy-input hook, not a payload member named DestroyBuffer. Removing the former invented payload method is correct; the frozen and current source searches show no caller of that removed game method. The positive installed-table binding supplies the virtual-dispatch evidence that a text search alone would not provide.

Both calls in each Prepare/Release hook occur before any branch testing their results. The current canonical template (`providers/.../CgsModuleSingleBufferedTemplate.h:86-105`) evaluates `input->Prepare/Release() && lbDone` in one statement and `output->Prepare/Release() && lbDone` in a second, so the output call is not skipped when the input returns false. Its two factories and destroy hooks (`:56-84`) match the primary effects. The template already owns private by-value TInputBuffer/TOutputBuffer members (`:108-110`); it is unchanged. These are separate from the base class's two DataBuffer wrappers. The actual DataBuffer setter stores the returned structure pointer (`CgsDataBuffer.cpp:3-6`), and its getter returns that same pointer (`CgsDataBuffer.h:27`). No input/output alias, allocation registry or invented template fix is used.

The proposed game base is the real specialization at `composed/src/GameSource/Game/BrnGameModule.hpp:192-195`, retaining IThreadClass as the second base. DecFIGS names that specialization, its two fields and six virtual hooks. The game declaration dump itself prints IThreadClass without the primary template base, so the load-bearing inheritance/ownership proof is the ARTIST installed table, constructor and factory addresses, together with the named template declarations; the dump omission is not treated as contradictory runtime evidence.

`BrnGameModuleIO.h:14-32` correctly gives InputBuffer an empty DataStructure base and OutputBuffer the same base plus its sole private RequestInterface<1024>. The genuine provider chain is RequestInterface → owned RequestQueue → ResourceRequestQueue → VariableEventQueue; its only output member and1024 capacity match DecFIGS. No IOBuffer flag header or guessed padding is inserted.

The eight named IO lifecycle methods at `BrnGameModuleIO.cpp:12-20` are legitimately empty Construct/Destruct and true Prepare/Release. ARTIST hooks actually call the empty ICF target8284CB38 (`blr`) or success target82C296C8 (`li r3,1; blr`). Separate named DecFIGS methods2DA534/538/540/548 and2DA550/554/55C/564 independently confirm those effects. They are not unsupported quiet-success replacements. The secondary named template ASM corroborates the signatures and both-call ordering without imposing PS3 offsets on the PC layout.

### Queue birth and caller effect

`composed/.../CgsVariableEventQueue.h:51-56` adds the genuine protected BaseVariableEventQueue constructor and initializes only mbIsConstructed=false. DecFIGS declares that protected constructor/member. In the actual game C++ constructor, r30=0 at827E5F50 and827E5F64 stores it to the output object's leading byte at console+0x22C; the output factory independently returns that same object. The output's sole request queue begins there. The canonical named base constructor models the actual birth store without a numeric-offset write in native source.

This initialization affects every newly constructed derived VariableEventQueue instance, including automatic and embedded queues outside the game pair. It does not zero data/counters, call Construct/Clear, set an alignment offset or make a queue ready. The existing VariableEventQueue::Construct still performs the true/counter/alignment initialization (`providers and composed header:188-207`); its other methods are unchanged. Existing explicit birth-zero stores/MarkUnconstructed calls remain redundant stores of the same flag. No direct BaseVariableEventQueue object or relevant trivial-default-construction assumption was found in the current source search. This is a generic constructor effect, not an isolated game-output reset.

The current game CPP is byte-identical to the composition parent, but its meaning changes through the new base. Construct still calls ModuleSingleBuffered::Construct (`providers/.../BrnGameModule.cpp:225-231`), preserving the game's legacy classification; its original five-stack Prepare still calls the zero-argument base Prepare at741, and Release calls base Release at3618. Those base operations now dispatch to the six real typed hooks and actual owned pair. The original zero-argument Prepare remains table slot+4 at8286E7A0; the separate five-argument game Prepare remains original slot+0x40 at823DB848. No original owner is activated by this packet.

The typed base adds real owned storage and changes native class layout/virtual dispatch. All affected native objects must be rebuilt together before any integration; unchanged caller text is not evidence of unchanged behavior. The existing canonical Module.h also retains its documented PC virtual-destructor divergence, so this pass does not claim native vtable slot numbers equal the X360 table. The recovery uses named C++ calls and actual typed ownership, not installation/indexing of that raw original table.

Optional template Clear conveniences and output request-interface accessors are outside the six-hook scope and are not granted completeness. In particular, the original empty output Construct and true Prepare do not construct its request queue. A false birth flag must not be promoted to request-queue readiness.

## Original allocator-list initialization

PACKET_VERDICT allocator_list_original_initialization: pass

`composed/src/GameSource/Resource/SharedIO/BrnGameDataAllocatorList.cpp:19-24` gives the canonical nonvirtual Construct exactly two effects: invalidate 67 map entries in order, then clear the sole audio allocator pointer. ARTIST82671B90 sets r30=0 at82671BAC;82671D30..50 forms the actual list base, loads loop count 0x43, stores -1 with stride 4, then82671D58 stores zero only at list+0x294. There are no intervening type-row or pointer-row resets in that original inline sequence. The proposed named stores match it.

DecFIGS attests the member names/types/order and void Construct declaration. Its64-bank/7-linear/8-heap dimensions are older; ARTIST's67-bank loop, accessor bound0x42 and pointer-row spans remain authoritative. The existing67/8/9 declaration bounds are unchanged by this packet. The+0x294 audio location is also consistent with the larger ARTIST rows. Original CreateAllocators8266DD00 fills the live type/pointer rows later; extra zeroing in canonical Construct would invent behavior.

The previous broader reset is preserved as the marked PC-platform leaf ConstructNativePC (`:28-50`). After restoring only the method name, its complete normalized method text equals the old Construct, SHA-256 `2b7864b1c56b1efd69532e5cead927dc2c5f8301a9b334152e9a8eede2d2ccbd`. Its interleaved map/type stores, two raw-resource/descriptor rows, seven linear rows, eight heap rows, five/five RW rows and final audio-null store retain their exact order/bounds. The existing spare linear[7]/heap[8] slots remain untouched. No new clearing or allocator-policy change is introduced.

The native GameData Construct now selects that preserved leaf at `composed/.../BrnGameDataModule.cpp:2450`. Reversing only that call spelling reproduces the complete preimage. The header adds only the native leaf declaration; no member layout changes. The compile-only embed fixture remains a local AllocatorList followed by canonical Construct (`providers/.../BrnGameDataAllocatorList_embed_check.cpp:13-14`); it was inspected, not compiled or run.

The canonical Construct method also exactly equals the prior e99 source chunk, normalized method SHA-256 `c26bac919c75e292b5329ca89625cba59f58f97396644ad0f48d9e5dba95b460`. The archived prior file matches exact sourcee99af2cb6b7f34bc870db2c5f95d35740a9c271e. That equality is continuity evidence only; the primary loop/stores above establish correctness.

The frozen47-file type-reference inventory and constructor/caller receipts were inspected, together with fresh source searches. The actual production owner is GameData's by-value mAllocatorList (`providers/.../BrnGameDataModule.h:505`), not a substitute registry. Its native Construct call selects ConstructNativePC; the other concrete canonical caller is the compile-only fixture. No virtual-dispatch shortcut is relevant to this nonvirtual method.

Publication still uses that exact member's address: original Prepare's completion writes SetAllocatorList(&mAllocatorList) under the output write lock (`composed/.../BrnGameDataModule.cpp:310-315`), and the retained native Update publishes the same address under its write lock (`:2775-2780`). The actual output setter stores the pointer, not an embedded copy. Invalidating the map is not proof that rows have been populated or that an allocator/list publication is ready.

## Shipping providers and remaining limits

The exact workflow's msvc_includes, msvc_flags, build_game_exe.bat and compile_exe.py are byte-identical to both packet-bound workflow baselines2ca227af02ca882a2fd9681ce3443e283df64121 and9be2fe4490a333a26a226f604c5bac9b05ae5396. The shipping route consumes the explicit BAT response-file list, not recursive discovery or game CMake.

| Source | Explicit shipping list |
| --- | --- |
| BrnGameModule.cpp | present |
| BrnGameModuleIO.cpp | absent |
| BrnGameDataAllocatorList.cpp | present |
| BrnGameDataModule.cpp | present |

The list has3021 entries/3002 unique paths. Game CMake's inclusion of BrnGameModuleIO.cpp does not mount it in that shipping route. No mount delta is part of either packet; the new lifecycle definitions exist in source but require the separate shipping integration before they can satisfy link references.

Canonical include order selects the target source's genuine ModuleSingleBufferedTemplate/DataStructure/request-queue headers; the template's relative ModuleSingleBuffered include resolves to that same owning directory. It selects `vendor/PPMalloc/include/ppmalloc/EAGeneralAllocator.h`, a tracked source subtree, rather than a similarly named SDK copy. Its actual BlockInfo uses size_t mnDataSize and char mBlockType. That header and all five relevant EAThread headers match expected source content after newline normalization. EAThread's expected gitlink is38576cbe30e9cd674ad0caa67898fd5ab6450c14; the inspected physical checkout iscefb9557ba9183c836a4e42eaf2c930ea63107e4, with these selected headers unchanged. Full expected/physical hashes and include-resolution records are in BINDINGS.json. No whole-vendor parity or compile validation is inferred.

These source fixes leave the complete original GameData Construct/resource/type-registration owner, missing mounts, allocator/native ownership reconciliation, PC schema/endianness choice, sky-dome lifetime and thread/Prepare scheduling boundaries pending. They do not authorize re-preparing already owned native allocations or using a successful base Prepare as a renderer/allocation readiness witness.

All five earlier sealed review folders, including the initial and sixth FAIL reports, remain byte-identical to their seals. Only read-only source/Git/assembly/DWARF inspection, byte/hash comparisons and creation of this new report folder were performed. No production/ref/index/build/config/profile/log change, C++ compilation, test, CI, IDB opening, game/input/native run or additional agent was used. Root owns publication and integration.

VERDICT: pass
