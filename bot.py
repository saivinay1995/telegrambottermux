import os
import yt_dlp
import logging
import json
import subprocess
import imageio_ffmpeg as ffmpeg
import threading
import asyncio
from flask import Flask
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeVideo

logging.basicConfig(level=logging.INFO)

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_FILE = "user"

COOKIE_TXT_CONTENT = os.environ.get("COOKIE_TXT_CONTENT")

# -------------------------------------
# Flask dummy server (REQUIRED by Render free)
# -------------------------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot running"

def run_flask():
    port = os.environ.get("PORT")
    if not port or not port.isdigit():
        port = 10000
    port = int(port)
    app.run(host="0.0.0.0", port=port)

# -------------------------------------
# Cookies
# -------------------------------------
COOKIES_FILE = None
if COOKIE_TXT_CONTENT:
    COOKIES_FILE = "cookies.txt"
    with open(COOKIES_FILE, "w") as f:
        f.write(COOKIE_TXT_CONTENT)

# -------------------------------------
# FFmpeg
# -------------------------------------
FFMPEG_BIN = ffmpeg.get_ffmpeg_exe()
FFPROBE_BIN = ffmpeg.get_ffmpeg_exe()

def get_video_info(path):
    if not os.path.exists(path):
        return 0,0,0
    cmd = [
        FFPROBE_BIN, "-v", "quiet", "-print_format", "json",
        "-show_streams", path
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        info = json.loads(result.stdout or "{}")
        for stream in info.get("streams", []):
            if stream.get("codec_type") == "video":
                return float(stream.get("duration",0)), stream.get("width",0), stream.get("height",0)
    except:
        return 0,0,0
    return 0,0,0

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
    cmd = [FFMPEG_BIN, "-i", original_file, "-c", "copy", "-movflags", "+faststart", final_path]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if os.path.exists(original_file):
        os.remove(original_file)
    return final_path

# -------------------------------------
# TELETHON CLIENT
# -------------------------------------
client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

@client.on(events.NewMessage(outgoing=True))
async def handler(event):
    url = event.message.message.strip()
    if not url.startswith("http"):
        return

    await event.reply("Downloading...")

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
                    duration=duration, w=width, h=height, supports_streaming=True
                )
            ],
            force_document=False
        )

        await event.reply(f"Uploaded: {video_name}")

    except Exception as e:
        await event.reply(f"Error: {e}")

    finally:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)

# -------------------------------------
# Start Telethon in its own event loop
# -------------------------------------
def start_telethon():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(client.start())
    loop.run_until_complete(client.run_until_disconnected())

# -------------------------------------
# START BOTH THREADS
# -------------------------------------
print("Starting free Render-compatible userbot...")

threading.Thread(target=run_flask).start()
threading.Thread(target=start_telethon).start()
