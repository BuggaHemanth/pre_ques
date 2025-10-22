"""
Quick test to verify Gemini API is working
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os

# Load environment
load_dotenv()

gemini_key = os.getenv('GEMINI_API_KEY')
print(f"API Key loaded: {gemini_key[:20]}..." if gemini_key else "No API key found!")

# Test Gemini
try:
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp",
        google_api_key=gemini_key,
        temperature=0.7
    )

    response = llm.invoke("Say 'Hello, Gemini is working!' in JSON format: {\"message\": \"your message here\"}")
    print("\n✅ SUCCESS! Gemini Response:")
    print(response.content)

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    print(traceback.format_exc())
