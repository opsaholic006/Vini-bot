import os
import asyncio
import edge_tts
import json
import logging
import yt_dlp
import uuid

from telegram import (
    Update,
    InlineQueryResultAudio
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    InlineQueryHandler
)

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "7359097163"))

DATA_DIR = "/app/data"
os.makedirs(DATA_DIR, exist_ok=True)
USER_FILE = os.path.join(DATA_DIR, "users.json")

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
def load_users():
    if not os.path.exists(USER_FILE):
        return {}
    try:
        with open(USER_FILE) as f:
            return json.load(f)
    except:
        return {}

def save_user(user):
    if user.is_bot:
        return
    users = load_users()
    users[str(user.id)] = f"{user.first_name} (@{user.username or 'N/A'})"
    with open(USER_FILE, "w") as f:
        json.dump(users, f)

# ---------- INLINE SEARCH (FAST, AUDIO ONLY) ----------
async def inline_sing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.inline_query.query.strip()
    if not q:
        await update.inline_query.answer(
            [],
            switch_pm_text="🎵 Type song name to search...",
            switch_pm_parameter="start"
        )
        return

    results = []

    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True,
        "geo_bypass": True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(
                ydl.extract_info,
                f"ytsearch5:{q}",
                False
            )

        for e in info.get("entries", []):
            if not e:
                continue
            if e.get("duration", 0) > 600:
                continue

            vid = e["id"]
            title = e["title"]

            audio_url = f"https://www.youtube.com/watch?v={vid}"

            results.append(
                InlineQueryResultAudio(
                    id=vid,
                    audio_url=audio_url,
                    title=title,
                    performer=e.get("uploader", "Vini Famous Audio")
                )
            )

        await update.inline_query.answer(results, cache_time=1)

    except:
        await update.inline_query.answer([], cache_time=1)

# ---------- COMMANDS ----------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user)
    await update.message.reply_text(
        style_text(f"Hi {update.effective_user.first_name}! Type /help for commands.")
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        style_text(
            "📖 ᴠɪɴɪ ʜᴇʟᴘ\n\n"
            "🎤 /ᴠɪɴɪ <ᴛᴇxᴛ>\n"
            "🎵 /sɪɴɢ <sᴏɴɢ>\n"
            "👑 /ᴏᴡɴᴇʀ\n"
            "📜 /ʜᴇʟᴘ"
        )
    )

async def vini_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return
    text = " ".join(context.args)
    file = f"tts_{uuid.uuid4().hex}.ogg"
    msg = await update.message.reply_text(style_text("🎤 ʀᴇᴄᴏʀᴅɪɴɢ..."))
    try:
        tts = edge_tts.Communicate(
            text=text,
            voice=settings["voice"],
            rate=settings["rate"],
            pitch=settings["pitch"]
        )
        await tts.save(file)
        await update.message.reply_voice(open(file, "rb"))
        await msg.delete()
    except:
        await msg.edit_text(style_text("❌ ᴛᴛs ᴇʀʀᴏʀ."))
    finally:
        if os.path.exists(file):
            os.remove(file)

# ---------- OWNER ----------
async def owner_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    await update.message.reply_text(
        style_text(
            f"👑 ᴏᴡɴᴇʀ ᴍᴇɴᴜ\n\n"
            f"/ᴜsᴇʀs\n"
            f"/ʙʀᴏᴀᴅᴄᴀsᴛ\n"
            f"/sᴇᴛᴠᴏɪᴄᴇ\n"
            f"/sᴇᴛʀᴀᴛᴇ\n"
            f"/sᴇᴛᴘɪᴛᴄʜ\n\n"
            f"ᴄᴜʀʀᴇɴᴛ: {settings['voice']}"
        )
    )

# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("vini", vini_cmd))
    app.add_handler(CommandHandler("owner", owner_cmd))
    app.add_handler(InlineQueryHandler(inline_sing))

    print("🚀 Vini Turbo is running!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
