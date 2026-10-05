import json
import subprocess
from pathlib import Path


class VideoInfo:
    def __init__(
        self,
        path: str,
        size: int = 0,
        duration: float = 0.0,
        width: int = 0,
        height: int = 0,
        fps: float = 0.0,
        codec: str = "",
        audio_codec: str = "",
    ):
        self.path = path
        self.size = size
        self.duration = duration
        self.width = width
        self.height = height
        self.fps = fps
        self.codec = codec
        self.audio_codec = audio_codec


def _parse_fraction(value: str) -> float:
    if not value:
        return 0.0

    try:
        if "/" in value:
            numerator, denominator = value.split("/", 1)

            numerator = float(numerator)
            denominator = float(denominator)

            if denominator == 0:
                return 0.0

            return numerator / denominator

        return float(value)

    except (ValueError, ZeroDivisionError):
        return 0.0


def probe_video(
    ffprobe_path: str,
    file_path: str,
) -> VideoInfo:

    path = Path(file_path)

    if not path.exists():
        raise RuntimeError(
            f"Video file does not exist:\n{file_path}"
        )

    command = [
        ffprobe_path,
        "-v",
        "error",
        "-show_entries",
        (
            "format=duration,size:"
            "stream=index,codec_type,codec_name,"
            "width,height,r_frame_rate"
        ),
        "-of",
        "json",
        str(path),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or "Unable to read video information."
        )

    try:
        data = json.loads(result.stdout)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "FFprobe returned invalid information."
        ) from exc

    format_data = data.get(
        "format",
        {},
    )

    streams = data.get(
        "streams",
        [],
    )

    video_stream = next(
        (
            stream
            for stream in streams
            if stream.get("codec_type") == "video"
        ),
        {},
    )

    audio_stream = next(
        (
            stream
            for stream in streams
            if stream.get("codec_type") == "audio"
        ),
        {},
    )

    # Duration
    try:
        duration = float(
            format_data.get("duration") or 0
        )

    except (ValueError, TypeError):
        duration = 0.0

    # File size
    try:
        size = int(
            format_data.get("size")
            or path.stat().st_size
        )

    except (ValueError, TypeError, OSError):
        size = path.stat().st_size

    # Resolution
    try:
        width = int(
            video_stream.get("width") or 0
        )

    except (ValueError, TypeError):
        width = 0

    try:
        height = int(
            video_stream.get("height") or 0
        )

    except (ValueError, TypeError):
        height = 0

    # FPS
    fps = _parse_fraction(
        video_stream.get(
            "r_frame_rate",
            "",
        )
    )

    return VideoInfo(
        path=str(path),
        size=size,
        duration=duration,
        width=width,
        height=height,
        fps=fps,
        codec=video_stream.get(
            "codec_name",
            "",
        ),
        audio_codec=audio_stream.get(
            "codec_name",
            "",
        ),
    )