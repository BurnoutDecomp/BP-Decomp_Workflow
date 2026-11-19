# Review policy: the reverser chooses

Not every TU needs a separate full review; an always-on strong-model review per TU is the
main quota sink. `progress/review.config.json` is a menu and a policy, not an auto-router:
you, the reverser agent, read it and decide per TU whether to review and with what, then
invoke that choice yourself. The reviewer's own procedure is the `review-tu` skill.

## After a clean `work submit`

1. **Classify** the TU as `trivial`, `standard` or `complex` using `review.classify_hints`
   (roughly: one self-contained idiom with no type recovery / a few functions with modest
   control flow / real type or struct-offset recovery, ambiguous control flow, or shared
   header edits that can ripple).
2. **Skip or review.**
   - Skip when `review.enabled` is false (or `review.mode` is `never`), or the class is
     `trivial` per `review.selection_guidance`: the compile gate plus your own self-check is
     the gate. Record it yourself:
     `work review <tu> --verdict pass --notes "trivial; gate-only"`.
   - `review.mode` `always` reviews every TU; `tiered` is this policy.
   - Parity GREEN lets a trivial or standard TU skip the LLM review; YELLOW prefers a review;
     RED means review and look hard at the flagged signal.
   - Otherwise review.
3. **Choose** a provider and model from `providers` (only those with `have: true`) and a
   thinking level inside that model's allowed range, following `review.selection_guidance`:
   the cheapest capable model for `standard`; a stronger model and more thinking for
   `complex`; bump model strength and/or thinking one notch (`escalate_when_unsure`) when you
   doubt your own work (FP precision, signedness, guessed offsets, inferred data tables). You
   make the call, and may deviate with a noted reason when a TU warrants it.
4. **Invoke exactly one fresh-eyes reviewer**, giving it only the packet path(s)
   (`progress/reviews/<tu>.md`, as `work submit` printed). Never share your reconstruction
   reasoning, and never review your own work inline.
   - **In-session subagent.** If you can spawn subagents in your session and the model it
     would run fits the tier (not an unnecessary drain compared with a smaller model reachable
     by CLI), prefer it.
     - Claude Code: `/review-tu <packet path> [<packet path> ...]` runs the reviewer as a
       fresh forked subagent.
     - Codex, Antigravity, other tools: spawn one fresh subagent, give it only the packet
       path(s), and tell it to follow `.agents/skills/review-tu/SKILL.md`.
   - **CLI flow.** If you have no in-session subagent tool, if the in-session model would be
     excessively large or expensive for the tier, or if the model you need is only reachable
     through a host CLI (`claude`, `codex`, `agy`, ...): run the chosen provider's `command`
     template through your shell, substituting `{model}`, `{thinking_flag}` and
     `{packet_path}`.
     - `{thinking_flag}`: an empty string when the model has `"thinking": false`; otherwise
       the provider's `thinking_flag` template with `{thinking}` replaced by the chosen level
       (map it onto that provider's `thinking_ladder`).
     - `{packet_path}`: the path of the packet file. Never inline the packet contents as a
       shell argument: escaping breaks, and it is a command-injection risk.
   - **Quota.** Never more than one subagent at a time, and never one per function: reviews
     are per TU. For a batch, exactly ONE subagent reviews every packet in a single session,
     or run the CLI reviews sequentially in a single command.
5. **Capture the verdict.** The reviewer must output a line `VERDICT: pass` or
   `VERDICT: fail` (one per TU in a batch). Treat a missing verdict line as `fail` (needs
   human review). Record each:
   `work review <tu> --verdict pass|fail [--notes "..."]`. A pass marks the TU `done` (its
   functions `reviewed`); a fail returns it to `in_progress` with the reviewer's notes. Fix,
   re-submit, review again.
6. **No config?** Review every non-trivial TU with the cheapest Claude or Gemini model you
   can spawn.

`--notes` replaces the TU's note in the ledger. If the TU carries a `corrected path <path>`
note (a misattributed TU, see quality-rules.md), repeat it in the verdict notes.
