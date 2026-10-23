# Original GameData caller manual postmortem

This is source/assembly inspection only; no builds, tests, source gates, runtime or fresh reviewer verdict were run.

| Check | ARTIST evidence | Proposal |
| --- | --- | --- |
| Four-arg ABI | 82673F38 prologue saves input stack r4, output stack r5 and output r7. The input r6 is not consumed. | Typed const input, typed output, exact stack order; unused input has no invented read. |
| Entry status | Calls FileSystemStatusInterface::Construct at GameData+475952 before the stage switch. | Named member Construct on every entry. |
| Base/resource | Stages0/1 base; successful base registers resource then DLC debug components; stage2 runs resource Prepare then clears receiver. | Same order and failure tails. |
| Stack helpers | Original3/4/5 pass both caller stacks. | Exact typed helper overloads; no forwarding into native void* shortcuts. |
| DLC readiness | Stage16 calls DLC Prepare, then clears the separate GameData package index. | Typed owned manager and distinct index. |
| Patch request | Stage17 obtains package version before the path call, constructs type25 with receiver/index, queues console268 bytes, clears receiver, unlocks, pumps, pops. | Same order; native pointer-preserving event and sizeof payload on x64. |
| Stage18 yield | 8267421C–230 increments index; remaining package stores17 and branches to false/status tail. | No second submission in that call. No receiver dequeue invented. |
| Wait pump | Pending stage18 carves one Resource input, pumps, pops, then returns false/status. | IOHelper leaves scope before common failure publication. |
| Attrib arguments | 82674258/68/78 fetch heap21/20/19;288 fetch linear22;2AC calls with linear,19,20,21,80. | Explicit temporaries preserve evaluation order. |
| Attrib scratch | 826742CC creates input;2E0 calls three-arg schema helper;2F8/300 destroy on either bool result. | Manual typed create/destroy pair and same ignored create result; no global static substitute. |
| GameTalk | 82674324 invokes with10 and1/60;328 checks low byte. Callee8283952C returns1. | Correct bool ABI and retained conditional; debug-interface failure asserts then continues as original. |
| LiveUpdate | 8267436C–394 virtual no-arg module Prepare at GameData+361728. | Canonical typed LiveUpdate module call, no invented success. |
| Lists/ICE reset | Two-stack calls9–14;826743E0 resets ICE counter only after challenge success. | Same helper signatures, stage/counter writes and failure behavior. |
| Success | 82674478 stores prepare1;47C release0;480–494 locks, publishes actual list, unlocks, returns1. | Same named fields and publication. Does not publish a fabricated status on success. |
| Default/false | Case15/default assert;826744C4–4DC publishes member status;4E0 returns0. | Same, with no nullable-output suppression. |
| Status helper | 826663B0 creates ResourceOutput, calls4arg core, read-locks/copies status, unlocks, destroys, returns original enum. | Typed IOHelper lifetime and enum preserved. |
| Output destruction | 826637F8 calls shared822DC3D0; thunk is a sole branch to IOBuffer::Destruct. | Canonical OutputBuffer::Destruct forwards to that base. |
| Existing host body | Current two-arg method and native DONE7. | Preserved exactly; separate source binding records its bytes. |

ARTIST controls the behavior and stage values. DecFIGS supplies the original const/typed helper APIs and enum result shape, but its test-stream/DONE values do not override ARTIST's invalid15 and DONE19. X360-only member identities are tied to actual constructor and call targets rather than imported PS3 fields. No Feb-2007 bodies or layouts were used.

The existing shortened release-stage field type is retained for compatibility with the unchanged native method; the recovered caller writes its original zero value. This packet recovers the caller and required typed additions, not every existing class-declaration debt item. Original stack helper/core definitions and constructor/factory availability remain explicitly unresolved. No null/empty/trap body is introduced for them.
