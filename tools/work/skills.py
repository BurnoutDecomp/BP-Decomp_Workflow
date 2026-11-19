#!/usr/bin/env python3
"""
skills -- link, list and check the agent skills in .agents/skills/.

Codex and Antigravity read .agents/skills/ themselves. Claude Code reads only
.claude/skills/, so `link` points .claude/skills at .agents/skills (a directory
junction on Windows, a symlink elsewhere). .claude/ is gitignored, so the link is
per checkout: every clone and worktree runs it once (`work bootstrap` does).

`check` holds every skill to the contract in .agents/skills/README.md, so a skill
that names a deleted tool, carries a dead link or forgets its user-invoked flags
fails loudly instead of quietly teaching the next agent something false.

`show` prints a skill for agents that have no skill loader (API / LiteLLM loops):
paste its output into the prompt.

    python tools/work/skills.py link [--force]
    python tools/work/skills.py check [--strict]
    python tools/work/skills.py list
    python tools/work/skills.py show <name> [--references]
    (or `work skills <action> ...`)
"""
import argparse
import os
import re
import subprocess
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILLS = os.path.join(ROOT, ".agents", "skills")
INDEX_MD = os.path.join(SKILLS, "README.md")
AGENTS_MD = os.path.join(ROOT, "AGENTS.md")
CLAUDE_LINK = os.path.join(ROOT, ".claude", "skills")

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_NAME = 64
MAX_DESC = 1024          # the strictest tool's limit (Claude Code truncates at 1,536)
MIN_DESC = 80            # shorter than this rarely says both what and when
MAX_BODY_LINES = 500     # Claude Code's documented SKILL.md limit
USER_PREFIX = "User-invoked only:"

# Ignored local inputs: a skill may point into them, but a fresh clone lacks them.
LOCAL_INPUTS = ("references/", "IDA Files/", ".ida-exports/", "scratch/", ".scratch/",
                "build/", ".trace/", ".ghidra-exports/", "progress/ledger.sqlite")
# A missing path under these prefixes is an error; elsewhere (illustrative examples
# under progress/ or b5-decomp/) it is only a warning.
STRICT_PATH_ROOTS = ("tools/", ".github/", ".agents/")
PATH_TOKEN = re.compile(
    r"(?<![\w./\\-])((?:tools|progress|\.github|\.agents|b5-decomp)[\\/][^\s`'\"()<>|,;*?{}$%\[\]]*)")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
ROOT_SCRIPTS = re.compile(r"(?<![\w./\\-])((?:work|build|debug-menu|convert-assets)\.cmd)\b")

HYGIENE = (
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "e-mail address"),
    (re.compile(r"(?i)\b[a-z]:[\\/]+users[\\/]+[^\\/\s]+"), "user-profile path"),
    (re.compile(r"(?i)(?:^|[\s\"'(`])/(?:[a-z]/)?(?:users|home)/[^/\s]+/"), "user-profile path"),
)
EMAIL_OK = ("noreply@anthropic.com", "@users.noreply.github.com", "@example.com", "@example.org",
            "git@github.com")   # the SSH remote user, not a person


# --------------------------------------------------------------------------- parsing
def _unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] == "'":
        return v[1:-1].replace("''", "'")
    if len(v) >= 2 and v[0] == v[-1] == '"':
        return v[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return v


def parse_frontmatter(text):
    """Return (fields, body, body_start_line, error). A deliberately small YAML subset:
    `key: value`, quoted scalars, folded/literal block scalars, simple block lists."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text, 1, "SKILL.md must start with a '---' frontmatter block"
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return {}, text, 1, "frontmatter block is not closed with '---'"
    fields, key, style, buf = {}, None, None, []

    def flush():
        if key is None:
            return
        if style == "|":
            fields[key] = "\n".join(buf).strip("\n")
        elif style == ">":
            fields[key] = re.sub(r"[ \t]*\n[ \t]*", " ", "\n".join(buf)).strip()
        elif style == "list":
            fields[key] = buf[:]
        else:
            fields[key] = " ".join(buf).strip()

    for raw in lines[1:end]:
        if raw.strip().startswith("#") and not (key and style in ("|", ">")):
            continue
        if raw and raw[0] not in " \t-" and ":" in raw:
            flush()
            k, _, v = raw.partition(":")
            key, buf = k.strip(), []
            v = v.strip()
            if v in (">", ">-", ">+", "|", "|-", "|+"):
                style = v[0]
            elif v == "":
                style = "list"
            else:
                fields[key], key, style = _unquote(v), None, None
        elif key is not None:
            s = raw.strip()
            if style == "list":
                if s.startswith("- "):
                    buf.append(_unquote(s[2:]))
            else:
                buf.append(s)
    flush()
    return fields, "\n".join(lines[end + 1:]), end + 2, None


def truthy(v):
    return str(v).strip().lower() in ("true", "yes", "on", "1")


def skill_dirs():
    if not os.path.isdir(SKILLS):
        return []
    return sorted(d for d in os.listdir(SKILLS) if os.path.isdir(os.path.join(SKILLS, d)))


def load(name):
    path = os.path.join(SKILLS, name, "SKILL.md")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    fields, body, body_line, err = parse_frontmatter(text)
    return path, text, fields, body, body_line, err


def implicit_disabled(name):
    """True when agents/openai.yaml switches off Codex's implicit invocation."""
    path = os.path.join(SKILLS, name, "agents", "openai.yaml")
    if not os.path.isfile(path):
        return False
    with open(path, encoding="utf-8") as f:
        text = f.read()
    return re.search(r"(?m)^policy:\s*$[\s\S]*?^\s+allow_implicit_invocation:\s*false\b", text) is not None


def section(text, heading_re):
    """The lines of the first markdown section whose heading matches heading_re."""
    out, inside, level = [], False, 0
    for line in text.splitlines():
        m = re.match(r"^(#+)\s+(.*)$", line)
        if m:
            if inside and len(m.group(1)) <= level:
                break
            if not inside and re.search(heading_re, m.group(2), re.I):
                inside, level = True, len(m.group(1))
                continue
        if inside:
            out.append(line)
    return out


def table_skills(lines, column=0):
    """{name: row} for each markdown table row whose cell at `column` names a skill in
    backticks (the index puts the skill first; AGENTS.md's routing table puts it last)."""
    rows = {}
    for line in lines:
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        m = re.search(r"`([a-z0-9-]+)`", cells[column]) if cells else None
        if m:
            rows[m.group(1)] = line
    return rows


# --------------------------------------------------------------------------- check
class Report:
    def __init__(self):
        self.items = []

    def err(self, where, msg):
        self.items.append(("ERROR", where, msg))

    def warn(self, where, msg):
        self.items.append(("warn", where, msg))

    def count(self, level):
        return sum(1 for lv, _, _ in self.items if lv == level)


def rel(path):
    return os.path.relpath(path, ROOT).replace("\\", "/")


def is_local_input(relpath):
    return any(relpath == p.rstrip("/") or relpath.startswith(p) for p in LOCAL_INPUTS)


def check_links(rep, path, text):
    base = os.path.dirname(path)
    for m in LINK_RE.finditer(text):
        target = m.group(1).strip("<>")
        if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("#"):
            continue                                  # URL, mailto:, in-page anchor
        target = urllib.parse.unquote(target.split("#", 1)[0])
        target = re.sub(r":\d+(?:-\d+)?$", "", target)   # file.md:42 line suffix
        if not target:
            continue
        resolved = os.path.normpath(os.path.join(base, target))
        if not resolved.startswith(ROOT):
            rep.err(rel(path), f"link leaves the repository: {m.group(1)}")
            continue
        if os.path.exists(resolved):
            continue
        r = rel(resolved)
        if is_local_input(r):
            rep.warn(rel(path), f"link into a local input this checkout lacks: {r}")
        else:
            rep.err(rel(path), f"dead link: {m.group(1)}")


def check_paths(rep, path, text):
    b5_populated = os.path.isdir(os.path.join(ROOT, "b5-decomp", "src"))
    seen = set()
    for m in PATH_TOKEN.finditer(text):
        if text[m.end():m.end() + 1] in ("*", "<", "{", "$", "%"):
            continue                                  # a glob or placeholder, not a path
        token = re.sub(r":\d+(?:-\d+)?$", "", m.group(1).replace("\\", "/")).rstrip(".:/")
        if not token or token in seen or "/" not in token:
            continue
        seen.add(token)
        if "..." in token or re.search(r"(?:^|/)(?:Foo|Bar|Baz|MyClass|Example)\w*(?:\.\w+)?$", token):
            continue                                  # an illustrative placeholder path
        if token.startswith("b5-decomp/") and not b5_populated:
            continue
        if os.path.exists(os.path.join(ROOT, token)):
            continue
        if is_local_input(token):
            continue
        if token.startswith(STRICT_PATH_ROOTS):
            rep.err(rel(path), f"names a path that does not exist: {token}")
        else:
            rep.warn(rel(path), f"names a path that does not exist (example?): {token}")
    for m in ROOT_SCRIPTS.finditer(text):
        if not os.path.exists(os.path.join(ROOT, m.group(1))):
            rep.err(rel(path), f"names a root script that does not exist: {m.group(1)}")


def check_hygiene(rep, path, text):
    for n, line in enumerate(text.splitlines(), 1):
        for rx, what in HYGIENE:
            for m in rx.finditer(line):
                if what == "e-mail address" and any(m.group(0).endswith(ok) for ok in EMAIL_OK):
                    continue
                rep.err(f"{rel(path)}:{n}", f"public-repo hygiene: {what} ({m.group(0).strip()})")


def check(strict=False):
    rep = Report()
    names = skill_dirs()
    if not names:
        print("no skills under .agents/skills/")
        return 1
    index_text = open(INDEX_MD, encoding="utf-8").read() if os.path.isfile(INDEX_MD) else ""
    index_rows = table_skills(section(index_text, r"^Index$"))
    agents_text = open(AGENTS_MD, encoding="utf-8").read() if os.path.isfile(AGENTS_MD) else ""
    routing_rows = table_skills(section(agents_text, r"\bskills?\b"), column=-1)
    if not index_text:
        rep.err(".agents/skills/README.md", "missing (it is the contract and the index)")
    if not routing_rows:
        rep.err("AGENTS.md", "no routing table: add a 'Skills' section whose table names each skill")

    for name in names:
        where = f".agents/skills/{name}"
        skill_md = os.path.join(SKILLS, name, "SKILL.md")
        if not os.path.isfile(skill_md):
            rep.err(where, "folder has no SKILL.md")
            continue
        path, text, fm, body, body_line, ferr = load(name)
        if ferr:
            rep.err(rel(path), ferr)
            continue
        fname = fm.get("name", "")
        if fname != name:
            rep.err(rel(path), f"frontmatter name {fname!r} must equal the folder name {name!r}")
        if not NAME_RE.match(name) or len(name) > MAX_NAME:
            rep.err(where, "folder name must be lowercase letters, digits and single hyphens (<= 64)")
        desc = fm.get("description", "")
        if not isinstance(desc, str) or not desc.strip():
            rep.err(rel(path), "frontmatter has no description (it is what makes the skill load)")
            desc = ""
        elif len(desc) > MAX_DESC:
            rep.err(rel(path), f"description is {len(desc)} characters (max {MAX_DESC})")
        elif len(desc) < MIN_DESC:
            rep.warn(rel(path), f"description is only {len(desc)} characters: say what AND when")
        body_lines = len(body.splitlines())
        if body_lines >= MAX_BODY_LINES:
            rep.err(rel(path), f"body is {body_lines} lines (keep it under {MAX_BODY_LINES}; move depth to references/)")

        user_only = truthy(fm.get("disable-model-invocation", "false"))
        codex_off = implicit_disabled(name)
        if user_only != codex_off:
            rep.err(where, "user-invoked flags disagree: disable-model-invocation in SKILL.md and "
                           "policy.allow_implicit_invocation: false in agents/openai.yaml go together")
        if user_only and not desc.startswith(USER_PREFIX):
            rep.err(rel(path), f"a user-invoked skill's description must start with {USER_PREFIX!r}")
        if not user_only and desc.startswith(USER_PREFIX):
            rep.err(rel(path), "description says user-invoked but disable-model-invocation is not true")

        row = index_rows.get(name)
        if row is None:
            rep.err(".agents/skills/README.md", f"index does not list {name}")
        elif user_only != ("user only" in row.lower()):
            rep.err(".agents/skills/README.md", f"index row for {name} disagrees about who invokes it")
        if routing_rows and name not in routing_rows:
            rep.err("AGENTS.md", f"routing table does not list {name}")

        files = [path]
        refdir = os.path.join(SKILLS, name, "references")
        if os.path.isdir(refdir):
            files += [os.path.join(refdir, f) for f in sorted(os.listdir(refdir)) if f.endswith(".md")]
        for f in files:
            t = text if f == path else open(f, encoding="utf-8").read()
            check_links(rep, f, t)
            check_paths(rep, f, t)
            check_hygiene(rep, f, t)

    for listed in sorted(set(index_rows) - set(names)):
        rep.err(".agents/skills/README.md", f"index lists {listed}, which has no folder")
    for listed in sorted(set(routing_rows) - set(names)):
        rep.err("AGENTS.md", f"routing table lists {listed}, which has no folder")
    if os.path.isfile(INDEX_MD):
        check_links(rep, INDEX_MD, index_text)
        check_hygiene(rep, INDEX_MD, index_text)

    for level, where, msg in rep.items:
        print(f"{level:5}  {where}: {msg}")
    errors, warns = rep.count("ERROR"), rep.count("warn")
    print(f"\n{len(names)} skills checked: {errors} error(s), {warns} warning(s)")
    return 1 if errors or (strict and warns) else 0


# --------------------------------------------------------------------------- link
def _same_target(link_path, target):
    try:
        return os.path.normcase(os.path.realpath(link_path)) == os.path.normcase(os.path.realpath(target))
    except OSError:
        return False


def _is_link(path):
    if os.path.islink(path):
        return True
    isjunction = getattr(os.path, "isjunction", None)
    if isjunction is not None:
        return isjunction(path)
    try:
        os.readlink(path)
        return True
    except (OSError, ValueError, NotImplementedError):
        return False


def link(force=False):
    if not os.path.isdir(SKILLS):
        print(f"nothing to link: {rel(SKILLS)} does not exist on this branch")
        return 1
    os.makedirs(os.path.dirname(CLAUDE_LINK), exist_ok=True)
    if os.path.lexists(CLAUDE_LINK):
        if _is_link(CLAUDE_LINK):
            if _same_target(CLAUDE_LINK, SKILLS):
                print(".claude/skills already points at .agents/skills")
                return 0
            if not force:
                print(".claude/skills is a link to somewhere else; re-run with --force to repoint it")
                return 1
            os.rmdir(CLAUDE_LINK) if os.name == "nt" else os.unlink(CLAUDE_LINK)
        elif os.path.isdir(CLAUDE_LINK) and not os.listdir(CLAUDE_LINK):
            os.rmdir(CLAUDE_LINK)
        else:
            print(".claude/skills is a real folder or file with content. Move any skills in it to\n"
                  ".agents/skills/ (so every agent gets them), delete it, then re-run.")
            return 1
    if os.name == "nt":
        res = subprocess.run(["cmd", "/c", "mklink", "/J", CLAUDE_LINK, SKILLS],
                             capture_output=True, text=True)
        if res.returncode != 0:
            print(f"mklink /J failed: {(res.stderr or res.stdout).strip()}")
            return 1
    else:
        os.symlink(os.path.relpath(SKILLS, os.path.dirname(CLAUDE_LINK)), CLAUDE_LINK,
                   target_is_directory=True)
    if not _same_target(CLAUDE_LINK, SKILLS):
        print("created .claude/skills but it does not resolve to .agents/skills")
        return 1
    print("linked .claude/skills -> .agents/skills (Claude Code now sees the skills; restart open sessions)")
    return 0


# --------------------------------------------------------------------------- list / show
def list_skills():
    for name in skill_dirs():
        try:
            _, _, fm, _, _, _ = load(name)
        except OSError:
            continue
        who = "user" if truthy(fm.get("disable-model-invocation", "false")) else "agent"
        desc = fm.get("description", "")
        first = re.split(r"(?<=[.!?])\s", desc, maxsplit=1)[0] if isinstance(desc, str) else ""
        print(f"{name:22} {who:5}  {first}")
    return 0


def show(name, references=False):
    if name not in skill_dirs():
        print(f"no skill named {name!r}; `work skills list` shows them")
        return 1
    path, text, _, _, _, _ = load(name)
    print(f"<!-- {rel(path)} -->\n{text.rstrip()}\n")
    refdir = os.path.join(SKILLS, name, "references")
    if references and os.path.isdir(refdir):
        for f in sorted(os.listdir(refdir)):
            if f.endswith(".md"):
                p = os.path.join(refdir, f)
                print(f"<!-- {rel(p)} -->\n{open(p, encoding='utf-8').read().rstrip()}\n")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="work skills", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="action", required=True)
    lk = sub.add_parser("link", help="point .claude/skills at .agents/skills (Claude Code)")
    lk.add_argument("--force", action="store_true", help="repoint an existing link that goes elsewhere")
    ck = sub.add_parser("check", help="validate every skill against .agents/skills/README.md")
    ck.add_argument("--strict", action="store_true", help="warnings fail too")
    sub.add_parser("list", help="one line per skill")
    sh = sub.add_parser("show", help="print a skill (for agents without a skill loader)")
    sh.add_argument("name")
    sh.add_argument("--references", action="store_true", help="also print its references/*.md")
    args = ap.parse_args(argv)
    if args.action == "link":
        return link(args.force)
    if args.action == "check":
        return check(args.strict)
    if args.action == "list":
        return list_skills()
    return show(args.name, args.references)


if __name__ == "__main__":
    sys.exit(main())
