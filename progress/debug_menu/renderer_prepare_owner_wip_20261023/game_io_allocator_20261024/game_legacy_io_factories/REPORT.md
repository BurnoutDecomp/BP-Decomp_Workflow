# Game legacy IO factory owner checkpoint

This four-path proposal restores the game's original `ModuleSingleBufferedTemplate<InputBuffer, OutputBuffer>` inheritance and the real by-value legacy IO pair. The existing generic template already owns both private typed buffers and implements all six virtual lifecycle hooks correctly for this pair. No template algorithm or storage is replaced.

The original input has no members. The output owns a `BrnResource::GameDataIO::RequestInterface<1024>`. Its request queue begins unconstructed through the genuine protected `BaseVariableEventQueue` C++ constructor. That constructor initializes only `mbIsConstructed=false`; it does not clear the payload or make any resource ready. The input/output `Construct` and `Destruct` methods are truly empty in ARTIST; their `Prepare` and `Release` methods truly return one. These are original legacy semantics positively bound through the actual game vtable, rather than placeholder completions for the newer IO stack owner.

The old `InputBuffer : IOBuffer` and `InputBuffer::DestroyBuffer(IOBuffer*)` attribution is incorrect. ARTIST `0x827E3100` is the template's `bool DestroyInputDataStructure(DataStructure*)` virtual: it receives `this` in r3, moves the supplied structure r4 into r3, calls the shared empty destructor, and returns one. The proposal removes that invented payload method and obtains the real hook from the existing typed template. The identity/inventory is not modified by this packet.

`SOURCE_MANIFEST.json` binds every full pre/post byte image to source `702d242bd0e99a8510ef09bbc42b0a316956ac9b`. `COMPOSITION_183_CONTINUITY.json` additionally proves the four preimages and all frozen canonical source providers unchanged at source `183ca9c9a23aa93fe9a1bdf1e47b02e84f395f1e`. The build evidence is separately bound to parent `2ca227af02ca882a2fd9681ce3443e283df64121`; it must be rechecked if Root composes against a changed shipping list.

## Availability and integration boundary

The shipping path is `tools/build/build_game_exe.bat` followed by `compile_exe.py`, which consumes the response file and deduplicates its explicit sources. Its exact list has 3021 source lines and 3002 unique paths. `BrnGameModule.cpp` is included; `BrnGameModuleIO.cpp` is absent. The game CMake list does include `BrnGameModuleIO.cpp`, but CMake is not authoritative for the shipping executable. This packet makes **no mount change**, and the eight real IO definitions remain a shipping link dependency until Root reviews and mounts them. No linker/build success is claimed.

Changing the game's base changes its actual object storage and virtual dispatch when composed, and therefore requires a full affected recompile and fresh review. It preserves every existing game method body, including the active two-argument/stage-7 path. It adds no call to original staged Prepare, no fake new-module classification, no renderer registration, and no allocation/sky-dome/thread policy.

The queue constructor is generic and affects birth initialization of every `VariableEventQueue` instantiation that uses the base. Existing explicit `MarkUnconstructed` calls are unchanged. This source-wide effect is genuine recovered initialization, but must be included in review rather than described as game-local.

The original table binds exactly the six protected virtual hooks. The optional nonvirtual `ClearInputBuffer`/`ClearOutputBuffer` APIs are not used by the current game source. This packet does not add the two legacy `Clear` methods or output accessor solely from unused DecFIGS declarations. Their original target/caller evidence must be recovered before those APIs are used; do not claim every template convenience API is now available.

The game C++ constructor at `0x827E5F00` establishes the main game vptr, the output queue birth flag, and the secondary `IThreadClass` vptr. The secondary vptr at `+0x640` belongs to `IThreadClass`, not `GlobalCpuMonitors`; `AutoTestManager` starts at `+0x648`. The compiler owns native alignment and pointer widths. There are no literal layout accesses or forced console padding in this proposal.

## Remaining owner work

The GameData original Construct order still needs a separate complete typed owner: resource construction, AttribSys, GameTalk, debug interface, LiveUpdate, resource lists, and final original classification. Existing native Construct creates and owns the working 0/2 allocation roots and dispatch resources. Replacing it or inserting new member calls next to its earlier AttribSys call would not preserve the original ordering. The preceding renderer seed packet's `CURRENT_PC_OWNERS_702.md` records these concrete allocation, audio, sky-dome, publication and thread hazards.

All writes for this checkpoint are private proposals/evidence. No source checkout, Git ref/index, inventory, build, test, CI, native executable or input was changed. Root remains the sole reviewer coordinator, publisher and integration/launch owner. Debug registration counts remain 50 verified / 7 no-ops / 1298 pending of 1355.
