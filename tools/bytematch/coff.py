"""Read the PowerPC big-endian COFF objects and archives the Xbox 360 XDK produces.

The XDK compiler (`cl` 14.00.6502 for PowerPC) writes ordinary Microsoft COFF: the
headers, symbol table and relocation records are little-endian, the section data is
big-endian PowerPC code. `/Gy` puts every function in its own COMDAT `.text`
section, which is what lets a single object be compared function by function.

Pure Python, no dependencies, so the tests and CI can import it on Linux.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import struct

MACHINE_PPCBE = 0x01F2

# IMAGE_REL_PPC_* (winnt.h). PAIR carries the REFHI displacement, not a symbol.
REL_ABSOLUTE, REL_ADDR64, REL_ADDR32, REL_ADDR24, REL_ADDR16, REL_ADDR14 = 0x00, 0x01, 0x02, 0x03, 0x04, 0x05
REL_REL24, REL_REL14, REL_TOCREL16, REL_TOCREL14, REL_ADDR32NB = 0x06, 0x07, 0x08, 0x09, 0x0A
REL_SECREL, REL_SECTION, REL_IFGLUE, REL_IMGLUE, REL_SECREL16 = 0x0B, 0x0C, 0x0D, 0x0E, 0x0F
REL_REFHI, REL_REFLO, REL_PAIR, REL_SECRELLO, REL_SECRELHI, REL_GPREL, REL_TOKEN = 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16

# The bits of the 32-bit instruction word a relocation of each type rewrites.
RELOC_FIELD = {
    REL_ADDR32: 0xFFFFFFFF, REL_ADDR32NB: 0xFFFFFFFF, REL_SECREL: 0xFFFFFFFF, REL_TOKEN: 0xFFFFFFFF,
    REL_ADDR24: 0x03FFFFFC, REL_REL24: 0x03FFFFFC,
    REL_ADDR14: 0x0000FFFC, REL_REL14: 0x0000FFFC, REL_TOCREL14: 0x0000FFFC,
    REL_ADDR16: 0x0000FFFF, REL_TOCREL16: 0x0000FFFF, REL_SECREL16: 0x0000FFFF, REL_SECTION: 0x0000FFFF,
    REL_REFHI: 0x0000FFFF, REL_REFLO: 0x0000FFFF, REL_SECRELLO: 0x0000FFFF, REL_SECRELHI: 0x0000FFFF,
    REL_GPREL: 0x0000FFFF,
}
NOT_A_FIELD = {REL_ABSOLUTE, REL_PAIR}

SCN_CNT_CODE = 0x00000020
SCN_LNK_COMDAT = 0x00001000
SCN_LNK_NRELOC_OVFL = 0x01000000
DTYPE_FUNCTION = 0x20
CLASS_EXTERNAL, CLASS_STATIC = 2, 3


class CoffError(ValueError):
    pass


@dataclass
class Reloc:
    offset: int          # from the start of its section
    symbol: int          # symbol-table index (PAIR: the REFHI displacement)
    type: int


@dataclass
class Section:
    index: int           # 1-based, as symbols number them
    name: str
    data: bytes
    flags: int
    relocs: list = field(default_factory=list)

    @property
    def is_code(self):
        return bool(self.flags & SCN_CNT_CODE)


@dataclass
class Symbol:
    index: int
    name: str
    value: int
    section: int         # 1-based section number; 0 undefined, negative special
    type: int
    storage: int


@dataclass
class Function:
    """One function body: its decorated name, code bytes and the relocations inside it."""
    symbol: str
    code: bytes
    relocs: list         # Reloc with offset relative to the function start, PAIR kept
    section: int
    offset: int
    static: bool

    def target(self, obj, reloc):
        return obj.symbols[reloc.symbol].name if reloc.symbol in obj.symbols else "?"


class ObjectFile:
    def __init__(self, data: bytes, name: str = "<object>"):
        self.name = name
        if len(data) < 20:
            raise CoffError(f"{name}: too short for a COFF header")
        if data[:4] == b"\0\0\xff\xff":
            raise CoffError(f"{name}: /bigobj objects are not supported")
        (self.machine, nsec, _stamp, symptr, nsym, optsize, _chars) = struct.unpack_from("<HHIIIHH", data, 0)
        if self.machine != MACHINE_PPCBE:
            raise CoffError(f"{name}: machine {self.machine:#06x}, expected PowerPC big-endian {MACHINE_PPCBE:#06x}")
        self.data = data
        strtab = symptr + nsym * 18

        def string_at(offset):
            end = data.index(b"\0", strtab + offset)
            return data[strtab + offset:end].decode("latin-1")

        def short_name(raw):
            if raw[:4] == b"\0\0\0\0":
                return string_at(struct.unpack_from("<I", raw, 4)[0])
            return raw.rstrip(b"\0").decode("latin-1")

        self.sections = {}
        for i in range(nsec):
            o = 20 + optsize + i * 40
            raw = data[o:o + 8]
            name_ = raw.rstrip(b"\0").decode("latin-1")
            if name_.startswith("/") and name_[1:].isdigit():
                name_ = string_at(int(name_[1:]))
            (_vsize, _va, rsize, rptr, relptr, _lnptr, nrel, _nln, flags) = struct.unpack_from("<IIIIIIHHI", data, o + 8)
            body = data[rptr:rptr + rsize] if rptr else b"\0" * rsize
            relocs = []
            first = 0
            if flags & SCN_LNK_NRELOC_OVFL and nrel == 0xFFFF:
                nrel = struct.unpack_from("<I", data, relptr)[0]
                first = 1
            for k in range(first, nrel):
                va, sym, typ = struct.unpack_from("<IIH", data, relptr + k * 10)
                relocs.append(Reloc(va, sym, typ))
            self.sections[i + 1] = Section(i + 1, name_, body, flags, relocs)

        self.symbols = {}
        i = 0
        while i < nsym:
            o = symptr + i * 18
            raw = data[o:o + 8]
            value, secnum, typ, storage, naux = struct.unpack_from("<IhHBB", data, o + 8)
            self.symbols[i] = Symbol(i, short_name(raw), value, secnum, typ, storage)
            i += 1 + naux

    def functions(self):
        """Every defined function, sized by its COMDAT section or the next function."""
        by_section = {}
        for sym in self.symbols.values():
            if sym.type & 0xF0 != DTYPE_FUNCTION or sym.section <= 0:
                continue
            if sym.storage not in (CLASS_EXTERNAL, CLASS_STATIC):
                continue
            section = self.sections.get(sym.section)
            if section is None or not section.is_code:
                continue
            by_section.setdefault(sym.section, []).append(sym)
        out = []
        for secnum, syms in by_section.items():
            section = self.sections[secnum]
            syms.sort(key=lambda s: s.value)
            for n, sym in enumerate(syms):
                end = syms[n + 1].value if n + 1 < len(syms) else len(section.data)
                start = sym.value
                relocs = [Reloc(r.offset - start, r.symbol, r.type) for r in section.relocs if start <= r.offset < end]
                out.append(Function(sym.name, section.data[start:end], relocs, secnum, start, sym.storage == CLASS_STATIC))
        return out


def read_object(path):
    with open(path, "rb") as fh:
        return ObjectFile(fh.read(), str(path))


def archive_members(data: bytes, name: str = "<archive>"):
    """Yield (member name, bytes) for each COFF object in a `.lib` archive.

    Skips the linker members and short import objects (Sig1 0, Sig2 0xFFFF).
    """
    if data[:8] != b"!<arch>\n":
        raise CoffError(f"{name}: not an archive")
    pos = 8
    longnames = b""
    while pos + 60 <= len(data):
        header = data[pos:pos + 60]
        member = header[:16].decode("latin-1").rstrip()
        size = int(header[48:58].decode("latin-1").strip() or 0)
        body = data[pos + 60:pos + 60 + size]
        pos += 60 + size + (size & 1)
        if member == "/" or member == "/SYM64/":
            continue
        if member == "//":
            longnames = body
            continue
        if member.startswith("/") and member[1:].isdigit():
            start = int(member[1:])
            end = longnames.find(b"\0", start)
            for stop in (b"/\n", b"\n"):
                cut = longnames.find(stop, start)
                if cut != -1 and (end == -1 or cut < end):
                    end = cut
            member = longnames[start:end if end != -1 else None].decode("latin-1")
        member = member.rstrip("/")
        if body[:4] == b"\0\0\xff\xff":
            continue
        yield member, body


def be_words(code: bytes):
    """The big-endian instruction words of a code blob."""
    return list(struct.unpack(">%dI" % (len(code) // 4), code[: len(code) - len(code) % 4]))
