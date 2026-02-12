"""
InteliCAD Local Simulator
Mimics what the Fusion 360 add-in will do, without needing Fusion open.
Use this to test the full pipeline end-to-end.

Run this alongside your backend server:
    python simulate_fusion.py
"""

import requests
import json
import time
import os
import shutil

BASE_URL = "http://127.0.0.1:8000"
POLL_INTERVAL = 5  # seconds

print("=" * 80)
print("🔧 InteliCAD Fusion 360 Simulator")
print("   Mimics the Fusion 360 add-in for testing")
print(f"   Polling {BASE_URL} every {POLL_INTERVAL} seconds...")
print("=" * 80)


def simulate_model_analysis(input_file_path):
    """
    Simulate Fusion 360 analyzing the model.
    In real add-in, this extracts actual properties from the .f3d file.
    """
    # Get actual file size as a rough proxy for complexity
    file_size = os.path.getsize(input_file_path) if os.path.exists(input_file_path) else 0

    # Simulated analysis data (real add-in would extract these from Fusion)
    return {
        "current_mass": 150.5,
        "volume": 125.3,
        "bounding_box": {"x": 100.0, "y": 50.0, "z": 30.0},
        "bodies_count": 1,
        "components_count": 0,
        "can_shell": True,
        "features": {
            "extrudes": 3,
            "revolves": 0,
            "holes": 2,
            "fillets": 1,
            "chamfers": 0,
            "shells": 0,
            "patterns": 0
        },
        "material": "PLA",
        "surface_area": 280.5,
        "file_size_bytes": file_size
    }


def simulate_execute_operations(input_file_path, operations, job_id):
    """
    Simulate executing CAD operations.
    In real add-in, this runs actual Fusion 360 API calls.
    For now, copies the input file as output to prove the pipeline works.
    """
    output_dir = f"jobs/{job_id}"
    os.makedirs(output_dir, exist_ok=True)
    output_path = f"{output_dir}/output.f3d"

    print(f"\n  Simulating {len(operations)} operations:")

    for i, op in enumerate(operations, 1):
        op_type = op.get('type', 'unknown')
        params = op.get('params', {})
        reasoning = op.get('reasoning', 'N/A')

        print(f"\n  [{i}/{len(operations)}] {op_type}")
        print(f"    Reasoning: {reasoning[:80]}...")
        print(f"    Params: {json.dumps(params, indent=4)[:200]}")

        # Simulate processing time
        time.sleep(0.5)
        print(f"    ✓ Simulated successfully")

    # Copy input file as output (real add-in would save modified file)
    if os.path.exists(input_file_path):
        shutil.copy2(input_file_path, output_path)
        print(f"\n  ✓ Output file created: {output_path}")
        print(f"    Size: {os.path.getsize(output_path):,} bytes")
    else:
        # Create a dummy output file if input doesn't exist
        with open(output_path, 'wb') as f:
            f.write(b"SIMULATED_F3D_OUTPUT_" + job_id.encode())
        print(f"\n  ⚠️  Input file not found, created placeholder output")

    return output_path


def process_analysis_job(job_id, job_info):
    """Handle a job that needs model analysis"""
    print(f"\n{'='*80}")
    print(f"📊 ANALYZING JOB: {job_id}")
    print(f"   Command: '{job_info.get('text_command')}'")
    print(f"{'='*80}")

    input_file = job_info.get('input_file')
    print(f"\n  Input file: {input_file}")

    # Simulate model analysis
    print("  🔍 Simulating model analysis...")
    analysis = simulate_model_analysis(input_file)

    print(f"  ✓ Analysis results:")
    print(f"    Mass:    {analysis['current_mass']}g")
    print(f"    Volume:  {analysis['volume']}cm³")
    print(f"    Box:     {analysis['bounding_box']['x']} x "
          f"{analysis['bounding_box']['y']} x "
          f"{analysis['bounding_box']['z']} mm")
    print(f"    Bodies:  {analysis['bodies_count']}")
    print(f"    Shell:   {'Yes' if analysis['can_shell'] else 'No'}")

    # Submit analysis to backend
    print("\n  📤 Submitting analysis to backend...")
    response = requests.post(
        f"{BASE_URL}/jobs/{job_id}/analysis",
        json=analysis
    )

    if response.status_code == 200:
        result = response.json()
        ops = result.get('operations', {}).get('operations', [])
        print(f"  ✓ Backend refined operations: {len(ops)} operations ready")
    else:
        print(f"  ✗ Failed to submit analysis: {response.status_code}")
        print(f"    {response.text}")


def process_execution_job(job_id, job_info):
    """Handle a job that's ready for execution"""
    print(f"\n{'='*80}")
    print(f"⚙️  EXECUTING JOB: {job_id}")
    print(f"   Command: '{job_info.get('text_command')}'")
    print(f"{'='*80}")

    input_file = job_info.get('input_file')
    final_operations = job_info.get('final_operations', {})
    operations = final_operations.get('operations', [])

    print(f"\n  Input file: {input_file}")
    print(f"  Operations: {len(operations)}")

    # Simulate executing operations
    output_path = simulate_execute_operations(input_file, operations, job_id)

    # Upload result back to backend
    print(f"\n  📤 Uploading result to backend...")
    with open(output_path, 'rb') as f:
        response = requests.post(
            f"{BASE_URL}/complete-job/{job_id}",
            files={"file": ("output.f3d", f, "application/octet-stream")}
        )

    if response.status_code == 200:
        print(f"  ✓ Job completed and uploaded!")
        print(f"  📥 User can now download at: {BASE_URL}/download/{job_id}")
    else:
        print(f"  ✗ Failed to upload result: {response.status_code}")
        print(f"    {response.text}")


# ============================================================================
# MAIN POLLING LOOP
# ============================================================================

analyzed_jobs = set()   # Jobs that have been through analysis
executed_jobs = set()   # Jobs that have been executed

while True:
    try:
        response = requests.get(f"{BASE_URL}/poll-jobs/", timeout=10)

        if response.status_code != 200:
            print(f"⚠️  Poll failed: {response.status_code}")
            time.sleep(POLL_INTERVAL)
            continue

        data = response.json()
        awaiting = data.get('awaiting_analysis', {})
        ready = data.get('ready_for_execution', {})

        total = len(awaiting) + len(ready)
        if total > 0:
            print(f"\n📬 Found {total} job(s): "
                  f"{len(awaiting)} need analysis, "
                  f"{len(ready)} ready to execute")

        # Process analysis jobs
        for job_id, job_info in awaiting.items():
            if job_id not in analyzed_jobs:
                analyzed_jobs.add(job_id)
                process_analysis_job(job_id, job_info)

        # Process execution jobs (separate tracking from analysis!)
        for job_id, job_info in ready.items():
            if job_id not in executed_jobs:
                executed_jobs.add(job_id)
                process_execution_job(job_id, job_info)

    except requests.exceptions.ConnectionError:
        print(f"⚠️  Cannot connect to backend at {BASE_URL}")
        print(f"   Make sure your server is running: uvicorn fastUpload:app --reload")
    except Exception as e:
        print(f"⚠️  Error: {e}")

    time.sleep(POLL_INTERVAL)