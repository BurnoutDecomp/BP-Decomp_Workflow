# Manual ARTIST / declaration postmortem

No compiler, source gate, tests, native run or independent reviewer was invoked. This is a source/assembly self-review.

| Check | Primary binding | Proposal |
| --- | --- | --- |
| ABI | All three prologues retain r3=this,r4=input stack,r5=output stack; DecFIGS declares private non-virtual bool members. | Exact typed overloads; original caller selects them using its IOBufferStack pointers. Current void-pointer overloads are retained. |
| Input lifetime | CreateResourceInput at each entry; 8266DB68..80,8266DCE0..F8,8266E3D4..E8 return true before the respective DestroyIOBuffer tails. | Manual Create/Destroy, no allocation-result guard or RAII pop. Success retains the carve. Pending paths destroy it. |
| Bank bounds | 8266DA9C..A4 reads header count minus1; GetBank82663C88 indexes i+1. Current getter returns count minus1 already. | Uses GetNumBanks directly; does not subtract twice. Selects all 15 non-root rows. |
| Bank requests | GetBank then increment count; Construct takes old count in r5; copy84 bytes; resource tag9/payload96. | Actual Params, old count ID, queue, native sizeof through the typed AddEvent overload. |
| Pool requests | Copy172 bytes; IDs3/4/15 set byte168; replace receiver and ID; tag0. | Canonical request fields and exact order; no PC heap allowance. |
| Reply gate | Outstanding nonzero and receiver count equals outstanding exactly. | No >= gate, result-code check or empty-table completion. Reset count, clear queue, return true. |
| Queue construction | Each local queue receives a leading zero byte then Construct. | MarkUnconstructed followed by Construct; no blanket zeroing. |
| Allocator ordering | Raw10,Linear14,Heap14,RWLinear11,RWGeneral12; family index event IDs; count increment after queueing. | Same order and counters, no synthetic rows/count clamps. |
| Typed storage ownership | 8266DE5C..64 binds raw arrays; DF18 binds Linear; DFD0 binds Heap; E2F4/E328 write member RW mirrors then registry. | Actual canonical GameData fields, not root-debug allocator objects or local storage. |
| Audio lifetime | 8266DD44..60 stores &GameData.mAudioStreamAllocator into the registry on every entry, without Construct. | Exact publication only; original Construct is responsible for initialization. |
| Drain | E284..EC copies5 pointers and10 descriptor words; E2F4..324/E328..358 copies one pointer and registry mirror;14 ignores payload; invalid tag asserts then continues. | Typed canonical GetResource/GetAllocator shapes; same drain cases. No validation of response result or pointer. |
| Capacity vs count | Raw map header82F2A788 gives1/7/8/4/4; row starts106738/106746/106755 pin Linear8/Heap9; ctor827E33BC..F4 constructs9 Heap interiors. | Storage capacities8/9, populated loops from the real map. Native7/8 bounds remain unchanged. |
| Response shape | 8286D11C queues76 console bytes; 8286D53C queues20. DecFIGS raw fields are only Resource/Descriptor; Linear has one allocator pointer. | Remove unattested raw tail/Linear second pointer, retain native getters/producer setters over the same canonical fields, add original out-parameter getters. |
| Existing path | Exact pre/post extracted native methods. | Prepare(void*,void*), three native helpers and Construct unchanged; no new caller or mount. |

Local descriptor default writes immediately overwritten by the complete map-record copy are elided; no externally visible field/store or branch is removed. Native pointer widening uses canonical member types and sizeof, without packing or offset casts. The invalid-event assertion retains ARTIST's message, original source path and cpp2560 location, then continues if the assertion returns.

This packet does not claim that the current constructor/factory or memory-service providers implement the original chain. Known gaps are enumerated separately, including existing empty RW handler bodies. Lower-rung capacities do not override ARTIST. No Feb-2007 layout or behavior was used.
