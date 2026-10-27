# Gameplay95 run 40504852023 retained-data review

**VERDICT: pass — retained hosted-data consistency only.** I checked the actual candidate and both original-control artifacts, their full check-ID transcripts, source/Git bindings, generated production slices, and owned-job cleanup. This does not award native gameplay or rendered-frame credit.

## Verified run evidence

- The run input receipt and worker result bind B5 `1887d92de05d915d53bc4f7645acf84daa39d1bc` and workflow `710832cadba2de0f2a32794dc36ddc95f73f4175`. B5 head equals the parent gitlink, with no override and empty recorded worktree status.
- All **28/28** worker source/provider bindings match the B5 Git source; all **5/5** fixture inputs and all **3/3** production source postimages match. The actual candidate and both old-control Construct/contact slices reproduce their retained extraction hashes.
- The actual stdout files contain the complete ordered **177/177** IDs for all variants. Candidate: **177 checks, 0 failures, exit 0**. Each genuine old source control: **177 checks, 89 failures, exit 1**, with the full expected failure IDs retained. Results and executable hashes rejoin to the worker receipts; stderr is empty.
- All **40/40** listed gameplay artifact files and **14/14** top-level build outputs match their recorded sizes and SHA-256 hashes. The owned worker exited 0 without timeout; cleanup is complete, all handles are closed, and active descendants after cleanup are zero.

The 89 failures per control are intentionally preserved: 57 selected reset checks and 32 enabled contact-output checks. The controls compile and execute the same check plan; they do not pass through a compiler failure.

## Exact boundary

This accepts the retained Gameplay95 source-slice regression data. It does not establish whole-vehicle lifecycle/layout, collision cache or classification behavior, manager singleton/threading, downstream GPU commands, native pixels, or native gameplay. The fixture supplies collision classifications and triangle inputs and observes actual production queue/replay/tessellation on the hosted CPU. No native site disposition is requested.

No runner, fixture, case, checker, compiler, or game was executed during this review. Root's old source/control and screenshot/circle packets remain unchanged.
