import os
import asyncio
import json
import logging
import uuid
import yt_dlp
import edge_tts

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
    ChosenInlineResultHandler
)

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "7359097163"))

DATA_DIR = "/app/data"
os.makedirs(DATA_DIR, exist_ok=True)
USER_FILE = os.path.join(DATA_DIR, "users.json")

logging.basicConfig(level=logging.WARNING)

# ---------- FONT STYLER ----------
def style_text(text):
    normal = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    fancy  = "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ0123456789"
    return text.translate(str.maketrans(normal, fancy))

# ---------- USERS ----------
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
    users[str(user.id)] = user.first_name
    with open(USER_FILE, "w") as f:
        json.dump(users, f)

# ---------- INLINE SEARCH (FAST) ----------
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
        "skip_download": True,
        "extract_flat": True,
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

            vid = e.get("id")
            title = e.get("title")

            results.append(
                InlineQueryResultArticle(
                    id=vid,
                    title=title,
                    description="🎧 Tap to play (fast)",
                    input_message_content=InputTextMessageContent("🎵 Fetching audio..."),
                )
            )

        await update.inline_query.answer(results, cache_time=1)

    except:
        await update.inline_query.answer([], cache_time=1)

# ---------- INLINE CLICK HANDLER ----------
async def chosen_inline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vid = update.chosen_inline_result.result_id
    chat_id = update.chosen_inline_result.from_user.id

    file = f"/tmp/{vid}.mp3"

    ydl_opts = {
        "format": "bestaudio[abr<=48]/bestaudio",
        "outtmpl": file,
        "noplaylist": True,
        "quiet": True,
        "geo_bypass": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "48"
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(
                ydl.extract_info,
                f"https://www.youtube.com/watch?v={vid}",
                True
            )

        await context.bot.send_audio(
            chat_id=chat_id,
            audio=open(file, "rb"),
            title="🎵 Music"
        )

    except Exception as e:
        await context.bot.send_message(
            chat_id=chat_id,
            text=style_text("❌ Failed to fetch audio.")
        )

    finally:
        if os.path.exists(file):
            os.remove(file)

# ---------- COMMANDS ----------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user)
    await update.message.reply_text(
        style_text("Hi! 🎧 Use inline mode to search music.")
    )

# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(InlineQueryHandler(inline_sing))
    app.add_handler(ChosenInlineResultHandler(chosen_inline))

    print("🚀 Vini Turbo is running!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

