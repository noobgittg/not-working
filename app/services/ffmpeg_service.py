import os
import sys
import shutil
import asyncio
import json
import re
from typing import Tuple, Optional, Dict, Any, List
from app.utils.logger import logger
from app.utils.font import to_smallcaps
from app.utils.helpers import sanitize_filename
from config import Config

# ==================== BINARY RESOLUTION ====================
FFMPEG_BIN = "ffmpeg"
FFPROBE_BIN = "ffprobe"

def _resolve_ffmpeg_binaries():
    global FFMPEG_BIN, FFPROBE_BIN
    
    # 1. System PATH
    sys_ffmpeg = shutil.which("ffmpeg")
    sys_ffprobe = shutil.which("ffprobe")
    if sys_ffmpeg and sys_ffprobe:
        FFMPEG_BIN = sys_ffmpeg
        FFPROBE_BIN = sys_ffprobe
        logger.info(f"Resolved system FFmpeg binaries -> ffmpeg: '{FFMPEG_BIN}', ffprobe: '{FFPROBE_BIN}'")
        return

    # 2. Try static_ffmpeg if available
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
        st_ffmpeg = shutil.which("ffmpeg")
        st_ffprobe = shutil.which("ffprobe")
        if st_ffmpeg and st_ffprobe:
            FFMPEG_BIN = st_ffmpeg
            FFPROBE_BIN = st_ffprobe
            logger.info(f"Resolved static_ffmpeg binaries -> ffmpeg: '{FFMPEG_BIN}', ffprobe: '{FFPROBE_BIN}'")
            return
    except Exception as e:
        logger.debug(f"static_ffmpeg check skipped: {e}")

    # 3. Common known paths on Linux / Heroku / Koyeb
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
            logger.info(f"Resolved FFmpeg binaries from known path -> ffmpeg: '{FFMPEG_BIN}', ffprobe: '{FFPROBE_BIN}'")
            return

    FFMPEG_BIN = sys_ffmpeg or "ffmpeg"
    FFPROBE_BIN = sys_ffprobe or "ffprobe"
    logger.info(f"Defaulting FFmpeg binaries -> ffmpeg: '{FFMPEG_BIN}', ffprobe: '{FFPROBE_BIN}'")

_resolve_ffmpeg_binaries()

# Language code to human readable name mapping
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
    """
    Dual-compatible container that behaves as both a dict (attrs['duration'])
    and a 3-tuple (width, height, duration) for tuple unpacking.
    """
    def __init__(self, width: int = 1280, height: int = 720, duration: int = 0):
        super().__init__(width=width, height=height, duration=duration)

    def __iter__(self):
        return iter((self["width"], self["height"], self["duration"]))

    def __getitem__(self, item):
        if isinstance(item, int):
            return (self["width"], self["height"], self["duration"])[item]
        return super().__getitem__(item)

async def check_media_streams(file_path: str) -> Dict[str, Any]:
    """
    Checks if a media file has decodable video or audio streams using ffprobe.
    Distinguishes actual video streams from cover art (attached_pic).
    """
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
    """
    Extracts width, height, and duration using ffprobe, returning a MediaAttributes
    object that supports both dict indexing and tuple unpacking.
    """
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
    """
    Extracts deep metadata from container formats, video streams, audio streams,
    and subtitle streams.
    """
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
                info["audio_streams"].append({
                    "index": len(info["audio_streams"]) + 1,
                    "codec": s.get("codec_name", "unknown").upper(),
                    "channels": int(s.get("channels", 2)),
                    "channel_layout": s.get("channel_layout", "stereo"),
                    "sample_rate": s.get("sample_rate", "44100"),
                    "bitrate": int(s.get("bit_rate", 0)) if s.get("bit_rate") else 0,
                    "lang_code": raw_lang.lower(),
                    "language": resolve_lang_name(raw_lang),
                    "title": s.get("tags", {}).get("title", f"Track {len(info['audio_streams']) + 1}")
                })
            elif ctype == "subtitle":
                raw_lang = s.get("tags", {}).get("language", "und")
                info["subtitle_streams"].append({
                    "index": len(info["subtitle_streams"]) + 1,
                    "codec": s.get("codec_name", "unknown").upper(),
                    "lang_code": raw_lang.lower(),
                    "language": resolve_lang_name(raw_lang),
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
    """Compresses an audio-only stream into high-efficiency AAC stereo."""
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
    """
    Compresses video media into universally compatible H.264/AAC with strict
    even-dimension scaling for yuv420p to avoid odd-dimension ffmpeg crashes.
    """
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
                now = asyncio.get_event_loop().time()
                if now - last_update > 4:
                    last_update = now
                    pct = min(100.0, (current_seconds / total_duration) * 100)
                    filled = int(pct // 10)
                    bar = "▰" * filled + "▱" * (10 - filled)
                    text = (
                        f"⚡ **{to_smallcaps('ᴄᴏᴍᴘʀᴇssɪɴɢ ᴠɪᴅᴇᴏ')}**\n\n"
                        f"[{bar}] `{pct:.1f}%`\n"
                        f"⏱ **{to_smallcaps('ᴘʀᴏᴄᴇssᴇᴅ')}** : `{int(current_seconds)}s / {total_duration}s`\n"
                        f"⚙️ **{to_smallcaps('ᴘʀᴇsᴇᴛ')}** : `{preset}` | **{to_smallcaps('ᴄʀғ')}** : `{crf}`\n\n"
                        f"⚡ **{to_smallcaps('ᴘᴏᴡᴇʀᴇᴅ ʙʏ')}** : [{Config.WATERMARK}]({Config.WATERMARK_URL})"
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

    logger.info("Executing universal fallback compression...")
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
        _, err = await proc.communicate()
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return True
        logger.warning(f"Fallback compression failed: {err.decode('utf-8', errors='ignore')}")
    except Exception as e:
        logger.warning(f"Fallback compression exception: {e}")

    # Fallback 2: video-only transcode (if source has incompatible/corrupt audio track)
    logger.info("Executing video-only fallback compression...")
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
        _, err = await proc.communicate()
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return True
        logger.error(f"Video-only compression failed: {err.decode('utf-8', errors='ignore')}")
        return False
    except Exception as e:
        logger.error(f"Video-only fallback exception: {e}")
        return False

# ==================== ADVANCE FILE PRO FEATURES ====================

def parse_time_range(text: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Parses flexible time range strings like:
    '00:01:30 00:05:00', '1:30 to 5:00', '90 - 300', '00:01:30, 00:05:00'
    Returns (start_sec, end_sec) or (None, None).
    """
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
    """
    Trims a video segment between start_sec and end_sec.
    Uses ultra-fast stream copy first, falling back to ultrafast libx264 transcode.
    """
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
        _, err = await proc.communicate()
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return True
        logger.warning(f"Fast stream copy trim failed, falling back to transcode: {err.decode('utf-8', errors='ignore')}")
    except Exception as e:
        logger.warning(f"Stream copy trim exception: {e}")

    # Fallback to ultrafast transcode
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
    except Exception as e:
        logger.error(f"Transcode trim exception: {e}")
        return False

async def extract_all_audio_tracks(video_path: str, output_dir: str) -> List[Dict[str, Any]]:
    """
    Extracts every audio track present in the video file into individual audio files.
    Returns a list of dicts with track metadata and file paths.
    """
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
    """
    Extracts every subtitle track in the video file into .srt or .ass files.
    Returns a list of dicts with subtitle metadata and file paths.
    """
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
    """
    Merges an audio track into a video container.
    """
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
        _, err = await proc.communicate()
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return True
        logger.warning(f"Direct stream copy mux audio failed, retrying with AAC transcode: {err.decode('utf-8', errors='ignore')}")
    except Exception as e:
        logger.warning(f"Audio mux error: {e}")

    # Fallback with audio transcoding
    fb_cmd = [
        FFMPEG_BIN, "-y",
        "-i", video_path,
        "-i", audio_path,
        "-map", "0:v:0" if replace_existing else "0:v",
        "-map", "1:a:0" if replace_existing else "0:a?",
        *([ "-map", "1:a:0" ] if not replace_existing else []),
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
    except Exception as e:
        logger.error(f"Fallback audio mux failed: {e}")
        return False

async def add_subtitle_to_video(
    video_path: str,
    subtitle_path: str,
    output_path: str,
    language: str = "eng"
) -> bool:
    """
    Soft-muxes a subtitle file (.srt, .ass) into the video container without re-encoding video.
    """
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
        _, err = await proc.communicate()
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return True
        logger.error(f"Failed to mux subtitle: {err.decode('utf-8', errors='ignore')}")
        return False
    except Exception as e:
        logger.error(f"Subtitle mux error: {e}")
        return False
