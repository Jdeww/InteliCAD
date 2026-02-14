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
NVIDIA_API_KEY = "nvapi-PASTE_YOUR_KEY_HERE"  # <-- REPLACE THIS!
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


async def call_nemotron(system_prompt: str, user_message: str, max_tokens: int = 3072, model: str = "nvidia/llama-3.3-nemotron-super-49b-v1.5") -> dict:
    """Helper function to call Nvidia API with any model"""
    if NVIDIA_API_KEY == "nvapi-PASTE_YOUR_KEY_HERE":
        print("WARNING: Nvidia API key not set!")
        return {"error": "Nvidia API key not configured", "raw_text": user_message}

    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
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
    "part_type": "structural_bracket | hanger | enclosure | functional_tool | decorative | mechanical_component",
    "use_case_description": "Brief description of what this part does and how it's used",
    "load_bearing": true/false,
    "exposure_conditions": "indoor | outdoor | high_temperature | wet_environment | clean_room",
    "quantitative_targets": {
      "weight_reduction_percent": 30,
      "strength_retention_percent": 85,
      "cost_reduction_percent": 20
    },
    "constraints": ["maintain_mounting_holes", "no_sharp_edges", "max_height_50mm"],
    "material_assumed": "PLA" or "ABS" or "Steel" etc.
  },
  "modification_strategy": {
    "approach": "shell_and_reinforce | lattice_infill | topology_optimization | hole_pattern | minimal_intervention",
    "reasoning": "Detailed explanation of why this approach fits the goals AND use case",
    "operations_to_avoid": ["ventilation - not needed for this use case", "strategic_holes - would weaken load-bearing structure"],
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

## CRITICAL CONTEXT-AWARENESS RULES:

**For LOAD-BEARING parts (brackets, hangers, structural components):**
- AVOID: ventilation, strategic_holes, excessive hollowing
- PREFER: selective reinforcement, minimal shelling with thick walls (5-8mm)
- REASONING: Strength is paramount, weight reduction is secondary

**For ENCLOSURES/HOUSINGS:**
- CONSIDER: ventilation (if electronics inside need cooling)
- PREFER: shelling with moderate walls (2-4mm), ribs for rigidity
- REASONING: Balance between protection and weight

**For DECORATIVE/NON-STRUCTURAL parts:**
- PREFER: aggressive hollowing, lattice patterns, artistic hole patterns
- AVOID: over-engineering with ribs
- REASONING: Weight reduction is primary goal

**For HANGERS/CLIPS (like headphone hangers):**
- AVOID: strategic_holes, ventilation (serve no purpose, only weaken)
- PREFER: selective shelling, reinforce at stress points (clip area, mounting point)
- REASONING: Must maintain grip strength and mounting strength

CRITICAL: Always output valid JSON. Think through the engineering tradeoffs AND use case appropriateness carefully."""

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
    print("   Using nvidia/llama-3.3-nemotron-super-49b-v1.5 (strategic reasoning)")
    thinking_prompt = "You are a CAD expert. Think through the strategy for this design."
    
    if model_analysis:
        thinking_msg = f"""Design Plan:\n{json.dumps(design_plan, indent=2)}\n\nModel Data:\n{json.dumps(model_analysis, indent=2)}\n\nThink through: exact parameters, sequence, edge cases."""
    else:
        thinking_msg = f"""Design Plan:\n{json.dumps(design_plan, indent=2)}\n\nThink through the approach with best-guess parameters."""
    
    # Use Nemotron Super for strategic thinking (it's good at this!)
    thinking = await call_nemotron(
        thinking_prompt, 
        thinking_msg, 
        max_tokens=1500,
        model="nvidia/llama-3.3-nemotron-super-49b-v1.5"
    )
    print(f"✓ Thinking complete")
    
    # STEP 2: Request clean JSON only
    print("📝 Phase 2 Step 2: Generating operations JSON...")
    print("   Using meta/llama-3.1-8b-instruct (fast, structured output)")
    
    json_prompt = """You are a JSON generator. Output ONLY the JSON object, nothing else.

CRITICAL: Every operation MUST have complete "params" with actual values!
CRITICAL: Use the model analysis data to calculate SAFE parameter values!
CRITICAL: RESPECT the "operations_to_avoid" from the design strategy!

PARAMETER SAFETY RULES:
- shell_body wall_thickness: MIN 10% of smallest dimension, typically 3-5mm for small parts (5-8mm for load-bearing)
- fillet_all_edges radius: MAX 2% of smallest dimension, typically 0.5-1.5mm  
- add_ribs height: MAX 20% of part height
- strategic_holes diameter: MAX 15% of smallest dimension

USE CASE APPROPRIATENESS:
- Load-bearing parts (brackets, hangers, clips): AVOID strategic_holes, ventilation (they only weaken!)
- Enclosures: OK to use ventilation if cooling needed
- Decorative parts: OK to use strategic_holes for aesthetics
- Headphone hangers/clips: ONLY use shell_body + add_ribs, NO holes!

Example for weight reduction on a HANGER/CLIP:
{
  "operations": [
    {
      "id": "op_001",
      "type": "shell_body",
      "params": {
        "wall_thickness": 6.0,
        "inside_offset": true,
        "faces_to_remove": ["top_face"]
      },
      "reasoning": "Hollow out body while maintaining clip strength"
    },
    {
      "id": "op_002", 
      "type": "add_ribs",
      "params": {
        "thickness": 2.0,
        "height": 8.0,
        "pattern": "cross_bracing",
        "locations": ["interior_walls"]
      },
      "reasoning": "Reinforce hollowed structure"
    },
    {
      "id": "op_003",
      "type": "fillet_all_edges",
      "params": {
        "radius": 1.0
      },
      "reasoning": "Smooth stress concentrations"
    }
  ]
}

IMPORTANT operation types and their REQUIRED params:
- shell_body: wall_thickness (number 3-8mm SAFE), inside_offset (bool), faces_to_remove (list)
- add_ribs: thickness (number 1-3mm), height (number 5-15mm), pattern (string), locations (list)

STRICTLY FORBIDDEN operations (will cause errors):
- fillet_all_edges: Causes geometry errors, DO NOT USE
- strategic_holes: ONLY for decorative parts, NEVER for load-bearing parts like hangers, brackets, clips
- ventilation: ONLY for electronics enclosures that need cooling, NEVER for hangers/brackets
- topology_optimization: Placeholder only
- lattice_infill: Placeholder only

FOR HANGERS, CLIPS, BRACKETS (load-bearing parts):
ONLY ALLOWED: shell_body, add_ribs
FORBIDDEN: strategic_holes, ventilation, fillet_all_edges

Generate ONLY 2 operations: shell_body + add_ribs"""
    
    if model_analysis:
        # Extract key dimensions for the AI to use
        bounding_box = model_analysis.get("bounding_box", {})
        dimensions = f"Part size: {bounding_box.get('length', 'N/A')}mm × {bounding_box.get('width', 'N/A')}mm × {bounding_box.get('height', 'N/A')}mm"
        
        # Extract operations to avoid from design strategy
        operations_to_avoid = design_plan.get("modification_strategy", {}).get("operations_to_avoid", [])
        avoid_note = ""
        if operations_to_avoid:
            avoid_note = f"\nCRITICAL - DO NOT USE THESE OPERATIONS:\n{json.dumps(operations_to_avoid, indent=2)}\n"
        
        # Extract part type for context
        part_type = design_plan.get("design_intent", {}).get("part_type", "unknown")
        use_case = design_plan.get("design_intent", {}).get("use_case_description", "")
        context_note = f"\nPART TYPE: {part_type}\nUSE CASE: {use_case}\n"
        
        json_msg = f"""Design plan and model data:
{json.dumps(design_plan, indent=2)}
{json.dumps(model_analysis, indent=2)}

{dimensions}
{context_note}
{avoid_note}

IMPORTANT: Calculate safe parameters based on part size above!
- For shell_body: wall_thickness should be at least 10% of smallest dimension (minimum 5mm for load-bearing parts)
- For fillet_all_edges: radius should be small (0.5-1.5mm) to avoid complex geometry
- ONLY use operations that make sense for this specific use case!

Generate operations JSON with SAFE, COMPLETE, APPROPRIATE params:"""
    else:
        json_msg = f"""Design plan:
{json.dumps(design_plan, indent=2)}

Generate operations JSON with COMPLETE params:"""
    
    # Use fast Llama 3.1 8B for JSON generation (more obedient, no thinking tendency)
    result = await call_nemotron(
        json_prompt, 
        json_msg, 
        max_tokens=2048,
        model="meta/llama-3.1-8b-instruct"
    )
    
    # POST-GENERATION FILTER: Remove operations that don't make sense for this use case
    if model_analysis:
        part_type = design_plan.get("design_intent", {}).get("part_type", "").lower()
        operations = result.get("operations", [])
        filtered_ops = []
        removed_ops = []
        
        for op in operations:
            op_type = op.get("type", "")
            
            # Rules for load-bearing parts (hangers, brackets, clips)
            if any(keyword in part_type for keyword in ["hanger", "bracket", "clip", "mount", "hook"]):
                if op_type in ["strategic_holes", "ventilation", "fillet_all_edges"]:
                    removed_ops.append(f"{op_type} (inappropriate for load-bearing {part_type})")
                    continue
            
            # Rules for enclosures
            if "enclosure" in part_type or "housing" in part_type:
                # Ventilation OK only if electronics mentioned
                if op_type == "ventilation":
                    use_case = design_plan.get("design_intent", {}).get("use_case_description", "").lower()
                    if "electronic" not in use_case and "cooling" not in use_case:
                        removed_ops.append(f"{op_type} (no cooling needed)")
                        continue
            
            filtered_ops.append(op)
        
        result["operations"] = filtered_ops
        
        if removed_ops:
            print(f"   ⚠️  Filtered out inappropriate operations: {', '.join(removed_ops)}")
    
    ops_count = len(result.get("operations", []))
    if ops_count == 0:
        print(f"\n⚠️  Phase 2 returned 0 operations!")
        print(f"📄 Raw response: {result.get('raw_response', str(result))[:800]}")
        if "error" in result:
            print(f"❌ Error: {result['error']}\n")
    else:
        print(f"✓ Generated {ops_count} operations\n")
    
    return result


async def phase3_retry_failed_operations(
    original_command: str,
    design_plan: dict,
    model_analysis: dict,
    execution_results: list
) -> dict:
    """
    PHASE 3: Intelligent Parameter Adjustment
    
    For FAILED operations: Retry the SAME operation with safer/adjusted parameters
    For SUCCESSFUL operations: Optionally make them more aggressive if safe to do so
    
    NEVER switch to different operation types - only adjust parameters!
    """
    
    print("🔄 PHASE 3: Analyzing execution results and adjusting parameters...")
    
    # Separate successful and failed operations
    succeeded = [r for r in execution_results if r.get('success')]
    failed = [r for r in execution_results if not r.get('success')]
    
    if not failed:
        print("   ✓ All operations succeeded - checking if we can be more aggressive...")
        # Could optionally make successful operations more aggressive here
        # For now, just return empty
        return {"operations": []}
    
    print(f"   Found {len(failed)} failed operation(s) to retry with adjusted parameters")
    
    # Build context for parameter adjustment
    retry_analysis = []
    for f in failed:
        op = f.get('operation', {})
        error = f.get('error', '')
        
        retry_analysis.append({
            "operation_type": op.get('type'),
            "original_params": op.get('params'),
            "error_message": error,
            "original_reasoning": op.get('reasoning')
        })
    
    # STEP 1: Analyze failures and determine parameter adjustments
    print("🧠 Phase 3 Step 1: Analyzing failures and planning parameter adjustments...")
    
    thinking_prompt = """You are a CAD expert analyzing failed operations to determine better parameters.

CRITICAL RULES:
- NEVER switch to a different operation type
- ONLY adjust parameters of the SAME operation
- If an operation is fundamentally impossible, recommend skipping it entirely
- Focus on making parameters SAFER (thicker walls, smaller radii, fewer holes, etc.)

CRITICAL: Understanding shell_body wall_thickness:
- wall_thickness = how much solid material REMAINS after hollowing
- THICKER walls = LESS material removed = SAFER operation
- THINNER walls = MORE material removed = MORE aggressive = more likely to fail
- "Topology change" error = too much material being removed
- Solution: INCREASE wall_thickness (add 5-10mm to make walls thicker)
- If already very thick (>8mm) and still failing: geometry incompatible, skip operation"""
    
    thinking_msg = f"""Original Goal: {original_command}

Part Information:
{json.dumps(model_analysis, indent=2)}

FAILED Operations Analysis:
{json.dumps(retry_analysis, indent=2)}

For EACH failed operation, think through:
1. WHY did it fail? (analyze the error message)
2. Can this SAME operation work with different parameters?
3. If YES: What parameter changes would make it succeed? (be specific!)
4. If NO: Recommend skipping this operation entirely

Common failure patterns and fixes:
- "topology change" error on shell_body → Increase wall_thickness (try 2x thicker)
- "fillet at corner" error → Decrease fillet radius (try 50% smaller)
- "extrusion outside boundary" for holes → Skip this operation (geometry changed)
- "complex geometry" → Simplify parameters or skip

Think through each operation separately."""
    
    thinking_result = await call_nemotron(
        thinking_prompt,
        thinking_msg,
        max_tokens=1500,
        model="nvidia/llama-3.3-nemotron-super-49b-v1.5"
    )
    print(f"✓ Analysis complete")
    
    # STEP 2: Generate adjusted parameters for SAME operations
    print("📝 Phase 3 Step 2: Generating adjusted parameters...")
    
    json_prompt = """You are a JSON generator. Output ONLY valid JSON with parameter adjustments.

CRITICAL RULES:
1. NEVER change the operation type - only adjust parameters
2. If an operation cannot work, return empty operations array
3. Use SAFER parameters than the original (thicker walls, smaller radii, etc.)

CRITICAL UNDERSTANDING OF SHELL_BODY:
- wall_thickness is how much MATERIAL REMAINS after hollowing
- LARGER wall_thickness = LESS material removed = LESS aggressive = SAFER
- SMALLER wall_thickness = MORE material removed = MORE aggressive = MORE likely to fail
- "Topology change" error means TOO MUCH material is being removed
- FIX: INCREASE wall_thickness significantly (add 5-10mm, not double it!)

Example for failed shell_body with "topology change":
Original: {"type": "shell_body", "params": {"wall_thickness": 5.0}}
Error: "topology change - too much material removed"
CORRECT Adjustment:
{
  "operations": [
    {
      "id": "op_retry_001",
      "type": "shell_body",
      "params": {
        "wall_thickness": 12.0,
        "inside_offset": true,
        "faces_to_remove": ["top_face"]
      },
      "reasoning": "Increased wall thickness from 5.0mm to 12.0mm to remove LESS material and avoid topology change"
    }
  ]
}

WRONG Adjustment (DO NOT DO THIS):
{
  "operations": [
    {
      "type": "shell_body",
      "params": {"wall_thickness": 2.5}  // WRONG - this removes MORE material!
    }
  ]
}

Example for failed fillet_all_edges:
Original: {"type": "fillet_all_edges", "params": {"radius": 1.0}}
Error: "edges meet at corner"
Adjusted:
{
  "operations": []
}
Reasoning: Fillet is fundamentally incompatible with this geometry - skip it entirely

PARAMETER ADJUSTMENT GUIDELINES:
- shell_body with "topology change" error: ADD 5-10mm to wall_thickness (make walls THICKER)
- shell_body with "topology change" and already thick (>8mm): SKIP entirely (geometry incompatible)
- fillet_all_edges with geometry error: SKIP entirely (return empty array)
- strategic_holes with "outside boundary": SKIP entirely (geometry changed)
- add_ribs with any error: Reduce height by 50% OR skip

Output ONLY the JSON with adjusted parameters for the SAME operations:"""
    
    json_msg = f"""Failed Operations:
{json.dumps(retry_analysis, indent=2)}

Part size: {model_analysis.get('bounding_box', {})}

Generate adjusted parameters for the SAME operations (or empty array if operation should be skipped):"""
    
    result = await call_nemotron(
        json_prompt,
        json_msg,
        max_tokens=1500,
        model="meta/llama-3.1-8b-instruct"
    )
    
    retry_count = len(result.get("operations", []))
    if retry_count > 0:
        print(f"✓ Generated {retry_count} retry operation(s) with adjusted parameters")
    else:
        print(f"   → All failed operations deemed unrecoverable - skipping retries")
    
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


@app.post("/retry-failed/{job_id}")
async def retry_failed_operations(job_id: str, execution_results: dict):
    """
    Phase 3: Generate alternative operations for failed ones
    
    Request body:
    {
        "execution_results": [
            {"operation": {...}, "success": true/false, "error": "..."},
            ...
        ]
    }
    """
    if job_id not in jobs:
        return {"error": "Job not found"}
    
    job = jobs[job_id]
    results = execution_results.get("execution_results", [])
    
    if not results:
        return {"error": "No execution results provided"}
    
    # Run Phase 3
    retry_ops = await phase3_retry_failed_operations(
        original_command=job.get("text_command", ""),
        design_plan=job.get("design_intent", {}),
        model_analysis=job.get("model_analysis", {}),
        execution_results=results
    )
    
    # Store retry operations
    job["retry_operations"] = retry_ops
    job["phase"] = "retry_ready"
    
    print(f"✓ Job {job_id} has {len(retry_ops.get('operations', []))} retry operations ready")
    
    return {
        "status": "success",
        "retry_operations": retry_ops.get("operations", []),
        "count": len(retry_ops.get("operations", []))
    }


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