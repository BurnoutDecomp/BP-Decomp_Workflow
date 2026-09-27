# Paradise Asset Converter

An offline browser interface for the existing Xbox 360 → PC decomp asset converters.
Double-click **`convert-assets.cmd`** in the repository root. It finds Python 3.11+
and opens the interface in your default browser. Keep the launcher window open;
Ctrl+C or **Quit converter** stops the local server and cancels any active converters.
Launching the script again reopens the running instance.

No Node.js, web framework, pip install, account, or network service is needed.
The browser interface needs Python; individual conversions still need the same
tools and input data as the command-line pipeline.

### Hosting on Ubuntu

For a public upload/download website, use **`bash deploy-converter.sh your.hostname`**
from the repository root. It builds native Linux converters and starts the hosted
app behind an HTTPS proxy. Each visitor gets a separate workspace and ZIP downloads.
See [deployment instructions and limits](deploy/README.md). This is a separate entry
point; the desktop launcher stays local and dependency-free.

## Use

1. Choose files or a folder, paste local paths, or drop a selection into the page.
   The native choosers read files directly. Browser uploads/drops stage a temporary
   copy locally under `build/converter-ui/uploads`; nothing is sent to the internet.
2. Choose a separate destination folder. The default is `build/converted-assets`.
3. Review the detected formats, selected converters, and any setup issues.
   Click a filename for resource types, paths, and converter details.
4. Convert selected files. The queue and activity panel show progress and errors.
   Open the output folder or download the report when the run finishes.

The attached-example family, `PARADISE_INGAME_JUNK.BUNDLE`, is identified from its
resource types. Environment keyframe/timeline bundles and colour-cube bundles with
the same basename are routed separately. Known game paths and constrained filenames
are also resolved through `tools/assets/game_data_manifest.toml`.

## Features

- Recursive folders, multiple sources, duplicate-source detection, and preserved
  game-relative paths. Unsupported files are listed rather than silently converted.
- Selectable queue, search, filters, pagination, format guide, and plan export.
- Light/dark themes, saved settings and source paths, local run history, JSON reports,
  and streamed converter logs. `/` focuses search; Ctrl+Enter starts a reviewed plan.
- Up to eight isolated converter workers. The project stager's `WorkerRoots` keeps
  Volatility's resource stores separate and redirects legacy `build/game` outputs.
- A setup panel that runs the existing `build tools` command if YAP/Volatility are
  missing. See the repository's `BUILD.md` for Visual Studio, CMake, Qt6 and .NET.
- Unchanged outputs are skipped using the stager's source/converter/output signature.
  Existing outputs are kept by default. Replacements keep a backup under
  `<output>/.asset-converter/backups/<run-id>/` before publishing the new file.
- Converters write to private staging. Manifest output checks must pass before
  files are published with an atomic file replacement. Failures preserve old outputs.
- Cancel terminates the run's process tree, retains completed outputs, and removes
  unfinished staging. Refreshing the page reconnects to the active run.
- Full game folder selections also offer generated schema/loading-screen assets
  from `BURNOUT_X360_ARTIST.XEX`. The optional original-game folder supplies
  companion data; AEMS/CSIS conversions can use an Xbox One data folder.

## Scope and behavior

This wraps the existing converters; it does not invent support for unknown formats.
The format guide reflects the manifest, including unhandled Apt and other families.
Some converters need companion data, native Xbox One banks, or the shader toolchain;
missing prerequisites are reported before starting where the manifest/stager knows
them, and converter failures appear with their actual diagnostic output.

A platform-4 header selects a verbatim copy; it is not proof that an externally
converted payload is correct. The app never feeds platform-4 files through an X360
payload converter. Automatic type detection is limited to unambiguous supported
resource sets. Advanced manual selection is for files whose family you already know.

The destination must be separate from the selected source and outside the source
tree, tooling tree, and live `build/game` directory. It never installs directly into
a running game. Symbolic links/junctions inside selected folder trees are skipped
and listed in the plan. Source data is opened for reading only.

The server binds only to `127.0.0.1` on an available port. Its random session token
is kept in the browser session and required for every API request. Host and origin
checks prevent unrelated websites from driving the local converter. No shell command
text is accepted from the browser; only manifest converter IDs can select commands.
Reports/logs/settings live under `build/converter-ui`, which is already gitignored.
Output reports and resume state live under `<output>/.asset-converter`.

## Development

```powershell
python tools/assets/converter_ui/server.py --no-browser
python tools/assets/converter_ui/server.py --port 8765
python -m unittest discover -s tools/assets/converter_ui -p 'test_*.py'
```

`engine.py` handles classification, manifest expansion, isolated workers and output
publication. `server.py` serves the static HTML/CSS/JS and orchestrates one run at a
time. All binary payload transformations remain in the existing converter scripts.
Tests use synthetic bundle directories and exercise ambiguity, unsupported formats,
collision/source guards, failed-output preservation, backups, resume signatures,
upload traversal, and API authorization. Real asset validation uses local game data;
no proprietary game fixture is committed here.
