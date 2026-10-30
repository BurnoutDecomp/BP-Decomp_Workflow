# Director IOBufferStack tag correction

One-line successor patch against private merged b5 `65f58d20c63dda8f351f672b5b9fc0d30f8a7af1`: change `namespace CgsModule { class IOBufferStack; }` to `namespace CgsModule { struct IOBufferStack; }` in BrnDirectorModule.h. The canonical CgsIOBufferStack.h declares a struct. The prior leaf's class forward declaration was my mistake; MSVC encodes the tag in decorated parameter names.

The original provider compiled its three methods with `PEAVIOBufferStack` while actual GameModule.cpp, which sees the canonical definition first, calls `PEAUIOBufferStack`. This compiles but fails to link. The correction aligns that declaration with its canonical home without changing layout, behavior, argument types or method bodies.

`SOURCE_MANIFEST.json` pins the exact one-file pre/postimages. `PATCH_CHECK.json` proves an LF patch applies and reproduces the exact successor bytes. Old sealed packets and the frozen native source/cache were not edited.

Actual provider/consumer evidence:

* `check_symbols.py` compiles the unchanged production DirectorModule.cpp twice using canonical native build flags and include roots, once with the class preimage and once with the struct successor. Both pass. `OPENED_HEADER_PROOF.json` checks opened source headers against the exact 65f58d20 Git blobs.
* The real cached `BrnGameModule.cdd04bb9.obj` supplies three undefined Director references. `consumer_symbols.txt` and `SYMBOL_CONTROL.json` bind its hash and exact names. The preimage provider resolves none; the successor resolves all three.
* `check_link.py` copies the existing full 3,018-object native linker response, replacing only `BrnDirectorModule.d517525e.obj` with each actual recompiled provider. It uses the original libraries/resource and redirects every output into an owned temporary directory. No substitute bodies, forced unresolved links, function-extraction adapters or native execution are used.
* Preimage negative control: the actual full cached link fails with seven unresolved symbols, including all three Director calls. Successor: it fails with four unresolved symbols, exactly the unchanged RaceCar WorldMap setter and three QuantisedVector compression symbols. `LINK_CONTROL.json` proves the unresolved sets differ by precisely the three intended Director methods.

The bounded regression control passes. The whole executable still requires the four unrelated providers; this packet does not claim a complete link or native replay success. Please review the one-line patch and return `VERDICT: pass` or `VERDICT: fail`.
