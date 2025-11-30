import os
import yt_dlp
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ["BOT_TOKEN"]
YOUR_USER_ID = int(os.environ["YOUR_USER_ID"])
PUBLIC_URL = os.environ["PUBLIC_URL"]
PORT = int(os.environ.get("PORT", 10000))

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a video URL!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url:
        return
    await update.message.reply_text("Downloading...")
    try:
        filename = yt_dlp.YoutubeDL({"outtmpl":"video.%(ext)s"}).extract_info(url, download=True)["title"]+".mp4"
        with open(filename, "rb") as f:
            await context.bot.send_document(chat_id=YOUR_USER_ID, document=f)
    except Exception as e:
        await update.message.reply_text(f"Failed: {e}")
    finally:
        if 'filename' in locals() and os.path.exists(filename):
            os.remove(filename)

# Build application
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Run webhook
if __name__ == "__main__":
    webhook_url = f"{PUBLIC_URL}/webhook"
    logging.info(f"Starting webhook at {webhook_url}")
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=webhook_url
    )
