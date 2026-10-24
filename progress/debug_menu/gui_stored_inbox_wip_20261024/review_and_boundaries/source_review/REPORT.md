Fresh independent source review, 2026-10-24. One reviewer reviewed all three requested packets sequentially from their supplied entry points. Root remains the integration, publication and launch owner.

| Bounded packet/context | Decision |
|---|---|
| GUI stored inbox, source `4c7c6ba2f97533315d5663d22499042cb007df31` | **FAIL — G1**, audio output has the wrong identity and representation for generic input replay. |
| Graphics wrapper alone, source `65a8992bdfc29e2ba7c92e4024a965a653a6af27` | **FAIL — G2**, original private constructor is declared public. The eight recovered bodies otherwise pass this bounded inspection. |
| Resource continuation on graphics, source `eb4dcbb1e7810f71dc16cd50e49707b2a54bc9b9` | **PASS**, including its explicit G2 correction and the final seven-path composition. |

BATCH_VERDICT: fail

A pass here means source WIP approval for the stated bodies and composition only. It grants no compilation, link, new mount, global initialization, registration completion, native adoption, activation, runtime feature/control, asset-schema or native-readiness credit. GUI and resource sources are separate branches; this report does not describe a combined GUI/resource commit. The pending callback correction and `native_graphics_adoption_prerequisite_20261024` are outside this review.

Exact contexts are:

| Context | Source/tree | Parent | Paired workflow |
|---|---|---|---|
| GUI | `4c7c6ba2f97533315d5663d22499042cb007df31` / `d80cdb4998eeea85613c17269b709506d18d32a1` | `d3ec7d2dd65a37b489d1dbf61a53b9ce030385ee` | `94285e77a7ea05dae14e781340a91bf5a6ce22d9` |
| Graphics | `65a8992bdfc29e2ba7c92e4024a965a653a6af27` / `9d7974ffa8770b1f5634fda7061cb4674e8d2623` | `02c63ea7ed5dfb3b43dbaeb959a2d23f3861db6b` | `53098be903b5abc42b7cf2b70951cbd9f4509615` |
| Resource final | `eb4dcbb1e7810f71dc16cd50e49707b2a54bc9b9` / `a5c3b9cfe6d9cefd3d9c5eed1878fc422ac90d7f` | `65a8992bdfc29e2ba7c92e4024a965a653a6af27` | `ade2096e15a3f6663a432ed0d27dfa3ee6dd0e02` |

All three workflow gitlinks independently name the stated b5 commit. Every full pre/post image matches its manifest and exact Git base/target. Both GUI preimages also independently equal delivered `d3ec7d2dd65a37b489d1dbf61a53b9ce030385ee`, although the author packet originally binds them to `edca934dc502f71f64ad873cdd386afe5e3eeeb2`. All three patches were reproduced from the complete pre/post text. Both sealed allocator packets, both ownership-context seals and all seven earlier review seals verify without mismatches. No earlier failure was rewritten.

| Packet | Manifest SHA-256 | Patch SHA-256 | Input seal SHA-256 |
|---|---|---|---|
| GUI | `bf39c76f80f4651f13a13405d44460ec378c9d791f892eff37a88c24439355df` | `30e87cb9a0deea57bedc1ec468af0ac1d8cd71b857a3e34c718d94f8af832d2b` | Unsealed author packet; every copied input is bound in this review. |
| Graphics | `0517a127a14bdf8908528dd16ec2c5e085a092be817f8615a6b57c8f60f27961` | `bf7ccccb881638ec14a56576454c2961f4db5be7d9dd2e2d23cc6c66804e58c4` | `4ae74df6dba0c45623c2ffe627be24b14b7a9ed9fd54369a85343e56617acec6` |
| Resource | `122fb3993766e271de4036e2f896c631e5a148cead355b871020c6881b686b52` | `16ad162c003180e42880de74c6a1692040870d38d41c04498941d47e8391dcec` | `7032f42d91585d3e26f88aeddca6ff7cdbe7ca75d0ff3d0b1ef931c6b2f33d43` |

Complete per-path SHA-256 values, Git blob identities, source comparisons, frozen evidence, providers and seal checks are in [BINDINGS.json](BINDINGS.json). Independent shipping selection, preserved-body hashes, raw instruction/root decodes and earlier-seal verification are in [STATIC_CHECKS.json](STATIC_CHECKS.json).

1. GUI stored inbox

VERDICT: fail

G1 is a concrete source-composition defect. New input case22 calls the existing `FlaptSoundTriggerCallback` at [BrnGuiModule.cpp:2538–2546](composed/gui_4c7c/src/GameSource/Gui/BrnGuiModule.cpp). That callback publishes `GuiAudioTriggerEvent` at lines2396–2416. Its actual definition is `GuiEvent<201>` with a 12-byte PC header plus a 100-byte payload, totaling112 bytes ([BrnGuiEventTypeDefs.h:107–130](providers/gui_4c7c/src/GameSource/Gui/BrnGuiEventTypeDefs.h)). The callback can also produce this record directly from FLApt.

The new complete-output copy at `BrnGuiModule.cpp:4539` stores that112-byte/type201 record. The next update appends it to GUI input at3695 and clears the stored source at3696. The new common cache tail at2841–2842 then calls `GuiCache::RecEvent(event,201)`. Its existing case201 is **HideDriveThru**, which copies the first eight bytes as a `CgsID` and can mark the matching drive-thru hidden ([BrnGuiCache.cpp:2608–2633](providers/gui_4c7c/src/GameSource/Gui/BrnGuiCache.cpp)). The audio record's PC header is not that ID. Manager/observer input delivery at2855–2859 also receives the wrong event identity. This is a wrong dispatch even when no drive-thru ID happens to match; no runtime hide or crash is asserted here.

ARTIST establishes the canonical replacement contract, rather than merely suggesting another number. `FlaptSoundTriggerCallback`825112B0 calls the audio publisher at825113DC. That publisher8250BE70 sets `r6=0x64` and `r5=0x1C9` at8250BF0C/10, then calls the actual variable queue AddEvent at8250BF1C: **100 raw payload bytes, type457**. These complete primary exports are frozen under [additional_primary](additional_primary/.ida-exports/BURNOUT_X360_ARTIST.XEX). Existing sound input already distinguishes typed201/112 from raw457/100 ([BrnSoundLogicModule.cpp:529–549](providers/gui_4c7c/src/GameSource/Sound/Module/LogicModule/BrnSoundLogicModule.cpp)). Renaming only the outer key to457 would feed the header as audio payload. A correction must reconcile the producer's wire representation and actual consumers. An ID filter or special discard would not restore the original generic owner. No unseen correction is included in this verdict.

The rest of the requested affected-chain inspection gives the following bounded results:

| Area | Source/primary result |
|---|---|
| Real stored owner | Derived Construct actually calls `CgsGui::GuiModule::Construct` at line900. The real base Construct calls `mStoredGuiEvents.Construct()` at provider `CgsGuiModule.cpp:32`, matching82857014/1C. C++ construction only marks its flag unconstructed, matching827E550C/14. It is the protected18432/16 member, not a new surrogate queue. Derived Destruct calls the real base at2274, whose queue Destruct is at provider124. |
| Per-update lifetime/order | Entry3690–3697 appends after the caller's existing input, then clears; ARTIST82527D58–74 does the same. ViewIO events are copied at4524 and retired at4532; complete module output follows at4539, matching8286051C–28 and82860564–78. Fixed queue storage supports the debug suffix cursor at3743–3761; cache64's direct renderer handoff is excluded from that suffix. |
| Observer/cache duplication | Old channel40/profile/custom-renderer/ViewIO immediate fanout and the seven-ID overlay subset are removed. The common input tail2841–2859 handles cache, selected tracker IDs, manager and subscription-filtered observers. Fourteen/sixteen retain their separate ModelIO seat. This removes those duplicate routes, conditional on correct event identities; G1 prevents approval of the complete replay stream. |
| View/custom-renderer order | The helper copies manager output first, then ViewModule output at4648–4649. It runs after View Update4423 and before manager Update4443 clears its event queue. The real manager body clears at `CustomRenderer/BrnCustomRenderer.cpp:669`, matching82450918/1C. ViewModule clears its own output at provider263. ViewIO records precede the final copied module-output batch, as in the base bridge. |
| Same-step consumers | Existing game frame owners copy the completed module queue into the substep output and retain it for game/director/sound/GameState consumers before step-boundary clear/IO teardown. The proposal does not destructively transfer that queue. The ARTIST loading caller's virtual GUI Update823F2A0C precedes sound823F2A2C and output/input destruction823F2C48/58. Frozen `BrnGameModule.cpp` preserves the corresponding active PC ownership. |
| Channels | Channel40 still unwraps payload size/type/offset to the canonical output queue at3371–3382, matching8285E568–57C. Channel42 remains the interpreter's separate next-update stream, whose original private queue append/clear is8285F6A0–B0. It is not copied through module output a second time. |
| Autosave/flow timing | Removed late356/141/144/507 shortcut handling now runs through input before consumers. Case356 at2797–2827 precedes the existing autosave tail3955–4028. Case144 at2534–2535 runs before controller Update3860, like ARTIST82528AAC before82529EF4. A request emitted by a flow on updateN returns onN+1; this preserves the requested Leaving/RunFsm input timing without proving a complete flow transition at runtime. Existing post-base514/515 handling remains a same-step output consumer. |

The ModelIO boundary remains real. The selected PC Update bypasses the original inherited Update. It consumes notifications14/16 through ModelOutput/cache/manager/controller/effects at3813–3877, with a separate ViewInput registration route, then clears them. It does not restore the complete original `BridgeFromModelToOutput` request/GuiOutEvents/load-notification-to-stored chain. Copying those notifications again would duplicate present consumers. The existing selected Prepare/Release also remain PC lifecycle ports; the original inherited queue Prepare/Release stages are not thereby restored. Construction, per-update persistence and final Destruct are accounted for, but this review gives no complete original-module or release/reprepare parity credit. G1 blocks even the narrower proposed complete module-output/ViewIO replay.

2. Graphics wrapper alone

VERDICT: fail

G2 is a declaration-shape defect in exact65a. [BrnResourceAllocator.h:140–151](composed/graphics_65a/src/GameSource/Resource/BrnResourceAllocator.h) declares `Allocators::ConstructGlobalGraphicsMemory()` under public access. The frozen DecFIGS declaration has `private:` at [evidence header:302](inputs/graphics_linear_wrapper/evidence/DecFIGS/GameSource/Resource/BrnResourceAllocator.h), followed by this method at310 and the resource constructor at313. ARTIST82666B70 attests the method. Public access unnecessarily exposes an internal initialization phase and fails the requested DWARF shape check. The resource continuation corrects this exact declaration to private; the original packet remains failed and immutable.

The eight recovered definitions were independently compared to the actual assembly, declaration shape and selected providers:

| Definition | Result |
|---|---|
| Game `LinearResourceAllocator::Construct(rw::LinearResourceAllocator*,const char*)` | Stores the two genuine members, as inlined at82666C48/4C; no backing/lazy policy is added. |
| Free `GetGraphicsAllocator()` | Returns the real global game wrapper. ARTIST8240A7A4–7C0 binds that object, distinct from the native anonymous RW arena. |
| `ClearResource(Resource&,const ResourceDescriptor&)` |826647B0 loops exactly five lanes, tests each pointer and fills exactly its descriptor size with0xCD. Source435–440 matches. |
| `Allocators::ConstructGlobalGraphicsMemory()` body |82666B70 sets capacities0=0x640000 and2=0x1D00000, both descriptor alignments4096; obtains the real RW storage descriptor; allocates only0/2 with4096 alignment and flags0x20000004/0x20000404; clears the storage requirements, initializes with the original capacity and constructs the wrapper named GlobalGraphics. Source445–460 matches. |
| Game `DoAllocate(const ResourceDescriptor&,const char*) -> Resource` |826651C0 uses hidden Resource return inr3, this inr4, descriptor inr5 and name inr6. Source465–542 returns Resource by value, checks unsupported lanes3/4/1 in order, then backing; computes available before allocation; retains optional allocation-name logging, both formatted Size/Free lines for every requested lane, real virtual allocation and pointer/alignment diagnostics. Formatting uses256 bytes, exact five primary strings and unsigned MB/KB/byte decomposition. Failed allocation does not skip alignment validation. Zero alignment is not normalized, preserving the original failing operation at82665618/1C. |
| Game `DoFree(const Resource&)` |82665708 checks unsupported pointer lanes3/4/1, then backing, then invokes its real backing DoFree; source545–561 matches. |
| Game `DoFreeDisposable(Resource&)` |82661F10 checks backing and then always asserts that disposable allocation/free is unsupported. Source564–576 does not forward to a backing free. |
| RW `GetAvailable() const -> ResourceDescriptor` |82BBC840 passes capacity and usage to subtraction82B63E50. Source `rwcore_alloc.cpp:539–545` copies capacity, subtracts only five unsigned size words and preserves alignments. No underflow clamp or extra accounting is introduced. |

Primary bytes independently establish the initial resources/internal pointer as zero and wrapper as `{vptr,0,0}`. The graphics descriptor data initially has first lane{0,0} and the other four{0,1};82C5FEE8 sets the first to{0,1}. The actual Resource constructor nulls all five pointers; BaseResourceDescriptor's real provider constructs{0,1}; static initialization gives the wrapper's two pointer members their initial zero state. No guessed ready backing is installed.

Shipping metadata was independently read from each paired workflow. `build_game_exe.bat` consumes canonical `msvc_includes.txt` and hands base/build responses to `compile_exe.py`. Ordered candidate inspection resolves `rw/rwcore_structs.h` only to `vendor/renderware/include/rw/rwcore_structs.h`: GUI SHA875f826a99a90e52898df2968a39c74160314646b4a822f2105951ae46970210, graphics/final SHA3fcc7fa2d41775d3219fb89e2f7284c5dce502796788c03b937834cd1e45e71c. The actual static `GetResourceDescriptor`/`Initialize` declarations and definitions are used; no SDK mirror or parallel allocator class is substituted. XPhysicalAlloc's four unsigned-long C-linkage arguments match the existing mounted PC provider, whose aligned-allocation implementation is preserved. Existing shipping list entries were inspected only; no mount/build result is inferred.

The renderer's only edit is the typed wrapper assignment at `BrnRendererModule.cpp:1223`. Its backing is still uninitialized, and the unchanged MemoryUsage queries require that backing. The anonymous256KiB `Allocators::GetGlobalGraphicsAllocator()` arena, debug/GameData helpers and WorldDispatch renderer code are preserved. No new call initializes either original global owner. The wrapper address is not readiness.

The separate ownership analysis is context only. Its immutable base-order correction is retained:8240A7A0 is an empty ICF target; typed binding ends at7C0; EffectsArbitrator and shader frame Constructs/stores precede the real ModuleSingleBuffered::Construct at8240A800; renderer state stores follow at808–830. Adding a base call at entry would not reproduce that order. Neither analysis nor this packet completes registration, buffers, sky, threads or native integration.

3. Resource continuation

VERDICT: pass

The four exact postimages compose on65a, with two overlapping allocator paths. Their ordered union is exactly seven changed paths against02c. All five graphics postimages survive in finaleb4 except the two explicitly continued files; all eight graphics bodies are byte-identical there. The genuine native debug, GameData-general and256KiB graphics helper bodies also remain byte-identical to02c. These comparisons and hashes are in STATIC_CHECKS.json.

The final header moves the graphics constructor into `private:` at161–163, closing G2, and adds the resource constructor there at164. It uses the actual `CgsMemoryBank.h` Params type and genuine free getters/friends. The added three original definitions pass:

| Definition | Source/primary result |
|---|---|
| Free `GetResourceAllocator()` | Source591–593 returns the actual global wrapper. ARTIST8266D5AC–5BC materializes that wrapper address directly without a backing assertion there. Its later DoAllocate performs the backing validation. No alias, lazy initialization or native helper is substituted. |
| `ConstructGlobalResourceMemory(const MemoryBank::Params*)` | Source597–615 matches82666C58. Loads at+0x28/+0x30 select unsigned sizes0/2, add0xFC0000/0x200000 with32-bit arithmetic, and set descriptor alignments0x10000. Both XPhysicalAlloc calls use the computed storage requirements, physical address-1, allocation alignment0x20000 and flags0x20000004. The0xCD clear uses that storage descriptor; Initialize receives the genuine capacity descriptor; wrapper Construct receives the returned backing and GlobalResource name. No invented guards, budget choices or fallback are added. |
| `MemoryMap::GetRootBank() const` | Source `CgsMemoryMap.cpp:135–137` returns `mpBanks`. DecFIGS h72 names this exact const accessor. Independently decoded instructions83EB0024 at8266AF08 and83FF0024 at8266D5B4 are lwz from map+0x24. The fixed header's first bank is the root, whose GetParams has no subobject adjustment. Ordinary GetBank(0) selects child row1, not root. No sentinel or map-to-Params cast is introduced. |

Raw root row82F2A7C8 independently decodes to Root Bank, parent-1, bank0, sizes{117440512,0,212860928,0,0}; the added sizes are133955584 and214958080 before RW object storage. The real Params shape places sizes at+40 and keeps the X360 five-lane84-byte row. Resource birth bytes independently show five null resource pointers, null internal backing and `{vptr,0,0}` wrapper;82C5FF68 makes descriptor lane0{0,1}, matching the four existing data lanes. Those initial values are distinct from the recovered, uncalled body.

Original outer selection/order is independently visible at8266AED8: print, CheckRenderwareBudget, preserve root Params inr31, system, debug, graphics, resource with that same pointer, child allocators, then install the genuine GlobalSystem wrapper as default and print. The current continuation supplies neither that outer constructor nor the missing budget/system/debug/child owners. It adds no unresolved calls or trap bodies for them. `InitMemoryMap` still owns typed-image fixup; the new accessor does not initialize/fix/activate it.

Final resource/graphics composed source at exacteb4: **PASS, bounded source WIP**. Standalone graphics65a remains **FAIL**, and GUI4c7 remains **FAIL**. There is no pass for a merged GUI/resource branch, original full GUI module, original full allocator initialization, native adoption or renderer registration pipeline.

Read-only Git inspection, full artifact comparisons, assembly/DWARF/provider reading and static hashing were performed. Writes were confined to this new review directory. No production source, ref/index, earlier packet/report, normal package, build/config/profile/log was changed; no C++ compilation/test, CI, game/input or IDB opening was performed.
