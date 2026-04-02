"""
Code-Repair Engine Module
Role: Strict code bug fixer
Rules: Output raw code only, NO EXPLANATIONS, NO MARKDOWN
"""

from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None

# Keywords that trigger the code-repair engine
CODE_REPAIR_KEYWORDS = [
    "fix code", "code fix", "debug code", "code repair", 
    "bug fix", "code theek", "error hata", "repair this",
    "fix this script", "correct code", "ye code fix karo"
]

def is_code_repair_request(text):
    """Detect if the user wants strict code repair instead of chat."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in CODE_REPAIR_KEYWORDS)

def get_repair_prompt():
    """System prompt for strict code-only output."""
    return """You are a Code-Repair Engine. 
Your ONLY purpose is to fix broken code, apply perfect SOLID principles, ensure correct imports, and add necessary try/except blocks.

STRICT CONSTRAINTS:
1. NO EXPLANATIONS: Do not write any English text, do not explain what you fixed.
2. NO MARKDOWN FENCES: Do not use ```python or ``` at the start or end.
3. RAW CODE ONLY: The output must be perfectly safe to execute via eval() or written directly to a .py file.
4. ROLE-BASED: You are a machine engine, not a human assistant.
5. ALWAYS ensure that any library you add (like 'psutil' or 'requests') is either already in the requirements.txt or mentioned as a comment at the top of the fixed file.

If the user gives buggy code, return ONLY the raw corrected source code strings.
If the user gives an error message or concept, return ONLY the raw template code strings.
"""

def repair_code(user_input):
    """
    Send the buggy code/error to Gemini with the strict repair prompt.
    Returns ONLY the repaired code string.
    """
    if not client:
        return "print('Error: GEMINI_API_KEY not found in .env')"
    
    full_prompt = f"{get_repair_prompt()}\n\nUSER INPUT/CODE TO REPAIR:\n{user_input}\n\nFIXED CODE:"
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=full_prompt
        )
        reply = response.text.strip()
        
        # Fallback safety: if Gemini accidentally includes markdown fences, strip them
        if reply.startswith("```"):
            lines = reply.split("\n")
            if len(lines) > 2 and lines[0].startswith("```") and lines[-1].startswith("```"):
                reply = "\n".join(lines[1:-1])
        
        return reply
    except Exception as e:
        # Return error as a python comment string so it doesn't break eval/write contexts
        return f"# Code-Repair Engine Error: {str(e)}"
