# widgets/music_player.py
"""
Music Player Widget - Audio playback controls
"""

from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                             QPushButton, QSlider, QFileDialog, QStyle)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QCursor

from models.music import MusicTrack
from config import COLORS


class MusicPlayer(QWidget):
    """Music player widget"""

    # Signals
    play_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    position_changed = pyqtSignal(float)  # Position in milliseconds

    def __init__(self):
        super().__init__()

        self.current_track: MusicTrack = None
        self.is_playing = False
        self.current_position = 0  # milliseconds
        self.duration = 0

        self._setup_ui()
        self._apply_styles()

        # Update timer for position
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_position_display)

    def _setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(8)

        # Track info
        self.track_label = QLabel("No Track Loaded")
        self.track_label.setProperty("subheading", True)
        self.track_label.setFont(QFont("Segoe UI", 14, QFont.Bold))

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setProperty("caption", True)

        track_info_layout = QHBoxLayout()
        track_info_layout.addWidget(self.track_label)
        track_info_layout.addStretch()
        track_info_layout.addWidget(self.time_label)

        layout.addLayout(track_info_layout)

        # Progress slider
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.setValue(0)
        self.progress_slider.sliderMoved.connect(self._on_slider_moved)
        self.progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self._on_slider_released)
        layout.addWidget(self.progress_slider)

        # Controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)

        # Previous button (placeholder)
        self.prev_btn = QPushButton()
        self.prev_btn.setFixedSize(40, 40)
        self.prev_btn.setProperty("secondary", True)
        self.prev_btn.setCursor(QCursor(Qt.PointingHandCursor))
        controls_layout.addWidget(self.prev_btn)

        # Play/Pause button
        self.play_btn = QPushButton()
        self.play_btn.setFixedSize(50, 50)
        self.play_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.play_btn.clicked.connect(self._on_play_clicked)
        controls_layout.addWidget(self.play_btn)

        # Stop button
        self.stop_btn = QPushButton()
        self.stop_btn.setFixedSize(40, 40)
        self.stop_btn.setProperty("secondary", True)
        self.stop_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        controls_layout.addWidget(self.stop_btn)

        # Next button (placeholder)
        self.next_btn = QPushButton()
        self.next_btn.setFixedSize(40, 40)
        self.next_btn.setProperty("secondary", True)
        controls_layout.addWidget(self.next_btn)

        controls_layout.addStretch()

        # Volume control
        volume_layout = QHBoxLayout()
        volume_layout.setSpacing(4)

        self.volume_label = QLabel("\U0001F508")  # Speaker icon
        self.volume_label.setProperty("caption", True)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)

        volume_layout.addWidget(self.volume_label)
        volume_layout.addWidget(self.volume_slider)

        controls_layout.addLayout(volume_layout)

        layout.addLayout(controls_layout)

        self.setLayout(layout)

        # Update icons
        self._update_icons()

    def _apply_styles(self):
        """Apply custom styles"""
        self.play_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: {COLORS['background']};
                border: none;
                border-radius: 25px;
                font-size: 20px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent']};
            }}
        """)

    def _update_icons(self):
        """Update button icons"""
        play_icon = self.style().standardIcon(QStyle.SP_MediaPlay)
        pause_icon = self.style().standardIcon(QStyle.SP_MediaPause)
        stop_icon = self.style().standardIcon(QStyle.SP_MediaStop)
        prev_icon = self.style().standardIcon(QStyle.SP_MediaSkipBackward)
        next_icon = self.style().standardIcon(QStyle.SP_MediaSkipForward)

        if self.is_playing:
            self.play_btn.setText("\u23F8")  # Pause symbol
        else:
            self.play_btn.setText("\u25B6")  # Play symbol

        self.stop_btn.setText("\u23F9")  # Stop symbol
        self.prev_btn.setText("\u23EA")  # Previous track
        self.next_btn.setText("\u23E9")  # Next track

    def load_track(self, track: MusicTrack):
        """Load a music track"""
        self.current_track = track
        self.duration = track.duration
        self.track_label.setText(track.name)
        self._update_time_display()
        self._update_icons()

    def set_playing(self, playing: bool):
        """Set playing state"""
        self.is_playing = playing

        if playing:
            self.update_timer.start(100)  # Update every 100ms
        else:
            self.update_timer.stop()

        self._update_icons()

    def set_position(self, position_ms: float):
        """Set current position"""
        self.current_position = position_ms
        self._update_time_display()
        self._update_slider()

    def set_duration(self, duration_ms: float):
        """Set duration"""
        self.duration = duration_ms
        self.progress_slider.setMaximum(int(duration_ms))
        self._update_time_display()

    def _update_position_display(self):
        """Update position (called by timer)"""
        # This would be updated by the music service
        pass

    def _update_time_display(self):
        """Update time label"""
        def format_time(ms):
            seconds = int(ms / 1000)
            minutes = seconds // 60
            seconds = seconds % 60
            return f"{minutes:02d}:{seconds:02d}"

        current = format_time(self.current_position)
        total = format_time(self.duration)
        self.time_label.setText(f"{current} / {total}")

    def _update_slider(self):
        """Update progress slider"""
        if self.duration > 0:
            self.progress_slider.blockSignals(True)
            self.progress_slider.setValue(int(self.current_position))
            self.progress_slider.blockSignals(False)

    def _on_play_clicked(self):
        """Handle play/pause button click"""
        if self.is_playing:
            self.pause_clicked.emit()
        else:
            self.play_clicked.emit()

    def _on_stop_clicked(self):
        """Handle stop button click"""
        self.stop_clicked.emit()
        self.set_position(0)

    def _on_slider_moved(self, value):
        """Handle slider movement"""
        self.current_position = value
        self._update_time_display()

    def _on_slider_pressed(self):
        """Handle slider press"""
        if self.is_playing:
            self.update_timer.stop()

    def _on_slider_released(self):
        """Handle slider release"""
        self.position_changed.emit(self.current_position)
        if self.is_playing:
            self.update_timer.start(100)

    def _on_volume_changed(self, value):
        """Handle volume change"""
        # Update volume icon based on level
        if value == 0:
            self.volume_label.setText("\U0001F507")  # Muted
        elif value < 50:
            self.volume_label.setText("\U0001F508")  # Low volume
        elif value < 80:
            self.volume_label.setText("\U0001F509")  # Medium volume
        else:
            self.volume_label.setText("\U0001F50A")  # High volume

    def get_volume(self) -> float:
        """Get volume level (0.0 - 1.0)"""
        return self.volume_slider.value() / 100.0

    def set_volume(self, volume: float):
        """Set volume level (0.0 - 1.0)"""
        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(int(volume * 100))
        self.volume_slider.blockSignals(False)
