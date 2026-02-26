import httpx
import json

# Replace with your actual API key
NVIDIA_API_KEY = ""  

print("=" * 80)
print("TESTING NVIDIA BUILD.NVIDIA.COM API")
print("=" * 80)

# The correct endpoint
url = "https://integrate.api.nvidia.com/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {NVIDIA_API_KEY}",
    "Content-Type": "application/json"
}

# Try different model name formats
test_models = [
    "nvidia/llama-3_3-nemotron-super-49b-v1_5",  # With underscores
    "nvidia/llama-3.3-nemotron-super-49b-v1.5",   # With dots
    "meta/llama-3.1-8b-instruct",                  # Different model to test API key
]

for model_name in test_models:
    print(f"\n{'='*80}")
    print(f"Testing model: {model_name}")
    print('='*80)
    
    payload = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": "Say hello"}
        ],
        "max_tokens": 50,
        "temperature": 0.2
    }
    
    try:
        with httpx.Client() as client:
            response = client.post(url, headers=headers, json=payload, timeout=30.0)
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ SUCCESS!")
                print(f"Response: {result['choices'][0]['message']['content']}")
                break  # Found working model format
            else:
                print(f"✗ Error Response:")
                print(response.text[:500])  # First 500 chars
                
    except Exception as e:
        print(f"✗ Exception: {e}")

print("\n" + "=" * 80)
print("If all models failed:")
print("1. Verify your API key is correct (should start with 'nvapi-')")
print("2. Check that you have access to Nemotron on build.nvidia.com")
print("3. Try visiting: https://build.nvidia.com/nvidia/llama-3_3-nemotron-super-49b-v1_5")
print("=" * 80)
