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

NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"


def _parse_nemotron_json(raw: str) -> dict:
    """
    Ultra-robust JSON parser for Nemotron responses.
    Handles: <think> tags anywhere, comments, trailing commas, incomplete JSON
    """
    import re
    
    text = raw
    
    # 1. Remove ALL <think>...</think> blocks (even nested/broken ones)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<think>.*', '', text, flags=re.DOTALL | re.IGNORECASE)  # Unclosed think tags
    
    # 2. Extract from ``` fences
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```")[0].strip()
    elif "```" in text:
        parts = text.split("```")
        if len(parts) >= 3:
            text = parts[1].strip()
    
    # 3. Find the LARGEST valid JSON object (first { to matching })
    # This handles cases where there's text after the JSON
    start = text.find("{")
    if start == -1:
        return {
            "operations": [],
            "error": "No JSON object found",
            "raw_response": raw[:1500]  # Save raw response for debugging
        }
    
    # Count braces to find the matching closing brace
    brace_count = 0
    end = -1
    for i in range(start, len(text)):
        if text[i] == '{':
            brace_count += 1
        elif text[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                end = i
                break
    
    if end == -1:
        return {
            "operations": [],
            "error": "Incomplete JSON object",
            "raw_response": raw[:1500]  # Save raw response for debugging
        }
    
    text = text[start:end+1]
    
    # 4. Clean up the JSON
    text = re.sub(r'//[^\n]*', '', text)  # Remove // comments
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)  # Remove /* */ comments
    text = re.sub(r',\s*([}\]])', r'\1', text)  # Remove trailing commas
    
    # 5. Try standard JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError as ex:
        print(f"JSON parse error: {ex.msg} near: {text[max(0,ex.pos-50):ex.pos+50]!r}")
    
    # 6. Try json5 (handles unquoted keys, trailing commas, etc.)
    try:
        import json5
        return json5.loads(text)
    except ImportError:
        print("Tip: pip install json5 for better tolerance")
    except Exception as ex5:
        print(f"json5 also failed: {ex5}")
    
    # 7. Last resort - return empty operations so job can continue
    return {
        "operations": [],
        "summary": raw[:200],
        "raw_response": raw[:1500],
        "error": "Could not parse Nemotron JSON response"
    }


async def call_nemotron(system_prompt: str, user_message: str, max_tokens: int = 3072) -> dict:
    """Helper function to call Nemotron API"""
    if NVIDIA_API_KEY == "nvapi-PASTE_YOUR_KEY_HERE":
        print("WARNING: Nvidia API key not set!")
        return {"error": "Nvidia API key not configured", "raw_text": user_message}

    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "nvidia/llama-3.3-nemotron-super-49b-v1.5",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message}
        ],
        "temperature": 0.2,
        "top_p": 0.7,
        "max_tokens": max_tokens
    }

    try:
        async with httpx.AsyncClient() as client:
            print("Calling Nvidia Nemotron API...")
            response = await client.post(NVIDIA_API_URL, headers=headers, json=payload, timeout=60.0)
            response.raise_for_status()
            raw = response.json()["choices"][0]["message"]["content"]
            print("Received response from Nemotron")
            return _parse_nemotron_json(raw)
    except Exception as e:
        print(f"Error calling Nemotron API: {e}")
        return {"error": str(e), "raw_text": user_message}


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
    TWO-STEP APPROACH:
    1. Let Nemotron think freely (no JSON pressure)
    2. Request clean JSON output based on thinking
    """
    
    # STEP 1: Let Nemotron think
    print("🧠 Phase 2 Step 1: Letting Nemotron analyze and plan...")
    thinking_prompt = "You are a CAD expert. Think through the strategy for this design."
    
    if model_analysis:
        thinking_msg = f"""Design Plan:\n{json.dumps(design_plan, indent=2)}\n\nModel Data:\n{json.dumps(model_analysis, indent=2)}\n\nThink through: exact parameters, sequence, edge cases."""
    else:
        thinking_msg = f"""Design Plan:\n{json.dumps(design_plan, indent=2)}\n\nThink through the approach with best-guess parameters."""
    
    thinking = await call_nemotron(thinking_prompt, thinking_msg, max_tokens=1500)
    print(f"✓ Thinking complete")
    
    # STEP 2: Request clean JSON only
    print("📝 Phase 2 Step 2: Generating operations JSON...")
    json_prompt = """You are a JSON generator. Output ONLY the JSON object, nothing else.

Example input: {"goal": "reduce_weight", "target": 30}
Example output: {"operations": [{"id": "op_001", "type": "shell_body", "params": {"wall_thickness": 2.5}}]}

Available types: shell_body, add_ribs, fillet_edges, fillet_all_edges, mirror, rotate, scale, topology_optimization, run_topology_optimization, add_cross_bracing, pattern, apply_draft_angle, add_draft_angles, add_lattice_infill, strategic_holes"""
    
    if model_analysis:
        json_msg = f"""Input:
{json.dumps(design_plan, indent=2)}
{json.dumps(model_analysis, indent=2)}

Output:"""
    else:
        json_msg = f"""Input:
{json.dumps(design_plan, indent=2)}

Output:"""
    
    result = await call_nemotron(json_prompt, json_msg, max_tokens=2048)
    
    ops_count = len(result.get("operations", []))
    if ops_count == 0:
        print(f"\n⚠️  Phase 2 returned 0 operations!")
        print(f"📄 Raw response: {result.get('raw_response', str(result))[:800]}")
        if "error" in result:
            print(f"❌ Error: {result['error']}\n")
    else:
        print(f"✓ Generated {ops_count} operations\n")
    
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
        if "summary" in operations:
            print(f"📄 Nemotron returned: {operations['summary']}")
    else:
        ops_count = len(operations.get('operations', []))
        print(f"✓ Generated {ops_count} operations")
        if ops_count == 0 and "error" in operations:
            print(f"⚠️  Warning: {operations.get('error')}")
            print(f"📄 Raw summary: {operations.get('summary', 'N/A')}")
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