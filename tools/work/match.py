"""`work match ...`: forwards to tools/bytematch/bytematch.py (the byte-match ledger)."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bytematch"))
import bytematch  # noqa: E402


def main(argv):
    return bytematch.main(argv)
