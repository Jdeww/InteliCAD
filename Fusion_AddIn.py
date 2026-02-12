"""
InteliCAD Fusion 360 Add-In Installer
Run this once to install the add-in into Fusion 360.

    python install_addin.py
"""

import os
import shutil
import sys

ADDIN_NAME = "InteliCAD"
ADDIN_FILES = [
    "InteliCAD.py",
    "InteliCAD.manifest",
    "api_client.py",
    "model_analyzer.py",
    "operation_executor.py",
    "ui_manager.py",
]

# Possible Fusion 360 add-in directories
POSSIBLE_DIRS = [
    os.path.join(os.environ.get('APPDATA', ''), "Autodesk", "Autodesk Fusion 360", "API", "AddIns"),
    os.path.join(os.environ.get('LOCALAPPDATA', ''), "Autodesk", "webdeploy", "production"),
    r"C:\Users\jdwil\AppData\Roaming\Autodesk\Autodesk Fusion 360\API\AddIns",
]

print("=" * 80)
print("🔧 InteliCAD - Fusion 360 Add-In Installer")
print("=" * 80)

# Step 1: Find Fusion 360 add-ins directory
print("\n1. Locating Fusion 360 Add-Ins directory...")
fusion_addin_dir = None

for d in POSSIBLE_DIRS:
    if os.path.exists(d):
        fusion_addin_dir = d
        print(f"   ✓ Found: {d}")
        break

if not fusion_addin_dir:
    print("   ❌ Could not find Fusion 360 Add-Ins directory automatically.")
    print("\n   Please enter the path manually.")
    print("   (Open Fusion 360 → Utilities → Add-Ins → Scripts and Add-Ins")
    print("    click the green '+' icon to see the folder location)")
    fusion_addin_dir = input("\n   Paste the path here: ").strip().strip('"')
    
    if not os.path.exists(fusion_addin_dir):
        print(f"\n   ❌ Path does not exist: {fusion_addin_dir}")
        sys.exit(1)

# Step 2: Check source files exist
print("\n2. Checking source files...")
script_dir = os.path.dirname(os.path.abspath(__file__))
missing = []

for f in ADDIN_FILES:
    src = os.path.join(script_dir, "fusion_addin", f)
    if os.path.exists(src):
        print(f"   ✓ {f}")
    else:
        print(f"   ❌ Missing: {f}")
        missing.append(f)

if missing:
    print(f"\n❌ Missing {len(missing)} file(s). Make sure all add-in files are in the fusion_addin/ folder.")
    sys.exit(1)

# Step 3: Create add-in folder
print(f"\n3. Creating add-in folder...")
target_dir = os.path.join(fusion_addin_dir, ADDIN_NAME)

if os.path.exists(target_dir):
    print(f"   ⚠️  Folder already exists, updating...")
    shutil.rmtree(target_dir)

os.makedirs(target_dir)
print(f"   ✓ Created: {target_dir}")

# Step 4: Copy files
print(f"\n4. Copying files...")
for f in ADDIN_FILES:
    src = os.path.join(script_dir, "fusion_addin", f)
    dst = os.path.join(target_dir, f)
    shutil.copy2(src, dst)
    print(f"   ✓ {f}")

# Step 5: Done
print(f"""
{'='*80}
✅ Installation Complete!

Next steps:
1. Open Fusion 360
2. Go to: Utilities → Add-Ins → Scripts and Add-Ins
3. Click the 'Add-Ins' tab
4. Find 'InteliCAD' in the list
5. Click 'Run'
6. Check 'Run on Startup' to auto-start it

Then start your backend:
    uvicorn fastUpload:app --reload

The add-in will poll for jobs every 10 seconds.
{'='*80}
""")