"""
InteliCAD Job Verifier
Checks completed jobs and shows before/after comparisons to verify changes were made.

Run after jobs complete:
    python verify_job.py                    # Check all completed jobs
    python verify_job.py <job_id>           # Check specific job
"""

import requests
import json
import sys
import os

BASE_URL = "http://127.0.0.1:8000"


def format_bytes(size):
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} MB"


def check_file_exists(file_path):
    """Check if an output file exists and get its properties"""
    if not file_path:
        return {"exists": False, "reason": "No file path recorded"}

    if not os.path.exists(file_path):
        return {"exists": False, "reason": f"File not found at: {file_path}"}

    size = os.path.getsize(file_path)
    modified = os.path.getmtime(file_path)

    import datetime
    modified_str = datetime.datetime.fromtimestamp(modified).strftime('%Y-%m-%d %H:%M:%S')

    return {
        "exists": True,
        "path": file_path,
        "size_bytes": size,
        "size_human": format_bytes(size),
        "modified": modified_str
    }


def compare_files(input_path, output_path):
    """Compare input and output files to detect if changes were made"""
    results = {
        "files_differ": False,
        "size_change_bytes": 0,
        "size_change_percent": 0,
        "verdict": "unknown"
    }

    if not os.path.exists(input_path) or not os.path.exists(output_path):
        results["verdict"] = "cannot_compare"
        return results

    input_size = os.path.getsize(input_path)
    output_size = os.path.getsize(output_path)

    size_diff = output_size - input_size
    size_change_pct = (size_diff / input_size * 100) if input_size > 0 else 0

    results["input_size"] = input_size
    results["output_size"] = output_size
    results["size_change_bytes"] = size_diff
    results["size_change_percent"] = round(size_change_pct, 1)
    results["files_differ"] = input_size != output_size

    # Read first bytes to check if content differs
    with open(input_path, 'rb') as f:
        input_start = f.read(256)
    with open(output_path, 'rb') as f:
        output_start = f.read(256)

    content_differs = input_start != output_start

    if content_differs and size_diff != 0:
        results["files_differ"] = True
        if size_diff < 0:
            results["verdict"] = "✅ File is SMALLER - material was likely removed"
        else:
            results["verdict"] = "✅ File is LARGER - geometry was likely added"
    elif content_differs:
        results["files_differ"] = True
        results["verdict"] = "⚠️  Content differs but same size - metadata may have changed"
    else:
        results["files_differ"] = False
        results["verdict"] = "❌ Files are IDENTICAL - no changes were made (simulator mode)"

    return results


def display_job_report(job_id, job_data):
    """Display a detailed report for a single job"""
    print(f"\n{'='*80}")
    print(f"JOB REPORT: {job_id}")
    print(f"{'='*80}")

    # Basic info
    print(f"\n📋 COMMAND:")
    print(f"   '{job_data.get('text_command', 'N/A')}'")

    print(f"\n📊 STATUS: {job_data.get('status', 'unknown').upper()}")

    # Design intent
    design_intent = job_data.get('design_intent', {})
    if design_intent and isinstance(design_intent, dict):
        di = design_intent.get('design_intent', {})
        strategy = design_intent.get('modification_strategy', {})

        print(f"\n🧠 AI PLAN:")
        print(f"   Goal:     {di.get('primary_goal', 'N/A')}")
        print(f"   Strategy: {strategy.get('approach', 'N/A')}")

        targets = di.get('quantitative_targets', {})
        if targets:
            print(f"   Targets:")
            for k, v in targets.items():
                print(f"     - {k}: {v}%")

    # Model analysis
    analysis = job_data.get('model_analysis', {})
    if analysis and isinstance(analysis, dict):
        print(f"\n📐 MODEL ANALYSIS (Before):")
        print(f"   Mass:    {analysis.get('current_mass', 'N/A')}g")
        print(f"   Volume:  {analysis.get('volume', 'N/A')}cm³")
        box = analysis.get('bounding_box', {})
        if box:
            print(f"   Size:    {box.get('x')} x {box.get('y')} x {box.get('z')} mm")
        print(f"   Bodies:  {analysis.get('bodies_count', 'N/A')}")
        print(f"   Material:{analysis.get('material', 'N/A')}")

    # Operations that were executed
    final_ops = job_data.get('final_operations', {})
    if final_ops and isinstance(final_ops, dict):
        ops = final_ops.get('operations', [])
        if ops:
            print(f"\n⚙️  OPERATIONS EXECUTED ({len(ops)}):")
            for i, op in enumerate(ops, 1):
                op_type = op.get('type', 'unknown')
                reasoning = op.get('reasoning', 'N/A')
                expected = op.get('expected_results', {})
                print(f"\n   [{i}] {op_type}")
                print(f"       {reasoning[:80]}")
                if expected:
                    for k, v in expected.items():
                        print(f"       Expected {k}: {v}")

    # File verification
    input_file = job_data.get('input_file')
    output_file = job_data.get('output_file')

    print(f"\n📁 FILE VERIFICATION:")

    input_check = check_file_exists(input_file)
    if input_check['exists']:
        print(f"   Input:  ✅ {input_check['path']}")
        print(f"           Size: {input_check['size_human']}")
    else:
        print(f"   Input:  ❌ {input_check['reason']}")

    output_check = check_file_exists(output_file)
    if output_check['exists']:
        print(f"   Output: ✅ {output_check['path']}")
        print(f"           Size: {output_check['size_human']}")
        print(f"           Modified: {output_check['modified']}")
    else:
        print(f"   Output: ❌ {output_check['reason']}")

    # Compare files
    if input_check['exists'] and output_check['exists']:
        comparison = compare_files(input_file, output_file)
        print(f"\n🔍 CHANGE DETECTION:")
        print(f"   Input size:  {format_bytes(comparison.get('input_size', 0))}")
        print(f"   Output size: {format_bytes(comparison.get('output_size', 0))}")
        size_change = comparison.get('size_change_bytes', 0)
        size_pct = comparison.get('size_change_percent', 0)
        sign = '+' if size_change >= 0 else ''
        print(f"   Change:      {sign}{format_bytes(abs(size_change))} ({sign}{size_pct}%)")
        print(f"\n   Verdict: {comparison.get('verdict', 'unknown')}")

    # What this means for real Fusion integration
    print(f"\n💡 NEXT STEPS:")
    if job_data.get('status') == 'completed':
        if output_check['exists']:
            if not compare_files(input_file, output_file).get('files_differ'):
                print("   ⚠️  Currently running in SIMULATOR mode.")
                print("   ⚠️  The output file is a copy of the input.")
                print("   👉 To see REAL changes:")
                print("      1. Install the Fusion 360 add-in")
                print("      2. Have Fusion 360 open with your model")
                print("      3. The add-in will execute real operations")
                print("      4. Output file will show actual geometry changes")
            else:
                print("   ✅ Changes detected in output file!")
                print("   👉 Open the output .f3d file in Fusion 360 to inspect changes")
        else:
            print("   ❌ Output file missing - check server logs")
    else:
        print(f"   Job status is '{job_data.get('status')}' - not yet complete")

    print(f"\n{'='*80}\n")


def main():
    # Get specific job ID from command line, or check all
    specific_job_id = sys.argv[1] if len(sys.argv) > 1 else None

    print("=" * 80)
    print("🔍 InteliCAD Job Verifier")
    print("=" * 80)

    if specific_job_id:
        # Check specific job
        response = requests.get(f"{BASE_URL}/job-status/{specific_job_id}")
        if response.status_code == 200:
            job_data = response.json()
            if 'error' in job_data:
                print(f"\n❌ Job not found: {specific_job_id}")
            else:
                display_job_report(specific_job_id, job_data)
        else:
            print(f"❌ Failed to get job: {response.status_code}")
    else:
        # Check all jobs in the jobs/ directory
        jobs_dir = "jobs"
        if not os.path.exists(jobs_dir):
            print("\n⚠️  No jobs directory found. Submit some jobs first!")
            return

        job_dirs = [d for d in os.listdir(jobs_dir)
                    if os.path.isdir(os.path.join(jobs_dir, d))]

        if not job_dirs:
            print("\n⚠️  No jobs found. Submit some jobs first!")
            return

        print(f"\nFound {len(job_dirs)} job(s). Checking status...\n")

        completed = 0
        pending = 0
        failed = 0

        for job_id in job_dirs:
            response = requests.get(f"{BASE_URL}/job-status/{job_id}")
            if response.status_code == 200:
                job_data = response.json()
                if 'error' not in job_data:
                    status = job_data.get('status', 'unknown')
                    if status == 'completed':
                        completed += 1
                        display_job_report(job_id, job_data)
                    elif status in ['pending', 'pending_analysis']:
                        pending += 1
                        print(f"⏳ {job_id[:8]}... - {status}")
                    elif status == 'failed':
                        failed += 1
                        print(f"❌ {job_id[:8]}... - FAILED: {job_data.get('error', 'unknown')}")

        print(f"\n{'='*80}")
        print(f"SUMMARY: {completed} completed, {pending} pending, {failed} failed")
        print(f"{'='*80}\n")


if __name__ == "__main__":
    main()