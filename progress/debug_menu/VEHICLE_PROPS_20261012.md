# Vehicle, deformation and props source checkpoint

**147 static sites**: VehicleManager83, Deformation48 and Physics Props16.
Vehicle source is pushed at4be7f005 (preceded by829e1d44), integrated on the
recovery pipeline at2c270c6e. Deformation/Props already matched the original
registration/metadata bodies and were audited without rewriting them.

The eight changed paths recover the original VehicleManager page and actual
contact-threshold, in-air/wheelie, forced-acceleration and crash-clamp consumers.
Canonical compile passes all five changed C++ TUs; no new faithfulness findings.
One combined source review is in progress. Wheelie sine lowering is a reported
review finding awaiting the full verdict. CPU/native validation remains pending.

Source maps preserve original callbacks, mutable aliases, per-car storage and
metadata. Reset Sensors remains an original empty callback candidate; no final
no-op verdict is promoted here. Readerless/incomplete attribution and the Prop
velocity-name/store discrepancy remain explicit. No consumer was invented.

Frozen maps/hashes/reports: scratch/DEBUG_MENU_1011/recovery_lanes/vehicle_packet,
physics_props_packet and review_vehicle_props_147. The separate handling packet
at11b37307 recovers26 direct plus2 delegated registrations/window preparation;
known missing render/HUD consumers keep it outside this covered-site set.
