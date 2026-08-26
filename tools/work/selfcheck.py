#!/usr/bin/env python3
"""Ledger-free compile self-check for workflow agents.

Usage: python tools/work/selfcheck.py <file.cpp> [<more files>...]

Runs the SAME compile gate as `work submit` (verify.compile_gate) but does NOT
touch the sqlite ledger or write a reviewer packet, so many agents can run it
concurrently without racing. Prints STATUS=pass|fail|skip and the compiler log.
"""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify  # noqa: E402

if __name__ == "__main__":
    files = sys.argv[1:]
    if not files:
        print("STATUS=skip\n(no files given)")
        sys.exit(0)
    status, log = verify.compile_gate(files)
    print(f"STATUS={status}")
    print(log)
