# Manual postmortem

This is the agent's assembly/source self-review of the bounded source proposal. No work-submit/review command, compile, link, tests, runtime, or inventory mutation was run. It is not the fresh reviewer verdict.

| Check | ARTIST evidence | Proposal result |
| --- | --- | --- |
| Signature/stack order | 823DB854â€“874 saves `this,r4,r5,r6,r7,r8`; main 827E65B4â€“D4 supplies all five stacks through virtual +0x40. | Virtual five-stack method; typed arguments retained without a base no-arg adapter. |
| Declaration shape | DecFIGS BrnGameModule.h:656 and GameDataModule.h:289. | Game Prepare virtual; separate GameData four-arg virtual with const input. No numeric native vtable indexing. |
| START/HARDWARE | 823DB8E8â€“914 clears termination, sets stage1, tests hardware, then AutoTest Init. | Hardware false returns directly; Init runs only after hardware success. |
| Base and IO ownership | 823DB918â€“98C records the four stack pointers, creates input/output on resource stacks, constructs dispatch on fifth. | Persistent typed member pair; CreateIOBuffer results discarded exactly as original. No guessed fallback allocator or scratch class. |
| GameData virtual call | 823DB990â€“9C8 uses resource stacks and persistent pair. | Four-arg method declaration/call retained. Missing original body is an explicit link dependency, not a successful shim. |
| Renderer allocator lock | 823DB9CCâ€“BA0C locks, obtains output's allocator pointer, calls embedded renderer, unlocks on both results. | Exact lock bracket; renderer failure reaches the disk-error tail after unlock. |
| D3D ownership | 823DBA10â€“18 releases X360 device thread ownership. | Explicit PC platform leaf; native D3D9/ThreadLayout ownership is not pretended to implement an X360 call. |
| Massive allocator lock/ABI | 823DBA1Câ€“5C passes hardware in r3, same list in r4. 823C129C overwrites r3 with r4 then fetches bank63. | Const-list member method, same lock bracket, bank63 assert retained. |
| Thread interface adjustment | 823DBA80 forms gm+0x640 before Begin. | Passing `this` to typed IThreadClass* lets C++ perform the base adjustment. |
| Thread configuration | 823DBA8Câ€“98 passes Resource/ThreadSync/WaitOnDispatch monitors; BACC/BAD4 store60/50. | Original monitor order; typed setters write the corresponding ThreadLayout members. |
| Loading command | 823DBABC reads dispatch-manager +8 (write buffer); BAD8 stores1 at loading-command offset. | GetWriteBuffer()->ShowLoadingScreen(), without an invented additional lock. |
| Frame-rate assert | 823DBADCâ€“BB08 tests Prepare and fires original expression on failure. | Called outside the assert, so the side effect remains when assertions compile out. |
| Callback/context | 823DBB1Câ€“2C obtains manager and supplies handler, Camera, this. Receiver823A9030 loads module from context slot. | Existing four-arg context registration; receiver takes void* then dereferences the stored module-pointer slot. |
| Completion | 823DBB38â€“4C stores prepare0/release0/system-menu-byte0, returns1. | Same fields; the system-menu latch is not mislabeled as termination. |
| Failure/default | 823DBB58â€“90 asserts default then checks signed stage>=3 for CheckDiskError. | Same condition and false result, including manager-failure exclusion. |
| Disk observer | 823BC7B0â€“858 reads file status, chooses port if bound, one-shot thread with priority0/processor2/boostfalse/name DispatchThread. | Typed FS getter and process latch; native EAThread context conversion marked platform leaf. |
| Output Construct | 82666924 stores constructed status1; 82666928 constructs+9; 82666930 clears pointer+4. | Base Construct + named FS Construct + allocator pointer null. No invented store to LiveUpdate. |
| Output accessor separation | 823B1778 returns+9; cached raw setter82663F7Câ€“80 copies one byte to+9. Live getter823B1638 uses+8. | Separate typed filesystem payload and existing LiveUpdate byte. |
| Constructor consumers | Original Output Construct resets IO status; current Update owns an existing output lifetime. | Loading initializer constructs before locks. Update clears only named FS payload under its existing lock; it does not reset the base while locked. |
| AutoTest bounded helpers | 823C0438, 823A9300, 823A9218, 823A9150, 823A91D0; raw tables82035274/820352B0. | Original initialization, file/Lua library/callback order and asserted append retained. Seven shipping callback targets remain unavailable (six absent bodies, one unmounted raw-offset PressButton body). |

Rung 1 was the ARTIST exports/assembly. DecFIGS supplied virtual/const/type/member names and enum names. No Feb-2007 behavior or layouts were used to override either. Existing primary evidence was frozen locally, including the missing-export setter's cached raw assembly; no IDB was opened or mutated.

The source is a complete recovery of the **outer owner**, not a complete recovery of its entire GameData/resource core. The current two-argument core has different omitted stages and terminal-state behavior. The later stage-18 source packet is retained only as a dependency lead; it still contains explicit deferrals and cannot justify activation.

No claim is made that the full 13-path proposal links: original GameData Prepare and seven callback symbols remain unavailable in the shipping target. No native allocation or registration was exercised. Renderer Prepare/native allocation reconciliation, resource status production, original five-stack host startup, and XContent transport remain outside this frozen owner checkpoint.
