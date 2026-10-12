# Repairs from the 199-site source review

The frozen 5ef9611d batch received VERDICT: fail with eight concrete source
findings. All 29 source pins and the snapshot matched. The read-only report is
scratch/DEBUG_MENU_1011/recovery_lanes/review_pipeline_199/SOURCE_REVIEW.md;
SHA-256 99e4ce96d059aace57feb3fb46142de5b5846d58ced260a7ccde025a254986dd.

Recovery continues in both Luna lanes during these repairs. Source candidates
are committed and pushed separately before grouped checks or final entry verdicts.

| Review finding | Pushed source candidate | Remaining check |
|---|---|---|
| Preview shadow-state / active-renderer bracket | Sol renderer-state-chain lane in progress | Full typed bracket, mount/link, focused checks and review |
| Preview packed RGBA lanes | d2a25d16 | Compile, grouped checks and review |
| Occlusion immediate / conditional defaults | fdc74c9b | Focused checks pass; review pending |
| Threshold visible before shadow / environment passes | d2a25d16 | Compile, grouped checks and review |
| Sixteen transferred color W lanes | fdc74c9b | Focused checks pass; review pending |
| Junkyard unconditional refinements and full lanes | 8743b279 | Focused checks pass; review and numeric model limits remain |
| Unordered clock-delta sign choice | 8743b279 | Focused checks pass; review pending |
| Grip ranges: VMX flush versus scalar initial scale | 8743b279 | Focused checks pass; review pending |

Root branch codex/debug-menu-renderer-environment-fixes at 8743b279011bb94739c19955c951b472619c05ef
has the five default/math source candidates. The changed Sky and grip C++ TUs
pass the canonical compile gate, with zero new faithfulness findings. Their
three-path versioned snapshot is renderer_environment_repair_packet/checkpoint_8743b279.
Sol branch codex/debug-menu-renderer-state-chain continues the three renderer
findings; d2a25d16 checkpoints the packed-color and threshold-publication fixes.
Root repairs and fixture235701ca are integrated and pushed on the feature branch.
The frozen review ZIP retains5ef9611d; the renderer branch remains separate.

The junkyard implementation explicitly models the reciprocal-square-root seed
and scalar dot product. Exact hardware seed bits, dot-product rounding, NaN
payloads and floating status remain unverified. Native behavior, query/backend
and caller gaps remain separate. Source packet coverage stays 711/1354; final
entry dispositions stay 25 verified plus 3 original no-ops, with 1326 pending.

The production-body environment/grip fixture passes54/54 checks. Extracting the
pre-repair5ef9611d bodies and declarations with the same fixture fails28 checks,
covering each of the five root findings. Source/header revision shadows are used
for the negative control. Logs are root_math_pass.log and
root_math_negative_5ef9611d.log under the repair packet. Typed environment/window
spies establish bounded CPU contracts; no full lifecycle/native claim follows.
