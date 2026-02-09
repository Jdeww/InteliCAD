import requests
import json

BASE_URL = "http://127.0.0.1:8000"

# Test file path
file_path = r"C:\Users\jdwil\Documents\Projects\GTC 2026 Golden Ticket\Headphone hanger.f3d"

# Test different types of commands to see how Nemotron interprets them
test_commands = [
    "Make this model 2x bigger",
    "Scale to 150% and rotate 90 degrees",
    "Add rounded corners with 5mm radius",
    "Mirror this along the X axis",
    "Make it twice as tall but keep the same width",
    "Add a 10mm fillet to all edges",
    "Create a linear pattern with 5 copies spaced 20mm apart"
]

print("=" * 80)
print("TESTING NEMOTRON CAD COMMAND GENERATION")
print("=" * 80)

for i, command in enumerate(test_commands, 1):
    print(f"\n{'='*80}")
    print(f"Test {i}: '{command}'")
    print('='*80)
    
    with open(file_path, "rb") as f:
        files = {"file": ("Headphone hanger.f3d", f, "application/octet-stream")}
        data = {"text_command": command}
        response = requests.post(f"{BASE_URL}/submit-job/", files=files, data=data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✓ Job submitted successfully")
        print(f"Job ID: {result['job_id']}")
        print(f"\nGenerated CAD Commands:")
        print(json.dumps(result.get('cad_commands', {}), indent=2))
    else:
        print(f"\n✗ Failed: {response.status_code}")
        print(response.text)
    
    print()

print("\n" + "=" * 80)
print("TESTING COMPLETE!")
print("=" * 80)
print("\nNote: Check your server terminal to see Nemotron's full responses")