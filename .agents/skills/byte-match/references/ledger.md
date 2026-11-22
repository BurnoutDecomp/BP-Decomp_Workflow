# The byte-match ledger

Everything here is produced and read by `tools/bytematch/` (`ledger.py` is the CI-safe core;
`bytematch.py` the CLI behind `work match`).

## Files

| Path | Who writes it | What it is |
|---|---|---|
| `progress/bytematch/universe.json.gz` | a maintainer: `work match universe` | Every ARTIST function: `[address, size, name, category, area, tu]`. Sizes come from the image's `.pdata` (packed unwind records) and, for frameless leaves without one, the export's instruction count minus the trailing zero words (alignment padding, which IDA counts into the function). `category` is `sdk` for bodies the XDK provides (a library function, a CRT save/restore entry point confirmed by name, or a XEX import stub), `unnamed` for functions the ledger has not named, `game` otherwise. `meta.providers` maps each SDK body to its `lib:member` (`import stub`, `module N` for a stub). |
| `progress/bytematch/objects/<source>.json` | the work server's measurement, committed by CI; or `work match measure ... --record`, `work match refresh --record` | One record per native source, one function per line. |
| `progress/bytematch/state.json` | the same | `verified_commit`: every record was current at this `x360` commit. |
| `progress/bytematch.json`, `progress/BYTEMATCH.md` | CI only | The summary: universe x records x the branch head. |

## A record

```
schema      1
source      the source path in the native tree (also the record's own path)
commit      the pushed x360 commit it was measured at
blob        the source file's blob id at that commit
toolchain   "cl <version> flags <fingerprint>": compiler banner + the flags with machine paths removed
measured    when (UTC); a re-measure that changes nothing else keeps the file and this time
compiled    false when the XDK compile failed; `errors` then holds the first diagnostics
functions   one per function the object defines:
            symbol (decorated; an anonymous namespace's ?A0x<hash>@ is stored as ?A0x@, since
            MSVC hashes the checkout's path into it), name (undecorated), artist (address) or none,
            status, score, size, artist_size, and when present first_diff, calls_unverified,
            calls_wrong, data_unchecked, data_wrong, unknown_relocs
```

A function that appears in several objects (an inline or a template) is measured in each; the
summary keeps the best copy, since the linker keeps one.

## Staleness

- A record is **changed** in the summary when its source's blob at the branch head differs from
  the blob it recorded, and **deleted** when the source is gone. Its verdicts are still shown,
  flagged, until someone re-measures.
- Headers are not visible to CI: a heavy native object includes around two thousand repository
  files. The work server's measurer and `work match refresh` both handle them: each keeps every
  object's include list (`/showIncludes`) and the blob of every input in its own object cache,
  recompiles exactly the objects whose inputs changed, and advances `state.json` once every record
  is current. The summary shows how many commits the head is past `verified_commit`.
- A changed toolchain fingerprint (new flags in the branch's `build_x360.py`, another compiler)
  re-measures every object. The server also re-measures every record when the measuring code
  changes (`MEASURE_INPUTS` in `tools/bytematch/wine.py`: the comparison modules, the ARTIST name
  pack, `progress/unidentified.json`, `progress/source_aliases.json`); a local refresh does not.

## The summary and CI

`.github/workflows/bytematch.yml` runs on b5-decomp's `b5-x360-push` dispatch (every push to
`x360`, from that branch's `notify-workflow.yml`), on any push to `main` touching
`progress/bytematch/` or `tools/bytematch/`, and by hand. Runs queue; none is cancelled. A run:

1. tests the ledger and clones the native branch without file contents;
2. asks the work server to measure the commit and waits for it
   (`python tools/bytematch/remote.py measure --sha <sha> --b5 <clone>`). The server keeps the
   commit's status for admins at `/admin/bytematch/measure/<sha>`; a commit that stopped being the
   tip before its turn comes is `superseded`, not measured. `remote.py` checks every record field
   by field and writes the ones whose result changed, unless `main` holds one measured at a
   later commit. A failed measurement does not stop the run;
3. resolves the `x360` tip again, builds the summary there with
   `python tools/bytematch/bytematch.py summary --b5 <clone> --head <tip>`, and publishes records,
   deletions, `state.json` and the summary in one commit through
   `tools/work/publish_snapshot.py --kind bytematch --files-from ... --delete-from ...` (only while
   that commit is still the tip);
4. asks the work server to sync. The server keeps one history point per distinct summary.

The server side (the root runner, its container, the XDK subset and ARTIST bytes it mounts, the
security model) is documented in BP-work-server's `deploy/bytematch/README.md`: maintainer business.

`progress/bytematch.json` holds `meta` (head, verified commit, how far behind), `totals` (`game`,
`sdk`, `unnamed`, `objects`), `areas`, `files`, `functions` (one row per ARTIST function, columns
named in `columns`), `first_exact` (when each exact function first matched; carried from the
previous summary, dropped on a regression) and `recent`.

## Maintenance

- An SDK leaf absent from both the export and `.pdata` can enter the catalogue through
  `sdk_leaf_functions` in `progress/source_aliases.json`. Record its complete archive symbol and
  extent together with an ARTIST branch whose caller's relocation identifies that symbol. The
  catalogue checks that the extent fits a gap and that the branch reaches its start. An archive
  comparison is required even when rebuilding with `--providers`.
- For a leaf supplied by the native tree, `native_leaf_functions` records a disjoint extent,
  an ARTIST branch with a matching native caller relocation, and the source of the compared
  body. The catalogue records its size and name. The regular object comparison determines
  whether the native implementation matches outside its relocation fields. For an exported leaf
  with an omitted tail, include `previous_size` and give a branch inside the exported extent that
  reaches the tail. The omitted range must fit a gap and the complete body must compare exact.
- Rebuild the universe when identity changes (new names, new TUs), when the export pack
  `progress/asmaudit_artist.json.gz` is repacked, or when the SDK identification should be
  redone: `work match universe` (needs the XDK's `lib/xbox` and the ARTIST image; tens of minutes,
  most of it the SDK library scan; `--providers <json>` reuses a saved identification). Commit the
  new `universe.json.gz` alone, with a message saying why.
- Records come from two writers, the bot and contributors, and only conflict when both measured
  the same source. If a push of records is rejected, pull (the bot may already hold the same
  records), run `work match refresh --record` again at the new head, and commit what it writes,
  which is often nothing.
- To start the ledger over (a new branch base, a new toolchain), delete `progress/bytematch/objects/`
  and `state.json` in one commit; the next push's server measurement records every source
  (`work match refresh --record` on a clean pushed head does it locally).
