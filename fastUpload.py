from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import FileResponse
import shutil
import os
import uuid
from datetime import datetime
import httpx
import json

app = FastAPI()

# Simple in-memory job queue (use database later)
jobs = {}

# ============================================================================
# NVIDIA API CONFIGURATION
# ============================================================================
NVIDIA_API_KEY = ""  # <-- REPLACE THIS!
# ============================================================================

NVIDIA_API_URL = ""


async def call_nemotron(system_prompt: str, user_message: str, max_tokens: int = 3072) -> dict:
    """
    Helper function to call Nemotron API
    """
    if NVIDIA_API_KEY == "nvapi-PASTE_YOUR_KEY_HERE":
        print("⚠️  WARNING: Nvidia API key not set! Using fallback mode.")
        return {
            "error": "Nvidia API key not configured",
            "raw_text": user_message
        }
    
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "nvidia/llama-3.3-nemotron-super-49b-v1.5",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.2,
        "top_p": 0.7,
        "max_tokens": max_tokens
    }
    
    try:
        async with httpx.AsyncClient() as client:
            print(f"🔄 Calling Nvidia Nemotron API...")
            response = await client.post(
                NVIDIA_API_URL,
                headers=headers,
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            print(f"✓ Received response from Nemotron")
            
            # Remove <think> tags if present
            if "<think>" in content and "</think>" in content:
                content = content.split("</think>", 1)[1].strip()
            
            # Strip markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            return json.loads(content)
            
    except Exception as e:
        print(f"❌ Error calling Nemotron API: {e}")
        return {
            "error": str(e),
            "raw_text": user_message
        }


async def phase1_design_intent_analysis(user_command: str) -> dict:
    """
    PHASE 1: Analyze user's high-level design intent
    Convert vague commands into structured design goals
    """
    
    system_prompt = """You are an expert CAD design strategist with deep knowledge of:
- Mechanical engineering and structural analysis
- Design for Manufacturing (DFM) and Design for Assembly (DFA)
- Topology optimization and generative design
- Material science and failure analysis
- Additive manufacturing and 3D printing optimization

Your task is to analyze high-level design intent and create a detailed modification strategy.

## Advanced CAD Operations Available:

### WEIGHT REDUCTION:
- shell_body: Convert solid to hollow shell
  - Params: wall_thickness (mm), faces_to_remove (list), inside_offset (bool)
- lattice_infill: Add internal lattice structures for strength-to-weight
  - Params: cell_type ("gyroid", "cubic", "diamond"), cell_size (mm), density (0-1)
- strategic_holes: Pattern of holes to reduce material
  - Params: hole_diameter (mm), pattern ("hexagonal", "grid", "staggered"), spacing (mm), regions (list)
- topology_optimize: AI-driven material removal based on loads
  - Params: preserve_regions (list), load_cases (list), target_reduction (%)

### STRUCTURAL ENHANCEMENT:
- add_ribs: Internal/external reinforcement ribs
  - Params: thickness (mm), height (mm or "full"), pattern ("parallel", "cross", "radial"), locations (list)
- add_gussets: Corner/joint reinforcement
  - Params: size (mm), fillet_radius (mm), corners (list)
- thicken_walls: Selective wall thickness increase
  - Params: regions (list), additional_thickness (mm)
- add_boss: Reinforcement around holes/mounting points
  - Params: hole_locations (list), outer_diameter (mm), height (mm)

### MATERIAL OPTIMIZATION:
- variable_wall_thickness: Non-uniform wall thickness based on stress
  - Params: min_thickness (mm), max_thickness (mm), stress_based (bool)
- infill_pattern: Internal fill patterns for 3D printing
  - Params: pattern_type ("honeycomb", "gyroid", "triangular"), density (%)

### MANUFACTURING OPTIMIZATION:
- add_draft_angles: Taper for molding/casting
  - Params: angle (degrees), direction, faces (list)
- fillet_all_edges: Round sharp edges
  - Params: radius (mm), edge_selection ("all", "external", "internal")
- split_for_assembly: Break into manufacturable/assemblable parts
  - Params: max_part_size (mm), join_method ("snap_fit", "screws", "adhesive")

### FUNCTIONAL FEATURES:
- add_ventilation: Airflow/cooling holes
  - Params: hole_size (mm), pattern, airflow_direction, regions
- add_drainage: Water drainage features
  - Params: hole_diameter (mm), locations ("bottom", "low_points")
- add_mounting_features: Screw holes, standoffs, brackets
  - Params: feature_type, size, locations, thread_spec

### ANALYSIS OPERATIONS:
- stress_analysis: FEA simulation
  - Params: load_cases (list), constraints (list), safety_factor
- weight_analysis: Mass properties calculation
- printability_check: 3D printing feasibility analysis

## Your Response Format:

You MUST return a JSON object with these fields:

{
  "design_intent": {
    "primary_goal": "reduce_weight | increase_strength | optimize_manufacturing | improve_function",
    "quantitative_targets": {
      "weight_reduction_percent": 30,
      "strength_retention_percent": 85,
      "cost_reduction_percent": 20
    },
    "constraints": ["maintain_mounting_holes", "no_sharp_edges", "max_height_50mm"],
    "use_case": "bracket for 50kg load",
    "material_assumed": "PLA" or "ABS" or "Steel" etc.
  },
  "modification_strategy": {
    "approach": "shell_and_reinforce | lattice_infill | topology_optimization | hole_pattern",
    "reasoning": "Detailed explanation of why this approach fits the goals",
    "risk_factors": ["may_reduce_strength_locally", "requires_support_material"],
    "estimated_iterations": 2
  },
  "analysis_required": {
    "before_modification": ["current_volume", "current_mass", "bounding_box", "feature_count"],
    "during_modification": ["stress_analysis", "weight_tracking"],
    "validation": ["final_mass", "fea_results", "safety_factor"]
  },
  "high_level_plan": [
    {
      "step": 1,
      "operation_category": "weight_reduction",
      "description": "Shell the main body to 3mm walls",
      "expected_outcome": "60-70% weight reduction",
      "potential_issues": ["may_create_weak_points_at_corners"]
    },
    {
      "step": 2,
      "operation_category": "structural_enhancement", 
      "description": "Add cross-bracing ribs for support",
      "expected_outcome": "restore 80-90% of original strength",
      "potential_issues": []
    }
  ],
  "requires_user_clarification": {
    "questions": ["What load will this part experience?", "What's your target weight?"],
    "assumptions_made": ["Assuming vertical load of 10kg", "Assuming 3D printing in PLA"]
  }
}

CRITICAL: Always output valid JSON. Think through the engineering tradeoffs carefully."""

    user_message = f"Design Intent: {user_command}\n\nAnalyze this command and create a detailed modification strategy."
    
    result = await call_nemotron(system_prompt, user_message, max_tokens=3072)
    return result


async def phase2_generate_operations(design_plan: dict, model_analysis: dict = None) -> dict:
    """
    PHASE 2: Convert high-level plan into specific CAD operations
    Uses model analysis data if available
    """
    
    system_prompt = """You are a CAD operation generator. Convert high-level design strategies into specific, 
executable Fusion 360 API operations with precise parameters.

Given a design plan and optional model analysis, generate the exact sequence of CAD operations.

## Response Format:

{
  "operations": [
    {
      "id": "op_001",
      "type": "shell_body",
      "params": {
        "body_name": "Body1",
        "wall_thickness": 3.0,
        "inside_offset": true,
        "faces_to_remove": ["top_face"]
      },
      "reasoning": "Create hollow interior to reduce mass",
      "expected_results": {
        "weight_reduction_percent": 65,
        "new_mass_estimate_grams": 85
      },
      "depends_on": [],
      "rollback_if": "wall_thickness_too_thin"
    },
    {
      "id": "op_002", 
      "type": "add_ribs",
      "params": {
        "thickness": 2.0,
        "height": "full",
        "pattern": "cross_bracing",
        "locations": ["interior_vertical_walls"],
        "fillet_radius": 0.5
      },
      "reasoning": "Reinforce structure after shelling",
      "expected_results": {
        "strength_retention_percent": 85
      },
      "depends_on": ["op_001"],
      "rollback_if": "stress_exceeds_threshold"
    }
  ],
  "validation_steps": [
    {
      "after_operation": "op_001",
      "check": "mass_analysis",
      "criteria": {
        "mass_reduction_min": 50,
        "mass_reduction_max": 70
      }
    },
    {
      "after_operation": "op_002",
      "check": "stress_analysis",
      "criteria": {
        "max_stress_mpa": 15,
        "safety_factor_min": 2.0
      }
    }
  ],
  "fallback_plan": {
    "if_validation_fails": [
      "increase_wall_thickness_by_1mm",
      "add_additional_ribs"
    ]
  }
}

CRITICAL: Be specific with parameters. Use actual numbers, not ranges."""

    if model_analysis:
        user_message = f"""Design Plan:
{json.dumps(design_plan, indent=2)}

Model Analysis:
{json.dumps(model_analysis, indent=2)}

Generate specific CAD operations to execute this plan."""
    else:
        user_message = f"""Design Plan:
{json.dumps(design_plan, indent=2)}

Model analysis not yet available. Generate operations with best-guess parameters.
Mark which parameters should be refined after analysis."""
    
    result = await call_nemotron(system_prompt, user_message, max_tokens=3072)
    return result


@app.post("/submit-job/")
async def submit_job(file: UploadFile, text_command: str = Form(...)):
    """
    Submit a new CAD modification job with complex design intent
    """
    job_id = str(uuid.uuid4())
    
    # Save uploaded file
    upload_dir = f"jobs/{job_id}"
    os.makedirs(upload_dir, exist_ok=True)
    f3d_path = f"{upload_dir}/input.f3d"
    
    with open(f3d_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    print(f"\n{'='*80}")
    print(f"📝 NEW JOB: {job_id}")
    print(f"Command: '{text_command}'")
    print(f"{'='*80}\n")
    
    # PHASE 1: Analyze design intent
    print("🧠 PHASE 1: Analyzing design intent...")
    design_intent = await phase1_design_intent_analysis(text_command)
    
    if "error" in design_intent:
        print(f"❌ Phase 1 failed: {design_intent['error']}")
        jobs[job_id] = {
            "status": "failed",
            "error": design_intent["error"],
            "text_command": text_command,
            "input_file": f3d_path,
            "created_at": datetime.now().isoformat()
        }
        return {"job_id": job_id, "status": "failed", "error": design_intent["error"]}
    
    print(f"✓ Design Intent:")
    print(f"  Primary Goal: {design_intent.get('design_intent', {}).get('primary_goal')}")
    print(f"  Strategy: {design_intent.get('modification_strategy', {}).get('approach')}")
    print(f"  Plan Steps: {len(design_intent.get('high_level_plan', []))}")
    
    # PHASE 2: Generate initial operations (without model analysis yet)
    print("\n⚙️  PHASE 2: Generating CAD operations...")
    operations = await phase2_generate_operations(design_intent, model_analysis=None)
    
    if "error" in operations:
        print(f"❌ Phase 2 failed: {operations['error']}")
    else:
        print(f"✓ Generated {len(operations.get('operations', []))} operations")
        for i, op in enumerate(operations.get('operations', [])[:3], 1):
            print(f"  {i}. {op.get('type')} - {op.get('reasoning', 'N/A')[:50]}...")
    
    # Store job with all planning data
    jobs[job_id] = {
        "status": "pending_analysis",  # Waiting for Fusion to analyze the model
        "text_command": text_command,
        "design_intent": design_intent,
        "preliminary_operations": operations,
        "model_analysis": None,
        "final_operations": None,
        "input_file": f3d_path,
        "output_file": None,
        "created_at": datetime.now().isoformat(),
        "phase": "awaiting_model_analysis"
    }
    
    print(f"\n✓ Job {job_id} created and awaiting model analysis from Fusion 360\n")
    
    return {
        "job_id": job_id,
        "status": "pending_analysis",
        "design_intent": design_intent,
        "preliminary_operations": operations,
        "next_step": "Fusion 360 add-in should analyze the model and POST to /jobs/{job_id}/analysis"
    }


@app.post("/jobs/{job_id}/analysis")
async def submit_model_analysis(job_id: str, analysis: dict):
    """
    Fusion 360 add-in submits model analysis data
    This triggers Phase 2B: refining operations based on actual model data
    """
    if job_id not in jobs:
        return {"error": "Job not found"}
    
    job = jobs[job_id]
    job["model_analysis"] = analysis
    
    print(f"\n{'='*80}")
    print(f"📊 RECEIVED MODEL ANALYSIS for {job_id}")
    print(f"{'='*80}")
    print(f"Current Mass: {analysis.get('current_mass')}g")
    print(f"Volume: {analysis.get('volume')}cm³")
    print(f"Suitable for shelling: {analysis.get('can_shell')}")
    
    # PHASE 2B: Refine operations with model analysis
    print("\n⚙️  PHASE 2B: Refining operations with model data...")
    refined_operations = await phase2_generate_operations(
        job["design_intent"], 
        model_analysis=analysis
    )
    
    job["final_operations"] = refined_operations
    job["status"] = "pending"  # Ready for execution
    job["phase"] = "ready_for_execution"
    
    print(f"✓ Operations refined and ready for execution")
    print(f"  Operation count: {len(refined_operations.get('operations', []))}")
    print(f"\n✓ Job {job_id} ready for Fusion 360 to execute\n")
    
    return {
        "status": "success",
        "message": "Model analysis received and operations refined",
        "operations": refined_operations
    }


@app.get("/poll-jobs/")
async def poll_jobs():
    """
    Fusion 360 add-in polls for jobs
    Returns different job types based on phase
    """
    # Jobs awaiting model analysis
    awaiting_analysis = {
        k: {
            "status": v["status"],
            "phase": v.get("phase"),
            "text_command": v["text_command"],
            "input_file": v["input_file"],
            "design_intent": v["design_intent"],
            "preliminary_operations": v["preliminary_operations"]
        }
        for k, v in jobs.items() 
        if v["status"] == "pending_analysis"
    }
    
    # Jobs ready for execution
    ready_for_execution = {
        k: {
            "status": v["status"],
            "phase": v.get("phase"),
            "text_command": v["text_command"],
            "input_file": v["input_file"],
            "final_operations": v["final_operations"]
        }
        for k, v in jobs.items() 
        if v["status"] == "pending"
    }
    
    return {
        "awaiting_analysis": awaiting_analysis,
        "ready_for_execution": ready_for_execution
    }


@app.post("/complete-job/{job_id}")
async def complete_job(job_id: str, file: UploadFile):
    """Fusion 360 add-in uploads completed file"""
    if job_id not in jobs:
        return {"error": "Job not found"}
    
    output_path = f"jobs/{job_id}/output.f3d"
    with open(output_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    jobs[job_id]["status"] = "completed"
    jobs[job_id]["output_file"] = output_path
    jobs[job_id]["phase"] = "completed"
    
    print(f"✓ Job {job_id} completed successfully")
    
    return {"status": "success"}


@app.get("/job-status/{job_id}")
async def get_job_status(job_id: str):
    """Users check job status"""
    if job_id not in jobs:
        return {"error": "Job not found"}
    return jobs[job_id]


@app.get("/download/{job_id}")
async def download_result(job_id: str):
    """Users download completed file"""
    if job_id not in jobs or jobs[job_id]["status"] != "completed":
        return {"error": "Job not ready"}
    
    return FileResponse(
        jobs[job_id]["output_file"],
        filename="modified.f3d"
    )
