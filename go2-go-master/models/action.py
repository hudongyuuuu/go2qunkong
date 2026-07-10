# models/action.py
"""
Action Data Model
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import json


class ActionType(Enum):
    """Action types for robot control"""
    # Basic movements
    STAND = "stand"
    SIT = "sit"
    LIE_DOWN = "lie_down"

    # Locomotion
    WALK = "walk"
    TROT = "trot"
    RUN = "run"

    # Directional movements
    MOVE_FORWARD = "move_forward"
    MOVE_BACKWARD = "move_backward"
    MOVE_LEFT = "move_left"
    MOVE_RIGHT = "move_right"

    # Rotations
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"

    # Special moves
    JUMP = "jump"
    WAVE_HAND = "wave_hand"
    SPIN = "spin"

    # Dance moves
    DANCE_MOVE_1 = "dance_move_1"
    DANCE_MOVE_2 = "dance_move_2"
    DANCE_MOVE_3 = "dance_move_3"
    DANCE_MOVE_4 = "dance_move_4"
    DANCE_MOVE_5 = "dance_move_5"

    # Custom
    CUSTOM = "custom"


@dataclass
class ActionParams:
    """Action parameters"""
    speed: float = 1.0  # Speed multiplier (0.1 - 3.0)
    distance: Optional[float] = None  # Distance in meters
    angle: Optional[float] = None  # Angle in degrees
    duration: Optional[float] = None  # Duration in seconds
    height: Optional[float] = None  # Jump height or stance height
    repeat: int = 1  # Number of repetitions

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'speed': self.speed,
            'distance': self.distance,
            'angle': self.angle,
            'duration': self.duration,
            'height': self.height,
            'repeat': self.repeat,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionParams':
        """Create from dictionary"""
        return cls(
            speed=data.get('speed', 1.0),
            distance=data.get('distance'),
            angle=data.get('angle'),
            duration=data.get('duration'),
            height=data.get('height'),
            repeat=data.get('repeat', 1),
        )


@dataclass
class Action:
    """Action model for robot control"""
    id: str
    type: ActionType
    name: str
    params: ActionParams = field(default_factory=ActionParams)
    description: str = ""
    custom_command: Optional[str] = None  # For custom actions

    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary"""
        return {
            'id': self.id,
            'type': self.type.value,
            'name': self.name,
            'params': self.params.to_dict(),
            'description': self.description,
            'custom_command': self.custom_command,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Action':
        """Create action from dictionary"""
        return cls(
            id=data['id'],
            type=ActionType(data['type']),
            name=data['name'],
            params=ActionParams.from_dict(data.get('params', {})),
            description=data.get('description', ''),
            custom_command=data.get('custom_command'),
        )

    def get_command(self) -> Dict[str, Any]:
        """Generate command for robot"""
        cmd = {
            'action': self.type.value,
            'params': self.params.to_dict(),
        }
        if self.custom_command:
            cmd['custom'] = self.custom_command
        return cmd

    def get_duration(self) -> float:
        """Estimate action duration in seconds"""
        if self.params.duration:
            return self.params.duration

        # Default durations based on action type
        default_durations = {
            ActionType.STAND: 1.0,
            ActionType.SIT: 1.0,
            ActionType.LIE_DOWN: 1.5,
            ActionType.WALK: 2.0,
            ActionType.TROT: 1.5,
            ActionType.RUN: 1.0,
            ActionType.TURN_LEFT: 1.0,
            ActionType.TURN_RIGHT: 1.0,
            ActionType.JUMP: 1.5,
            ActionType.WAVE_HAND: 2.0,
            ActionType.SPIN: 2.0,
            ActionType.DANCE_MOVE_1: 2.0,
            ActionType.DANCE_MOVE_2: 2.0,
            ActionType.DANCE_MOVE_3: 2.0,
            ActionType.DANCE_MOVE_4: 2.0,
            ActionType.DANCE_MOVE_5: 2.0,
        }

        duration = default_durations.get(self.type, 1.0)

        # Adjust for speed
        if self.params.speed > 0:
            duration = duration / self.params.speed

        # Multiply by repetitions
        duration *= self.params.repeat

        return duration

    def __repr__(self) -> str:
        return f"Action(id={self.id}, type={self.type.value}, name={self.name})"


class ActionLibrary:
    """Library of predefined actions"""

    ACTIONS = {
        'stand': Action(
            id='act_stand',
            type=ActionType.STAND,
            name='Stand',
            description='Stand up from sitting or lying position'
        ),
        'sit': Action(
            id='act_sit',
            type=ActionType.SIT,
            name='Sit',
            description='Sit down from standing position'
        ),
        'lie_down': Action(
            id='act_lie_down',
            type=ActionType.LIE_DOWN,
            name='Lie Down',
            description='Lie down on the ground'
        ),
        'walk_forward': Action(
            id='act_walk_fwd',
            type=ActionType.WALK,
            name='Walk Forward',
            params=ActionParams(distance=1.0, speed=0.5),
            description='Walk forward 1 meter'
        ),
        'trot_forward': Action(
            id='act_trot_fwd',
            type=ActionType.TROT,
            name='Trot Forward',
            params=ActionParams(distance=1.0, speed=1.0),
            description='Trot forward 1 meter'
        ),
        'run_forward': Action(
            id='act_run_fwd',
            type=ActionType.RUN,
            name='Run Forward',
            params=ActionParams(distance=1.0, speed=2.0),
            description='Run forward 1 meter'
        ),
        'turn_left': Action(
            id='act_turn_left',
            type=ActionType.TURN_LEFT,
            name='Turn Left',
            params=ActionParams(angle=90.0),
            description='Turn left 90 degrees'
        ),
        'turn_right': Action(
            id='act_turn_right',
            type=ActionType.TURN_RIGHT,
            name='Turn Right',
            params=ActionParams(angle=90.0),
            description='Turn right 90 degrees'
        ),
        'jump': Action(
            id='act_jump',
            type=ActionType.JUMP,
            name='Jump',
            params=ActionParams(height=0.3),
            description='Jump up 30cm'
        ),
        'wave_hand': Action(
            id='act_wave',
            type=ActionType.WAVE_HAND,
            name='Wave Hand',
            params=ActionParams(duration=2.0),
            description='Wave hand gesture'
        ),
        'spin': Action(
            id='act_spin',
            type=ActionType.SPIN,
            name='Spin',
            params=ActionParams(angle=360.0, speed=1.5),
            description='Spin 360 degrees'
        ),
        'dance_1': Action(
            id='act_dance_1',
            type=ActionType.DANCE_MOVE_1,
            name='Dance Move 1',
            params=ActionParams(duration=2.0),
            description='Dance choreography move 1'
        ),
        'dance_2': Action(
            id='act_dance_2',
            type=ActionType.DANCE_MOVE_2,
            name='Dance Move 2',
            params=ActionParams(duration=2.0),
            description='Dance choreography move 2'
        ),
        'dance_3': Action(
            id='act_dance_3',
            type=ActionType.DANCE_MOVE_3,
            name='Dance Move 3',
            params=ActionParams(duration=2.0),
            description='Dance choreography move 3'
        ),
    }

    @classmethod
    def get_action(cls, action_id: str) -> Optional[Action]:
        """Get action by ID"""
        return cls.ACTIONS.get(action_id)

    @classmethod
    def get_all_actions(cls) -> list[Action]:
        """Get all predefined actions"""
        return list(cls.ACTIONS.values())

    @classmethod
    def get_actions_by_type(cls, action_type: ActionType) -> list[Action]:
        """Get actions by type"""
        return [a for a in cls.ACTIONS.values() if a.type == action_type]
