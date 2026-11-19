# Proving a port

A converter that ran is not a converter that worked: a manifest `verify` checks the container,
not the content. Byte and alpha statistics are invariant under permutations (tiling,
interleaving, reordering), so they cannot show that a permutation went wrong. Every port needs a
metric that can actually fail.

## Metrics, weakest to strongest

1. **Per-item differential** (textures). Untiling is a permutation, so histograms prove nothing.
   Score each texture on block-boundary discontinuity for the real port against deliberately
   broken variants (endian swap off, untile off, a uniform swap); the real port must win on every
   non-degenerate texture. Absolute thresholds did not separate the cases; only the differential
   did.
2. **"Zero byte permutations" against an oracle** (the Remaster's little-endian data). A wrong
   field width always produces a byte permutation of the source, so zero permutations among the
   differing fields is strong evidence, but not universal: on deformation data it fired on
   content edits the Remaster made (sensor pairs swapped together with their weights and
   vectors). Against a remaster oracle a permutation is as likely a content edit as a width bug.
3. **Per-slot width contest** (the best so far). For each record-relative slot, derive what each
   competing width hypothesis would emit from the X360 bytes, and tally which one the oracle
   agrees with; report "0 of N slots where an alternative width beats the schema". It
   discriminates per slot and is immune to content deltas (a retuned float disagrees with every
   hypothesis equally). It settled a mixed dword (s16 + u8 + pad) that no uniform width explains.

## Pin record sizes from the data, not by inference

- A count or offset that predicts where the next section starts, in every file of a family,
  pins the record size outright.
- Every section offset re-deriving from the previous `count * stride`, with full coverage and no
  overlap, is a second, independent proof.
- Files whose layout genuinely differs must reconcile exactly: a rig with more tags and fewer
  joints predicted +4,496 bytes and was +4,496.

## The standing checklist for a new porter

- 100% schema byte coverage: reject unclaimed and double-claimed bytes.
- Involution: the swap applied twice returns the source bytes.
- Per-field equality of the big-endian source and the little-endian output.
- Byte fidelity for every char, u8 and pad byte.
- Per-type semantic invariants.
- `SystemExit` on zero ported resources or an unhandled type: refuse by name, never silently
  drop (a bundle carrying resource types with no consumer anywhere is reported, not shipped).
- Re-extract after packing and compare.
- An import-count guard, and the container invariant `entriesOffset + count * 0x40 == dataOffset[0]`.
- Negative controls, each confirmed to bite: a control that cannot fail proves nothing.

`tools/assets/bundles/engine_transcode.py` implements most of this list; its docstring and its
expected-failure controls are a working example to copy.

## The freshness contest: is the installed product current?

- Platform 4 does not mean current. `verify = ["bnd2_platform=4"]` passes on a stale port, the
  size need not change, and a same-day mtime proves nothing (a colour-cube dictionary built
  earlier the same day still differed in hundreds of kilobytes from a fresh convert).
- Re-convert the retail file through its rule into a scratch output folder
  (`build file <name> --out <dir>`; a folder on C: also needs `--allow-c-drive`) and
  byte-compare it with the installed product (`cmp` in bash, `fc /b` in cmd). YAP-packed bundles
  can differ only in unreferenced alignment slack between two correct packs: check where the
  differing bytes are before you call a product stale.
- Sweep a data folder for `bnd2` containers whose platform is not 4 and diff that list against
  the manifest's `convert` rules; what remains must be a deliberate `skip` or `unhandled`.
