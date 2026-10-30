# Traffic replay producer and codec checkpoint

Private source authoring only. Nine exact postimages and a method-scoped patch are bound by `SEAL.json`; canonical sources and game files were not changed. `TRAFFIC_PRODUCER.patch` is relative to b5-decomp. The preimages match the immutable f1 source baseline after normalizing line endings. The TrafficCull-owned `HandleExternalResponses` function is unchanged and its normalized body hash is recorded in the seal.

Recovered behavior:

- Real TrafficEntitySerialiser header/member and native eleven-pointer replay request interface.
- Original Construct, replay boundary flags, early PreScene clear/read/capture order, and PostPhysics registration/write order.
- Live/entity vehicle intersection, all transform chunks, physical-slot data, active hulls, streamed assets and traffic-light state capture.
- Original full/delta physics codecs, including detached part transforms, 128 skinning vectors, aligned float locators and four 48-byte wheel matrices.
- Real matrix/quaternion conversion, original Y floor of -900, and original skinning descriptor (9/9/9/5 bits; XYZ -2..2, W 0..1).
- Original guarded clear behavior before buffer allocation. The prior reconstruction's unconditional GetStaticLayout return introduced an assertion on the mode-0/null-buffer path; the recovered method is void and follows the original two guards.

The original delta writer's unusual equal-light-tag branch, unequal-glass condition and wheel-row self-subtractions are retained, with instruction addresses beside the code.

Validation:

- Four immutable f1/c9 compile gates pass, with 519/409/13/319 opened headers and no repository header drift. Exact receipts are linked from `SEAL.json`.
- `fixture.py`: producer modes 0 through 7, sparse mask and chunk boundaries, physics slot 24, hulls/assets/lights, locks and native registration/Append pass.
- `codec_fixture.py`: actual source and real F1 quantizers round-trip a complete 1713-byte frame, including an 804-byte physics record, full and delta paths, 90-degree rotation, position/Y floor, first-allocation lifetime and real live-vehicle data packing. Missing-prior-frame negative control exits through the real assertion with code 9.
- Base ReadFloat/WriteFloat bodies are imported from the separately sealed BaseFloat provider; its exact path and SHA are bound in the seal. No fixture substitute implements either primitive.

The TrafficLightManager exposes 4812 named native bytes. ARTIST copies a 4816-byte span; its last 4 reserved/alignment bytes are not emitted by the frame writer. Capture copies all 4812 meaningful bytes, and does not alter the runtime manager type based on an unproven alignment assumption.

Integration still needs the coordinator's World aggregation, BaseFloat provider, build mounts and final combined review/link. Both Traffic serialiser CPPs are absent from the current canonical mount list. Actual playback renderer consumers are being recovered in a separate, approved follow-on packet; this checkpoint proves capture and stream decoding, not application to a running scene. No game run was performed.

The one-off authoring scripts are historical; the sealed postimages are authoritative. Re-run the fixture scripts for their checks; do not replay the incremental source-writing scripts over this sealed directory.
