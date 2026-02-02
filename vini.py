import os
import asyncio
import edge_tts
import random
import json
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ================= CONFIG =================
BOT_TOKEN = "8544824856:AAF2GxVnKafvoIUBVX7MAmH_gSctr5TcEfk"
OWNER_ID = 7359097163
USER_FILE = "users.json"

# Settings
CURRENT_PITCH = "+2Hz"
VOICE_RATE = "+3%"
CURRENT_VOICE = "hi-IN-SwaraNeural"

VOICE_LIST = {
    "nezuko": "ja-JP-NanamiNeural",
    "aoi": "ja-JP-AoiNeural",
    "ana": "en-US-AnaNeural",
    "aria": "en-US-AriaNeural",
    "swara": "hi-IN-SwaraNeural",
    "lakshmi": "hi-IN-LakshmiNeural",
    "prabhat": "hi-IN-PrabhatNeural"
}

# SILENT LOGGING: Only shows errors, not every request
logging.basicConfig(level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# ---------- DATABASE ----------
def load_users():
    if not os.path.exists(USER_FILE): return {}
    try:
        with open(USER_FILE, "r") as f: return json.load(f)
    except: return {}

def save_user(user):
    users = load_users()
    users[str(user.id)] = f"{user.first_name} (@{user.username if user.username else 'N/A'})"
    with open(USER_FILE, "w") as f: json.dump(users, f)

# ---------- TTS ----------
async def generate_tts(text: str, voice: str, rate: str, pitch: str, file_name: str):
    try:
        communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
        await communicate.save(file_name)
        return True
    except Exception: return False

# ---------- COMMANDS ----------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user)
    await update.message.reply_text(f"Hello {update.effective_user.first_name}! I'm Vini. Use /vini <text> to make me speak.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📖 **Vini Help**\n\n/vini <text> - Convert text to voice\n/start - Restart bot", parse_mode="Markdown")

async def vini_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user)
    if not context.args:
        await update.message.reply_text("Usage: /vini <text>")
        return
    text = " ".join(context.args)
    file_name = f"tts_{update.effective_user.id}.ogg"
    msg = await update.message.reply_text("🎤 Generating...")
    if await generate_tts(text, CURRENT_VOICE, VOICE_RATE, CURRENT_PITCH, file_name):
        await update.message.reply_voice(voice=open(file_name, "rb"))
        await msg.delete()
    else:
        await msg.edit_text("❌ Error generating voice.")
    if os.path.exists(file_name): os.remove(file_name)

# --- OWNER ONLY ---
async def owner_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    dashboard = (
        "👑 **OWNER DASHBOARD**\n\n"
        "📊 `/users` - User List\n"
        "📢 `/broadcast <msg>` - Broadcast\n"
        "⚙️ `/voice <name>` - Set Voice\n"
        "⚙️ `/speed <%>` - Set Speed\n"
        "⚙️ `/pitch <Hz>` - Set Pitch\n\n"
        "Current Voice: `{}`".format(CURRENT_VOICE)
    )
    await update.message.reply_text(dashboard, parse_mode="Markdown")

async def users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    users = load_users()
    list_txt = "\n".join([f"ID: `{uid}` | Name: {info}" for uid, info in users.items()])
    await update.message.reply_text(f"📊 **Total Users:** {len(users)}\n\n{list_txt}", parse_mode="Markdown")

async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID or not context.args: return
    msg = " ".join(context.args)
    users = load_users()
    count = 0
    for uid in users.keys():
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 **Admin Message:**\n\n{msg}")
            count += 1
        except: continue
    await update.message.reply_text(f"✅ Broadcast sent to {count} users.")

async def voice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CURRENT_VOICE
    if update.effective_user.id != OWNER_ID or not context.args: return
    choice = context.args[0].lower()
    if choice in VOICE_LIST:
        CURRENT_VOICE = VOICE_LIST[choice]
        await update.message.reply_text(f"Voice changed to {choice}")

# ---------- ERROR HANDLER ----------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    # Quietly log network errors without crashing or spamming terminal
    pass

# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).connect_timeout(30).read_timeout(30).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("vini", vini_cmd))
    app.add_handler(CommandHandler("owner", owner_cmd))
    app.add_handler(CommandHandler("users", users_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CommandHandler("voice", voice_cmd))
    
    app.add_error_handler(error_handler)

    print("⚡ Vini is Online. Terminal is clean and silent.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

