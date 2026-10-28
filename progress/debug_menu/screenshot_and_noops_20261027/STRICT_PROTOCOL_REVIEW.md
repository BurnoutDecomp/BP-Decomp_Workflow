VERDICT: fail

The original strict protocol/case/owner-driver acceptance remains failed. This report does not rerun or repair any evaluation and does not change a bound, original receipt or verdict. The separate per-site retained-behavior assessment is in `PER_SITE_REVIEW.md`; it is not a replacement case result or a successful owner-driver join.

Original case `result.json` is exactly SHA256 `61efe5efe015a613e4c77f2639b3bcf457459ba5b075b73098d592f9b81fd99d`: verdict FAIL, as_expected=false, five of six checks pass. The final evidence checker reports: `String '10/27/2026 13:55:00' was not recognized as a valid DateTime.` The raw witness stores the actual ISO timestamp `2026-10-27T13:55:00.8132937Z`; the supplied checker's string conversion and DateTime.Parse call are consistent with a type/culture formatting failure. That is a static inference from the actual error, literal data and source. No checker or repaired checker was evaluated here, and this exception was not treated as proof that other predicates pass.

Original `ROOT_HANDOFF_RESULT.json` is exactly SHA256 `38a707d827b9a431b763a83b6d0d47e4b5fa9fea3be4d705ac9a883de7763466`: canonical_exit=null, trigger_exit=0, canonical_join_confirmed=false, elapsed450.0159999999996s. Its original error states the canonical launcher did not terminate within450s and acceptance is blocked. The outer wrapper throws and defers. The approved protocol requires this failure to remain a strict acceptance blocker. No bound extension or successful retrospective join is claimed.

The game and launcher chronology are distinct:

| Evidence | UTC / actual retained fact |
|---|---|
| Canonical game launch | 13:53:29.6082659Z; exact process start13:53:29.6203373Z; gamePID27524, private image, slot62095 |
| Helper completes requested sequence | 13:56:28.7025303Z; two sites, six states, ten BMPs, no helper deferred sites |
| Canonical loop end | Actual console END420.2s with MaxSeconds420; normal polling granularity, no changed bound or450-second gameplay claim |
| Flow terminal created/written | 14:00:42.1799333Z; original creation-handle cleanup and input reset true, success/exit-request0 |
| Case flow terminal written | 14:00:42.3892366Z; exact canonical status hash, profile restoration true |
| Owner-driver join failure receipt | 14:00:50.9619893Z;450s join expired |
| Original case FAIL written | 14:00:54.7727810Z; DateTime error retained |

The immutable canonical flow source stops and waits for its original game creation handle at `Stop-OwnedGame 'run-finished'` before copying the game log and writing its terminal. Its finally resets input and records cleanup success only after that owned stop/wait succeeds. The actual case source writes `flow-terminal.json` before evaluating its checks. Both harness files match the reviewed runtime hashes. The canonical cleanup terminal predates the driver failure receipt by8.782056s; the case result follows that failure by3.8107917s. The missing450s launcher join therefore does not show that the owned game ran for450s or remained uncleaned. Exact exit UTC is not recorded, so no precise kill timestamp is invented. Cleanup is confirmed no later than the retained14:00:42 terminal, before the join expires. Launcher case/evidence processing continues past the join bound.

Canonical cleanup facts do not turn the driver/case into PASS. Conversely, the strict aggregate failure does not erase the independently inspected native images and raw behavior evidence. The separate report records exactly that narrower scope. All original failure hashes are rechecked in `FINAL_RECHECK.json`.
