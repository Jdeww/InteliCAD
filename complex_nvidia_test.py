import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

# Test file path
file_path = r"C:\Users\jdwil\Documents\Projects\GTC 2026 Golden Ticket\Headphone hanger.f3d"

# Complex, high-level design commands
complex_commands = [
    "Make this lighter without compromising structural integrity",
    "Reduce material usage by 40% while maintaining strength for a 20kg load",
    "Optimize this for 3D printing with minimal support material needed",
    "Make it hollow but keep it strong enough to hang a laptop bag",
    "Add ventilation holes while maintaining the overall structure",
]

print("=" * 100)
print("TESTING ADVANCED AI-DRIVEN CAD MODIFICATION")
print("=" * 100)

for i, command in enumerate(complex_commands[:2], 1):  # Test first 2 to save tokens
    print(f"\n{'='*100}")
    print(f"TEST {i}: '{command}'")
    print('='*100)
    
    # Submit job
    with open(file_path, "rb") as f:
        files = {"file": ("Headphone hanger.f3d", f, "application/octet-stream")}
        data = {"text_command": command}
        response = requests.post(f"{BASE_URL}/submit-job/", files=files, data=data)
    
    if response.status_code != 200:
        print(f"\n✗ Failed to submit: {response.status_code}")
        print(response.text)
        continue
    
    result = response.json()
    job_id = result.get('job_id')
    
    print(f"\n✓ Job submitted: {job_id}")
    print(f"Status: {result.get('status')}")
    
    # Display design intent analysis
    design_intent = result.get('design_intent', {})
    if design_intent and 'design_intent' in design_intent:
        di = design_intent['design_intent']
        print(f"\n📋 DESIGN INTENT ANALYSIS:")
        print(f"  Primary Goal: {di.get('primary_goal')}")
        print(f"  Material: {di.get('material_assumed', 'N/A')}")
        
        targets = di.get('quantitative_targets', {})
        if targets:
            print(f"  Targets:")
            for key, val in targets.items():
                print(f"    - {key}: {val}%")
        
        constraints = di.get('constraints', [])
        if constraints:
            print(f"  Constraints: {', '.join(constraints[:3])}")
    
    # Display modification strategy
    strategy = design_intent.get('modification_strategy', {})
    if strategy:
        print(f"\n🎯 MODIFICATION STRATEGY:")
        print(f"  Approach: {strategy.get('approach')}")
        print(f"  Reasoning: {strategy.get('reasoning', 'N/A')[:100]}...")
        
        risks = strategy.get('risk_factors', [])
        if risks:
            print(f"  Risk Factors: {', '.join(risks[:2])}")
    
    # Display high-level plan
    plan = design_intent.get('high_level_plan', [])
    if plan:
        print(f"\n📝 HIGH-LEVEL PLAN ({len(plan)} steps):")
        for step in plan[:3]:
            print(f"  Step {step.get('step')}: {step.get('description')}")
            print(f"    Expected: {step.get('expected_outcome')}")
    
    # Display preliminary operations
    ops = result.get('preliminary_operations', {}).get('operations', [])
    if ops:
        print(f"\n⚙️  PRELIMINARY OPERATIONS ({len(ops)}):")
        for op in ops[:3]:
            print(f"  - {op.get('type')}: {op.get('reasoning', 'N/A')[:60]}...")
            params = op.get('params', {})
            if params:
                print(f"    Params: {json.dumps(params, indent=6)[:100]}...")
    
    # Check if it needs user clarification
    clarification = design_intent.get('requires_user_clarification', {})
    questions = clarification.get('questions', [])
    if questions:
        print(f"\n❓ QUESTIONS FOR USER:")
        for q in questions:
            print(f"  - {q}")
        assumptions = clarification.get('assumptions_made', [])
        if assumptions:
            print(f"\n💭 ASSUMPTIONS MADE:")
            for a in assumptions:
                print(f"  - {a}")
    
    print(f"\n{'='*100}")
    time.sleep(1)  # Brief pause between tests

print("\n" + "=" * 100)
print("TESTING COMPLETE!")
print("\nNote: In a real workflow:")
print("1. Fusion 360 would analyze the model")
print("2. POST analysis data to /jobs/{job_id}/analysis")
print("3. Nemotron refines operations based on actual model data")
print("4. Fusion 360 executes the refined operations")
print("=" * 100)