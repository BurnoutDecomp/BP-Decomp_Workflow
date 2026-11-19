# The byte-match ledger

Everything here is produced and read by `tools/bytematch/` (`ledger.py` is the CI-safe core;
`bytematch.py` the CLI behind `work match`).

## Files

| Path | Who writes it | What it is |
|---|---|---|
| `progress/bytematch/universe.json.gz` | a maintainer: `work match universe` | Every ARTIST function: `[address, size, name, category, area, tu]`. Sizes come from the image's `.pdata` (packed unwind records) and, for frameless leaves without one, the export's instruction count. `category` is `sdk` for bodies byte-identical to an XDK library function, `unnamed` for functions the ledger has not named, `game` otherwise. `meta.providers` maps each SDK body to its `lib:member`. |
| `progress/bytematch/objects/<source>.json` | `work match measure ... --record`, `work match refresh --record` | One record per native source, one function per line. |
| `progress/bytematch/state.json` | `work match refresh --record` | `verified_commit`: every record was current at this `x360` commit. |
| `progress/bytematch.json`, `progress/BYTEMATCH.md` | CI only | The summary: universe x records x the branch head. |

## A record

```
schema      1
source      the source path in the native tree (also the record's own path)
commit      the pushed x360 commit it was measured at
blob        the source file's blob id at that commit
toolchain   "cl <version> flags <fingerprint>": compiler banner + the flags with machine paths removed
measured    when (UTC)
compiled    false when the XDK compile failed; `errors` then holds the first diagnostics
functions   one per function the object defines:
            symbol (decorated), name (undecorated), artist (address) or none,
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
  files. `work match refresh` handles them locally. The object cache keeps each object's include
  list (`/showIncludes`) and the blob of every input, recompiles exactly the objects whose inputs
  changed, and `--record` then advances `state.json`. The summary shows how many commits the
  head is past `verified_commit`.
- A changed toolchain fingerprint (new flags in the branch's `build_x360.py`, another compiler)
  makes `refresh --record` re-measure every object.

## The summary and CI

`.github/workflows/bytematch.yml` runs on b5-decomp's `b5-x360-push` dispatch (every push to
`x360`, from that branch's `notify-workflow.yml`), on any push to `main` touching
`progress/bytematch/` or `tools/bytematch/`, and by hand. It tests the ledger, clones the native
branch without file contents, builds the summary with
`python tools/bytematch/bytematch.py summary --b5 <clone> --head <sha>`, publishes it through
`tools/work/publish_snapshot.py --kind bytematch` (only while that commit is still the `x360`
tip), and asks the work server to sync. The server keeps one history point per distinct summary.

`progress/bytematch.json` holds `meta` (head, verified commit, how far behind), `totals` (`game`,
`sdk`, `unnamed`, `objects`), `areas`, `files`, `functions` (one row per ARTIST function, columns
named in `columns`), `first_exact` (when each exact function first matched; carried from the
previous summary, dropped on a regression) and `recent`.

## Maintenance

- Rebuild the universe when identity changes (new names, new TUs), when the export pack
  `progress/asmaudit_artist.json.gz` is repacked, or when the SDK identification should be
  redone: `work match universe` (needs the XDK's `lib/xbox` and the ARTIST image; tens of minutes,
  most of it the SDK library scan; `--providers <json>` reuses a saved identification). Commit the
  new `universe.json.gz` alone, with a message saying why.
- Records from two contributors never conflict unless both measured the same source. If a push
  of records is rejected, pull, run `work match refresh --record` again at the new head, and
  commit what it writes.
- To start the ledger over (a new branch base, a new toolchain), delete `progress/bytematch/objects/`
  and `state.json` in one commit and run `work match refresh --record` on a clean pushed head.
