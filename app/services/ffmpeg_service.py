import asyncio
import json
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Callable
from app.utils.logger import logger
from app.utils.task_manager import task_manager


def sanitize_path(file_path: Any) -> str:
    """
    Safely converts any input (including tuples/lists mistakenly passed) into a valid string path.
    Prevents 'expected str, bytes or os.PathLike object, not tuple' errors.
    """
    if isinstance(file_path, (list, tuple)):
        if len(file_path) > 0:
            file_path = file_path[0]
        else:
            raise ValueError("Empty tuple or list provided as path.")

    if isinstance(file_path, Path):
        return str(file_path.resolve())

    return str(file_path).strip()


class FFmpegService:
    """Robust FFmpeg and FFprobe wrapper with stream validation and concurrency support."""

    @staticmethod
    async def probe_media(file_path: Any) -> Dict[str, Any]:
        """
        Probes a media file and returns details on video, audio, format, and streams.
        Resolves the 'no audio or video stream that ffmpeg can decode' bug.
        """
        clean_path = sanitize_path(file_path)

        if not os.path.exists(clean_path):
            raise FileNotFoundError(f"Input file does not exist on disk: {clean_path}")

        if os.path.getsize(clean_path) == 0:
            raise ValueError("The input file is 0 bytes (corrupted or incomplete download).")

        # Probe with extended analyzeduration to handle high bitrate or unusual containers
        cmd = [
            "ffprobe",
            "-v", "error",
            "-analyzeduration", "100M",
            "-probesize", "100M",
            "-show_entries", "format=duration,size,bit_rate:stream=index,codec_type,codec_name,width,height,duration,channels,sample_rate",
            "-of", "json",
            clean_path,
        ]

        logger.info(f"Probing media: {' '.join(cmd)}")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            err_msg = stderr.decode().strip()
            logger.error(f"FFprobe failed with code {process.returncode}: {err_msg}")
            raise RuntimeError(f"FFprobe inspection failed: {err_msg}")

        try:
            data = json.loads(stdout.decode())
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Failed to parse FFprobe output: {exc}")

        streams = data.get("streams", [])
        has_video = any(s.get("codec_type") == "video" for s in streams)
        has_audio = any(s.get("codec_type") == "audio" for s in streams)

        if not has_video and not has_audio:
            raise ValueError(
                "This file has no audio or video stream that FFmpeg can decode. "
                "Ensure the file is a valid media format."
            )

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        # Extract duration from format or streams
        format_info = data.get("format", {})
        duration = float(format_info.get("duration") or 0)
        if duration == 0 and video_stream:
            duration = float(video_stream.get("duration") or 0)
        if duration == 0 and audio_stream:
            duration = float(audio_stream.get("duration") or 0)

        width = int(video_stream.get("width", 0)) if video_stream else 0
        height = int(video_stream.get("height", 0)) if video_stream else 0

        return {
            "has_video": has_video,
            "has_audio": has_audio,
            "duration": duration,
            "width": width,
            "height": height,
            "video_stream": video_stream,
            "audio_stream": audio_stream,
            "format": format_info,
            "streams": streams,
        }

    @classmethod
    async def compress_video(
        cls,
        input_path: Any,
        output_path: Any,
        crf: int = 28,
        preset: str = "veryfast",
        target_resolution: Optional[str] = None,
        task_id: Optional[str] = None,
        progress_callback: Optional[Callable[[float], Any]] = None,
    ) -> str:
        """
        Compresses video safely. Handles video-only files without crashing on missing audio.
        """
        clean_input = sanitize_path(input_path)
        clean_output = sanitize_path(output_path)

        probe_info = await cls.probe_media(clean_input)
        has_video = probe_info["has_video"]
        has_audio = probe_info["has_audio"]
        total_duration = probe_info["duration"]

        cmd = ["ffmpeg", "-y", "-i", clean_input]

        # Video filters & encoding
        video_filters = []
        if target_resolution:
            # e.g., "1280:720" or "854:480"
            video_filters.append(f"scale={target_resolution}:force_original_aspect_ratio=decrease,pad={target_resolution}:(ow-iw)/2:(oh-ih)/2")

        if has_video:
            cmd.extend(["-c:v", "libx264", "-crf", str(crf), "-preset", preset])
            if video_filters:
                cmd.extend(["-vf", ",".join(video_filters)])
            cmd.extend(["-map", "0:v:0"])
        else:
            cmd.extend(["-vn"])

        if has_audio:
            # Map first audio stream and encode to AAC
            cmd.extend(["-map", "0:a:0", "-c:a", "aac", "-b:a", "128k"])
        else:
            # Explicitly disable audio mapping if no audio stream exists to avoid FFmpeg errors
            cmd.append("-an")

        # Copy any existing subtitle tracks optionally without failing if none exist
        cmd.extend(["-map", "0:s?", "-c:s", "copy"])

        # Web optimization flag
        cmd.extend(["-movflags", "+faststart", clean_output])

        logger.info(f"Executing compression: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        if task_id:
            task_manager.set_subprocess(task_id, process)

        time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")

        async def read_stderr():
            while True:
                line = await process.stderr.readline()
                if not line:
                    break
                decoded_line = line.decode("utf-8", errors="ignore")
                match = time_pattern.search(decoded_line)
                if match and total_duration > 0 and progress_callback:
                    hours, minutes, seconds = map(float, match.groups())
                    elapsed = hours * 3600 + minutes * 60 + seconds
                    percent = min(100.0, (elapsed / total_duration) * 100.0)
                    try:
                        if asyncio.iscoroutinefunction(progress_callback):
                            await progress_callback(percent)
                        else:
                            progress_callback(percent)
                    except Exception as e:
                        logger.debug(f"Progress callback exception: {e}")

        await asyncio.gather(read_stderr(), process.wait())

        if process.returncode != 0:
            if os.path.exists(clean_output):
                os.remove(clean_output)
            raise RuntimeError(f"FFmpeg process returned non-zero exit code: {process.returncode}")

        if not os.path.exists(clean_output) or os.path.getsize(clean_output) == 0:
            raise RuntimeError("Compressed output file was not created or is empty.")

        return clean_output


ffmpeg_service = FFmpegService()
