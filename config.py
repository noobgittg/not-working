import os
import re
from typing import List

class Config:
    API_ID: int = int(os.environ.get("API_ID") or "29301015")
    API_HASH: str = os.environ.get("API_HASH") or "18e14b754391d71fc46463955456ae54"
    BOT_TOKEN: str = os.environ.get("BOT_TOKEN") or "8838145751:AAEzVG9K7CLWxKP7uJbwzBZxIPc5RgXAoWw"

    OWNER_ID: int = int(os.environ.get("OWNER_ID") or "970284861")
    raw_admins: str = os.environ.get("ADMINS") or str(OWNER_ID)
    ADMINS: List[int] = [int(x) for x in re.findall(r"\d+", raw_admins)]
    if OWNER_ID not in ADMINS:
        ADMINS.append(OWNER_ID)

    MONGO_URI: str = (
        os.environ.get("MONGO_URI")
        or os.environ.get("DATABASE_URL")
        or "mongodb+srv://Sarkar123:GAUTAMMISHRA@sarkar.1uiwqkd.mongodb.net/?retryWrites=true&w=majority"
    )
    DATABASE_NAME: str = os.environ.get("DATABASE_NAME") or "MMW_ProBot"

    BIN_CHANNEL: int = int(os.environ.get("BIN_CHANNEL") or "-1002064884494")
    LOG_CHANNEL: int = int(os.environ.get("LOG_CHANNEL") or "-1002064884494")

    PORT: int = int(os.environ.get("PORT") or "8080")
    BIND_ADDRESS: str = os.environ.get("BIND_ADDRESS") or "0.0.0.0"

    koyeb_app: str = os.environ.get("KOYEB_APP_NAME") or "mmwbot"
    default_base: str = f"https://{koyeb_app}.koyeb.app" if koyeb_app else f"http://127.0.0.1:{PORT}"
    BASE_URL: str = (
        os.environ.get("BASE_URL")
        or os.environ.get("URL")
        or default_base
    ).rstrip("/")

    THAM_URL: str = os.environ.get("THAM_URL") or "https://envs.sh/dp1.jpg"

    WATERMARK: str = "t.me/mallumovieworldmain2"
    WATERMARK_URL: str = "https://t.me/mallumovieworldmain2"

    CACHE_TTL: int = int(os.environ.get("CACHE_TTL") or "600")
    CACHE_MAX_ENTRIES: int = int(os.environ.get("CACHE_MAX_ENTRIES") or "1000")
    DEFAULT_AUTO_DELETE: int = int(os.environ.get("AUTO_DELETE_TIME") or "0")

    FORCE_SUB_CHANNEL: str = (
        os.environ.get("FORCE_SUB_CHANNEL")
        or os.environ.get("FORCE_SUB")
        or "@mallumovieworldmain1"
    )

    WORKERS: int = int(os.environ.get("WORKERS") or "200")
    MAX_CONCURRENT_TASKS: int = int(os.environ.get("MAX_CONCURRENT_TASKS") or "5")

    DOWNLOAD_DIR: str = os.path.join(os.getcwd(), "downloads")
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
