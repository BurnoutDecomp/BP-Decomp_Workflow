# Callback manual postmortem

No compile, tests, runtime, or fresh reviewer verdict was produced. This records the author source/ARTIST walk.

| Check | Original evidence | Source result |
| --- | --- | --- |
| Callback ABI | All seven callbacks save r3 as lua_State* and immediately pass it to lua_gettop; the Lua registration table takes plain C callbacks. | Static methods; no implicit this. |
| Helper state | 823C6024–6038 and matching prologues store Lua pointer, count and result-count zero. | Typed canonical helper constructor; GetNumParams reads its named count. |
| Arity/assert behavior | Call/Press/Activate/Deactivate require1; RecordLog <=1; Acquire/Relinquish require0. | Same conditions/expressions. Assertions do not become early returns. |
| Actual debug owner | Call/Activate/Deactivate form gm+0x996FB8 before manager calls. | Actual GetMainGameModule()->mDebugManager, through narrow AutoTest friendship. |
| Optional log filename | 823C6100–6124 uses null for zero arguments, GetStringParam(0) otherwise, then gm+0x648 DumpGameState. | Same optional name and actual embedded AutoTest. |
| Action store | 823C6264 adds0x10A6; 626C shifts2; 6278 stores1.0f to global gm. Init823C048C clears AutoTest+0x3C50 for61 words. | Typed `mAutoTestManager.maActions[index]`; removes old0x429C8 raw cast. No added bounds policy. |
| Pad control | 823A9974 stores1 and823A98FC stores0 at gm+0x438C. Init823C0474 writes AutoTest+0x3D44. | Named `mbControlPad` in the same embedded AutoTest. |
| Press log order | 823C61AC–6204 gates first log; 6210 lua_isstring precedes second filter check621C. | Same evaluation order. |
| Manager string activation | 82832214 FindComponentByName; found target invokes pointer ActivateComponent at228. | Lookup then delegate; not-found does nothing. |
| Manager deactivation | 82828E28 looks up; only found component's active byte is cleared. | Named active-bit store, no invented unregister or OnDeactivate call. |
| Function dispatch | 8282E308 asserts mpUI then calls its FunctionManager atUI+332. | Typed mpUI assert and GetUI().GetFunctionManager().CallFunction. |
| Return/stack | Every callback calls lua_settop with0 then returns0. | Preserved, including after assertion handling. |
| Source ownership | DecFIGS attributes callbacks to BrnAutoTestManager.cpp; old PressButton split is absent from the exact shipping list. | Folded all bodies into canonical original TU; deletion proposal for the old dead split. |

No lower-rung layout overrides were used. Pointer widening is handled by existing typed members. The owner packet's static declarations are a required preimage dependency. Unknown original GameData core behavior is not replaced by this continuation.
