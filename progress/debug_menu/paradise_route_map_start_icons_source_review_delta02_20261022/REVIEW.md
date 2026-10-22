# Combined route map start-icon source review: delta01 + delta02

VERDICT: pass

Reviewed the full composed map-icon proposal against immutable B5 `5093cdb07f74fe0cfa6a6a32283fb6195be790ab` (tree `684d10b1b878200cdebf1b6fab29ce03646ea828`) and the pinned ARTIST exports. The composed source preimage matches the 5093 blob; the b6 checkout has the same blob for this path.

The four restored online-route branches preserve the ARTIST-selected light-trigger lookup, junction lookup, active/inactive alpha choice, zero rotation, `WorldToDevice(..., true)`, online start state 46, pool-slot placement, used-count update, capacity assert and unused-tail handling. The final delta02 correction fixes the delta01 divergence: `UpdateSatNavIcons` junction arm now selects state 49 unconditionally. ARTIST `0x82522588` at `0x82522974` loads `r4 = 0x31` and immediately calls `SetState`; this arm has no crash-nav state test. The separate `UpdateCrashNavIcons` arm retains its 49/51 condition, matching ARTIST `0x825212C0` at `0x825216B4..0x825216C4`.

Delta02 changes only that state selection. Its frozen delta01 fail review remains unchanged at SHA-256 `bc19204fd61e0c5b97e87b506d8bfadb6305a7542407b5e2abd14a98e0e7388d`.

Exact composed input SHA-256: `7dafbe9bf00fd9a8cf0fff7342e59eecd89da4f922d9a8882d987f5e29d599b4` (113690 bytes). Exact full composed postimage SHA-256: `8aa7591528c64ac6b9e3a729b857b73455a845050b6c14e0705527a3f194ed2b` (114251 bytes). Composed patch SHA-256: `3123eca9e2860abffc0fc4bff8ae9b658675dc4bf82542d07c706603ce004e40`; delta02 correction patch SHA-256: `56f927b0196b63bb4bbf183b29337f38140aca1e30ff3b783aab380ae644aa69`.

This is a source/design verdict only. No runtime behavior credit is granted; no build, fixture, game, CI or IDA action was run.