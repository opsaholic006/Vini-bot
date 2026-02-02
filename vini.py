import os
import asyncio
import edge_tts
import json
import logging
import yt_dlp
import uuid
from telegram import Update, InlineQueryResultAudio
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, InlineQueryHandler

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8544824856:AAF2GxVnKafvoIUBVX7MAmH_gSctr5TcEfk")
OWNER_ID = int(os.getenv("OWNER_ID", "7359097163"))

DATA_DIR = "/app/data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)
USER_FILE = os.path.join(DATA_DIR, "users.json")

settings = {"voice": "hi-IN-SwaraNeural", "rate": "+3%", "pitch": "+2Hz"}
VOICE_LIST = {
    "nezuko": "ja-JP-NanamiNeural", "aoi": "ja-JP-AoiNeural",
    "ana": "en-US-AnaNeural", "aria": "en-US-AriaNeural",
    "swara": "hi-IN-SwaraNeural", "lakshmi": "hi-IN-LakshmiNeural",
    "prabhat": "hi-IN-PrabhatNeural"
}

logging.basicConfig(level=logging.WARNING)

# ---------- FONT STYLER ----------
def style_text(text):
    normal_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    fancy_chars  = "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ0123456789"
    return text.translate(str.maketrans(normal_chars, fancy_chars))

# ---------- DATABASE ----------
def load_users():
    if not os.path.exists(USER_FILE): return {}
    try:
        with open(USER_FILE, "r") as f: return json.load(f)
    except: return {}

def save_user(user):
    if user.is_bot: return 
    users = load_users()
    users[str(user.id)] = f"{user.first_name} (@{user.username if user.username else 'N/A'})"
    with open(USER_FILE, "w") as f: json.dump(users, f)

# ---------- INLINE SEARCH HANDLER ----------

async def inline_sing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    if not query:
        await update.inline_query.answer(
            [], 
            switch_pm_text="🎵 Type song name to search...",
            switch_pm_parameter="start"
        )
        return
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'geo_bypass': True,
        'extract_flat': False, 
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    }
    
    results = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, f"ytsearch5:{query}", download=False)
            if 'entries' in info:
                for entry in info['entries']:
                    results.append(
                        InlineQueryResultAudio(
                            id=entry['id'],
                            audio_url=entry['url'], 
                            title=entry['title'],
                            performer=entry.get('uploader', "Vini Audio")
                        )
                    )
        
        await update.inline_query.answer(results, cache_time=0)
    except Exception as e:
        print(f"Inline Error: {e}")

# ---------- COMMANDS ----------

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user)
    await update.message.reply_text(style_text(f"Hi {update.effective_user.first_name}! Type /help for commands."))

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(style_text("📖 ᴠɪɴɪ ʜᴇʟᴘ\n\n🎤 /ᴠɪɴɪ <ᴛᴇxᴛ>\n🎵 /sɪɴɢ <sᴏɴɢ>\n👑 /ᴏᴡɴᴇʀ\n📜 /ʜᴇʟᴘ"))

async def vini_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return
    text = " ".join(context.args)
    file_name = f"tts_{uuid.uuid4().hex[:5]}.ogg"
    msg = await update.message.reply_text(style_text("🎤 ʀᴇᴄᴏʀᴅɪɴɢ..."))
    try:
        comm = edge_tts.Communicate(text=text, voice=settings["voice"], rate=settings["rate"], pitch=settings["pitch"])
        await comm.save(file_name)
        await update.message.reply_voice(voice=open(file_name, "rb"))
        await msg.delete()
    except: await msg.edit_text(style_text("❌ ᴛᴛs ᴇʀʀᴏʀ."))
    if os.path.exists(file_name): os.remove(file_name)

async def sing_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return
    query = " ".join(context.args)
    status_msg = await update.message.reply_text(style_text(f"🔍 sᴇᴀʀᴄʜɪɴɢ {query}..."))
    file_path = f"song_{uuid.uuid4().hex[:5]}.mp3"
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': file_path,
        'noplaylist': True,
        'quiet': True,
        'geo_bypass': True,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '128'}],
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.extract_info, f"ytsearch1:{query}", download=True)
        await update.message.reply_audio(audio=open(file_path, 'rb'), title=query)
        await status_msg.delete()
    except: await status_msg.edit_text(style_text("❌ ᴇʀʀᴏʀ: sᴏɴɢ ɴᴏᴛ ꜰᴏᴜɴᴅ."))
    if os.path.exists(file_path): os.remove(file_path)

# --- OWNER COMMANDS ---
async def owner_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    await update.message.reply_text(style_text(f"👑 ᴏᴡɴᴇʀ ᴍᴇɴᴜ\n\n/ᴜsᴇʀs\n/ʙʀᴏᴀᴅᴄᴀsᴛ\n/sᴇᴛᴠᴏɪᴄᴇ\n/sᴇᴛʀᴀᴛᴇ\n/sᴇᴛᴘɪᴛᴄʜ\n\nᴄᴜʀʀᴇɴᴛ: {settings['voice']}"))

async def set_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == OWNER_ID and context.args:
        v = context.args[0].lower()
        if v in VOICE_LIST:
            settings["voice"] = VOICE_LIST[v]
            await update.message.reply_text(style_text(f"✅ ᴠᴏɪᴄᴇ sᴇᴛ ᴛᴏ {v}"))

async def set_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == OWNER_ID and context.args:
        settings["rate"] = context.args[0]
        await update.message.reply_text(style_text(f"✅ sᴘᴇᴇᴅ sᴇᴛ ᴛᴏ {settings['rate']}"))

async def set_pitch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == OWNER_ID and context.args:
        settings["pitch"] = context.args[0]
        await update.message.reply_text(style_text(f"✅ ᴘɪᴛᴄʜ sᴇᴛ ᴛᴏ {settings['pitch']}"))

async def users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    u = load_users()
    await update.message.reply_text(style_text(f"📊 ᴜsᴇʀs: {len(u)}\n" + "\n".join([f"• {info}" for info in u.values()])))

async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID or not context.args: return
    m = style_text(f"📢 ᴀɴɴᴏᴜɴᴄᴇᴍᴇɴᴛ:\n\n{' '.join(context.args)}")
    for uid in load_users().keys():
        try: await context.bot.send_message(chat_id=int(uid), text=m)
        except: continue
    await update.message.reply_text(style_text("✅ sᴇɴᴛ."))

# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("vini", vini_cmd))
    app.add_handler(CommandHandler("sing", sing_cmd))
    app.add_handler(CommandHandler("owner", owner_cmd))
    app.add_handler(CommandHandler("setvoice", set_voice))
    app.add_handler(CommandHandler("setrate", set_rate))
    app.add_handler(CommandHandler("setpitch", set_pitch))
    app.add_handler(CommandHandler("users", users_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(InlineQueryHandler(inline_sing)) 
    
    print("🚀 Vini Turbo is running!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
