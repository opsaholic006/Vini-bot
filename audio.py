import os
import subprocess
import uuid

BASE_DIR = "/tmp/audio"
os.makedirs(BASE_DIR, exist_ok=True)

YTDLP_CMD = [
    "yt-dlp",
    "-f", "bestaudio",
    "--extract-audio",
    "--audio-format", "mp3",
    "--audio-quality", "0",
    "--no-playlist",
]

SOURCES = [
    "ytsearch1:",
    "scsearch1:",
]

def download_audio(query: str) -> str:
    filename = f"{uuid.uuid4()}.mp3"
    output = os.path.join(BASE_DIR, filename)

    for src in SOURCES:
        try:
            cmd = YTDLP_CMD + ["-o", output, src + query]
            subprocess.run(cmd, check=True, timeout=60)
            if os.path.exists(output):
                return output
        except Exception:
            continue

    raise RuntimeError("All sources failed")
