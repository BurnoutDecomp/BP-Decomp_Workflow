# Root selection and unresolved outer owner

Original InitMemoryMap82664728 builds a resource whose lane0 is the map image, calls FixUp and installs the initial default allocator. The subsequent Allocators::Construct8266AED8 loads the first bank pointer from the fixed header at8266AF08 and keeps it in callee-saved r31 while the system/debug/graphics owners execute. At8266AF18 it passes that same pointer to ConstructGlobalResourceMemory. DecFIGS names local `const MemoryBank::Params* lpParams` and the inlined MemoryMapBank::GetParams operation.

The faithful typed selection is:

```cpp
const CgsMemory::MemoryMap* lpMap = /* the already-fixed canonical map image */;
const CgsMemory::MemoryBank::Params* lpParams = lpMap->GetRootBank()->GetParams();
```

The comment is an evidence placeholder for the existing map owner, not an executable adapter or a proposed replacement allocator/map. Current MemoryMapImageInitializer and InitMemoryMap already own the native typed image/fixup; neither is called or changed by the new accessor. GetRootBank returns the real first bank pointer and does not fix the map, mark it ready or select a child.

Original outer phase order is:

1. PrintConsoleMemory("Pre-allocators construction").
2. DefaultLinearAllocator::CheckRenderwareBudget82661AF0.
3. Select root Params from the fixed map as above.
4. ConstructGlobalSystemMemory82666990.
5. ConstructGlobalDebugMemory82666A80.
6. ConstructGlobalGraphicsMemory82666B70.
7. ConstructGlobalResourceMemory82666C58 with the preserved root Params.
8. ConstructChildAllocators82666D48.
9. SetDefaultAllocator to the genuine public GlobalSystem wrapper.
10. PrintConsoleMemory("Post-allocators construction").

The next dependency boundary is precise: budget-check82661AF0, system82666990, debug82666A80 and child82666D48 bodies, plus their genuine heap/global fields, are unavailable in the current canonical header/body. The existing native anonymous debug heap/getter and native default allocator do not implement those original owners. No empty definitions, declarations posing as availability, substitute default or callback are supplied for them. The full outer constructor and its startup call stay unactivated.

The older31ae source's backing assertion in GetResourceAllocator is not reused as authority. Current primary caller8266D5AC..5BC obtains the wrapper address directly with no resource-backing assert there, while the separate Debug allocator assertion is visible at8266D5EC..D640. The recovered getter performs the attested address return; actual wrapper DoAllocate enforces its own backing precondition.
