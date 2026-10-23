# Manual source/assembly postmortem

No compilation, source gate, tests, native run or independent reviewer was invoked.

| Check | ARTIST / declaration evidence | Proposal |
| --- | --- | --- |
| Handler ABI | Both prologues retain r3=this,r4=request,r5=output. General's decompiler five-argument prototype is wrong. DecFIGS h has const typed requests and void result. | Exact typed declarations/definitions; dispatcher uses the matching derived request. No new virtual slot. |
| Source reuse | Prior56676 includes the mutable bank-view compile repair over9e70738. | Both complete normalized method chunks are identical to56676. No stale whole source file was transplanted. |
| Capacity vs storage | D1C8..208 and D5E8..628 copy original five-lane capacity, call static GetResourceDescriptor, copy expanded requirements. | Separate capacity/storage descriptors; no alias or guessed console reserve. |
| Initial state | Five backing pointers null; all84 Params bytes zero; strncpy32 then byte31 zero; requested IDs and leaf byte1. | Canonical default Resource clears five pointers; aggregate Params clears members; same name/ID/leaf writes. Fragmentation remains false. |
| Parent ownership | D2DC..300 / D6FC..724 resolve the parent anew for every lane, including empty lanes; u16 block-size units are KiB. | Actual GetBankIndexFromId/GetBank/GetBlockSize members, left-shift10. No parent fallback or skipped lookup. |
| Rounding | Unsigned alignment comparison, signed divw(size-1,granule), +1, wrapping mullw. Every nonzero lane gets one block. | Signed quotient and u32 multiplication, exact one/zero block values; no raw-service block-count substitution. |
| Arithmetic traps | Expanded descriptor alignments are at least1; positive granules are u16<<10. | Zero granule fails the original alignment check before division; no invented divide guard or error policy. |
| Diagnostics | Unsigned bank size>=0x4000000 asserts at Linear536/General656; signed waste>=1024 logs only under filter bit1. | Same text/path/locations, original "waisting" spelling, signed wanted/waste and unsigned granule. Assertion continuation preserved. |
| Bank failure | After five lane checks, CreateBank result propagates. Alignment failure is13. Either failure leaves all backing lanes null. | Same result and backing state. No extra ID-range reply, bank fallback or rollback. |
| Initialization | D514..520 / D934..940 always invoke the correct static Initialize with backing and original capacity. | Exact call and pointer response, including failure. Real static null guard prevents fake construction. |
| Reply | D524..540 / D944..960 use request event type, receiver/id/type/result/allocator and20 console bytes. | Canonical single-pointer response and sizeof(native reply); no queue/receiver ownership change. |
| Lifetime | Update owns input-read/output-write locks; queue copies the stack reply. | No nested locks, escaped local reply or extra free/destroy. Memory bank retains backing; allocator lives inside lane zero. |
| Existing path | All unrelated method bodies extracted from pre/post. | Native/raw/wrapper creation, base preparation and existing bank construction remain unchanged. Source binding is not runtime proof. |

The source uses a local `Params` aggregate rather than duplicating byte writes into its padding; only named fields are consumed by CreateBank. Descriptor default writes that are completely overwritten by the request copy have no external effect. The existing canonical assert/stream APIs render original diagnostics; no parallel callback/stream implementation is introduced.

Current GetBankIndexFromId retains a pre-existing unsigned/const declaration and simplified invalid-ID assertion, whereas raw82866E70 and DecFIGS name a signed non-const accessor with a streamed assertion. That provider is frozen but not silently replaced in this packet. Current bank/block engines and host initialization are not blanket-approved by these two recovered handlers. Exact pending boundaries are reported separately.
