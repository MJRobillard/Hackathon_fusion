"""
Check which Fireworks models are available
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("FIREWORKS")

if not api_key:
    print("❌ FIREWORKS API key not found in .env")
    exit(1)

print("Checking available Fireworks models...\n")

# Common Llama models to test
models_to_test = [
    "accounts/fireworks/models/llama-v3p1-8b-instruct",
    "accounts/fireworks/models/llama-v3p1-70b-instruct",
    "accounts/fireworks/models/llama-v3-8b-instruct",
    "accounts/fireworks/models/llama-v3-70b-instruct",
    "accounts/fireworks/models/llama-v3p2-1b-instruct",
    "accounts/fireworks/models/llama-v3p2-3b-instruct",
    "accounts/fireworks/models/firefunction-v2",
    "accounts/fireworks/models/mixtral-8x7b-instruct",
    "accounts/fireworks/models/qwen2p5-72b-instruct",
]

url = "https://api.fireworks.ai/inference/v1/chat/completions"
headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

print("Testing models:\n")
available_models = []

for model in models_to_test:
    payload = {
        "model": model,
        "max_tokens": 10,
        "messages": [{"role": "user", "content": "Hi"}]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ {model}")
            available_models.append(model)
        else:
            error = response.json().get("error", {})
            if "not found" in error.get("message", "").lower():
                print(f"❌ {model} - Not found")
            else:
                print(f"⚠️  {model} - {error.get('message', 'Unknown error')}")
    except Exception as e:
        print(f"❌ {model} - Error: {e}")

print("\n" + "=" * 60)
if available_models:
    print(f"✅ Found {len(available_models)} available models:")
    print("\nRecommended model (fastest):")
    print(f"   {available_models[0]}")
    print("\nUpdate simple_rag_agent.py to use this model.")
else:
    print("❌ No models available. Check your API key or Fireworks account.")
print("=" * 60)

