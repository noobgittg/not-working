import asyncio
import json
import os
import re
from typing import Any, Dict, Optional

from app.utils.font import to_smallcaps
from app.utils.logger import logger
from config import Config


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


async def _run_ffprobe(file_path: str) -> Dict[str, Any]:
    if not os.path.isfile(file_path):
        return {}
    cmd = [
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", file_path,
    ]
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            logger.warning("ffprobe failed for %s: %s", file_path, stderr.decode(errors="ignore")[-1000:])
            return {}
        return json.loads(stdout.decode("utf-8", errors="ignore") or "{}")
    except FileNotFoundError:
        logger.error("ffprobe is not installed or not in PATH")
    except Exception as exc:
        logger.warning("ffprobe extraction failed: %s", exc)
    return {}


async def get_media_attributes(file_path: str) -> Dict[str, Any]:
    """Return a stable dictionary contract used by rename/compress/stream code."""
    data = await _run_ffprobe(file_path)
    fmt = data.get("format") or {}
    streams = data.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

    return {
        "width": _safe_int(video.get("width"), 0) if video else 0,
        "height": _safe_int(video.get("height"), 0) if video else 0,
        "duration": _safe_int(fmt.get("duration"), 0),
        "size": _safe_int(fmt.get("size"), 0),
        "has_video": bool(video),
        "has_audio": bool(audio),
        "video_codec": video.get("codec_name") if video else None,
        "audio_codec": audio.get("codec_name") if audio else None,
        "format": fmt.get("format_name", "unknown"),
        "format_long": fmt.get("format_long_name", "Unknown"),
    }


async def get_detailed_mediainfo(file_path: str) -> Dict[str, Any]:
    data = await _run_ffprobe(file_path)
    if not data:
        return {}

    fmt = data.get("format") or {}
    streams = data.get("streams") or []
    info: Dict[str, Any] = {
        "container": fmt.get("format_long_name", fmt.get("format_name", "Unknown")),
        "duration": _safe_int(fmt.get("duration")),
        "size": _safe_int(fmt.get("size")),
        "bitrate": _safe_int(fmt.get("bit_rate")),
        "video_streams": [],
        "audio_streams": [],
        "subtitle_streams": [],
    }

    for stream in streams:
        kind = stream.get("codec_type")
        if kind == "video":
            info["video_streams"].append({
                "codec": str(stream.get("codec_name", "unknown")).upper(),
                "profile": stream.get("profile", "N/A"),
                "width": _safe_int(stream.get("width")),
                "height": _safe_int(stream.get("height")),
                "aspect_ratio": stream.get("display_aspect_ratio", "N/A"),
                "pix_fmt": stream.get("pix_fmt", "N/A"),
                "r_frame_rate": stream.get("r_frame_rate", "N/A"),
                "bitrate": _safe_int(stream.get("bit_rate")),
                "fps": stream.get("avg_frame_rate", stream.get("r_frame_rate", "N/A")),
            })
        elif kind == "audio":
            info["audio_streams"].append({
                "codec": str(stream.get("codec_name", "unknown")).upper(),
                "channels": _safe_int(stream.get("channels"), 2),
                "channel_layout": stream.get("channel_layout", "unknown"),
                "sample_rate": stream.get("sample_rate", "unknown"),
                "bitrate": _safe_int(stream.get("bit_rate")),
                "lang": (stream.get("tags") or {}).get("language", "und"),
            })
        elif kind == "subtitle":
            info["subtitle_streams"].append({
                "codec": str(stream.get("codec_name", "unknown")).upper(),
                "lang": (stream.get("tags") or {}).get("language", "und"),
                "title": (stream.get("tags") or {}).get("title", "Subtitle"),
            })
    return info


async def extract_frame_screenshot(video_path: str, output_dir: str, duration: int) -> Optional[str]:
    os.makedirs(output_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(video_path))[0]
    out_path = os.path.join(output_dir, f"thumb_{stem}.jpg")
    timestamp = max(0, min(max(duration - 1, 0), duration // 2))
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", str(timestamp),
        "-i", video_path, "-frames:v", "1", "-q:v", "2", "-y", out_path,
    ]
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await process.communicate()
        if process.returncode == 0 and os.path.isfile(out_path):
            return out_path
        logger.warning("Frame extraction failed: %s", stderr.decode(errors="ignore")[-1000:])
    except Exception as exc:
        logger.warning("Error taking screenshot: %s", exc)
    return None


async def compress_media(
    input_path: str,
    output_path: str,
    crf: int = 28,
    preset: str = "superfast",
    scale_height: int = 720,
    progress_message=None,
    total_duration: int = 0,
) -> bool:
    """Compress video or audio using FFmpeg, based on detected streams."""
    attrs = await get_media_attributes(input_path)
    if not attrs.get("has_video") and not attrs.get("has_audio"):
        logger.warning("No audio/video stream detected in %s", input_path)
        return False

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    crf = max(18, min(int(crf), 36))
    allowed_presets = {"ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower"}
    preset = preset if preset in allowed_presets else "superfast"
    duration = max(int(total_duration or attrs.get("duration") or 0), 0)

    if attrs.get("has_video"):
        even_h = max(0, int(scale_height))
        if even_h and even_h % 2:
            even_h -= 1
        vf_filter = f"scale=-2:{even_h}:flags=lanczos,setsar=1" if even_h > 0 else "null"
        cmd = [
            "ffmpeg", "-hide_banner", "-nostdin", "-y", "-i", input_path,
            "-map", "0:v:0", "-map", "0:a?", "-map_metadata", "0",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", preset,
            "-crf", str(crf), "-vf", vf_filter,
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
            "-progress", "pipe:2", "-nostats", output_path,
        ]
    else:
        # Audio-only compression. Output extension should normally be .m4a from the caller.
        cmd = [
            "ffmpeg", "-hide_banner", "-nostdin", "-y", "-i", input_path,
            "-map", "0:a:0", "-map_metadata", "0", "-c:a", "aac", "-b:a", "128k",
            "-progress", "pipe:2", "-nostats", output_path,
        ]

    progress_re = re.compile(r"(?:out_time_ms=(\d+)|out_time=(\d+:\d+:\d+(?:\.\d+)?))")
    started = asyncio.get_running_loop().time()
    last_update = 0.0
    stderr_tail = []

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE
        )
        assert process.stderr is not None
        while True:
            line = await process.stderr.readline()
            if not line:
                break
            text_line = line.decode("utf-8", errors="ignore").strip()
            if text_line:
                stderr_tail.append(text_line)
                if len(stderr_tail) > 40:
                    stderr_tail.pop(0)
            match = progress_re.search(text_line)
            if match and progress_message and duration > 0:
                if match.group(1):
                    current = int(match.group(1)) / 1_000_000
                else:
                    h, m, s = match.group(2).split(":")
                    current = int(h) * 3600 + int(m) * 60 + float(s)
                now = asyncio.get_running_loop().time()
                if now - last_update >= 4.0:
                    last_update = now
                    pct = min(100.0, max(0.0, current / duration * 100.0))
                    filled = int(pct // 10)
                    bar = "▰" * filled + "▱" * (10 - filled)
                    label = "ᴄᴏᴍᴘʀᴇssɪɴɢ ᴍᴇᴅɪᴀ"
                    try:
                        await progress_message.edit_text(
                            f"⚡ **{to_smallcaps(label)}**\n\n"
                            f"[{bar}] `{pct:.1f}%`\n"
                            f"⏱ **{to_smallcaps('ᴘʀᴏᴄᴇssᴇᴅ')}** : `{int(current)}s / {duration}s`\n"
                            f"⚙️ **{to_smallcaps('ᴘʀᴇsᴇᴛ')}** : `{preset}` | **{to_smallcaps('ᴄʀғ')}** : `{crf}`\n\n"
                            f"⚡ **{to_smallcaps('ᴘᴏᴡᴇʀᴇᴅ ʙʏ')}** : [{Config.WATERMARK}]({Config.WATERMARK_URL})"
                        )
                    except Exception:
                        pass

        return_code = await process.wait()
        ok = return_code == 0 and os.path.isfile(output_path) and os.path.getsize(output_path) > 0
        if not ok:
            logger.error("FFmpeg failed (%s): %s", return_code, " | ".join(stderr_tail[-8:]))
        return ok
    except FileNotFoundError:
        logger.error("FFmpeg binary not found")
    except asyncio.CancelledError:
        try:
            process.terminate()
            await process.wait()
        except Exception:
            pass
        raise
    except Exception as exc:
        logger.exception("FFmpeg compression exception: %s", exc)
    return False
