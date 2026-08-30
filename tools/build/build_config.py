#!/usr/bin/env python3
"""Loader for build.config.toml -- the ONE place machine-specific paths live.

Precedence everywhere: CLI argument > environment variable > build.config.toml >
probed default. `apply_env()` implements the env-beats-config half with
os.environ.setdefault (the same idiom as work.py's .env loader): a value from the
file only lands in the environment when the variable is not already set, and the
scripts' own probed defaults still apply when both are absent.

ENV_MAP is the single authoritative (section, key, env-var) contract; the
consumers of each variable are documented in build.config.example.toml.

Deliberately in tools/build/, NOT tools/assets/: build_game_data.py's WorkerRoots
only mirrors tools/assets into per-slot converter roots, so converters running in
a workroot cannot import this module -- by design they receive the resolved values
as environment variables from the orchestrator instead.
"""
import os

try:
    import tomllib  # stdlib from 3.11
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
CONFIG_PATH = os.path.join(REPO, "build.config.toml")

# (section, key, env_name)
ENV_MAP = [
    ("inputs",    "x360_root",       "BRN_X360_ROOT"),
    ("inputs",    "bpr_root",        "BRN_BPR_ROOT"),
    ("inputs",    "xb1_root",        "BRN_XB1_ROOT"),
    ("inputs",    "nushaders_tub",   "NUSHADERS_TUB"),
    ("inputs",    "xenia_dir",       "BRN_XENIA_DIR"),
    ("toolchain", "vcvars64",        "VCVARS64"),
    ("toolchain", "qt6_dir",         "QT6_DIR"),
    ("toolchain", "fxc",             "PC_FXC"),
    ("toolchain", "msys2_root",      "MSYS2_ROOT"),
    ("toolchain", "strawberry_root", "STRAWBERRY_ROOT"),
    ("toolchain", "ida_path",        "IDA_PATH"),
    ("toolchain", "undname_exe",     "UNDNAME_EXE"),
]

# Keys that are read directly (driver/stager), never exported as env vars.
_DIRECT_KEYS = {("output", "game_data"), ("build", "jobs"), ("build", "borrow_dir")}


def load_config(path=None):
    """Parse build.config.toml -> dict. {} when the file is absent. A syntax error
    is fatal with a clear file:line message (a silently-ignored config is worse)."""
    p = path or CONFIG_PATH
    if not os.path.isfile(p):
        return {}
    if tomllib is None:
        raise SystemExit("build.config.toml needs Python 3.11+ (tomllib)")
    try:
        with open(p, "rb") as fh:
            return tomllib.load(fh)
    except tomllib.TOMLDecodeError as e:
        raise SystemExit(f"{p}: TOML parse error: {e}")


def _clean(v):
    if not isinstance(v, str):
        return v
    v = os.path.expanduser(v.strip())
    return v or None


def get(cfg, section, key, default=None):
    """Bare config read (no env), for driver/stager-only keys."""
    v = _clean((cfg.get(section) or {}).get(key))
    return v if v not in (None, "") else default


def unknown_keys(cfg):
    """section.key entries not in the schema -- the typo guard for `build doctor`."""
    known = {(s, k) for s, k, _ in ENV_MAP} | _DIRECT_KEYS
    out = []
    for section, table in cfg.items():
        if not isinstance(table, dict):
            out.append(section)
            continue
        for key in table:
            if (section, key) not in known:
                out.append(f"{section}.{key}")
    return out


def apply_env(cfg):
    """Export each non-empty configured value as its env var (env wins over config).
    Returns {env_name: 'env'|'config'} provenance for values that ended up set."""
    prov = {}
    for section, key, env in ENV_MAP:
        v = _clean((cfg.get(section) or {}).get(key))
        if env in os.environ and os.environ[env]:
            prov[env] = "env"
        elif v:
            os.environ[env] = v
            prov[env] = "config"
    return prov
