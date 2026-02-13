"""
Check which CAD operations are implemented and available
"""

import os
import re

# Use relative path from current directory
EXECUTOR_FILE = os.path.join("fusion_addin", "operation_executor.py")

print("="*80)
print("🔍 CAD Operations Status Check")
print("="*80)

if not os.path.exists(EXECUTOR_FILE):
    print(f"❌ File not found: {EXECUTOR_FILE}")
    print(f"   Current directory: {os.getcwd()}")
    print(f"   Make sure you're running this from the repository root!")
    exit(1)

with open(EXECUTOR_FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the handlers dictionary
handlers_match = re.search(r'handlers = \{([^}]+)\}', content, re.DOTALL)
if not handlers_match:
    print("❌ Could not find handlers dictionary")
    exit(1)

handlers_text = handlers_match.group(1)

# Parse the handlers
operations = {}
for line in handlers_text.split('\n'):
    line = line.strip()
    if ':' in line:
        parts = line.split(':')
        op_name = parts[0].strip().strip('"')
        handler_name = parts[1].strip().rstrip(',')
        operations[op_name] = handler_name

print(f"\n📋 Found {len(operations)} operation types:\n")

# Check implementation status for each
for op_name, handler_name in sorted(operations.items()):
    # Find the handler function
    handler_func = handler_name.replace('self.', '')
    func_pattern = f"def {handler_func}(self, params):"
    
    if func_pattern in content:
        # Check if it's a real implementation or placeholder
        func_start = content.find(func_pattern)
        func_text = content[func_start:func_start+500]
        
        if 'raise Exception' in func_text or 'NotImplementedError' in func_text:
            status = "🚧 PLACEHOLDER (raises exception)"
        elif 'return "Skipped' in func_text or 'not yet implemented' in func_text.lower():
            status = "⚠️  STUB (returns skip message)"
        elif 'TODO' in func_text or 'FIXME' in func_text:
            status = "🔨 PARTIAL (has TODOs)"
        else:
            status = "✅ IMPLEMENTED"
    else:
        status = "❌ MISSING"
    
    print(f"  {op_name:30s} → {status}")

print(f"\n{'='*80}")
print("📊 SUMMARY:")
print("="*80)
print("   These operations will actually modify your CAD model:")

# Manually list the ones we know work
working_ops = [
    "shell_body - Hollow out solids (CRITICAL for weight reduction)",
    "fillet / fillet_edges - Smooth sharp edges",
    "fillet_all_edges - Apply fillets to all edges",
    "scale - Resize geometry",
    "mirror - Mirror across planes",
    "rotate - Rotate geometry",
    "move - Translate geometry",
    "add_ribs - Add reinforcing ribs (creates small plates)",
    "strategic_holes - Create grid of holes for weight reduction",
]

for op in working_ops:
    print(f"   • {op}")

print(f"\n⚠️  PLACEHOLDERS (won't do anything):")
placeholder_ops = [
    "topology_optimization - Needs Fusion Generative Design API",
    "run_topology_optimization - Same as above",
    "lattice_infill / add_lattice_infill - Needs mesh generation",
    "variable_wall_thickness - Not yet implemented",
    "apply_draft_angles / add_draft_angles - Placeholder",
    "add_ventilation - Placeholder",
    "pattern - Basic implementation",
]

for op in placeholder_ops:
    print(f"   • {op}")

print(f"\n{'='*80}")
print("💡 RECOMMENDATIONS:")
print("="*80)
print("""
For WEIGHT REDUCTION, the AI should generate:
  1. shell_body (CRITICAL - hollows out the part)
  2. strategic_holes (removes material strategically)  
  3. fillet_all_edges (optional - for stress relief)
  
AVOID these (they're placeholders):
  - topology_optimization
  - lattice_infill
  - apply_draft_angles
  
The AI is currently generating these placeholders because they sound
sophisticated, but they don't actually work yet!
""")