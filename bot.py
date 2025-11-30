import os
import yt_dlp
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Environment variables ===
BOT_TOKEN = os.environ.get("BOT_TOKEN")
YOUR_USER_ID = os.environ.get("YOUR_USER_ID")
PUBLIC_URL = os.environ.get("PUBLIC_URL")  # Render service URL

if not BOT_TOKEN or not YOUR_USER_ID or not PUBLIC_URL:
    raise Exception("Please set BOT_TOKEN, YOUR_USER_ID, and PUBLIC_URL in Render environment variables")

YOUR_USER_ID = int(YOUR_USER_ID)
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"


# === yt-dlp download ===
def download_video(url: str) -> str:
    ydl_opts = {
        "outtmpl": "downloaded.%(ext)s",
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
    if not filename.endswith(".mp4"):
        mp4_file = "video.mp4"
        os.rename(filename, mp4_file)
        filename = mp4_file
    return filename


# === Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a video URL!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = (update.message.text or "").strip()
    if not url:
        await update.message.reply_text("Send a valid URL")
        return
    await update.message.reply_text("Downloading... ⏳")
    try:
        filepath = download_video(url)
        with open(filepath, "rb") as f:
            await context.bot.send_document(chat_id=YOUR_USER_ID, document=f, caption="Downloaded via yt-dlp")
        await update.message.reply_text("Sent to Saved Messages ✅")
    except Exception as e:
        logger.exception("Download failed")
        await update.message.reply_text(f"Failed: {e}")
    finally:
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)


# === Build Application ===
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


# === Run webhook for Render ===
if __name__ == "__main__":
    webhook_url = PUBLIC_URL.rstrip("/") + WEBHOOK_PATH
    logger.info(f"Setting webhook: {webhook_url}")

    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        webhook_url=webhook_url,
        webhook_path=WEBHOOK_PATH
    )
