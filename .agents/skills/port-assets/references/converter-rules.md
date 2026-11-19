# Manifest rules and the stager's mechanics

Source of truth: `tools/assets/build_game_data.py` (its module docstring, `Rule`, `WorkerRoots`,
`guard_out`) and the header of `tools/assets/game_data_manifest.toml`.

## A rule

```toml
[[rule]]
id     = "world-support"
match  = ["PVS.BNDL", "WORLDCOL.BIN"]
action = "convert"
tool   = "bundles/world_support_transcode.py"
argv   = ["--bundle", "{src}", "{out}"]
verify = ["bnd2_platform=4"]
why    = """The evidence this mapping rests on: the converter's docstring, the consumer, the measurement."""
```

- **Order matters:** the first rule whose `match` accepts a file wins (globs over the
  source-relative path, case-insensitive). A file no rule matches falls through to the built-in
  catch-all and is reported UNHANDLED.
- **Actions:** `convert` (run `tool` with `argv`; the product must satisfy `verify`), `copy`
  (byte-for-byte, only when the file needs no change), `skip` (the PC build does not want it),
  `generate` (a product with no 1:1 source, e.g. `schema.vlt`), `unhandled` (needed, no converter
  yet; `reason` is required). A `copy` of a platform-2 `bnd2` is a manifest bug and `--dry-run`
  flags it.
- **Keys** (the stager's `Rule`): `id`, `match`, `action`, `tool` (relative to `tools/assets/`),
  `argv`, `verify`, `why`, `reason`, `isolate` (`"volatility"` gives the tool a private resource
  store), `produces` (where a tool that only writes under `ROOT/build/game` leaves its product, to
  be collected from the worker root), `out_name` (rename the product), `generate`-rule keys
  (`inputs`, `outputs`, `stage_in`, `cwd`, `produces_dir`, `out_subdir`), and `requires` (a list
  of `{ path = "...", fix = "..." }`) with `requires_fix`.
- **Placeholders** in `argv` / `produces` / `out_name`: `{src}` `{out}` `{srcdir}` `{outdir}`
  `{name}` `{stem}` `{ext}` `{src_rel}` `{out_rel}` `{srcroot}` `{outroot}` `{repo}`
  `{workroot}`, and `{tok0}`, `{tok1}` ... (the underscore-split tokens of `{stem}`:
  `VEH_PUSMC01_AT` gives `tok1 = PUSMC01`).
- **Verify expressions:** `bnd2_platform=N`, `nonempty`, `min_size=N`, `magic=<ascii or 0x hex>`.
  A miss is a FAILURE: the half-written product is deleted so a re-run retries it, and the run
  exits non-zero.
- Every rule carries `why`. A constant without provenance is a guess, and so is a mapping.

## The mirrored worker root

- Each job slot gets `<out>/.build_game_data/work/w<N>/`: a copy of `tools/assets/` (without
  `__pycache__` and `out`) and of `build/tools/{yap,volatility}`, plus empty `build/game/` and
  `references/` folders.
- A converter that computes `ROOT` from its own `__file__` therefore writes into
  `<workroot>/build/game`, never into the real `build/game` (another agent's live run directory),
  and Volatility's exe-adjacent resource store is per worker, so parallel world-bundle conversion
  cannot race.
- `tools/build/` is not mirrored: a converter cannot import `build_config.py`. The stager passes
  configuration in as environment variables (`BRN_X360_ROOT`, `NUSHADERS_TUB` ...).
- `--keep-work` keeps the worker roots after the run, for debugging.

## Preflight

- The binaries a rule needs (`YAP.exe`, `Volatility.Cli.exe`) are read out of the converter's
  own source, following its local imports: nothing to declare. An executing run with a missing
  one stops before any work, instead of failing one file at a time for hours; `--dry-run` only
  reports.
- `requires` with `requires_fix` covers what no scan can find (the nushaders HLSL tree for
  `SHADERS.BNDL`).

## The caches

- `<out>/.build_game_data/state.json`, per product: the source size and mtime, the rule id, a
  signature of the converter script and of every local module it imports, and the product's own
  size and mtime. A re-run skips whatever is still current; the state is checkpointed every
  minute, so an interrupted run resumes cheaply. `--force` redoes only the selected items and
  leaves the rest of the cache standing.
- It cannot see inputs a converter reads from elsewhere (the nushaders HLSL tree, an external
  data folder). `build shaders` and `build file` force a re-convert for that reason.
- `build/portcache` is a content-addressed cache of Volatility resource ports, shared by every
  job slot and every output folder; a hit is byte-compared with the stored input before it is
  served. `--no-vola-cache` disables it; `--verify-cache` re-runs the real path on every hit and
  fails the run on any mismatch.
- YAP's packer is not byte-reproducible: it writes uninitialised heap into the alignment slack
  between regions (16 packs of one directory gave 5 distinct bundles, differing only there). A
  byte difference between two packs is not a cache or converter fault until you have checked
  where it is.

## Output safety

- `--out` may not resolve to or inside `build/game`, `b5-decomp`, `tools/`, the source folder or
  the repository root; C: needs `--allow-c-drive` (a full C: has presented as fake game bugs);
  the run refuses when the destination volume lacks the space the plan needs.
- Nothing on the deny list is ever written into the output (`obj/`, `_staging_uiassets/`, dated
  backup folders, `*.x360` sidecars, logs, linker maps); a sweep after each run removes anything
  a converter dropped there anyway.
- `--borrow-dir` only ever stats the exact relative path it wants; it never walks the folder.

## The browser converter

- `convert-assets.cmd` opens a local UI (bound to `127.0.0.1`, with a per-session token) over the
  same manifest and converters: file and folder selection, format detection, isolated workers,
  progress and logs. Outputs are staged privately and published atomically after the manifest's
  checks pass; a replaced file is backed up under `<output>/.asset-converter/backups/<run-id>/`.
  The destination must be outside the source, the tooling tree and `build/game`.
- `bash deploy-converter.sh <hostname>` hosts it publicly on Ubuntu
  ([deploy README](../../../../tools/assets/converter_ui/deploy/README.md)).
- A change to manifest routing or to a converter's command line: run
  `python -m unittest discover -s tools/assets/converter_ui -p "test_*.py"`.
