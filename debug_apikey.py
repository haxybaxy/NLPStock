#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv
import json

# Load environment variables
print("Loading environment variables...")
load_dotenv()

# Get the API key
api_key = os.getenv("GROQ_API_KEY")

print("\n=== API KEY DIAGNOSTICS ===")
if not api_key:
    print("❌ ERROR: API key is empty or not found")
    print("  Check if your .env file exists and contains GROQ_API_KEY")
else:
    print(f"✓ API key found with length: {len(api_key)}")
    print(f"✓ API key starts with: {api_key[:10]}...")

    # Check common problems
    if not api_key.startswith("gsk_"):
        print("❌ ERROR: API key doesn't start with 'gsk_', which is required for Groq API keys")
    
    if api_key != api_key.strip():
        print("❌ ERROR: API key has extra whitespace at beginning or end")
        print(f"  Key with whitespace removed: '{api_key.strip()}'")
    
    if "=" in api_key:
        print("❌ ERROR: API key contains '=', which suggests the .env file might be incorrectly formatted")
        print("  The .env file should have: GROQ_API_KEY=gsk_your_key_here (no spaces around =)")
    
    if '"' in api_key or "'" in api_key:
        print("❌ ERROR: API key contains quotes, which should be removed")

print("\n=== .ENV FILE DIAGNOSTICS ===")
env_path = os.path.join(os.getcwd(), ".env")
if os.path.exists(env_path):
    print(f"✓ .env file found at: {env_path}")
    
    try:
        with open(env_path, 'r') as f:
            env_content = f.read()
            print("✓ .env file content:")
            for line in env_content.split('\n'):
                if "GROQ_API_KEY" in line:
                    # Hide most of the actual key
                    key_parts = line.split('=', 1)
                    if len(key_parts) > 1:
                        key = key_parts[1]
                        if len(key) > 10:
                            masked_key = key[:10] + "..." + key[-4:] if len(key) > 14 else key
                            print(f"  {key_parts[0]}={masked_key}")
                        else:
                            print(f"  {line}")
                    else:
                        print(f"  {line}")
                else:
                    print(f"  {line}")
    except Exception as e:
        print(f"❌ ERROR reading .env file: {e}")
else:
    print(f"❌ ERROR: .env file not found at {env_path}")
    
print("\n=== TESTING GROQ API ===")
try:
    from groq import Groq
    print("✓ groq package is installed")
    
    if api_key:
        try:
            # Create client with the API key
            client = Groq(api_key=api_key)
            print("✓ Groq client initialized successfully")
            
            # Try to make a simple API call
            print("Sending test request to Groq API...")
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": "Say hello in one word"}],
                model="llama3-8b-8192",
                max_tokens=5
            )
            print(f"✓ API call successful! Response: {response.choices[0].message.content}")
            print("Your API key is working correctly!")
            
        except Exception as e:
            print(f"❌ ERROR with Groq API call: {e}")
            print("Your API key is not working. Please check the error above.")
    else:
        print("❌ Skipping API test because no valid API key was found")
        
except ImportError:
    print("❌ ERROR: groq package is not installed")
    print("  Install it with: pip install groq")

print("\n=== RECOMMENDATIONS ===")
print("1. Make sure your .env file contains exactly: GROQ_API_KEY=gsk_your_key_here")
print("   - No spaces around =")
print("   - No quotes around the API key")
print("   - No spaces or newlines after the key")
print("2. Check if your Groq API key is still valid in the Groq dashboard")
print("3. If using a new API key, be sure to restart any running applications")

if not api_key or not api_key.startswith("gsk_"):
    print("\nTo fix your .env file, run:")
    print("echo 'GROQ_API_KEY=your_key_here' > .env")
    print("Replace 'your_key_here' with your actual API key from Groq") 