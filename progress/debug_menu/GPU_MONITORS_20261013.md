# GPU monitor repair - 2026-10-13

**Candidate pushed; combined review and full-game validation pending.**

The two GPU switches were registered, but the renderer had no monitor
registrations, disabled timing brackets, and a no-op platform callback.
Source coverage had not established working behavior.

Gameplay candidate `77bdc4a1bf05154c75bef58ca2caceae5b47d6c8` on
`codex/debug-menu-gpu-monitors` restores the original 20 names, budgets and
pass categories, update-side Swap, and graph layout. Native D3D9 timestamp
queries supply completed GPU spans without waiting for pending packets.

Five affected TUs compile with no new faithfulness findings. The real native
GPU/engine registry/report path passes 26 checks; the existing whole-frame
GPU regression passes 16. These are small hardware tests, not proof that the
full game's graph, table, or visibility switch works.

New isolated cases cover graph, table and hidden modes with explicit config
copies, real debug bindings, completed queries, downstream draw callbacks,
frames, and driving witnesses. Full-game frames must also be inspected before
claiming those settings work. No verified menu-entry count changes here.

Frozen review packet:
`scratch/DEBUG_MENU_1011/gpu_monitor_recovery_20261013/review_77bdc4a1b/REVIEW_PACKET.md`.
