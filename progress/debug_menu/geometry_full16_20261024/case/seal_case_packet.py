"""Write a hash inventory for this source-only proposal packet; no game/build/test actions."""
from __future__ import annotations
import hashlib
from pathlib import Path

PACKET = Path(__file__).resolve().parent
OUT = PACKET / "SHA256SUMS.txt"
rows = []
for path in sorted(PACKET.rglob("*")):
    if not path.is_file() or path == OUT:
        continue
    if any(part in {"stage", "run", "frames"} or part.startswith("run_full16_") for part in path.relative_to(PACKET).parts):
        continue
    data = path.read_bytes()
    rows.append(f"{hashlib.sha256(data).hexdigest()}  {path.relative_to(PACKET).as_posix()}")
OUT.write_text("\n".join(rows) + "\n", encoding="utf-8")
print(f"sealed {len(rows)} packet files")
