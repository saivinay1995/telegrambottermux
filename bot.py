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

SESSION_FILE = "user"
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
FFPROBE_BIN = ffmpeg.get_ffmpeg_exe()

# ------------------------------
# Video metadata
# ------------------------------
def get_video_info(path):
    if not os.path.exists(path):
        logging.warning(f"File not found: {path}")
        return 0, 0, 0

    cmd = [
        FFPROBE_BIN, "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        path
    ]

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        info = json.loads(result.stdout or "{}")

        for stream in info.get("streams", []):
            if stream.get("codec_type") == "video":
                duration = float(stream.get("duration", 0))
                width = stream.get("width", 0)
                height = stream.get("height", 0)
                return duration, width, height

    except:
        return 0, 0, 0

    return 0, 0, 0

# ------------------------------
# Download + FASTSTART remux
# ------------------------------
def download_video(url: str) -> str:

    ydl_opts = {
        "outtmpl": "video.%(ext)s",
        "format": "best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "ignoreerrors": True,
        "quiet": True
    }

    if COOKIES_FILE:
        ydl_opts["cookiefile"] = COOKIES_FILE

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        original_file = ydl.prepare_filename(info)
        download_video.last_title = info.get("title", os.path.basename(original_file))

    # Convert to streamable faststart MP4
    final_path = os.path.abspath("streamable.mp4")

    cmd = [
        FFMPEG_BIN, "-i", original_file,
        "-c:v", "copy", "-c:a", "copy",
        "-movflags", "+faststart",
        final_path
    ]

    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if not os.path.exists(final_path):
        raise Exception("FFmpeg failed to create streamable.mp4")

    os.remove(original_file)
    return final_path

# ------------------------------
# TELETHON CLIENT
# ------------------------------
client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

# ------------------------------
# Message Handler
# ------------------------------
@client.on(events.NewMessage(outgoing=True))
async def handler(event):
    url = event.message.message.strip()

    if not url.startswith("http"):
        return

    await event.reply("Downloading... ⏳")

    filepath = None  # <<< FIXED

    try:
        filepath = download_video(url)
        duration, width, height = get_video_info(filepath)
        video_name = download_video.last_title

        await client.send_file(
            "me",
            filepath,
            caption=video_name,     # send REAL video name
            attributes=[
                DocumentAttributeVideo(
                    duration=duration,
                    w=width,
                    h=height,
                    supports_streaming=True
                )
            ],
            force_document=False
        )

        await event.reply(f"Uploaded: {video_name}")

    except Exception as e:
        await event.reply(f"Error: {e}")

    finally:
        # <<< FIXED SAFE DELETE
        if filepath and os.path.exists(filepath):
            os.remove(filepath)

# ------------------------------
# Start
# ------------------------------
print("Userbot Started...")
client.start()
client.run_until_disconnected()
