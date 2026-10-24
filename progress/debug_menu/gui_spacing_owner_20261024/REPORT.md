# GUI event 62: real spacing owner and consumer

This is a five-path canonical source proposal, **unactivated**. It recovers the original event-62 store and the two original named setter methods. The selected PC GUI frame port still needs its complete input-to-view ownership reconciled before this can deliver the debug action in the native game. No registration-site disposition or runtime result is claimed.

Base source: `36ae3ffed6e8fb3ea89ca91947647aa9465c8658`, tree `11d65ea7620c833b4fe36d943f85bfdc2a186128`. Shipping-build evidence: workflow `1c7766f9da14ef677bac273e16921196ea58f9fc`. Private GUI comparison: `43ff84778bf12a6bf5883b3416bacfd4370d2486`.

## Recovered source

The deferred-store comment in `CgsGuiViewModule.cpp` incorrectly describes event 62 as an unmodelled AptAux tail. The storage already exists and already feeds the real text renderer. The proposal:

- Recovers case 62's flat `f32` payload, exact original assert at `CgsGuiViewModule.cpp:545`, and assert-and-continue store through `mAptAux.DebugChangeFontSpacing`.
- Declares and defines genuine nonvirtual `AptAux::DebugChangeFontSpacing(f32)` and `AptRenderHandler::DebugChangeFontSpacing(f32)`. The former delegates to the embedded handler; the latter performs one float store.
- Renames the existing single handler member `mfFontSizeScale` to its original DWARF name, `mfCharSpacingMultiplier`. Its type, position, access, two existing 1.0 seeds, and callback getter remain the same. `GetFontSizeScale()` retains its existing PC API name and reads that same member.

There is no extra field, layout padding, allocator, readiness flag, invalidation walk, range check, Apt SDK edit, or shipping mount change. Event 61 remains deferred; its old claim that event 62 lacks an owner is removed. No source outside these five full postimages is proposed.

## Primary identity and type proof

| Evidence | Original identity |
| --- | --- |
| ARTIST `ViewModule::Construct`, `0x828605A0`, asm `82860610/2C/58` | The actual AptAux subobject is View +57360 (`0xE010`). |
| ARTIST `AptAux::Construct`, `0x8285FFE0`, asm `82860124/28` | Its actual handler is Aux +1056 (`0x420`). |
| Same constructor, asm `82860198` | Publishes that Aux as the callback singleton `off_8305A6C8`; the original also diagnoses multiple instances. |
| ARTIST handler Construct, `0x82854430`, asm `82854A10/20` | Seeds float at handler +108584 (`0x1A828`), adjacent to the text-effect word at +108580. |
| ARTIST View event consumer, `0x8285FCE8`, asm `8285FD70/74`, `8285FF18..40` | Materializes View +167000 (`0x28C58`), asserts `lpSpacingEvent`, loads one float and stores it there. |
| DecFIGS `CgsAptRender.h:285/216` | Names that float `mfCharSpacingMultiplier` and declares public nonvirtual `void DebugChangeFontSpacing(float32_t)`. |
| DecFIGS `CgsAptAux.h:398/486` | Declares the corresponding Aux method and embedded `mRenderHandler`. |

`57360 + 1056 + 108584 = 167000`. The adjacent type, constructor seed, callback read and consuming `TextObject` write independently support the identity. These console offsets are evidence; the proposed host C++ uses named members and ordinary object layout.

Full existing exports and DWARF files are frozen under `evidence/`; `evidence/PRIMARY_ASM.txt` and `evidence/CHAIN_SLICES.txt` are navigation excerpts. Export pseudocode's erroneous parameter counts are not used as ABI authority.

## Producer, transport and actual owner

The component is `Gui/Gui Module`. Original OnActivate site #0020 registers the function **Change Font Spacing**; #0021 registers its `f32` percentage parameter with range 30..250 and default 100. It does **not** attach a change callback to this parameter. Editing #0021 alone is not the apply action. Selecting #0020 reads its current value and enqueues event 62.

ARTIST callback `0x8250D160`, asm `8250D1F4..214`, reads component +0x2C, multiplies by the 0.01 float, and calls `VariableEventQueue<18432,16>::AddEvent` with id 62 and payload size 4. Current `GuiDebugComponent::ChangeFontSpacing` has that same producer. `GuiDebugComponent::Update` appends its persistent input queue to the caller's GUI input, unlocks it, then clears the persistent source. The queue owns copied packed bytes; the callback's local float is not retained by pointer.

The original frame chain is complete in the primary evidence:

1. Original Brn wrapper `0x82527A58` calls the shared GUI Update at `0x8252A314`.
2. Shared Update `0x828602C8` calls `BridgeFromInputToView` at `0x82860378`, under the real IO locks and before the single view Update.
3. Bridge `0x8285B088` forwards the **whole caller GUI-input queue** with the real `AddViewState<32768,16>` publisher, not an event-id list. Its mounted explicit instantiation and ARTIST `0x82859E28` are frozen too: it uses the actual destination view queue's AppendSafe and reports an append failure. Queue capacities, locks and original overflow behavior are not changed.
4. View Update consumes that view queue before AptAux Update. Case 62 changes the embedded handler's existing scalar; the view's ordinary per-event tail still delivers the record to the installed custom-renderer manager.

Current native object identity is also explicit: BrnGui constructs its by-value `mViewModule`, the derived View calls the shared View Construct, and shared GUI Construct stores `mpGuiView = &mViewModule`. That shared View owns `mAptAux`; its Construct publishes this same Aux singleton. No second view or mirror is introduced by the patch. Any future runtime validation must establish that these owners and the original singleton lifetime remain the ones in use.

## Prepared text and visible rendering

The existing consumer is already mounted and substantive:

1. `AptAux::ConstructApt` installs the real AllocateString and DrawString callbacks, plus the dynamic-text draw hook.
2. `AptCallbackRender::AcquireStringSlot` resolves the singleton's **same handler**, obtains its existing string slot/character storage, and reads `GetFontSizeScale()` from the recovered scalar.
3. `AllocateString` passes that float to the genuine `CgsAptString::Prepare`. ARTIST `828592D4/E8/F0` loads handler +0x1A828 into FP argument f1 and calls Prepare.
4. Prepare copies a non-1.0 value into the actual `mTextObject.mfCharSpacingMultiplier`; ARTIST `828550A8/B0` preserves that condition/store. A value of 1.0 leaves the authored font-specific setting in place, including the existing condensed-font 0.85000002 value. This is character spacing, not font-height scaling.
5. The Apt item renders its resolved text handle through `gpfnAptDrawTextRenderData`; the installed hook reaches `AptCallbackRender::DrawString`, the original slot, and `TextRenderer::RenderStringBuffered` on the current real command buffer.
6. The selected buffered glyph loop advances `lfPenX` by `mfAdvance * mfCharSpacingMultiplier * lfGlyphX` (`CgsFontRenderer.cpp:799`). ARTIST `82800710..18` consumes the same TextObject float in glyph advance. Right-aligned line placement also uses the multiplier.

Handler-owned native string objects and per-slot character buffers live beyond a callback; the returned host handle resolves back into that pool until release/reuse. The current header includes the genuine `CgsAptString` type. Older comments describing an opaque conflicting slot are stale and are not used as evidence.

The event store does **not** dirty existing text. `AptCIH::ProcessTextInst` only calls EnsureStringAllocated for visible unresolved/empty or dirty dynamic text. Thus the multiplier is baked when a string is genuinely prepared or rebuilt. Cached prepared strings may retain the old value. The proposal adds no global reallocation/invalidation policy.

For Apt ABI, the frozen XB1 `?GetZID@AptCharacterTextInst@@QEBAQEAXXZ` at `0x140839E60` returns `void*` and loads eight bytes at native item +0x68. The current SDK uses `intptr_t mZID`; the existing slot-index handle bridge is retained. Other frozen XB1 accessors attest the existing native item reads for font size, bounds, format and measurements. No new Apt engine offsets, pointer narrowing, serialized-data changes or console-layout widening are proposed. This bounded trace is not a blanket parity claim for the existing Apt engine.

## Precise remaining selected-PC prerequisite

Exact `BrnGameModule.cpp:4887..4893` calls the derived **zero-argument** `mGuiModule.Update()` after its prepared check. That entry selects the existing **two-argument GameData port**. The port appends/flushed debug records, dispatches its suffix, directly feeds the renderer manager and flow observers, posts selected view events, and invokes `mViewModule.Update` once at line 4519. It does not invoke the canonical whole-input bridge in this selected frame owner.

The shared **eight-argument Update is virtual**. It is a distinct signature; the derived zero-argument override does not select it automatically. The report does not claim global unreachability from a text search. It binds the actual selected scheduler entry, its concrete overload body, the virtual declarations, the original wrapper call, and the inherited view identity. Read-only search receipts are navigation evidence, not proof that every possible virtual/template call is absent. The known typed Sku owner publishes language/resource events and supplies no alternate shared-frame update in its inspected body.

Merely appending the whole GUI queue before the existing view tick would make the view's universal renderer-manager tail duplicate the current direct manager delivery. Calling the entire shared Update in addition to the port would also duplicate flow/model/view work and output ownership. In private43ff, the manager/cache notification exceptions and retained output loop-back differ again. An event-62-only forwarding arm would hide this missing frame owner, so none is proposed.

The required next recovery/integration boundary is the real original Brn GUI frame wrapper and its caller-owned IO set: preserve original input/model/view bridge order, exactly one model/view/flow update, exactly one manager/observer delivery, output-loop-back order, queue retirement and caller locks. Either recover that genuine wrapper coherently or review a complete PC ownership reconciliation of those same seats. Its original ARTIST `0x82527A58`, shared `0x828602C8`, bridge `0x8285B088`, and the full selected caller bodies are frozen here. This packet must remain source-only and unactivated until that boundary is resolved; it is not a working native-control claim.

## Comparison, mounts and verification limits

All five proposed preimages are byte-identical in private43ff. Across the 27 original chain snapshots, only `BrnGuiModule.cpp/.h` differ there; the complete 38,037-byte Git comparison patch is retained. Those private changes add real input cases 22/507, shared cache/manager tail rules and retained output delivery, and remove the selective overlay queue/direct drains. They do not recover the missing whole-input-to-view bridge or change the five owner files. Seventeen further transport/provider snapshots were compared by full SHA-256: only the `BrnGameModule.cpp` audio-event comment and the unrelated `GuiEvent<452>` tag specialization in `CgsGuiEvent.h` differ. Their full private images and 2,183-byte diff are retained; the concrete prepared-check/zero-argument scheduler call is unchanged. No private postimage silently replaces the 36ae base.

All three changed implementation TUs and the eighteen other enumerated caller/consumer/provider TUs have one explicit shipping roster entry each in the exact workflow `build_game_exe.bat`; `MOUNT_AUDIT.json` records their lines. No CMake result is used as executable authority and no mount change is needed for these two new methods.

`BINDINGS.json` binds full raw pre/post SHA-256s and Git preimage blobs. `STATIC_AUDIT.json` records 175 source/evidence consistency checks, including the single renamed float, original diagnostic, private preimage equality, pointer-width witness, whole-byte patch regeneration and shipping entries. These are static receipts only. No C++ compiler, fixture, provider import/evaluation, build, CI, game, IDB opening/export, production source edit, Git mutation or registration inventory change was performed. Fresh review, hosted validation, caller integration and any later behavior-specific run belong to Root.

After the caller boundary is genuinely integrated, behavior evidence must show #0021's chosen value, #0020 apply, the copied four-byte event through both queues, the same live handler scalar, a genuinely newly prepared text slot receiving that multiplier, and its actual glyph-advance/pixels. Keep font, height, transform and caption fixed, use actual Apt dynamic text with loaded fonts and live renderer/command buffer, and restore the default through the same action plus genuine rebuild. A variable readback, event count, allocation success, `fTextWidth` metadata alone, or an arbitrary FLAPT caption is insufficient. No control is marked complete by this proposal.
