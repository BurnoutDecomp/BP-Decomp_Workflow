# Replay frame runtime recovery checkpoint

The private source24 proposal restores the active frame's original typed Replay
IO chain: PreSim, GUI PreWorld, Sound PreUpdate, late update set, World/GUI/
Effects/Sound consumers, PostSim, PostWorld and resource forwarding. One frame
owner retains and reverses the output lifetimes. It also recovers the actual
Sound channel owner, Replay IO construction/getter and active World/Prop
transfers; the Resource provider is a declared three-file dependency import.

`SOURCE_MANIFEST.json` binds sixteen source files and `combined_source.patch`.
`WORKFLOW_SOURCE_MOUNT.json` binds the three real Sound TUs added to the private
shipping source roster. `FRESH_REVIEW.md` records fresh source approval.
`CONTRACT_RECEIPT.json`, `AUDIT_RECEIPT.json`, `PATCH_CHECK.json`, `gates/` and
the provider packets retain the focused positive and negative evidence.

No game run, full link, recording/playback success, site verdict or count is
claimed. Shared source/game/canonical state and refs were not changed by this
lane. Checkpoint commit objects, when present, are unattached for Root to broker.

Required follow-ons are active: original Replay state-entry/open-file/job
producers; RaceCar/Traffic providers and aggregation; Director serialiser and
ReplayDirector; Sound traffic/in-air/collision/deformation consumers. Their new
private revisions do not rewrite this frozen source composition.
