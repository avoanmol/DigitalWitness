"""Bounded, local video frame sampling for OCR and optional vision review."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from backend.app.ai.extract import extract_document_text

MAX_VIDEO_SECONDS = 60
MAX_VIDEO_FRAMES = 4
MAX_FRAME_BYTES = 2 * 1024 * 1024


def _run(command: list[str], timeout: int) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(command, capture_output=True, text=True, check=True, timeout=timeout,
                              stdin=subprocess.DEVNULL, shell=False)
    except FileNotFoundError as exc:
        raise RuntimeError("FFmpeg and ffprobe must be installed for video evidence analysis.") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Video processing exceeded its time limit.") from exc
    except subprocess.CalledProcessError as exc:
        raise ValueError("The video could not be decoded safely.") from exc


def _rate(value: str | None) -> float | None:
    try:
        numerator, denominator = str(value).split("/", 1)
        result = float(numerator) / float(denominator)
        return round(result, 3) if 0 < result < 241 else None
    except (ValueError, ZeroDivisionError):
        return None


def extract_video_frames(data: bytes, filename: str) -> tuple[str, str, list[bytes], dict[str, Any]]:
    """Return bounded OCR text, extraction note, sampled frames, and safe metadata."""
    suffix = Path(filename).suffix.lower()
    if suffix in {".mp4", ".mov"} and (len(data) < 12 or data[4:8] != b"ftyp"):
        raise ValueError("MP4/MOV file does not have a valid ISO media container signature.")
    if suffix == ".webm" and not data.startswith(b"\x1a\x45\xdf\xa3"):
        raise ValueError("WEBM file does not have a valid EBML signature.")
    if suffix not in {".mp4", ".mov", ".webm"}:
        raise ValueError("Only MP4, MOV, or WEBM video is supported.")
    with tempfile.TemporaryDirectory(prefix="dw-video-") as temp_name:
        temp = Path(temp_name)
        source = temp / ("input" + suffix)
        source.write_bytes(data)
        probe = _run([
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration:format_tags=creation_time:stream=codec_type,codec_name,width,height,r_frame_rate",
            "-of", "json", str(source),
        ], timeout=10)
        try:
            info = json.loads(probe.stdout)
            duration = float(info.get("format", {}).get("duration", 0))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Video duration metadata is invalid.") from exc
        if duration <= 0 or duration > MAX_VIDEO_SECONDS:
            raise ValueError(f"Video duration must be between 1 and {MAX_VIDEO_SECONDS} seconds.")
        streams = [item for item in info.get("streams", []) if item.get("codec_type") == "video"]
        if not streams:
            raise ValueError("The uploaded file has no video stream.")
        stream = streams[0]
        tags = info.get("format", {}).get("tags", {}) or {}
        video_summary = {
            "duration_seconds": round(duration, 2),
            "frames_examined_limit": MAX_VIDEO_FRAMES,
            "video_codec": str(stream.get("codec_name", "unknown"))[:40],
            "frame_width": int(stream["width"]) if isinstance(stream.get("width"), int) else None,
            "frame_height": int(stream["height"]) if isinstance(stream.get("height"), int) else None,
            "frame_rate": _rate(stream.get("r_frame_rate")),
            "container_creation_time_present": any(str(key).casefold() == "creation_time" for key in tags),
            "caveat": "Container metadata may be edited or spoofed and does not establish video authenticity.",
        }
        times = [duration * (index + 1) / (MAX_VIDEO_FRAMES + 1) for index in range(MAX_VIDEO_FRAMES)]
        frames: list[bytes] = []
        sampled_timestamps: list[float] = []
        text_parts: list[str] = []
        ocr_languages: set[str] = set()
        for index, timestamp in enumerate(times, 1):
            frame_path = temp / f"frame-{index}.jpg"
            _run([
                "ffmpeg", "-nostdin", "-v", "error", "-threads", "1", "-ss", f"{timestamp:.3f}",
                "-i", str(source), "-an", "-frames:v", "1", "-vf",
                "scale=1280:720:force_original_aspect_ratio=decrease", "-q:v", "5", str(frame_path),
            ], timeout=15)
            if not frame_path.is_file():
                continue
            frame = frame_path.read_bytes()
            if not frame or len(frame) > MAX_FRAME_BYTES:
                continue
            frames.append(frame)
            sampled_timestamps.append(round(timestamp, 2))
            text, method = extract_document_text(frame, frame_path.name, "image/jpeg")
            if text:
                text_parts.append(f"[Frame {index} at {timestamp:.1f}s]\n{text}")
            if method and method.startswith("tesseract_ocr:"):
                ocr_languages.add(method.split(":", 1)[1])
        video_summary["frames_examined"] = len(frames)
        video_summary["sampled_timestamps_seconds"] = sampled_timestamps
        if not frames:
            raise ValueError("No video frames could be extracted within the safe limits.")
        text = "\n\n".join(text_parts)[:100_000]
        note = "ffmpeg_frames+tesseract_ocr:" + "+".join(sorted(ocr_languages)) if ocr_languages else "ffmpeg_frames:no_text"
        return text, note, frames, video_summary
