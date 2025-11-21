import os
import tempfile
import asyncio
import re # <-- စောင့်ဆိုင်းရမည့်အချိန်ကို စာသားမှ တွက်ထုတ်ရန်
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import ContextTypes
import google.generativeai as genai

from src.services.gemini import get_gemini_response, get_explanation
from src.utils.audio import convert_ogg_to_mp3
from src.utils.state import is_bot_active
from src.config import ADMIN_IDS

# /start command handler (အပြည့်အစုံ)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🙏 <b>မင်္ဂလာပါ! (Sawadee Krub/Ka)</b>\n\n"
        "ကျွန်တော်က ထိုင်း-မြန်မာ အပြန်အလှန် ဘာသာပြန် Bot ပါ။\n"
        "Google Gemini 2.5 Flash နည်းပညာကို သုံးထားပါတယ်။\n\n"
        "👉 <b>အသုံးပြုနည်း:</b>\n"
        "1. ထိုင်း/မြန်မာ စာသား ရိုက်ပို့ပါ။\n"
        "2. 🎤 <b>အသံဖိုင် (Voice Msg)</b> ပို့ပြီးလည်း မေးနိုင်ပါသည်။\n"
        "3. Admin များသည် /admin ဖြင့် ထိန်းချုပ်နိုင်ပါသည်။\n\n"
        "---"
        "✨ <b>Developed by @MyanmarTecharea</b>"
    )
    await update.message.reply_text(welcome_text, parse_mode=constants.ParseMode.HTML)


# Core function to handle request logic with Retries and User Notification
# Text နှင့် Voice handler နှစ်ခုလုံးက ဒီ function ကိုပဲ ခေါ်ပါမယ်။
async def _process_and_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, user_input, is_audio=False):
    MAX_RETRIES = 2 # အများဆုံး ၂ ကြိမ် ပြန်ကြိုးစားပါမယ်
    RETRY_DELAY = 10 # ပုံမှန်စောင့်ဆိုင်းချိန်
    
    # 1. Initial typing indicator
    await update.message.reply_chat_action(action=constants.ChatAction.TYPING if not is_audio else constants.ChatAction.RECORD_AUDIO)
    
    for attempt in range(MAX_RETRIES):
        response_text = await asyncio.to_thread(get_gemini_response, user_input, is_audio)
        
        # 2. Check for Quota Error in the response text
        if "Quota exceeded" in response_text and "AI Error" in response_text:
            
            # 3. Parse the retry delay time from the error string
            wait_time = RETRY_DELAY
            match = re.search(r'Please retry in ([\d\.]+)s\.', response_text)
            if match:
                try:
                    # Parse the time and add 1 second buffer
                    wait_time = int(float(match.group(1))) + 1 
                except ValueError:
                    pass # Use default 10s if parsing fails

            # 4. Final attempt check
            if attempt < MAX_RETRIES - 1:
                # Notify user and wait
                wait_message = f"⏳ စနစ်ရဲ့ Quota ပြည့်နေလို့ ခေတ္တ စောင့်ဆိုင်းနေပါတယ်။ {wait_time} စက္ကန့်အတွင်း (ကြိုးစားမှု {attempt + 1}/{MAX_RETRIES}) ပြန်လည် ကြိုးစားပါမယ်။"
                
                # Send the waiting message 
                await update.message.reply_text(wait_message, parse_mode=constants.ParseMode.HTML) 
                
                # Wait asynchronously
                await asyncio.sleep(wait_time) 
                # After waiting, the loop continues to the next attempt
                continue 
            else:
                # Final failure message
                final_error = "⛔️ ခွင့်ပြုထားသော စောင့်ဆိုင်းချိန်အတွင်း Quota ပြန်မရသေးပါ။ ခဏနေမှ ထပ်မံ ကြိုးစားပေးပါ။"
                await update.message.reply_text(final_error)
                return # Exit the function after final failure
        
        # 5. Success (or non-retryable error)
        
        # Save context (Only needed for successful text or voice)
        context.user_data['last_query'] = user_input if not is_audio else "Voice Input" 
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 အသေးစိတ်ရှင်းပြပါ", callback_data="explain")]
        ])
        
        # Determine the prefix based on input type
        prefix = "🎤 <b>အသံဖိုင် အဖြေ:</b>\n\n" if is_audio else ""
        
        await update.message.reply_text(f"{prefix}{response_text}", reply_markup=keyboard, parse_mode=constants.ParseMode.HTML)
        return # Success, exit the loop


# Original handle_text modified to call the new core processor
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check Maintenance Mode
    if not is_bot_active() and update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⚠️ Bot ကို ခေတ္တ ပြုပြင်မွမ်းမံနေပါသည်။")
        return

    user_text = update.message.text
    # Call the core processing function
    await _process_and_reply(update, context, user_text, is_audio=False)


# Original handle_voice modified to include the processor and clean up logic
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_bot_active() and update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⚠️ Bot ကို ခေတ္တ ပြုပြင်မွမ်းမံနေပါသည်။")
        return

    # Call the core function to handle the typing indicator and processing
    
    try:
        voice_file = await update.message.voice.get_file()
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            ogg_path = os.path.join(tmp_dir, "voice.ogg")
            mp3_path = os.path.join(tmp_dir, "voice.mp3")
            
            await voice_file.download_to_drive(ogg_path)
            
            # Convert
            if convert_ogg_to_mp3(ogg_path, mp3_path):
                gemini_file = genai.upload_file(mp3_path, mime_type="audio/mp3")
                
                # Process with retry logic
                await _process_and_reply(update, context, gemini_file, is_audio=True)
                
            else:
                await update.message.reply_text("Error processing audio.")
            
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

# Callback Handler (Remains the same)
async def user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # Ignore if it's admin callback
    if query.data.startswith("admin_"):
        return 

    await query.answer()
    
    if query.data == "explain":
        last_text = context.user_data.get('last_query')
        if last_text:
            await query.message.reply_text("⏳ ဆင်တူရိုးမှားများနှင့် သဒ္ဒါကို ရှာဖွေနေပါသည်...")
            explanation = await asyncio.to_thread(get_explanation, last_text)
            await query.message.reply_text(f"📖 <b>ရှင်းလင်းချက်:</b>\n\n{explanation}", parse_mode=constants.ParseMode.HTML)
        else:
            await query.message.reply_text("ဒေတာ ဟောင်း မရှိတော့ပါ။")
