"""
Quick script to check available Fireworks models
"""

import os
from dotenv import load_dotenv
import requests

load_dotenv()

api_key = os.getenv("FIREWORKS")

if not api_key:
    print("ERROR: FIREWORKS key not found in .env")
    exit(1)

# Try to list available models using Fireworks API
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

# Try the models endpoint
url = "https://api.fireworks.ai/inference/v1/models"

print("Fetching available models from Fireworks API...")
print("=" * 60)

try:
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        models = response.json()
        
        if isinstance(models, dict) and 'data' in models:
            print(f"\nFound {len(models['data'])} models:\n")
            for model in models['data'][:20]:  # Show first 20
                model_id = model.get('id', 'unknown')
                print(f"  - {model_id}")
        else:
            print("Response format:")
            print(models)
    else:
        print(f"Error {response.status_code}: {response.text}")
        
except Exception as e:
    print(f"Exception: {e}")

print("\n" + "=" * 60)
print("\nAlternatively, try these commonly available models:")
print("  - accounts/fireworks/models/llama-v3-70b-instruct")
print("  - accounts/fireworks/models/mixtral-8x7b-instruct")
print("  - accounts/fireworks/models/llama-v2-70b-chat")

