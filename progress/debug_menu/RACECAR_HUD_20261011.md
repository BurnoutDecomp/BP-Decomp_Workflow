# Race-car HUD and statistics

Six original entries share one assembly review and one isolated drive:

| Original OnActivate site | Control |
| --- | --- |
| #0001 | Render car damage state |
| #0002 | Render car streaming state |
| #0005 | Show average speed |
| #0006 | Reset average speed |
| #0008 | Show player engine state |
| #0009 | Traffic Related |

The component is `BrnWorld::RaceCarEntityModuleDebugComponent`. Its embedded
owner and registration were repaired in the earlier reset-history batch.

## Shared repair

ARTIST `Debug2DImmediateRender::DrawText` @82823DE0 uses its final bool to check
the origin against the screen. The PC code treated it as centering. Its store at
82823EAC sets alignment at TextObject+2C, not multiline at+30. The original text
object stays single-line, uses the exact measured-width/one-height rectangle and
caches unscaled string width. The former PC code enabled wrapping and enlarged
the rectangle to compensate.

Construct @8281A258 clears the font handle, initializes TextRenderer and sets the
vector-font default size. The no-font draw path selects line-list topology 2.
DrawLine @8281C1F0 likewise queues the two original endpoints; it no longer draws
an invented thickness quad. DispatchVertices @8281B6E0 restores the shared
untextured texture state and submits the selected topology without changing the
drawing mode. Native D3D9 quads and solid triangles explicitly select their own
topologies. The unused placeholder font table was removed.

These are shared dependencies. Their repair does not automatically certify every
menu page or other 2D primitive algorithm.

## Original consumers

OnActivate @822C2538 binds the six component fields/action. RenderHUD @822ED4C8
reads the real active-car damage/render state and streamer flags/models across
eight slots. The mean accumulates the player's velocity length each update
(@822D55F8), independently of whether its readout is visible, and displays a
truncated mph value. Reset @822A7B78 clears both the mean and frame count.
RenderEngineState @822C3080 selects OFF/STARTING/RUNNING/STOPPING from the actual
engine enum, using original position, size and green colour. Traffic readout
@822D56E8 requires a valid ground test and reads the player's heading and surface
collision tag; DrawTextWithOffsets @822A7B90 emits the original lines.

Audit findings for IsAttached, streamer bounds and enum increment assertions are
covered by the called GetGlobalRaceCar, IsRaceCarActive and increment helpers.
MaybeDrawText's scalar wrapper and the typed DrawText overload reach the same
original vector call, with scalar-wrapper screen checking always disabled. Garbled PPC pseudocode parameter counts are not signatures.
Other pre-existing 2D findings remain pending.

## Evidence

- Production text-object regression: baseline 2/17, repaired 17/17. It extracts the
  actual draw/construct bodies, uses a real font handle/TextObject, and inspects
  exact bounds, flags, culling, cached width, colour and mode transitions.
  `b5-decomp/tests/run_debug_2d_text.py`. The scalar wrapper also restores the
  original unconditional origin forwarding; its native extra bool is retained
  only for existing caller ABI compatibility and is ignored.
- Native D3D9 regression: 125/125, including production line/box/polygon producers
  replayed through the real native buffer into pixels.
  `b5-decomp/tests/run_pc_im2d_buffer.py`. Its white-state getter is a fixture seam;
  the real shared state was exercised by the earlier 84-check Im3d regression.
- Shipping build: 2949 TUs, zero warnings/errors. Logs:
  `scratch/DEBUG_MENU_1011/build/20261011_162919_debug-hud-observer.log` and
  `20261011_164257_debug-hud-reviewed-source.log`. The latter only changes passive
  observer budgets and removes dead data/comments. Owned-source faithfulness passes.
- Live run: `scratch/bugtest/runs/debug_menu_racecar_hud/20261011_163254`,
  actual exe 97c6e62d0580, build 76d7db4b+dirty. Slot 15 uses a copied profile;
  the private-slot save is restored afterward. No asserts or exceptions.
  With the console closed, the car drove 359.2m and 88 motion samples had positive
  accelerator input. All six actual readout kinds submitted glyph vertices.
  Eight saved registry states supply 40 matching field checks, including cleanup.
  The mean rose above zero; reset cleared both fields after 2769 samples.
- Manually inspected average/reset/engine/damage/streaming/traffic/hidden/restored
  BMPs show readable values at original positions, all overlays hidden and speed
  restored. Reset is followed by fresh accumulation while the car is moving;
  the later reset capture is not expected to display zero indefinitely.

The first evaluator failed one of seven checks because average sampling spent
the 24-line observer budget before later visibility transitions. That report is
preserved as `scratch/DEBUG_MENU_1011/hud-initial-observer-budget-report.md`.
The evaluator now reads all 40 saved field states alongside glyph evidence and
the inspected captures. Re-evaluation of the same run passes 7/7; no second live
run is claimed. The observer now reserves separate transition/sample budgets.

Live coverage includes ENGINE RUNNING, active/inactive damage rows,
loaded/unused streamer slots and Traffic Direction: No Lanes. The other enum and
surface branches are assembly/source reviewed, not separately live exercised.
The full debug menu and other renderer algorithms remain pending.

Combined fresh-eyes review: VERDICT: pass after independent assembly/consumer,
registry and pixel inspection. Final wrapper regression passes 17/17, baseline 2/17;
canonical compile_gate passes. Review packet: scratch/DEBUG_MENU_1011/review-hud-packet.md.

Published b5 commit: 5d946430. Final integrated shipping build
`scratch/DEBUG_MENU_1011/build/20261011_171131_debug-hud-sound-linked.log`
passes 2950 TUs with zero warnings/errors. That build also includes separately
in-flight Sound/Challenge source; their behavior is excluded from this batch.
