"""
Helper script to add FIREWORKS API key to .env file
"""

import os
from pathlib import Path

def setup_fireworks_key():
    env_file = Path(".env")
    
    print("=" * 60)
    print("FIREWORKS API KEY SETUP")
    print("=" * 60)
    print()
    
    # Check if .env exists
    if not env_file.exists():
        print("[INFO] .env file not found, will create it")
        existing_content = ""
    else:
        print("[INFO] .env file found, will update it")
        existing_content = env_file.read_text()
    
    # Check if FIREWORKS already exists
    if "FIREWORKS=" in existing_content and not existing_content.split("FIREWORKS=")[1].split("\n")[0].strip() in ["", "your_key_here"]:
        print("\n[WARNING] FIREWORKS key already configured!")
        print("Current value: " + existing_content.split("FIREWORKS=")[1].split("\n")[0][:30] + "...")
        
        response = input("\nOverwrite existing key? (y/N): ").strip().lower()
        if response != 'y':
            print("Cancelled.")
            return
    
    print("\nGet your Fireworks API key from: https://fireworks.ai/account/api-keys")
    print()
    api_key = input("Enter your FIREWORKS API key: ").strip()
    
    if not api_key:
        print("\n[ERROR] No key provided. Cancelled.")
        return
    
    # Update or add FIREWORKS key
    lines = existing_content.split("\n")
    fireworks_found = False
    
    new_lines = []
    for line in lines:
        if line.startswith("FIREWORKS="):
            new_lines.append(f"FIREWORKS={api_key}")
            fireworks_found = True
        else:
            new_lines.append(line)
    
    if not fireworks_found:
        new_lines.append(f"FIREWORKS={api_key}")
    
    # Write back
    env_file.write_text("\n".join(new_lines))
    
    print("\n[SUCCESS] FIREWORKS key added to .env file!")
    print("\nYou can now run:")
    print("  python multi_agent_poc.py")
    print("  python multi_agent_with_memory.py")
    print()
    print("=" * 60)

if __name__ == "__main__":
    setup_fireworks_key()

