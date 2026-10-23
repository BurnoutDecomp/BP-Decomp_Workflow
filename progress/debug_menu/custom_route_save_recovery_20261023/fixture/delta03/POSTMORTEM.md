Hosted run 39955666449 attempt 1 remains a real failure. Its candidate fixture completed all six compiles with exit zero, then link.exe returned 1120. No fixture mode, negative control, shipping build or native game ran. The retained logs/result/input receipt and Root's failure review are evidence of that boundary.

The original six-TU composition omitted diagnostics required by emitted production VariableEventQueue and SpecificGameMode Event code. `/Gy` and `/OPT:REF` did not remove all of those references. The missing definitions are:

| Retained unresolved symbol | Delta03 provider |
| --- | --- |
| StrStreamBase::operator<<(int) | Actual c36 CgsStrStream.cpp s32 overload |
| StrStreamBase::operator<<(void*) | Actual c36 CgsStrStream.cpp native pointer overload |
| StrStreamBase::operator<<(PrintMode) | Actual c36 CgsStrStream.cpp mode overload |
| StrStream(char*,int) | Actual c36 CgsStrStream.cpp constructor and its base/sink dependencies |
| Log::gpDebugPrint | Fixture globals TU, declared StrStreamBase* by actual CgsLog.h |
| Message::gxMessageFilterFlags | Fixture globals TU, declared u64 by actual CgsLog.h |

The corrected binder appends the complete production CgsStrStream.cpp and a 453-byte globals-only TU to each variant. Production formatting is compiled directly; no formatter method or subject method is mirrored. GuiModelIO/GuiInterpreterIO already use this diagnostic arrangement with real CgsStrStream.cpp, a null debug sink and zero optional message-filter bits. Exact c36 sources for that idiom, the formatter and declarations are retained.

The route fixture, cache input providers, original-control source, process helper, runner and complete test plan stay byte-identical. In particular, the delta02 disjoint GUID poison and all unexpected-assert hooks remain unchanged. Production queue assert paths still format their local buffers and call FireAssert directly; the fixture still increments its assertion count and prints UNEXPECTED_ASSERT. Message-filter zero affects optional log output and does not disable CGS_ASSERT or its recording hooks.

The fix changes dependency composition only: eight compile units, eight installed payloads and twenty-four pinned b5 input files. The CI composition updates corresponding hard pins and count guards while retaining all 71/13/1/1 mode identities, 0/6/1/1 failure expectations, zero assertions, owned cleanup and exact negative witnesses. Python AST and PowerShell syntax were inspected without importing/invoking the proposed code. The new link and behavior results remain unverified until Root performs a reviewed hosted rerun.
