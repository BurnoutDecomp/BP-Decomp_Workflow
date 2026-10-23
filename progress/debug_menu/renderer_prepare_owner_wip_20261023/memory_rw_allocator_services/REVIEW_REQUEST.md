# Fresh review of the two RW service bodies

Review the two source paths under source/pre and source/post, their full SOURCE_MANIFEST hashes and `source/memory_rw_allocator_services.patch`. Exact current base is sourceabcde0e0731587ba4169189918c257c5a3e86ceb. The fourth allocation packet is a required typed response dependency; its manifest hash and exact committed postimage are checked explicitly.

Scope: original Linear8286D130 and General8286D550 services, their canonical typed handler declarations and corresponding dispatcher casts. Both method bodies must match the bound56676 prior chunks exactly. Inspect them against primary assembly, not the General pseudocode prototype. No original pipeline is activated and no native buffer/capacity/mount is changed.

Please check requested capacity versus expanded backing extent, typed native placement reserve, all five parent lookups, u16 KiB granules, signed rounding with u32 product, one block per populated lane, exact warning/assert branches and continuation, null backing on failures, unconditional real Initialize, and actual receiver/id/type/result/pointer replies with native sizeof. Inspect the mutable GetBank result needed by GetData and the canonical single-pointer response contract.

`PROVIDER_BINDINGS.json` distinguishes current full source from exact method comparisons; `NATIVE_BODY_BINDINGS.json` records unchanged existing methods. `PROVIDER_BOUNDARIES.md` records unresolved original core/schema/list, initialization/factories and existing bank-engine differences. No compiler, tests, source gates, native run or independent verdict was executed by this lane. Root owns those actions.

Return `VERDICT: pass` or `VERDICT: fail` for this bounded source-only checkpoint, with locations tied to primary evidence. A pass does not establish complete startup/link/runtime parity or registration-site credit.
