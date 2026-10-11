# Original empty Reset Sensors action

Final disposition: original-noop for
BrnPhysics::Deformation::DeformationDebugComponent::OnActivate#0019.

ARTIST OnActivate at 82623198 registers Reset Sensors with the folded
CgsSceneManager::CgsCollision::BaseCollisionGenerator::Destruct target. The target
is 8284CB38; its entire instruction body is `blr` (raw word 4E800020), followed by
padding. Its borrowed folded symbol name does not give the action a sensor effect.

The current OnActivate registers DeformationDebugComponent::ResetSensors. That
callback has an empty body, matching the original target. The independent combined
147-site review also inspected and confirmed this empty action. No reset behavior
was added. This direct empty-body disposition does not certify other Deformation
controls or close the batch's separate preset comparison finding.

Original exports: .ida-exports/BURNOUT_X360_ARTIST.XEX/0x82623198.json and
0x8284CB38.json. Production: b5-decomp/src/GameSource/Physics/DeformationManager/
BrnDeformationDebugComponent.cpp at integration commit c1f551e3. Independent review:
scratch/DEBUG_MENU_1011/recovery_lanes/review_vehicle_props_147/SOURCE_REVIEW.md;
raw-image corroboration: shadow_effects_scene_packet/raw_image_checks.json.
