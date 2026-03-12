"""
Quick diagnostic - check the InteliCAD log and current job status
"""

import os
import requests

LOG_FILE = os.path.join(os.path.expanduser("~"), "Desktop", "intelicad_log.txt")
BACKEND_URL = "http://127.0.0.1:8000"

print("InteliCAD Diagnostic")

# 1. Check log file
print("\n1. Checking log file...")
if os.path.exists(LOG_FILE):
    print(f"Log file exists: {LOG_FILE}")
    with open(LOG_FILE, 'r') as f:
        lines = f.readlines()
    
    print(f"Last 20 lines of log:")
    print("   " + "-"*70)
    for line in lines[-20:]:
        print(f"   {line.rstrip()}")
    print("   " + "-"*70)
else:
    print(f"Log file not found at: {LOG_FILE}")
    print("The add-in may not be running")

# 2. Check backend jobs
print("\n2. Checking pending jobs...")
try:
    response = requests.get(f"{BACKEND_URL}/poll-jobs/")
    data = response.json()
    
    awaiting = data.get('awaiting_analysis', {})
    ready = data.get('ready_for_execution', {})
    
    print(f"   Jobs awaiting analysis: {len(awaiting)}")
    if awaiting:
        for job_id, info in list(awaiting.items())[:3]:
            print(f"      - {job_id[:8]}... '{info.get('text_command')}'")
    
    print(f"   Jobs ready for execution: {len(ready)}")
    if ready:
        for job_id, info in list(ready.items())[:3]:
            print(f"      - {job_id[:8]}... '{info.get('text_command')}'")
    
except Exception as e:
    print(f"Could not connect to backend: {e}")

# 3. Check if add-in is polling
print("\n3. Diagnosis:")
if not os.path.exists(LOG_FILE):
    print("PROBLEM: Add-in is not running")
    print("   → Start it in Fusion: Utilities → Add-Ins → InteliCAD → Run")
elif os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'r') as f:
        content = f.read()
    
    if "InteliCAD started" not in content:
        print("PROBLEM: Add-in started but crashed immediately")
        print("   → Check the log file for errors")
    elif "Found" in content:
        print("   ✓ Add-in IS polling and finding jobs")
    elif len(content.strip().split('\n')) < 5:
        print("PROBLEM: Add-in started but no polling activity")
        print("   → The polling thread may have crashed")
        print("   → Check if backend is running: http://127.0.0.1:8000")
    else:
        print("Add-in is running but may not be finding jobs")

print("\n" + "="*80)
print("NEXT STEPS:")
print("="*80)

if not os.path.exists(LOG_FILE):
    print("1. Open Fusion 360")
    print("2. Utilities → Add-Ins → Scripts and Add-Ins")
    print("3. Click 'Add-Ins' tab")
    print("4. Find 'InteliCAD' and click 'Run'")
    print("5. You should see a popup with the log file location")
    print("6. Run this script again")
elif len(awaiting) > 0:
    print("1. Make sure Fusion 360 is open")
    print("2. Make sure a .f3d file is open in Fusion")
    print("3. Make sure InteliCAD add-in is running")
    print("4. Wait 10 seconds and check the log file")
    print(f"5. The log should show activity within 10 seconds")
else:
    print("No pending jobs - submit one with:")
    print("   python test_complex_commands.py")