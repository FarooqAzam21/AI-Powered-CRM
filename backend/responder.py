import os
import google.genai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
client = None

if api_key:
    client = genai.Client(api_key=api_key)
else:
    print("Warning: GEMINI_API_KEY not found in .env")

def generate_reply(email_body, category, tone, confidence, history):
    """
    Generates a professional email response using Gemini.
    """
    if not client:
        return "Error: AI not configured. Saving as draft for manual review."

    prompt = f"""
    You are an Executive AI Assistant acting on behalf of a busy professional.
    
    INCOMING EMAIL:
    category: {category}
    body: "{email_body}"
    
    YOUR TASK:
    Draft a professional, concise, and polite email response.
    
    GUIDELINES:
    1. Tone: {tone} (Professional, Polite, Efficient).
    2. Format: Standard Email (Greeting, Body, Closing).
    3. Do NOT include placeholders like [Your Name] - sign off as "AI Assistant".
    4. Since the category is {category}, address the specific needs of that topic.
    
    OUTPUT:
    Return ONLY the email body text.
    """

    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"Error generating draft: {str(e)}"
