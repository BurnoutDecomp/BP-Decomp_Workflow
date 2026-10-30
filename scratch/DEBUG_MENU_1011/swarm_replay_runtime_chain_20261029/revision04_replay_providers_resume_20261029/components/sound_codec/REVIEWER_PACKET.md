# Sound replay stream closure

Read-only review of two changed paths against source f32c7d531d98c811a89f69a6f868fdc10b74716a.
Return explicit `VERDICT: pass` or `VERDICT: fail`. No source/ref/ledger/game edits or native audio claim.

The prior SoundLogic registration, traffic producers, collision/scrape capture and deformation
are already in V3. This delta repairs their concrete shared stream boundary in SoundSerialiser.cpp.
The accompanying header change only corrects the stream-format description.

ARTIST SoundSerialiser::ReadAsQuatPos826534E0 calls sub82652640. WriteAsQuatPos82658EC8
calls sub826525A0. Both exact raw exports in evidence/ show seven calls to the aligned
float primitive, position xyz followed by quaternion xyzw. The existing QuantisedQuatPos
Read/Write declarations have no bodies in V3, and their comments incorrectly suggest a
12-byte quantised format. This delta restores the actual original seven-float protocol
within the owning Sound methods. The quaternion/matrix conversion remains the existing
recovered implementation. No provider shim, new backend or 12-byte quantisation is added.

The other defect is SoundSerialiser::Read826590E0 at826592D0: `stw r27,0xBC(r30)` with
r30=record+0x1C clears the complete32-bit sample marker at record+216. V3 instead writes
one byte, preserving the high bytes of a previous-1 or stale sample index. The corrected
read writes the canonical OutputCollision::miSampleID for each streamed collision. It
preserves the neighboring bin index and unrecorded entries. Existing scrape initialization
and unstreamed fields are unchanged.

Inspect preimage/, postimage/, sound_codec.patch, SOURCE_MANIFEST.json, PATCH_CHECK.json,
SEAL.json and the exact ARTIST assembly. The delta adds no source mount: the Sound TU,
BaseSerialiser, SoundSerialiserFrame and StaticLayout providers are already present.

The final immutable actual-TU gate uses canonical flags from workflow5a73986a and the
existing85MB f1 Git snapshot plus all38 exact changed V3 source blobs, with no mutable
shipping src include. RESULT.json records the complete opened-header proof. REGRESSION.json
records the full production SoundSerialiser.cpp and real Base/Frame/StaticLayout providers,
not extracted replacement bodies. Only assert reporting is observed by the fixture.

The fixture independently checks the28-byte wire sequence and supplied quaternion/position,
then sends actual collision/scrape/traffic banks through the production writer and reader.
It covers zero/full bank sizes, all three traffic counts0/1/6, stale32-bit sample sentinels,
and typed consumer fields. Negative controls restore the one-byte defect, omit the marker,
always reset slot0, omit position writes, omit a quaternion read, and reverse the wire order.
Each is a separately compiled full production TU and must fail at runtime.

These are component stream semantics and compile/link evidence. Whole game replay entry,
live recording/playback, native audio output and audible parity remain unverified. Root
owns integration and publication. Do not credit this delta as native audio delivery.
