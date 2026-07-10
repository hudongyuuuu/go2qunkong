# models/music.py
"""
Music Data Model
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path
import json


@dataclass
class BeatMarker:
    """Beat marker for music synchronization"""
    position: float  # Position in milliseconds
    bpm: float  # Beats per minute at this position
    label: str = ""  # Optional label for this beat

    def to_dict(self) -> Dict[str, Any]:
        return {
            'position': self.position,
            'bpm': self.bpm,
            'label': self.label,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BeatMarker':
        return cls(
            position=data['position'],
            bpm=data['bpm'],
            label=data.get('label', ''),
        )


@dataclass
class TimeRange:
    """Time range for looping or specific sections"""
    start_ms: float
    end_ms: float
    label: str = ""

    @property
    def duration(self) -> float:
        return self.end_ms - self.start_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            'start_ms': self.start_ms,
            'end_ms': self.end_ms,
            'label': self.label,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TimeRange':
        return cls(
            start_ms=data['start_ms'],
            end_ms=data['end_ms'],
            label=data.get('label', ''),
        )


@dataclass
class MusicTrack:
    """Music track model"""
    id: str
    name: str
    file_path: str
    duration: float  # Duration in milliseconds
    bpm: float = 120.0  # Default BPM
    beat_markers: List[BeatMarker] = field(default_factory=list)
    loop_range: Optional[TimeRange] = None
    volume: float = 0.7  # Volume 0.0 - 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'file_path': self.file_path,
            'duration': self.duration,
            'bpm': self.bpm,
            'beat_markers': [m.to_dict() for m in self.beat_markers],
            'loop_range': self.loop_range.to_dict() if self.loop_range else None,
            'volume': self.volume,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MusicTrack':
        """Create from dictionary"""
        return cls(
            id=data['id'],
            name=data['name'],
            file_path=data['file_path'],
            duration=data['duration'],
            bpm=data.get('bpm', 120.0),
            beat_markers=[
                BeatMarker.from_dict(m) for m in data.get('beat_markers', [])
            ],
            loop_range=TimeRange.from_dict(data['loop_range']) if data.get('loop_range') else None,
            volume=data.get('volume', 0.7),
        )

    def add_beat_marker(self, position: float, bpm: float, label: str = ""):
        """Add a beat marker"""
        marker = BeatMarker(position=position, bpm=bpm, label=label)
        self.beat_markers.append(marker)
        self.beat_markers.sort(key=lambda m: m.position)

    def remove_beat_marker(self, position: float):
        """Remove beat marker at position"""
        self.beat_markers = [m for m in self.beat_markers if m.position != position]

    def get_beat_at_position(self, position_ms: float) -> Optional[BeatMarker]:
        """Get beat marker closest to position"""
        if not self.beat_markers:
            return None

        closest = min(self.beat_markers, key=lambda m: abs(m.position - position_ms))
        if abs(closest.position - position_ms) < 100:  # Within 100ms
            return closest
        return None

    def get_beat_index(self, position_ms: float) -> int:
        """Get beat index at position (0-based)"""
        if not self.beat_markers or position_ms < self.beat_markers[0].position:
            return 0

        count = 0
        for marker in self.beat_markers:
            if marker.position <= position_ms:
                count += 1
            else:
                break
        return count

    def format_duration(self) -> str:
        """Format duration as MM:SS"""
        seconds = int(self.duration / 1000)
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def format_position(self, position_ms: float) -> str:
        """Format position as MM:SS"""
        seconds = int(position_ms / 1000)
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def __repr__(self) -> str:
        return f"MusicTrack(id={self.id}, name={self.name}, duration={self.format_duration()})"


@dataclass
class Choreography:
    """Choreography combining music and robot actions"""
    id: str
    name: str
    music_track: Optional[MusicTrack] = None
    actions: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)  # robot_id -> list of actions
    timeline_duration: float = 60000.0  # Default 60 seconds in milliseconds

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'music_track': self.music_track.to_dict() if self.music_track else None,
            'actions': self.actions,
            'timeline_duration': self.timeline_duration,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Choreography':
        """Create from dictionary"""
        return cls(
            id=data['id'],
            name=data['name'],
            music_track=MusicTrack.from_dict(data['music_track']) if data.get('music_track') else None,
            actions=data.get('actions', {}),
            timeline_duration=data.get('timeline_duration', 60000.0),
        )

    def add_action(self, robot_id: str, action: Dict[str, Any], start_time: float, end_time: float):
        """Add action for robot at specific time"""
        if robot_id not in self.actions:
            self.actions[robot_id] = []

        self.actions[robot_id].append({
            'action': action,
            'start_time': start_time,
            'end_time': end_time,
        })

        # Sort by start time
        self.actions[robot_id].sort(key=lambda x: x['start_time'])

    def get_actions_at_time(self, robot_id: str, time_ms: float) -> List[Dict[str, Any]]:
        """Get all active actions for robot at specific time"""
        if robot_id not in self.actions:
            return []

        return [
            a for a in self.actions[robot_id]
            if a['start_time'] <= time_ms <= a['end_time']
        ]

    def get_all_robot_ids(self) -> List[str]:
        """Get all robot IDs in choreography"""
        return list(self.actions.keys())
