"""IDAPython script to export all functions from an IDB into structured JSON files.

Creates one JSON file per function under `.ida-exports/<db_name>/<addr_hex>.json`.
For each function, exports:
- Address & Name
- Prototype Signature
- Local Variables (Decompiler)
- Pseudocode (Hex-Rays)
- Assembly listing (single string: one "<ea>  <disasm>  ; <comment>" line per instruction)
- Callers (xrefs to) and Callees (xrefs from)
"""
import json
import os
import sys

import ida_auto
import ida_bytes
import ida_funcs
import ida_hexrays
import ida_lines
import ida_xref
import idautils
import idc

# Wait for auto-analysis to finish
print("[IDA-EXPORT] Waiting for auto-analysis...")
ida_auto.auto_wait()
print("[IDA-EXPORT] Auto-analysis complete.")

# Initialize Hex-Rays
has_hexrays = ida_hexrays.init_hexrays_plugin()
if not has_hexrays:
    print("[IDA-EXPORT] WARNING: Hex-Rays decompiler plugin not available. Will export assembly-only.")

DB_PATH = idc.get_idb_path()
DB_NAME = os.path.splitext(os.path.basename(DB_PATH))[0]

# Determine output directory
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".ida-exports", DB_NAME)
if not os.path.exists(OUT_DIR):
    os.makedirs(OUT_DIR)

print(f"[IDA-EXPORT] Output directory: {OUT_DIR}")

# Optional limits from environment
EXPORT_MAX = int(os.environ.get("EXPORT_MAX", "0") or "0")

def get_callees(func):
    """Get list of function addresses called by this function."""
    callees = []
    # Iterate over all heads/instructions in the function
    for ea in idautils.Heads(func.start_ea, func.end_ea):
        # Look for code references (calls) originating from this instruction
        for xref in idautils.XrefsFrom(ea, ida_xref.XREF_ALL):
            if xref.type in (ida_xref.fl_CF, ida_xref.fl_CN): # Code Call Far / Near
                if xref.to not in callees and xref.to != func.start_ea:
                    callees.append(xref.to)
    return callees

def get_callers(func_ea):
    """Get list of function addresses calling this function."""
    callers = []
    for xref in idautils.XrefsTo(func_ea, ida_xref.XREF_ALL):
        if xref.type in (ida_xref.fl_CF, ida_xref.fl_CN):
            # Resolve the calling instruction's function
            caller_func = ida_funcs.get_func(xref.frm)
            if caller_func:
                if caller_func.start_ea not in callers:
                    callers.append(caller_func.start_ea)
    return callers

def get_lvars(cfunc):
    """Extract local variable info from decompiled function."""
    lvars = []
    if not cfunc:
        return lvars
    try:
        for lvar in cfunc.get_lvars():
            type_str = str(lvar.type())
            lvars.append({
                "name": lvar.name,
                "type": type_str,
                "is_reg": lvar.is_reg(),
                "size": lvar.width
            })
    except Exception as exc:
        print(f"[IDA-EXPORT] Failed to get local variables: {exc}")
    return lvars

def export_function(fva):
    func = ida_funcs.get_func(fva)
    if not func:
        return False

    name = ida_funcs.get_func_name(fva) or f"sub_{fva:X}"
    
    # Base JSON metadata
    fdata = {
        "address": f"0x{fva:X}",
        "name": name,
        "prototype": None,
        "variables": [],
        "pseudocode": None,
        "assembly": "",
        "xrefs_to": [],
        "xrefs_from": []
    }

    # 1. Decompile with Hex-Rays if available
    if has_hexrays:
        try:
            cfunc = ida_hexrays.decompile(func)
            if cfunc:
                fdata["pseudocode"] = str(cfunc)
                # Try getting the function signature / prototype
                try:
                    # cfunc.print_dstr() prints variable declarations + body,
                    # cfunc.get_func_type() retrieves the type signature
                    ftype = cfunc.type
                    fdata["prototype"] = f"{str(ftype.get_rettype())} {name}{str(ftype)}"
                except Exception:
                    pass
                fdata["variables"] = get_lvars(cfunc)
        except Exception as exc:
            pass

    # 2. Extract Assembly as a single listing string: "<ea>  <disasm>  ; <comment>".
    # One line per instruction keeps the address (for branch-target / xref lookup)
    # and any IDA comment inline, without the per-instruction JSON-object overhead.
    asm_lines = []
    for ea in idautils.Heads(func.start_ea, func.end_ea):
        disasm = idc.generate_disasm_line(ea, 0)
        # Strip IDA HTML-like tags or extra color markers if present
        disasm = ida_lines.tag_remove(disasm)

        # Get comments (regular, else repeatable)
        cmt = ida_bytes.get_cmt(ea, False) or ""
        rcmt = ida_bytes.get_cmt(ea, True) or ""
        comment = cmt if cmt else rcmt

        line = f"0x{ea:X}  {disasm}"
        if comment:
            line += f"  ; {comment}"
        asm_lines.append(line)

    fdata["assembly"] = "\n".join(asm_lines)

    # 3. Extract Xrefs
    try:
        for caller_ea in get_callers(fva):
            c_name = ida_funcs.get_func_name(caller_ea) or f"sub_{caller_ea:X}"
            fdata["xrefs_to"].append({
                "address": f"0x{caller_ea:X}",
                "name": c_name
            })
            
        for callee_ea in get_callees(func):
            c_name = ida_funcs.get_func_name(callee_ea) or f"sub_{callee_ea:X}"
            fdata["xrefs_from"].append({
                "address": f"0x{callee_ea:X}",
                "name": c_name
            })
    except Exception as exc:
        print(f"[IDA-EXPORT] Failed to resolve xrefs for {name}: {exc}")

    # Write to file
    out_path = os.path.join(OUT_DIR, f"0x{fva:X}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(fdata, f, indent=2)
    return True

def main():
    print("[IDA-EXPORT] Beginning function export...")
    functions = list(idautils.Functions())
    total = len(functions)
    print(f"[IDA-EXPORT] Found {total} functions to export.")

    exported_count = 0
    for idx, fva in enumerate(functions):
        if EXPORT_MAX and exported_count >= EXPORT_MAX:
            print(f"[IDA-EXPORT] Reached EXPORT_MAX limit of {EXPORT_MAX}.")
            break

        if idx % 1000 == 0 and idx > 0:
            print(f"[IDA-EXPORT] Progress: {idx}/{total} functions processed...")

        try:
            if export_function(fva):
                exported_count += 1
        except Exception as exc:
            fname = ida_funcs.get_func_name(fva) or f"sub_{fva:X}"
            print(f"[IDA-EXPORT] ERROR exporting function {fname} (0x{fva:X}): {exc}")

    print(f"[IDA-EXPORT] Export complete! Successfully exported {exported_count} functions to {OUT_DIR}.")
    idc.qexit(0)

if __name__ == "__main__":
    main()
