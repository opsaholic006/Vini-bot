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

# >>> ADDED
OWNER_ID = int(os.getenv("OWNER_ID", "7359097163"))
VINI_USERS = {}
# <<< ADDED

settings = {
    "voice": "hi-IN-SwaraNeural",
    "rate": "+3%",
    "pitch": "+2Hz"
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
    if context.args and context.args[0].lower() == "owner":
        if update.effective_user.id != OWNER_ID:
            return
        await update.message.reply_text(
            style_text(
                "👑 ᴏᴡɴᴇʀ ʜᴇʟᴘ\n\n"
                "/owner\n"
                "• View who is using Vini\n"
                "• Total users count"
            )
        )
        return

    await update.message.reply_text(
        style_text("🎤 /ᴠɪɴɪ <ᴛᴇxᴛ>\n🗣️ Converts text to speech")
    )

async def vini_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return

    # >>> ADDED (user tracking)
    user = update.effective_user
    VINI_USERS[user.id] = (
        f"{user.first_name} "
        f"(@{user.username})" if user.username else user.first_name
    )
    # <<< ADDED

    text = " ".join(context.args)
    file_name = f"tts_{uuid.uuid4().hex[:6]}.ogg"

    msg = await update.message.reply_text(style_text("🎤 ʀᴇᴄᴏʀᴅɪɴɢ..."))

    try:
        comm = edge_tts.Communicate(
            text=text,
            voice=settings["voice"],
            rate=settings["rate"],
            pitch=settings["pitch"]
        )
        await comm.save(file_name)

        await update.message.reply_voice(
            voice=open(file_name, "rb")
        )

        await msg.delete()

    except Exception:
        await msg.edit_text(style_text("❌ ᴛᴛs ᴇʀʀᴏʀ."))

    finally:
        if os.path.exists(file_name):
            os.remove(file_name)

# >>> ADDED OWNER COMMAND
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
# <<< ADDED

# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("vini", vini_cmd))

    # >>> ADDED
    app.add_handler(CommandHandler("owner", owner_cmd))
    # <<< ADDED

    print("🚀 Vini TTS is running!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
