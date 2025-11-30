# user_stream_bot.py
import os
import yt_dlp
import logging
from telethon import TelegramClient, events

logging.basicConfig(level=logging.INFO)

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]

COOKIE_TXT_CONTENT = os.environ.get("COOKIE_TXT_CONTENT")
SESSION = "user.session"

# optional: create cookies.txt from env if provided
COOKIES_FILE = None
if COOKIE_TXT_CONTENT:
    COOKIES_FILE = "cookies.txt"
    with open(COOKIES_FILE, "w") as f:
        f.write(COOKIE_TXT_CONTENT)
    logging.info("Cookies file created.")

client = TelegramClient(SESSION, API_ID, API_HASH)


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


async def stream_upload(filepath):
    await client.send_file(
        "me",
        filepath,
        caption="Uploaded via userbot stream",
        force_document=True,
        part_size_kb=512,
        supports_streaming=True
    )


@client.on(events.NewMessage(pattern=r"http"))
async def url_handler(event):
    url = event.raw_text.strip()
    await event.reply("Downloading… ⏳")
    filepath = None
    try:
        filepath = download_video(url)
        await event.reply("Uploading to Saved Messages… ☁️")
        await stream_upload(filepath)
        await event.reply("Done! Check your Saved Messages ✅")
    except Exception as e:
        await event.reply(f"Error: {e}")
    finally:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)


if __name__ == "__main__":
    print("Userbot starting — will create session if first run.")
    client.start()   # interactive on first run: phone + code
    client.run_until_disconnected()
