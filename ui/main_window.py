import os
import shutil
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QDoubleSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.compressor import CompressorWorker
from core.video_info import probe_video
from utils.formatters import (
    format_bytes,
    format_duration,
    output_name,
)
from ui.styles import APP_STYLE


PROJECT_ROOT = Path(__file__).resolve().parent.parent

LOCAL_FFMPEG = (
    PROJECT_ROOT
    / "ffmpeg"
    / "ffmpeg.exe"
)

LOCAL_FFPROBE = (
    PROJECT_ROOT
    / "ffmpeg"
    / "ffprobe.exe"
)


class DropZone(QFrame):
    fileDropped = Signal(str)

    def __init__(self):
        super().__init__()

        self.setObjectName(
            "DropZone"
        )

        self.setAcceptDrops(
            True
        )

        layout = QVBoxLayout(
            self
        )

        title = QLabel(
            "Drop your video here"
        )

        title.setObjectName(
            "DropTitle"
        )

        title.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        subtitle = QLabel(
            "or choose a video file from your computer"
        )

        subtitle.setObjectName(
            "DropSubtitle"
        )

        subtitle.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        button = QPushButton(
            "Choose Video"
        )

        button.setObjectName(
            "Secondary"
        )

        button.clicked.connect(
            self.choose_file
        )

        layout.addStretch()

        layout.addWidget(
            title
        )

        layout.addWidget(
            subtitle
        )

        layout.addSpacing(
            12
        )

        layout.addWidget(
            button,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )

        layout.addStretch()

    def choose_file(self):
        file_path, _ = (
            QFileDialog.getOpenFileName(
                self,
                "Select Video",
                "",
                (
                    "Video Files "
                    "(*.mp4 *.mov *.mkv *.avi "
                    "*.webm *.m4v *.wmv);;"
                    "All Files (*.*)"
                ),
            )
        )

        if file_path:
            self.fileDropped.emit(
                file_path
            )

    def dragEnterEvent(
        self,
        event: QDragEnterEvent,
    ):
        mime = event.mimeData()

        if mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile():
                    event.acceptProposedAction()

                    self.setProperty(
                        "dragging",
                        True,
                    )

                    self.style().unpolish(
                        self
                    )

                    self.style().polish(
                        self
                    )

                    return

        event.ignore()

    def dragLeaveEvent(
        self,
        event,
    ):
        self.setProperty(
            "dragging",
            False,
        )

        self.style().unpolish(
            self
        )

        self.style().polish(
            self
        )

        event.accept()

    def dropEvent(
        self,
        event: QDropEvent,
    ):
        self.setProperty(
            "dragging",
            False,
        )

        self.style().unpolish(
            self
        )

        self.style().polish(
            self
        )

        for url in event.mimeData().urls():
            if url.isLocalFile():
                self.fileDropped.emit(
                    url.toLocalFile()
                )

                event.acceptProposedAction()

                return

        event.ignore()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(
            "Video Compressor"
        )

        self.setMinimumSize(
            900,
            700,
        )

        self.resize(
            1000,
            760,
        )

        self.input_path = None
        self.video_info = None

        self.thread = None
        self.worker = None

        self.ffmpeg_path = (
            self.find_executable(
                LOCAL_FFMPEG,
                "ffmpeg.exe",
            )
        )

        self.ffprobe_path = (
            self.find_executable(
                LOCAL_FFPROBE,
                "ffprobe.exe",
            )
        )

        self.setup_ui()

        self.update_buttons()

    @staticmethod
    def find_executable(
        local_path: Path,
        executable_name: str,
    ):
        if local_path.exists():
            return str(local_path)

        system_path = shutil.which(
            executable_name
        )

        if system_path:
            return system_path

        return None

    def setup_ui(self):
        self.setStyleSheet(
            APP_STYLE
        )

        central = QWidget()

        self.setCentralWidget(
            central
        )

        root = QVBoxLayout(
            central
        )

        root.setContentsMargins(
            30,
            25,
            30,
            25,
        )

        root.setSpacing(
            18
        )

        title = QLabel(
            "Video Compressor"
        )

        title.setObjectName(
            "Title"
        )

        subtitle = QLabel(
            "Compress your videos locally with FFmpeg."
        )

        subtitle.setObjectName(
            "Subtitle"
        )

        root.addWidget(
            title
        )

        root.addWidget(
            subtitle
        )

        # --------------------------------------------------
        # DROP ZONE
        # --------------------------------------------------

        self.drop_zone = DropZone()

        self.drop_zone.setMinimumHeight(
            180
        )

        self.drop_zone.fileDropped.connect(
            self.load_video
        )

        root.addWidget(
            self.drop_zone
        )

        # --------------------------------------------------
        # VIDEO INFORMATION
        # --------------------------------------------------

        info_card = QFrame()

        info_card.setObjectName(
            "Card"
        )

        info_layout = QVBoxLayout(
            info_card
        )

        section_title = QLabel(
            "Video Information"
        )

        section_title.setObjectName(
            "SectionTitle"
        )

        info_layout.addWidget(
            section_title
        )

        info_grid = QGridLayout()

        self.file_label = QLabel(
            "No video selected"
        )

        self.file_label.setObjectName(
            "Muted"
        )

        self.size_label = QLabel(
            "--"
        )

        self.duration_label = QLabel(
            "--"
        )

        self.resolution_label = QLabel(
            "--"
        )

        self.fps_label = QLabel(
            "--"
        )

        self.codec_label = QLabel(
            "--"
        )

        info_grid.addWidget(
            QLabel("File:"),
            0,
            0,
        )

        info_grid.addWidget(
            self.file_label,
            0,
            1,
            1,
            3,
        )

        info_grid.addWidget(
            QLabel("Size:"),
            1,
            0,
        )

        info_grid.addWidget(
            self.size_label,
            1,
            1,
        )

        info_grid.addWidget(
            QLabel("Duration:"),
            1,
            2,
        )

        info_grid.addWidget(
            self.duration_label,
            1,
            3,
        )

        info_grid.addWidget(
            QLabel("Resolution:"),
            2,
            0,
        )

        info_grid.addWidget(
            self.resolution_label,
            2,
            1,
        )

        info_grid.addWidget(
            QLabel("FPS:"),
            2,
            2,
        )

        info_grid.addWidget(
            self.fps_label,
            2,
            3,
        )

        info_grid.addWidget(
            QLabel("Video Codec:"),
            3,
            0,
        )

        info_grid.addWidget(
            self.codec_label,
            3,
            1,
        )

        info_layout.addLayout(
            info_grid
        )

        root.addWidget(
            info_card
        )

        # --------------------------------------------------
        # COMPRESSION SETTINGS
        # --------------------------------------------------

        settings_card = QFrame()

        settings_card.setObjectName(
            "Card"
        )

        settings_layout = QVBoxLayout(
            settings_card
        )

        settings_title = QLabel(
            "Compression Settings"
        )

        settings_title.setObjectName(
            "SectionTitle"
        )

        settings_layout.addWidget(
            settings_title
        )

        settings_grid = QGridLayout()

        # Compression mode
        settings_grid.addWidget(
            QLabel("Compression"),
            0,
            0,
        )

        self.quality_combo = QComboBox()

        self.quality_combo.addItem(
            "Best Quality",
            "best",
        )

        self.quality_combo.addItem(
            "Balanced",
            "balanced",
        )

        self.quality_combo.addItem(
            "Small File",
            "small",
        )

        self.quality_combo.setCurrentIndex(
            1
        )

        self.quality_combo.currentIndexChanged.connect(
            self.quality_mode_changed
        )

        settings_grid.addWidget(
            self.quality_combo,
            0,
            1,
        )

        # Target size
        settings_grid.addWidget(
            QLabel("Target Size"),
            0,
            2,
        )

        self.target_size_spin = (
            QDoubleSpinBox()
        )

        self.target_size_spin.setRange(
            1.0,
            5000.0,
        )

        self.target_size_spin.setDecimals(
            1
        )

        self.target_size_spin.setSingleStep(
            1.0
        )

        self.target_size_spin.setSuffix(
            " MB"
        )

        # Your requested target.
        self.target_size_spin.setValue(
            20.0
        )

        # Always enabled.
        self.target_size_spin.setEnabled(
            True
        )

        settings_grid.addWidget(
            self.target_size_spin,
            0,
            3,
        )

        # Resolution
        settings_grid.addWidget(
            QLabel("Resolution"),
            1,
            0,
        )

        self.resolution_combo = QComboBox()

        self.resolution_combo.addItem(
            "Keep Original",
            "source",
        )

        self.resolution_combo.addItem(
            "1080p",
            "1920:1080",
        )

        self.resolution_combo.addItem(
            "720p",
            "1280:720",
        )

        self.resolution_combo.addItem(
            "480p",
            "854:480",
        )

        settings_grid.addWidget(
            self.resolution_combo,
            1,
            1,
        )

        # FPS
        settings_grid.addWidget(
            QLabel("Frame Rate"),
            1,
            2,
        )

        self.fps_combo = QComboBox()

        self.fps_combo.addItem(
            "Original FPS",
            0,
        )

        self.fps_combo.addItem(
            "30 FPS",
            30,
        )

        self.fps_combo.addItem(
            "24 FPS",
            24,
        )

        self.fps_combo.setCurrentIndex(
            1
        )

        settings_grid.addWidget(
            self.fps_combo,
            1,
            3,
        )

        # Codec
        settings_grid.addWidget(
            QLabel("Video Codec"),
            2,
            0,
        )

        self.codec_combo = QComboBox()

        self.codec_combo.addItem(
            "H.265 / HEVC - Smaller",
            "libx265",
        )

        self.codec_combo.addItem(
            "H.264 - Compatible",
            "libx264",
        )

        settings_grid.addWidget(
            self.codec_combo,
            2,
            1,
        )

        # Audio
        settings_grid.addWidget(
            QLabel("Audio"),
            2,
            2,
        )

        self.audio_combo = QComboBox()

        self.audio_combo.addItem(
            "96 kbps",
            96,
        )

        self.audio_combo.addItem(
            "128 kbps",
            128,
        )

        self.audio_combo.addItem(
            "64 kbps",
            64,
        )

        self.audio_combo.addItem(
            "Mute Audio",
            0,
        )

        self.audio_combo.setCurrentIndex(
            0
        )

        settings_grid.addWidget(
            self.audio_combo,
            2,
            3,
        )

        settings_layout.addLayout(
            settings_grid
        )

        self.quality_hint = QLabel(
            "Balanced: targets approximately "
            "20 MB while maintaining good quality."
        )

        self.quality_hint.setObjectName(
            "Muted"
        )

        settings_layout.addWidget(
            self.quality_hint
        )

        root.addWidget(
            settings_card
        )

        # --------------------------------------------------
        # PROGRESS
        # --------------------------------------------------

        progress_card = QFrame()

        progress_card.setObjectName(
            "Card"
        )

        progress_layout = QVBoxLayout(
            progress_card
        )

        self.status_label = QLabel(
            "Ready"
        )

        self.status_label.setObjectName(
            "Muted"
        )

        self.progress_bar = QProgressBar()

        self.progress_bar.setRange(
            0,
            100,
        )

        self.progress_bar.setValue(
            0
        )

        progress_layout.addWidget(
            self.status_label
        )

        progress_layout.addWidget(
            self.progress_bar
        )

        root.addWidget(
            progress_card
        )

        # --------------------------------------------------
        # BUTTONS
        # --------------------------------------------------

        button_layout = QHBoxLayout()

        self.compress_button = QPushButton(
            "Compress Video"
        )

        self.compress_button.setObjectName(
            "Primary"
        )

        self.compress_button.clicked.connect(
            self.start_compression
        )

        self.cancel_button = QPushButton(
            "Cancel"
        )

        self.cancel_button.setObjectName(
            "Secondary"
        )

        self.cancel_button.clicked.connect(
            self.cancel_compression
        )

        self.open_button = QPushButton(
            "Open Output"
        )

        self.open_button.setObjectName(
            "Secondary"
        )

        self.open_button.clicked.connect(
            self.open_output
        )

        button_layout.addWidget(
            self.compress_button
        )

        button_layout.addWidget(
            self.cancel_button
        )

        button_layout.addWidget(
            self.open_button
        )

        root.addLayout(
            button_layout
        )

        # --------------------------------------------------
        # LOG
        # --------------------------------------------------

        log_title = QLabel(
            "FFmpeg Log"
        )

        log_title.setObjectName(
            "SectionTitle"
        )

        root.addWidget(
            log_title
        )

        self.log = QPlainTextEdit()

        self.log.setObjectName(
            "Log"
        )

        self.log.setReadOnly(
            True
        )

        self.log.setMinimumHeight(
            150
        )

        root.addWidget(
            self.log
        )

    def quality_mode_changed(self):
        mode = (
            self.quality_combo.currentData()
        )

        target = (
            self.target_size_spin.value()
        )

        if mode == "best":
            self.quality_hint.setText(
                "Best Quality: uses a slower encoder "
                "preset for better compression efficiency "
                f"at approximately {target:.1f} MB."
            )

        elif mode == "small":
            self.quality_hint.setText(
                "Small File: uses faster encoding and "
                f"targets approximately {target:.1f} MB."
            )

        else:
            self.quality_hint.setText(
                "Balanced: targets approximately "
                f"{target:.1f} MB while maintaining good quality."
            )

    def load_video(
        self,
        file_path: str,
    ):
        if not os.path.isfile(
            file_path
        ):
            return

        if not self.ffprobe_path:
            QMessageBox.critical(
                self,
                "FFprobe Not Found",
                (
                    "ffprobe.exe was not found.\n\n"
                    "Make sure it exists in the project's "
                    "ffmpeg folder."
                ),
            )

            return

        try:
            self.status_label.setText(
                "Reading video information..."
            )

            self.log.clear()

            self.video_info = probe_video(
                self.ffprobe_path,
                file_path,
            )

            self.input_path = file_path

            self.file_label.setText(
                Path(file_path).name
            )

            self.size_label.setText(
                format_bytes(
                    self.video_info.size
                )
            )

            self.duration_label.setText(
                format_duration(
                    self.video_info.duration
                )
            )

            self.resolution_label.setText(
                f"{self.video_info.width} × "
                f"{self.video_info.height}"
            )

            self.fps_label.setText(
                f"{self.video_info.fps:.2f}"
            )

            self.codec_label.setText(
                self.video_info.codec
                or "Unknown"
            )

            self.status_label.setText(
                "Video loaded successfully."
            )

            self.log.appendPlainText(
                f"Loaded: {file_path}"
            )

            self.log.appendPlainText(
                "Size: "
                f"{format_bytes(self.video_info.size)}"
            )

            self.log.appendPlainText(
                "Duration: "
                f"{format_duration(self.video_info.duration)}"
            )

        except Exception as exc:
            self.video_info = None
            self.input_path = None

            self.status_label.setText(
                "Unable to read video."
            )

            QMessageBox.critical(
                self,
                "Video Error",
                str(exc),
            )

        self.update_buttons()

    def start_compression(self):
        if (
            not self.input_path
            or not self.video_info
        ):
            QMessageBox.warning(
                self,
                "No Video",
                "Please select a video first.",
            )

            return

        if not self.ffmpeg_path:
            QMessageBox.critical(
                self,
                "FFmpeg Not Found",
                (
                    "ffmpeg.exe was not found.\n\n"
                    "Make sure it exists in the project's "
                    "ffmpeg folder."
                ),
            )

            return

        target_size_mb = (
            self.target_size_spin.value()
        )

        original_size_mb = (
            self.video_info.size
            / (1024 * 1024)
        )

        if target_size_mb >= original_size_mb:
            answer = QMessageBox.question(
                self,
                "Target Size",
                (
                    f"Original: "
                    f"{original_size_mb:.2f} MB\n"
                    f"Target: "
                    f"{target_size_mb:.1f} MB\n\n"
                    "The target is not smaller than "
                    "the original video.\n\n"
                    "Continue anyway?"
                ),
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
            )

            if (
                answer
                != QMessageBox.StandardButton.Yes
            ):
                return

        output_path = output_name(
            self.input_path
        )

        compression_mode = (
            self.quality_combo.currentData()
        )

        resolution = (
            self.resolution_combo.currentData()
        )

        fps = (
            self.fps_combo.currentData()
        )

        # 0 means keep original FPS.
        if fps == 0:
            fps = max(
                1,
                round(
                    self.video_info.fps
                ),
            )

        codec = (
            self.codec_combo.currentData()
        )

        audio_bitrate = (
            self.audio_combo.currentData()
        )

        self.log.clear()

        self.progress_bar.setValue(
            0
        )

        self.status_label.setText(
            "Compressing..."
        )

        self.compress_button.setEnabled(
            False
        )

        self.open_button.setEnabled(
            False
        )

        self.cancel_button.setEnabled(
            True
        )

        self.thread = QThread()

        self.worker = CompressorWorker(
            ffmpeg_path=self.ffmpeg_path,
            input_path=self.input_path,
            output_path=output_path,
            resolution=resolution,
            fps=fps,
            codec=codec,
            audio_bitrate=audio_bitrate,
            compression_mode=compression_mode,
            target_size_mb=target_size_mb,
        )

        self.worker.moveToThread(
            self.thread
        )

        self.thread.started.connect(
            lambda: self.worker.run(
                self.video_info.duration
            )
        )

        self.worker.progress.connect(
            self.update_progress
        )

        self.worker.log.connect(
            self.append_log
        )

        self.worker.finished.connect(
            self.compression_finished
        )

        self.worker.failed.connect(
            self.compression_failed
        )

        self.worker.finished.connect(
            self.thread.quit
        )

        self.worker.failed.connect(
            self.thread.quit
        )

        self.thread.finished.connect(
            self.thread_finished
        )

        self.thread.start()

    def cancel_compression(self):
        if self.worker:
            self.status_label.setText(
                "Cancelling..."
            )

            self.worker.cancel()

            self.cancel_button.setEnabled(
                False
            )

    def update_progress(
        self,
        value: float,
    ):
        self.progress_bar.setValue(
            max(
                0,
                min(
                    100,
                    round(value),
                ),
            )
        )

    def append_log(
        self,
        message: str,
    ):
        self.log.appendPlainText(
            message
        )

        scrollbar = (
            self.log.verticalScrollBar()
        )

        scrollbar.setValue(
            scrollbar.maximum()
        )

    def compression_finished(
        self,
        output_path: str,
    ):
        self.progress_bar.setValue(
            100
        )

        self.status_label.setText(
            "Compression complete: "
            f"{Path(output_path).name}"
        )

        self.last_output_path = (
            output_path
        )

        self.append_log("")
        self.append_log(
            f"Output: {output_path}"
        )

        try:
            output_size = (
                Path(output_path).stat().st_size
            )

            output_size_mb = (
                output_size
                / (1024 * 1024)
            )

            target_size = (
                self.target_size_spin.value()
            )

            self.append_log(
                f"Output size: "
                f"{format_bytes(output_size)}"
            )

            self.append_log(
                f"Target size: "
                f"{target_size:.1f} MB"
            )

            difference = (
                output_size_mb
                - target_size
            )

            self.append_log(
                f"Difference from target: "
                f"{difference:+.2f} MB"
            )

            if (
                self.video_info
                and self.video_info.size
            ):
                ratio = (
                    output_size
                    / self.video_info.size
                ) * 100

                reduction = (
                    100
                    - ratio
                )

                self.append_log(
                    f"Output size is "
                    f"{ratio:.1f}% of original."
                )

                self.append_log(
                    f"Size reduction: "
                    f"{reduction:.1f}%"
                )

        except OSError:
            pass

        self.open_button.setEnabled(
            True
        )

        QMessageBox.information(
            self,
            "Compression Complete",
            (
                "Video compressed successfully.\n\n"
                f"Output:\n{output_path}"
            ),
        )

    def compression_failed(
        self,
        message: str,
    ):
        self.status_label.setText(
            "Compression failed."
        )

        self.append_log(
            f"ERROR: {message}"
        )

        QMessageBox.critical(
            self,
            "Compression Error",
            message,
        )

    def thread_finished(self):
        self.thread.deleteLater()

        self.thread = None
        self.worker = None

        self.cancel_button.setEnabled(
            False
        )

        self.update_buttons()

    def open_output(self):
        output_path = getattr(
            self,
            "last_output_path",
            None,
        )

        if not output_path:
            return

        if not os.path.exists(
            output_path
        ):
            QMessageBox.warning(
                self,
                "File Not Found",
                "The output file no longer exists.",
            )

            return

        try:
            os.startfile(
                output_path
            )

        except Exception as exc:
            QMessageBox.warning(
                self,
                "Unable to Open",
                str(exc),
            )

    def update_buttons(self):
        busy = (
            self.thread is not None
        )

        self.compress_button.setEnabled(
            bool(self.input_path)
            and bool(self.ffmpeg_path)
            and not busy
        )

        self.cancel_button.setEnabled(
            busy
        )

        self.open_button.setEnabled(
            bool(
                getattr(
                    self,
                    "last_output_path",
                    None,
                )
            )
        )

    def closeEvent(
        self,
        event,
    ):
        if self.worker:
            answer = QMessageBox.question(
                self,
                "Compression Running",
                (
                    "A compression is currently running.\n\n"
                    "Do you want to cancel it and exit?"
                ),
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
            )

            if (
                answer
                == QMessageBox.StandardButton.Yes
            ):
                self.worker.cancel()

                if self.thread:
                    self.thread.quit()
                    self.thread.wait(
                        3000
                    )

                event.accept()

                return

            event.ignore()

            return

        event.accept()