import os
import yt_dlp
import logging
from telethon import TelegramClient, events

logging.basicConfig(level=logging.INFO)

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]

COOKIE_TXT_CONTENT = os.environ.get("COOKIE_TXT_CONTENT")
SESSION = "user.session"

# Write cookies file if provided
COOKIES_FILE = None
if COOKIE_TXT_CONTENT:
    COOKIES_FILE = "cookies.txt"
    with open(COOKIES_FILE, "w") as f:
        f.write(COOKIE_TXT_CONTENT)
    logging.info("Cookies.txt created.")

client = TelegramClient(SESSION, API_ID, API_HASH)


# ------------------- DOWNLOAD VIDEO -------------------
def download_video(url: str) -> str:
    ydl_opts = {
        "outtmpl": "video.%(ext)s",
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "noplaylist": True
    }
    if COOKIES_FILE:
        ydl_opts["cookiefile"] = COOKIES_FILE

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)


# ------------------- STREAM UPLOAD -------------------
async def stream_upload(filepath):
    """
    Uploads file to Saved Messages (Telegram cloud) using streaming.
    Works for 2GB+ files.
    """
    await client.send_file(
        "me",
        filepath,
        caption="Uploaded via userbot stream 🚀",
        force_document=True,
        part_size_kb=512,   # streaming chunk size
        supports_streaming=True
    )


# ------------------- MESSAGE LISTENER -------------------
@client.on(events.NewMessage(pattern=r"http"))
async def url_handler(event):
    url = event.raw_text.strip()

    await event.reply("Downloading video… ⏳")

    try:
        file_path = download_video(url)
        await event.reply("Uploading to Saved Messages… ☁️")

        await stream_upload(file_path)

        await event.reply("Done! Check your Saved Messages ✅")
    except Exception as e:
        await event.reply(f"Error: {e}")
    finally:
        if os.path.exists("video.mp4"):
            os.remove("video.mp4")


# ------------------- START USERBOT -------------------
print("Userbot started 🚀")
client.start()
client.run_until_disconnected()
