# Current-run addendum: known DLC slot-24 SAVE boundary

**Disposition:** the 2026-10-22 failure is a recurrence of the original-broken DLC caption boundary already reported on 2026-10-13. This packet binds the current B5 source, the 5093 executable source identity, the new exception and partial SAVE output. It does not create a new static site credit. The existing `BrnResource::DLCDebugComponent::OnActivate#0001` inventory row remains `pending`.

The earlier immutable finding is [`prior/REPORT.md`](prior/REPORT.md), SHA256 `fb9fc8da4ef1348110d1a4c4291f4316c99c1f7bae64e98868505834381a2074; its manifest is [`prior/manifest.json`](prior/manifest.json), SHA256 `a91f9a0da1a72228b4a1269232f677434dac76aac73732fce0dc6042fc42b774. That report already established the ARTIST null caption at feature index 24 and the original SaveState dereference. The current run adds a matching 5093 exception and partial file. The source paths below are byte-identical at current primary/run commit 5093 and requested private B5 base b6dc5da5.

## What changed since the earlier report

The old report also recorded a separate PC DLC table initialization gap at source 8cbd95c6. That is recovered by current source: `BrnGameDataModule::Construct` calls `mDLCManager.Construct()` and then constructs the DLC debug component; `DLCManager::Construct` calls `g_DLCFeatureAvailability.Construct()`. Current feature index 24 maps to pack 3 and its enabled flag is set true. `DLCDebugComponent::OnActivate` registers pack 3 as `world Pack`, so the current null name is not a stale zero pack mapping or an invalid pack record. The earlier friends-Pack/all-false grouping belongs to the old initialization gap and is not ascribed to this run.

The caption defect itself remains in ARTIST and current source. Constructor 0x826627F8 clears all 25 name pointers and writes string literals only for indices 0 through 23. OnActivate 0x82662B40 still loops while its index is below 0x19, reads the corresponding name pointer and passes it to the grouped bool-registration wrapper. Feature 24 has a valid World-pack index and valid bool storage, but its caption pointer at `this + 0x6C` is still the zero left by the clear.

## Current failure correlation

The current native report identifies a NULL-source read in `CgsCore::StrCat` from `ScriptInterface::SaveState`. The emergency log records `READ 0x0000000000000000`, with `CgsCore::StrCat +0x40 [rva 0x4D7A0]` called from `SaveState +0x285 [rva 0x3FA385]`. The partial `baseline-GuiModule.txt` ends at the last non-null DLC caption, `Leaderboards - Stunt run` (index 23), and contains no GUI variable rows.

The source chain carries that same null unchanged. `OnActivate` passes the generated entitlement path separately from `mapcFeatureNames[index]`; at index 24 the path remains valid (`world Pack/world Pack Entitlement`) while the name is NULL. `DebugComponent::RegisterVariable` uses the path to build the full menu path and forwards the name separately. `VariableManager::RegisterVariable` allocates a normal variable/menu-item pair and calls `Variable::Prepare`; `Variable::Prepare` stores the supplied name pointer directly in `mpcName`, with no null check. No read-only or save-disabled metadata is attached, so the normal defaults include the row in SaveState. The active pool appends registrations in order and SaveState walks that pool by index, which places the bad DLC row after index 23 and before later Gui Module variables.

At the crash site, SaveState calls `StrCat(lacPath, ..., lpVariable->GetName())` without a name guard. `CgsCore::StrCat` reads `src[i]` directly; the reported zero-source read matches that call. ARTIST SaveState likewise loads the variable name pointer from the Variable object and begins scanning its first byte without a null test. This is an original failure path carried into the PC reconstruction, not a lost pointer lifetime in the current pool. The separate temporary entitlement buffer is consumed synchronously to create the menu path; menu path segments are copied into Menu storage. All 24 earlier DLC names are static literals.

The first GUI-owned variable is `Render GUI Objects`, a non-null literal in `BrnGuiDebugComponent::OnActivate`. That module triggers the baseline command, but the global SaveState walk reaches the earlier DLC pool row first. The GUI module is therefore not the null producer.

## Source decision

No production source change is proposed. A 24-iteration workaround would diverge from ARTIST's 25-iteration loop; a synthetic 25th caption would invent source data; skipping or guarding the null would hide the original broken row. `SOURCE_DELTA.patch` is intentionally empty, and the exact b6 preimages and postimages are byte-identical.

For the GUI behavior case, the safe design boundary is to avoid the engine's global `SAVE` command and use readback-only aliases through the actual output/log path. That harness correction is separate from this source-cause addendum. The corrected CASE packet must reject every engine `SAVE` command before execution.

No compiler, C++ fixture, CI job, game/native run, or IDA session was performed during this source audit.
