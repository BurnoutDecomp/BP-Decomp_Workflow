# Vehicle, deformation and props source checkpoint

The 147-site batch covers VehicleManager 83, Deformation 48 and Physics Props 16.
Vehicle source 4be7f005 is integrated at 2c270c6e. Five changed C++ TUs compile,
with no new faithfulness findings. Deformation/Props registration bodies were
already present and audited without a registration rewrite.

The combined source review failed three source details: editable wheelie sine,
takeoff ramp refinement/order/exceptional predicates and unsigned compression
preset validation. Original sine and both repairs are now pushed on the recovery
pipeline at c1f551e3 (source checkpoints 38b6a739 and ceb88eab). One independent
supplement is reviewing them while grouped CPU validation runs. Native behavior
remains pending. The original failed report is retained.

Reset Sensors is a confirmed original no-op; see DEFORMATION_NOOP_20261012.md.
Other readerless or incompletely attributed controls remain unclassified.
The original Prop velocity label/store discrepancy is preserved.

Frozen maps/reports live under scratch/DEBUG_MENU_1011/recovery_lanes in
vehicle_packet, physics_props_packet, review_vehicle_props_147 and
review_vehicle_props_147_repair. Handling is separately pushed through b5d927fb:
registration, observer, traction leaves and grip windows/graphs are recovered,
but RenderWorld/HUD and listed helpers remain incomplete. Its 28 sites remain
outside the source-covered union and no test or runtime verdict is claimed.
