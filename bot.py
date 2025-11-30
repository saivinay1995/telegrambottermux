from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update
import os
import yt_dlp
import logging

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ["BOT_TOKEN"]
YOUR_USER_ID = int(os.environ["YOUR_USER_ID"])
PUBLIC_URL = os.environ["PUBLIC_URL"]

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a video URL!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url:
        return
    await update.message.reply_text("Downloading...")
    try:
        filename = yt_dlp.YoutubeDL({"outtmpl":"video.%(ext)s"}).extract_info(url, download=True)["title"]+".mp4"
        with open(filename,"rb") as f:
            await context.bot.send_document(chat_id=YOUR_USER_ID, document=f)
    except Exception as e:
        await update.message.reply_text(f"Failed: {e}")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

if __name__ == "__main__":
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        webhook_url=PUBLIC_URL.rstrip("/") + WEBHOOK_PATH,
        webhook_path=WEBHOOK_PATH
    )
