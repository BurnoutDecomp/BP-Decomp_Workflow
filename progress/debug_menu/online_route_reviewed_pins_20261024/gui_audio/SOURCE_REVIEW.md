VERDICT: pass

The exact two-path correction closes A1 by moving the unchanged audio specialization into an existing mounted TU and removing its former definition. The resulting canonical audio/retained-inbox composition receives a bounded source pass. This establishes static source availability and definition uniqueness, not a successful compilation, link, fixture or native execution.

| Binding | Exact value |
|---|---|
| Source | `25d8523608e81df090ff123970cb25fbcb650708` |
| Source tree | `4403548b43b3ecf072e03c35aca866911cc0971b` |
| Parent/base | `a761bf9fc3b1bc960bc77d3f0f36c0a0c34e5f7c` |
| Paired workflow | `b2c191caccb5d3362506c3661a9567630d41221d` |
| Workflow gitlink | Exactly the source above |
| Root input seal SHA-256 | `8347df02f20ff58666345d8027d1f903eb72437a8747eb8f85e8bca91d8d9be2` |
| Author bindings SHA-256 | `999230dcfdde44cfbb7a85715ea4603dee93a9370f5e35acd9c219eaed2af051` |
| Author patch SHA-256 | `4cc4864fdba64a4dc8f761cd95cf7bf140b3f21945bd3ba8b856e9fede662f46` |
| New BrnGuiEventTypeDefs.cpp SHA-256 | `52b2581ff9268b5a62676d1714fc0546ddf11d63bfd68e7d54fbb9f8313a6b6b` |
| New generic-instantiation CPP SHA-256 | `12fc4d955a1c6ef432c64a92e017f5ccfb92e6cd02e15c4dea1d6388839b8ab2` |

All nine packet files match Root's frozen seal. Both complete preimages match the exact a761 Git blobs, both complete postimages match the exact new source blobs, and the patch reproduces byte for byte from those images. The full source diff contains exactly these two paths. The paired workflow's build-source list, compile driver, flags and ordered include roots are byte-identical to the metadata bound by the prior family review. The author's build evidence names workflow2bd1, and its build-file SHA-256 independently matches the actual new workflow's file: `05a4579c12341f241cc3d7e66554ae01a6cc36fb5ab72aef7cd481949be7e792`.

**A1 is closed.** `src/GameSource/Gui/BrnGuiEventTypeDefs.cpp:15–16` includes the canonical payload header and shared StateInterface declaration. After the existing BrnGui namespace closes at line581, a top-level CgsGui namespace defines the explicit specialization at lines586–593. The new definition is unconditional, has the same qualified member name, void return and nonconst audio-reference parameter, and legally uses the member's output queue. It is not an anonymous-namespace helper or a separate replacement publisher.

The actual shipping build_game_exe.bat mounts this exact CPP once, at line4145. It still mounts the ordinary CgsGuiStateInterface.cpp at4902. The new symbol is consequently defined by a source file already in the shipping response-file set. The unchanged compile driver derives its object plan from that set at compile_exe.py:643/668 and feeds those objects to the link at728–739; this inspection did not run the driver.

The former definition has been removed from `CgsGuiStateInterface_OutputGuiEvent_Inst.cpp`, which remains unmounted. All 65 other generic explicit-instantiation lines remain byte-identical. A source-wide search of all 53 files containing the audio type finds exactly one explicit specialization definition, at the new mounted home, and the unchanged shared-header declaration at CgsGuiStateInterface.h:296–298. A separate complete source filename-reference search finds no source inclusion of either CPP. Thus this move adds no second definition through an included CPP, and the old unmounted TU cannot contribute a duplicate audio definition if separately mounted later. This is source-level one-definition-rule inspection, not an observed linker result.

The complete moved function is exactly 377 bytes in both old and new homes, SHA-256 `5381eaadde11fdbdb8280c96a050844dbdf479483e193f6beceef525e1c9d86e`. Removing only the added include and appended namespace block restores the entire payload CPP's exact preimage. The existing Construct and every other payload/accessor body therefore remain byte-identical. No queue, event, type, flag, initialization or consumer behavior was added by the move.

The retained ARTIST publisher `82436890` was read directly again. Its mangled QAAX return is void; r3 is StateInterface and r4 supplies the event. It copies100 bytes, writes wrapper words100/457/12, and calls AddEvent on channel40 with record size112 at `824368B0–68D8`. The new body still instantiates the existing `GuiEventWrapper<GuiAudioTriggerEvent,40>` and calls that same queue interface. The selected payload remains100 bytes/alignment4 with fields at0/32/36/68 and runtime id457. The selected wrapper captures sizeof(T), derived GetEventType and the payload offset at CgsGuiEvent.h:180–210. Its stack lifetime is sufficient because selected CgsVariableEventQueue.h:460–466 copies the supplied bytes synchronously. The explicit specialization declaration remains visible before all uses, so these calls select the audio specialization rather than falling back to the unchanged primary template.

All 45 state audio call expressions across34 mounted TUs are unchanged, including39 explicit and six deduced calls. Every one of those TUs directly includes the shared declaration header; their actual build mount rows are captured in STATIC_CHECKS.json. The complete call inventory is identical to the prior review. Counts are source expressions/TUs, not registration sites or runtime witnesses. The 65 generic instantiations remain unmounted and their existing unrelated generic payload semantics receive no new approval.

Actual providers were resolved against the exact shipping include order and captured. Fully qualified payload, StateInterface, GuiEvent, variable-queue and GUI resource-IO includes resolve under the first `b5-decomp/src` root; `types.hpp` supplies s32 as int32_t and the empty Event/tag/header definitions are unchanged. The actual `rw/rwcore_structs.h` candidate is `vendor/renderware/include/rw/rwcore_structs.h`, SHA-256 `875f826a99a90e52898df2968a39c74160314646b4a822f2105951ae46970210`; no SDK mirror or another branch's provider was substituted. The move introduces no new allocator operation or runtime provider. This provider inspection supplies no compilation or vendor-wide parity credit.

**Resulting audio/inbox composition.** All54 source snapshots from the sealed family review were compared with this new source. Only the two correction files differ; every producer, canonical payload/header, raw callback, CodeTicker publisher, sound decoder/sink and GUI retained-inbox source remains byte-identical. All other captured providers are likewise unchanged. The prior reviewed contracts therefore compose directly:

| Route or contract | Exact retained source evidence | Disposition |
|---|---|---|
| State output | New owner CPP:586–593; shared declaration h:296–298; payload h:113–148 | Pass: wrapper112 on channel40 carrying100/457/12+payload |
| Raw callback and CodeTicker | BrnGuiModule.cpp:2396–2416; InGameMessageRenderer.cpp:1534–1537/1600–1603 | Pass: raw457/100, with no extra channel40 header |
| Sound copy and sink | BrnSoundLogicModule.cpp:529–564; actual CgsMessage.h:52–168; PresentationEffect.cpp:265–297 | Pass within the retained changed contract: message6/116 with an exact100-byte body copy and matching named fields |
| Genuine HideDriveThru | GuiDemangledEventTypes.h:239; game bridge free-roam CPP:111–117; GuiCache.cpp:2608–2633 | Pass: distinct201/8 remains unchanged |
| Old audio201 compatibility | SoundLogic CPP:539–549 | Pass as retained PC compatibility: exact112 bytes with words0/201/12, body at+12; event201/8 is rejected before header access |
| Retained input/output | GuiModule.cpp:2538–2546,3371–3382,3695–3696,4524–4539 and common cache delivery2841–2842 | Pass within reviewed inbox scope: wrapper unwrapping, whole-output retention, next-input append/clear and common delivery unchanged |

The sound457 arm retains its prior scope: exact canonical wrapper112 or a raw prefix of at least100 bytes; this is not a new malformed-wire validation claim. No other actual audio producer/layout or consumer was changed by this two-path correction. The earlier G1 payload/identity collision remains closed: callback output is457/100 and cannot enter the genuine201 cache arm as the former201/112 audio record did. The new source adds no per-ID filtering or dropped-input workaround.

The earlier exact-a761 FAIL/A1 report remains immutable: REPORT SHA-256 `3783a05731766fd17e19dc69e02ef1777a8114be80c47c828d31521f146045c4`, SEAL `7f3c8b338bc5c25aacd469375604bac4f96ab80fd0b1232417ae251d925757e3`. All197 files in its original author packet remain unchanged. The original exact4c7 FAIL/G1 report and seal also remain unchanged (`ace7a51a09406e1b2f2414de3d5b1c1960d6cf9baa2c6289f43524e539846119` / `8238d54ea831bf44664f7886a61c390b89edae1c1fe20b9b736c2c77ff458d70`). This new pass applies to the exact corrected composition, without retroactively editing either failure.

No further source blocker was identified within the correction and previously bounded audio/inbox scope. Full ModelIO recovery, cold route loading, original complete Module/Prepare/Release activation, other flagged GUI/sound behavior, individual controls and native readiness remain excluded. The separate source-extracted fixture was not compiled, run or approved here. No production edits, refs/index writes, compilation/fixtures, build, link, CI, game/input, IDB opening or additional agents were performed. Root owns all integration/publication and runtime work.

A1_STATUS: closed in exact25d8523608e81df090ff123970cb25fbcb650708

COMPOSED_SOURCE_VERDICT: pass (bounded audio family and retained inbox)
