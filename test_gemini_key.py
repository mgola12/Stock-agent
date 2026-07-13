"""
Quick standalone check that your Gemini API key works.

Usage:
    export GEMINI_API_KEY="your-key-here"
    python3 test_gemini_key.py
"""

import os
import sys

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("❌ GEMINI_API_KEY is not set in your environment.")
    print("   Set it with: export GEMINI_API_KEY='your-key-here'")
    sys.exit(1)

try:
    from google import genai
except ImportError:
    print("❌ google-genai not installed. Run: pip install google-genai")
    sys.exit(1)

print("Testing Gemini API key...")
client = genai.Client(api_key=api_key)

try:
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents="Reply with exactly the word: OK",
    )
    print("✅ Success! Gemini responded:", response.text.strip())
except Exception as e:
    print("❌ Gemini API call failed:", e)
    sys.exit(1)
