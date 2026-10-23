# Root static review of Road Rage delta04a

VERDICT: pass

Reviewed complete proposal seal: 23525b2b9f9c4ef000473b479b0fcff9d52277a9ad3ef3fc6715e98bc3447ac8 (56 members rehashed).

Preactivation only registers the original TakedownManager controls after an actual engine-RUNNING sample. The sole F2 callback still requires actual mode3/state2, HUD0/target, no accepted producer in that interval, an observed empty player output queue without a later nonempty read, and a fresh postactivation >=55mph player sample. No game source, AI override, score write, queue clear or global input is added. Stage, Run, reporter and watchdog remain byte-identical to the independently reviewed delta03 composition.

Root found that delta04 selected the new early engine wait in its transcript check, making its later-motion order impossible. Delta04a corrects only that search: anchor must be present, then IndexOf starts at that anchor. Both waits remain distinct; missing anchor leaves -1 and fails. Read the full Case check and helper delta directly.

Exact source/executable/host/runtime bindings remain Root-owned. Template source-file capture_parent_head labels are stale historical metadata; Root will record the actual physical 8d67 parent when binding. Actual file SHA checks are mandatory. The existing flow postimage is b972 and runner preimage is2f6b; no runner change until these RR runs finish.

Both earlier native attempts remain FAIL with zero F2 taps. Their mode/motion/AI observations explain setup changes but supply no count/timer acceptance. This is a static pass only. Native producer-versus-reader counts and actual baseline/post-event/later timer BMPs remain required. Forced original callback is labelled as debug stimulus, with no organic-collision or victim-active claim. No native execution occurred during this review.
