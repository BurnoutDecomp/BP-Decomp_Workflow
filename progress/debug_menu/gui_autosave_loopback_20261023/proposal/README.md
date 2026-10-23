# GUI autosave event-356 loopback repair proposal

**Recommendation:** apply the exact event-356 force/pending latch at the late PC channel-40 observer drain, after wrapper unwrapping and before the existing output forwarding. This is the smallest faithful bridge across the PC scheduling split: the inbound consumer and autosave tail already ran, and the per-step GUI input buffer is destroyed before the next update.

- Candidate: `b5-decomp` `9af6a868959578f4eafa9af0d69ccd27081667a0` (`src/GameSource/Gui/BrnGuiModule.cpp` blob `eee391b23fc3e4b0c0e1406394489d2db596e1cc`). The checked-out B5 worktree (`91a0ed564f9c9e3dec915bfb416c0467650084ef`) was not edited.
- Proposed delta: one `if (luEventType == 356u)` block in `BrnGuiModule.cpp`; it applies `force |= payload[0]` and `pending = true`, then falls through to the original forwarding unchanged.
- Expected behavior: payload zero follows the existing 60-second throttle; nonzero keeps the original force bypass. The natural route producer is zero, so this proposal does not force a save.
- Review evidence: [ARTIST excerpts and hashes](evidence/artist_assembly.md), [source/lifetime proof](evidence/lifecycle.md), and [native before result plus acceptance](evidence/native_before_and_acceptance.md).
- Exact full-file proposal: [before](source/BrnGuiModule.cpp.before.cpp), [after](source/BrnGuiModule.cpp.after.cpp), [diff](source/BrnGuiModule.patch).
- No C++ compile/test, game run, Stage/Run/input action, CI, or Git mutation was performed. Only this new scratch folder was written.
