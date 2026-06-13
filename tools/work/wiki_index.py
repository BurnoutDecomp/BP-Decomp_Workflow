#!/usr/bin/env python3
"""Extract struct/type field tables from the burnout.wiki MediaWiki dump into a
small, queryable index (references/Wiki/types.json).

WHY: the raw dump is ~30 MB of XML — too big to grep mid-reconstruction. The
field NAMES/TYPES the wiki documents already follow this project's Hungarian
convention (mfLuminance, mv4Scale, ...), so they are near drop-in member names.
But the OFFSETS/SIZES are whatever build each page was authored against (B1 ->
Paradise), NOT necessarily our X360 2007-02 spine. So the index is authoritative
for names/types/semantics ONLY; pseudocode/asm remains the source of truth for
layout. Every entry is tagged with the build it came from so a wrong-build table
is visibly advisory. Paradise-era pages are marked primary.

Usage:
    python tools/work/wiki_index.py            # rebuild references/Wiki/types.json
    python tools/work/wiki_index.py --lookup CGtRGB   # print what we have for a type
"""
import os, re, json, html, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WIKI_DIR = os.path.join(ROOT, "references", "Wiki")
DUMP = os.path.join(WIKI_DIR, "burnoutwiki-20260602.xml")
OUT = os.path.join(WIKI_DIR, "types.json")

SKIP_NS = ("File", "User", "Template", "MediaWiki", "Category", "Help", "Module")

HEADING_RE = re.compile(r"^\s*(={1,6})\s*(.*?)\s*\1\s*$")
# a real struct offset cell: hex, decimal, or empty (a continued cell). Anything
# else is prose from a multi-line description cell that MediaWiki split into rows.
OFFSET_OK = re.compile(r"^(0x[0-9A-Fa-f]+|\d+)?$")


def derive_build(title: str, section: str) -> tuple[str, bool]:
    """Return (build_label, is_primary). Primary = name-authoritative for our
    X360 2007-02 spine: the Paradise/Burnout 5 era on EITHER console. PS3 counts
    as primary too — it's the same game's symbols (the wiki tables are partly
    derived from the PS3 symbols), invaluable where the X360 export is missing."""
    hay = f"{title} / {section}"
    low = hay.lower()
    is_ps3 = "playstation 3" in low or "ps3" in low
    is_x360 = "xbox 360" in low or "x360" in low or "xenon" in low
    if "paradise" in low or "burnout 5" in low or "burnout5" in low:
        plat = " PS3" if is_ps3 else (" X360" if is_x360 else "")
        return (f"Paradise{plat}", True)
    if is_ps3:
        # untagged PS3 page -> Paradise-era console sister of our spine
        return ("PS3", True)
    if "remaster" in low:
        return ("Paradise Remastered", False)
    if "dominator" in low:
        return ("Dominator", False)
    if "revenge" in low:
        return ("Revenge", False)
    if "legends" in low:
        return ("Legends", False)
    if "burnout 3" in low or "takedown" in low:
        return ("Burnout 3", False)
    if "burnout 2" in low or "point of impact" in low:
        return ("Burnout 2", False)
    if "burnout (game)" in low or re.search(r"\bburnout 1\b", low):
        return ("Burnout 1", False)
    # Paradise is the dominant build documented on the wiki and shares the
    # GtXxx/Renderware engine with our spine -> treat untagged as Paradise-ish
    # but NOT primary (we didn't positively confirm the build).
    return ("unknown", False)


def clean_cell(s: str) -> str:
    s = s.strip()
    # strip simple wiki/html markup that gets in the way of a name/type token
    s = re.sub(r"</?(code|tt|nowiki|small|sub|sup|b|i)>", "", s, flags=re.I)
    s = re.sub(r"'''?", "", s)               # bold/italic
    s = re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", s)  # [[link|text]] -> text
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"<ref[^>]*/>", "", s)
    s = re.sub(r"\{\{[^}]*\}\}", "", s)       # templates
    return s.strip()


def parse_tables(body: str):
    """Yield (section, columns, rows) for each wikitable in a page body."""
    lines = body.splitlines()
    section = ""
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        m = HEADING_RE.match(line)
        if m:
            section = clean_cell(m.group(2))
            i += 1
            continue
        if line.lstrip().startswith("{|"):
            # collect until matching |}
            cols, rows, cur = [], [], []
            i += 1
            while i < n and not lines[i].lstrip().startswith("|}"):
                ln = lines[i].rstrip()
                s = ln.lstrip()
                if s.startswith("|-"):
                    if cur:
                        rows.append(cur)
                        cur = []
                elif s.startswith("!"):
                    parts = re.split(r"!!", s[1:])
                    cols.extend(clean_cell(p) for p in parts)
                elif s.startswith("|") and not s.startswith("|}"):
                    parts = re.split(r"\|\|", s[1:])
                    cur.extend(clean_cell(p) for p in parts)
                i += 1
            if cur:
                rows.append(cur)
            yield section, cols, rows
        i += 1


def normalize(section, title, cols, rows):
    """Build a record if the table has a recognizable Name/Type (struct) or
    ID/Name (enum) shape."""
    lc = [c.lower() for c in cols]

    def idx(*names):
        for nm in names:
            if nm in lc:
                return lc.index(nm)
        return None

    i_off = idx("offset")
    i_size = idx("size")
    i_type = idx("type")
    i_name = idx("name")
    i_desc = idx("description", "notes", "comments", "value")
    i_id = idx("id")
    i_alt = idx("alternate names", "alternate name", "aliases")

    kind = None
    if i_name is not None and i_type is not None:
        kind = "struct"
    elif i_id is not None and i_name is not None:
        kind = "enum"
    if kind is None:
        return None

    def cell(row, j):
        return row[j] if (j is not None and j < len(row)) else ""

    fields = []
    for row in rows:
        if not any(c.strip() for c in row):
            continue
        if kind == "struct":
            off = cell(row, i_off).strip()
            nm = cell(row, i_name).strip()
            ty = cell(row, i_type).strip()
            # drop prose rows from split multi-line cells (offset not offset-shaped)
            # and wholly-empty rows; keep real fields and padding rows
            if not OFFSET_OK.match(off) or not (off or nm or ty):
                continue
            fields.append({
                "offset": off,
                "size": cell(row, i_size),
                "type": ty,
                "name": nm,
                "desc": cell(row, i_desc),
            })
        else:
            fields.append({
                "id": cell(row, i_id),
                "name": cell(row, i_name),
                "alt": cell(row, i_alt),
                "desc": cell(row, i_desc),
            })
    if not fields:
        return None

    build, primary = derive_build(title, section)
    return {
        "type": section or title,
        "kind": kind,
        "build": build,
        "primary": primary,
        "page": title,
        "columns": cols,
        "fields": fields,
    }


def build_index():
    data = open(DUMP, encoding="utf-8").read()
    pages = re.findall(r"<title>(.*?)</title>.*?<text[^>]*>(.*?)</text>", data, re.S)
    types: dict[str, list] = {}
    n_pages = n_tables = 0
    for title, raw in pages:
        title = html.unescape(title).strip()
        if title.split(":")[0] in SKIP_NS:
            continue
        body = html.unescape(raw)
        n_pages += 1
        for section, cols, rows in parse_tables(body):
            rec = normalize(section, title, cols, rows)
            if not rec:
                continue
            n_tables += 1
            types.setdefault(rec["type"], []).append(rec)

    # drop byte-identical duplicates (some pages repeat a struct in a notes
    # section), then put primary (Paradise-era) entries first within each type
    for key, recs in list(types.items()):
        seen, uniq = set(), []
        for r in recs:
            sig = (r["build"], r["page"], json.dumps(r["fields"], sort_keys=True))
            if sig in seen:
                continue
            seen.add(sig)
            uniq.append(r)
        uniq.sort(key=lambda r: (not r["primary"], r["build"]))
        types[key] = uniq

    out = {
        "generated_from": os.path.basename(DUMP),
        "note": ("Field NAMES/TYPES/semantics are authoritative; OFFSETS/SIZES "
                 "are per the tagged build and may differ from the X360 spine — "
                 "verify layout against pseudocode/asm. 'primary':true == "
                 "Paradise/X360-era page."),
        "n_types": len(types),
        "types": types,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"pages scanned: {n_pages}  tables indexed: {n_tables}  types: {len(types)}")
    print(f"wrote {OUT}")


def lookup(name):
    idx = json.load(open(OUT, encoding="utf-8"))
    recs = idx["types"].get(name)
    if not recs:
        # case-insensitive contains fallback
        hits = [k for k in idx["types"] if name.lower() in k.lower()]
        print(f"no exact match for {name!r}; similar: {hits[:20]}")
        return
    for r in recs:
        star = "*" if r["primary"] else " "
        print(f"\n[{star}] {r['type']}  ({r['kind']}, build={r['build']}, page={r['page']})")
        for fld in r["fields"]:
            if r["kind"] == "struct":
                print(f"    {fld['offset']:>6} {fld['size']:>5}  {fld['type']:24} {fld['name']}"
                      + (f"   ; {fld['desc']}" if fld['desc'] else ""))
            else:
                print(f"    {fld['id']:>5}  {fld['name']}"
                      + (f"   (alt: {fld['alt']})" if fld['alt'] else ""))


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--lookup":
        lookup(sys.argv[2])
    else:
        build_index()
