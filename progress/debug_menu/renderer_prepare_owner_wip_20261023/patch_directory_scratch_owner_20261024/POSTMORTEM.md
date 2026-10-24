# Static self-review

| Check | Evidence/result |
|---|---|
| Callback ABI |828F0BA0 saves context r3; no other incoming argument is consumed. EAThread RunnableFunction supplies the one context. Return zero remains native-width intptr_t. |
| Allocation |828F0B9C–BFC: size6590, alignment10, other descriptor lanes0/1, null name, retained allocator's DoAllocate. Existing real helper has the same contract. |
| Pointer field |828F0C18–1C extracts Resource lane0 and stores it+89C;0C30 reads it into the free record. It is not an integer count. No dereference requires a guessed record type. |
| Scan call | Existing current-patch-folder/empty-subfolder source invocation is retained; no new scanner filter or path behavior is introduced. ARTIST supplies the current patch folder and820046A7 address. |
| Free |828F0C2C–60 zeros five target pointer lanes, assigns retained pointer to lane0, dispatches allocator DoFree at virtual+14. Native Resource's actual constructor and typed DoFree supply that operation. |
| Completion order |828F0C64 loads the old index before0C6C's mbPatching=false;0C70/74 store old+1. The proposal captures the index before publishing false. No extra null clear is added. |
| Static helper | SearchFolder call r3=dest/r4=256/r5=source and GetPhysicalPath prologue r17=r3/r18=r4/r29=r5+7 prove static. Its prior body remains exact; a stale r3 return is not used to invent a return type. |
| Preservation | Removing the recovered callback body and restoring the old body reconstructs the complete prior CPP. Constructor/table recovery, AddPatch, SearchFolder, hash policy and path body are unchanged. Header changes are the pointer, static declaration and corrected allocator comment only. |
| Claims | Allocation owner recovery is separate from full scanner, caller-thread policy, mounts, review, compilation and activation. No gameplay/control credit. |
