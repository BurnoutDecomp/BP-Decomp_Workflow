# Source postmortem

Checked against X360 ARTIST assembly first, then DecFIGS declaration shape. This is source-only; no compiler, fixture, game, native runtime, CI, or IDA operation ran.

- Signature and order: ARTIST 0x8240D31C-0x8240D334 supplies matrix address in r4, Im3d in r5, texture in r6, alpha in f1, white level in f2, and calls the manager in r3. DecFIGS mangling gives the source types and Matrix44 by value. The proposed helper passes the existing input matrix, texture/alpha members, and current white-level local. The call remains under mbRenderCarsTransparent and mbRenderBlobbyShadows and precedes stencil begin.
- Control flow: ARTIST selects the internal buffer, returns for count <= 0, initializes the first-alpha static before the count check, then runs BeginRendering, transform, texture assert/bind, three state binds, one eight-vertex draw per record, and EndRendering. The proposal preserves that sequence.
- Math and vertex contents: It preserves 1.25 fade distance, clamped height ratio, 0.4 spread, truncated cached-opacity fade, spread outer anchors, unscaled axle anchors, spread right vector, and UV rows 0/0.1875/0.8125/1. It writes RGBA8 fields explicitly. The GPU path reads xyz, RGBA8, UV; CPU w is still filled.
- States and sink: Factory slot identities come from existing assert-string-backed enums. Existing Im3d and D3D9 immediate-vertex implementations form the sink. No missing primitive is left in this chain.
- Empty-list gate: The existing PC work gate is count-based; the manager call is not. The proposal separates them. State cleanup is extended only for a nonempty internal shadow buffer, so a zero-count manager call still leaves render state untouched.
- Unresolved producer: Exact c36 source has no live AddShadow caller. Therefore no claim is made that records reach the recovered renderer or that pixels appear. Recovering the producer is a separate required step.
- Validation: Full pre/post source images and diff are supplied. Hosted compile and behavior validation remain undone.
