# Unsigned/pointer formatter review

Review the two changed canonical method bodies against ARTIST821F0EC8 and the inlined pointer sequence in828E0A10. Check parameter widths, exact formats, unsigned invalid-mode no-op, live HEXONCE reload/reset and saved-mode restoration. DecFIGS attests the actual u32 andvoid* overloads; ignore decompiler vararg residue as a prototype source.

The current PC per-thread GetPrintModePC leaf, pointer projection and other formatting bodies are retained. This source correction affects existing unsigned/pointer formatting when Root composes it; it is separate from the inactive Vehicle caller. Check full exact source2ce pre/post hashes and unchanged-body receipt. No build, tests, link, mount, activation or native validation was run.
