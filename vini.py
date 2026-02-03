import sys
import traceback

def excepthook(exc_type, exc, tb):
    print("UNCAUGHT EXCEPTION:", file=sys.stderr)
    traceback.print_exception(exc_type, exc, tb)

sys.excepthook = excepthook

import os
import json
import asyncio
from telegram import (
    Update,
    InlineQueryResultAudio,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    InlineQueryHandler,
)
from redis.asyncio import from_url as redis_from_url

from config import BOT_TOKEN, OWNER_ID, TTS_SETTINGS
from style import style_text
from utils import load_json, save_json, retry
from audio import download_audio

# ---------------- REDIS (PRIMARY) ----------------
REDIS_URL = os.getenv("REDIS_URL")
rdb = redis_from_url(REDIS_URL, decode_responses=True) if REDIS_URL else None

# ---------------- JSON FALLBACK ----------------
DATA_DIR = "/app/data"
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = f"{DATA_DIR}/users.json"
FILEID_FILE = f"{DATA_DIR}/file_ids.json"
BROKEN_FILE = f"{DATA_DIR}/broken.json"

users_json = load_json(USERS_FILE, [])
fileid_json = load_json(FILEID_FILE, {})
broken_json = load_json(BROKEN_FILE, [])

# ---------------- HELPERS ----------------
async def add_user(uid: int):
    if rdb:
        await rdb.sadd("users", uid)
    if uid not in users_json:
        users_json.append(uid)
        save_json(USERS_FILE, users_json)

def is_broken(query: str) -> bool:
    return query in broken_json

def mark_broken(query: str):
    if query not in broken_json:
        broken_json.append(query)
        save_json(BROKEN_FILE, broken_json)

def search_cached_audio(query: str, limit: int = 10):
    q = query.lower()
    results = []

    for key, fid in fileid_json.items():
        if q in key:
            results.append((key, fid))
            if len(results) >= limit:
                break

    return results

# ---------------- COMMANDS ----------------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await add_user(update.effective_user.id)
    await update.message.reply_text(
        style_text("Send /sing <song name> to get music")
    )

# ---------- SING ----------
async def sing_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await add_user(update.effective_user.id)

    query = " ".join(context.args).strip()
    if not query:
        return await update.message.reply_text("Usage: /sing <song name>")

    qkey = query.lower()

    if is_broken(qkey):
        return await update.message.reply_text("This song is temporarily unavailable.")

    # CDN reuse
    if rdb:
        fid = await rdb.get(f"audio:{qkey}")
        if fid:
            return await update.message.reply_audio(fid)

    if qkey in fileid_json:
        return await update.message.reply_audio(fileid_json[qkey])

    msg = await update.message.reply_text("Fetching audio...")

    try:
        path = await retry(lambda: asyncio.to_thread(download_audio, query), retries=3)

        sent = await update.message.reply_audio(
            audio=open(path, "rb"),
            title=query
        )

        fid = sent.audio.file_id

        if rdb:
            await rdb.set(f"audio:{qkey}", fid)
        fileid_json[qkey] = fid
        save_json(FILEID_FILE, fileid_json)

        os.remove(path)
        await msg.delete()

    except Exception:
        mark_broken(qkey)
        await msg.edit_text("Audio fetching failed.")

# ---------- STATS ----------
async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    redis_users = await rdb.scard("users") if rdb else 0
    total_users = max(redis_users, len(users_json))
    total_cache = len(fileid_json)

    text = (
        f"Users: {total_users}\n"
        f"Cached Tracks: {total_cache}\n"
        f"Broken Queries: {len(broken_json)}"
    )
    await update.message.reply_text(text)

# ==========INLINE HANDLER (CACHE-ONLY)=========
async def inline_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip().lower()

    if not query:
        return

    await add_user(update.inline_query.from_user.id)

    results = []

    # Redis-first (fastest)
    if rdb:
        keys = await rdb.keys("audio:*")
        for k in keys:
            song = k.replace("audio:", "")
            if query in song:
                fid = await rdb.get(k)
                if fid:
                    results.append(
                        InlineQueryResultAudio(
                            id=f"{song}:{fid}",
                            audio_file_id=fid,
                            title=song.title()
                        )
                    )
            if len(results) >= 10:
                break

    # JSON fallback
    if not results:
        for song, fid in search_cached_audio(query):
            results.append(
                InlineQueryResultAudio(
                    id=f"{song}:{fid}",
                    audio_file_id=fid,
                    title=song.title()
                )
            )

    # IMPORTANT: no results = no answer
    if results:
        await update.inline_query.answer(
            results,
            cache_time=3600,
            is_personal=False
        )

# ---------- BROADCAST ----------
async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    text = " ".join(context.args)
    if not text:
        return await update.message.reply_text("Usage: /broadcast <message>")

    users = set(users_json)
    if rdb:
        users |= {int(u) for u in await rdb.smembers("users")}

    sent = 0
    for uid in users:
        try:
            await context.bot.send_message(uid, text)
            sent += 1
        except:
            continue

    await update.message.reply_text(f"Broadcast sent to {sent} users")

# ---------- OWNER TTS CONTROLS ----------
async def setvoice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    TTS_SETTINGS["voice"] = " ".join(context.args)
    await update.message.reply_text("Voice updated")

async def setrate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    TTS_SETTINGS["rate"] = " ".join(context.args)
    await update.message.reply_text("Rate updated")

async def setpitch_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    TTS_SETTINGS["pitch"] = " ".join(context.args)
    await update.message.reply_text("Pitch updated")

# ---------------- APP ----------------
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start_cmd))
app.add_handler(CommandHandler("sing", sing_cmd))
app.add_handler(CommandHandler("stats", stats_cmd))
app.add_handler(CommandHandler("broadcast", broadcast_cmd))
app.add_handler(CommandHandler("setvoice", setvoice_cmd))
app.add_handler(CommandHandler("setrate", setrate_cmd))
app.add_handler(CommandHandler("setpitch", setpitch_cmd))
app.add_handler(InlineQueryHandler(inline_music))

app.run_polling()
