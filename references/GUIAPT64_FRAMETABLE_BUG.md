# GUIAPT64 frame-table packing bug (native-8 `1:7:8` GuiApt bundles)

*Diagnosed 2026-07-05 against the GUIAPT64 drive set (JeBobs' native-8 conversion of the
Nov-13 console GuiApt data). Repair tool:
[`tools/assets/bundles/apt8_fix_frametables.py`](../tools/assets/bundles/apt8_fix_frametables.py).
113 of 290 bundles in the drop are affected.*

## TL;DR

The GUIAPT64 emitter does **not 8-align the start of movie frame-record tables**. Whenever
a table happens to land on a 4-mod-8 address (typically right after an odd-length string
pool), its records are written with **natural C packing** instead of the fixed layout the
engine reads. Every frame of such a movie then reads as garbage at runtime; the engine's
data-plausibility guard skips those frames, and the movie clip simply never composes its
children. Nothing crashes — content silently goes missing.

Observed casualties (before repair): the title-menu item **text fields** (`B5MenuItem` →
`labelHolder`), the **"HD Compatible for Optimal Gaming"** panel (3 tables in
`TITLE_SCREEN02`), the help-prompt **button glyph**, licence screens, help items, results,
HUD messages — anything whose wrapper sprite's table drew the short straw on alignment.

## The correct layout (Xbox One retail, the 64-bit ground truth)

A movie definition (root `type 9` char, or a nested `type 5` sprite) holds, at def+0x20:

```
+0x20  u64  frameCount
+0x28  u64  framesOffset          ; apt-chunk-relative; chunk base = resource + h_apt
```

`frames` is an array of **16-byte** records, **8-aligned**, fixed stride:

```
AptMovieFrame {
    +0x00  i32  commandCount
    +0x04  u32  (pad, always 0)
    +0x08  u64  commandArrayOffset   ; -> array of u64 command offsets, stride 8
}
```

This is what the Xbox One binary reads (`AptMovie::doFrameControls` twin
`sub_14084D0B0`: `mov ecx,[table+16*i]` / `mov rdx,[table+16*i+8]`), what
`AptMovie::resolve64` relocates (the 8-byte slot at `frame+0x08`), and what the healthy
majority of records in the GUIAPT64 bundles themselves use.

## The bug

When the emitter reaches a frame table at an **unaligned** (4-mod-8) write position, it
does not insert alignment padding first. The records are then laid out as a naturally
packed C struct — each `u64` field aligns itself to the next 8-boundary **relative to the
running cursor**, so the record stride alternates 12/16 and the `commandArrayOffset` sits
at `align8(rec+4)` instead of a fixed `rec+8`.

Real bytes, `B5MENUITEM.bundle`, char[14] `labelHolder` (fc=1, stored framesOffset
`0x1974` → table at chunk+`0x19c4`, which is 4-mod-8):

```
0x19c4: 01 00 00 00        ; commandCount = 1
0x19c8: 48 1c 00 00 00 00 00 00   ; commandArrayOffset = 0x1c48  <-- at rec+4, not rec+8!
```

A healthy sibling for comparison (char[7], table at chunk+`0x1970`, 8-aligned):

```
0x1970: 01 00 00 00  00 00 00 00  30 1c 00 00 00 00 00 00
        count=1      pad          commandArrayOffset = 0x1c30 @ rec+8   ; correct
```

Multi-frame variant (`B5HELPITEM.bundle`, fc=2 table at `0x5d4`): rec0 packs to 12 bytes
(`{4, 0x600}`), which re-aligns the cursor, so rec1 is a normal 16-byte record — the
stride alternates. `B5CRASHEDHUD` has a 31-frame table in this state.

### Why the engine sees nothing instead of crashing

The runtime reads `commandArrayOffset` at the fixed `+0x08`. On a packed record that slot
holds the pad/next-record straddle (e.g. `0x0000000100000000`). The engine's converted-
bundle guards (`doFrameControls`' `bCmdsPlausible` check, `resolve64`'s bounds checks)
classify that as an implausible pointer and **skip the frame** — so the affected movie
ticks but never places its children. `labelHolder` composes as an empty sprite → no text
field → the menu shows no item text; `HDComp_mc` never gains its `transin` label; etc.

### The trigger pattern

The emitter writes string pools (instance/export names, font names) and frame tables into
the same region. A pool whose total length is ≡4 (mod 8) leaves the cursor 4-misaligned;
the very next frame table inherits that. That is why the bug hits scattered wrapper
sprites (1-frame `labelHolder`-style clips right after their name strings) rather than
whole bundles.

## Second manifestation: misaligned COMMAND records (added 2026-07-05)

The same missing-alignment bug also hits individual **command records**. Simple commands
are `{u32 tag; u32 pad; u64 payload}` with the payload read by the engine at the FIXED
`cmd+8` (tag 1 action-stream ptr, tag 2 label-name ptr, tag 4 remove depth, tag 5
back-to-script, tag 8 morph id+stream). When a record base lands 4-mod-8, natural packing
puts the payload at `cmd+4` (which is then 8-aligned) and the engine's `cmd+8` read
straddles into the next field.

Observed casualty: `B5MENUITEM` char[20] **frame 9's Stop action** — its stream slot read
`0x200000000` (garbage), the enqueue guard skipped it, so the `Selected` state band never
stopped and rolled into the dim `Unselected` band: *"the menu doesn't keep the hover
state."* The f19/f29/f39 stops in the same movie were aligned and healthy — which is also
why the payload offset looked like it "depended on the bundle set" during earlier
debugging (it depends on each record's accidental alignment, not on the set).

**224 of 290 bundles** carry at least one such record (RESULTS.bundle alone: 145).
Tag-3 place records are naturally immune: the engine computes their body address as
`align8(cmd+4)`, which self-adapts.

The repair tool covers this too (same run): misaligned tag-1/2/4/5/8 records are decoded
with the natural-packing rule, re-emitted aligned in the appended block, and their
command-array slot patched. After repair the hover state persists and swaps correctly.

**Emitter fix, restated to cover both:** 8-align the write cursor before EVERY frame
table *and every command record*, and emit explicit `{u32, u32 pad, u64}` layouts.

## Detection

A movie def whose `(chunkBase + framesOffset) % 8 != 0` is affected — that single test
finds all 113 bundles (scanner logic lives in the repair tool; a standalone scan variant
was used during diagnosis). No false positives observed: every healthy table in the drop
is 8-aligned.

## The repair (what `apt8_fix_frametables.py` does)

Pure **data** repair — no engine change, no content change:

1. Walk the apt chunk: root char + every `type 5/9` char in the root's charTable.
2. For each movie whose frame table is misaligned, decode the packed records with the
   natural-alignment rule (`count = u32@cursor`, `cmds = u64@align8(cursor+4)`,
   `cursor = that + 8`).
3. Re-emit them as a correct 8-aligned stride-16 table **appended at the end of the apt
   resource block** (offsets are chunk-relative, so appended space is addressable and
   nothing inside the resource shifts), and patch the movie def's `framesOffset`.
4. Repack the bnd2 container (the apt entry grows; later mem0 entries and the mem1/mem2
   stream offsets shift; entry size words are patched).

Idempotent in effect: repaired tables are aligned, so a re-run finds nothing.
Run it after staging any fresh GUIAPT64 drop:

```
python tools/assets/bundles/apt8_fix_frametables.py build/game/GUIAPT
```

## The real fix (for the GUIAPT64 emitter)

Align the output cursor to 8 **before writing each frame-record table**, and emit records
as the explicit fixed layout `{u32 count; u32 pad=0; u64 commandArrayOffset}` rather than
relying on struct packing. (Equivalently: `#pragma pack` is not the issue — the missing
*table-start* alignment is; both fixes together make the output byte-identical to the
healthy records.)

Note: the retired `apt_widen_4to8.py` converter had the same bug class (its malformed
`char[15]/[23]/[36]` TITLE_SCREEN02 frame tables were worked around with engine-side
skip guards at the time), which suggests shared lineage in the emit logic.

## Verification (2026-07-05, repaired drive set active in `build/game/GUIAPT`)

- Menu items show their localised text (`$TITLESCREEN_MENU_NORMAL` / `_BEATTHETEAM`).
- "HD Compatible for Optimal Gaming" composes again.
- The help-prompt ControllerButtons glyph composes **and** its `select` state applies
  (previously a standing FLAG).
- Up/down navigation state swaps clean; no crashes through the menu stress run.

## Set provenance (so nobody stages the wrong data again)

| Location | Format | Status |
| --- | --- | --- |
| `build/game/GUIAPT/` | native-8 `1:7:8` | JeBobs' drive set, **repaired** by this tool — the active data |
| `Downloads/burnout-paradise-907389d186ed/GUIAPT/` | native-8 `1:7:8` | JeBobs' drive set, pristine (pre-repair) |
| `Downloads/burnout-paradise-f794573e2e48/GUIAPT/` | native-8 `1:7:8` | old `apt_widen_4to8.py` converter output — retired |
| `build/game/GUIAPT_Unmodified/` | console `1:7:4` | untouched console originals — the 64-bit engine cannot load these; do **not** stage |
