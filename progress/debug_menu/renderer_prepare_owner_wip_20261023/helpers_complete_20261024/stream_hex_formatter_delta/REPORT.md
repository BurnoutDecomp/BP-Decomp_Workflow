# Original unsigned and pointer formatting dependency

Vehicle's original Entry diagnostic needs the real unsigned hex and pointer formatting contracts. This one-CPP proposal recovers those two canonical CgsDev::StrStreamBase overloads. It fixes current padded output (`0x000000A5`) to original `0xA5`, preserves decimal/HEX/HEXONCE state rules, and restores original no-output behavior for unsigned modes>=3.

ARTIST821F0EC8 passes `%u` in mode0 and `0x%X` in modes1/2, then reloads the live mode and clears2 to0. Other unsigned mode values return without output or mutation. ARTIST Entry stream828E0A90..AC inlines the real void-pointer overload: save mode, set1, emit the address asu32, restore saved mode. The proposal preserves these operations and the current u32 address projection. It adds no new pointer-width policy.

The existing GetPrintModePC provider and shared-log thread policy remain unchanged. Other numeric overloads, format constants, buffer/sink implementations and all bytes outside these two bodies remain unchanged. Existing signed/float/64-bit formatting is not blanket-approved by this delta. The canonical CPP is already shipping-mounted; no source-list or activation edit is proposed.

Full pre/post hashes bind exact source2ce. This is a source dependency correction, separate from Vehicle's caller/operator packet. It changes formatting for existing unsigned/pointer users when composed, so it is explicitly disclosed and requires fresh review. The playable physical source/exe is untouched. No compiler, test, link, CI or native run was performed.
