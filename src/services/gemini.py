import google.generativeai as genai
from src.config import GEMINI_API_KEY
import logging

# ---------------------------------------------------------
# 1. MODEL CONFIGURATION (Free Tier Fix)
# ---------------------------------------------------------

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    try:
        # FREE TIER MODEL: gemini-2.5-flash ကို အမြဲတမ်းသုံးရန် သတ်မှတ်
        model = genai.GenerativeModel('gemini-2.5-flash') 
    except Exception as e:
        logging.error(f"Failed to initialize Gemini model: {e}")
        model = None 
else:
    logging.error("GEMINI_API_KEY is missing!")
    model = None

# ---------------------------------------------------------
# 2. GEMINI INTELLIGENCE LAYER (Prompt Optimized for Speed)
# ---------------------------------------------------------
def get_gemini_response(user_input, is_audio=False):
    if not model:
        return "⚠️ AI စနစ် မချိတ်ဆက်နိုင်ပါ။ API Key ကို စစ်ဆေးပါ။"
        
    try:
        # System Prompt: Defining the Persona and Logic
        base_prompt = """
        You are an expert Thai-Myanmar Dictionary Bot. Your goal is to provide fast, accurate translations and explanations usable by both native Thai and native Myanmar speakers.
        
        INSTRUCTIONS:
        1. Analyze the input (Text or Audio).
        2. Auto-detect the language.
        
        CONDITION A: If input is THAI:
            - Translate to Myanmar naturally.
            - Provide Definition.

        CONDITION B: If input is MYANMAR:
            - Translate to THAI.
            - **CRITICAL**: Provide "Romanization" (English pronunciation) for the Thai output.
              Example: "ไปไหน" -> (Pai Nai)
        
        FORMAT YOUR RESPONSE EXACTLY LIKE THIS (Use HTML for bolding):
        
        🇹🇭 <b>Thai:</b> [Thai Script] [Romanization if translated from Myanmar]
        🇲🇲 <b>Myanmar:</b> [Myanmar Script]
        📚 <b>Definition:</b> [Brief meaning/Context]
        
        (If explaining grammar or responding to "Explain", be detailed.)
        """
        
        if is_audio:
            response = model.generate_content([base_prompt, user_input])
        else:
            response = model.generate_content(f"{base_prompt}\n\nUser Input: {user_input}")
            
        return response.text
    except Exception as e:
        return f"⚠️ AI Error: {e}"

def get_explanation(word):
    if not model:
        return "ရှင်းပြချက် ရယူမရနိုင်ပါ။ AI စနစ် ချိတ်ဆက်ထားခြင်းမရှိပါ။"
        
    try:
        # 🌟 FIX: Message Too Long Error ဖြေရှင်းရန် စာလုံးရေ ၅၀၀ သာ အများဆုံးထုတ်ရန် ကန့်သတ်ခြင်း
        prompt = f"Explain the grammar, usage, and provide 3 similar words for: '{word}'. Limit the entire explanation to a maximum of 500 characters. Language context: Thai-Myanmar."
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return "ရှင်းပြချက် ရယူမရနိုင်ပါ။"
