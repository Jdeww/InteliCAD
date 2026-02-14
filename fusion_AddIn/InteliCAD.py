"""
InteliCAD - Fusion 360 Add-In
Main entry point. Polls backend, analyzes models, executes operations.
"""

import adsk.core
import adsk.fusion
import traceback
import threading
import time
import os
import sys
import json

# Add this folder to path so we can import sibling modules
_dir = os.path.dirname(os.path.realpath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

# Don't import the modules here - do it inside run() so we can catch errors

# ============================================================================
BACKEND_URL = "http://127.0.0.1:8000"
POLL_INTERVAL = 10  # seconds
# Log file in the repository folder where backend runs
LOG_FILE = r"C:\Users\jdwil\Documents\Projects\GTC 2026 Golden Ticket\intelicad_log.txt"
# ============================================================================

app = None
ui = None
_stop_event = threading.Event()
_thread = None
_analyzed = set()
_executed = set()

# Will be set after imports succeed
APIClient = None
ModelAnalyzer = None
OperationExecutor = None


def _log(message):
    """Write to both log file and try to print"""
    timestamp = time.strftime("%H:%M:%S")
    full_msg = f"[{timestamp}] {message}"
    
    # Write to log file and FORCE flush
    
    with open(LOG_FILE, "a") as f:
        f.write(full_msg + "\n")
        f.flush()  # Force write immediately
        os.fsync(f.fileno())  # Force OS to write to disk
    
    # Also try print (may not show in UI but worth trying)
    print(full_msg)


def run(context):
    global app, ui, _thread, _stop_event
    global APIClient, ModelAnalyzer, OperationExecutor  # Import these globally
    
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        
        # Create log directory if it doesn't exist
        try:
            log_dir = os.path.dirname(LOG_FILE)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            # Create log file
            with open(LOG_FILE, "w") as f:
                f.write(f"InteliCAD Log Started: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*70 + "\n\n")
            _log("V Log file created")
        except Exception as e:
            ui.messageBox(f"Failed to create log file:\n{e}\n\nTried: {LOG_FILE}")
            return
        
        # Test imports immediately
        try:
            _log("Testing imports...")
            from api_client import APIClient as AC
            from model_analyzer import ModelAnalyzer as MA
            from operation_executor import OperationExecutor as OE
            APIClient = AC
            ModelAnalyzer = MA
            OperationExecutor = OE
            _log("V All modules imported successfully")
        except Exception as e:
            _log(f"X Import failed: {e}")
            _log(f"   Traceback: {traceback.format_exc()}")
            ui.messageBox(f"Import error - check log file:\n{LOG_FILE}")
            return
        
        # Create and start thread
        try:
            _log("Creating polling thread...")
            _stop_event.clear()
            _thread = threading.Thread(target=_poll_loop, daemon=True)
            _log("V Thread created, starting...")
            _thread.start()
            _log("V Thread started!")
            
            # Give thread a moment to run
            time.sleep(0.5)
            
            if _thread.is_alive():
                _log("V Thread is alive and running")
            else:
                _log("X Thread died immediately!")
                
        except Exception as e:
            _log(f"X Failed to start thread: {e}")
            _log(f"   Traceback: {traceback.format_exc()}")
            ui.messageBox(f"Thread startup error - check log:\n{LOG_FILE}")
            return
        
        ui.messageBox(
            "InteliCAD started!\n\n"
            f"Polling {BACKEND_URL} every {POLL_INTERVAL}s\n\n"
            f"Log file: {LOG_FILE}\n\n"
            "Watch the log file to see activity!\n"
            "(It updates in real-time)"
        )
        
    except Exception as e:
        error_msg = f"Failed to start:\n{traceback.format_exc()}"
        try:
            _log(f"X FATAL startup error: {e}")
            _log(f"   {error_msg}")
        except:
            pass
        if ui:
            ui.messageBox(error_msg)


def stop(context):
    global _stop_event, _thread
    try:
        _stop_event.set()
        if _thread:
            _thread.join(timeout=5)
        if ui:
            ui.messageBox("InteliCAD stopped.")
    except:
        pass


def _poll_loop():
    """Main polling loop - runs in background thread"""
    try:
        _log("Starting polling loop...")
        
        # Test 1: Can we create the API client?
        try:
            client = APIClient(BACKEND_URL)
            _log(f"V API client created for {BACKEND_URL}")
        except Exception as e:
            _log(f"X Failed to create API client: {e}")
            _log(f"   Traceback: {traceback.format_exc()}")
            return
        
        # Test 2: Can we make a single poll request?
        try:
            _log("Testing initial poll request...")
            data = client.poll_jobs()
            _log(f"V Poll successful, got: {data.keys()}")
        except Exception as e:
            _log(f"X Initial poll failed: {e}")
            _log(f"   Traceback: {traceback.format_exc()}")
            return
        
        _log(f"V Polling loop ready - checking every {POLL_INTERVAL}s")
        
        # Main loop with aggressive error catching
        poll_count = 0
        while not _stop_event.is_set():
            try:
                poll_count += 1
                _log(f"\n[Poll #{poll_count}] Checking for jobs...")
                
                data = client.poll_jobs()
                
                if "error" in data:
                    _log(f"Poll returned error: {data['error']}")
                    time.sleep(POLL_INTERVAL)
                    continue

                awaiting = data.get("awaiting_analysis", {})
                ready    = data.get("ready_for_execution", {})
                
                if awaiting or ready:
                    _log(f"Found {len(awaiting)} awaiting analysis, {len(ready)} ready to execute")

                for job_id, info in awaiting.items():
                    if job_id not in _analyzed:
                        _analyzed.add(job_id)
                        _log(f"Scheduling analysis for {job_id[:8]}...")
                        try:
                            _run_on_main(lambda j=job_id, i=info: _do_analysis(j, i, client))
                        except Exception as e:
                            _log(f"X Failed to schedule analysis: {e}")

                for job_id, info in ready.items():
                    if job_id not in _executed:
                        _executed.add(job_id)
                        _log(f"Scheduling execution for {job_id[:8]}...")
                        try:
                            _run_on_main(lambda j=job_id, i=info: _do_execution(j, i, client))
                        except Exception as e:
                            _log(f"X Failed to schedule execution: {e}")

            except Exception as e:
                _log(f"X Poll loop error: {e}")
                _log(f"   Traceback: {traceback.format_exc()}")

            time.sleep(POLL_INTERVAL)
            
    except Exception as e:
        _log(f"X FATAL: Polling thread crashed: {e}")
        _log(f"   Traceback: {traceback.format_exc()}")
        _log("   Thread is now stopped. Restart the add-in to try again.")


def _run_on_main(fn):
    """
    Fusion 360 API calls should happen on the main thread.
    This is a simplified version that runs directly.
    Note: May fail if Fusion is busy or in a command.
    """
    try:
        _log("Executing on background thread (may have API limitations)...")
        fn()
        _log("Execution completed")
    except Exception as e:
        _log(f"X Error executing: {e}")
        _log(f"   Traceback: {traceback.format_exc()}")


# ============================================================================
# ANALYSIS PHASE
# ============================================================================

def _do_analysis(job_id, job_info, client):
    _log(f"\n{'='*70}")
    _log(f"ANALYSIS: {job_id[:8]}...")
    _log(f"   Command: '{job_info.get('text_command')}'")
    _log(f"{'='*70}")

    # Use the currently active design in Fusion
    try:
        doc = app.activeDocument
        if not doc:
            _log("X No active document in Fusion 360")
            _log("   Please open a .f3d file first!")
            return
        
        design = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
        if not design:
            _log("X Active document is not a Fusion design")
            return
        
        _log(f"V Using active design: {doc.name}")
    except Exception as e:
        _log(f"X Could not get active design: {e}")
        return

    # Analyze
    _log("Analyzing model...")
    analyzer = ModelAnalyzer(design)
    analysis = analyzer.analyze()

    _log(f"   Mass:    {analysis['current_mass']}g")
    _log(f"   Volume:  {analysis['volume']}cm³")
    _log(f"   Bodies:  {analysis['bodies_count']}")
    _log(f"   Material:{analysis['material']}")

    # Send to backend
    _log("Sending analysis to backend...")
    result = client.submit_analysis(job_id, analysis)
    ops = result.get("operations", {}).get("operations", [])
    _log(f"V {len(ops)} refined operations received from Nemotron")


# ============================================================================
# EXECUTION PHASE
# ============================================================================

def _do_execution(job_id, job_info, client):
    _log(f"\n{'='*70}")
    _log(f"EXECUTION: {job_id[:8]}...")
    _log(f"   Command: '{job_info.get('text_command')}'")
    _log(f"   CODE VERSION: 2025-02-14-v3-DETAILED-LOGGING")  # Version marker
    _log(f"{'='*70}")

    final_ops  = job_info.get("final_operations", {})
    operations = final_ops.get("operations", [])

    if not operations:
        _log("No operations to execute")
        return

    # Use the currently active design
    try:
        doc = app.activeDocument
        if not doc:
            _log("X No active document in Fusion 360")
            return
        
        design = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
        if not design:
            _log("X Active document is not a Fusion design")
            return
        
        _log(f"V Using active design: {doc.name}")
    except Exception as e:
        _log(f"X Could not get active design: {e}")
        return

    # Execute each operation
    executor = OperationExecutor(design, app)
    success_count = 0
    
    _log(f"\nDEBUG: About to loop through {len(operations)} operations")
    _log(f"   Operations list type: {type(operations)}")
    _log(f"   Operations content: {operations[:1] if operations else 'EMPTY'}")

    execution_results = []  # NEW: Track for Phase 3
    
    for i, op in enumerate(operations, 1):
        _log(f"\n  [{i}/{len(operations)}] {op.get('type', 'unknown')}")
        _log(f"    Reasoning: {op.get('reasoning', 'N/A')[:70]}")
        _log(f"    Params: {json.dumps(op.get('params', {}))[:100]}")
        
        # Execute and log result
        result = executor.execute(op)
        
        # NEW: Track for Phase 3
        execution_results.append({
            "operation": op,
            "success": result["success"],
            "error": result.get("error", "") if not result["success"] else "",
            "message": result.get("message", "") if result["success"] else ""
        })
        
        if result["success"]:
            _log(f"    V SUCCESS {result.get('message', '')}")
            success_count += 1
        else:
            _log(f"    X FAILED {result.get('error', 'Unknown error')}")

    # Execution complete - show summary
    _log(f"\nEXECUTION SUMMARY:")
    _log(f"   Total operations: {len(operations)}")
    _log(f"   Succeeded: {success_count}")
    _log(f"   Failed: {len(operations) - success_count}")
    
    # NEW: Phase 3 - Retry failed operations
    failed_count = len(operations) - success_count
    retry_ops = []
    if failed_count > 0:
        _log(f"\n>> PHASE 3: Requesting alternatives for {failed_count} failed operation(s)...")
        try:
            retry_result = client.retry_failed_operations(job_id, execution_results)
            retry_ops = retry_result.get("retry_operations", [])
            
            if retry_ops:
                _log(f"   V Received {len(retry_ops)} alternative operation(s)")
                _log(f"\n>> EXECUTING RETRY OPERATIONS:")
                
                retry_success = 0
                for i, retry_op in enumerate(retry_ops, 1):
                    _log(f"\n  [Retry {i}/{len(retry_ops)}] {retry_op.get('type')}")
                    _log(f"    Reasoning: {retry_op.get('reasoning', 'N/A')[:70]}")
                    _log(f"    Params: {json.dumps(retry_op.get('params', {}))[:100]}")
                    
                    retry_exec_result = executor.execute(retry_op)
                    
                    if retry_exec_result["success"]:
                        _log(f"    V SUCCESS {retry_exec_result.get('message', 'Done')}")
                        retry_success += 1
                    else:
                        _log(f"    X FAILED {retry_exec_result.get('error', 'Unknown')}")
                
                _log(f"\n>> RETRY SUMMARY: {retry_success}/{len(retry_ops)} succeeded")
                success_count += retry_success
            else:
                _log(f"   ! No alternative operations generated")
        except Exception as e:
            _log(f"   X Phase 3 error: {e}")

    _log(f"\n>> FINAL SUMMARY:")
    _log(f"   Total attempted: {len(operations) + len(retry_ops)}")
    _log(f"   Total succeeded: {success_count}")
    _log(f"   Total operations: {len(operations)}")
    _log(f"   Succeeded: {success_count}")
    _log(f"   Failed: {len(operations) - success_count}")

    # Save output to the job folder
    _log(f"\nSaving modified file...")
    input_path = job_info.get("input_file")
    output_path = _save_f3d(design, job_id, input_path)

    if not output_path:
        _log("X Failed to save output file")
        return

    _log(f"   V Saved: {output_path}")

    # Upload to backend
    _log("Uploading to backend...")
    result = client.complete_job(job_id, output_path)

    if result.get("status") == "success":
        _log(f"\nJob {job_id[:8]}... COMPLETE!")
        _log(f"   {success_count}/{len(operations)} operations succeeded")
        _log(f"   Download: {BACKEND_URL}/download/{job_id}")
    else:
        _log(f"X Upload failed: {result}")


# ============================================================================
# FILE HELPERS
# ============================================================================

def _open_f3d(file_path):
    """Open a .f3d file in Fusion 360 and return the Design object"""
    try:
        if not file_path or not os.path.exists(file_path):
            _log(f"   X File not found: {file_path}")
            return None

        import_mgr = app.importManager
        options = import_mgr.createFusionArchiveImportOptions(file_path)
        import_mgr.importToNewDocument(options)

        doc = app.activeDocument
        design = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
        return design

    except Exception as e:
        _log(f"   X Error opening file: {e}")
        return None


def _save_f3d(design, job_id, input_path):
    """Save the current design as .f3d and return the output path"""
    try:
        _log(f"   Saving to job folder...")
        _log(f"   Input path: {input_path}")
        
        # Save next to the input file
        output_dir = os.path.dirname(input_path)
        output_path = os.path.join(output_dir, "output.f3d")
        
        _log(f"   Output path: {output_path}")
        _log(f"   Output dir exists: {os.path.exists(output_dir)}")
        
        if not os.path.exists(output_dir):
            _log(f"   Creating output directory...")
            os.makedirs(output_dir, exist_ok=True)

        export_mgr = design.exportManager
        _log(f"   Creating export options...")
        options = export_mgr.createFusionArchiveExportOptions(output_path)
        _log(f"   Executing export...")
        export_mgr.execute(options)
        
        _log(f"   Export complete. File size: {os.path.getsize(output_path)} bytes")
        return output_path

    except Exception as e:
        _log(f"   X Error saving file: {e}")
        _log(f"   Traceback: {traceback.format_exc()}")
        return None