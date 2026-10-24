# Static postmortem

No build, test, game, input, CI, original IDB or helper launch ran. This is a source/evidence review of the proposed native platform effect.

| Check | Result |
|---|---|
| Load-bearing original input |827EE010 passes query ID and Flags1; End uses0. No inferred flag is substituted. |
| Original bit encoding |82949EB0/EB4/ED4/EDC plus register write82949F04–F14 attest query-enable/id/flag bit7. End82949FF0–A028 restores outer/disabled mode. |
| Register name cross-reference | Pinned official Xenia register table/declaration identify2293 and kill_pix_post_hi_z. ARTIST remains behavioral authority. No emulator query-result or draw-skipping implementation is imported. |
| Higher state owner | Original BeginQueries and query walk do not install a no-write state; selected Im3dZOnly BeginRendering binds shader/descriptor only. The native shim loses the original platform flag. |
| Command-production hypothesis | Query walk is a direct interpreter call. Staged constants flush before WorldDraw. Both retained and UP endpoints make actual native D3D9 draw calls before EndSurvey. No timing relocation is warranted by source. |
| Query lifecycle untouched | After removing only new flags storage/signatures/getter, provider CPP restores byte-for-byte to95. All Issue/GetData/token/generation/serial/decision function bodies remain exact. |
| Correct flag lifetime | Active survey frame retains full flags before native query availability checks. Getter reads the actual top stack frame. No success/ready flag is manufactured. |
| Suppression placement | Scope surrounds the native draw expression after geometry/instancing setup; it ends before existing successful-submission processing. The original expression and all draw arguments survive exactly apart from indentation/declaration. |
| Output and test ownership | Four color masks, depth write, stencil write mask, alpha test/coverage are scoped. Depth/stencil tests, depth function and culling remain unchanged. Shaders, matrix upload, geometry and query stay real. |
| Restoration/cache | Actual saved values restore through D3D9. Native coverage restores through its same request/reconciler owner. No shadow-cache stores are invented. Diagnostic tuple equality verifies the claimed restoration in a future Root run. |
| Diagnostics | Existing env gate only;96 lines maximum; actual readbacks are budget-gated. No query/result/scene mutation is caused by diagnostic logging. |
| Native path coverage | The sole game BeginConditionalSurvey caller on95 is the indexed occludee box path. Other provider call sites keep default Flags0. General non-indexed survey modes are not claimed. |
| Exact byte binding | Source preimages come from full95 hash. Mixed CR/CRLF/LF bytes outside edited regions remain preserved; static reversal reproduces the complete prior shim. |
| Claims bounded | Static defect/correction proposal only. No visual acceptance, control credit, native pass, performance pass or all-registration-count change. |
