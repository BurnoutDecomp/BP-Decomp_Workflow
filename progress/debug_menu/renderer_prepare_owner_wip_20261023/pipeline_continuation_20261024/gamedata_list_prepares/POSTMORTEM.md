# Source self-review

ARTIST pseudocode and assembly were checked first, followed by the DecFIGS declarations. Five bool methods each take this inr3, input stack inr4 and output stack inr5. Each preserves both caller-owned stacks and returns false only after the original pump/destroy tail, or true after its own completion cleanup. No additional parameter, allocator or callback is inferred from decompiler locals.

| Check | Evidence and result |
|---|---|
| Request ownership | Each load and acquire uses the actual embedded mReceiverQueue; tags2/4; event-id0; canonical native sizeof. No generic PrepareDataListResource call. |
| Exact strings | Twelve pointer slots82F2A6F0..A73C and ASCII targets were read from the primary IDB. Load/acquire constants in all five bodies match those bytes. |
| Substage stores | Challenge0/1 has no extra store1. ICE/wheel/HUD/popups do. All use2/3/4 while waiting. Wheel success stores2; others store5. |
| Load flags | Challenge allows failure; the other four do not. All disable live replacement and HD cache. No reply result is checked by the original callers. |
| Receiver timing | Challenge/ICE/wheel clear after submitting load/acquire and after completion. HUD clears before each submission and retains completion response. Popup clears before each submission and once after AddPopupResource. |
| Response contracts | All assert first queue tag2 for load and4 for acquire. Challenge/ICE/wheel/popup additionally assert miEventId==0. HUD lacks that assertion in ARTIST and the proposal. |
| Resource adoption | Challenge/wheel construct typed ResourcePtr from the response's native ResourceHandle pair; ICE uses the canonical ICETakeDictionaryResourcePtr typedef. Real destructors unlink the temporary after AddListResource. HUD and popup receive the whole typed acquire response. |
| Hash width | ARTIST828D8550 and8568 explicitly clear the upper32 bits of the u64 result. The canonical current provider returns s32; the proposal casts through u32 before u64, preserving those exact values without changing global callers. |
| Input lifetime | All create before substage check. Every successful and pending branch unlocks and destroys the actual carved input. Only pending/invalid branches pump; no result-based fake readiness. |
| Native preservation | Removing the complete added payload reproduces the exact full preimage, as recorded in NATIVE_BODY_BINDINGS. No existing helper/body/field is changed. |

DecFIGS `BrnGameDataModule.h` attests all five original two-stack bool declarations. Existing canonical declarations supply each stage field, receiver, list/controller member and request/response type. Type/accessor/body evidence is frozen from exact source2ce; the sixth-packet destructor overlay is bound separately.

The source proposal introduces no additional PC platform policy. The retained current queue capacity, data-list binary layouts, smart-pointer implementation and native stack allocation templates are existing canonical providers, not a claim that this packet audits their entire transitive engine. The primary Wheel export was absent from the JSON set, so the bounded existing-instruction/raw-byte read is preserved with script, log and input receipts. No decompilation or autoanalysis was requested. The original IDB hash is unchanged, and the one BelowNormal worker exited.

Known prior defects stay separate: the missing quote has Root's separately reviewed correction; sixth-packet SetDiskErrorOccured still needs its one-store body. The two remaining schema/vehicle helpers, initialization/factory recovery and PC renderer allocation integration are not supplied. No compilation, native behavior or registration credit is asserted.
