# Independent SatNav alpha constant supplement

VERDICT: pass

The separate capture supplies the raw multiplier word missing from the original proposal packet. At ARTIST address 0x820552E0, the four bytes are 40 23 33 33: big-endian word 0x40233333, binary32 value 2.549999952316284. This matches the accepted source literal 2.55f.

I inspected the exact x360rd.py source, whose SHA-256 matches the capture: cbfbcdb8eee42c57f8b1392f75b8b20880642f90785cf133185ad7b19cfb2b3d. Independently following its ID1 segment/flag mapping with read-only file I/O reproduced the same four image data bytes. No reader script or IDA process was executed. The image size (320888599 bytes) and modification timestamp (1788019120284893000 ns) match VALUES.json and stayed unchanged across the read.

The retained calibrations record 0x82001C98 = 3f800000 (1.0f), and both 0x8250DA58 and 0x824F7F28 = 7d8802a6 (mflr r12). Their expected values agree with the inspected ARTIST exports; both copied code exports match their actual original files. The earlier transform-helper export also links flt_82001C98 to its 1.0 value. Calibration data words were inspected as retained evidence, not reread; independent image payload reading was limited to the four bytes at the multiplier address, plus mapping metadata.

TriggerSatNavPositionUpdate's frozen assembly loads this exact symbol at 0x8250DB0C and uses fmuls at DB10. The captured word therefore supports the accepted explicit single-precision literal. This adds constant evidence only; it establishes no compiled numerical, fixture, runtime or gameplay result.

All four capture seal entries verify. The four-byte blob SHA-256 is f7660f27d0d5211a9c21dc31c53a7ca08ded0a3744ef76cd587730fb1a0e60e2; capture INTEGRITY.sha256 hashes to 5bbf03208a76f620ef88dd47015cf246f5d44a5cd5f10b6e10f8b40a8ee2346e.

The original proposal's 23 sealed payloads, its seal/sidecar, and all four independent review files remain unchanged. The earlier REPORT.md hash remains cd58be256072568bde827d1456ef46c5026f9e15dd6f08a6cee308d74ccfe4b6. Its statement that the original packet lacked the raw word remains accurate and has not been rewritten.

Bounds: whole-image provenance is not certified by a whole-file hash; this result is bound to the recorded image path/metadata, mapping and retained calibrations. No compiler, fixture, game/native, CI or IDA execution, original edit or source/index mutation occurred. Only this new sibling supplement folder was written. REVIEWED_INPUTS.json records the exact inputs and read bounds; INTEGRITY.json and SHA256SUMS.txt seal this supplement without self-reference.
