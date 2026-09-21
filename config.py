import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


def _int_env(name: str, default: int = 0) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value.strip())
    except ValueError as exc:
        raise RuntimeError(f"Invalid integer environment variable {name!r}: {value!r}") from exc


def _id_list_env(name: str, default: List[int] | None = None) -> List[int]:
    raw = os.getenv(name, "")
    values: List[int] = []
    for item in raw.replace(",", " ").split():
        if item.lstrip("-").isdigit():
            values.append(int(item))
    if not values and default:
        values = list(default)
    return list(dict.fromkeys(values))


class Config:
    API_ID: int = _int_env("API_ID", 0)
    API_HASH: str = os.getenv("API_HASH", "").strip()
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()

    OWNER_ID: int = _int_env("OWNER_ID", 0)
    ADMINS: List[int] = _id_list_env("ADMINS", [OWNER_ID] if OWNER_ID else [])
    if OWNER_ID and OWNER_ID not in ADMINS:
        ADMINS.append(OWNER_ID)

    MONGO_URI: str = os.getenv("MONGO_URI", os.getenv("DATABASE_URL", "mongodb://localhost:27017")).strip()
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", os.getenv("DB_NAME", "MMW_ProBot")).strip() or "MMW_ProBot"

    BIN_CHANNEL: int = _int_env("BIN_CHANNEL", 0)
    LOG_CHANNEL: int = _int_env("LOG_CHANNEL", 0)

    PORT: int = _int_env("PORT", 8080)
    BIND_ADDRESS: str = os.getenv("BIND_ADDRESS", "0.0.0.0").strip() or "0.0.0.0"

    koyeb_app = os.getenv("KOYEB_APP_NAME", "").strip()
    default_base = f"https://{koyeb_app}.koyeb.app" if koyeb_app else f"http://127.0.0.1:{PORT}"
    BASE_URL: str = os.getenv("BASE_URL", os.getenv("URL", default_base)).strip().rstrip("/")

    THAM_URL: str = os.getenv("THAM_URL", "").strip()

    WATERMARK: str = "t.me/mallumovieworldmain2"
    WATERMARK_URL: str = "https://t.me/mallumovieworldmain2"

    CACHE_TTL: int = _int_env("CACHE_TTL", 600)
    DEFAULT_AUTO_DELETE: int = _int_env("AUTO_DELETE_TIME", 0)
    FORCE_SUB_CHANNEL: str = os.getenv("FORCE_SUB_CHANNEL", os.getenv("FORCE_SUB", "")).strip()
    WORKERS: int = max(1, _int_env("WORKERS", 50))
    MAX_CONCURRENT_TASKS: int = max(1, _int_env("MAX_CONCURRENT_TASKS", 5))

    # Pyrogram/Pyrofork bot uploads are limited by Telegram. Keep a safety margin
    # for multipart/request overhead instead of trying to upload exactly at the edge.
    MAX_TELEGRAM_UPLOAD_BYTES: int = 2000 * 1024 * 1024
    SAFE_TELEGRAM_PART_BYTES: int = 1900 * 1024 * 1024

    DOWNLOAD_DIR: str = os.path.join(os.getcwd(), "downloads")
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    @classmethod
    def validate(cls) -> None:
        missing = []
        if cls.API_ID <= 0:
            missing.append("API_ID")
        if not cls.API_HASH:
            missing.append("API_HASH")
        if not cls.BOT_TOKEN:
            missing.append("BOT_TOKEN")
        if cls.PORT <= 0 or cls.PORT > 65535:
            raise RuntimeError(f"PORT must be between 1 and 65535, got {cls.PORT}")
        if not cls.MONGO_URI:
            missing.append("MONGO_URI")
        if missing:
            raise RuntimeError("Missing required environment variables: " + ", ".join(missing))
