# Manual primary / declaration postmortem

This is source/assembly inspection. No compiler, source gate, tests, native run or fresh reviewer verdict was invoked.

| Check | Primary / declaration binding | Proposal |
| --- | --- | --- |
| Resource ABI | 82907948 saves r3=this,r4=input stack,r5=output stack,r6=const input,r7=output; DecFIGS result enum0/1. | Exact four-argument API and enum, without a two-argument forwarding body. |
| Outer monitor | Resource ID is retained before Start; Stop follows all six output/input pops. | Saved ID; explicit inner scope ends before outer Stop. |
| Creation order | Memory input, Loader update input, Pool input; Memory output, Loader output, Pool output. Create/Destroy failure assertions come from IOHelper52/57. | Typed IOHelpers in that declaration order, destructed in exact reverse order. No fabricated buffers or allocation guards. |
| Input processing | File response phase first; input read, Memory/Loader/Pool write locks; inverse unlock order. Original input is not cleared. | Same phases, locks and private const shuttle API. Current native adapter's clear/null branches are retained only in its unchanged body. |
| Loader child | 82907638 profiles, output write, input read, receiver/load/pool processors, input unlock, UpdateStream, output unlock. Stack args unused. | Exact typed void method and order; no adapter return interpretation. |
| Pool bridge/result | Pair helper823B6FE0 locks destination-write/source-read;7060 unlocks source then destination. Pool result compared exactly to1. | Actual canonical pair helper with restored null assertions, typed Append, enum comparison. |
| Pool state transitions | 829076D8 starts allocation FIFO when idle, then selects1/2/5; later independently tests3 and6; output unlock precedes 128-pool Update sweep. | Same independent tests and live member state after each call, same GetId!=-1 sweep and final emergency-state result. |
| Delayed records | Resource owner creates record input after pool phase, copies pool replies, records in loader cache under read lock, then pops record before memory. | Nested IOHelper and existing real RecordPostUpdateEvents/cache provider. No immediate extra loader update. |
| Memory/output | Pool memory requests precede real MemoryModule Update; outgoing memory, pool and loader reads precede status publication. | Same stack arguments, locks, source order and dynamic reply transport. No fake success. |
| Disk status | 82907948 reads static830EA574 and writes its nonzero bool through output status getter under write lock. RWDiskErrorHandler828E8B20 atomically stores1, returns0. | Private canonical AtomicInt32 static, const reader, original static callback and typed status setter. Primary initial word is0. No host callback wiring invented. |
| CPU fields | Raw82F34004..1C,82F33FD4 and82F34044..60 are all-1. DecFIGS identifies Resource7,Loader1,Pool8 names. | Correct owned static fields and initial values; original Construct registration remains separate. No zero monitor handle used to fake readiness. |
| Memory destructors | 8286BB18/BB68 call IOBuffer Destruct then corresponding queue Destruct. | Same named calls. Existing native request capacity remains13312; original12288 is not silently substituted. |
| Pool destructors | Raw828F2F40 and828F3208 show base first, then input queue / resource queue then output queue. | Same order, real queue Destruct methods, no offset writes. |
| Loader destructors | 828F2D70 clears load/unload lengths after base;3020 destructs stream, clears load/unload response lengths, destructs send queue;33D0 destructs base then receive queue. | Named fixed/variable queue Destruct calls in exact observed order. |
| Resource input destructor | 828EC940 base then Resource queue Destruct; missing export82663580 confirms its stack destroy thunk calls that method. | Canonical InputBuffer Destruct corrected; previous output destructor retained. |
| Native preservation | Extracted pre/post methods. | Three current two-argument updates and existing Construct/Prepare/device registration bodies unchanged. Source-only proof, not a runtime claim. |

The private const shuttle corrections change declaration shape, not body behavior; their source bodies are separately bound. The existing native13312 request queue and all other capacities remain unchanged. Native pointers/event records use canonical types and sizeof; no guessed allocator, duplicate registry, class-offset access or packing is added.

The paired helper null checks use the existing canonical host assert macro and original messages; the host macro supplies current source locations. All valid lock ordering and original assertion continuation is preserved. Other overloads remain unchanged.

The full existing loader, pool, filesystem and bank engines are not blanket reviewed by these three caller bodies. Missing schema/list definitions, original member/monitor initialization, unconnected host disk-error callback and current capacity/layout differences remain explicitly reported. The primary vtable evidence is kept in the separate factory folder and is not used to infer an initializer here.
