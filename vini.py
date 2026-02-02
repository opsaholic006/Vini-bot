import os
import asyncio
import edge_tts
import json
import logging
import yt_dlp
import uuid
from datetime import datetime

from telegram import (
    Update,
    InlineQueryResultArticle,
    InputTextMessageContent
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    InlineQueryHandler,
    MessageHandler,
    filters
)

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "7359097163"))

DATA_DIR = "/app/data"
AUDIO_DIR = f"{DATA_DIR}/audio_cache"
SEARCH_CACHE_FILE = f"{DATA_DIR}/search_cache.json"
TRENDING_FILE = f"{DATA_DIR}/trending.json"
USER_FILE = os.path.join(DATA_DIR, "users.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

settings = {"voice": "hi-IN-SwaraNeural", "rate": "+3%", "pitch": "+2Hz"}

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

# ---------- FONT STYLER ----------
def style_text(text):
    normal = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    fancy  = "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ0123456789"
    return text.translate(str.maketrans(normal, fancy))

# ---------- DATABASE ----------
def load_json(file_path):
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except:
        return {}

def save_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f)

def load_users():
    return load_json(USER_FILE)

def save_user(user):
    if user.is_bot:
        return
    users = load_users()
    users[str(user.id)] = f"{user.first_name} (@{user.username or 'N/A'})"
    save_json(USER_FILE, users)

# ---------- SEARCH CACHE ----------
SEARCH_CACHE = load_json(SEARCH_CACHE_FILE)
TRENDING = load_json(TRENDING_FILE)

# Helper to save search cache safely
def update_search_cache(query, results):
    SEARCH_CACHE[query.lower()] = results
    save_json(SEARCH_CACHE_FILE, SEARCH_CACHE)

# ---------- INLINE SEARCH ----------
async def inline_sing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip()
    if not query:
        await update.inline_query.answer([], switch_pm_text="Type song name...", switch_pm_parameter="start")
        return

    results = []

    # Serve trending results if query is empty or exact match cached
    cache_key = query.lower()
    if cache_key in SEARCH_CACHE:
        for e in SEARCH_CACHE[cache_key]:
            results.append(
                InlineQueryResultArticle(
                    id=e["id"],
                    title=e["title"],
                    description="Tap to play (cached)",
                    input_message_content=InputTextMessageContent(f"Audio fetching...\nID:{e['id']}")
                )
            )
        await update.inline_query.answer(results, cache_time=1)
        return

    # Otherwise search YouTube
    ydl_opts = {"quiet": True, "extract_flat": True, "skip_download": True}
    collected = []

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, f"ytsearch10:{query}", False)

        for e in info.get("entries", []):
            if not e or e.get("duration", 0) > 600:
                continue
            vid = e["id"]
            title = e["title"]
            collected.append({"id": vid, "title": title})

            results.append(
                InlineQueryResultArticle(
                    id=vid,
                    title=title,
                    description="Tap to play",
                    input_message_content=InputTextMessageContent(f"Audio fetching...\nID:{vid}")
                )
            )

        if collected:
            update_search_cache(query, collected)

        await update.inline_query.answer(results, cache_time=1)

    except Exception as e:
        await update.inline_query.answer([], cache_time=1)

# ---------- AUDIO HANDLER ----------
async def audio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    if "ID:" not in text:
        return

    video_id = text.split("ID:")[-1].strip()
    audio_path = f"{AUDIO_DIR}/{video_id}.mp3"

    if os.path.exists(audio_path):
        await update.message.reply_audio(audio=open(audio_path, "rb"), title="Vini Audio", performer="Vini Turbo")
        return

    msg = await update.message.reply_text(style_text("Fetching audio..."))

    temp_file = f"{uuid.uuid4().hex}.mp3"
    url = f"https://www.youtube.com/watch?v={video_id}"

    ydl_opts = {
        "format": "bestaudio",
        "outtmpl": temp_file,
        "quiet": True,
        "noplaylist": True,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}]
    }

    try:
        # Retry once if fails
        for attempt in range(2):
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    await asyncio.to_thread(ydl.download, [url])
                break
            except:
                if attempt == 1:
                    raise

        os.rename(temp_file, audio_path)
        await update.message.reply_audio(audio=open(audio_path, "rb"), title="Vini Audio", performer="Vini Turbo")
        await msg.delete()

    except:
        await msg.edit_text(style_text("Audio fetching failed, please try again"))

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

# ---------- TTS ----------
async def vini_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return
    text = " ".join(context.args)
    file = f"tts_{uuid.uuid4().hex}.ogg"
    msg = await update.message.reply_text(style_text("Recording..."))
    try:
        tts = edge_tts.Communicate(text=text, voice=settings["voice"], rate=settings["rate"], pitch=settings["pitch"])
        await tts.save(file)
        await update.message.reply_voice(open(file, "rb"))
        await msg.delete()
    except:
        await msg.edit_text(style_text("TTS error"))
    finally:
        if os.path.exists(file):
            os.remove(file)

# ---------- COMMANDS ----------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user)
    await update.message.reply_text(style_text(f"Hi {update.effective_user.first_name}! Type /help for commands."))

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        style_text("Vini Bot Help\n\n"
                   "/vini <text> - Text to speech\n"
                   "Inline search - Search songs\n"
                   "/owner - Owner menu\n"
                   "/help - Show this help")
    )

async def owner_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    await update.message.reply_text(
        style_text(f"Owner Menu\n"
                   f"/users\n"
                   f"/broadcast\n"
                   f"/setvoice\n"
                   f"/setrate\n"
                   f"/setpitch\n"
                   f"Current voice: {settings['voice']}")
    )

# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("vini", vini_cmd))
    app.add_handler(CommandHandler("owner", owner_cmd))
    app.add_handler(InlineQueryHandler(inline_sing))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, audio_handler))
    print("Vini Turbo running")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
