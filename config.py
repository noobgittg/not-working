import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID: int = int(os.environ.get("API_ID", "2040"))
    API_HASH: str = os.environ.get("API_HASH", "b18441a1ff607e10a989891a5462e627")
    BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")

    OWNER_ID: int = int(os.environ.get("OWNER_ID", "1892771262"))
    ADMINS: List[int] = [int(x) for x in os.environ.get("ADMINS", f"{OWNER_ID}").split() if x.isdigit()]
    if OWNER_ID not in ADMINS:
        ADMINS.append(OWNER_ID)

    MONGO_URI: str = os.environ.get("MONGO_URI", os.environ.get("DATABASE_URL", "mongodb://localhost:27017"))
    DATABASE_NAME: str = os.environ.get("DATABASE_NAME", "MMW_ProBot")

    BIN_CHANNEL: int = int(os.environ.get("BIN_CHANNEL", "0"))
    LOG_CHANNEL: int = int(os.environ.get("LOG_CHANNEL", "0"))

    PORT: int = int(os.environ.get("PORT", "8080"))
    BIND_ADDRESS: str = os.environ.get("BIND_ADDRESS", "0.0.0.0")

    koyeb_app = os.environ.get("KOYEB_APP_NAME")
    default_base = f"https://{koyeb_app}.koyeb.app" if koyeb_app else f"http://127.0.0.1:{PORT}"
    _raw_base = os.environ.get("BASE_URL", os.environ.get("URL", default_base)).rstrip("/")
    if _raw_base and not (_raw_base.startswith("http://") or _raw_base.startswith("https://")):
        _raw_base = f"https://{_raw_base}"
    BASE_URL: str = _raw_base

    THAM_URL: str = os.environ.get("THAM_URL", "https://envs.sh/thumb.jpg")

    WATERMARK: str = "t.me/mallumovieworldmain2"
    _raw_wm_url = os.environ.get("WATERMARK_URL", "https://t.me/mallumovieworldmain2")
    if _raw_wm_url and not (_raw_wm_url.startswith("http://") or _raw_wm_url.startswith("https://")):
        _raw_wm_url = f"https://{_raw_wm_url}"
    WATERMARK_URL: str = _raw_wm_url

    CACHE_TTL: int = int(os.environ.get("CACHE_TTL", "600"))
    DEFAULT_AUTO_DELETE: int = int(os.environ.get("AUTO_DELETE_TIME", "0"))
    FORCE_SUB_CHANNEL: str = os.environ.get("FORCE_SUB_CHANNEL", os.environ.get("FORCE_SUB", ""))
    WORKERS: int = int(os.environ.get("WORKERS", "100"))
    MAX_CONCURRENT_TASKS: int = int(os.environ.get("MAX_CONCURRENT_TASKS", "100"))

    DOWNLOAD_DIR: str = os.path.join(os.getcwd(), "downloads")
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
