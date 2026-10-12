"""Find debug-menu entries and build a standalone, searchable navigation guide.

Uses only the Python standard library. Indexes literal PC registrations and the
existing ARTIST inventory; it does not run the game or execute debug actions.
"""
from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import webbrowser

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/re"))
from debug_menu_inventory import call_arguments

UNKNOWN = object()
STRING = r'"(?:\\.|[^"\\])*"'
LEXEMES = re.compile(STRING + r"|'(?:\\.|[^'\\])*'|//[^\n]*|/\*[\s\S]*?\*/")
IDENTIFIER = r"[A-Za-z_]\w*"
QUALIFIED = rf"{IDENTIFIER}(?:::{IDENTIFIER})*"
CALL = re.compile(r"\b(RegisterVariable|RegisterFunction)\s*\(")
ASSIGNMENT = re.compile(rf"\b({IDENTIFIER})\s*=(?!=)\s*([^;]+);")
CORE_OWNERS = {
    "CgsDev::DebugComponent", "CgsDev::DebugInterface", "CgsDev::DebugManager",
    "CgsDev::DebugUI::VariableManager", "CgsDev::DebugUI::FunctionManager",
}


def blank(text: str) -> str:
    return re.sub(r"[^\n]", " ", text)


def clean_source(text: str) -> str:
    """Keep offsets/lines while removing comments and literal #if 0 branches."""
    text = LEXEMES.sub(lambda m: blank(m[0]) if m[0].startswith(("//", "/*")) else m[0], text)
    enabled, output = [True], []
    for line in text.splitlines(keepends=True):
        directive = re.match(r"\s*#\s*(if|ifdef|ifndef|else|elif|endif)\b(.*)", line)
        if directive:
            kind, condition = directive.groups()
            if kind in ("if", "ifdef", "ifndef"):
                enabled.append(enabled[-1] and not (kind == "if" and condition.strip() == "0"))
            elif kind in ("else", "elif") and len(enabled) > 1:
                # Unknown build conditions are indexed on both sides. Only an
                # explicit #if 0 is suppressed; this is not a preprocessor.
                enabled[-1] = enabled[-2]
            elif kind == "endif" and len(enabled) > 1:
                enabled.pop()
            output.append(blank(line))
        else:
            output.append(line if enabled[-1] else blank(line))
    return "".join(output)


def string_value(expression: str):
    expression = expression.strip()
    if re.fullmatch(rf"(?:{STRING}\s*)+", expression):
        try:
            return "".join(ast.literal_eval(m[0]) for m in re.finditer(STRING, expression))
        except (ValueError, SyntaxError):
            pass
    if expression in ("nullptr", "NULL", "0"):
        return None
    if expression in ("true", "false"):
        return expression == "true"
    return UNKNOWN


def qualify(name: str, prefix: str) -> str:
    if not prefix or name.startswith(prefix.split("::")[0] + "::"):
        return name
    return prefix + "::" + name


@dataclass
class Scope:
    start: int
    end: int
    kind: str
    name: str
    parent: Scope | None
    signature: str = ""
    parameters: list[str] = field(default_factory=list)

    @property
    def owner(self) -> str:
        return self.name.rsplit("::", 1)[0] if "::" in self.name else ""


@dataclass
class Source:
    path: str
    text: str
    scopes: list[Scope]
    code: str

    def at(self, position: int, kind: str) -> Scope | None:
        matches = (s for s in self.scopes if s.kind == kind and s.start < position < s.end)
        return max(matches, key=lambda s: s.start, default=None)

    def environment(self, position: int, function: Scope | None = None, seed: dict | None = None) -> dict:
        values = dict(seed or {})
        for match in ASSIGNMENT.finditer(self.text, 0, position):
            containing = self.at(match.start(), "function")
            if containing is not None and containing is not function:
                continue
            # Do not leak a local from a closed block or another class.
            blocks = [s for s in self.scopes if s.start < match.start() < s.end]
            if any(not (s.start < position < s.end) and s.kind != "namespace" for s in blocks):
                continue
            if any(s.kind == "namespace" and s.name and function is not None
                   and not function.name.startswith(s.name + "::") for s in blocks):
                continue
            expression = match[2].strip()
            values[match[1]] = values.get(expression, string_value(expression))
        return values


def parse_source(path: str, text: str) -> Source:
    text = clean_source(text)
    masked = LEXEMES.sub(lambda m: blank(m[0]), text)
    scopes, stack, boundary, parentheses = [], [], 0, 0
    controls = {"if", "for", "while", "switch", "catch"}
    for match in re.finditer(r"[{};()]", masked):
        position, char = match.start(), match[0]
        if char == "(":
            parentheses += 1
            continue
        if char == ")":
            parentheses = max(0, parentheses - 1)
            continue
        if char == ";" and parentheses:
            continue
        if char == "{":
            header = masked[boundary:position].strip()
            named_parent = next((s for s in reversed(stack) if s.kind in ("namespace", "class")), None)
            prefix = named_parent.name if named_parent else ""
            namespace = re.search(rf"\bnamespace(?:\s+({QUALIFIED}))?\s*$", header)
            cls = re.search(rf"\b(?:class|struct)\s+({IDENTIFIER})(?:\s+final)?\s*(?::[^{{}};]*)?$", header)
            func = re.search(rf"(~?{QUALIFIED})\s*\(([^{{}};]*)\)\s*(?:(?:const|override|final|noexcept)\s*)*$", header)
            kind, name, parameters = "block", "", []
            if namespace:
                kind, name = "namespace", qualify(namespace[1], prefix) if namespace[1] else prefix
            elif cls:
                kind, name = "class", qualify(cls[1], prefix)
            elif func and func[1] not in controls:
                kind, name = "function", qualify(func[1], prefix)
                try:
                    args, _ = call_arguments("(" + func[2] + ")", 0)
                except ValueError:
                    # A brace initializer or macro can resemble a function
                    # header. Keep it as an unnamed scope instead.
                    kind, name, args = "block", "", []
                for argument in args:
                    identifiers = re.findall(IDENTIFIER, argument.split("=")[0])
                    parameters.append(identifiers[-1] if identifiers else "")
            scope = Scope(position, len(text), kind, name, stack[-1] if stack else None, header, parameters)
            scopes.append(scope)
            stack.append(scope)
        elif char == "}" and stack:
            stack.pop().end = position
        boundary = position + 1
    return Source(path, text, scopes, masked)


def collect_sources(source_root: Path) -> list[Source]:
    sources = []
    for path in sorted(source_root.rglob("*")):
        if path.suffix.lower() not in (".cpp", ".h", ".hpp"):
            continue
        relative = path.relative_to(source_root)
        if relative.parts[0].lower() in ("sdks", "vendor"):
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        if not any(marker in text for marker in ("Register", "GetName", "GetPath")):
            continue
        sources.append(parse_source("b5-decomp/src/" + relative.as_posix(), text))
    return sources


def component_identities(sources: list[Source]) -> dict:
    """Recover literal getters, including the inherited empty GetPath default."""
    identities, classes, declared = defaultdict(dict), {}, defaultdict(set)
    for source in sources:
        for scope in source.scopes:
            if scope.kind == "class":
                classes[scope.name] = scope.signature
            if scope.kind != "function" or scope.name.rsplit("::", 1)[-1] not in ("GetName", "GetPath"):
                continue
            body = source.text[scope.start + 1:scope.end].strip()
            returned = re.fullmatch(r"return\s+([\s\S]+?)\s*;", body)
            if returned:
                value = string_value(returned[1])
                if value is not UNKNOWN:
                    identities[scope.owner][scope.name.rsplit("::", 1)[-1]] = value
        for match in re.finditer(r"\b(GetName|GetPath)\s*\(\s*\)\s*(?:const\s*)?(?:override\s*)?(?:final\s*)?[;{]", source.text):
            cls = source.at(match.start(), "class")
            if cls and source.at(match.start(), "function") is None:
                declared[cls.name].add(match[1])

    def inherits_component(name: str, visited: set) -> bool:
        if name == "CgsDev::DebugComponent":
            return True
        if name in visited or name not in classes:
            return False
        visited = visited | {name}
        inheritance = re.split(r"(?<!:):(?!:)", classes[name], maxsplit=1)[-1]
        for base in re.findall(QUALIFIED, inheritance):
            if base in ("public", "protected", "private", "virtual"):
                continue
            prefix = name.rsplit("::", 1)[0] if "::" in name else ""
            for candidate in (base, qualify(base, prefix)):
                if candidate != name and inherits_component(candidate, visited):
                    return True
        return False

    def inherited_getter(name: str, getter: str, visited: set):
        if name in visited:
            return UNKNOWN
        if getter in identities[name]:
            return identities[name][getter]
        if getter in declared[name]:
            return UNKNOWN
        if name == "CgsDev::DebugComponent":
            return ""
        prefix = name.rsplit("::", 1)[0] if "::" in name else ""
        inheritance = re.split(r"(?<!:):(?!:)", classes.get(name, ""), maxsplit=1)[-1]
        for base in re.findall(QUALIFIED, inheritance):
            for candidate in (base, qualify(base, prefix)):
                if candidate != name and (candidate in classes or candidate == "CgsDev::DebugComponent"):
                    value = inherited_getter(candidate, getter, visited | {name})
                    if value is not UNKNOWN:
                        return value
        return UNKNOWN

    for name in classes:
        if inherits_component(name, set()):
            identities[name]["component"] = True
            for getter in ("GetPath", "GetName"):
                value = inherited_getter(name, getter, set())
                if value is not UNKNOWN:
                    identities[name][getter] = value
    return dict(identities)


def segments(*paths: str | None) -> list[str]:
    # MenuManager::CreateMenuPath accepts either separator and ignores empty
    # segments. A caption is appended separately: '/' inside a caption is text.
    return [part for path in paths if path for part in re.split(r"[/\\]+", path) if part]


def expression_value(expression: str | None, environment: dict):
    if expression is None:
        return UNKNOWN
    return environment.get(expression.strip(), string_value(expression))


def condition_allows(source: Source, position: int, environment: dict) -> bool:
    for scope in source.scopes:
        if not scope.start < position < scope.end:
            continue
        condition = re.fullmatch(rf"if\s*\(\s*(!?)\s*({IDENTIFIER})\s*\)", scope.signature)
        if condition:
            value = environment.get(condition[2], UNKNOWN)
            if isinstance(value, bool) and (not value if not condition[1] else value):
                return False
    return True


def helper_contexts(sources: list[Source], targets: dict[str, Scope]) -> dict[str, list[dict]]:
    """Bind literal arguments of uniquely named registration helpers.

    Shared PC reflection/shadow helpers take their menu path as an argument.
    Ambiguous overloads and computed arguments stay unresolved.
    """
    by_short, records = defaultdict(list), defaultdict(list)
    for name in targets:
        by_short[name.rsplit("::", 1)[-1]].append(name)
    if not by_short:
        return {}
    pattern = re.compile(rf"\b({QUALIFIED})\s*\(")
    for source in sources:
        for match in pattern.finditer(source.code):
            short = match[1].rsplit("::", 1)[-1]
            if short not in by_short:
                continue
            function = source.at(match.start(), "function")
            if function is None:
                continue
            candidates = by_short[short]
            exact = [name for name in candidates if name == match[1] or name.endswith("::" + match[1])]
            if len(exact) == 1:
                candidates = exact
            if len(candidates) != 1 or candidates[0] == function.name:
                continue
            try:
                args, _ = call_arguments(source.text, match.end() - 1)
            except ValueError:
                continue
            target = targets[candidates[0]]
            if len(args) != len(target.parameters):
                continue
            records[candidates[0]].append((source, match.start(), function, args))

    def resolve(name: str, visited: set) -> list[dict]:
        if name in visited or not records[name]:
            return [{}]
        contexts = []
        for source, position, caller, args in records[name]:
            parents = resolve(caller.name, visited | {name}) if caller.name in targets else [{}]
            for parent in parents:
                env = source.environment(position, caller, parent)
                if not condition_allows(source, position, env):
                    continue
                contexts.append({parameter: expression_value(arg, env)
                                 for parameter, arg in zip(targets[name].parameters, args)})
        return contexts or [{}]

    return {name: resolve(name, set()) for name in targets}


def pc_entries(sources: list[Source], identities: dict) -> tuple[list[dict], int]:
    calls, targets, symbolic = [], {}, 0
    for source in sources:
        for match in CALL.finditer(source.code):
            function = source.at(match.start(), "function")
            if function is None or function.owner in CORE_OWNERS:
                continue
            try:
                args, _ = call_arguments(source.text, match.end() - 1)
            except ValueError:
                continue
            if len(args) < 2:
                continue
            env = source.environment(match.start(), function)
            caption = expression_value(args[-1], env)
            if not isinstance(caption, str):
                symbolic += 1
                continue
            receiver = re.search(rf"({IDENTIFIER}|\))\s*(\.|->|::)\s*$", source.text[max(function.start, match.start() - 100):match.start()])
            component = identities.get(function.owner, {})
            relative = bool(component.get("component")) and (
                receiver is None or receiver[1] == "this" or receiver[2] == "::")
            absolute = False
            if receiver:
                receiver_text = source.text[max(function.start, match.start() - 160):match.start()]
                if receiver[1] == ")":
                    absolute = bool(re.search(r"Get(?:Variable|Function)Manager\(\)\s*\.\s*$", receiver_text))
                else:
                    declaration = rf"\b(?:DebugInterface|VariableManager|FunctionManager)\s*[&*]*\s*{re.escape(receiver[1])}\b"
                    absolute = bool(re.search(declaration, function.signature + source.text[:match.start()]))
            minimum = 2 if match[1] == "RegisterVariable" else 3
            group = args[-2] if len(args) > minimum else None
            if group in function.parameters:
                targets[function.name] = function
            calls.append((source, function, match, args, env, caption, relative, absolute, group))

    contexts, entries = helper_contexts(sources, targets), []
    for source, function, match, args, env, caption, relative, absolute, group in calls:
        bindings = contexts.get(function.name, [{}]) if group in function.parameters else [{}]
        for binding in bindings:
            values = source.environment(match.start(), function, binding) if binding else env
            if not condition_allows(source, match.start(), values):
                continue
            component = identities.get(function.owner, {})
            base_known = not relative or ("GetName" in component and "GetPath" in component)
            base = segments(component.get("GetPath"), component.get("GetName")) if relative else []
            path = expression_value(group, values) if group is not None else None
            if path is not UNKNOWN and path is not None and not isinstance(path, str):
                path = UNKNOWN
            known = (relative or absolute) and base_known and path is not UNKNOWN
            menus = ["Development", *base, *segments(path if path is not UNKNOWN else None)]
            notes = []
            if relative:
                notes.append("Select the component section to populate its controls.")
            if not known:
                notes.append("Path contains a computed or unresolved expression: " + (group or function.owner))
            target = re.sub(r"\s+", "", args[0])
            body = source.text[function.start:function.end]
            for setter in re.finditer(r"\b(SetReadOnly|SetVisible)\s*\(", body):
                try:
                    setter_args, _ = call_arguments(body, setter.end() - 1)
                except ValueError:
                    continue
                if len(setter_args) == 2 and re.sub(r"\s+", "", setter_args[0]) == target:
                    if setter[1] == "SetReadOnly" and setter_args[1] == "true":
                        notes.append("Read-only in source.")
                    if setter[1] == "SetVisible" and setter_args[1] == "false":
                        notes.append("Hidden in source; runtime code may change visibility.")
            entries.append({"caption": caption, "menus": menus, "resolved": known,
                "kind": "variable" if match[1] == "RegisterVariable" else "function",
                "origins": ["pc"], "notes": notes,
                "sources": [{"path": source.path, "line": source.text.count("\n", 0, match.start()) + 1,
                             "function": function.name, "origin": "pc"}]})
    return entries, symbolic


def reference_entries(inventory: dict, identities: dict) -> list[dict]:
    entries = []
    for row in inventory.get("entries", []):
        if row.get("caption") is None:
            continue
        component = identities.get(row.get("component"), {})
        name = row.get("component_name")
        if name is None:
            name = component.get("GetName", UNKNOWN)
        path = row.get("component_path")
        if path is None:
            path = component.get("GetPath", UNKNOWN)
        api = row.get("registration_api", "")
        manager = "::VariableManager::" in api or "::FunctionManager::" in api
        implicit = row.get("uses_component_path")
        base_known = manager or (name is not UNKNOWN and path is not UNKNOWN)
        base = [] if manager else segments(path if path is not UNKNOWN else None, name if name is not UNKNOWN else None)
        group = None if implicit is True else row.get("path", UNKNOWN)
        if group is None and implicit is not True:
            group = UNKNOWN
        known = base_known and group is not UNKNOWN and implicit is not None
        menus = ["Development", *base, *segments(group if group is not UNKNOWN else None)]
        notes = ["Original ARTIST registration; may be absent from the PC menu."]
        if not known:
            notes.append("Original path or registration overload is unresolved.")
        entries.append({"caption": row["caption"], "menus": menus, "resolved": known,
            "kind": row["kind"], "origins": ["artist"], "notes": notes,
            "sources": [{"path": row["original_export"], "line": row["pseudocode_line"],
                         "address": row.get("original_call_address"),
                         "function": row["function"], "origin": "artist"}]})
    return entries


def merge_entries(entries: list[dict]) -> list[dict]:
    merged = {}
    for entry in entries:
        # Menu captions are case insensitive; leaf captions remain verbatim.
        # Keep unresolved sites separate: identical partial paths aren't proof
        # that they resolve to the same menu.
        key = (entry["caption"], tuple(part.casefold() for part in entry["menus"]), entry["kind"])
        if not entry["resolved"]:
            key += (entry["sources"][0]["path"], entry["sources"][0]["line"])
        if key not in merged:
            merged[key] = entry
            continue
        existing = merged[key]
        for field in ("origins", "notes", "sources"):
            existing[field].extend(value for value in entry[field] if value not in existing[field])
    return sorted(merged.values(), key=lambda r: ("pc" not in r["origins"], not r["resolved"], r["caption"].casefold(), r["menus"]))


def build_index(source_root: Path, inventory_path: Path) -> dict:
    if not source_root.is_dir():
        raise ValueError(f"Source directory not found: {source_root}")
    sources = collect_sources(source_root)
    identities = component_identities(sources)
    pc, symbolic = pc_entries(sources, identities)
    inventory = json.loads(inventory_path.read_text(encoding="utf-8-sig")) if inventory_path.is_file() else {}
    references = reference_entries(inventory, identities)
    entries = merge_entries(pc + references)
    return {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "entries": entries,
        "summary": {"pc": sum("pc" in row["origins"] for row in entries),
                    "reference": sum("pc" not in row["origins"] for row in entries),
                    "unresolved_pc": sum(not row["resolved"] and "pc" in row["origins"] for row in entries),
                    "symbolic_pc": symbolic,
                    "symbolic_reference": sum(row.get("caption") is None for row in inventory.get("entries", []))}}


def search(entries: list[dict], query: str, include_reference: bool = False) -> list[dict]:
    terms = re.findall(r"\w+", query.casefold())
    results = []
    for entry in entries:
        if not include_reference and "pc" not in entry["origins"]:
            continue
        caption = entry["caption"].casefold()
        haystack = " ".join([caption, *entry["menus"]]).casefold()
        if all(term in haystack for term in terms):
            score = (0 if caption == query.casefold().strip() else 1 if all(t in caption for t in terms) else 2,
                     "pc" not in entry["origins"], not entry["resolved"], caption)
            results.append((score, entry))
    return [entry for _, entry in sorted(results, key=lambda pair: pair[0])]


def write_page(index: dict, output: Path) -> None:
    template = Path(__file__).with_name("template.html").read_text(encoding="utf-8")
    payload = json.dumps(index, ensure_ascii=False).replace("<", "\\u003c").replace("&", "\\u0026")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(template.replace("__MENU_INDEX__", payload), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "b5-decomp/src")
    parser.add_argument("--inventory", type=Path, default=ROOT / "progress/debug_menu/entries.json")
    parser.add_argument("--output", type=Path, default=ROOT / "build/debug-menu/index.html")
    parser.add_argument("--query", help="Search in the terminal instead of opening the browser")
    parser.add_argument("--include-reference", action="store_true", help="Include ARTIST reference entries in terminal searches")
    parser.add_argument("--json", action="store_true", help="Print terminal search results as JSON")
    parser.add_argument("--no-open", action="store_true", help="Generate the page without opening it")
    args = parser.parse_args()
    if args.json and args.query is None:
        parser.error("--json requires --query")
    try:
        index = build_index(args.source, args.inventory)
        if args.query is not None:
            results = search(index["entries"], args.query, args.include_reference)
            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                for entry in results:
                    route = " > ".join(entry["menus"] + ([] if entry["resolved"] else ["[path unresolved]"]) + [entry["caption"]])
                    print(route)
                    print("  " + ("PC source" if "pc" in entry["origins"] else "ARTIST reference"))
                print(f"{len(results)} result(s)")
            return 0
        output = args.output.resolve()
        write_page(index, output)
        print(f"Indexed {index['summary']['pc']} PC entries; {index['summary']['reference']} additional ARTIST references.")
        print(f"Search page: {output}")
        if not args.no_open and not webbrowser.open(output.as_uri()):
            print("Open the generated HTML file in your browser.")
        return 0
    except (OSError, ValueError) as error:
        print(f"Debug menu search: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
