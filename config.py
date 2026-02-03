import os

# ===== REQUIRED =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# ===== PATHS =====
BASE_DIR = "/app/data"
AUDIO_DIR = f"{BASE_DIR}/audio_cache"

USERS_FILE = f"{BASE_DIR}/users.json"
FILE_ID_CACHE = f"{BASE_DIR}/file_ids.json"
SEARCH_CACHE_FILE = f"{BASE_DIR}/search_cache.json"

# ===== TTS SETTINGS (OWNER CONTROLLABLE) =====
TTS_SETTINGS = {
    "voice": "hi-IN-SwaraNeural",
    "rate": "+3%",
    "pitch": "+2Hz"
}

# ===== AUDIO LIMITS =====
MAX_DURATION = 600
MAX_RESULTS = 5
