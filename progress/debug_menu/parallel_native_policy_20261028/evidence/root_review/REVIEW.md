# Configurable native test concurrency

VERDICT: pass

Root independently reviewed the two-file proposal against workflow 54a7fd30253542a9b001923b4aad206a33b4e379 and authenticated every author manifest member and both exact Git preimages. The approved postimages are:

- tools/tests/run_case.ps1: ae52582150424b48befd35972179d4f1a8ca04af0862a98355a744afcdae1247
- tools/diagnostics/flow_run.ps1: 4b646fcf24f385290742bd15261ea5074c9e07200561a4a2404499310318f5ae

MaxConcurrentOtherGames defaults to one and permits an explicit value from one through 100. Increasing it requires the existing concurrency opt-in, strict ownership, positive slot and private path pair. CLI and case forwarding agree. The count no longer imposes a two-game ceiling on explicitly opted-in tests. Existing PID, image, creation-time, private profile and cleanup ownership checks remain. The new duplicate normalized peer-image rejection prevents a previously unreachable collision among multiple peers.

Both independent executions of the actual source-extracted guard, argument and AST tests passed 65/65: Windows PowerShell 5 and PowerShell 7. Inputs and outputs are retained in this review's ps5 and ps7 directories. The tests cover default refusal, explicit capacities, normalization and collision failures, invalid combinations, CLI precedence and forwarding. Other helper function bodies remain unchanged.

This accepts the bounded workflow change, not a claim that 100 real games have been launched or that any debug control is verified. Native runtime adaptations must retain their actual workflow hashes separately from the executable's build provenance. No C++ source, executable, profile or game process changed during review.
