"""
InteliCAD - AI-Powered CAD Modification Add-In for Fusion 360

This add-in connects to your backend server, polls for CAD modification jobs,
analyzes models, executes AI-generated operations, and returns results.
"""

import adsk.core
import adsk.fusion
import traceback
import json
import threading
import time
import os
import sys

# Add the parent directory to the path to import our modules
script_dir = os.path.dirname(os.path.realpath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Import our custom modules
from .api_client import APIClient
from .model_analyzer import ModelAnalyzer
from .operation_executor import OperationExecutor
from .ui_manager import UIManager

# Global variables
app = None
ui = None
handlers = []
stop_event = threading.Event()
polling_thread = None

# Configuration
BACKEND_URL = "http://127.0.0.1:8000"  # Your FastAPI backend
POLL_INTERVAL = 10  # seconds


def run(context):
    """
    Entry point when the add-in starts
    """
    try:
        global app, ui
        app = adsk.core.Application.get()
        ui = app.userInterface
        
        # Create UI
        ui_manager = UIManager(ui)
        ui_manager.create_panel()
        
        # Start polling thread
        start_polling()
        
        ui.messageBox('InteliCAD Add-In Started!\n\nPolling backend for jobs...')
        
    except:
        if ui:
            ui.messageBox('Failed to start:\n{}'.format(traceback.format_exc()))


def stop(context):
    """
    Called when the add-in is stopped
    """
    try:
        global stop_event, polling_thread
        
        # Stop the polling thread
        stop_event.set()
        if polling_thread:
            polling_thread.join(timeout=5)
        
        # Clean up UI
        ui_manager = UIManager(ui)
        ui_manager.cleanup()
        
        if ui:
            ui.messageBox('InteliCAD Add-In Stopped')
            
    except:
        if ui:
            ui.messageBox('Failed to stop:\n{}'.format(traceback.format_exc()))


def start_polling():
    """
    Start the background thread that polls for jobs
    """
    global polling_thread, stop_event
    
    stop_event.clear()
    polling_thread = threading.Thread(target=poll_for_jobs, daemon=True)
    polling_thread.start()


def poll_for_jobs():
    """
    Background thread function that polls the backend for new jobs
    """
    global app, ui, stop_event
    
    api_client = APIClient(BACKEND_URL)
    
    while not stop_event.is_set():
        try:
            # Poll for jobs
            jobs_data = api_client.poll_jobs()
            
            # Process jobs awaiting analysis
            awaiting_analysis = jobs_data.get('awaiting_analysis', {})
            for job_id, job_info in awaiting_analysis.items():
                process_analysis_job(job_id, job_info, api_client)
            
            # Process jobs ready for execution
            ready_for_execution = jobs_data.get('ready_for_execution', {})
            for job_id, job_info in ready_for_execution.items():
                process_execution_job(job_id, job_info, api_client)
            
        except Exception as e:
            print(f"Polling error: {e}")
            print(traceback.format_exc())
        
        # Wait before next poll
        time.sleep(POLL_INTERVAL)


def process_analysis_job(job_id, job_info, api_client):
    """
    Process a job that needs model analysis
    """
    try:
        print(f"\n{'='*80}")
        print(f"📊 ANALYZING JOB: {job_id}")
        print(f"Command: {job_info.get('text_command')}")
        print(f"{'='*80}\n")
        
        # Download the .f3d file
        input_file = job_info.get('input_file')
        local_path = api_client.download_file(input_file)
        
        # Open the file in Fusion 360
        design = open_f3d_file(local_path)
        if not design:
            print("Failed to open .f3d file")
            return
        
        # Analyze the model
        analyzer = ModelAnalyzer(design)
        analysis_data = analyzer.analyze()
        
        print(f"✓ Analysis complete:")
        print(f"  Mass: {analysis_data.get('current_mass')}g")
        print(f"  Volume: {analysis_data.get('volume')}cm³")
        print(f"  Bodies: {analysis_data.get('bodies_count')}")
        
        # Send analysis back to backend
        response = api_client.submit_analysis(job_id, analysis_data)
        
        print(f"✓ Analysis submitted to backend")
        print(f"  Status: {response.get('status')}")
        
    except Exception as e:
        print(f"Error processing analysis job {job_id}: {e}")
        print(traceback.format_exc())


def process_execution_job(job_id, job_info, api_client):
    """
    Process a job that's ready for operation execution
    """
    try:
        print(f"\n{'='*80}")
        print(f"⚙️  EXECUTING JOB: {job_id}")
        print(f"Command: {job_info.get('text_command')}")
        print(f"{'='*80}\n")
        
        # Download the .f3d file
        input_file = job_info.get('input_file')
        local_path = api_client.download_file(input_file)
        
        # Open the file in Fusion 360
        design = open_f3d_file(local_path)
        if not design:
            print("Failed to open .f3d file")
            return
        
        # Get operations to execute
        operations = job_info.get('final_operations', {}).get('operations', [])
        
        print(f"📋 Executing {len(operations)} operations...")
        
        # Execute operations
        executor = OperationExecutor(design)
        results = []
        
        for i, operation in enumerate(operations, 1):
            print(f"\n  Operation {i}/{len(operations)}: {operation.get('type')}")
            result = executor.execute_operation(operation)
            results.append(result)
            
            if not result.get('success'):
                print(f"  ✗ Failed: {result.get('error')}")
                break
            else:
                print(f"  ✓ Success")
        
        # Save the modified file
        output_path = save_f3d_file(design, job_id)
        
        # Upload result back to backend
        api_client.complete_job(job_id, output_path)
        
        print(f"\n✓ Job {job_id} completed and uploaded")
        
    except Exception as e:
        print(f"Error processing execution job {job_id}: {e}")
        print(traceback.format_exc())


def open_f3d_file(file_path):
    """
    Open a .f3d file in Fusion 360 and return the design
    """
    try:
        global app
        
        # Import the file
        import_manager = app.importManager
        import_options = import_manager.createFusionArchiveImportOptions(file_path)
        import_manager.importToTarget(import_options, app.activeProduct)
        
        # Get the active design
        design = adsk.fusion.Design.cast(app.activeProduct)
        return design
        
    except Exception as e:
        print(f"Error opening file: {e}")
        return None


def save_f3d_file(design, job_id):
    """
    Save the current design as a .f3d file
    """
    try:
        global app
        
        # Create temp directory if it doesn't exist
        temp_dir = os.path.join(os.environ['TEMP'], 'intelicad')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Save path
        output_path = os.path.join(temp_dir, f"{job_id}_output.f3d")
        
        # Export as Fusion Archive
        export_mgr = design.exportManager
        archive_options = export_mgr.createFusionArchiveExportOptions(output_path)
        export_mgr.execute(archive_options)
        
        return output_path
        
    except Exception as e:
        print(f"Error saving file: {e}")
        return None
