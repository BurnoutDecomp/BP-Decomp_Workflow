# Positive original factory binding

`evidence/ARTIST/factory_vtables.json` is the bounded raw-table and existing-assembly extraction from the single lane-owned ARTIST IDB copy. Its game record reads `0x820D14A8`, confirmed as the installed primary vptr by the original game C++ constructor (`0x827E5F58`/`6C`). Only entries 0 through 16 are vtable entries; the subsequent words in the recorded 96-byte range are literal text. No claim is based on interpreting that trailing text as callable slots.

| Virtual slot | ARTIST target | Actual behavior | Typed existing-template owner |
|---|---|---|---|
| +0x28 | 0x827E3100 | r4 structure -> empty destructor; return 1 | DestroyInputDataStructure |
| +0x2C | 0x827E3128 | r4 structure -> empty destructor; return 1 | DestroyOutputDataStructure |
| +0x30 | 0x827E3150 | call input Prepare, call output Prepare unconditionally, boolean AND | PrepareDataStructures |
| +0x34 | 0x827E31C0 | call input Release, call output Release unconditionally, boolean AND | ReleaseDataStructures |
| +0x38 | 0x827E3090 | own input at console this+0x228; empty Construct; return pointer | CreateInputDataStructure |
| +0x3C | 0x827E30C8 | own output at console this+0x22C; empty Construct; return pointer | CreateOutputDataStructure |

The shared empty target is `0x8284CB38` (`blr`) and the shared success target is `0x82C296C8` (`li r3,1; blr`). Their symbol names are ICF-selected representatives from unrelated systems. Their bytes and the calling ABI, not those representative names, establish the game methods' effect. The DecFIGS named input/output methods independently retain the empty or true bodies: input `0x2DA534`, `38`, `40`, `48`; output `0x2DA550`, `54`, `5C`, `64`. Named template signatures and fields are in the frozen DWARF header, with the game specialization beginning at physical line 51. The corresponding named PS3 template methods are also frozen, but their console offsets are not used for PC layout.

`CgsModuleSingleBufferedTemplate.h` already declares private `TInputBuffer mInputBuffer; TOutputBuffer mOutputBuffer;`. It already constructs and returns the corresponding owned object. The destroy hooks take the structure argument, invoke its `Destruct`, and return true. Its Prepare/Release implementation evaluates each respective member call as the left operand of a separate statement's `&&`, so both calls execute; it does not short-circuit the output call based on the input result. These complete existing canonical bytes are frozen as providers. They are not edited.

## Member and constructor evidence

DecFIGS `BrnGameModuleIO.h` names the empty `InputBuffer : DataStructure` and output's single private `ResourceRequestInterface mResourceRequestInterface`. Its typedef capacity is 1024. The concrete RequestInterface declaration is `BrnResource::GameDataIO::RequestInterface<1024>` in the frozen `BrnGameDataRequestQueue.h` at physical line 481; its sole member is `RequestQueue<1024>`. The current canonical provider supplies that genuine queue/interface chain. `DataStructure` is genuinely empty in the frozen declaration; no size or payload is invented.

DecFIGS `CgsVariableEventQueue.h` physical lines 1-10 declare protected `bool mbIsConstructed` and the protected C++ constructor at original h51. In primary game C++ construction, r30 is zeroed at `0x827E5F50`, and `0x827E5F64` stores that byte to `this+0x22C`. The actual factory independently identifies exactly that address as the output object. The output's sole queue begins at offset zero; therefore the genuine base constructor initializes that queue's leading flag to false. The proposal writes this through the named bool in the canonical base constructor. It adds no counters, memset, Construct/Clear call, readiness store or native offset.

The console output occupies the 1024-byte queue plus the original 16-byte queue metadata, consistent with the next secondary base vptr at `this+0x640`, installed twice in the original constructor as the base and derived `IThreadClass` vtables (`0x827E5F68`, `70`). This is a consistency check on original ownership, not a mandate to freeze PC offsets or insert padding. The declaration in current `BrnGameModule.hpp` already has `IThreadClass` as its second base. The proposal retains that base and every existing data member.

## Caller coverage and scope

The positive main-vptr/table binding resolves virtual calls that a text search would not prove. The constructor and generic-template field ownership also establish which actual instance the factories return; the result is not inferred from an unreferenced class name. Frozen exact-source searches record the old fake method/type references and current absence of game uses of the optional Clear wrappers. These searches are supplementary scope checks, not proof that virtual dispatch never reaches a hook.

The inherited zero-argument Prepare remains original `ModuleSingleBuffered::Prepare` at slot +4. The five-argument game Prepare remains the separate appended original slot +0x40. Restoring the six factory hooks does not activate the five-argument owner. New-module classification must not be changed to bypass these factories.

The original table extraction used one existing lane-owned IDB copy with analysis/cache/decompiler APIs disabled, sequentially at BelowNormal priority. Small source script, read log and original/copy binding receipts are frozen here. The IDA process/plugin log can mention plugin loading; no decompiler call was made by the script. No new IDB read or copy was needed for this packet. Earlier automatic approval rejections left the retained inactive copy untouched, as recorded in the preserved receipt.
