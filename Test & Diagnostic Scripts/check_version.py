"""
Check which version of InteliCAD is installed in Fusion
"""

import os

FUSION_ADDINS = os.path.join(
    os.environ['APPDATA'], 
    r"Autodesk\Autodesk Fusion 360\API\AddIns\InteliCAD\InteliCAD.py"
)

print("="*80)
print("Checking Installed Add-In Version")
print("="*80)

print(f"\nChecking: {FUSION_ADDINS}\n")

if not os.path.exists(FUSION_ADDINS):
    print("File not found!")
    exit(1)

# Read the file and look for specific markers
with open(FUSION_ADDINS, 'r', encoding='utf-8') as f:
    content = f.read()

# Check for the new logging we added
if "→ Executing..." in content:
    print("NEW VERSION installed (has detailed execution logging)")
elif "executor.execute(op)" in content and "Got result" not in content:
    print("OLD VERSION installed (no detailed logging)")
else:
    print("UNKNOWN VERSION")

print(f"\nFile Info:")
print(f"   Size: {os.path.getsize(FUSION_ADDINS)} bytes")
print(f"   Modified: {os.path.getmtime(FUSION_ADDINS)}")

# Show a snippet around the execution code
if "for i, op in enumerate(operations, 1):" in content:
    idx = content.find("for i, op in enumerate(operations, 1):")
    snippet = content[idx:idx+500]
    print(f"\nExecution Code Snippet:")
    print("="*80)
    for line in snippet.split('\n')[:15]:
        print(f"   {line}")
    print("="*80)

print("\nIf showing OLD VERSION:")
print("   1. Make sure you ran: python update_addin.py")
print("   2. In Fusion: Stop the add-in completely")
print("   3. Wait 5 seconds")
print("   4. Run the add-in again")
print("   5. Fusion caches Python files - full restart may be needed!")