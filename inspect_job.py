"""
Quick script to inspect what operations were generated for a job
Usage: python inspect_job.py [job_id]

Log file location: C:\\Users\\jdwil\\Documents\\Projects\\GTC 2026 Golden Ticket\\intelicad_log.txt
"""

import sys
import json
import requests
import os

BASE_URL = "http://127.0.0.1:8000"
LOG_FILE = r"C:\Users\jdwil\Documents\Projects\GTC 2026 Golden Ticket\intelicad_log.txt"

def show_recent_log():
    """Show the last 30 lines of the Fusion add-in log"""
    if os.path.exists(LOG_FILE):
        print(f"\n📄 Recent Fusion Add-In Activity (last 30 lines):")
        print("="*80)
        try:
            with open(LOG_FILE, 'r') as f:
                lines = f.readlines()
            for line in lines[-30:]:
                print(f"   {line.rstrip()}")
            print("="*80 + "\n")
        except Exception as e:
            print(f"   ⚠️  Could not read log: {e}\n")
    else:
        print(f"\n⚠️  Log file not found at: {LOG_FILE}")
        print(f"   Make sure the Fusion add-in is running!\n")

if len(sys.argv) < 2:
    print("Usage: python inspect_job.py [job_id]")
    print("\nOr run without args to see all jobs:")
    
    # Show recent log activity
    show_recent_log()
    
    # Show available jobs
    try:
        response = requests.get(f"{BASE_URL}/poll-jobs/")
        data = response.json()
    
        print("\n📋 All Jobs:")
        print("="*80)
        all_jobs = {**data.get('awaiting_analysis', {}), **data.get('ready_for_execution', {})}
        for job_id, info in all_jobs.items():
            print(f"\n{job_id[:16]}...")
            print(f"  Command: {info.get('text_command')}")
            print(f"  Status: {info.get('status', info.get('phase'))}")
    except requests.exceptions.ConnectionError:
        print("❌ Backend not running")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    sys.exit(0)

job_id = sys.argv[1]

print(f"\n{'='*80}")
print(f"🔍 Inspecting Job: {job_id}")
print(f"{'='*80}\n")

try:
    response = requests.get(f"{BASE_URL}/job-status/{job_id}")
    job = response.json()
    
    print(f"📌 Command: {job.get('text_command')}")
    print(f"📊 Status: {job.get('status')}")
    print(f"⏱️  Phase: {job.get('phase')}\n")
    
    # Design Intent
    intent = job.get('design_intent', {})
    if intent:
        print(f"🎯 Design Intent:")
        print(f"   Goal: {intent.get('design_intent', {}).get('primary_goal')}")
        print(f"   Strategy: {intent.get('modification_strategy', {}).get('approach')}\n")
    
    # Model Analysis
    analysis = job.get('model_analysis')
    if analysis:
        print(f"📐 Model Analysis:")
        print(f"   Mass: {analysis.get('current_mass')}g")
        print(f"   Volume: {analysis.get('volume')}cm³")
        print(f"   Material: {analysis.get('material')}\n")
    
    # Final Operations (the ones that were executed)
    final_ops = job.get('final_operations', {})
    if final_ops and final_ops.get('operations'):
        ops = final_ops['operations']
        print(f"⚙️  Operations Generated ({len(ops)}):")
        print(f"{'='*80}")
        for i, op in enumerate(ops, 1):
            print(f"\n[{i}] {op.get('type').upper()}")
            print(f"    ID: {op.get('id')}")
            print(f"    Parameters:")
            for k, v in op.get('params', {}).items():
                print(f"      - {k}: {v}")
            print(f"    Reasoning: {op.get('reasoning', 'N/A')[:100]}")
            if op.get('expected_results'):
                print(f"    Expected: {op.get('expected_results')}")
    else:
        print(f"⚠️  No operations found in final_operations")
        
        # Check preliminary operations
        prelim = job.get('preliminary_operations', {})
        if prelim and prelim.get('operations'):
            print(f"\n📝 Preliminary Operations (before refinement): {len(prelim['operations'])}")
    
    print(f"\n{'='*80}")
    
    # Show recent log activity for this job
    print(f"\n📄 Fusion Add-In Log (filtering for {job_id[:8]}):")
    print("="*80)
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r') as f:
                lines = f.readlines()
            
            # Show lines related to this job
            relevant_lines = [l for l in lines if job_id[:8] in l or 'EXECUTION' in l or 'ANALYSIS' in l]
            if relevant_lines:
                for line in relevant_lines[-20:]:  # Last 20 relevant lines
                    print(f"   {line.rstrip()}")
            else:
                print(f"   No log entries found for this job")
                print(f"\n   Last 10 lines of log:")
                for line in lines[-10:]:
                    print(f"   {line.rstrip()}")
        except Exception as e:
            print(f"   ⚠️  Could not read log: {e}")
    else:
        print(f"   ⚠️  Log file not found: {LOG_FILE}")
    print("="*80)
    
except requests.exceptions.ConnectionError:
    print("❌ Backend not running. Start it with:")
    print("   uvicorn fastUpload:app --reload")
except Exception as e:
    print(f"❌ Error: {e}")