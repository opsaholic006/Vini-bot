import os
import asyncio
import edge_tts
import json
import logging
import yt_dlp
import uuid
from collections import deque
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, InlineQueryHandler, MessageHandler, filters

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "7359097163"))

DATA_DIR = "/app/data"
AUDIO_DIR = f"{DATA_DIR}/audio_cache"
CACHE_FILE = f"{DATA_DIR}/cache.json"
USER_FILE = os.path.join(DATA_DIR, "users.json")
STATS_FILE = os.path.join(DATA_DIR, "stats.json")
TRENDING_FILE = os.path.join(DATA_DIR, "trending.json")

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

# ---------- JSON UTILITIES ----------
def load_json(file):
    if not os.path.exists(file):
        return {}
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return {}

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

# ---------- USER DATABASE ----------
def load_users():
    return load_json(USER_FILE)

def save_user(user):
    if user.is_bot:
        return
    users = load_users()
    users[str(user.id)] = f"{user.first_name} (@{user.username or 'N/A'})"
    save_json(USER_FILE, users)

# ---------- STATS ----------
def update_stats(action, key=None):
    stats = load_json(STATS_FILE)
    stats.setdefault("searches", {})
    stats.setdefault("cache_hits", 0)
    stats.setdefault("total_requests", 0)
    stats["total_requests"] += 1
    if action == "search" and key:
        stats["searches"][key] = stats["searches"].get(key, 0) + 1
    elif action == "cache_hit":
        stats["cache_hits"] += 1
    save_json(STATS_FILE, stats)

# ---------- AUDIO CACHE ----------
CACHE = load_json(CACHE_FILE)

def get_cached_audio(video_id):
    entry = CACHE.get(video_id)
    if entry:
        if "file_id" in entry:
            return entry["file_id"]
        if os.path.exists(entry.get("path","")):
            return entry["path"]
    return None

def set_cached_audio(video_id, file_id=None):
    CACHE[video_id] = {"file_id": file_id, "path": f"{AUDIO_DIR}/{video_id}.mp3"}
    save_json(CACHE_FILE, CACHE)

# ---------- PRIORITY DOWNLOAD QUEUE ----------
download_queue = deque()
download_lock = asyncio.Lock()
MAX_WORKERS = 4

async def download_worker():
    while True:
        await asyncio.sleep(0.1)
        async with download_lock:
            if download_queue:
                video_id = download_queue.popleft()
                await fetch_audio_parallel(video_id)

async def enqueue_download(video_id):
    async with download_lock:
        if video_id not in download_queue and not get_cached_audio(video_id):
            download_queue.append(video_id)

# ---------- AUDIO DOWNLOAD ----------
async def fetch_audio_parallel(video_id):
    if get_cached_audio(video_id):
        return
    temp_file = f"{uuid.uuid4().hex}.mp3"
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        "format":"bestaudio[abr<=64]/bestaudio",
        "outtmpl":temp_file,
        "quiet":True,
        "noplaylist":True,
        "postprocessors":[{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"64"}]
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
        audio_path = f"{AUDIO_DIR}/{video_id}.mp3"
        os.rename(temp_file, audio_path)
        set_cached_audio(video_id)
    except:
        if os.path.exists(temp_file):
            os.remove(temp_file)

# ---------- TRENDING PRELOAD ----------
async def preload_trending():
    ydl_opts = {"quiet": True, "extract_flat": True, "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, "https://www.youtube.com/feed/trending", False)
        trending = info.get("entries", [])[:10]
        save_json(TRENDING_FILE, trending)
        for e in trending:
            vid = e["id"]
            await enqueue_download(vid)
    except:
        pass

# ---------- INLINE SEARCH ----------
async def inline_sing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.inline_query.query.strip()
    if not q:
        await update.inline_query.answer([], switch_pm_text="Type song name to search...", switch_pm_parameter="start")
        return
    update_stats("search", key=q.lower())
    results = []
    ydl_opts = {"quiet": True, "extract_flat": True, "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, f"ytsearch10:{q}", False)
        for e in info.get("entries", []):
            if not e or e.get("duration", 0) > 600:
                continue
            vid = e["id"]
            title = e["title"]
            results.append(InlineQueryResultArticle(
                id=vid,
                title=title,
                description="Tap to play",
                input_message_content=InputTextMessageContent(f"ID:{vid}")
            ))
            await enqueue_download(vid)
        await update.inline_query.answer(results, cache_time=1)
    except:
        await update.inline_query.answer([], cache_time=1)

# ---------- AUDIO HANDLER ----------
async def audio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    if "ID:" not in text:
        return
    video_id = text.split("ID:")[-1].strip()
    cached_file = get_cached_audio(video_id)
    if cached_file:
        if os.path.exists(cached_file):
            audio = open(cached_file, "rb")
        else:
            audio = cached_file
        msg = await update.message.reply_audio(audio=audio)
        if os.path.exists(cached_file):
            set_cached_audio(video_id, file_id=msg.audio.file_id)
        update_stats("cache_hit")
        return
    msg = await update.message.reply_text("Fetching audio...")
    await enqueue_download(video_id)
    # Wait up to 6 seconds
    for _ in range(6):
        await asyncio.sleep(1)
        cached_file = get_cached_audio(video_id)
        if cached_file:
            if os.path.exists(cached_file):
                audio = open(cached_file, "rb")
            else:
                audio = cached_file
            msg2 = await update.message.reply_audio(audio=audio)
            if os.path.exists(cached_file):
                set_cached_audio(video_id, file_id=msg2.audio.file_id)
            await msg.delete()
            return
    await msg.edit_text("Audio fetching failed.")

# ---------- TTS ----------
async def vini_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return
    text = " ".join(context.args)
    file = f"{uuid.uuid4().hex}.ogg"
    msg = await update.message.reply_text("Recording...")
    try:
        tts = edge_tts.Communicate(text=text, voice=settings["voice"], rate=settings["rate"], pitch=settings["pitch"])
        await tts.save(file)
        await update.message.reply_voice(open(file, "rb"))
        await msg.delete()
    except:
        await msg.edit_text("TTS failed.")
    finally:
        if os.path.exists(file):
            os.remove(file)

# ---------- COMMANDS ----------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user)
    await update.message.reply_text(f"Hi {update.effective_user.first_name}! Type /help for commands.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/vini <text> - Convert text to voice\nInline search - Search & play songs\n/owner - Owner menu")

async def owner_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    stats = load_json(STATS_FILE)
    total_requests = stats.get("total_requests", 0)
    cache_hits = stats.get("cache_hits", 0)
    await update.message.reply_text(f"Owner menu:\nTotal requests: {total_requests}\nCache hits: {cache_hits}\nCurrent voice: {settings['voice']}")

# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("vini", vini_cmd))
    app.add_handler(CommandHandler("owner", owner_cmd))
    app.add_handler(InlineQueryHandler(inline_sing))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, audio_handler))

    loop = asyncio.get_event_loop()
    for _ in range(MAX_WORKERS):
        loop.create_task(download_worker())
    # Preload trending songs
    loop.run_until_complete(preload_trending())

    print("Vini Turbo running ultra fast with preloaded trending songs + multi-worker downloads + Telegram CDN caching + all previous features!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
