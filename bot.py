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

# FFmpeg & FFprobe from imageio-ffmpeg
FFMPEG_BIN = ffmpeg.get_ffmpeg_exe()
FFPROBE_BIN = ffmpeg.get_ffmpeg_exe()  # ffprobe included

# ------------------------------
# VIDEO METADATA (ffprobe)
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
# DOWNLOAD VIDEO USING YT-DLP
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

    # Remux with FFmpeg to make it streamable
    streamable_file = "streamable.mp4"
    cmd = [
        FFMPEG_BIN, "-i", filename,
        "-c", "copy",
        "-movflags", "faststart",
        streamable_file
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Remove original download
    if os.path.exists(filename):
        os.remove(filename)

    return streamable_file

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
client.start()
client.run_until_disconnected()
