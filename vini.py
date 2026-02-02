import os
import asyncio
import edge_tts
import json
import logging
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8544824856:AAF2GxVnKafvoIUBVX7MAmH_gSctr5TcEfk")
OWNER_ID = int(os.getenv("OWNER_ID", "7359097163"))

DATA_DIR = "/app/data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)
USER_FILE = os.path.join(DATA_DIR, "users.json")

CURRENT_PITCH = "+2Hz"
VOICE_RATE = "+3%"
CURRENT_VOICE = "hi-IN-SwaraNeural"

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

# ---------- COMMANDS ----------

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user)
    await update.message.reply_text(f"Hi {update.effective_user.first_name}! I'm Vini. Type /help to see my commands.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *Vini Help Menu*\n\n"
        "🎤 `/vini <text>` - Text to Voice\n"
        "🎵 `/sing <song>` - Get music\n"
        "👑 `/owner` - Owner settings\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def vini_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user)
    if not context.args:
        await update.message.reply_text("Usage: `/vini hello`", parse_mode="Markdown")
        return
    text = " ".join(context.args)
    file_name = f"tts_{update.effective_user.id}.ogg"
    msg = await update.message.reply_text("🎤 Recording...")
    communicate = edge_tts.Communicate(text=text, voice=CURRENT_VOICE, rate=VOICE_RATE, pitch=CURRENT_PITCH)
    await communicate.save(file_name)
    await update.message.reply_voice(voice=open(file_name, "rb"))
    await msg.delete()
    if os.path.exists(file_name): os.remove(file_name)

async def sing_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: `/sing song name`")
        return
    query = " ".join(context.args)
    status_msg = await update.message.reply_text(f"🔍 Searching for `{query}`...", parse_mode="Markdown")
    file_path = f"song_{update.effective_user.id}.mp3"
    ydl_opts = {
        'format': 'bestaudio/best',
        'default_search': 'ytsearch1',
        'outtmpl': file_path,
        'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([query])
        await update.message.reply_voice(voice=open(file_path, 'rb'))
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text("❌ Error downloading song.")
    if os.path.exists(file_path): os.remove(file_path)

async def owner_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    await update.message.reply_text("👑 *Owner Menu*\n/users - List users\n/broadcast - Message all", parse_mode="Markdown")

async def users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    users = load_users()
    list_txt = "\n".join([f"• {info}" for uid, info in users.items()])
    await update.message.reply_text(f"📊 *Users:* {len(users)}\n{list_txt}", parse_mode="Markdown")

async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID or not context.args: return
    msg = " ".join(context.args)
    users = load_users()
    for uid in users.keys():
        try: await context.bot.send_message(chat_id=uid, text=msg)
        except: continue
    await update.message.reply_text("✅ Sent.")

# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("vini", vini_cmd))
    app.add_handler(CommandHandler("sing", sing_cmd))
    app.add_handler(CommandHandler("owner", owner_cmd))
    app.add_handler(CommandHandler("users", users_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))

    print("⚡ Vini Cloud is Live!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
