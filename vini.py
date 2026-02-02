import os
import asyncio
from telegram import (
    Update,
    InlineQueryResultArticle,
    InputTextMessageContent,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    InlineQueryHandler,
    ContextTypes,
)
import yt_dlp

BOT_TOKEN = os.getenv("BOT_TOKEN")

MAX_DURATION = 600  # 10 minutes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot is running.")


# ================= INLINE SEARCH (INSTANT, METADATA ONLY) =================

async def inline_sing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip()
    if not query:
        await update.inline_query.answer([], cache_time=1)
        return

    results = []

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            data = await asyncio.to_thread(
                ydl.extract_info,
                f"ytsearch5:{query}",
                download=False
            )

        for entry in data.get("entries", []):
            duration = entry.get("duration")
            if not duration or duration > MAX_DURATION:
                continue

            video_id = entry.get("id")
            title = entry.get("title")

            results.append(
                InlineQueryResultArticle(
                    id=video_id,
                    title=title,
                    input_message_content=InputTextMessageContent(
                        f"/sing {video_id}"
                    ),
                )
            )

        await update.inline_query.answer(results, cache_time=1)

    except:
        await update.inline_query.answer([], cache_time=1)


# ================= /SING COMMAND (FAST AUDIO ONLY) =================

async def sing_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return

    query = context.args[0]
    os.makedirs("downloads", exist_ok=True)

    ydl_opts = {
        "format": "bestaudio[abr<=64]/bestaudio",
        "outtmpl": "downloads/%(id)s.%(ext)s",
        "quiet": True,
        "noplaylist": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "64",
            }
        ],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(
                ydl.extract_info,
                query,
                download=True
            )

        file_path = f"downloads/{info['id']}.mp3"
        title = info.get("title", "Audio")

        await update.message.reply_audio(
            audio=open(file_path, "rb"),
            title=title
        )

        os.remove(file_path)

    except:
        pass


# ================= MAIN =================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sing", sing_cmd))
    app.add_handler(InlineQueryHandler(inline_sing))

    app.run_polling()


if __name__ == "__main__":
    main()
