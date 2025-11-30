import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telethon import TelegramClient
import yt_dlp

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

client = TelegramClient("user", API_ID, API_HASH)

# -------- Download Function -------- #
async def download_youtube(url):
    ydl_opts = {
        "outtmpl": "video.mp4",
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4"
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return "video.mp4"

# -------- Handlers -------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send a YouTube link!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    await update.message.reply_text("Downloading...")

    file_path = await download_youtube(url)

    # Upload via Telethon (userbot)
    await client.connect()
    msg = await client.send_file("me", file_path, caption="Uploaded via userbot 🚀")
    await update.message.reply_text("Uploaded to Saved Messages!")

# -------- Main -------- #
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Render webhook settings
    port = int(os.environ.get("PORT", 10000))
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN,
        webhook_url=f"https://{os.getenv('RENDER_EXTERNAL_URL')}/{BOT_TOKEN}",
    )

if __name__ == "__main__":
    main()
