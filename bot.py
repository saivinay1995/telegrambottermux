import os
import logging
import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from telethon import TelegramClient

logging.basicConfig(level=logging.INFO)

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION = "session_data"

TELETHON_CLIENT = TelegramClient(SESSION, API_ID, API_HASH)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL") + "/webhook"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send any YouTube link to download!")


async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text

    await update.message.reply_text("Downloading...")

    output = "/data/video.mp4"

    cmd = [
        "yt-dlp",
        "-f", "best",
        "-o", output,
        url
    ]

    subprocess.run(cmd)

    if not os.path.exists(output):
        return await update.message.reply_text("Download failed!")

    await update.message.reply_text("Uploading to Saved Messages...")

    async with TELETHON_CLIENT:
        await TELETHON_CLIENT.send_file("me", output)

    return await update.message.reply_text("Done! Check your Saved Messages.")


async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    await app.bot.set_webhook(WEBHOOK_URL)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, download))

    await TELETHON_CLIENT.connect()

    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 10000)),
        webhook_url=WEBHOOK_URL,
    )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
