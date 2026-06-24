"""IDAPython script to decompile one function headlessly in IDA Pro.

Reads function address from environment variable `IDA_DECOMPILE_ADDR`
and writes the pseudocode output to `IDA_DECOMPILE_OUT`.
"""
import os
import sys

import ida_auto
import ida_funcs
import ida_hexrays
import idc

print("[IDA-DECOMPILE] Script started.")

# Wait for auto-analysis to finish to ensure types and functions are fully resolved
print("[IDA-DECOMPILE] Waiting for auto-analysis...")
ida_auto.auto_wait()
print("[IDA-DECOMPILE] Auto-analysis completed.")

# Get environment variables
addr_str = os.environ.get("IDA_DECOMPILE_ADDR")
out_path = os.environ.get("IDA_DECOMPILE_OUT")

if not addr_str:
    print("ERROR: IDA_DECOMPILE_ADDR environment variable not set.")
    idc.qexit(1)

if not out_path:
    print("ERROR: IDA_DECOMPILE_OUT environment variable not set.")
    idc.qexit(1)

try:
    if addr_str.lower().startswith("0x"):
        addr = int(addr_str, 16)
    else:
        addr = int(addr_str)
except ValueError:
    print(f"ERROR: Invalid address string: {addr_str}")
    idc.qexit(1)

print(f"[IDA-DECOMPILE] Querying address: 0x{addr:X}")

# Ensure the Hex-Rays decompiler is initialized
if not ida_hexrays.init_hexrays_plugin():
    print("ERROR: Hex-Rays decompiler plugin could not be initialized.")
    idc.qexit(1)

# Retrieve the function at the target address
func = ida_funcs.get_func(addr)
if not func:
    print(f"ERROR: No function found at address 0x{addr:X}")
    idc.qexit(1)

# Decompile the function
try:
    cfunc = ida_hexrays.decompile(func)
    if cfunc:
        pseudocode = str(cfunc)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(pseudocode)
        print(f"[IDA-DECOMPILE] Successfully decompiled function at 0x{addr:X}")
        print(f"[IDA-DECOMPILE] Written to {out_path}")
        idc.qexit(0)
    else:
        print(f"ERROR: Decompilation returned None for function at 0x{addr:X}")
        idc.qexit(1)
except Exception as e:
    print(f"ERROR: Decompilation failed: {e}")
    idc.qexit(1)
