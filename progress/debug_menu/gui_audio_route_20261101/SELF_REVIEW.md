# Callback self-review before source checkpoint

The mandatory `work postmortem GameSource/Gui/BrnGuiModule.cpp` dossier was generated with original assembly. The changed callback and original callees/data were checked directly, using the retained nine exports and action-table bytes in evidence/.

- ARTIST825112B0 uses five pointer arguments with userData inr3; the unchanged static callback declaration matches. Original constructors pass component/action/label/movie; existing100-byte projection preserves fields0/32/36/68 and truncation at31.
- ARTIST8250BE70 writes raw100 bytes/event457 under the output write lock. Replacing the direct legacy201/112 queue publication with existing AddGuiOutEvent projection restores that boundary; current GetOutEventQueueNonConst already asserted the lock, so no missing-lock repair is claimed.
- Original82F277A8 pointer table contains ON_LEFTSWEEP/ON_RIGHTSWEEP at11/13. Only those two spellings change; unknown strings still select14. No event or action is invented.
- DecFIGS independently corroborates the100-byte component/action/label/movie shape. Its452 ID is older; ARTIST457 arbitrates. Legacy typed201 ABI and Sound compatibility handling are unchanged.
- The candidate actual callback/constructors/queues/consumer/Notify fixture passes323 checks. Exact baseline counterfactual is323/112 with correct original-source mismatch labels, not a compile/setup failure. Resolve/Play boundaries are observed; audible/live behavior remains pending.
- Complete GUI TU compiled against canonical shipping flags/includes. Faithfulness scan found0 total/new smells. Cached whole-TU audit debt outside the touched callback remains unresolved; no full GUI completion or fresh whole-TU parity is claimed.

Fresh source/test review, full link, native GUI behavior, dev integration and normal-build refresh remain pending at this checkpoint.
