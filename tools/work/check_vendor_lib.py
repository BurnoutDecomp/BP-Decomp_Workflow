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
        
    # We currently only have rwtypes.lib to check against for closed-source middleware
    lib_path = r"b5-decomp\vendor\renderware\lib\rwtypes.lib"
    vcvars = r"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
    
    if not os.path.exists(lib_path):
        print("MISSING")
        sys.exit(0)
        
    # Run dumpbin through the MSVC developer command prompt to check for the symbol
    # We suppress vcvars64.bat output so it doesn't pollute the pipe.
    cmd = f'cmd.exe /c ""{vcvars}" > NUL && dumpbin /symbols "{lib_path}" | findstr /I "{target}""'
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
