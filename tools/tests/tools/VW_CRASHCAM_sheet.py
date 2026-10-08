"""Contact sheet of dumped frames (lane CRASHCAM).

usage: VW_CRASHCAM_sheet.py <frames dir> <out.png> [--start N] [--step K] [--count C] [--cols 4] [--width 320]

Picks every K-th bb_*.bmp from index N, labels each tile with its file name, writes one PNG.
"""
from pathlib import Path
import argparse
from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frames")
    ap.add_argument("out")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--step", type=int, default=10)
    ap.add_argument("--count", type=int, default=16)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--width", type=int, default=320)
    ap.add_argument("--glob", default="bb_*.bmp")
    args = ap.parse_args()
    files = sorted(Path(args.frames).glob(args.glob))
    pick = files[args.start::args.step][:args.count]
    if not pick:
        raise SystemExit("no frames")
    first = Image.open(pick[0])
    w = args.width
    h = int(first.height * w / first.width)
    rows = (len(pick) + args.cols - 1) // args.cols
    sheet = Image.new("RGB", (w * args.cols, (h + 14) * rows), (40, 40, 40))
    draw = ImageDraw.Draw(sheet)
    for i, path in enumerate(pick):
        tile = Image.open(path).convert("RGB").resize((w, h))
        x, y = (i % args.cols) * w, (i // args.cols) * (h + 14)
        sheet.paste(tile, (x, y + 14))
        draw.text((x + 2, y + 1), path.stem, fill=(255, 255, 0))
    sheet.save(args.out)
    print(f"{len(pick)} tiles of {len(files)} frames -> {args.out}")


if __name__ == "__main__":
    main()
