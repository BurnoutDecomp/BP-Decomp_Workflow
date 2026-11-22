"""Compare one compiled function with its ARTIST body.

EXACT means all of these hold:
  * the two bodies have the same length;
  * every instruction word is identical outside the fields our object's relocations
    rewrite at link time (a `bl` displacement, an `@ha`/`@l` half, ...);
  * every call relocation names the function ARTIST calls at that instruction, when
    ARTIST's target is a named function (an unnamed target is counted as unverified);
  * every literal-pool constant we reference (`__real@...`, `__xmm@...`) holds the same
    value at the address ARTIST loads it from.
Data relocations to other symbols are masked, not checked (counted as unchecked).

The SCORE is a fuzzy instruction match for everything that is not exact: both bodies
become token streams with address-shaped fields abstracted, and the score is difflib's
ratio over them (2*matches / total), 0-100. Only an exact match scores 100.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import difflib
import re

from coff import (Function, ObjectFile, RELOC_FIELD, NOT_A_FIELD, REL_REL24, REL_REL14,
                  REL_REFHI, REL_REFLO, be_words)
from artist import Artist, demangle, normal_name

LITERAL = re.compile(r"^__(?:real|xmm|vec|m128)@([0-9a-fA-F]{8}|[0-9a-fA-F]{16}|[0-9a-fA-F]{32})$")
# ARTIST data lives here; a `lis` loading a high half in this range is an address.
ADDRESS_HI = range(0x8200, 0x8300)
DFORM_ADDRESS_USERS = {14, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47,
                       48, 49, 50, 51, 52, 53, 54, 55}


def branch_target(word, address, mask):
    displacement = word & mask
    sign_bit = (mask + 4) >> 1
    if displacement & sign_bit:
        displacement -= sign_bit * 2
    return (displacement + (0 if word & 2 else address)) & 0xFFFFFFFF


@dataclass
class Result:
    status: str                   # "exact" | "nonmatching"
    score: float
    size: int
    artist_size: int
    first_diff: int | None = None
    calls_checked: int = 0
    calls_unverified: int = 0
    calls_wrong: list = field(default_factory=list)
    data_checked: int = 0
    data_unchecked: int = 0
    data_wrong: list = field(default_factory=list)
    unknown_relocs: int = 0

    def row(self):
        out = {"status": self.status, "score": self.score, "size": self.size, "artist_size": self.artist_size}
        if self.first_diff is not None:
            out["first_diff"] = self.first_diff
        for key in ("calls_unverified", "data_unchecked", "unknown_relocs"):
            if getattr(self, key):
                out[key] = getattr(self, key)
        if self.calls_wrong:
            out["calls_wrong"] = self.calls_wrong[:8]
        if self.data_wrong:
            out["data_wrong"] = self.data_wrong[:8]
        return out


def _field_masks(fn: Function, count: int):
    masks = [0] * count
    unknown = 0
    for reloc in fn.relocs:
        if reloc.type in NOT_A_FIELD or not 0 <= reloc.offset < count * 4:
            continue
        bits = RELOC_FIELD.get(reloc.type)
        if bits is None:
            bits = 0xFFFFFFFF
            unknown += 1
        masks[reloc.offset // 4] |= bits
    return masks, unknown


def refhi_lo_address(high_word, low_word):
    low = low_word & 0xFFFF
    signed_low = low - 0x10000 if low & 0x8000 else low
    return (((high_word & 0xFFFF) << 16) + signed_low) & 0xFFFFFFFF


def symbol_name(obj: ObjectFile, index: int) -> str:
    sym = obj.symbols.get(index)
    return sym.name if sym else "?"


def ours_tokens(fn: Function, obj: ObjectFile, words, masks):
    by_word = {}
    for reloc in fn.relocs:
        if reloc.type not in NOT_A_FIELD:
            by_word.setdefault(reloc.offset // 4, reloc)
    tokens = []
    for i, word in enumerate(words):
        reloc = by_word.get(i)
        if reloc is None:
            tokens.append(("w", word))
        elif reloc.type in (REL_REL24, REL_REL14):
            tokens.append(("call", word & ~masks[i] & 0xFFFFFFFF, normal_name(demangle(symbol_name(obj, reloc.symbol)))))
        else:
            tokens.append(("reloc", word & ~masks[i] & 0xFFFFFFFF))
    return tokens


def artist_tokens(words, address, size, artist: Artist):
    """Tokens for ARTIST's body, abstracting what a relocation would have produced."""
    tokens = []
    base_regs = set()
    for i, word in enumerate(words):
        opcode = word >> 26
        here = address + 4 * i
        if opcode == 18:
            target = branch_target(word, here, 0x03FFFFFC)
            if address <= target < address + size:
                tokens.append(("w", word))
            else:
                name = artist.name_at(target)
                tokens.append(("call", word & ~0x03FFFFFC & 0xFFFFFFFF,
                               normal_name(name) if name else "#%08X" % target))
            continue
        rd, ra = (word >> 21) & 31, (word >> 16) & 31
        if opcode == 15 and ra == 0 and (word & 0xFFFF) in ADDRESS_HI:
            tokens.append(("reloc", word & 0xFFFF0000))
            base_regs.add(rd)
            continue
        if opcode in DFORM_ADDRESS_USERS and ra in base_regs:
            tokens.append(("reloc", word & 0xFFFF0000))
            if opcode == 14 and rd != ra:
                base_regs.discard(rd)
            continue
        if opcode in (14, 15, 24, 25, 28, 29, 32, 33, 34, 35, 40, 41, 42, 43, 31):
            base_regs.discard(rd)
        tokens.append(("w", word))
    return tokens


def compare(fn: Function, obj: ObjectFile, artist: Artist, address: int, artist_size: int,
            fuzzy: bool = True) -> Result:
    """Exact or not, and (unless fuzzy=False, for callers that only need the verdict) a score."""
    ours = be_words(fn.code)
    theirs = be_words(artist.bytes(address, artist_size)) if artist_size else []
    masks, unknown = _field_masks(fn, len(ours))
    result = Result("nonmatching", 0.0, len(fn.code), artist_size, unknown_relocs=unknown)

    # Positional comparison outside relocated fields.
    first = None
    for i in range(max(len(ours), len(theirs))):
        if i >= len(ours) or i >= len(theirs):
            first = i * 4
            break
        keep = ~masks[i] & 0xFFFFFFFF
        if ours[i] & keep != theirs[i] & keep:
            first = i * 4
            break

    # Symbolic checks: call targets and literal-pool values. They read ARTIST's word at
    # the relocation's own offset, so they only mean something once the bodies line up.
    aligned = first is None and len(ours) == len(theirs)
    refhi = {}
    for reloc in sorted(fn.relocs, key=lambda r: r.offset) if aligned else ():
        i = reloc.offset // 4
        if reloc.type == REL_REFHI and i < len(theirs):
            refhi.setdefault(reloc.symbol, []).append(i)
        if i >= len(theirs):
            continue
        if reloc.type in (REL_REL24, REL_REL14):
            mask = 0x03FFFFFC if reloc.type == REL_REL24 else 0x0000FFFC
            target = branch_target(theirs[i], address + 4 * i, mask)
            ours_name = normal_name(demangle(symbol_name(obj, reloc.symbol)))
            name = artist.name_at(target)
            if name is None:
                result.calls_unverified += 1
            elif artist.matches_name(target, ours_name):
                result.calls_checked += 1
            else:
                result.calls_wrong.append({"at": reloc.offset, "ours": ours_name, "artist": name})
        elif reloc.type == REL_REFLO:
            symbol = symbol_name(obj, reloc.symbol)
            literal = LITERAL.match(symbol)
            if not literal:
                result.data_unchecked += 1
                continue
            highs = [h for h in refhi.get(reloc.symbol, []) if h <= i]
            if not highs:
                result.data_unchecked += 1
                continue
            target = refhi_lo_address(theirs[highs[-1]], theirs[i])
            want = bytes.fromhex(literal.group(1))
            try:
                got = artist.bytes(target, len(want))
            except KeyError:
                got = b""
            if got == want:
                result.data_checked += 1
            else:
                result.data_wrong.append({"at": reloc.offset, "symbol": symbol, "artist": got.hex()})

    exact = aligned and not result.calls_wrong and not result.data_wrong and not unknown
    result.first_diff = None if exact else (first if first is not None else
                                            (result.calls_wrong[0]["at"] if result.calls_wrong else
                                             result.data_wrong[0]["at"] if result.data_wrong else 0))
    if exact:
        result.status, result.score = "exact", 100.0
        return result
    if not fuzzy:
        return result
    a = ours_tokens(fn, obj, ours, masks)
    b = artist_tokens(theirs, address, artist_size, artist)
    score = round(100.0 * difflib.SequenceMatcher(None, a, b, autojunk=False).ratio(), 1)
    result.score = min(score, 99.9)
    return result
