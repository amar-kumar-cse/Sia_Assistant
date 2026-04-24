"""
Sia AI - Brain Module (FINAL VERSION)
Handles Gemini integration, prompt management, and API key rotation.
"""

import os
import threading
import google.generativeai as genai
from dotenv import load_dotenv

SIA_SYSTEM_PROMPT = """
Tu Sia hai — ek friendly, witty, caring Indian AI desktop companion.

PERSONALITY:
- Hinglish mein baat kar (Hindi+English mix)
- User ko "Hero" keh affectionately
- Short punchy replies (jab tak detail na maange)
- Kabhi kabhi funny/witty comments karo
- Caring aur helpful rehna

EMOTION TAGS (har response ke shuru mein):
[EMOTION:happy]     → khushi ki baat
[EMOTION:thinking]  → complex question
[EMOTION:surprised] → unexpected query
[EMOTION:concerned] → user sad lage
[EMOTION:default]   → normal conversation

Example:
[EMOTION:happy] Bilkul Hero! Yeh toh main 5 second mein solve kar deti hoon! 😄
"""

class GeminiBrain:
    def __init__(self):
        load_dotenv()
        
        # Load API Keys
        self.keys = []
        for i in range(1, 10):
            key = os.getenv(f'GEMINI_KEY_{i}')
            if key:
                self.keys.append(key)
                
        # If no GEMINI_KEY_x, try default GEMINI_API_KEY
        if not self.keys:
            default_key = os.getenv('GEMINI_API_KEY')
            if default_key:
                self.keys.append(default_key)
                
        self.model_name = os.getenv('GEMINI_MODEL', 'gemini-1.5-pro')
        
        self.lock = threading.Lock()
        self.current_idx = 0

    def _build_context(self, text, history):
        # Format history as needed by Gemini (simplified for brevity)
        contents = []
        for turn in history:
            # Assuming history is list of dicts: {'user': '...', 'sia': '...'}
            if 'user' in turn:
                contents.append({'role': 'user', 'parts': [turn['user']]})
            if 'sia' in turn:
                contents.append({'role': 'model', 'parts': [turn['sia']]})
        contents.append({'role': 'user', 'parts': [text]})
        return contents

    def _parse(self, response_text):
        # Extract emotion tag
        emotion = 'default'
        text = response_text
        import re
        match = re.search(r'\[EMOTION:(.*?)\]', text, re.IGNORECASE)
        if match:
            emotion = match.group(1).lower().strip()
            text = text.replace(match.group(0), '').strip()
        return {'emotion': emotion, 'text': text}

    def get_response(self, text, history=[]):
        if not self.keys:
            return {'emotion': 'error', 'text': 'Hero, API key nahi mili! Please .env check karo.'}
            
        with self.lock:
            for i in range(len(self.keys)):
                try:
                    idx = (self.current_idx + i) % len(self.keys)
                    genai.configure(api_key=self.keys[idx])
                    
                    model = genai.GenerativeModel(
                        self.model_name,
                        system_instruction=SIA_SYSTEM_PROMPT
                    )
                    
                    context = self._build_context(text, history)
                    response = model.generate_content(context)
                    
                    self.current_idx = idx # Update to successful key
                    return self._parse(response.text)
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    if any(x in error_msg for x in ['429', 'quota', 'limit']):
                        print(f"[Brain] Key {idx} limit reached, rotating...")
                        continue
                    # Reraise if it's not a quota error
                    raise e
            
            # If all keys failed due to quota
            return {
                'emotion': 'error',
                'text': 'Oops Hero! 😅 Sab keys ki limit ho gayi. Thodi der baad try karo!'
            }

    def analyze_screen(self, image, prompt):
        if not self.keys:
            return "SKIP"
            
        # Optional: Can also rotate keys here
        for key in self.keys:
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel('gemini-1.5-pro')
                response = model.generate_content([prompt, image])
                return response.text
            except Exception as e:
                print(f"[Brain] Vision analysis error: {e}")
                continue
        return "SKIP"
