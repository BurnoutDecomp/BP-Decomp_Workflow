# Menu GUI event 23 hosted fixture proposal

This is a new, immutable path-corrected packet; the earlier `luna01` packet is preserved unchanged. The fixture has not been run or wired into CI. It is intended for the hosted Windows/MSVC job and is not a local C++ validation result.

The runner extracts the selected source revision's actual `SoundLogicModule::ProcessGuiEvents` case 23, `GuiEventWireHeader`, `GetGuiPayload`, `EventS32At`, `EventU8At`, `QueueSoundMessage`, and `PostSoundMessage`. It compiles those bodies against that revision's actual `CgsGuiStateInterface.h`, `CgsVariableEventQueue.h`, `CgsMessage.h`, `BrnMessageData.h`, assertion/log/stream headers, and `CgsStrStream.cpp`. It also extracts BootLegal's actual local type-155 `MusicOnMenuStreamEvent` declaration.

The candidate pass sends raw 8-byte event-23 bodies, full 20-byte type-23 records, and full 20-byte BootLegal type-155 records translated to queue id 23 through the actual GUI queue and extracted case arm. It tests each representation with flag pairs `00`, `01`, `10`, and `11`, then reads the actual sound queue and checks the type-13 record, message size, hash, flags, zeroed reserved bytes, and destination `(state manager 0, instance 0, effect 2, OBJECT)`.

The production effect-type argument is checked across its complete call chain. Case 23 calls `PostSoundMessage(mMessageQueue, 13, 0, 0, 2, E_EFFECT_TYPE_OBJECT, lData)`. The extracted helper signature orders parameters as event id, state manager, instance, effect, effect type, payload; its body forwards those five header values to `Message<T>::Construct`, copies the payload, then queues the message using `GetEventId()` and `sizeof(message)`. The fixture checks both queue id/header event id 13 and `GetEffectType() == E_EFFECT_TYPE_OBJECT` along with all destination fields.

The B595 negative control extracts the unchanged old case 23 and the same helpers. It requires all four raw-8 values to mismatch numerically, while full type-23 and translated type-155 compatibility cases pass. The raw negative-control pointer is a padded, correctly typed 20-byte event object declared as size 8, so legacy reads at +12/+16/+17 stay within valid storage. Candidate raw-8 records go through the actual queue.

## Hosted invocation

The intended installed files are `b5-decomp/tests/run_gui_menu_music_wire.py` and `b5-decomp/tests/GuiMenuMusicWire.cpp`. Run from the workflow root with the corrected candidate and B595 control revisions pinned below:

```powershell
python b5-decomp/tests/run_gui_menu_music_wire.py `
  --rev 829305f8a5db176ec62f2f2cc406c812e4a46f8b `
  --control-rev b595d61d2440ca94d61aa8fa610ab0bf6048cc66 `
  --output-dir scratch/DEBUG_MENU_1011/menu23_wire_fixture_20261023_delta04_root/out
```

The packet also has a validated scratch fallback invocation:

```powershell
python scratch/DEBUG_MENU_1011/menu23_wire_fixture_20261023_delta04_root/run_gui_menu_music_wire.py `
  --rev 829305f8a5db176ec62f2f2cc406c812e4a46f8b `
  --control-rev b595d61d2440ca94d61aa8fa610ab0bf6048cc66 `
  --output-dir scratch/DEBUG_MENU_1011/menu23_wire_fixture_20261023_delta04_root/out
```

The runner resolves an installed `tests/` directory as `B5_ROOT = HERE.parent` and `WORKFLOW = B5_ROOT.parent`. The scratch fallback is accepted only when `HERE.name` is exactly `menu23_wire_fixture_20261023_delta04_root`; it uses `HERE.parents[2]` as the workflow root. Both layouts validate `b5-decomp/tests/fxgs_common.py` and `tools/build/msvc_flags.txt` before importing the shared harness. Other locations fail closed. `--source-root <b5-decomp-root>` is also supported for the candidate source; the B595 negative control still comes from `--control-rev`.

The output path must be new or empty. The runner exits `0` only when both candidate and control numeric contracts pass, `1` for numeric failures (including a B595 raw-body false pass), and `2` for extraction, compile, or execution failures. The output retains each `run.cmd`, extracted C++, shadowed selected-revision headers, stdout/stderr, and `result.json` with the compile command, input hashes, process status, and numeric results. The top-level `fixture.json` records both revisions and the overall status; stdout and JSON preserve field observations, failure witnesses, and expected B595 raw mismatches.

This checks source-extracted consumer behavior beginning with the body delivered to `ProcessGuiEvents`. It does not execute the channel-40 drain, measure playback timing, prove audible output, or replace runtime validation.

Root delta03 requires the retained process exit to be zero and numeric receipts to agree with the parsed result. A printed zero-failure summary cannot hide a nonzero process exit. The shared fxgs_common helper and C++ fixture remain unchanged. No fixture or C++ compilation was run locally.

Root delta04 makes every compile/execution failure return2, including a nonzero exit after a zero-failure summary; numeric failures return1. It retains the delta03 process/numeric consistency check. No C++ or fixture execution was performed locally.
