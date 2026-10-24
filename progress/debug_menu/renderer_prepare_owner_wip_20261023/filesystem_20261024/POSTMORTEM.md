# Source self-review

This is a static walkthrough of the proposed bodies against the primary evidence. No C++ compiler, tests, native input, ledger or Git mutation ran.

| Check | Result and evidence |
|---|---|
| Constructor ABI |829033E4–F0 saves r4/r5/r6/r7. Four explicit inputs; the PS3 fifth input is not guessed into X360. |
| Construction order |82903408–C0 files then streams; C4–E8 allocator/debug/Patch/manager;8290350C–5B8 the two16-entry pools;5BC–658 physical then remap then virtual;65C–874 final count/layout/copy/debug bytes. |
| Base/concrete File state |82903434–458 covers each named store under the one actual lock. No last-operation size, priority or miscellaneous memset is added. |
| Exact physical backing | Both constructed pool counts are16 with s8 free indices. Console4400-byte stride independently fits the declared backing. All indexing uses typed sizeof on the host. |
| Real allocation |828EB9C8–BA34 sets main{size,16}, remaining{0,1}, virtual DoAllocate with null name, and extracts lane0. The selected vendor helper has precisely that contract. |
| Initializer assertions/publication |828F91E0 checks absence44/allocator45, stores allocator, requests0x277B0 original bytes, conditionally invokes the constructor, publishes the result, then unconditionally calls InitInternal. Host sizeof replaces the console literal, without adding a silent success/null exit. |
| C++ subobject order |828F0CAC–CE4 lock, deferred semaphore(NULL,false), Thread for each of8 slots; manager lock last. A named OperationFutex constructor preserves that order before the Semaphore member constructor. |
| Registration-time synchronization |828F9650–96AC locks the existing queue, clears64 used bytes, constructs original count0/intraprocess/empty-name parameters, Init, unlock. No lock reinitialization or invented canonical FIFO reset. |
| InitInternal stores |828E97B0–804 clears8 physical and32 virtual pointers, sets initialized and clears actual path byte276A8. No initialization-thread/releasing reset is invented for the original owner. Native factory retains its prior own scalar values. |
| Physical registration | Duplicate143/capacity154, strict9-byte copy, real operation pool initialization, device/callback/null parent stores before manager unlock. 32-byte thread name and params350/0/false/name plus canonical global wrapper. |
| Virtual registration | Full owned raw instructions828F0CF8–11B4: four assertions196/200/211/232, real Device parent/callback, root walk,8 physical slots, complete opcode8 request including null callback/context and INT_MAX priority. Opcode8's legacy E_OP_DISCONNECT spelling is misleading; existing worker dispatch already implements Connect/Init. |
| Callback shape | FDeviceErrorCallback is bool(EDeviceErrors), not int(int). Six names/values agree with DWARF and target physical call immediates. RW int callback remains exact; typed callback keeps X360's complete one-store/false body with the registration role documented. No PS3 recovery behavior is imported. |
| Remap arguments |828DE6B0 saves/restores only the actual three explicit Open arguments. No inferred r7 argument is added. Parent-forwarding uses real base storage. |
| Assert/copy semantics | Inlined source CgsStringUtils.h65/75: diagnostic then terminator-inclusive copy; strict concat sum<255. No truncation, quiet guard or fallback path. |
| DiskCache platform split |8290386C/70/74 are three stores1/0/1; the pseudocode misses the middle byte. Next PatchManager offset and prior Futex/member extent support the three-byte X360 footprint. PS3 engine storage is not transplanted. |
| Provider/API bindings | Pinned EAThread38576 and tracked vendored RW headers are frozen. PC selected Begin copies its name during the call. Original priority350 remains an explicit unactivated platform limit. |
| Existing native path | Old AddPhysicalDevice body exact after NativePC rename. All manager consumer code from SetDefaultPath onward exact. Native Ensure has exactly two owner call replacements. Native FileSystem ctor/noarg Construct/Prepare/Release/Destruct/RW callback full bodies exact. Queue semaphore creation phase changes are explicitly reported and require review. |
| No ready-by-declaration claim | Unmounted PhysicalX360/Patch CPPs, missing top ResourceModule owner, FIFO-byte proof, original release/delete and PC policy are explicit. Full link/lifecycle readiness is false. |

The earlier merged scratch-pool stage question belongs to the separate sealed `scratch_initpool_lifecycle_delta_20261024` evidence supplement and its original full-game zero owner. This packet does not change that precise Construct body or add a speculative stage seed.
