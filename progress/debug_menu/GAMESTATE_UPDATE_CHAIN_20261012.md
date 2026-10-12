# GameState update-chain recovery

Source branch: codex/debug-menu-gamestate-update-chain.
6cba4b3a checkpoints the complete eleven-path GameState binding/HUD/arrow cohort
throughbfd81989, with canonical math-header and BoxRegion-accessor compile fixes.
All three changed C++ TUs compile; zero new faithfulness findings.

d62fe25b adds the original EmmPreWorldUpdate and ModeManager::PausedUpdate bodies,
plus the lifecycle identity/17-monitor tail. EMM now has the player-transform and
timer writers, original takedown-camera pause argument, mode/road-rules dispatch,
and scoring/network/overtake tail. PausedUpdate publishes the previous/current
mode snapshot and still exits a finished mode. Both changed TUs compile with
private source headers in the canonical include slots; zero new faithfulness.

Versioned source ZIPs/pins, compile logs and self-review evidence are under
scratch/DEBUG_MENU_1011/recovery_lanes/gamestate_update_chain_packet. Full work
postmortem dossiers were generated for both TUs; EMM_POSTMORTEM.md distinguishes
the private produced source from their primary-tree embedded source/audit data.

The original full PreWorldUpdate caller and replacement of the current PC
bring-up pump remain in progress. This is a pushed source checkpoint, not a
fresh reviewer/native verdict or a complete25-entry page. GameState's existing
unclassified fields remain unresolved. Source packet union stays711/1354;
final dispositions stay25 verified+3 original no-ops,1326 pending.

Private prerequisite checkpoint 3ab5932cde6d5384c6764d25133ca7888eadf12e homes the original takedown output
queue as its real EventQueue member and adds action 193 with two native-width
pointers plus its availability byte. The OnlineCarSelect controller snapshot
type is correctly qualified. Changed production groups compile, with 0 new
faithfulness findings. Full PreWorldUpdate, independent review and native caller
integration remain pending; GameState25 is not promoted into source totals.
