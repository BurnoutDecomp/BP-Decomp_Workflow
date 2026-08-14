import sys
import subprocess
import os

def main():
    if len(sys.argv) < 2:
        print("Usage: python check_vendor_lib.py <tu_name>")
        sys.exit(1)
        
    tu_name = sys.argv[1]
    
    # Extract the core class or file name (e.g., class:rw::collision::VolumeLineQuery -> VolumeLineQuery)
    target = tu_name.split("::")[-1].replace(".cpp", "").replace(".h", "")
    if target.startswith("class:"):
        target = target[6:]
        
    # Open source EA libraries are already in the vendor/ directory as source code.
    # We do not need to check the binary for them.
    tu_lower = tu_name.lower()
    if "eastl" in tu_lower or "eabase" in tu_lower or "ea::thread" in tu_lower:
        print("PRESENT")
        sys.exit(0)
        
    # We currently only have rwcore.lib to check against for closed-source middleware.
    # Paths are repo-root-derived (this script used to hardcode a CWD-relative lib and
    # a Community-only vcvars -- both silently dead on non-Community boxes).
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    lib_path = os.path.join(root, "b5-decomp", "vendor", "renderware", "lib", "rwcore.lib")
    resolver = os.path.join(root, "tools", "build", "msvc_env.bat")

    if not os.path.exists(lib_path):
        print("MISSING")
        sys.exit(0)

    # Run dumpbin through the shared MSVC resolver (VCVARS64 env override supported).
    # Resolver output is suppressed so it doesn't pollute the pipe.
    cmd = f'cmd.exe /c "call "{resolver}" >NUL 2>&1 && dumpbin /symbols "{lib_path}" | findstr /I "{target}""'
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        # findstr returns 0 if it finds a match, 1 otherwise
        if result.returncode == 0:
            print("PRESENT")
        else:
            print("MISSING")
    except Exception as e:
        print(f"Error running dumpbin: {e}")
        print("MISSING")

if __name__ == "__main__":
    main()
