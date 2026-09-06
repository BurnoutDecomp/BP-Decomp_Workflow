#!/usr/bin/env python3
"""template_static_sweep.py -- find `static` LOCALS inside TEMPLATE function bodies.

⭐ THE DEFECT CLASS. A `static` declared inside a template function body is ONE OBJECT PER
INSTANTIATION. Where the console has ONE word for the module -- a device shadow, a
"last bound" cache, a one-shot latch -- every instantiation gets its own private copy and
they lie to each other. The failure is silent: the code compiles, links, runs, and reports
success while the device is in a state nobody's cache describes.

It has bitten this tree three times on the graphics path:
  * the sky-dome leaf's shadow;
  * BrnLionBlendRenderer's three vertex-program statics and its texture shadow -- the
    latter made every particle quad sample the depth buffer;
  * ImRenderer<V>::BeginRendering / ::SetProgram's `spgLastVertexProgram` and the vertex
    DESCRIPTOR twin (dfb711d7). BeginRendering's own ResetShadowing() nulled the device's
    copy while the per-instantiation cache still said "already bound", so
    FlushVertexProgramState returned early and 4.6 MILLION vertices were submitted at
    hr=S_OK with NO VERTEX SHADER BOUND.

⚠️ A NAMESPACE-SCOPE SWEEP DOES NOT FIND THESE. An earlier pass over 166 files / 62
namespace-scope objects found no further forks and was read as "the class is closed" -- it
could not have caught a `static` inside a template body, which is exactly where the third
one lived. That is why this tool exists as a separate shape.

METHOD. Walk each file tracking brace depth, remembering the depth at which the nearest
enclosing `template<...>` opened. A `static` declaration seen at least two braces deeper
than that (class/function scope + the function body) is a per-instantiation object.
`static_assert`, `static const` class constants and static MEMBER FUNCTION declarations are
excluded -- none of them is state.

READ EVERY HIT; A HIT IS A LEAD, NOT A VERDICT. A per-instantiation diagnostic print budget
is a cosmetic quirk; a per-instantiation cache of a device word is the defect. The question
to ask of each is: DOES THE CONSOLE HAVE ONE WORD HERE?

    python tools/re/template_static_sweep.py [root ...]        # default: b5-decomp/src
"""
import os
import re
import sys

EXTS = (".h", ".hpp", ".cpp", ".inl")

STATIC_RE = re.compile(r"^\s*static\s+")
TEMPLATE_RE = re.compile(r"^\s*template\s*<")
CONST_RE = re.compile(r"^\s*static\s+const\b")
# A declaration carrying a parenthesised parameter list before its ; or { is a function.
FUNC_RE = re.compile(r"\b\w+\s*\([^;]*\)\s*(const\s*)?[;{]")


def sweep(roots):
    hits = []
    files = 0
    for root in roots:
        for dirpath, _dirnames, filenames in os.walk(root):
            for fn in filenames:
                if not fn.endswith(EXTS):
                    continue
                path = os.path.join(dirpath, fn)
                files += 1
                try:
                    text = open(path, encoding="utf-8", errors="replace").read()
                except OSError:
                    continue
                depth = 0
                template_depths = []
                pending_template = False
                for lineno, raw in enumerate(text.split("\n"), 1):
                    code = raw.split("//")[0]
                    if TEMPLATE_RE.match(raw):
                        pending_template = True
                    if pending_template and "{" in code:
                        template_depths.append(depth)
                        pending_template = False
                    if (STATIC_RE.match(raw)
                            and "static_assert" not in raw
                            and not CONST_RE.match(raw)
                            and template_depths
                            and depth >= template_depths[-1] + 2
                            and not FUNC_RE.search(raw)):
                        hits.append((path, lineno, raw.strip()))
                    depth += code.count("{") - code.count("}")
                    while template_depths and depth <= template_depths[-1]:
                        template_depths.pop()
    return files, hits


def main():
    roots = sys.argv[1:]
    if not roots:
        here = os.path.dirname(os.path.abspath(__file__))
        roots = [os.path.normpath(os.path.join(here, "..", "..", "b5-decomp", "src"))]
    files, hits = sweep(roots)
    print("scanned %d files; %d per-instantiation static(s) inside template bodies"
          % (files, len(hits)))
    for path, lineno, txt in hits:
        print("%s:%d\n    %s" % (path, lineno, txt[:160]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
