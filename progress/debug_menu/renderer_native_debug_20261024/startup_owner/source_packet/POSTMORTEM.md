# Source self-review

## ARTIST behavior and ABI

- Renderer Prepare82409C20 takes this inr3 and AllocatorList inr4, savedr28. The bounded native caller passes the list from the actual read-locked output, matching823DB9D0..9F0. It does not pass a temporary/generated list or guessed allocator.
- The original stage switch starts at0, calls the base at82409C8C, traverses the empty2/3 stages and resets only release stage at Done4. Its source block is unchanged. The original allocation tail runs even at Done, so repeated calls cannot be treated as harmless.
- The Windows resource branch is an explicit platform change, not an assertion of exact console allocation behavior. All native capacities, allocator return identities and resource owners come from exact-base Construct/provider code. The untouched original tail is retained under#else; the original Register and MemoryUsage completion is common.
- The original base Construct is at8240A800, after shader frames and writable selectors. A7A0 is an empty ICF target, not that base call. The proposed placement honors the separately frozen order correction. Earlier native effects/display adaptations are outside this delta; full Construct parity is not claimed.
- The original final new-module seed from8240BF90 stays at Construct's end. The base uses it to skip old DataStructure factories, not to mark graphics resources ready. There is no new ready member or derived-stage assignment.
- Sky Prepare82408DF0 invokes CreateGeometry with(22,45) and(5,10). CreateGeometry824076D8's index-count formula yields2066/118; named draw fields carry primitive6/base0/min0. Snapshot headers use sizeof the actual native header types. No new class reinterpretation is used.

## Declaration shape and source contracts

- DecFIGS binds the original renderer/base, AllocatorList map/type/array indirection, sky members and IO pointer shape. New methods/structs are explicitly PC leaves; they are not attributed to DWARF.
- GameData's existing friend relationship permits validation of the actual private AllocatorList row without adding setters, layouts, casts or public mutable access. Slot bounds precede indexed pointer reads; a negative or failed slot cannot index an array.
- The actual native general-allocator publication occurs only after all required backing lanes succeed and AdoptMemory runs. The validation requires agreement between the published list and the module-retained generated pointer.
- The output getter is called only under the original IO read lock. GameData Update takes its own write/read brackets before that; no lock is held across Update. Its existing output Construct is the members-only active-consumer inline body. The different larger-WIP constructor/caller corrections were not imported.
- ImRenderBuffer public named fields are inspected through the actual template type. uintptr_t conversions are address-span checks only, never memory-offset access. Bounds use subtraction to avoid end-address overflow. Constant guard additions are the exact native allocation contract.
- DispatchBin's qword is the actual16-byte DispatchCommand; actual Construct rounds its128-byte-aligned allocation and adds128. Native constants are128-byte multiples. No command cursor/list is reset.
- The sky snapshot is read only after the existing owner reported ready, so previously unconstructed draw fields are not read. Its four saved header pointers are compared across the ready-owner reuse branch, and all five usage lanes must be unchanged.
- The genuine graphics wrapper query providers and canonical vendor methods already exist in exact prerequisitee315. Their declaration accessibility correction remains intact; no src/SDKs-only constructor/API was selected.

## Source availability and scope

- The new non-inline methods have declarations and definitions in the same proposed batch; the remaining new snapshot/validation template bodies are inline or local.
- Game/flow, IO, base module, graphics allocator, RW, sky, presentation, shutdown/window and logging dependencies are retained exact-base providers, bound as evidence. The changed CPPs are shipping-mounted already. This is a static availability audit, not a successful compile/link claim.
- EngineUpdate's BeginFramesPC call count is unchanged. The initial startup owner exits after one successful canonical Prepare. Existing later ThreadLayout handoffs are retained. No new Begin/End or original owner call was added.
- Old GameData Prepare/Construct/Update/allocator creation and GameModule/flow/thread source bodies are unchanged. Native Done7 remains active; original stage19/full-owner integration is separate.
- Root's prior native log proves only its attributed observations. No newly proposed diagnostics executed. No C++ compilation, tests, builds, CI, registry Save, game input or runtime activation occurred.

## Explicit platform tradeoffs

Earlier startup table preparation, message-pump timing, main-thread presentation recovery and allocation-failure shutdown are reviewable PC behavior changes. The canonical original registration lifecycle governs completion, but this patch does not restore all original renderer allocation routing or the five original main stacks. A future original-owner migration must remove/reconcile this sole native startup owner before adding another Prepare caller.
