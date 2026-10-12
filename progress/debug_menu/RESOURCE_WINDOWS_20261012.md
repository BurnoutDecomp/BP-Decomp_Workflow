# Resource debug windows

Root source branch `codex/debug-menu-resource-windows` is pushed at `0e6dcdc1`,
based on the separate GUI/Replay candidate `ab80240c`. It remains outside the
primary source union and has no native or final-entry verdict.

The first checkpoint restores all five original embedded window types, the
four-window pointer table, texture-entry allocation, and Histogram/TypeList
reset bodies. It replaces the incorrect standalone TypeList accounting shape
with its original Window base and named type/category records. Real descriptor
constructors initialize size/alignment to `{0,1}`; the previous explicit zero
alignment and invented scratch fields were incorrect. The original seventh
category slot is retained. Window construction leaves its data untouched until
the original Prepare path sets it.

Six affected production TUs compile with zero new faithfulness findings.
The8799da15 increment restores all20 registrations, pool-option generation,
texture/page and bundle callbacks, and the original texture reset. Its four
production TUs also compile with zero new faithfulness. The original reset
leaves texture byte sizes and the total-texture field untouched; it initializes
the attested pointers, indices, model/instance sentinels and selection state.
The1237d59d increment restores option-table refresh, invalid-pool removal,
all four typed window reset dispatches, window add/remove order, mode updates,
and the stats/share-test update dispatch. Three affected production TUs compile
with zero new faithfulness.

The0e6dcdc1 checkpoint restores the stats dump and its real buffered logger.
Original Open truncates and closes the file; Flush reopens it with OPEN_EXISTING,
seeks to the end and writes the pending buffer. Append preserves an exactly full
buffer until overflow or an explicit flush; the old source dropped excess text.
Three production TUs compile. The complete production logger and StrStream pass
36 checks using real temporary Win32 files. A focused negative control retains
the recovered lifecycle but substitutes only the old char sink;7 checks fail.
This proves that backend regression, not the original in-game action.
Resource destruction, the remaining window render/update bodies,
shared-window source review, linking and native checks remain pending. The
planned scope is 20 static registration sites; none is promoted by this partial
construction checkpoint.

The exclusive manifest now contains24 paths, adding only the named buffered-log
seam, its compile anchor/tests, and a manifested Pool friendship for the next
window increment. The original function/address map, compile records
and constructor postmortem are under
`scratch/DEBUG_MENU_1011/recovery_lanes/resource_windows_packet`.
ARTIST constructors `827E08D0`, `827DF8E8` and `821F05C8` arbitrate initialization;
DecFIGS supplies the declaration shapes. No raw-offset/vtable workaround or
duplicate window family is introduced.
