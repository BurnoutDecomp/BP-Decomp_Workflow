# Subsystem writing rules: vendor SDKs, Apt, RenderWare 4, rw::audio::core

Which build is authoritative for each subsystem, and how to read it, is `console-evidence`.
These are the rules for the code you write once you know. The general rules in
[quality-rules.md](quality-rules.md) apply on top.

## Vendor SDKs (EABase, EASTL, EAThread, RenderWare, EATech, ...): test before decompiling

- For `EABase`, `EASTL` and `EAThread` the original open-source code is in
  `b5-decomp/vendor/` and is compiled directly, so those bodies are never decompiled.
- If `work next` or the user hands you a vendor SDK TU, run
  `python tools/work/check_vendor_lib.py <tu_name>` first.
  - **PRESENT**: original buildable source exists. Skip it and block the TU:
    `work block <tu> "Vendor code; original source is present."`
  - **MISSING**: reconstruct it from ARTIST like normal, or provide a documented platform
    leaf when the behaviour is genuinely host-specific.
- Closed vendor SDK binaries (RenderWare and the rest) are reference-only evidence: never
  linked into the game, and their symbols never satisfy the build.
- **PRESENT blocks the SDK's bodies, not its types.** Still recover its public types on
  demand when game code needs a real layout (to replace an opaque blob or an offset poke):
  that is type recovery, not decompilation.
- `work external <tu> "<provider and scope>"` is the durable status for a TU that vendor
  source or a host-platform implementation supplies without reconstructing its console
  internals (STRATEGY.md). It satisfies dependency availability, is not claimable (not even
  by an explicit claim), does not count as done, and `work unblock <tu>` returns it to
  reconstruction. It refuses a TU that is `in_progress`, `compiled` or has an owner. It does
  not certify feature parity.

## Apt (EATech Apt runtime and its glue)

Scope: `SDKs/EATech/Apt`, `SDKs/EATech/include/Apt` and the `CgsApt*` glue.

- **The Xbox One x64 build is rung 1 for Apt.** The `Burnout_External_Xbox_One.exe` export
  (`.ida-exports/Burnout_External_Xbox_One.exe/`, a local input) outranks X360 ARTIST here:
  it is the only native little-endian 64-bit build, so its pointer widths, struct layouts and
  8-byte strides match the PC target exactly. X360 ARTIST and PS3 (32-bit big-endian) drop to
  cross-reference for functions that are unnamed `sub_` in x64: identify them by their X360 or
  PS3 name, then verify against the x64 `assembly` before trusting any layout. A named x64
  symbol's mangled name is the exact prototype.
- **Never let a 32-bit build arbitrate an Apt pointer width or offset over x64.**
  Hand-widening console layouts to x64 is what produced the unfaithful-leaf debt this rule
  exists to stop.
- The x64 build's named public accessors (MSVC-mangled names such as
  `?GetDepth@AptCIH@@QEBAHXZ`, 1-3 instruction bodies) pin exact 64-bit member offsets; its
  large private bodies are unnamed but locatable by call-graph and constant matching against
  the named X360 twins. Use it to verify every native-8 layout or record-offset decision that
  was inferred from 32-bit X360 asm (Apt place/remove records, frame tables, display-list
  nodes, GUIAPT `1:7:8` data). It arbitrates 64-bit widths, offsets and alignment only: it is
  a later retail-era build (expect content drift) and does not displace ARTIST as the
  behavioural spine.
- **An engine stub is an audit failure, not a leaf.** A `Class::method` reduced to a
  `return null`/`{}` stub, or renamed to an `Apt*_<verb>` free-function shim, fails review.
  A leaf is permitted only for genuinely PC-platform code (the D3D9-vs-D3D11 render backend,
  single-threaded threading/mutex/thread-id, host `/alternatename` callback shims, `.apt`
  file-blob offset access) and must be marked `// FLAG PC-platform leaf: <reason>`. The AS VM,
  CIH timeline, GC, scope/variable resolution and value coercions are the ENGINE: decompile
  them faithfully from the x64 build.
- Reviewers fail an Apt TU whose body, or a body it forwards to, is an engine stub. Do not
  trust an Apt ledger `done` without reading the body: `tools/re/hasbody.py` finds it, and
  `work faithfulness --files <file> --all` lists the stub smells already in the file.
- **`.apt` data widening belongs to libapt2; never mint a widener.** Console `.apt` bundles
  are 4-byte-pointer (`Apt Data:1:7:4`); the PC target needs the 8-byte form
  (`Apt Data:1:7:8`). That widening already exists in the maintainer's libapt2 tool (its
  GUIAPT64 writer). Never mint a parallel widener (the `apt_widen_4to8.py` / `.apt4` backdoor
  was exactly this mistake, reverted). If libapt2's `1:7:8` output diverges from the real XB1
  layout, fix it in libapt2 (asset side: `port-assets`), never bend the decompiled loader to
  eat the wrong bytes.
- **The loader stays a pure faithful decompile** of the XB1 native-8 read path
  (`CompleteLoad` = `sub_1408348B0` reads `movieOffset@const+0x18` directly): libapt2 makes
  the data match the loader, not the reverse. Audit failures in the loader: offset
  "accommodations" (reading `+0x04` where XB1 uses `+0x08`), `LocateMovieRoot`-style
  signature scans, `#pragma pack(4)`, and plausibility guards that silently drop records.
  The faithfulness gate flags this vocabulary and the pack pragma.
- **The Burnout Revenge `B4Extern` PDB is naming and shape corroboration only.** A fully
  symbolized X360 build of Burnout Revenge (Apt 0.19.02) ships a real PDB
  (`IDA Files/B4Extern.pdb`, extracted to `references/B4Extern/`, both local inputs; headers
  regenerate with `tools/apt_revenge/generate_apt_headers.py`; its addresses are PDB RVA +
  image base `0x400000`). It names and lays out the Apt engine (AS VM, CIH timeline, GC, the
  `AptValue` and `AptScriptFunction*` hierarchies). Use it to name engine functions the x64
  build leaves as `sub_`, recover the class hierarchy and pin method signatures, then verify
  offsets against x64 and behaviour against ARTIST. It is an older Apt and 32-bit big-endian:
  not offset or width authority, not the behavioural spine. Adopting its layouts wholesale
  into `b5-decomp/src` is the version-drift trap.
- The Apt runtime is a tightly coupled type web: functions that construct complex objects
  through offsets need those struct headers recovered first (types before functions).

## RenderWare 4 follows the Paradise build

- ARTIST is the authority for RenderWare behaviour and game-facing structure: class
  relationships, vtable order, resource-lane count, serialised contracts. DecFIGS supplies
  declaration names and shapes, gated on ARTIST evidence.
- The PC implementation may widen pointers and use native host services, but must not import
  structural drift from a different (later host) revision.
- Isolate genuine platform behaviour with the original compiler flags, especially
  `D_PLATFORM_X360`.
- The canonical vocabulary lives in `b5-decomp/vendor/renderware/include/rw/`. Maintain it
  by hand from the source-of-truth ladder and prove host sizes with `static_assert` under
  `RW_VERIFY_LAYOUT`.
- RenderWare runtime objects (`rw::Resource`) get named members; only the data they process
  (resource blobs walked during fix-up, `rw::collision` data) may use documented raw offsets.

## rw::audio::core types come from the X360 audio PDB

- The `rwaudiocore` runtime (the layer `CgsSound::Playback` sits on: `System`,
  `Mixer`, `SubMix`, `Voice`, `Dac`, `SndPlayer1`, `Decoder`, `PlugIn`, `Send`, `Route`,
  `GainFader`, `StreamPool`, ...) has full type ground truth in the X360 audio
  PDB: an Xbox 360 build of another game, same platform and era as ARTIST, with a complete PDB
  and MAP (in `IDA Files/` beside `B4Extern.pdb`, local inputs).
- Extract layouts with
  `llvm-pdbutil pretty -classes -class-definitions=layout -include-types="rw::audio::core::<regex>" "IDA Files/<audio PDB>.pdb"`.
  For the symbol-to-address catalogue (to find a body in the ARTIST asm), grep the demangled
  forms in its MAP (mangled tail `@core@audio@rw@@`).
- **Width caveat:** it is X360 (32-bit pointers, big-endian). It gives authoritative field
  order, names and types on ARTIST's platform; model the PC layout with x64 widths (widen
  pointers, as in every reconstruction).
- It comes from a different game: use it only for the shared `rwaudiocore` vocabulary, never
  for Burnout-specific `CgsSound`/`BrnSound` shape (that stays ARTIST + DecFIGS).
- The existing `b5-decomp/vendor/renderware/include/rw/audio/core/` headers predate this PDB
  and were hand-guessed: treat the PDB as ground truth to verify and correct them.
