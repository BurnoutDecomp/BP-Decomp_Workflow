# Native before evidence and bounded acceptance plan

## Before result

Prior run: `scratch/DEBUG_MENU_1011/route_save_gui_execution_ready_input_delta04/runs/native_20261023_162951_f5da400b/case_a` against the original 9af-derived hosted executable (`31de06d9…`, host `39965534136`). The selected fields from `observer/save1.json` are `success=false`, `request_log_seen=false`, `write_completion_log_seen=false`, `expected_count=1`, and `slot_index=0`. `native_acceptance.json` has `pass=false`, `save2=null`, and `after_profile=null`. The capture showed the empty route / “A SAVE” state, the second accept returned to Summary DONE at 119.6 seconds, and `DiskProfile.sav.after` had `created_count=0`. No request or write followed the observer arm; only the earlier autosave at 60.016 seconds was observed. There was no assert or exception. Case B was not run.

The natural ARTIST event-356 producer stores payload zero, so at 119.6 seconds a correct non-forced request may still wait for the 60-second window to elapse (past 120.016 seconds). A test that stops at 119.6 seconds would not distinguish this repair from a lost request unless it also checks the pending request/next save window.

## Fixed acceptance

1. Repeat the original route/save case after the proposed source change. Observe a single channel-40 event 356 reaching the late drain and confirm the UI returns through the original summary flow.
2. Confirm the unchanged forward path emits the unwrapped 356 once to `mGuiOutQueue`/renderer/registered flows; the new code adds no second record.
3. With the natural zero payload, confirm no force bit is introduced and the save begins only after the existing 60-second throttle expires; confirm exactly one profile write and the expected count increment.
4. Separately exercise an existing force path (event 505 or 358) and confirm it still bypasses the throttle. The menu's event-356 producer is zero, so a payload-one event-356 check requires a separate production-path fixture or a real force-capable producer; that fixture is not part of this narrow proposal.
5. Verify both cases produce no new assert/exception and retain the profile after a fresh launch.

No fixed build or native run was performed here; the above is an acceptance plan for the root-owned hosted build/run.
