import os
from dotenv import load_dotenv

load_dotenv()

# Key များနှင့် Token များကို Environment Variables မှ တိုက်ရိုက်ယူပါမည်။
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ADMIN_IDS ကို စာရင်း (List) အဖြစ် ပြောင်းလဲခြင်း
admin_env = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in admin_env.split(",") if x.strip()]
