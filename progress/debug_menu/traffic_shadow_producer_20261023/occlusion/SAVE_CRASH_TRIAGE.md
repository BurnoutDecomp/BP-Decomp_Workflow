# Failed occlusion smoke: pre-toggle state-export crash

Exactsource7e455d, hosted40018949056, exe434e24abbcc0d813f02e5ac21b537f2e7f72d7ced6a4659f64987d469cc526a1. Originalrun remains FAIL. No occlusion toggle executed. The run reached ordinary free roam; the last retained frame shows a rendered world and console input.

The private log reports `Component not found`, then an access violation readingnull in CgsCore::StrCat (module+0x4E100), called by ScriptInterface::SaveState+0x285. `initial.txt` contains active DLC/RaceCar/World components and ends after DLC's `Leaderboards - Stunt run` variable.

The source-supported explanation is the original DLC unnamed25th feature slot. ARTIST DLCDebugComponent::Construct0x826627F8 zeroes25name pointers but fills only0..23; OnActivate0x82662B40 loops25 and passes the lastnullname through register helper0x8282D640. VariableManager::RegisterVariable0x82829A80 stores the name without a null check. ScriptInterface::SaveState0x82832660 appends each saveable variable's name with StrCat without a null check. These behaviors match current source. A generic SaveState/null-name skip would change the original leftover behavior, so no such source patch is proposed. The runtime stack and final serialized row fit this chain; no live variable-pointer dump was taken.

The component-lookup failure is distinct: RendererModule is a valid short key, but the actual renderer debug component registration lifecycle is not yet established on the host. See renderer_debug_component_lookup_20261023/REPORT.md. A separate Solowner audit now checks currentrenderinstance, virtual/templatecallcoverage, original5argPrepare andallocatorownership.

Next bounded case must use targeted alias/value readback plus existing engine-state probe rather than whole-registry SAVE, and only after the Renderer component lifecycle is correctly integrated. Preserve initial/failed artifacts and use a new run folder. Normal24 files retain hashes and mtimes, zero owned games remain, helpercleanup andprivateprofile restoration completed.
