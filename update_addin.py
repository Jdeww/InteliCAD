"""
Update Fusion 360 Add-In Files
Copies the latest versions to the Fusion add-ins folder
"""

import os
import shutil

# Source files (in repository)
REPO_DIR = r"C:\Users\jdwil\Documents\Projects\GTC 2026 Golden Ticket\fusion_addin"

# Destination (Fusion add-ins folder)
FUSION_ADDINS = os.path.join(
    os.environ['APPDATA'], 
    r"Autodesk\Autodesk Fusion 360\API\AddIns\InteliCAD"
)

FILES_TO_COPY = [
    "InteliCAD.py",
    "InteliCAD.manifest",
    "api_client.py",
    "model_analyzer.py",
    "operation_executor.py"
]

print("="*80)
print("Updating Fusion 360 Add-In Files")
print("="*80)

print(f"\nSource: {REPO_DIR}")
print(f"Destination: {FUSION_ADDINS}\n")

# Check if destination exists
if not os.path.exists(FUSION_ADDINS):
    print(f"Fusion add-ins folder not found!")
    print(f"Expected: {FUSION_ADDINS}")
    print(f"\n   Run install_addin.py first to create the folder")
    exit(1)

# Copy each file
success_count = 0
for filename in FILES_TO_COPY:
    src = os.path.join(REPO_DIR, filename)
    dst = os.path.join(FUSION_ADDINS, filename)
    
    if not os.path.exists(src):
        print(f"{filename} - NOT FOUND in repository")
        continue
    
    try:
        shutil.copy2(src, dst)
        print(f"{filename} - copied successfully")
        success_count += 1
    except Exception as e:
        print(f"{filename} - FAILED: {e}")

print(f"\n{'='*80}")
print(f"Updated {success_count}/{len(FILES_TO_COPY)} files")
print(f"{'='*80}")

print(f"\nNEXT STEPS:")
print(f"1. Open Fusion 360")
print(f"2. Utilities → Add-Ins → Scripts and Add-Ins")
print(f"3. Find 'InteliCAD' and click 'Stop'")
print(f"4. Then click 'Run' to restart with new code")
print(f"\nThe updated add-in should now show detailed execution logs!")
