# Menu regression handoff — 2026-07-06

Title selection menu regressed today: **no visible hover highlight, no prompt text**
(screenshots show items render but the Selected state doesn't hold and the "select"
prompt string is blank). This note is the clean-start context for tomorrow.

## Status: NOT fixed. Banked deliberately.

What was tried today and did **not** fix the visible symptoms:
- Gated `KB_CLASS_BINDING = false` (`b5-decomp/src/SDKs/EATech/include/Apt/AptDisplayList.cpp:1302`).
  This *did* remove two real but secondary symptoms — the state **oscillation** (0↔1 ping-pong)
  and the literal `PROMPT TEXT` placeholder — but it does **not** restore visible hover or the
  prompt text. Left gated OFF (correct state regardless: single-driver principle). Uncommitted
  in the working tree on branch `l2-drive-clean`.

## Ground truth established

- **Last commit where the menu visibly worked: `36edf039`** (Jul 4,
  "title menu shows its real content — localised items, states, nav, prompt").
- **Regression window: `f3871240..HEAD`** (all of today's Layer 2 work; `f3871240` = "stage A:
  the faithful AptCommunicator delivery chain is live").
- The menu-drive facade `src/GameSource/Gui/BrnAptRuntimeBringUp.cpp` was rewritten today
  (`+848/-323` vs `36edf039`).

## Why it's NOT the obvious suspects

- **Not the shim being skipped.** `GuiComponent::AddOutputAptViewState`
  (`src/GameShared/GameClasses/Gui/Model/State/CgsGuiComponent.cpp`) still calls BOTH the faithful
  path (`FillAptViewMessage`) AND the shim (`AptRuntimeSetComponentKeyValue`) unconditionally.
- **Not the apply logic.** `AptViewStateGotoLabel` (HEAD `BrnAptRuntimeBringUp.cpp:2575`) still does
  the faithful `gotoAndPlay`: `jumpToFrame(frame)` + set auto-play bit `0x40` + `SetDirtyState(true,true)`
  — structurally the same as `36edf039`. The log even reports `apt_state='Selected' (APPLIED)` and
  `helpitem: prompt text set (ok)`. The apply runs; the screen doesn't reflect it.

## Leading hypothesis (unverified)

The regression is in the **tick / frame-control machinery underneath the apply**, which today's
commits made much more faithful — not in the apply itself. Specifically:

- The `Selected` state is a `gotoAndPlay` (auto-play bit `0x40` is set on purpose). With today's
  more-complete tick, the item clip likely now **plays straight past the highlighted frame** instead
  of parking/looping on it → hover never visually holds. At `36edf039` the less-complete tick left
  it parked, so it "worked" partly by under-implementation.
- Prompt text is probably a related re-layout casualty (`SetTextValue` + invalidate →
  `ProcessTextInst`), possibly the same play-past-frame issue on the help-item clip, or the
  localised prompt key resolving empty.

## Suggested first steps tomorrow (verify by SCREENSHOT, not logs)

1. Build `36edf039`, screenshot the menu → the golden reference for "correct."
2. Bisect `f3871240..HEAD` for the commit that flips hover-holds → hover-plays-past
   (likely a doFrameControls / tick / frame-wrap commit, not the facade rewrite).
3. Check whether the item's `Selected` label segment is meant to loop/stop and whether the
   frame-table for that clip has a Stop at the segment end (tie-in: `apt8_fix_frametables.py`,
   the tag-histogram of B5MenuItem's Selected frames).
4. For the prompt: confirm whether the localised prompt string resolves non-empty and whether
   the help-item clip is playing past its label.

## Don't forget

- Kill `Burnout_PC.exe` before building (exe lock silently breaks the link — check exe mtime).
- Build via PowerShell `& cmd.exe /c "tools\build\build_game_exe.bat"` (bash-invoked cmd exits silently).
- The 3 green squares bottom-center are leftover diagnostic probes from the WIP branch (cosmetic).
- `dev` (`277097b9`) also contains the regression (it's past `f3871240`), so it is not a fallback
  for a working menu — only `~36edf039` is.
