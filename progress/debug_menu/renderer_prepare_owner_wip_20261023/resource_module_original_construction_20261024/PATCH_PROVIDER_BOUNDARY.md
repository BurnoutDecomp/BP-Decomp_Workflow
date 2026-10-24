# Genuine PatchManager construction dependency

ARTIST828F0980 makes **two** lane-zero requests of0x4000 bytes at alignment16 with null names. Their distinct returned pointers are passed in r4/r5 to828E9BC8 with r6=4096. It then clears mbPatching and publishes the actual manager. Current785 instead makes one0x8000 request for interleaved entries; that is the wrong target container.

The genuine `CgsContainers::LinearSOAHashTable` already exists. ARTIST828DF260 AddEntry and828DF3E0 FindEntry independently attest length+0, invalid key+4, keys+8 and values+0xC, with unsigned32 division/remainder and four-byte key/value strides. The correct native instantiation uses u32 keys and s32 values; it will retain the current source template's ValueType-first parameter convention. No interleaved compatibility view or invented container is needed.

The exact32-bit Initialize828E9BC8 was absent from the JSON exports. After Root confirmed the private game was closed and authorized the one bounded read, `export_patch_table_read.py` read its248 bytes from the retained owned copy. PID37332 completed in1.7492 seconds, exit0, hidden/BelowNormal/-a, with no analysis/decompiler/cache API. The read confirms the167 assertion, four fields and key-only clear. Root was notified of process completion before its next native launch. The complete definition is now included.

The current PatchManager CPP is unmounted by the shipping build. Its only Construct caller in exact785 is the unactivated original four-input FileSystem owner; the native no-argument path does not call it. Thus replacing this incorrect constructor/container does not require inventing a second table representation for a working native caller. The existing caller/mount evidence will be frozen in the final packet.

Both the existing interleaved descriptor and the forthcoming two descriptors get all identity lanes from the real `rw::BaseResourceDescriptor` constructor. Those lanes are **not uninitialized**. The genuine two requests can use the existing original AllocateMemoryResource helper with the same five-lane/null-name contract.

Construction recovery does not complete the patch scanner. Its existing directory worker omits the original allocator-owned scratch chain and still needs separate recovery before full patch activation. No empty/trap substitute or false readiness claim is included here.
