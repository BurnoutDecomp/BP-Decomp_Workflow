# Debug menu finder

Double-click **`debug-menu.cmd`** in the repository root. It refreshes the index
from the current checkout and opens a standalone search page in your browser.
Python 3.11+ is the only dependency; no server or running game is needed.

Search an entry name or any words in its menu path. Each match shows the full
breadcrumb from **Development**, with a copy button. Menu/type filters narrow the
results. In-game, **Ctrl+Space** opens the menu; selecting a component reveals its
controls.

The default view uses PC source registrations, including native graphics controls.
Enable **Include original ARTIST entries** to search the existing original-menu
inventory too. Reference-only matches may be absent from the PC build. Computed
paths remain marked incomplete; generated captions and runtime rows are not fully
enumerated. Visibility also depends on build conditions and game state.

Terminal searches:

```powershell
.\debug-menu.cmd --query "tailgate cone"
.\debug-menu.cmd --query "Apply Ram" --include-reference
.\debug-menu.cmd --query "resolution" --json
.\debug-menu.cmd --no-open
```

The generated page is `build/debug-menu/index.html`. Re-run the launcher after
source changes; the saved HTML also works offline. Use `--output <file.html>` for
another destination. Regenerating the optional ARTIST inventory is a separate
operation: `python tools/re/debug_menu_inventory.py`.

Indexer regression checks:

```powershell
python -m unittest discover -s tools/debug_menu -p "test_*.py"
```
