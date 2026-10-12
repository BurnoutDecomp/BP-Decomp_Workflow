# Repairs from the 199-site source review

The combined review is still running against frozen integration 5ef9611d.
Source corrections are being checkpointed on codex/debug-menu-renderer-environment-fixes
in a separate checkout, so its reviewed snapshot remains unchanged.

fdc74c9b restores two original contracts: sixteen sky/scattering/lighting/cloud
color writes now set the fourth lane to positive zero, and occlusion defaults
are immediate=false, conditional=true. ARTIST DebugToManager827B3B28 stores each
RGB vector with zero W; Construct827F1E00 sets those flags at1E68/1E6C after
loading r30=0 and r25=1. The two-path source checkpoint is pushed and pinned under
renderer_environment_repair_packet. It is unverified pending the combined review
supplement and grouped checks.

Other findings raised during review remain open: the render-target preview's
active-renderer/shadow-state chain, junkyard normalization refinements/full lanes,
index threshold publication before shadow/environment passes and VMX grip-range
flush behavior. These are findings under review, not the final combined verdict.
Native behavior and documented missing query/backend/caller work remain separate.
