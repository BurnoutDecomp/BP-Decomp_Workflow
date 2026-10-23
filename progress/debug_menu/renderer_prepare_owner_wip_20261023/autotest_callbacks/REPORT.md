# AutoTest callback continuation

This separate source proposal resolves all seven AutoTest Lua callback bodies and their small helper/DebugManager method dependencies. It builds on the sealed owner postimages; it does not activate the five-stack owner, change active source, or claim compilation, linking, runtime, or debug-site credit.

`source/autotest_callbacks.patch` has six named paths: five changed files and deletion of the old unmounted PressButton file after folding its corrected body into the original BrnAutoTestManager.cpp home. Full pre/post SHA256 bindings are in `SOURCE_MANIFEST.json`. Overlapping preimages are exact sealed owner postimages, not current shared-tree files. All six preimages match published WIP source `53961615f5f9105568fa37a329f79758451c922d`; the two overlapping files also match the sealed owner postimages.

| Original callback | Recovered operation |
| --- | --- |
| 823C6010 CallDebugFunction | Assert one string; call the actual game module's DebugManager function dispatcher. |
| 823C60A8 RecordLog | Assert at most one argument; pass an optional name to the actual embedded AutoTest's existing DumpGameState. |
| 823C6150 PressButton | Preserve argument/log order; store 1.0f in the actual embedded AutoTest's `maActions[index]`. |
| 823A9920 AcquirePad | Assert zero arguments; set that same AutoTest's `mbControlPad` true. |
| 823A98A8 RelinquishPad | Assert zero arguments; set `mbControlPad` false. |
| 823C6290 ActivateDebugComponent | Assert one string; use the original by-name activation method on the actual game's debug manager. |
| 823C6328 DeactivateDebugComponent | Assert one string; use the original by-name deactivation method. |

Each callback receives only lua_State* in r3, clears the Lua stack with lua_settop(L,0), and returns zero. They are static methods as required by the Lua C function table; no synthetic this/context parameter is introduced.

The existing PressButton source has a definite arithmetic/ownership error: ARTIST 823C6264 adds `0x10A6`, shifts by two at 626C, then stores through the real game global at 6278. That is **0x4298**, not the old file's `0x429C8`. AutoTest Init writes the 61-float action array at AutoTest+0x3C50 and the control byte at AutoTest+0x3D44. Its module base is gm+0x648, giving exactly gm+0x4298 and gm+0x438C. The proposal uses those named fields and no class-offset cast. It does not invent an index guard absent from ARTIST.

The callbacks' assembly directly addresses the game's private debug manager at gm+0x996FB8. A bounded friend declaration allows the recovered AutoTest methods to use that actual named member; it does not add an alternate singleton or accessor API. DecFIGS does not emit friendship. The member name/type/private placement is corroborated there, and the original callbacks attest the required access.

Three original DebugManager methods are recovered with their original bodies: CallFunction asserts mpUI then forwards to its FunctionManager; ActivateComponent(name) looks up and delegates to the existing component overload only when found; DeactivateComponent(name) looks up and clears only the active bit. The unnamed 82832200 body is identified as the string activation overload by its exact call shape and DecFIGS h:204.

The Lua helper constructor and GetNumParams were declared but had no body. Their bounded definitions restore the three local fields shown in every callback prologue: Lua pointer, lua_gettop result, zero result count. Existing GetParamType/GetInt32Param/GetStringParam bodies are retained. The helper implementation includes the actual Lua header, avoiding the deleted file's incorrect int-return declaration for lua_settop.

No builds, tests, IDB mutations, source/worktree/index/ref edits, CI, game/input, or inventory changes were performed. Root owns the separate WIP checkpoint and fresh review.
