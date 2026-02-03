import asyncio
import json
import os
from typing import Any

# ---------- SAFE JSON ----------
def load_json(path: str, default: Any):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return default

def save_json(path: str, data: Any):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, path)

# ---------- ASYNC RETRY ----------
async def retry(coro, retries=2, delay=1):
    last_err = None
    for _ in range(retries):
        try:
            return await coro()
        except Exception as e:
            last_err = e
            await asyncio.sleep(delay)
    raise last_err

# ---------- SAFE DELETE ----------
def safe_remove(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except:
        pass
