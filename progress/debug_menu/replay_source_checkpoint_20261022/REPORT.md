# Replay HUD and PC support-status recovery delta02

This separate source proposal composes on immutable B5 82682a7992193892a1911a55a6d20abb9bed46bb, the exact Replay5/Replay8 overlays, and the frozen lifecycle delta02 packet at scratch/DEBUG_MENU_1011/replay_module_lifecycle_recovery_delta02_20261022. Its seal is ff1087db162abb966fc6ce6d55716f425e6681f0524a7b710c6844ded1dc3f9a. Delta02 and all previous review records remain unchanged.

The three changed paths add the ARTIST-backed ReplayModule::RenderDebugHUD body and expose the existing EnableJobThread declaration/body to the WIN32 PC build. The private RenderDebugHUD declaration from delta02 is carried unchanged. The HUD follows the recorded alpha guard, DebugInterface acquire/release, completion percentage, no-space text, fixed position and size, alpha-colored constants, and both alpha updates.

The first delta02 report said RenderDebugHUD was unavailable in retained exports. That was accurate for the standard per-address export directory at that time. The original body was subsequently recovered through a read-only export from a private copy of the original ARTIST IDB; this packet retains the export and process receipt. The earlier delta02 packet is not amended.

The PC EnableJobThread implementation uses the exact unconditional ARTIST assert text, X360 source path and line 247. If the Replay caller reaches it, it preserves the original unsupported status. It does not activate a PC worker or add scheduler policy. PC worker setup remains in its existing initialization path.

Validation is source-only: recovered assembly, original function bytes, DecFIGS declaration shape, retained B5 API sources, frozen delta02 seal, exact 12-path composed pre/postimages, and SHA-256 manifests. No C++ compile, fixture, test, CI, native/game run, or new IDA session was performed by this proposal. No runtime or Replay behavior credit is granted.
