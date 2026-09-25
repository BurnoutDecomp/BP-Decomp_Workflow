#!/usr/bin/env python3
"""Convert an extracted Xenia Burnout Paradise save to the decomp's B5SV container.

Python 3.10+, standard library only. See README.md beside this file for supported
layouts and evidence. Never modifies the source or overwrites an existing output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import zlib


IMAGE_SIZE = 262144
REVENGE = 118064
OPTIONS = 148080
DLC = 177632
DLC_OPTIONS = 187432
MUGSHOT_SIZE = 9608
MUGSHOT_COUNT = 100
CONTAINER_HEADER = struct.Struct("<6I32s256s")
CONTAINER_MAGIC = 0x42355356
MUGSHOT_MAGIC = 0x4D554753
TITLE_ID = "45410806"


class SaveError(ValueError):
    """Invalid, damaged or unsupported save; no output should be installed."""


def _crc_table() -> tuple[int, ...]:
    table = []
    for value in range(256):
        value <<= 24
        for _ in range(8):
            value = ((value << 1) ^ (0x04C11DB7 if value & 0x80000000 else 0)) & 0xFFFFFFFF
        table.append(value)
    return tuple(table)


CRC_TABLE = _crc_table()


def mc02_crc(data: bytes) -> int:
    """ARTIST Crc32 @82C44850; table @82FA7C88. This is NOT zlib.crc32.

    Seed with the complement of the first big-endian word, shift subsequent
    bytes into the low byte, table-xor using the OLD high byte, then complement.
    The console returns zero for inputs shorter than four bytes.
    """
    if len(data) < 4:
        return 0
    value = int.from_bytes(data[:4], "big") ^ 0xFFFFFFFF
    for byte in data[4:]:
        value = (((value << 8) | byte) ^ CRC_TABLE[value >> 24]) & 0xFFFFFFFF
    return value ^ 0xFFFFFFFF


def read_mc02(data: bytes, expected_size: int, label: str) -> bytes:
    if len(data) != expected_size + 28:
        raise SaveError(f"{label}: expected {expected_size + 28} bytes, got {len(data)}")
    magic, total, extra, size, empty_crc, crc, header_crc = struct.unpack_from(">7I", data)
    if (magic, total, extra, size, empty_crc) != (0x4D433032, len(data), 0, expected_size, 0):
        raise SaveError(f"{label}: unsupported MC02 header (requires an extracted Xenia save)")
    if mc02_crc(data[:24]) != header_crc:
        raise SaveError(f"{label}: MC02 header checksum mismatch")
    payload = data[28:]
    if mc02_crc(payload) != crc:
        raise SaveError(f"{label}: MC02 payload checksum mismatch")
    return payload


def _fields() -> tuple[tuple[int, int, int], ...]:
    """(offset, width, count) runs of numeric fields in ProfileStoredData.

    Base/DLC offsets: BrnProfile_SaveImage.cpp, SaveImage/SaveImageDLC1.
    Record widths: the owning Car/Livery/Rival/Challenge/Mugshot headers.
    Strings, bools, opaque inactive data and padding deliberately have no run.
    """
    fields: list[tuple[int, int, int]] = []

    def add(offset: int, width: int = 4, count: int = 1) -> None:
        fields.append((offset, width, count))

    def date(offset: int) -> None:
        # Xbox FILETIME is high-word first: GetRawTimeValue @828D6F68
        # shifts the +4 word LEFT 32, then adds +8. Windows expects low first.
        # Treat the pair as ONE u64; swapping two u32s would corrupt every date.
        add(offset + 4, 8)

    def records(base: int, count: int, kind: str) -> None:
        stride = {"car": 24, "livery": 24, "rival": 56, "event": 8}[kind]
        for i in range(count):
            offset = base + i * stride
            if kind == "car":
                add(offset, 8)
                add(offset + 12, 4, 2)  # float deformation, enum unlock type
            elif kind == "livery":
                add(offset, 8, 2)
                add(offset + 16)
            elif kind == "rival":
                add(offset, 8, 2)
                add(offset + 16, 4, 9)
            else:
                add(offset)
                add(offset + 4, 2)  # u16 flags, followed by padding

    def id_array(base: int, capacity: int) -> None:
        add(base, 8, capacity)
        add(base + 8 * capacity)  # Array/Set count; final four bytes are pad

    add(0)
    add(48, 4, 8)  # position and direction are four FLOATS each, not two u64s
    add(80, 8, 2)
    add(96, 4, 4)
    add(116, 4, 126)  # counters, scores, four 17-element mode arrays, table counts
    records(624, 512, "car")
    records(12912, 512, "livery")
    records(25200, 64, "rival")
    records(28784, 175, "event")
    for i in range(3):
        id_array(30184 + i * 4104, 512)
    add(42496)
    for offset, capacity in ((42504, 5), (42552, 11), (42648, 5), (42696, 14), (42816, 11), (42912, 2000)):
        id_array(offset, capacity)
    add(58920, 8, 4688)  # BitArray<300000>, rounded to whole u64 fields
    add(96424, 2, 15)
    for i in range(64):
        for base, stride in ((96456, 56), (100040, 40)):
            offset = base + i * stride
            add(offset, 8, 2)  # dirty and valid score bit arrays
            add(offset + 16, 4, 2)
        add(100040 + i * 40 + 24, 8, 2)  # local car IDs; remote names stay bytes
    add(102600)
    add(102604, 4, 6)  # stored 32-bit texture descriptor; final bytes are flags
    for gallery in range(5):
        base = 112240 + gallery * 1128
        for i in range(20):
            offset = base + i * 56
            add(offset + 16, 8)  # name[16] then XUID
            date(offset + 24)
            add(offset + 36, 4, 3)  # county, district, number of captures
            add(offset + 48, 2)  # file ID; lock bool stays byte-sized
        add(base + 1120)
    add(117880, 8, 5)
    add(117920, 4, 4)
    add(117936, 8, 4)
    add(117968, 4, 3)
    date(117980)
    date(117992)
    add(118004)
    add(118008, 8)
    add(118028)
    add(118032, 8)
    add(118040, 4, 3)

    # LiveRevengeProfile / LiveRevengeRelationship: stats, date, identity, score.
    add(REVENGE)
    for i in range(250):
        offset = REVENGE + 8 + 120 * i
        add(offset, 4, 18)
        date(offset + 72)
        add(offset + 104, 8)
        add(offset + 112, 4, 2)
    add(REVENGE + 30008)

    # OptionsDataProfile: twenty routes, each with ten 144-byte event records.
    add(OPTIONS)
    for i in range(20):
        route = OPTIONS + 8 + i * 1472
        for event in range(10):
            offset = route + event * 144
            add(offset, 8, 16)  # landmark CgsIDs
            add(offset + 128, 4, 3)  # junction ID, landmark count, event ID
        add(route + 1440, 4, 7)  # enums/counts then three bools and pad
    add(OPTIONS + 0x7308, 4, 2)
    add(OPTIONS + 0x7310, 8, 6)  # three FastBitArray<128> track sets
    add(OPTIONS + 0x7340, 4, 10)  # audio/video options; trailing bools stay bytes

    add(DLC)
    # ProcessGameEvents @823A0A18 case 152 receives NetworkOutTargetScoreEvent:
    # the first 24 bytes are UniquePlayerIDX360 (name[16], XUID), copied by
    # SetTargetEventScore @823714F8. The record header still calls this opaque.
    for i in range(49):
        add(DLC + 8 + 40 * i + 16, 8)
        add(DLC + 8 + 40 * i + 24, 8)
        add(DLC + 8 + 40 * i + 32)
    add(DLC + 1968)
    for i in range(49):
        offset = DLC + 1976 + 16 * i
        add(offset, 8)
        add(offset + 8, 4, 2)
    add(DLC + 2760)
    add(DLC + 2768, 8)
    add(DLC + 2776, 4, 4)
    records(DLC + 2792, 100, "car")
    records(DLC + 5192, 100, "livery")
    # The actual reserved spans fit 32 rivals / 48 events (not the 100 maximum
    # passed to SplitArray in the console). Bounds are checked before conversion.
    records(DLC + 7592, 32, "rival")
    records(DLC + 9384, 48, "event")
    add(DLC + 9768, 8, 2)
    add(DLC + 9784, 4, 4)
    add(DLC_OPTIONS, 4, 2)

    occupied: set[int] = set()
    for offset, width, count in fields:
        for byte in range(offset, offset + width * count):
            if byte in occupied or not 0 <= byte < IMAGE_SIZE:
                raise RuntimeError(f"overlapping/out-of-bounds schema at {byte:#x}")
            occupied.add(byte)
    return tuple(fields)


NUMERIC_FIELDS = _fields()


def swap_profile_fields(image: bytes) -> bytes:
    if len(image) != IMAGE_SIZE:
        raise SaveError(f"profile image must be {IMAGE_SIZE} bytes")
    result = bytearray(image)
    for offset, width, count in NUMERIC_FIELDS:
        for position in range(offset, offset + width * count, width):
            result[position:position + width] = image[position:position + width][::-1]
    return bytes(result)


def validate_profile(image: bytes, endian: str = ">") -> dict:
    if len(image) != IMAGE_SIZE:
        raise SaveError(f"profile image must be {IMAGE_SIZE} bytes")

    def integer(offset: int) -> int:
        return struct.unpack_from(endian + "I", image, offset)[0]

    def count(offset: int, capacity: int, name: str) -> int:
        value = integer(offset)
        if value > capacity:
            raise SaveError(f"{name}: count {value} exceeds capacity {capacity}")
        return value

    versions = [(0, 28, "progression"), (REVENGE, 6, "live revenge"),
                (OPTIONS, 12, "options"), (DLC, 6, "DLC progression"),
                (DLC_OPTIONS, 1, "DLC options")]
    for offset, expected, name in versions:
        actual = integer(offset)
        if actual != expected:
            raise SaveError(f"unsupported {name} version {actual}; expected {expected}")
    cars = count(604, 512, "cars")
    liveries = count(608, 512, "liveries")
    rivals = count(612, 64, "rivals")
    events = count(616, 175, "events")
    for i in range(3):
        count(30184 + i * 4104 + 4096, 512, "stunt elements")
    for offset, maximum in ((42544, 5), (42640, 11), (42688, 5), (42808, 14), (42904, 11)):
        count(offset, maximum, "drive-through locations")
    challenges = count(58912, 2000, "freeburn challenges")
    for i in range(5):
        count(112240 + i * 1128 + 1120, 20, "mugshot gallery")
    count(REVENGE + 30008, 249, "live revenge relationships")  # runtime asserts <250
    for offset in (0x7308, 0x730C):
        routes = count(OPTIONS + offset, 10, "online routes")
        base = OPTIONS + (8 if offset == 0x7308 else 0x3988)
        for i in range(routes):
            for event in range(10):
                # Inactive event slots can hold the game's unconstructed sentinel.
                position = base + i * 1472 + event * 144
                if integer(position + 136) != 0xFFFFFFFF:
                    count(position + 132, 16, "route landmarks")
    count(DLC + 1968, 49, "target event scores")
    count(DLC + 2760, 49, "pending event uploads")
    for offset, maximum, name in ((2776, 100, "cars"), (2780, 100, "liveries"),
                                  (2784, 32, "rivals"), (2788, 48, "events")):
        dlc_count = count(DLC + offset, maximum, "DLC " + name)
        total, capacity = {"cars": (cars, 512), "liveries": (liveries, 512),
                           "rivals": (rivals, 64), "events": (events, 175)}[name]
        if total + dlc_count > capacity:
            raise SaveError(f"combined base/DLC {name} exceed the runtime capacity {capacity}")
    if image[112232] not in (0, 1):
        raise SaveError("invalid licence picture flag")
    rank = struct.unpack_from("b", image, 112)[0]
    if not -2 <= rank <= 6:
        raise SaveError(f"invalid progression rank {rank}")
    online, offline, seconds = struct.unpack_from(endian + "3f", image, 100)
    if not all(math.isfinite(value) and value >= 0 for value in (online, offline, seconds)):
        raise SaveError("invalid distance/time values")
    return {"cars": cars, "liveries": liveries, "rivals": rivals, "events": events,
            "freeburn_challenges": challenges, "rank": rank,
            "mugshot_gallery_counts": [integer(112240 + i * 1128 + 1120) for i in range(5)],
            "distance_online_m": online, "distance_offline_m": offline,
            "driving_time_seconds": seconds,
            "spawn_car_id": f"{struct.unpack_from(endian + 'Q', image, 80)[0]:016X}"}


def swap_dxt1_pixels(pixels: bytes) -> bytes:
    """Linear 160x120 DXT1, Xenos 8IN16 -> PC BC1 (no tiling).

    NetworkTexture uses PIXELFORMAT_LIN_DXT1 (0x1A200052); bits 6..7
    select GPUENDIAN_8IN16. UnpackFromNetworkTexture @8288F498 copies rows
    directly, unlike the tiled world texture resources. BC1 payload is 9600 B.
    """
    result = bytearray(pixels)
    result[0::2], result[1::2] = pixels[1::2], pixels[0::2]
    return bytes(result)


def convert_mugshots(blob: bytes) -> tuple[bytes, list[int]]:
    if len(blob) != MUGSHOT_COUNT * MUGSHOT_SIZE:
        raise SaveError("incorrect mugshot payload size")
    result = bytearray(blob)
    corrupt_slots = []
    for offset in range(0, len(blob), MUGSHOT_SIZE):
        magic, checksum = struct.unpack_from(">II", blob, offset)
        if magic == MUGSHOT_MAGIC:
            pixels = blob[offset + 8:offset + MUGSHOT_SIZE]
            if checksum != (zlib.crc32(pixels) ^ 0xFFFFFFFF):
                # Some Xenia saves contain MUGS + zero checksum + zero pixels.
                # Keep those slots unreadable under the decomp's IsCorrupt check;
                # do not manufacture a valid photo by repairing its checksum.
                corrupt_slots.append(offset // MUGSHOT_SIZE)
            else:
                pixels = swap_dxt1_pixels(pixels)
                result[offset + 8:offset + MUGSHOT_SIZE] = pixels
                checksum = zlib.crc32(pixels) ^ 0xFFFFFFFF
        struct.pack_into("<II", result, offset, magic, checksum)
    return bytes(result), corrupt_slots


def fnv1a(data: bytes) -> int:
    value = 2166136261
    for byte in data:
        value = ((value ^ byte) * 16777619) & 0xFFFFFFFF
    return value


def make_container(image: bytes, mugshots: bytes) -> bytes:
    payload = image + mugshots
    return CONTAINER_HEADER.pack(CONTAINER_MAGIC, 1, len(image), len(mugshots),
                                 fnv1a(payload), 0, b"Burnout Paradise",
                                 b"Converted from Xenia (Xbox 360)") + payload


def read_container(data: bytes) -> tuple[bytes, bytes]:
    if len(data) < CONTAINER_HEADER.size:
        raise SaveError("truncated decomp container")
    magic, version, image_size, mugshot_size, checksum, reserved, _, _ = CONTAINER_HEADER.unpack_from(data)
    if (magic, version, image_size, reserved) != (CONTAINER_MAGIC, 1, IMAGE_SIZE, 0):
        raise SaveError("unsupported decomp container header")
    if mugshot_size not in (0, MUGSHOT_COUNT * MUGSHOT_SIZE):
        raise SaveError("incorrect decomp mugshot size")
    payload = data[CONTAINER_HEADER.size:]
    if len(payload) != image_size + mugshot_size or fnv1a(payload) != checksum:
        raise SaveError("decomp container size/checksum mismatch")
    return payload[:image_size], payload[image_size:]


def resolve_source(path: Path) -> Path:
    """Accept a Profile file, its directory, or a Xenia installation directory."""
    path = path.expanduser().resolve()
    if path.is_file():
        return path
    # Prefer the exact active Profile path. Never choose an 'unlocked' or backup
    # save based on modification time, nor pick another user's profile silently.
    candidates = [path / "Profile", path / "content" / TITLE_ID / "00000001" / "Profile" / "Profile"]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    alternatives = sorted((path / "content").glob(f"*/{TITLE_ID}/00000001/Profile/Profile"))
    if len(alternatives) == 1:
        return alternatives[0]
    if alternatives:
        raise SaveError("multiple Xenia user saves found; pass the exact Profile file:\n" +
                        "\n".join(str(p) for p in alternatives))
    raise SaveError(f"no active Burnout Paradise Profile found under {path}; pass its exact file path")


def convert(source: Path, output: Path | None = None) -> dict:
    profile_path = resolve_source(source)
    mugshot_path = profile_path.with_name("Mugshots")
    source_data = profile_path.read_bytes()
    image = read_mc02(source_data, IMAGE_SIZE, "Profile")
    summary = validate_profile(image)
    mugshot_data = mugshot_path.read_bytes() if mugshot_path.is_file() else None
    if mugshot_data is None and any(summary["mugshot_gallery_counts"]):
        raise SaveError("Mugshots file is missing but the profile contains gallery records")
    mugshots, corrupt_slots = (convert_mugshots(read_mc02(mugshot_data, MUGSHOT_COUNT * MUGSHOT_SIZE, "Mugshots"))
                              if mugshot_data is not None else (b"", []))
    converted = swap_profile_fields(image)
    if validate_profile(converted, "<") != summary:
        raise SaveError("conversion changed profile summary values")
    if swap_profile_fields(converted) != image:
        raise SaveError("profile endian round-trip failed")
    if image[112232]:
        pixels = swap_dxt1_pixels(image[102632:112232])
        converted = converted[:102632] + pixels + converted[112232:]
    container = make_container(converted, mugshots)
    if read_container(container) != (converted, mugshots):
        raise SaveError("container round-trip failed")
    report = {"source": str(profile_path), "source_sha256": hashlib.sha256(source_data).hexdigest(),
              "mugshots_source": str(mugshot_path) if mugshot_data is not None else None,
              "mugshots_source_sha256": hashlib.sha256(mugshot_data).hexdigest() if mugshot_data is not None else None,
              "unreadable_mugshot_slots_preserved": corrupt_slots,
              "output_size": len(container), "output_sha256": hashlib.sha256(container).hexdigest(),
              "profile": summary}
    if output is not None:
        output = output.expanduser().resolve()
        if output in (profile_path, mugshot_path):
            raise SaveError("output must be separate from the Xenia source files")
        # Exclusive creation deliberately has no --force mode. A failed write
        # removes only the newly-created output, never an existing file.
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            with output.open("xb") as stream:
                try:
                    stream.write(container)
                    stream.flush()
                except BaseException:
                    stream.close()
                    output.unlink()
                    raise
        except FileExistsError as error:
            raise SaveError(f"output already exists: {output}; choose a new path") from error
        report["output"] = str(output)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Xenia installation, save directory, or extracted Profile file")
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--output", "-o", type=Path, help="new .sav file (existing files are never overwritten)")
    destination.add_argument("--check", action="store_true", help="validate and convert in memory without writing")
    parser.add_argument("--json", action="store_true", help="print a machine-readable conversion report")
    args = parser.parse_args(argv)
    try:
        report = convert(args.source, args.output)
    except (OSError, SaveError) as error:
        parser.exit(1, f"Error: {error}\n")
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        summary = report["profile"]
        print(f"Source: {report['source']}")
        print(f"Validated: {summary['cars']} cars, {summary['events']} events, "
              f"rank {summary['rank']}, {summary['driving_time_seconds'] / 3600:.2f} driving hours")
        if report["unreadable_mugshot_slots_preserved"]:
            print("Note: existing unreadable mugshot slots preserved: " +
                  ", ".join(map(str, report["unreadable_mugshot_slots_preserved"])))
        if args.output:
            print(f"Written: {report['output']} ({report['output_size']:,} bytes)")
            print("To use: close the decomp, back up its Memcard\\Profile.sav, then place this file there.")
        else:
            print("Checks passed; no files written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
