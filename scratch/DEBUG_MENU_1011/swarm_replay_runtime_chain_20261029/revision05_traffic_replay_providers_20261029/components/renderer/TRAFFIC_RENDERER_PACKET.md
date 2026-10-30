# Traffic replay renderer follow-on

Private overlay only. This packet extends the sealed traffic producer and codec at
`../swarm_replay_traffic_producer_recovery_20261029/SEAL.json`. It contains two postimages:
`BrnTrafficEntityModule_Render.cpp`, and its owning header with one added
`SubmitCoronasForVehicle` declaration. The header preimage is the sealed producer
postimage. The Render.cpp preimage is identical in f1 and source32 abbc.

`SEAL.json` binds the exact source bytes, LF patch, ARTIST evidence, opened headers,
actual TU compile, source-coupled fixture and omission controls. Fresh combined review
and coordinator integration remain required.

Recovered consumers:

- `PreDispatchUpdate`: recorded vehicle-update mask, recorded transform distance,
  strict render cull, near-to-far ordering and render budget. The recorded branch
  bypasses live visibility, parameter pools and live rendered-last-frame writes.
- `SubmitCoronasForVehicle`: ARTIST flags and all locator cases, recorded transform,
  optional recorded physical locator positions, live no-entity/fatal gates, parked
  alarm/indicator rules, original baked spotlight position and front/rear out vectors.
- `GenerateDispatchLists`: the actual per-vehicle corona caller loop before road
  lights and the geometry pass, preserving per-car output vector indexing.
- `RenderTrafficCar`: recorded type/physical slot/body/wheel selection, original
  fixed replay speed 30 and replay bypass of live interpolation history.
- `RenderTrafficLightCoronas`: recorded manager and recorded active-hull selection.
  The native manager remains 4812 bytes; this change does not infer alignment from
  the console's 4816-byte copy span or change its layout.

ARTIST sources: `8274D900` and replay arm `8274DDE0..8274E504`, comparator
`82708BF0`; full exported `82727BB0` corona body and `82728B08` vehicle renderer;
`8273B438..8273B4C4` corona caller; road selection `8271ECD8..8271ED08`.
DecFIGS owning header supplies declaration shape; ARTIST register use supplies
the writable front/rear vector outputs and behavior.

Checks use actual full `PreDispatchUpdate` and `SubmitCoronasForVehicle` bodies,
the exact caller loop, and source-coupled renderer/road selection fragments. The
fixture poisons live state, covers sparse mask/chunk boundaries and physics slot
24, all locator types 1..13, parked/hidden/live gates, exact light/hull selection,
and bad recorded physics assertion. Six compiling omission controls remove the
recorded predispatch, coronas, render selector, caller loop, light manager or hull
selection; each must fail the corresponding behavior assertion.

The full renderer TU is compiled against the frozen f1 dependencies and sealed
producer overlay, with pre/post private pinning and opened-header provenance.
The fixture imports the frozen engine `BlendTransform` body rather than supplying
replacement transform math.

No game run or graphics hardware dispatch was performed. Outside the exercised
selector/pose fragments, `RenderTrafficCar` has compile evidence only. This packet
does not establish whole-traffic completion, native PC parity, or final gameplay.

Re-run `fixture.py`, the coordinator immutable gate, then `seal.py`. Historical
`recover.py` is not a reproducible authoring recipe and must not be replayed over
these postimages.
