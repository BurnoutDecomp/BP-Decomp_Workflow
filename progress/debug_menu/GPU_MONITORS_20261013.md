# GPU monitor repair - 2026-10-13

**Candidate pushed; combined review and full-game validation pending.**

The two GPU switches were registered, but the renderer had no monitor
registrations, disabled timing brackets, and a no-op platform callback.
Source coverage had not established working behavior.

Gameplay candidate `749a190a14a87207ddb19b6ed8cf4945eb16b87a` on
`codex/debug-menu-gpu-monitors` restores the original 20 names, budgets and
pass categories, update-side Swap, and graph layout. Native D3D9 timestamp
queries supply completed GPU spans without waiting for pending packets.

Five affected TUs compile with no new faithfulness findings. The real native
GPU/engine registry/report path passes 26 checks; the existing whole-frame
GPU regression passes16. A complete graph/callback fixture passes12 checks.
Review caught the previously wrong callback-total/high-water update;749a
repairs it. Frozen77 fails5 of the same graph checks, and the old41 timing body
fails both positive native-data checks. These checks are not proof that the
full game's graph, table, or visibility switch works.

New isolated cases cover graph, table and hidden modes with explicit config
copies, real debug bindings, completed queries, downstream draw callbacks,
frames, and driving witnesses. Full-game frames must also be inspected before
claiming those settings work. No verified menu-entry count changes here.

Frozen review packet:
`scratch/DEBUG_MENU_1011/gpu_monitor_recovery_20261013/review_749a190a1/REVIEW_PACKET.md`.
