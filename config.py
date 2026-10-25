import os
import re
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID: int = int(os.environ.get("API_ID", "2040"))
    API_HASH: str = os.environ.get("API_HASH", "b18441a1ff607e10a989891a5462e627")
    BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")
    OWNER_ID: int = int(os.environ.get("OWNER_ID", "1892771262"))
    raw_admins = os.environ.get("ADMINS", str(OWNER_ID))
    ADMINS: List[int] = [int(x) for x in re.findall(r"\d+", raw_admins)]
    if OWNER_ID not in ADMINS:
        ADMINS.append(OWNER_ID)

    # Single Unified Database Configuration
    MONGO_URI: str = os.environ.get("MONGO_URI", os.environ.get("DATABASE_URL", "mongodb://localhost:27017"))
    DATABASE_NAME: str = os.environ.get("DATABASE_NAME", "MMW_ProBot")

    BIN_CHANNEL: int = int(os.environ.get("BIN_CHANNEL", "0"))
    LOG_CHANNEL: int = int(os.environ.get("LOG_CHANNEL", "0"))

    PORT: int = int(os.environ.get("PORT", "8080"))
    BIND_ADDRESS: str = os.environ.get("BIND_ADDRESS", "0.0.0.0")

    koyeb_app = os.environ.get("KOYEB_APP_NAME")
    default_base = f"https://{koyeb_app}.koyeb.app" if koyeb_app else f"http://127.0.0.1:{PORT}"
    BASE_URL: str = os.environ.get("BASE_URL", os.environ.get("URL", default_base)).rstrip("/")

    THAM_URL: str = os.environ.get("THAM_URL", "https://envs.sh/thumb.jpg")

    WATERMARK: str = "MMW BOTZ"
    WATERMARK_URL: str = "https://t.me/mallumovieworldmain2"

    # Fast cache and adaptive streaming configuration
    CACHE_TTL: int = int(os.environ.get("CACHE_TTL", "900"))
    CACHE_MAX_ENTRIES: int = int(os.environ.get("CACHE_MAX_ENTRIES", "5000"))
    STREAM_CHUNK_SIZE: int = int(os.environ.get("STREAM_CHUNK_SIZE", str(4 * 1024 * 1024)))  # 4 MB local chunks
    STREAM_SPEED_LIMIT_MBPS: int = int(os.environ.get("STREAM_SPEED_LIMIT_MBPS", "20"))  # internal pacing hint only
    STREAM_BUFFER_CHUNKS: int = int(os.environ.get("STREAM_BUFFER_CHUNKS", "32"))        # adaptive pre-fetch buffer

    DEFAULT_AUTO_DELETE: int = int(os.environ.get("AUTO_DELETE_TIME", "0"))
    FORCE_SUB_CHANNEL: str = os.environ.get("FORCE_SUB_CHANNEL", os.environ.get("FORCE_SUB", ""))
    WORKERS: int = int(os.environ.get("WORKERS", "64"))
    TG_TRANSMISSION_WORKERS: int = max(1, int(os.environ.get("TG_TRANSMISSION_WORKERS", "32")))
    MAX_CONCURRENT_TASKS: int = int(os.environ.get("MAX_CONCURRENT_TASKS", "10"))
    KEEPALIVE_INTERVAL: int = max(5, int(os.environ.get("KEEPALIVE_INTERVAL", "10")))
    RESTART_INTERVAL: int = max(3600, int(os.environ.get("RESTART_INTERVAL", "86400")))

    DOWNLOAD_DIR: str = os.path.join(os.getcwd(), "downloads")
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
