# CI

All workflows live in `.github/workflows/`. b5-decomp has one of its own that matters here:
`b5-decomp/.github/workflows/notify-workflow.yml` sends a `repository_dispatch` to this
repository for every commit pushed to `dev`.

## The workflows

| Workflow | Trigger | What it does | Commits to `main` |
|---|---|---|---|
| `reconcile-status.yml` | every b5-decomp push to `dev` (the dispatch above); hourly repair (`17 * * * *`); manual, with an optional `b5_sha` that must be the full 40-character SHA | audits that exact b5 commit from the packed console cache (`tools/re/funcaudit.py`, `tools/re/stubaudit.py`), reconciles the work server's ledger, exports the durable ledger | `progress/status.json`, `class_homes.json`, `funcaudit.json`, `stubs.json`, `source_status.json` and the `b5-decomp` gitlink, through `tools/work/publish_snapshot.py`, only while that commit is still the canonical `dev` tip |
| `build-and-publish.yml` | daily `0 4 * * *` UTC when the site has no build or the `b5-decomp` gitlink differs from the latest build; manual (always builds) | builds the exe on `windows-2022` from `main` (prebuilt FFmpeg, the XAudio2 redistributable, SDL3 from `vendor/SDL`), uploads the exe bundle to the work server, which merges the game assets and serves the download; runs the instruction-shape audit and the compiled-file inventory | `progress/asmaudit.json`, `progress/linked_files.json`, when `tools/build/build_audit_gate.py` sees new source since the last audited build, or on a manual run |
| `build-candidate.yml` | manual, `b5_commit` = an exact 40-hex b5-decomp commit, plus optional regression-fixture switches | builds and checks that b5 commit on hosted `windows-2022` through `ci/check-candidate-build.ps1`; no publish, no server, no game data | nothing (artifacts kept one day) |
| `audit-backfill.yml` | manual | re-runs the evidence audits over older b5 commits, sharded | nothing (artifacts only) |

There is deliberately no per-push build: `main` receives frequent automated ledger commits, and a
build per push would keep restarting.

The scheduled run starts with a small Linux `gate` job. `tools/build/website_build_gate.py` reads
the parent commit of the website's latest build from `/api/builds`, fetches that commit, and
compares its `b5-decomp` gitlink with the one in the scheduled checkout. A matching gitlink skips
the Windows job. A failed website or Git lookup fails the gate and skips the Windows job as well.
Use a manual run to publish parent-only changes or to pick up changes to external inputs such as
prebuilt FFmpeg, the XAudio2 package or the Drive assets the server merges in on each upload.

## What CI actually builds

- The build job checks out `main` and runs `git submodule update --init b5-decomp`: it compiles
  the **pointer committed on `main`** (the reconcile bot's last move) with **`main`'s `.bat`**.
  Your b5 commit reaches it only once the bot has moved the pointer; your mount line only once
  you have pushed it. Before asking for a build, check `git ls-tree origin/main b5-decomp`.
- Re-running a workflow never picks up an unpushed commit. A red build with a single LNK2019 is
  most often a mount still sitting unpushed in someone's parent checkout ("ahead N" in
  `git status -sb`), while the bot already moved the pointer to the code that needs it.
- `ci/publish-build.ps1` calls the same standalone scripts a developer uses
  (`tools/build/build_game_exe.bat` and its prerequisites); the `build` driver is a convenience,
  not a CI dependency.
- The per-TU object cache (`build/game/obj/tu`) is restored between runs and judged by content
  (`BRN_EXE_HASH_DEPS=1`), keyed on the hashes of `tools/build/msvc_flags.txt` and
  `tools/build/msvc_includes.txt`. A changed flag or include file, or a newer MSVC on the image,
  costs a full compile, as it should.

## The runner pin, and why

`runs-on: windows-2022`, never `windows-latest`. On 2026-08-24 `windows-latest` resolved to the
`windows-2025-vs2026` image (Visual Studio 18, MSVC 14.51), a compiler generation newer than the
Visual Studio 2022 17.14 / MSVC 14.44 this tree is developed and tested against. The flags are
committed and identical on both sides, so the toolset was the only difference. That exe booted
and then died with an access violation (a null read at `+0x10`) in
`BrnDirector::Camera::BehaviourGameplayExternal::Update`, on the same data where the local build
reaches gameplay, and it is the same function players' crash reports named. CI reported success
on every run.

- The tree deliberately preserves the console's undefined behaviour, so a newer optimiser is free
  to make different, legal choices about it. Pin the toolchain; do not chase the codegen.
- The "Record toolchain" step prints `cl`'s version, `VCToolsVersion` and `VSINSTALLDIR` in every
  run. Read it whenever a CI exe behaves differently from a local one.
- A green CI run says the compiler was happy, not that the exe works.

## Crash reports from players

A player's fault address resolves only against the exe CI built. The runner's MSVC lays code out
differently from any local toolchain: the same RVA named a different function in a local map
(2026-08). Use the map and `Burnout_PC.cgsmap` from that build: the `exe-bundle-<sha>` artifact
of Build & Publish (kept 30 days) or the player's own download. Never a local rebuild of the same
commit.

## Running a workflow

- Start Build & Publish (`gh workflow run build-and-publish.yml`, or the Actions page) only when
  the maintainer asks: it publishes a public download.
- A candidate check builds an exact b5 commit on the CI toolchain without publishing:
  `gh workflow run build-candidate.yml -f b5_commit=<40-hex sha>`.
- The download is the exe bundle plus an asset set the work server maintains. A porter change
  that alters a converted file needs that set refreshed before the next publish, or the nightly
  build ships code that expects data it does not have ([`port-assets`](../../port-assets/SKILL.md)).
