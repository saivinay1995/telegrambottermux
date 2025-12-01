import os
import yt_dlp
import logging
import json
import subprocess
import imageio_ffmpeg as ffmpeg
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeVideo
from flask import Flask
import threading

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
FFPROBE_BIN = os.path.join(os.path.dirname(FFMPEG_BIN), 'ffprobe')  # Derive FFprobe path from FFmpeg

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

    except subprocess.CalledProcessError as e:
        logging.error(f"FFprobe error: {e.stderr.decode()}")
    except Exception as e:
        logging.error(f"Unexpected error in get_video_info: {e}")

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
        # Removed "ignoreerrors": True and "quiet": True for debugging
    }

    if COOKIES_FILE:
        ydl_opts["cookiefile"] = COOKIES_FILE

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logging.info(f"Extracting info for URL: {url}")
            info = ydl.extract_info(url, download=True)
            if not info:
                raise Exception("Failed to extract video info")
            original_file = ydl.prepare_filename(info)
            download_video.last_title = info.get("title", os.path.basename(original_file))
            logging.info(f"Downloaded: {original_file}")
    except Exception as e:
        logging.error(f"yt-dlp error: {e}")
        raise

    # Sanitize title for filename (remove invalid chars)
    safe_title = "".join(c for c in download_video.last_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    if not safe_title:
        safe_title = "video"

    # Convert to streamable faststart MP4 with actual title
    final_path = os.path.abspath(f"{safe_title}.mp4")

    cmd = [
        FFMPEG_BIN, "-i", original_file,
        "-c:v", "copy", "-c:a", "copy",
        "-movflags", "+faststart",
        final_path
    ]

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        logging.info("FFmpeg remux completed")
    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg error: {e.stderr.decode()}")
        raise Exception("FFmpeg remux failed")

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

    filepath = None

    try:
        filepath = download_video(url)
        duration, width, height = get_video_info(filepath)
        video_name = download_video.last_title

        await client.send_file(
            "me",
            filepath,
            caption=video_name,
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
        logging.error(f"Handler error: {e}")
        await event.reply(f"Error: {e}")

    finally:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)

# ------------------------------
# Simple Web Server for Render
# ------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ------------------------------
# Start
# ------------------------------
print("Userbot Started...")
# Start web server in a separate thread
threading.Thread(target=run_web_server, daemon=True).start()
client.start()
client.run_until_disconnected()
