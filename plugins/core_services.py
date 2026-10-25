import time
import os
import sys
import shutil
import asyncio
import json
import re
import datetime
from plugins.media_types import is_audio_mime, is_video_mime, normalize_mime
import socket
import urllib.request
from urllib.parse import urlparse
import http.client
from collections import defaultdict
from typing import Tuple, Optional, Dict, Any, List, Union
try:
    import aiohttp
except ImportError:
    aiohttp = None
from config import Config
from plugins.core_utils import (
    logger,
    to_smallcaps,
    format_watermark,
    humanbytes,
    time_formatter,
    is_valid_url,
    sanitize_filename
)
from plugins.core_db import user_repo, chat_repo

try:
    import aiofiles
except ImportError:
    aiofiles = None

# ==================== 1. FFMPEG & MEDIA ENGINE ====================

def telegram_media_metadata(media: Any, message: Any = None) -> Dict[str, Any]:
    """Normalize metadata available directly from a Telegram media object."""
    mime_type = normalize_mime(getattr(media, "mime_type", "") or "application/octet-stream")
    if getattr(message, "video", None) or is_video_mime(mime_type):
        kind = "video"
    elif getattr(message, "audio", None) or is_audio_mime(mime_type):
        kind = "audio"
    elif mime_type.startswith("image/") or getattr(message, "photo", None):
        kind = "image"
    else:
        kind = "document"

    language = (
        getattr(media, "language_code", None)
        or getattr(media, "language", None)
        or getattr(media, "lang", None)
        or "Undetermined"
    )
    title = getattr(media, "title", None) or ""
    performer = getattr(media, "performer", None) or ""
    audio_track = " — ".join(part for part in (title, performer) if part) or "Default Audio"
    return {
        "media_kind": kind,
        "mime_type": mime_type,
        "duration": int(getattr(media, "duration", 0) or 0),
        "width": int(getattr(media, "width", 0) or 0),
        "height": int(getattr(media, "height", 0) or 0),
        "language": str(language),
        "audio_track": audio_track,
        "audio_tracks": [],
        "subtitle_tracks": [],
        "caption": getattr(message, "caption", None) or ""
    }

FFMPEG_BIN = "ffmpeg"
FFPROBE_BIN = "ffprobe"

def _resolve_ffmpeg_binaries():
    global FFMPEG_BIN, FFPROBE_BIN
    sys_ffmpeg = shutil.which("ffmpeg")
    sys_ffprobe = shutil.which("ffprobe")
    if sys_ffmpeg and sys_ffprobe:
        FFMPEG_BIN = sys_ffmpeg
        FFPROBE_BIN = sys_ffprobe
        return

    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
        st_ffmpeg = shutil.which("ffmpeg")
        st_ffprobe = shutil.which("ffprobe")
        if st_ffmpeg and st_ffprobe:
            FFMPEG_BIN = st_ffmpeg
            FFPROBE_BIN = st_ffprobe
            return
    except Exception:
        pass

    known_dirs = [
        "/usr/bin",
        "/usr/local/bin",
        "/workspace/.heroku/python/lib/python3.12/site-packages/static_ffmpeg/bin/linux",
        "/workspace/.heroku/python/lib/python3.10/site-packages/static_ffmpeg/bin/linux"
    ]
    for kdir in known_dirs:
        ff = os.path.join(kdir, "ffmpeg")
        fp = os.path.join(kdir, "ffprobe")
        if os.path.exists(ff) and os.path.exists(fp):
            FFMPEG_BIN = ff
            FFPROBE_BIN = fp
            return

    FFMPEG_BIN = sys_ffmpeg or "ffmpeg"
    FFPROBE_BIN = sys_ffprobe or "ffprobe"

_resolve_ffmpeg_binaries()

LANG_MAP = {
    "eng": "English", "en": "English",
    "mal": "Malayalam", "ml": "Malayalam",
    "hin": "Hindi", "hi": "Hindi",
    "tam": "Tamil", "ta": "Tamil",
    "tel": "Telugu", "te": "Telugu",
    "kan": "Kannada", "kn": "Kannada",
    "ben": "Bengali", "bn": "Bengali",
    "mar": "Marathi", "mr": "Marathi",
    "guj": "Gujarati", "gu": "Gujarati",
    "pan": "Punjabi", "pa": "Punjabi",
    "urd": "Urdu", "ur": "Urdu",
    "ara": "Arabic", "ar": "Arabic",
    "spa": "Spanish", "es": "Spanish",
    "fre": "French", "fra": "French", "fr": "French",
    "ger": "German", "deu": "German", "de": "German",
    "ita": "Italian", "it": "Italian",
    "por": "Portuguese", "pt": "Portuguese",
    "rus": "Russian", "ru": "Russian",
    "chi": "Chinese", "zho": "Chinese", "zh": "Chinese",
    "jpn": "Japanese", "ja": "Japanese",
    "kor": "Korean", "ko": "Korean",
    "und": "Undetermined"
}

def resolve_lang_name(code: str) -> str:
    if not code:
        return "Undetermined"
    c = code.strip().lower()
    return LANG_MAP.get(c, c.upper())

class MediaAttributes(dict):
    def __init__(self, width: int = 1280, height: int = 720, duration: int = 0):
        super().__init__(width=width, height=height, duration=duration)

    def __iter__(self):
        return iter((self["width"], self["height"], self["duration"]))

    def __getitem__(self, item):
        if isinstance(item, int):
            return (self["width"], self["height"], self["duration"])[item]
        return super().__getitem__(item)

async def check_media_streams(file_path: str) -> Dict[str, Any]:
    cmd = [
        FFPROBE_BIN, "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        file_path
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        data = json.loads(stdout.decode('utf-8', errors='ignore'))
        has_video = False
        has_audio = False
        video_index = None
        audio_index = None

        streams = data.get("streams", [])
        for i, s in enumerate(streams):
            ctype = s.get("codec_type")
            disposition = s.get("disposition", {})
            if ctype == "video" and not disposition.get("attached_pic", False):
                has_video = True
                if video_index is None:
                    video_index = i
            elif ctype == "audio":
                has_audio = True
                if audio_index is None:
                    audio_index = i

        return {
            "has_video": has_video,
            "has_audio": has_audio,
            "video_index": video_index,
            "audio_index": audio_index,
            "stream_count": len(streams)
        }
    except Exception as e:
        logger.warning(f"Error checking media streams: {e}")
        return {"has_video": True, "has_audio": True, "video_index": 0, "audio_index": 0, "stream_count": 1}

async def get_media_attributes(file_path: str) -> MediaAttributes:
    cmd = [
        FFPROBE_BIN, "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        file_path
    ]
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        data = json.loads(stdout.decode('utf-8', errors='ignore'))
        duration = int(float(data.get("format", {}).get("duration", 0)))
        width, height = 1280, 720
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video" and not stream.get("disposition", {}).get("attached_pic", False):
                width = int(stream.get("width", 1280))
                height = int(stream.get("height", 720))
                break
        return MediaAttributes(width=width, height=height, duration=duration)
    except Exception as e:
        logger.warning(f"ffprobe extraction failed: {e}")
        return MediaAttributes(width=1280, height=720, duration=0)

async def get_detailed_mediainfo(file_path: str) -> Dict[str, Any]:
    cmd = [
        FFPROBE_BIN, "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        file_path
    ]
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        data = json.loads(stdout.decode('utf-8', errors='ignore'))

        fmt = data.get("format", {})
        streams = data.get("streams", [])

        info = {
            "container": fmt.get("format_long_name", fmt.get("format_name", "Unknown")),
            "duration": int(float(fmt.get("duration", 0))),
            "size": int(fmt.get("size", 0)),
            "bitrate": int(fmt.get("bit_rate", 0)),
            "video_streams": [],
            "audio_streams": [],
            "subtitle_streams": []
        }

        for s in streams:
            ctype = s.get("codec_type")
            if ctype == "video":
                info["video_streams"].append({
                    "codec": s.get("codec_name", "unknown").upper(),
                    "profile": s.get("profile", "N/A"),
                    "width": s.get("width", 0),
                    "height": s.get("height", 0),
                    "aspect_ratio": s.get("display_aspect_ratio", "N/A"),
                    "pix_fmt": s.get("pix_fmt", "yuv420p"),
                    "r_frame_rate": s.get("r_frame_rate", "N/A"),
                    "bitrate": int(s.get("bit_rate", 0)) if s.get("bit_rate") else 0
                })
            elif ctype == "audio":
                raw_lang = s.get("tags", {}).get("language", "und")
                lang_full = resolve_lang_name(raw_lang)
                info["audio_streams"].append({
                    "index": len(info["audio_streams"]) + 1,
                    "codec": s.get("codec_name", "unknown").upper(),
                    "channels": int(s.get("channels", 2)),
                    "channel_layout": s.get("channel_layout", "stereo"),
                    "sample_rate": s.get("sample_rate", "44100"),
                    "bitrate": int(s.get("bit_rate", 0)) if s.get("bit_rate") else 0,
                    "lang": lang_full,
                    "lang_code": raw_lang.lower(),
                    "language": lang_full,
                    "title": s.get("tags", {}).get("title", f"Track {len(info['audio_streams']) + 1}")
                })
            elif ctype == "subtitle":
                raw_lang = s.get("tags", {}).get("language", "und")
                lang_full = resolve_lang_name(raw_lang)
                info["subtitle_streams"].append({
                    "index": len(info["subtitle_streams"]) + 1,
                    "codec": s.get("codec_name", "unknown").upper(),
                    "lang": lang_full,
                    "lang_code": raw_lang.lower(),
                    "language": lang_full,
                    "title": s.get("tags", {}).get("title", f"Subtitle {len(info['subtitle_streams']) + 1}")
                })
        return info
    except Exception as e:
        logger.error(f"Error getting detailed mediainfo: {e}")
        return {}

async def extract_frame_screenshot(video_path: str, output_dir: str, duration: int) -> Optional[str]:
    out_path = os.path.join(output_dir, f"thumb_{os.path.basename(video_path)}.jpg")
    timestamp = max(1, duration // 2)
    cmd = [
        FFMPEG_BIN, "-ss", str(timestamp),
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2",
        "-y", out_path
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc.communicate()
        if os.path.exists(out_path):
            return out_path
    except Exception as e:
        logger.error(f"Error taking screenshot: {e}")
    return None

async def compress_audio(input_path: str, output_path: str) -> bool:
    cmd = [
        FFMPEG_BIN, "-y",
        "-i", input_path,
        "-vn",
        "-c:a", "aac",
        "-b:a", "96k",
        "-ac", "2",
        output_path
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE
        )
        _, err = await proc.communicate()
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True
        logger.error(f"Audio compression failed: {err.decode('utf-8', errors='ignore')}")
        return False
    except Exception as e:
        logger.error(f"Error compressing audio: {e}")
        return False

async def compress_media(
    input_path: str,
    output_path: str,
    crf: int = 28,
    preset: str = "superfast",
    scale_height: int = 720,
    progress_message = None,
    total_duration: int = 0
) -> bool:
    even_h = scale_height if scale_height % 2 == 0 else scale_height - 1
    if even_h > 0:
        vf_filter = f"scale=-2:{even_h}:flags=lanczos,setsar=1"
    else:
        vf_filter = "scale=trunc(iw/2)*2:trunc(ih/2)*2"

    primary_cmd = [
        FFMPEG_BIN, "-y",
        "-i", input_path,
        "-map", "0:v:0?",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", preset,
        "-crf", str(crf),
        "-vf", vf_filter,
        "-c:a", "aac",
        "-b:a", "128k",
        "-ac", "2",
        "-sn",
        "-movflags", "+faststart",
        "-max_muxing_queue_size", "9999",
        output_path
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *primary_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        last_update = 0
        time_regex = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")

        while True:
            line = await process.stderr.readline()
            if not line:
                break
            decoded = line.decode('utf-8', errors='ignore')
            match = time_regex.search(decoded)
            if match and total_duration > 0 and progress_message:
                hours, minutes, seconds = map(float, match.groups())
                current_seconds = hours * 3600 + minutes * 60 + seconds
                now = float(time.time())
                if now - last_update > 4:
                    last_update = now
                    pct = min(100.0, (current_seconds / total_duration) * 100)
                    filled = int(pct // 10)
                    bar = "▰" * filled + "▱" * (10 - filled)
                    text = (
                        f"⚡ **{to_smallcaps('compressing video')}**\n\n"
                        f"[{bar}] `{pct:.1f}%`\n"
                        f"⏱ **{to_smallcaps('processed')}** : `{int(current_seconds)}s / {total_duration}s`\n"
                        f"⚙️ **{to_smallcaps('preset')}** : `{preset}` | **{to_smallcaps('crf')}** : `{crf}`"
                        f"{format_watermark()}"
                    )
                    try:
                        await progress_message.edit_text(text)
                    except Exception:
                        pass

        await process.wait()
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return True
    except Exception as e:
        logger.warning(f"Primary compression attempt failed: {e}")

    fallback_cmd = [
        FFMPEG_BIN, "-y",
        "-i", input_path,
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ac", "2",
        "-sn",
        "-movflags", "+faststart",
        "-max_muxing_queue_size", "9999",
        output_path
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *fallback_cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return True
    except Exception:
        pass

    video_only_cmd = [
        FFMPEG_BIN, "-y",
        "-i", input_path,
        "-map", "0:v:0?",
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-an",
        "-movflags", "+faststart",
        output_path
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *video_only_cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        return os.path.exists(output_path) and os.path.getsize(output_path) > 1000
    except Exception:
        return False

def parse_time_range(text: str) -> Tuple[Optional[float], Optional[float]]:
    cleaned = text.strip().lower().replace("to", " ").replace("-", " ").replace(",", " ")
    tokens = [t for t in cleaned.split() if t]
    if len(tokens) != 2:
        return None, None

    def parse_one(val: str) -> Optional[float]:
        if re.match(r"^\d+(\.\d+)?$", val):
            return float(val)
        parts = val.split(":")
        try:
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + float(parts[1])
        except Exception:
            return None
        return None

    s = parse_one(tokens[0])
    e = parse_one(tokens[1])
    if s is not None and e is not None and e > s:
        return s, e
    return None, None

async def trim_video(video_path: str, output_path: str, start_sec: float, end_sec: float) -> bool:
    duration = end_sec - start_sec
    copy_cmd = [
        FFMPEG_BIN, "-y",
        "-ss", str(start_sec),
        "-i", video_path,
        "-t", str(duration),
        "-c", "copy",
        "-avoid_negative_ts", "1",
        "-movflags", "+faststart",
        output_path
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *copy_cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return True
    except Exception:
        pass

    transcode_cmd = [
        FFMPEG_BIN, "-y",
        "-ss", str(start_sec),
        "-i", video_path,
        "-t", str(duration),
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "22",
        "-c:a", "copy",
        "-movflags", "+faststart",
        output_path
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *transcode_cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        return os.path.exists(output_path) and os.path.getsize(output_path) > 1000
    except Exception:
        return False

async def extract_all_audio_tracks(video_path: str, output_dir: str) -> List[Dict[str, Any]]:
    cmd = [
        FFPROBE_BIN, "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        video_path
    ]
    tracks = []
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        data = json.loads(stdout.decode('utf-8', errors='ignore'))
        audio_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]

        base_name = sanitize_filename(os.path.splitext(os.path.basename(video_path))[0])

        for idx, s in enumerate(audio_streams):
            raw_lang = s.get("tags", {}).get("language", "und").lower()
            lang_name = resolve_lang_name(raw_lang)
            title = s.get("tags", {}).get("title", f"Track {idx+1}")
            codec = s.get("codec_name", "mp3").lower()
            channels = int(s.get("channels", 2))
            dur = int(float(s.get("duration", 0)))

            ext = "mp3" if codec in ["mp3", "mpeg"] else ("m4a" if codec in ["aac", "alac"] else "mp3")
            out_filename = f"{base_name}_audio_{idx+1}_{raw_lang}.{ext}"
            out_filepath = os.path.join(output_dir, out_filename)

            if ext == "mp3" and codec in ["mp3", "mpeg"]:
                ext_cmd = [FFMPEG_BIN, "-y", "-i", video_path, "-map", f"0:a:{idx}", "-vn", "-c:a", "copy", out_filepath]
            elif ext == "m4a" and codec in ["aac"]:
                ext_cmd = [FFMPEG_BIN, "-y", "-i", video_path, "-map", f"0:a:{idx}", "-vn", "-c:a", "copy", out_filepath]
            else:
                ext_cmd = [FFMPEG_BIN, "-y", "-i", video_path, "-map", f"0:a:{idx}", "-vn", "-c:a", "libmp3lame", "-b:a", "192k", out_filepath]

            p = await asyncio.create_subprocess_exec(
                *ext_cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
            )
            await p.communicate()

            if os.path.exists(out_filepath) and os.path.getsize(out_filepath) > 0:
                tracks.append({
                    "path": out_filepath,
                    "index": idx + 1,
                    "language": lang_name,
                    "lang_code": raw_lang,
                    "title": title,
                    "codec": codec.upper(),
                    "channels": channels,
                    "duration": dur
                })
    except Exception as e:
        logger.error(f"Error extracting audio tracks: {e}")
    return tracks

async def extract_all_subtitle_tracks(video_path: str, output_dir: str) -> List[Dict[str, Any]]:
    cmd = [
        FFPROBE_BIN, "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        video_path
    ]
    tracks = []
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        data = json.loads(stdout.decode('utf-8', errors='ignore'))
        sub_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "subtitle"]

        base_name = sanitize_filename(os.path.splitext(os.path.basename(video_path))[0])

        for idx, s in enumerate(sub_streams):
            raw_lang = s.get("tags", {}).get("language", "und").lower()
            lang_name = resolve_lang_name(raw_lang)
            title = s.get("tags", {}).get("title", f"Sub {idx+1}")
            codec = s.get("codec_name", "srt").lower()

            ext = "ass" if "ass" in codec or "ssa" in codec else "srt"
            out_filename = f"{base_name}_sub_{idx+1}_{raw_lang}.{ext}"
            out_filepath = os.path.join(output_dir, out_filename)

            if ext == "ass":
                ext_cmd = [FFMPEG_BIN, "-y", "-i", video_path, "-map", f"0:s:{idx}", "-c:s", "copy", out_filepath]
            else:
                ext_cmd = [FFMPEG_BIN, "-y", "-i", video_path, "-map", f"0:s:{idx}", "-c:s", "srt", out_filepath]

            p = await asyncio.create_subprocess_exec(
                *ext_cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
            )
            await p.communicate()

            if os.path.exists(out_filepath) and os.path.getsize(out_filepath) > 0:
                tracks.append({
                    "path": out_filepath,
                    "index": idx + 1,
                    "language": lang_name,
                    "lang_code": raw_lang,
                    "title": title,
                    "codec": codec.upper()
                })
    except Exception as e:
        logger.error(f"Error extracting subtitle tracks: {e}")
    return tracks

async def add_audio_to_video(
    video_path: str,
    audio_path: str,
    output_path: str,
    replace_existing: bool = False,
    language: str = "und"
) -> bool:
    if replace_existing:
        cmd = [
            FFMPEG_BIN, "-y",
            "-i", video_path,
            "-i", audio_path,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "copy",
            "-metadata:s:a:0", f"language={language}",
            "-max_muxing_queue_size", "9999",
            output_path
        ]
    else:
        cmd = [
            FFMPEG_BIN, "-y",
            "-i", video_path,
            "-i", audio_path,
            "-map", "0:v",
            "-map", "0:a?",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "copy",
            "-max_muxing_queue_size", "9999",
            output_path
        ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return True
    except Exception:
        pass

    fb_cmd = [
        FFMPEG_BIN, "-y",
        "-i", video_path,
        "-i", audio_path,
        "-map", "0:v:0" if replace_existing else "0:v",
        "-map", "1:a:0" if replace_existing else "0:a?",
        *(["-map", "1:a:0"] if not replace_existing else []),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-max_muxing_queue_size", "9999",
        output_path
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *fb_cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
        )
        await proc.communicate()
        return os.path.exists(output_path) and os.path.getsize(output_path) > 1000
    except Exception:
        return False

async def add_subtitle_to_video(
    video_path: str,
    subtitle_path: str,
    output_path: str,
    language: str = "eng"
) -> bool:
    cmd = [
        FFMPEG_BIN, "-y",
        "-i", video_path,
        "-i", subtitle_path,
        "-map", "0",
        "-map", "1:0",
        "-c", "copy",
        "-c:s", "srt" if subtitle_path.endswith(".srt") else "copy",
        "-metadata:s:s:0", f"language={language}",
        "-max_muxing_queue_size", "9999",
        output_path
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        return os.path.exists(output_path) and os.path.getsize(output_path) > 1000
    except Exception:
        return False

async def compress_to_target_size(
    input_path: str,
    output_path: str,
    target_size_mb: float,
    duration_sec: int,
    scale_height: int = 720
) -> bool:
    dur = max(1, duration_sec)
    total_kbits = target_size_mb * 8192
    audio_bitrate_kb = 96
    video_bitrate_kb = max(80, int((total_kbits / dur) - audio_bitrate_kb))

    even_h = scale_height if scale_height % 2 == 0 else scale_height - 1
    if even_h > 0:
        vf_filter = f"scale=-2:{even_h}:flags=lanczos,setsar=1"
    else:
        vf_filter = "scale=trunc(iw/2)*2:trunc(ih/2)*2"

    cmd = [
        FFMPEG_BIN, "-y",
        "-i", input_path,
        "-map", "0:v:0?",
        "-map", "0:a?",
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-b:v", f"{video_bitrate_kb}k",
        "-maxrate", f"{int(video_bitrate_kb * 1.5)}k",
        "-bufsize", f"{int(video_bitrate_kb * 2)}k",
        "-pix_fmt", "yuv420p",
        "-preset", "veryfast",
        "-c:a", "aac",
        "-b:a", f"{audio_bitrate_kb}k",
        "-ac", "2",
        "-sn",
        "-movflags", "+faststart",
        "-max_muxing_queue_size", "9999",
        output_path
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return True
    except Exception:
        pass

    fb_cmd = [
        FFMPEG_BIN, "-y",
        "-i", input_path,
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v", "libx264",
        "-b:v", f"{video_bitrate_kb}k",
        "-pix_fmt", "yuv420p",
        "-preset", "ultrafast",
        "-c:a", "aac",
        "-b:a", "96k",
        "-ac", "2",
        "-sn",
        "-movflags", "+faststart",
        output_path
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *fb_cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        return os.path.exists(output_path) and os.path.getsize(output_path) > 1000
    except Exception:
        return False


# ==================== 2. THUMBNAIL SERVICE ====================

GLOBAL_THUMB_CACHE = os.path.join(Config.DOWNLOAD_DIR, "global_tham_cache.jpg")

async def download_thumbnail_url(url: str, target_path: str) -> Optional[str]:
    if not url or not is_valid_url(url):
        return None
    try:
        if aiohttp is not None:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        if aiofiles:
                            async with aiofiles.open(target_path, "wb") as f:
                                await f.write(data)
                        else:
                            with open(target_path, "wb") as f:
                                f.write(data)
                        return target_path
        else:
            loop = asyncio.get_running_loop()
            def _sync_dl():
                req = urllib.request.Request(url, headers={"User-Agent": "MMW-ProBot/3.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status == 200:
                        with open(target_path, "wb") as f:
                            f.write(resp.read())
                        return target_path
                return None
            return await loop.run_in_executor(None, _sync_dl)
    except Exception as e:
        logger.warning(f"Failed to download thumbnail from URL {url}: {e}")
    return None

async def resolve_thumbnail(
    client: Any,
    user_id: int,
    temp_dir_or_thumb_id: Any = None,
    video_path: Optional[str] = None,
    duration: int = 0,
    temp_dir: Optional[str] = None
) -> Optional[str]:
    resolved_dir = temp_dir
    if not resolved_dir:
        if isinstance(temp_dir_or_thumb_id, str) and os.path.isdir(temp_dir_or_thumb_id):
            resolved_dir = temp_dir_or_thumb_id
        elif video_path and os.path.exists(video_path):
            resolved_dir = os.path.dirname(video_path)
        else:
            resolved_dir = os.path.join(Config.DOWNLOAD_DIR, str(user_id))
    os.makedirs(resolved_dir, exist_ok=True)

    user = await user_repo.get_user(user_id)
    thumb_id = None
    if user and user.get("thumb_id"):
        thumb_id = user["thumb_id"]
    elif isinstance(temp_dir_or_thumb_id, str) and not os.path.isdir(temp_dir_or_thumb_id):
        thumb_id = temp_dir_or_thumb_id

    if thumb_id and client:
        try:
            custom_path = os.path.join(resolved_dir, "custom_thumb.jpg")
            return await client.download_media(thumb_id, file_name=custom_path)
        except Exception as e:
            logger.warning(f"Error fetching user custom thumbnail: {e}")

    user_tham = user.get("tham_url") if user else None
    if user_tham:
        user_thumb_path = os.path.join(resolved_dir, "user_tham.jpg")
        downloaded = await download_thumbnail_url(user_tham, user_thumb_path)
        if downloaded and os.path.exists(downloaded):
            return downloaded

    if Config.THAM_URL:
        if os.path.exists(GLOBAL_THUMB_CACHE) and os.path.getsize(GLOBAL_THUMB_CACHE) > 0:
            return GLOBAL_THUMB_CACHE
        downloaded = await download_thumbnail_url(Config.THAM_URL, GLOBAL_THUMB_CACHE)
        if downloaded and os.path.exists(downloaded):
            return downloaded

    if video_path and os.path.exists(video_path):
        return await extract_frame_screenshot(video_path, resolved_dir, duration)

    return None


# ==================== 3. CAPTION SERVICE ====================

DEFAULT_CAPTION = (
    "📁 **{filename}**\n\n"
    "• 📦 **sɪᴢᴇ** : `{filesize}`\n"
    "• ⏱️ **ᴅᴜʀᴀᴛɪᴏɴ** : `{duration}`\n"
    "• 🌐 **ʟᴀɴɢᴜᴀɢᴇ** : `{language}`\n"
    "• 🎧 **ᴀᴜᴅɪᴏ** : `{audio_track}`\n"
    "• 🏷️ **ᴛʏᴘᴇ** : `{ext}`\n"
    "• 🆔 **ғɪʟᴇ ɪᴅ** : `{file_id}`\n"
    "• 📢 **ᴡᴀᴛᴇʀᴍᴀʀᴋ** : [{watermark}]({watermark_url})"
)

async def format_caption(
    user_or_id: Union[int, Dict[str, Any], Any],
    file_name: str,
    file_size_str: Any = "0 B",
    duration_str: Any = "0s",
    ext: str = "",
    file_caption: str = "",
    language: str = "Undetermined",
    audio_track: str = "Default Audio",
    file_id: str = "",
    resolution: str = "N/A",
    video_codec: str = "N/A",
    audio_codec: str = "N/A",
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    user: Optional[Dict[str, Any]] = None
    if isinstance(user_or_id, dict):
        user = user_or_id
    elif isinstance(user_or_id, int):
        user = await user_repo.get_user(user_or_id)
    elif user_or_id is not None:
        uid = getattr(user_or_id, "id", None) or getattr(user_or_id, "user_id", None)
        if uid:
            user = await user_repo.get_user(int(uid))

    if isinstance(file_size_str, (int, float)):
        file_size_str = humanbytes(int(file_size_str))

    if isinstance(duration_str, (int, float)):
        duration_str = time_formatter(seconds=int(duration_str))

    user_custom = user.get("custom_caption") if user else None
    user_caps_list = user.get("captions_list", []) if user else []
    if user is not None and user.get("auto_caption") is False:
        caption = file_caption or ""
        if Config.WATERMARK not in caption:
            caption += format_watermark()
        return caption[:1024]

    template = user_custom
    if not template and user_caps_list:
        template = user_caps_list[0]
    if not template and file_caption:
        template = file_caption
    if not template:
        template = DEFAULT_CAPTION

    if metadata:
        if not language or language == "Undetermined":
            langs = [a.get("language") or a.get("lang") for a in metadata.get("audio_streams", []) if (a.get("language") or a.get("lang"))]
            if langs:
                language = ", ".join(sorted(set([str(l).title() for l in langs])))
        if not audio_track or audio_track == "Default Audio":
            auds = [f"{a.get('codec', '')} {a.get('channels', 2)}ch".strip() for a in metadata.get("audio_streams", [])]
            if auds:
                audio_track = ", ".join(auds)
        if not resolution or resolution == "N/A":
            v_streams = metadata.get("video_streams", [])
            if v_streams:
                resolution = f"{v_streams[0].get('width', 0)}x{v_streams[0].get('height', 0)}"
        if not video_codec or video_codec == "N/A":
            v_streams = metadata.get("video_streams", [])
            if v_streams:
                video_codec = v_streams[0].get("codec", "N/A")
        if not audio_codec or audio_codec == "N/A":
            a_streams = metadata.get("audio_streams", [])
            if a_streams:
                audio_codec = a_streams[0].get("codec", "N/A")

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_str = now_utc.strftime("%Y-%m-%d %H:%M UTC")
    time_str = now_utc.strftime("%H:%M:%S UTC")

    fmt_dict = {
        "filename": file_name,
        "file_name": file_name,
        "filesize": file_size_str,
        "file_size": file_size_str,
        "duration": duration_str,
        "language": language or "Undetermined",
        "languages": language or "Undetermined",
        "audio_track": audio_track or "Stereo 2.0",
        "autotrack": audio_track or "Stereo 2.0",
        "audio_tracks": audio_track or "Stereo 2.0",
        "caption": file_caption or "",
        "file_caption": file_caption or "",
        "original_caption": file_caption or "",
        "file_id": file_id or "N/A",
        "fileid": file_id or "N/A",
        "resolution": resolution or "N/A",
        "video_codec": video_codec or "N/A",
        "audio_codec": audio_codec or "N/A",
        "ext": ext,
        "watermark": Config.WATERMARK,
        "watermark_url": Config.WATERMARK_URL,
        "date": now_str,
        "time": time_str,
        "current_time": time_str,
        "time_str": time_str
    }

    try:
        class SafeDict(dict):
            def __missing__(self, key):
                return f"{{{key}}}"
        caption = template.format_map(SafeDict(**fmt_dict))
    except Exception:
        caption = template

    if Config.WATERMARK not in caption:
        caption += format_watermark()

    if len(caption) > 1024:
        wm = format_watermark()
        avail = 1024 - len(wm) - 4
        caption = caption[:max(0, avail)] + "...\n" + wm

    return caption

async def extract_and_format_caption(
    user_id: int,
    file_path: str,
    original_caption: str = "",
    file_id: str = ""
) -> str:
    file_name = os.path.basename(file_path)
    file_size_bytes = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    file_size_str = humanbytes(file_size_bytes)
    ext = os.path.splitext(file_name)[1].replace(".", "").lower()

    metadata = await get_detailed_mediainfo(file_path)
    dur_sec = metadata.get("duration", 0)
    duration_str = time_formatter(seconds=dur_sec) if dur_sec > 0 else "0s"

    return await format_caption(
        user_or_id=user_id,
        file_name=file_name,
        file_size_str=file_size_str,
        duration_str=duration_str,
        ext=ext,
        file_caption=original_caption,
        file_id=file_id,
        metadata=metadata
    )


# ==================== 4. AUTO-DELETE SERVICE ====================

async def schedule_deletion(chat_id: int, message_id: int, seconds: int):
    if seconds <= 0:
        return
    delete_at = float(time.time()) + float(seconds)
    await chat_repo.create_auto_delete_task(chat_id, message_id, delete_at)

async def run_autodelete_sweeper(client: Any):
    logger.info("⏱️ Auto-Delete background sweeper started.")
    while True:
        try:
            curr_time = float(time.time())
            expired_tasks = await chat_repo.get_expired_auto_delete(curr_time)
            if expired_tasks:
                chat_buckets = defaultdict(list)
                for item in expired_tasks:
                    chat_buckets[item["chat_id"]].append(item["message_id"])

                for chat_id, msg_ids in chat_buckets.items():
                    for i in range(0, len(msg_ids), 100):
                        chunk = msg_ids[i:i+100]
                        try:
                            await client.delete_messages(chat_id=chat_id, message_ids=chunk)
                        except Exception as e:
                            logger.debug(f"Failed deleting batch in {chat_id}: {e}")
                    for mid in msg_ids:
                        await chat_repo.delete_auto_delete_task(chat_id, mid)
        except Exception as e:
            logger.error(f"Auto-delete sweeper exception: {e}")
        await asyncio.sleep(6)


# ==================== 5. KEEPALIVE & 24H RESTART SERVICE ====================

RESTART_MARKER_FILE = os.path.join(Config.DOWNLOAD_DIR, ".restarted_marker")

class KeepAliveManager:
    def __init__(self, bot, target_url: str = None, interval: int = 6):
        self.bot = bot
        self.target_url = (target_url or Config.BASE_URL).rstrip("/")
        self.local_url = f"http://127.0.0.1:{Config.PORT}"
        self.interval = interval
        self._current_type_idx = 0

    async def ping_type_1_aiohttp_get(self) -> bool:
        try:
            url = f"{self.target_url}/health"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                    return resp.status in [200, 204, 301, 302]
        except Exception:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.local_url}/health", timeout=aiohttp.ClientTimeout(total=3)) as resp:
                        return resp.status in [200, 204]
            except Exception:
                return False

    async def ping_type_2_aiohttp_head(self) -> bool:
        try:
            url = f"{self.target_url}/health"
            async with aiohttp.ClientSession() as session:
                async with session.head(url, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                    return resp.status in [200, 204, 301, 302]
        except Exception:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.head(f"{self.local_url}/health", timeout=aiohttp.ClientTimeout(total=3)) as resp:
                        return resp.status in [200, 204]
            except Exception:
                return False

    async def ping_type_3_urllib_get(self) -> bool:
        loop = asyncio.get_running_loop()
        def _sync_urllib():
            for target in [f"{self.target_url}/health", f"{self.local_url}/health"]:
                try:
                    req = urllib.request.Request(target, headers={"User-Agent": "MMW-KeepAlive-Ping/2.5"})
                    with urllib.request.urlopen(req, timeout=4) as response:
                        if response.status in [200, 204, 301, 302]:
                            return True
                except Exception:
                    continue
            return False
        return await loop.run_in_executor(None, _sync_urllib)

    async def ping_type_4_http_client(self) -> bool:
        loop = asyncio.get_running_loop()
        def _sync_http_client():
            try:
                conn = http.client.HTTPConnection("127.0.0.1", Config.PORT, timeout=3)
                conn.request("GET", "/health")
                resp = conn.getresponse()
                conn.close()
                return resp.status in [200, 204]
            except Exception:
                return False
        return await loop.run_in_executor(None, _sync_http_client)

    async def ping_type_5_tcp_socket(self) -> bool:
        loop = asyncio.get_running_loop()
        def _sync_tcp_ping():
            try:
                sock = socket.create_connection(("127.0.0.1", Config.PORT), timeout=3)
                sock.close()
                return True
            except Exception:
                return False
        return await loop.run_in_executor(None, _sync_tcp_ping)

    async def ping_type_6_telegram_ping(self) -> bool:
        try:
            if self.bot and getattr(self.bot, "is_connected", False):
                await self.bot.get_me()
                return True
        except Exception:
            pass
        return False

    async def execute_ping(self, ping_type: int = None) -> bool:
        if ping_type is None:
            self._current_type_idx = (self._current_type_idx % 6) + 1
            ptype = self._current_type_idx
        else:
            ptype = ping_type

        handlers = {
            1: self.ping_type_1_aiohttp_get,
            2: self.ping_type_2_aiohttp_head,
            3: self.ping_type_3_urllib_get,
            4: self.ping_type_4_http_client,
            5: self.ping_type_5_tcp_socket,
            6: self.ping_type_6_telegram_ping
        }
        handler = handlers.get(ptype, self.ping_type_1_aiohttp_get)
        return await handler()

async def run_keepalive_worker(bot, interval: int = 6):
    manager = KeepAliveManager(bot=bot, interval=interval)
    logger.info(f"💓 KeepAlive Engine active (interval: {interval}s).")
    await asyncio.sleep(5)
    while True:
        try:
            await manager.execute_ping()
        except Exception:
            pass
        await asyncio.sleep(interval)

async def send_restart_notification(bot):
    message_text = (
        f"🔄 **{to_smallcaps('bot restarted successfully!')}** ⚡\n\n"
        f"• 🚀 **{to_smallcaps('engine')}** : `{to_smallcaps('adaptive range stream & pro plugins ready')}`\n"
        f"• 🍃 **{to_smallcaps('database')}** : `{to_smallcaps('single unified db + fast cache')}`"
        f"{format_watermark()}"
    )
    for admin_id in Config.ADMINS:
        try:
            await bot.send_message(chat_id=admin_id, text=message_text)
        except Exception:
            pass

async def schedule_24h_restart(bot, interval: int = 86400):
    logger.info(f"🔄 24-Hour Auto-Restart scheduler active ({interval}s).")
    while True:
        await asyncio.sleep(interval)
        try:
            os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)
            with open(RESTART_MARKER_FILE, "w") as f:
                f.write(f"{float(time.time())}")
        except Exception:
            pass
        await send_restart_notification(bot)
        try:
            await bot.stop()
        except Exception:
            pass
        os.execl(sys.executable, sys.executable, *sys.argv)
