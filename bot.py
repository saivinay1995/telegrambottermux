import os
import yt_dlp
import logging
import json
import subprocess
import imageio_ffmpeg as ffmpeg
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeVideo

logging.basicConfig(level=logging.INFO)

# ------------------------------
# TELEGRAM CONFIG
# ------------------------------
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]

SESSION_FILE = "user"  # hardcoded, user.session must be in same folder
COOKIE_TXT_CONTENT = os.environ.get("COOKIE_TXT_CONTENT")

# ------------------------------
# Cookies support
# ------------------------------
COOKIES_FILE = None
if COOKIE_TXT_CONTENT:
    COOKIES_FILE = "cookies.txt"
    with open(COOKIES_FILE, "w") as f:
        f.write(COOKIE_TXT_CONTENT)
    logging.info("Cookies file created")

# ------------------------------
# FFmpeg & FFprobe
# ------------------------------
FFMPEG_BIN = ffmpeg.get_ffmpeg_exe()
FFPROBE_BIN = ffmpeg.get_ffmpeg_exe()  # ffprobe included

# ------------------------------
# Video metadata
# ------------------------------
def get_video_info(path):
    cmd = [
        FFPROBE_BIN, "-v", "quiet", "-print_format", "json",
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

    return 0, 0, 0

# ------------------------------
# Download + make streamable
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

    # Remux to streamable mp4
    streamable_file = "streamable.mp4"
    cmd = [
        FFMPEG_BIN, "-i", filename,
        "-c", "copy",
        "-movflags", "faststart",
        streamable_file
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Remove original
    if os.path.exists(filename):
        os.remove(filename)

    return streamable_file

# ------------------------------
# TELETHON CLIENT
# ------------------------------
client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

# ------------------------------
# Message handler
# ------------------------------
@client.on(events.NewMessage(outgoing=True))  # listen to own messages
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
            force_document=False,
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
client.start()  # uses user.session
client.run_until_disconnected()
