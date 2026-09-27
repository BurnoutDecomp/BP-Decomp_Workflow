"""Linux Landlock filesystem boundary inherited by a hosted job's children.

The web process keeps access to its session store. Conversion processes can read
the installed tools and system libraries, and can write only their own workspace.
Ubuntu 24.04's kernel supports this unprivileged API. Fail closed if unavailable.
"""
import ctypes
import os
from pathlib import Path
import sys


def restrict(workspace, repo):
    if sys.platform != "linux":
        raise RuntimeError("Hosted conversion sandbox requires Linux with Landlock support")
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    create, add_rule, restrict_self = 444, 445, 446
    abi = libc.syscall(create, ctypes.c_void_p(), 0, 1)
    if abi < 1:
        raise RuntimeError("Landlock is unavailable. Use an Ubuntu 24.04 kernel with Landlock enabled.")
    # Include REFER (v2) and TRUNCATE (v3) when the running kernel supports them.
    handled = (1 << (15 if abi >= 3 else 14 if abi >= 2 else 13)) - 1
    read = (1 << 0) | (1 << 2) | (1 << 3)
    write = handled & ~((1 << 6) | (1 << 11))  # No device-node creation.

    class Ruleset(ctypes.Structure):
        _fields_ = [("handled_access_fs", ctypes.c_uint64)]

    class PathRule(ctypes.Structure):
        _pack_ = 1
        _fields_ = [("allowed_access", ctypes.c_uint64), ("parent_fd", ctypes.c_int32)]

    attr = Ruleset(handled)
    fd = libc.syscall(create, ctypes.byref(attr), ctypes.sizeof(attr), 0)
    if fd < 0:
        raise OSError(ctypes.get_errno(), "Cannot create converter sandbox")
    try:
        grants = [(Path(repo), read), (Path(sys.prefix), read), (Path(sys.base_prefix), read),
                  (Path(workspace), write)]
        grants += [(Path(p), read) for p in ("/usr", "/lib", "/lib64", "/etc", "/proc")]
        grants += [(Path(p), (1 << 1) | (1 << 2)) for p in ("/dev/null", "/dev/zero", "/dev/random", "/dev/urandom")]
        seen = set()
        for path, access in grants:
            if not path.exists():
                continue
            path = path.resolve()
            if (path, access) in seen:
                continue
            seen.add((path, access))
            parent = os.open(path, os.O_PATH | os.O_CLOEXEC)
            try:
                rule = PathRule(access, parent)
                if libc.syscall(add_rule, fd, 1, ctypes.byref(rule), 0):
                    raise OSError(ctypes.get_errno(), "Cannot configure converter sandbox")
            finally:
                os.close(parent)
        if libc.prctl(38, 1, 0, 0, 0) or libc.syscall(restrict_self, fd, 0):
            raise OSError(ctypes.get_errno(), "Cannot activate converter sandbox")
    finally:
        os.close(fd)
