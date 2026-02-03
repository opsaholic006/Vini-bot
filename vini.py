import os
import uuid
import logging
import edge_tts
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ================= CONFIG =================
BOT_TOKEN = os.getenv(
    "BOT_TOKEN",
    "8544824856:AAF2GxVnKafvoIUBVX7MAmH_gSctr5TcEfk"
)

OWNER_ID = int(os.getenv("OWNER_ID", "7359097163"))

# Tracking users and per-user settings
VINI_USERS = {}
USER_SETTINGS = {}

# Global TTS defaults
settings = {
    "voice": "en-US-AnaNeural",  # default voice
    "rate": "+3%",
    "pitch": "+2Hz"
}

# Predefined voices
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
    normal_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    fancy_chars  = "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ0123456789"
    return text.translate(str.maketrans(normal_chars, fancy_chars))

# ---------- COMMANDS ----------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        style_text(f"Hi {update.effective_user.first_name}! Use /vini <text>")
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Owner help
    if context.args and context.args[0].lower() == "owner":
        if update.effective_user.id != OWNER_ID:
            return
        await update.message.reply_text(
            style_text(
                "👑 ᴏᴡɴᴇʀ ʜᴇʟᴘ\n\n"
                "/owner\n"
                "• View who is using Vini\n"
                "• Total users count\n\n"
                "/setvoice <voice> - Change TTS voice\n"
                "/setrate <rate> - Change speech speed\n"
                "/setpitch <pitch> - Change speech pitch\n\n"
                "Available voices: " + ", ".join(VOICE_LIST.keys())
            )
        )
        return

    # Regular user help
    await update.message.reply_text(
        style_text(
            "🎤 /ᴠɪɴɪ <ᴛᴇxᴛ>\n🗣️ Converts text to speech\n\n"
            "🛠️ User commands:\n"
            "/setmypitch <pitch> - Change your own pitch for Vini (temporary)"
        )
    )

async def vini_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return

    # Track user
    user = update.effective_user
    VINI_USERS[user.id] = (
        f"{user.first_name} "
        f"(@{user.username})" if user.username else user.first_name
    )

    text = " ".join(context.args)
    file_name = f"tts_{uuid.uuid4().hex[:6]}.ogg"
    msg = await update.message.reply_text(style_text("🎤 ʀᴇᴄᴏʀᴅɪɴɢ..."))

    # Use user-specific pitch if set
    pitch_to_use = USER_SETTINGS.get(user.id, {}).get("pitch", settings["pitch"])

    try:
        comm = edge_tts.Communicate(
            text=text,
            voice=settings["voice"],  # global voice (set by default or owner)
            rate=settings["rate"],
            pitch=pitch_to_use
        )
        await comm.save(file_name)
        await update.message.reply_voice(voice=open(file_name, "rb"))
        await msg.delete()

    except Exception:
        await msg.edit_text(style_text("❌ ᴛᴛs ᴇʀʀᴏʀ."))

    finally:
        if os.path.exists(file_name):
            os.remove(file_name)

# ---------- OWNER COMMANDS ----------
async def owner_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    if not VINI_USERS:
        await update.message.reply_text(
            style_text("👑 ᴏᴡɴᴇʀ\n\nɴᴏ ᴜsᴇʀs ʏᴇᴛ.")
        )
        return

    user_list = "\n".join([f"• {u}" for u in VINI_USERS.values()])
    await update.message.reply_text(
        style_text(
            f"👑 ᴏᴡɴᴇʀ\n\n"
            f"ᴛᴏᴛᴀʟ ᴜsᴇʀs: {len(VINI_USERS)}\n\n"
            f"{user_list}"
        )
    )

async def setvoice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID or not context.args:
        return
    key = context.args[0].lower()
    if key in VOICE_LIST:
        settings["voice"] = VOICE_LIST[key]
        await update.message.reply_text(style_text(f"✅ Voice set to {key}"))
    else:
        await update.message.reply_text(
            style_text("❌ Invalid voice! Available: " + ", ".join(VOICE_LIST.keys()))
        )

async def setrate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID or not context.args:
        return
    settings["rate"] = context.args[0]
    await update.message.reply_text(style_text(f"✅ Rate set to {context.args[0]}"))

async def setpitch_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID or not context.args:
        return
    settings["pitch"] = context.args[0]
    await update.message.reply_text(style_text(f"✅ Pitch set to {context.args[0]}"))

# ---------- USER COMMAND ----------
async def setmypitch_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return
    USER_SETTINGS[update.effective_user.id] = {"pitch": context.args[0]}
    await update.message.reply_text(
        style_text(f"✅ Your pitch is now set to {context.args[0]} for your /vini TTS")
    )

# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Basic commands
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("vini", vini_cmd))

    # Owner commands
    app.add_handler(CommandHandler("owner", owner_cmd))
    app.add_handler(CommandHandler("setvoice", setvoice_cmd))
    app.add_handler(CommandHandler("setrate", setrate_cmd))
    app.add_handler(CommandHandler("setpitch", setpitch_cmd))

    # User-specific commands
    app.add_handler(CommandHandler("setmypitch", setmypitch_cmd))

    print("🚀 Vini TTS is running!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
