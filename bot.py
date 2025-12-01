import os
import yt_dlp
import logging
import json
import subprocess
import threading
from flask import Flask
import imageio_ffmpeg as ffmpeg
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeVideo

logging.basicConfig(level=logging.INFO)

# ------------------------------
# FLASK SERVER (for Render Free Web Service)
# ------------------------------
app = Flask(__name__)

@app.get("/")
def home():
    return "Userbot Running Successfully"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ------------------------------
# TELEGRAM CONFIG
# ------------------------------
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]

SESSION_FILE = "user"
COOKIE_TXT_CONTENT = os.environ.get("COOKIE_TXT_CONTENT")

# ------------------------------
# Cookies
# ------------------------------
COOKIES_FILE = None
if COOKIE_TXT_CONTENT:
    COOKIES_FILE = "cookies.txt"
    with open(COOKIES_FILE, "w") as f:
        f.write(COOKIE_TXT_CONTENT)
    logging.info("Cookies file created")

# ------------------------------
# FFmpeg
# ------------------------------
FFMPEG_BIN = ffmpeg.get_ffmpeg_exe()
FFPROBE_BIN = ffmpeg.get_ffmpeg_exe()


def get_video_info(path):
    if not os.path.exists(path):
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
# Download video
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

    final_path = os.path.abspath("streamable.mp4")

    cmd = [
        FFMPEG_BIN, "-i", original_file,
        "-c:v", "copy",
        "-c:a", "copy",
        "-movflags", "+faststart",
        final_path
    ]
    subprocess.run(cmd)

    os.remove(original_file)
    return final_path

# ------------------------------
# TELETHON BOT
# ------------------------------
client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

@client.on(events.NewMessage(outgoing=True))
async def handler(event):
    url = event.raw_text.strip()

    if not url.startswith("http"):
        return

    await event.reply("Downloading...")

    filepath = None

    try:
        filepath = download_video(url)
        duration, width, height = get_video_info(filepath)
        title = download_video.last_title

        await client.send_file(
            "me",
            filepath,
            caption=title,
            attributes=[
                DocumentAttributeVideo(
                    duration=duration,
                    w=width,
                    h=height,
                    supports_streaming=True
                )
            ]
        )

        await event.reply(f"Uploaded: {title}")

    except Exception as e:
        await event.reply(f"Error: {e}")

    finally:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)


def start_telethon():
    client.start()
    client.run_until_disconnected()


# ------------------------------
# RUN BOTH (Flask + Telethon)
# ------------------------------
print("Starting free Render-compatible userbot...")

threading.Thread(target=run_flask).start()
threading.Thread(target=start_telethon).start()
