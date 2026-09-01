import sys


"""Report whether a vendor TU is supplied as buildable original source.

Only original buildable source makes a vendor TU PRESENT. Other vendor behavior
is reconstructed from ARTIST or supplied as an explicit platform implementation.
"""

def main():
    if len(sys.argv) < 2:
        print("Usage: python check_vendor_lib.py <tu_name>")
        sys.exit(1)
        
    tu_name = sys.argv[1]
    
    # Open source EA libraries are already in the vendor/ directory as source code.
    # Their original bodies, unlike closed binary middleware, are valid providers.
    tu_lower = tu_name.lower()
    if "eastl" in tu_lower or "eabase" in tu_lower or "ea::thread" in tu_lower:
        print("PRESENT")
        sys.exit(0)

    # Every closed-source SDK body must be reconstructed or replaced by a
    # documented platform implementation. Native libraries may still be
    # inspected, but their symbols never satisfy the build.
    print("MISSING")

if __name__ == "__main__":
    main()
