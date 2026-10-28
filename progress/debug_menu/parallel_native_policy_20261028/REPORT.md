# Configurable native concurrency policy

The two harness entry points now accept `MaxConcurrentOtherGames` from 1 through 100, defaulting to 1. A larger explicit limit requires the existing concurrency opt-in, strict ownership, positive slot and private sibling slot/data paths. CLI precedence and case forwarding agree. Normalized duplicate peer images reject. Existing PID/image/creation-time ownership, profile restoration, per-slot locking and owned cleanup remain intact.

Root independently reviewed the exact postimages and reran the actual source-extracted fixture in Windows PowerShell 5 and PowerShell 7: 65/65 in each. The immutable author pre/post/test packet and Root inputs/results are retained under `evidence/`; these are historical proof, not new CI tests. Both tool preimages were revalidated against the latest published workflow before publication.

The limit counts other games. Explicit 100 permits up to 100 other distinct-image processes; it does not claim that 100 real games were launched. Enumeration remains sampled rather than an atomic capacity reservation. Defaults remain backward compatible.

This is workflow-only. No C++ commit, executable/package update, profile operation, game launch or debug-site disposition accompanies it. Each native executor must record the new runtime workflow and actual script hashes separately from its executable's existing build provenance. The installed f06c7a7b image remains built from source 209fb3b9/workflow 4eb229dc; the older 34dd9dad image retains source 00830db6/workflow 78de90f2.
