import re
import subprocess
from pathlib import Path

from PySide6.QtCore import QObject, Signal


class CompressorWorker(QObject):
    progress = Signal(float)
    log = Signal(str)
    finished = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        ffmpeg_path: str,
        input_path: str,
        output_path: str,
        resolution: str,
        fps: int,
        codec: str,
        audio_bitrate: int,
        compression_mode: str,
        target_size_mb: float,
    ):
        super().__init__()

        self.ffmpeg_path = ffmpeg_path
        self.input_path = input_path
        self.output_path = output_path

        self.resolution = resolution
        self.fps = fps
        self.codec = codec
        self.audio_bitrate = audio_bitrate

        self.compression_mode = compression_mode
        self.target_size_mb = target_size_mb

        self._process = None
        self._cancel_requested = False

    def cancel(self):
        self._cancel_requested = True

        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
            except Exception:
                pass

    def get_preset(self):
        """
        Presets affect encoding speed/efficiency.

        slower = better compression but slower
        fast   = good balance
        veryfast = faster but less efficient
        """

        if self.compression_mode == "best":
            return "medium"

        if self.compression_mode == "small":
            return "veryfast"

        # Balanced
        return "fast"

    def calculate_video_bitrate(self, duration: float) -> int:
        """
        Calculate video bitrate required to approximately
        hit the requested final file size.

        Returns kbps.
        """

        if duration <= 0:
            raise RuntimeError(
                "Video duration is invalid."
            )

        if self.target_size_mb <= 0:
            raise RuntimeError(
                "Target size must be greater than 0 MB."
            )

        # Convert MB to bytes.
        target_bytes = (
            self.target_size_mb
            * 1024
            * 1024
        )

        # Reserve approximately 3% for:
        # - MP4 container
        # - metadata
        # - moov atom
        # - small bitrate variations
        usable_bytes = (
            target_bytes * 0.97
        )

        total_bits = (
            usable_bytes * 8
        )

        # Audio bitrate in bits/sec.
        audio_bits_per_second = (
            self.audio_bitrate * 1000
        )

        # Total bitrate needed.
        total_bits_per_second = (
            total_bits / duration
        )

        # Video bitrate = total bitrate - audio.
        video_bits_per_second = (
            total_bits_per_second
            - audio_bits_per_second
        )

        # Don't allow an unusably low bitrate.
        video_bits_per_second = max(
            video_bits_per_second,
            300_000,
        )

        return max(
            300,
            int(
                video_bits_per_second / 1000
            ),
        )

    def build_video_filter(self):
        """
        Keep original dimensions or scale down while
        preserving aspect ratio.
        """

        if self.resolution == "source":
            return "format=yuv420p"

        return (
            f"scale={self.resolution}:"
            "force_original_aspect_ratio=decrease:"
            "flags=lanczos,"
            "format=yuv420p"
        )

    def build_command(self, duration: float):
        video_bitrate = (
            self.calculate_video_bitrate(
                duration
            )
        )

        preset = self.get_preset()

        video_filter = (
            self.build_video_filter()
        )

        command = [
            self.ffmpeg_path,

            "-y",

            "-hide_banner",

            "-loglevel",
            "info",

            "-progress",
            "pipe:1",

            "-nostats",

            "-i",
            self.input_path,

            # Video only.
            "-map",
            "0:v:0",

            "-vf",
            video_filter,

            # Target FPS.
            "-r",
            str(self.fps),

            # Video codec.
            "-c:v",
            self.codec,

            # Encoding speed.
            "-preset",
            preset,

            # Target video bitrate.
            "-b:v",
            f"{video_bitrate}k",

            # Keep bitrate reasonably close to target.
            "-maxrate",
            f"{video_bitrate}k",

            "-bufsize",
            f"{video_bitrate * 2}k",

            "-pix_fmt",
            "yuv420p",

            # Allow playback before the whole file downloads.
            "-movflags",
            "+faststart",
        ]

        # Audio.
        if self.audio_bitrate > 0:
            command += [
                "-map",
                "0:a:0?",

                "-c:a",
                "aac",

                "-b:a",
                f"{self.audio_bitrate}k",

                "-ac",
                "2",
            ]
        else:
            command += [
                "-an",
            ]

        command.append(
            self.output_path
        )

        return command, video_bitrate, preset

    def run(self, duration: float):
        try:
            (
                command,
                video_bitrate,
                preset,
            ) = self.build_command(
                duration
            )

            self.log.emit(
                "Compression mode: "
                f"{self.compression_mode}"
            )

            self.log.emit(
                f"Target size: "
                f"{self.target_size_mb:.1f} MB"
            )

            self.log.emit(
                f"Calculated video bitrate: "
                f"{video_bitrate} kbps"
            )

            self.log.emit(
                f"Audio bitrate: "
                f"{self.audio_bitrate} kbps"
            )

            self.log.emit(
                f"Codec: {self.codec}"
            )

            self.log.emit(
                f"Preset: {preset}"
            )

            self.log.emit(
                f"Resolution: {self.resolution}"
            )

            self.log.emit(
                f"FPS: {self.fps}"
            )

            self.log.emit("")

            self.log.emit(
                "Starting FFmpeg..."
            )

            formatted_command = " ".join(
                (
                    f'"{item}"'
                    if " " in item
                    else item
                )
                for item in command
            )

            self.log.emit(
                formatted_command
            )

            self.log.emit("")

            creationflags = getattr(
                subprocess,
                "CREATE_NO_WINDOW",
                0,
            )

            self._process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=creationflags,
            )

            last_percent = -1.0

            for raw_line in self._process.stdout:
                if self._cancel_requested:
                    break

                line = raw_line.strip()

                if not line:
                    continue

                # FFmpeg progress.
                if line.startswith(
                    "out_time_ms="
                ):
                    try:
                        out_time_us = int(
                            line.split(
                                "=",
                                1,
                            )[1]
                        )

                        current_seconds = (
                            out_time_us
                            / 1_000_000
                        )

                        if duration > 0:
                            percent = (
                                current_seconds
                                / duration
                            ) * 100

                            percent = max(
                                0.0,
                                min(
                                    100.0,
                                    percent,
                                ),
                            )
                        else:
                            percent = 0.0

                        if (
                            abs(
                                percent
                                - last_percent
                            )
                            >= 0.1
                        ):
                            self.progress.emit(
                                percent
                            )

                            last_percent = (
                                percent
                            )

                    except ValueError:
                        pass

                elif line.startswith(
                    "progress="
                ):
                    if line == "progress=end":
                        self.progress.emit(
                            100.0
                        )

                else:
                    cleaned = re.sub(
                        r"\x1b\[[0-9;]*m",
                        "",
                        line,
                    )

                    self.log.emit(
                        cleaned[-2000:]
                    )

            # Cancellation.
            if self._cancel_requested:
                if (
                    self._process
                    and self._process.poll()
                    is None
                ):
                    try:
                        self._process.terminate()
                    except Exception:
                        pass

                self._process.wait()

                try:
                    output_file = Path(
                        self.output_path
                    )

                    if output_file.exists():
                        output_file.unlink()

                except OSError:
                    pass

                self.failed.emit(
                    "Compression cancelled."
                )

                return

            return_code = (
                self._process.wait()
            )

            if return_code != 0:
                raise RuntimeError(
                    "FFmpeg failed with exit code "
                    f"{return_code}. "
                    "Check the FFmpeg log."
                )

            output_file = Path(
                self.output_path
            )

            if not output_file.exists():
                raise RuntimeError(
                    "FFmpeg finished but the "
                    "output file was not created."
                )

            output_size = (
                output_file.stat().st_size
            )

            output_size_mb = (
                output_size
                / (1024 * 1024)
            )

            self.log.emit("")
            self.log.emit(
                f"Final output size: "
                f"{output_size_mb:.2f} MB"
            )

            difference = (
                output_size_mb
                - self.target_size_mb
            )

            self.log.emit(
                f"Difference from target: "
                f"{difference:+.2f} MB"
            )

            self.progress.emit(
                100.0
            )

            self.finished.emit(
                self.output_path
            )

        except Exception as exc:
            self.failed.emit(
                str(exc)
            )

        finally:
            self._process = None