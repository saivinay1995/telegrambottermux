import os
import yt_dlp
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ------------------- Logging -------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ------------------- Environment -------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
YOUR_USER_ID = int(os.environ.get("YOUR_USER_ID"))

if not BOT_TOKEN or not YOUR_USER_ID:
    raise Exception("BOT_TOKEN or YOUR_USER_ID environment variables not set!")

# ------------------- Video Download -------------------
def download_video(url: str) -> str:
    """Download video using yt-dlp and return filename."""
    ydl_opts = {
        "outtmpl": "video.%(ext)s",
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
    return filename

# ------------------- Handlers -------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! Send me a video URL and I will download it to your Saved Messages."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url:
        return
    await update.message.reply_text("Downloading... ⏳")
    try:
        filepath = download_video(url)
        with open(filepath, "rb") as f:
            await context.bot.send_document(chat_id=YOUR_USER_ID, document=f)
        await update.message.reply_text("Sent to Saved Messages ✅")
    except Exception as e:
        await update.message.reply_text(f"Failed to download/send: {e}")
    finally:
        # Clean up downloaded file
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)

# ------------------- Application -------------------
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ------------------- Run Bot (Polling) -------------------
if __name__ == "__main__":
    logging.info("Bot is starting with long polling...")
    app.run_polling()
