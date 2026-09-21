import asyncio
import json
import os
import re
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Callable
from app.utils.logger import logger
from app.utils.task_manager import task_manager


def ensure_ffmpeg_binaries() -> Tuple[str, str]:
    """
    Locates ffmpeg and ffprobe executables.
    1. Checks standard PATH and common Linux/Unix directories.
    2. Uses static-ffmpeg as an automatic standalone fallback.
    """
    # Try importing and running static_ffmpeg first to populate PATH if needed
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
    except Exception as exc:
        logger.debug(f"static_ffmpeg import note: {exc}")

    probe_path = shutil.which("ffprobe")
    ffmpeg_path = shutil.which("ffmpeg")

    # Search common system directories if not in default PATH
    if not probe_path or not ffmpeg_path:
        search_dirs = [
            "/usr/bin",
            "/usr/local/bin",
            "/bin",
            "/opt/homebrew/bin",
            os.path.expanduser("~/.local/bin"),
        ]
        for sdir in search_dirs:
            p_cand = os.path.join(sdir, "ffprobe")
            f_cand = os.path.join(sdir, "ffmpeg")
            if not probe_path and os.path.isfile(p_cand) and os.access(p_cand, os.X_OK):
                probe_path = p_cand
            if not ffmpeg_path and os.path.isfile(f_cand) and os.access(f_cand, os.X_OK):
                ffmpeg_path = f_cand

    # Final fallback names
    ffmpeg_path = ffmpeg_path or "ffmpeg"
    probe_path = probe_path or "ffprobe"

    logger.info(f"Resolved FFmpeg binaries -> ffmpeg: '{ffmpeg_path}', ffprobe: '{probe_path}'")
    return ffmpeg_path, probe_path


FFMPEG_BIN, FFPROBE_BIN = ensure_ffmpeg_binaries()


def sanitize_path(file_path: Any) -> str:
    """Safely converts any input into a valid string path, unpacking tuples/lists."""
    if isinstance(file_path, (list, tuple)):
        if len(file_path) > 0:
            file_path = file_path[0]
        else:
            raise ValueError("Empty tuple or list provided as path.")

    if isinstance(file_path, Path):
        return str(file_path.resolve())

    return str(file_path).strip()


class FFmpegService:
    """FFmpeg and FFprobe wrapper with stream validation and concurrency support."""

    @staticmethod
    async def probe_media(file_path: Any) -> Dict[str, Any]:
        """Probes a media file and checks video/audio streams."""
        global FFPROBE_BIN, FFMPEG_BIN
        clean_path = sanitize_path(file_path)

        if not os.path.exists(clean_path):
            raise FileNotFoundError(f"Input file does not exist on disk: {clean_path}")

        if os.path.getsize(clean_path) == 0:
            raise ValueError("The input file is 0 bytes (corrupted or incomplete download).")

        cmd = [
            FFPROBE_BIN,
            "-v", "error",
            "-analyzeduration", "100M",
            "-probesize", "100M",
            "-show_entries", "format=duration,size,bit_rate:stream=index,codec_type,codec_name,width,height,duration,channels,sample_rate",
            "-of", "json",
            clean_path,
        ]

        logger.info(f"Probing media with {FFPROBE_BIN}: {clean_path}")
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            # Re-attempt adding static-ffmpeg paths dynamically at runtime
            try:
                import static_ffmpeg
                static_ffmpeg.add_paths()
                FFMPEG_BIN, FFPROBE_BIN = ensure_ffmpeg_binaries()
                cmd[0] = FFPROBE_BIN
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            except Exception as exc:
                raise RuntimeError(
                    f"ffprobe is not installed or not found at '{FFPROBE_BIN}'. "
                    "Ensure 'static-ffmpeg' is installed via pip or ffmpeg is installed via apt."
                ) from exc

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
        """Compresses video safely using dynamically resolved ffmpeg."""
        clean_input = sanitize_path(input_path)
        clean_output = sanitize_path(output_path)

        probe_info = await cls.probe_media(clean_input)
        has_video = probe_info["has_video"]
        has_audio = probe_info["has_audio"]
        total_duration = probe_info["duration"]

        cmd = [FFMPEG_BIN, "-y", "-i", clean_input]

        video_filters = []
        if target_resolution:
            video_filters.append(
                f"scale={target_resolution}:force_original_aspect_ratio=decrease,pad={target_resolution}:(ow-iw)/2:(oh-ih)/2"
            )

        if has_video:
            cmd.extend(["-c:v", "libx264", "-crf", str(crf), "-preset", preset])
            if video_filters:
                cmd.extend(["-vf", ",".join(video_filters)])
            cmd.extend(["-map", "0:v:0"])
        else:
            cmd.extend(["-vn"])

        if has_audio:
            cmd.extend(["-map", "0:a:0", "-c:a", "aac", "-b:a", "128k"])
        else:
            cmd.append("-an")

        cmd.extend(["-map", "0:s?", "-c:s", "copy"])
        cmd.extend(["-movflags", "+faststart", clean_output])

        logger.info(f"Executing compression with {FFMPEG_BIN}: {' '.join(cmd)}")

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
