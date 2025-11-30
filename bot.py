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

SESSION_FILE = "user"  # Hardcoded user.session must exist
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
# FFmpeg / FFprobe
# ------------------------------
FFMPEG_BIN = ffmpeg.get_ffmpeg_exe()
FFPROBE_BIN = ffmpeg.get_ffmpeg_exe()  # ffprobe included

# ------------------------------
# Video metadata
# ------------------------------
def get_video_info(path):
    if not os.path.exists(path):
        logging.warning(f"File not found: {path}")
        return 0, 0, 0

    cmd = [
        FFPROBE_BIN,
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        path
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        if not result.stdout:
            logging.warning("ffprobe returned empty output")
            return 0, 0, 0

        info = json.loads(result.stdout)
        for stream in info.get("streams", []):
            if stream.get("codec_type") == "video":
                duration = float(stream.get("duration", 0))
                width = stream.get("width", 0)
                height = stream.get("height", 0)
                return duration, width, height
    except Exception as e:
        logging.error(f"ffprobe error: {e}")
        return 0, 0, 0

    return 0, 0, 0

# ------------------------------
# Download + make streamable
# ------------------------------
def download_video(url: str) -> str:
    ydl_opts = {
        "outtmpl": "video.%(ext)s",
        "format": "bestaudio[ext=m4a]+bestvideo[ext=mp4]/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "ignoreerrors": True,
        "quiet": True,
    }
    if COOKIES_FILE:
        ydl_opts["cookiefile"] = COOKIES_FILE

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        original_filename = ydl.prepare_filename(info)
        # store original video name for reply
        download_video.last_video_name = info.get("title", os.path.basename(original_filename))

    # Remux to streamable mp4
    streamable_file = "streamable.mp4"
    cmd = [
        FFMPEG_BIN, "-i", original_filename,
        "-c", "copy",
        "-movflags", "faststart",
        streamable_file
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Remove original download
    if os.path.exists(original_filename):
        os.remove(original_filename)

    return streamable_file

# ------------------------------
# TELETHON CLIENT
# ------------------------------
client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

# ------------------------------
# Message handler
# ------------------------------
@client.on(events.NewMessage(outgoing=True))  # listens to your own messages
async def handler(event):
    url = event.message.message.strip()
    if not url.startswith("http"):
        return

    await event.reply("Downloading... ⏳")

    try:
        filepath = download_video(url)
        duration, width, height = get_video_info(filepath)
        video_name = download_video.last_video_name

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

        # Send original video name in reply
        await event.reply(f"Uploaded video: `{video_name}` ✔")

    except Exception as e:
        await event.reply(f"Error: {e}")
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

# ------------------------------
# START USERBOT
# ------------------------------
print("Userbot Started...")
client.start()  # Uses hardcoded user.session
client.run_until_disconnected()
