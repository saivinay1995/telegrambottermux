import os
import yt_dlp
import logging
import json
import subprocess
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeVideo

logging.basicConfig(level=logging.INFO)

# ------------------------------
# ENV VARIABLES
# ------------------------------
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION = os.environ.get("SESSION", "userbot")
COOKIE_TXT_CONTENT = os.environ.get("COOKIE_TXT_CONTENT")

# Create cookies.txt if provided
COOKIES_FILE = None
if COOKIE_TXT_CONTENT:
    COOKIES_FILE = "cookies.txt"
    with open(COOKIES_FILE, "w") as f:
        f.write(COOKIE_TXT_CONTENT)
    logging.info("Cookies file created")

# ------------------------------
# VIDEO METADATA (ffprobe)
# ------------------------------
def get_video_info(path):
    """Returns duration, width, height for Telegram streaming."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    info = json.loads(result.stdout)

    for stream in info["streams"]:
        if stream["codec_type"] == "video":
            duration = float(stream.get("duration", 0))
            width = stream.get("width", 0)
            height = stream.get("height", 0)
            return duration, width, height

    return 0, 0, 0  # fallback

# ------------------------------
# DOWNLOAD VIDEO USING YT-DLP + RE-MUX FOR STREAMING
# ------------------------------
def download_video(url: str) -> str:
    ydl_opts = {
        "outtmpl": "video.%(ext)s",
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
    }
    if COOKIES_FILE:
        ydl_opts["cookiefile"] = COOKIES_FILE

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

    # Re-mux for Telegram streaming (moov atom at start)
    streamed_file = "streamable.mp4"
    cmd = [
        "ffmpeg", "-i", filename,
        "-c", "copy",
        "-movflags", "faststart",  # ensures video is streamable
        streamed_file
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Remove original downloaded file
    if os.path.exists(filename):
        os.remove(filename)

    return streamed_file

# ------------------------------
# TELETHON USERBOT CLIENT
# ------------------------------
client = TelegramClient(SESSION, API_ID, API_HASH)

# ------------------------------
# MESSAGE HANDLER
# ------------------------------
@client.on(events.NewMessage(outgoing=False))
async def handler(event):
    url = event.message.message.strip()

    if not url.startswith("http"):
        return

    await event.reply("Downloading... ⏳")

    try:
        filepath = download_video(url)
        duration, width, height = get_video_info(filepath)

        await client.send_file(
            "me",  # Saved Messages
            filepath,
            caption="Streamable video 🚀",
            attributes=[
                DocumentAttributeVideo(
                    duration=duration,
                    w=width,
                    h=height,
                    supports_streaming=True
                )
            ],
            force_document=False,   # IMPORTANT!!!
        )

        await event.reply("Uploaded as STREAMABLE video ✔")

    except Exception as e:
        await event.reply(f"Error: {e}")
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

# ------------------------------
# START USERBOT
# ------------------------------
print("Userbot Started...")
client.start()
client.run_until_disconnected()
