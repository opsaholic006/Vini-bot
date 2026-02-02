import os
import asyncio
import edge_tts
import random
import json
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ================= CONFIG =================
# We use Environment Variables for Railway security
BOT_TOKEN = os.getenv("BOT_TOKEN", "8544824856:AAF2GxVnKafvoIUBVX7MAmH_gSctr5TcEfk")
OWNER_ID = int(os.getenv("OWNER_ID", "7359097163"))

# Path for Railway Persistent Volume
DATA_DIR = "/app/data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)
USER_FILE = os.path.join(DATA_DIR, "users.json")

# Default Settings
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

logging.basicConfig(level=logging.WARNING)

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
    await update.message.reply_text(f"Hello {update.effective_user.first_name}! Vini is now running on Railway Cloud ☁️.")

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

async def owner_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    await update.message.reply_text("👑 **Owner Dashboard Active**\n/users | /broadcast | /voice", parse_mode="Markdown")

async def users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    users = load_users()
    list_txt = "\n".join([f"ID: `{uid}` | Name: {info}" for uid, info in users.items()])
    await update.message.reply_text(f"📊 **Users:** {len(users)}\n\n{list_txt}", parse_mode="Markdown")

async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID or not context.args: return
    msg = " ".join(context.args)
    users = load_users()
    for uid in users.keys():
        try: await context.bot.send_message(chat_id=uid, text=f"📢 **Admin Message:**\n\n{msg}")
        except: continue
    await update.message.reply_text("✅ Sent.")

# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("vini", vini_cmd))
    app.add_handler(CommandHandler("owner", owner_cmd))
    app.add_handler(CommandHandler("users", users_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    
    print("⚡ Vini Cloud is starting...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

