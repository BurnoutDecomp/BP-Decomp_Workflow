# Original allocator-list initialization

This three-path proposal recovers the genuine `AllocatorList::Construct`: invalidate all 67 bank-map entries, then set only `mpAudioStreamAllocator` to null. ARTIST inlines it into `GameDataModule::Construct` at `0x82671D30..58`. It does not clear type columns or per-family pointer rows. DecFIGS supplies the method/member names; ARTIST supplies the 67 bound and the actual stores.

The current canonical method performs a broader native reset. It is retained under the explicit `ConstructNativePC` platform leaf, with its **complete body byte-identical**, including interleaved map/type writes, all pointer writes, store order and existing 7/8 populated linear/heap bounds. The current arrays' 8/9 capacities are untouched, and this packet does not add clearing of their spare slots. The one call inside the existing native GameData Construct is renamed to retain that same reset. No original GameData Construct or Prepare path is activated.

Full source base is `d458cd5641a318f8289da22058220f995b6846b5`, parent `9be2fe4490a333a26a226f604c5bac9b05ae5396`. All three full preimages are additionally byte-identical at `183ca9c9a23aa93fe9a1bdf1e47b02e84f395f1e`. The original method also matches the prior source chunk from `e99af2cb6b7f34bc870db2c5f95d35740a9c271e`; that source is reference evidence, while the independently frozen ARTIST assembly remains authority. Prior native-wrapper behavior from e99 is deliberately not copied because it additionally cleared spare slots.

## Ownership and callers

Current GameData owns the real list by value. The original Prepare/CreateAllocators recovery writes that list's genuine fields, and Update publishes a pointer to it through the real GameData output buffer. The initialization method creates no allocator, acquires no bank and establishes no publication/readiness shortcut. Its original unassigned columns may remain untouched until the original producer writes them.

The canonical class is non-template and the method is nonvirtual, so there is no virtual/thunk factory replacing this call. The exact-source type/alias enumeration covers 47 files. The two concrete by-value owners are GameData and the compile-only embed fixture. The only live native reset invocation found is the retained GameData call; the embed fixture still invokes canonical original initialization. Consumer pointer/reference APIs are preserved. These source bindings are recorded as bounded caller evidence, not an execution trace or a claim that resource requests have completed.

Both existing CPPs are already in the shipping source list; the newly recovered method introduces no external symbol dependency. No shipping/CMake mount change is proposed. Source byte checks preserve all existing GameData code except the call spelling, preserve all existing allocator accessors, and preserve the complete native reset body. No compile or runtime validation was performed.

The full original GameData Construct still requires genuine resource construction and its ordered GameTalk/debug-interface/LiveUpdate chain. Its original allocator initialization belongs late in that sequence, after the resident table Constructs. The current native allocation roots, budgets, buffers, sky-dome and thread ownership remain outside this packet. Do not call original Prepare, substitute the native list reset for original readiness, or use this recovery to bypass any resource request.

This is an immutable source-only checkpoint for Root's fresh review/composition. No physical source, Git/index/ref, inventory, build, test, CI, native game or input was changed. Counts remain 50 verified / 7 no-ops / 1298 pending of 1355.
