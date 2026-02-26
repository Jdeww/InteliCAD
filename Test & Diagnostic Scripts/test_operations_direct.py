"""
Standalone Operation Tester for Fusion 360
Run this as a script directly in Fusion to test operations

Instructions:
1. Open Fusion 360
2. Open a design file
3. Run this as a script (Utilities → Scripts and Add-Ins → Scripts → + → Run)
4. Check the Text Commands window for results
"""

import adsk.core
import adsk.fusion
import traceback
import sys
import os

# Add the InteliCAD folder to path so we can import operation_executor
addin_path = os.path.join(
    os.environ['APPDATA'],
    r'Autodesk\Autodesk Fusion 360\API\AddIns\InteliCAD'
)
if addin_path not in sys.path:
    sys.path.insert(0, addin_path)

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        
        # Get active design
        doc = app.activeDocument
        if not doc:
            ui.messageBox("No active document. Open a design first!")
            return
        
        design = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
        if not design:
            ui.messageBox("Active document is not a Fusion design!")
            return
        
        ui.messageBox(f"Testing operations on: {doc.name}")
        
        # Import the executor
        from operation_executor import OperationExecutor
        
        # Create executor
        executor = OperationExecutor(design, app)
        
        # Test operations one by one
        operations = [
            {
                "type": "shell_body",
                "params": {
                    "wall_thickness": 2.5,
                    "inside_offset": True,
                    "faces_to_remove": ["top_face"]
                }
            },
            {
                "type": "add_ribs",
                "params": {
                    "thickness": 1.5,
                    "height": 10.0,
                    "pattern": "cross_bracing"
                }
            },
            {
                "type": "fillet_all_edges",
                "params": {
                    "radius": 2.0
                }
            }
        ]
        
        results = []
        for i, op in enumerate(operations, 1):
            op_type = op["type"]
            try:
                result = executor.execute(op)
                if result["success"]:
                    status = f"✅ SUCCESS: {result.get('message', 'Done')}"
                else:
                    status = f"❌ FAILED: {result.get('error', 'Unknown')}"
                results.append(f"[{i}] {op_type}\n    {status}")
            except Exception as e:
                results.append(f"[{i}] {op_type}\n    ❌ EXCEPTION: {e}")
        
        # Show results
        message = "OPERATION TEST RESULTS:\n\n" + "\n\n".join(results)
        ui.messageBox(message)
        
    except:
        if ui:
            ui.messageBox(f"ERROR:\n{traceback.format_exc()}")
