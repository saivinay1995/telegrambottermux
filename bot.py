# bot.py
import os
import logging
import yt_dlp
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")            # set in Render
YOUR_USER_ID = int(os.environ.get("YOUR_USER_ID")) # set in Render
PORT = int(os.environ.get("PORT", 8000))
WEBHOOK_PATH = os.environ.get("WEBHOOK_PATH", f"/webhook/{BOT_TOKEN}")
# public URL will be https://<your-service>.onrender.com + WEBHOOK_PATH
PUBLIC_URL = os.environ.get("PUBLIC_URL")  # set to your Render service URL (see below)


# === yt-dlp helper ===
def download_with_ytdlp(url: str) -> str:
    # saves to local file and returns filename
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
    # normalize extension to .mp4 if merged
    if not filename.endswith(".mp4") and os.path.exists(filename):
        base, _ = os.path.splitext(filename)
        mp4 = f"{base}.mp4"
        try:
            os.rename(filename, mp4)
            filename = mp4
        except Exception:
            pass
    return filename


# === Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a video URL and I'll download & save it to your Saved Messages.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = (update.message.text or "").strip()
    if not url:
        await update.message.reply_text("Please send a valid URL.")
        return

    await update.message.reply_text("Downloading... ⏳")
    try:
        filepath = download_with_ytdlp(url)
        # send to Saved Messages (your user id)
        with open(filepath, "rb") as f:
            await context.bot.send_document(chat_id=YOUR_USER_ID, document=f, caption="Downloaded via yt-dlp")
        await update.message.reply_text("Sent to Saved Messages ✅")
    except Exception as e:
        logger.exception("Download/send failed")
        await update.message.reply_text(f"Failed: {e}")
    finally:
        try:
            if 'filepath' in locals() and os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass


# === App bootstrap & webhook setup ===
def build_app():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app

if __name__ == "__main__":
    app = build_app()

    # Set webhook URL (Render gives you https://<service>.onrender.com)
    if not PUBLIC_URL:
        raise SystemExit("PUBLIC_URL environment variable not set. Set it to your Render service URL (e.g. https://my-bot.onrender.com)")
    webhook_url = PUBLIC_URL.rstrip("/") + WEBHOOK_PATH
    logger.info("Setting webhook to %s", webhook_url)

    # start webhook (built-in run_webhook will host a simple webserver)
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=webhook_url,
        webhook_path=WEBHOOK_PATH
    )
