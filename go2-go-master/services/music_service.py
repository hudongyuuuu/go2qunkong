# services/music_service.py
"""
Music Service - Audio playback and BPM detection
"""

import os
import numpy as np
from pathlib import Path
from typing import Optional, List, Callable
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTimer

import pygame

# Optional scipy imports
try:
    from scipy import signal
    from scipy.io import wavfile
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

from models.music import MusicTrack, BeatMarker
from config import MUSIC_CONFIG


class MusicService(QObject):
    """Music playback and BPM detection service"""

    # Signals
    track_loaded = pyqtSignal(object)  # MusicTrack
    playback_started = pyqtSignal()
    playback_paused = pyqtSignal()
    playback_stopped = pyqtSignal()
    position_changed = pyqtSignal(float)  # position_ms
    track_finished = pyqtSignal()
    bpm_detected = pyqtSignal(float)

    def __init__(self):
        super().__init__()

        # Initialize pygame mixer
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

        self.current_track: Optional[MusicTrack] = None
        self.is_playing = False
        self.is_paused = False
        self.current_position = 0.0

        # Position update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_position)

        # Track end timer
        self.end_timer = QTimer()
        self.end_timer.setSingleShot(True)
        self.end_timer.timeout.connect(self._on_track_finished)

    def load_track(self, file_path: str) -> Optional[MusicTrack]:
        """Load music track from file"""
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                return None

            # Get file info
            file_path_obj = Path(file_path)
            track_name = file_path_obj.stem
            file_ext = file_path_obj.suffix.lower()

            if file_ext not in MUSIC_CONFIG['supported_formats']:
                return None

            # Load with pygame to get duration
            sound = pygame.mixer.Sound(file_path)
            duration_ms = sound.get_length() * 1000

            # Create track
            track_id = f"track_{hash(file_path)}"
            track = MusicTrack(
                id=track_id,
                name=track_name,
                file_path=file_path,
                duration=duration_ms,
                bpm=MUSIC_CONFIG['default_bpm'],
            )

            self.current_track = track
            self.track_loaded.emit(track)

            return track

        except Exception as e:
            print(f"Error loading track: {e}")
            return None

    def play(self):
        """Start playback"""
        if not self.current_track:
            return

        try:
            if self.is_paused:
                pygame.mixer.music.unpause()
                self.is_paused = False
            else:
                pygame.mixer.music.load(self.current_track.file_path)
                pygame.mixer.music.play()
                pygame.mixer.music.set_volume(self.current_track.volume)

            self.is_playing = True

            # Start position update timer
            self.update_timer.start(50)  # Update every 50ms

            # Set track end timer
            remaining = self.current_track.duration - self.current_position
            self.end_timer.start(int(remaining))

            self.playback_started.emit()

        except Exception as e:
            print(f"Error playing track: {e}")

    def pause(self):
        """Pause playback"""
        if self.is_playing and not self.is_paused:
            pygame.mixer.music.pause()
            self.is_paused = True
            self.update_timer.stop()
            self.playback_paused.emit()

    def stop(self):
        """Stop playback"""
        pygame.mixer.music.stop()
        self.is_playing = False
        self.is_paused = False
        self.current_position = 0.0
        self.update_timer.stop()
        self.end_timer.stop()
        self.playback_stopped.emit()
        self.position_changed.emit(0.0)

    def set_position(self, position_ms: float):
        """Set playback position"""
        if not self.current_track:
            return

        was_playing = self.is_playing and not self.is_paused

        # Stop current playback
        pygame.mixer.music.stop()

        # Pygame doesn't support seek, so we reload and play
        # This is a limitation - for true seeking, we'd need a different audio library
        self.current_position = position_ms
        self.position_changed.emit(position_ms)

        if was_playing:
            pygame.mixer.music.play(start=position_ms / 1000.0)
            # Update end timer
            remaining = self.current_track.duration - position_ms
            self.end_timer.start(int(remaining))

    def set_volume(self, volume: float):
        """Set volume (0.0 - 1.0)"""
        volume = max(0.0, min(volume, 1.0))
        pygame.mixer.music.set_volume(volume)

        if self.current_track:
            self.current_track.volume = volume

    def get_volume(self) -> float:
        """Get current volume"""
        return pygame.mixer.music.get_volume()

    def get_position(self) -> float:
        """Get current position in milliseconds"""
        return self.current_position

    def get_duration(self) -> float:
        """Get track duration in milliseconds"""
        if self.current_track:
            return self.current_track.duration
        return 0.0

    def is_track_loaded(self) -> bool:
        """Check if track is loaded"""
        return self.current_track is not None

    def _update_position(self):
        """Update playback position"""
        if self.is_playing and not self.is_paused:
            self.current_position += 50  # Timer runs every 50ms
            self.position_changed.emit(self.current_position)

    def _on_track_finished(self):
        """Handle track finished"""
        self.is_playing = False
        self.is_paused = False
        self.current_position = 0.0
        self.update_timer.stop()
        self.track_finished.emit()

    def detect_bpm(self, file_path: str, callback: Optional[Callable[[float], None]] = None):
        """Detect BPM of audio file (async)"""
        detector = BPMDetector(file_path, callback)
        detector.finished.connect(self._on_bpm_detected)
        detector.start()

    def detect_bpm_sync(self, file_path: str) -> float:
        """Detect BPM of audio file (synchronous)"""
        if not SCIPY_AVAILABLE:
            print("Scipy not available, using default BPM")
            return MUSIC_CONFIG['default_bpm']

        try:
            # For WAV files, we can use scipy
            if file_path.lower().endswith('.wav'):
                sample_rate, samples = wavfile.read(file_path)

                # Convert to mono if stereo
                if len(samples.shape) > 1:
                    samples = np.mean(samples, axis=1)

                # Detect BPM
                bpm = self._calculate_bpm(samples, sample_rate)

                if bpm > 0:
                    return bpm

            # Fallback: estimate based on genre or return default
            return MUSIC_CONFIG['default_bpm']

        except Exception as e:
            print(f"Error detecting BPM: {e}")
            return MUSIC_CONFIG['default_bpm']

    def _calculate_bpm(self, samples: np.ndarray, sample_rate: int) -> float:
        """Calculate BPM from audio samples"""
        try:
            # Take first 30 seconds for faster processing
            max_samples = min(len(samples), sample_rate * 30)
            samples = samples[:max_samples]

            # Calculate energy
            energy = np.abs(samples)

            # Find peaks
            peaks, _ = signal.find_peaks(energy, distance=int(sample_rate / 4))

            if len(peaks) < 2:
                return MUSIC_CONFIG['default_bpm']

            # Calculate intervals
            intervals = np.diff(peaks) / sample_rate

            # Convert to BPM
            mean_interval = np.mean(intervals)
            if mean_interval > 0:
                bpm = 60.0 / mean_interval
                # Clamp to reasonable range
                return max(60, min(bpm, 200))
            else:
                return MUSIC_CONFIG['default_bpm']

        except Exception as e:
            print(f"Error calculating BPM: {e}")
            return MUSIC_CONFIG['default_bpm']

    def _on_bpm_detected(self, bpm: float):
        """Handle BPM detection complete"""
        if self.current_track:
            self.current_track.bpm = bpm
        self.bpm_detected.emit(bpm)

    def cleanup(self):
        """Cleanup resources"""
        self.stop()
        pygame.mixer.quit()


class BPMDetector(QThread):
    """Thread for BPM detection"""

    finished = pyqtSignal(float)

    def __init__(self, file_path: str, callback: Optional[Callable[[float], None]]):
        super().__init__()

        self.file_path = file_path
        self.callback = callback

    def run(self):
        """Run BPM detection"""
        service = MusicService()
        bpm = service.detect_bpm_sync(self.file_path)
        self.finished.emit(bpm)

        if self.callback:
            self.callback(bpm)
