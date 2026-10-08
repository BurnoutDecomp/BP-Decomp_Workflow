"""Contact sheet of dumped frames: VW_PAUSE_sheet.py <framesdir> <out.png> <first> <last> [step] [width]

Frames are bb_<present>.bmp; every dumped frame with first <= present <= last (and
present % step == 0 when step is given) is scaled to <width> px and labelled.
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw


def main():
    frames = Path(sys.argv[1])
    out = Path(sys.argv[2])
    first, last = int(sys.argv[3]), int(sys.argv[4])
    step = int(sys.argv[5]) if len(sys.argv) > 5 else 1
    width = int(sys.argv[6]) if len(sys.argv) > 6 else 320
    picks = []
    for path in sorted(frames.glob("bb_*.bmp")):
        present = int(path.stem[3:])
        if first <= present <= last and present % step == 0:
            picks.append((present, path))
    if not picks:
        raise SystemExit("no frames in range")
    tiles = []
    for present, path in picks:
        image = Image.open(path).convert("RGB")
        height = image.height * width // image.width
        tile = image.resize((width, height), Image.BILINEAR)
        ImageDraw.Draw(tile).text((4, 4), str(present), fill=(255, 0, 255))
        tiles.append(tile)
    columns = 4
    rows = (len(tiles) + columns - 1) // columns
    height = tiles[0].height
    sheet = Image.new("RGB", (columns * width, rows * height))
    for index, tile in enumerate(tiles):
        sheet.paste(tile, ((index % columns) * width, (index // columns) * height))
    sheet.save(out)
    print(f"{len(tiles)} frames -> {out}")


if __name__ == "__main__":
    main()
