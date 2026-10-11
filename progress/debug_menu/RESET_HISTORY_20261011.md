# Reset-history overlay repair

`Race Car Entity / Show place on track info` now displays the latest reset axis,
vertical line test and intersection mesh. The original toggle is writable again.
The underlying debug component is embedded in its real owner, constructed,
registered and torn down at the console's lifecycle points.

The latest history belongs to whichever car made the request. Accepted empty
results clear the intersection array; full vector lanes and the original ten-item
array's bounds behavior are retained. This is diagnostic storage only.

The repair also removes immediate GPU calls from the 3D debug producer. It queues
the original state, projection and copied geometry commands for the existing
renderer debug pass. Spheres use ARTIST's 34 vertices and 192 byte indices through
primitive 3 (line strip), replacing the three-circle approximation. Native storage
hosts the original render-state parameters. Other primitives, text and the entire
renderer TU have not received a parity verdict.

## Original evidence

| Behavior | ARTIST evidence |
| --- | --- |
| Embedded owner declaration | DecFIGS `BrnRaceCarEntityModule.h:349`, attested at module +0x17CF0 |
| Construct before streamer | `Construct` @822FD898, call @822FD924 |
| Register | `Prepare` @82303E78, @823040C4..823040CC |
| Owner teardown | `Destruct` @822F3DC0, @822F3E1C..822F3E54 |
| Last queued line endpoints | `PostSceneUpdate` @822D3168, @822D33E0..822D33F8 |
| Clear/copy accepted intersections before placement | `PrePhysicsUpdate` @822F6DF8, @822F70BC..822F7100 |
| Copy reset transform before active-car branch | `ResetActiveRaceCar` @822F4880, @822F48A8..822F48E0 |
| Menu and render calls | `OnActivate` @822C2538; `RenderWorld` @822ED308 |
| Debug command lifecycle | `Begin` @8282C780; `End` @828243F8; `DispatchVertices` @8281B8F0 |
| Projection/depth and native state parameters | @8281B998, @828244C0, @82818B68 |
| Sphere topology and vertices | @82816EC0, @82817018, @8281D930 |

`DispatchVertices` deliberately retains both consecutive global depth-state
writes from the assembly. Portable host trigonometry implements the original
sphere math; this is not a bit-exact trig claim.

## Validation

- Producer regressions: line endpoints **12/12 + 4 structural checks**; accepted
  results/empty clearing **16/16**; unconditional reset transform **3/3**.
  Their pre-fix results were 10/12, 15/16 and 0/3 respectively.
- Native production command/shader/pixel test: **84/84**. It checks deferred
  drawing, frozen copies, state/projection changes, sphere topology and pixels.
- Canonical compile gate and faithfulness pass. The shipping driver compiled and
  linked all 2,949 TUs without warnings/errors. A running user game locked the main
  executable, so the same source list, flags and driver linked to an isolated path.
- Combined fresh-eyes review covers both ownership/history and renderer changes.

The final live evidence is
`scratch/bugtest/runs/debug_menu_reset_history/20261011_152920`, executable
**9c24d98e4a91**. The case uses slot 15, copied `DISCO_collect_base.sav` (SHA1 prefix
`1AC773F168B3`), real console commands and F2/F3 bindings. It passes **8/8**, with
zero asserts/exceptions. The renderer reports two draws/200 vertices for the
single-intersection history. Shown/hidden/restored frames were visually inspected;
the original mesh appears, disappears and returns, including on a traffic car
after the shared history advances.

The visibility metric counts bright geometry in this fixture's lower scene;
shown/hidden/restored counts are **14096 / 5946 / 12349**. This is a bounded visual
witness, not a general scene-image parity metric or a performance measurement.

Earlier run `20261011_145820` (exe **7f82cfd0c5b0**) passes the data/console checks
but fails the final renderer/pixel checks (**6/8**); counts are
**6177 / 5945 / 5784**. Run `20261011_145005` also reproduces the old read-only
control. Neither data-only success nor a held garage frame obscured by a modal was
credited as visual completion. The flow log's executable banner is authoritative
when re-evaluating saved captures with `-NoRun`.

The passive `BRN_RESET_HISTORY_TRACE` witness is capped at 24 component lines and
12 renderer-dispatch lines. The source and tested executable include that witness.
Six registration sites are now verified; the remaining 1,348 sites and expanded
dynamic rows remain pending.

Implementation published as b5-decomp commit `82a36373`.
