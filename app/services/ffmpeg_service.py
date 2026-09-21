import os
import asyncio
import json
import re
from typing import Tuple, Optional, Dict, Any
from app.utils.logger import logger
from app.utils.font import to_smallcaps
from config import Config

async def get_media_attributes(file_path: str) -> Tuple[int, int, int]:
    cmd = [
        "ffprobe", "-v", "quiet",
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
        data = json.loads(stdout.decode())
        duration = int(float(data.get("format", {}).get("duration", 0)))
        width, height = 1280, 720
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                width = int(stream.get("width", 1280))
                height = int(stream.get("height", 720))
                break
        return width, height, duration
    except Exception as e:
        logger.warning(f"ffprobe extraction failed: {e}")
        return 1280, 720, 0

async def get_detailed_mediainfo(file_path: str) -> Dict[str, Any]:
    cmd = [
        "ffprobe", "-v", "quiet",
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
        data = json.loads(stdout.decode())
        
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
                info["audio_streams"].append({
                    "codec": s.get("codec_name", "unknown").upper(),
                    "channels": s.get("channels", 2),
                    "channel_layout": s.get("channel_layout", "stereo"),
                    "sample_rate": s.get("sample_rate", "44100"),
                    "bitrate": int(s.get("bit_rate", 0)) if s.get("bit_rate") else 0,
                    "lang": s.get("tags", {}).get("language", "und")
                })
            elif ctype == "subtitle":
                info["subtitle_streams"].append({
                    "codec": s.get("codec_name", "unknown").upper(),
                    "lang": s.get("tags", {}).get("language", "und"),
                    "title": s.get("tags", {}).get("title", "Subtitle")
                })
        return info
    except Exception as e:
        logger.error(f"Error getting detailed mediainfo: {e}")
        return {}

async def extract_frame_screenshot(video_path: str, output_dir: str, duration: int) -> Optional[str]:
    out_path = os.path.join(output_dir, f"thumb_{os.path.basename(video_path)}.jpg")
    timestamp = max(1, duration // 2)
    cmd = [
        "ffmpeg", "-ss", str(timestamp),
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
    vf_filter = f"scale=-2:{even_h}:flags=lanczos,setsar=1" if even_h > 0 else "null"
    cmd = [
        "ffmpeg", "-i", input_path,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", preset,
        "-crf", str(crf),
        "-vf", vf_filter,
        "-c:a", "aac",
        "-b:a", "128k",
        "-y", output_path
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
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
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        logger.error(f"FFmpeg Compression exception: {e}")
        return False
