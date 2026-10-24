# Fresh review request — survey output semantics

Use Root's existing single review lane. Review the three exact proposed postimages against95e513ae15ebfd322fd639664f835b171718e736 / workflow992e2896286ed83aa0098729e1b00497476b4c41. The rejected62065 picture remains a failure.

Please verify:

1. ARTIST827EE010 Flags1 and82949E90 bit7/register2293 contract; pinned Xenia only names the hardware bits. Confirm the native mapping preserves genuine visibility testing without framebuffer/depth/stencil pollution.
2. Source timing all the way through query Issue, actual indexed GPU draw, End and matching result. Do not substitute a command-production timing theory for the actual call chain.
3. Header compatibility, complete actual flags lifetime, stack/device-loss behavior, and suppression even for unavailable host queries. Existing Issue/GetData/token/generation/serial/decision bodies must remain unchanged.
4. All four color masks, depth/stencil write controls, alpha test and existing alpha-coverage request/reconciler ownership. Check actual save/restore, no stale shadow cache, and unchanged depth/stencil tests/function/culling/programs.
5. The scope surrounds the actual retained/UP native draw expression, not an earlier producer. No fake results, new fail-open policy or skipped box/scene draw is introduced.
6. C++ source and exact shipping headers/flags. This lane has not compiled. Check the explicit assertion include after D3D9 and all new public PC API declarations/definitions.
7. Bounded passive diagnostics: serial correspondence, actual draw-state tuple and after-restore equality. No performance or visual success claim follows from source.

Return `VERDICT: pass` or `VERDICT: fail` with exact candidate paths/lines. Root controls publication, hosted compilation and any further native capture. No reproduction is requested before those gates.
