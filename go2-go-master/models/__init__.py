# models/__init__.py
"""
Unitree GO2AIR Robot Control - Data Models
"""

from .robot import Robot, RobotState, ConnectionStatus, RobotGroup
from .action import Action, ActionType
from .group import FormationType
from .music import MusicTrack, BeatMarker, Choreography

__all__ = [
    'Robot', 'RobotState', 'ConnectionStatus', 'RobotGroup',
    'Action', 'ActionType',
    'FormationType',
    'MusicTrack', 'BeatMarker', 'Choreography',
]
