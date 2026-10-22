# Paradise Drives freeze: captured, unresolved

The private candidate still freezes after editing a checkpoint and moving the Paradise Drives cursor. Both completed captures fail the required return-to-menu check; all normal executable, config, log and save bytes and modification times remain unchanged. The installed build remains source `5093cdb`.

The first main-thread sample is in `AptValue::findChild`; the second is allocating integer `1` for an ActionScript instruction. Both are inside the nested script call made by `gAptCommunicator.UpdateAll`. These are samples of active script execution, not proof of a cyclic prototype or a lock hang. The XB1 original uses the same unbounded prototype lookup, so no invented guard is appropriate. The next diagnostic captures the actual script body and PC. The small dumps stay local.

The corrected source visibly restores the traffic-light start marker in the retained Paradise frame. Inactive-map half opacity is original behavior. Neither observation establishes that the complete route workflow works.

Hosted run `39846825773` passed all nine selected groups and all 12 output hashes. The audio formatter now has 6 passing checks in addition to the unchanged 16,427 capacity checks; the original-code control still has its six expected failures. This validates the witness formatter, not an audio or menu-freeze repair. Debug behavior totals do not change.
