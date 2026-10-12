# Resource debug windows

Root source branch `codex/debug-menu-resource-windows` is pushed at `1237d59d`,
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
with zero new faithfulness. The source still lacks the actual stats-dump buffered
logging backend; its declaration is retained without a substitute body.
Resource destruction, the remaining window render/update bodies,
shared-window source review, linking and native checks remain pending. The
planned scope is 20 static registration sites; none is promoted by this partial
construction checkpoint.

The exclusive 18-path manifest, original function/address map, compile records
and constructor postmortem are under
`scratch/DEBUG_MENU_1011/recovery_lanes/resource_windows_packet`.
ARTIST constructors `827E08D0`, `827DF8E8` and `821F05C8` arbitrate initialization;
DecFIGS supplies the declaration shapes. No raw-offset/vtable workaround or
duplicate window family is introduced.
