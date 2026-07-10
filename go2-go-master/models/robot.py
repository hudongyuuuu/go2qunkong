# models/robot.py
"""
Robot Data Model
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime


class ConnectionStatus(Enum):
    """Robot connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class RobotState(Enum):
    """Robot operational state"""
    IDLE = "idle"
    MOVING = "moving"
    DANCING = "dancing"
    CHARGING = "charging"
    ERROR = "error"
    OFFLINE = "offline"


@dataclass
class Position:
    """Robot position in 2D space"""
    x: float = 0.0
    y: float = 0.0
    rotation: float = 0.0  # in degrees

    def to_dict(self) -> Dict[str, float]:
        return {
            'x': self.x,
            'y': self.y,
            'rotation': self.rotation,
        }

    @staticmethod
    def from_dict(data: Dict[str, float]) -> 'Position':
        return Position(
            x=data.get('x', 0.0),
            y=data.get('y', 0.0),
            rotation=data.get('rotation', 0.0),
        )


@dataclass
class BatteryInfo:
    """Robot battery information"""
    level: float = 100.0  # percentage
    voltage: float = 0.0  # volts
    is_charging: bool = False
    estimated_time: int = 0  # minutes remaining

    def to_dict(self) -> Dict[str, Any]:
        return {
            'level': self.level,
            'voltage': self.voltage,
            'is_charging': self.is_charging,
            'estimated_time': self.estimated_time,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'BatteryInfo':
        return BatteryInfo(
            level=data.get('level', 100.0),
            voltage=data.get('voltage', 0.0),
            is_charging=data.get('is_charging', False),
            estimated_time=data.get('estimated_time', 0),
        )


@dataclass
class Robot:
    """Robot model"""
    id: str
    name: str
    ip: str
    port: int = 8080
    connection_status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    state: RobotState = RobotState.IDLE
    position: Position = field(default_factory=Position)
    battery: BatteryInfo = field(default_factory=BatteryInfo)
    group_id: Optional[str] = None
    last_seen: Optional[datetime] = None
    firmware_version: str = "1.0.0"
    model: str = "GO2AIR"

    def to_dict(self) -> Dict[str, Any]:
        """Convert robot to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'ip': self.ip,
            'port': self.port,
            'connection_status': self.connection_status.value,
            'state': self.state.value,
            'position': self.position.to_dict(),
            'battery': self.battery.to_dict(),
            'group_id': self.group_id,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'firmware_version': self.firmware_version,
            'model': self.model,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Robot':
        """Create robot from dictionary"""
        return cls(
            id=data['id'],
            name=data['name'],
            ip=data['ip'],
            port=data.get('port', 8080),
            connection_status=ConnectionStatus(data.get('connection_status', 'disconnected')),
            state=RobotState(data.get('state', 'idle')),
            position=Position.from_dict(data.get('position', {})),
            battery=BatteryInfo.from_dict(data.get('battery', {})),
            group_id=data.get('group_id'),
            last_seen=datetime.fromisoformat(data['last_seen']) if data.get('last_seen') else None,
            firmware_version=data.get('firmware_version', '1.0.0'),
            model=data.get('model', 'GO2AIR'),
        )

    def update_position(self, x: float, y: float, rotation: float = 0.0):
        """Update robot position"""
        self.position.x = x
        self.position.y = y
        self.position.rotation = rotation

    def update_battery(self, level: float, voltage: float = 0.0, is_charging: bool = False):
        """Update battery information"""
        self.battery.level = level
        self.battery.voltage = voltage
        self.battery.is_charging = is_charging

    def is_connected(self) -> bool:
        """Check if robot is connected"""
        return self.connection_status == ConnectionStatus.CONNECTED

    def is_low_battery(self) -> bool:
        """Check if battery is low (< 20%)"""
        return self.battery.level < 20.0

    def is_critical_battery(self) -> bool:
        """Check if battery is critical (< 10%)"""
        return self.battery.level < 10.0

    def __repr__(self) -> str:
        return f"Robot(id={self.id}, name={self.name}, status={self.connection_status.value})"


class RobotGroup:
    """Group of robots for coordinated control"""

    def __init__(self, group_id: str, name: str):
        self.group_id = group_id
        self.name = name
        self.robots: list[str] = []  # List of robot IDs
        self.formation_type: str = 'line'
        self.formation_params: Dict[str, Any] = {}

    def add_robot(self, robot_id: str):
        """Add robot to group"""
        if robot_id not in self.robots:
            self.robots.append(robot_id)

    def remove_robot(self, robot_id: str):
        """Remove robot from group"""
        if robot_id in self.robots:
            self.robots.remove(robot_id)

    def clear(self):
        """Clear all robots from group"""
        self.robots.clear()

    def robot_count(self) -> int:
        """Get number of robots in group"""
        return len(self.robots)

    def to_dict(self) -> Dict[str, Any]:
        """Convert group to dictionary"""
        return {
            'group_id': self.group_id,
            'name': self.name,
            'robots': self.robots,
            'formation_type': self.formation_type,
            'formation_params': self.formation_params,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RobotGroup':
        """Create group from dictionary"""
        group = cls(data['group_id'], data['name'])
        group.robots = data.get('robots', [])
        group.formation_type = data.get('formation_type', 'line')
        group.formation_params = data.get('formation_params', {})
        return group
