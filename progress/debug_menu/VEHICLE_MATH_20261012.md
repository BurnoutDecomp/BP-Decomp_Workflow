# Vehicle arithmetic repair validation

The combined 147-site source review and its repair supplement now pass. The
source fixes are pushed at c1f551e3, followed by 57b12968 with reproducible tests
and the renderer enum compile correction. The original failed review is retained.

The focused fixture passes **35 checks** against extracted production arithmetic,
wheelie threshold/bleed and preset dispatch. The original 1.5-degree sine result
3CD6710A is one ULP below the mathematical sine reference 3CD6710B. A pitch at the
upper value must enter the original strict bleed gate. The fixture checks all
three resulting force/velocity rows, equality, the directional guard, edited
power-of-two takeoff ramps, zero/subnormal/NaN/infinite threshold paths, valid
presets and unsigned-invalid presets/null-rig early return.

Negative controls demonstrate that the fixture detects the old errors: replacing
sine with std::sin fails five checks; extracting the old preset at 21ad74ad fails
two. Neither negative run changes production source.

Canonical compilation passes VehiclePhysics.cpp, BrnDeformationDebugComponent.cpp
and the corrected BrnRendererModule.cpp. No new faithfulness findings. The other
three changed Environment/Graphics TUs compiled in the initial group; its sole
error was the corrected renderer enum increment. Full shipping link/native work
remains pending and the current game executable predates these source batches.

No entry is promoted to working from these CPU/source results. Hardware vrefp
estimate bits, NaN payload/status behavior, incomplete original-reader attribution
and live physics/actions remain unverified. Exact hashes and command outcomes are
in vehicle_math_validation_20261012.json. The independent source report remains
under scratch/DEBUG_MENU_1011/recovery_lanes/review_vehicle_props_147_repair.
