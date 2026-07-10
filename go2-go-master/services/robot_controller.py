# services/robot_controller.py
"""
Robot Controller - Send control commands to robots
"""

from typing import Dict, Any, List, Optional
from PyQt5.QtCore import QObject, pyqtSignal

from models.robot import Robot
from models.action import Action
from models.group import Formation, FormationType
from services.network_service import NetworkService
from config import ROBOT_CONFIG


class RobotController(QObject):
    """Controller for robot operations"""

    # Signals
    command_sent = pyqtSignal(str, dict)  # robot_id, command
    command_failed = pyqtSignal(str, str)  # robot_id, error
    formation_complete = pyqtSignal(bool)

    def __init__(self, network_service: NetworkService):
        super().__init__()

        self.network_service = network_service
        self.active_choreography = None

    def send_action(self, robot_id: str, action: Action) -> bool:
        """Send action command to robot"""
        command = {
            'type': 'action',
            'action': action.type.value,
            'params': action.params.to_dict(),
            'timestamp': self._get_timestamp(),
        }

        success = self.network_service.send_command(robot_id, command)

        if success:
            self.command_sent.emit(robot_id, command)
        else:
            self.command_failed.emit(robot_id, "Failed to send command")

        return success

    def send_action_to_group(self, robot_ids: List[str], action: Action) -> Dict[str, bool]:
        """Send action to multiple robots"""
        results = {}

        for robot_id in robot_ids:
            results[robot_id] = self.send_action(robot_id, action)

        return results

    def move_robot(self, robot_id: str, x: float, y: float, rotation: float = 0.0, speed: float = 1.0) -> bool:
        """Move robot to position"""
        command = {
            'type': 'move',
            'target': {
                'x': x,
                'y': y,
                'rotation': rotation,
            },
            'speed': speed,
            'timestamp': self._get_timestamp(),
        }

        success = self.network_service.send_command(robot_id, command)

        if success:
            self.command_sent.emit(robot_id, command)
        else:
            self.command_failed.emit(robot_id, "Failed to send move command")

        return success

    def move_group_to_formation(self, robot_ids: List[str], formation: Formation,
                                center_x: float = 0.0, center_y: float = 0.0) -> bool:
        """Move group of robots into formation"""
        positions = formation.calculate_positions(robot_ids, center_x, center_y)

        success = True
        for pos in positions:
            if not self.move_robot(pos.robot_id, pos.x, pos.y, pos.rotation):
                success = False

        self.formation_complete.emit(success)
        return success

    def start_dance(self, robot_ids: List[str], choreography: Any) -> bool:
        """Start dance choreography"""
        self.active_choreography = choreography

        # Send start command to all robots
        command = {
            'type': 'start_dance',
            'choreography_id': choreography.id,
            'timestamp': self._get_timestamp(),
        }

        all_success = True
        for robot_id in robot_ids:
            if not self.network_service.send_command(robot_id, command):
                all_success = False

        return all_success

    def stop_dance(self, robot_ids: List[str]) -> bool:
        """Stop dance choreography"""
        command = {
            'type': 'stop_dance',
            'timestamp': self._get_timestamp(),
        }

        all_success = True
        for robot_id in robot_ids:
            if not self.network_service.send_command(robot_id, command):
                all_success = False

        self.active_choreography = None
        return all_success

    def pause_dance(self, robot_ids: List[str]) -> bool:
        """Pause dance choreography"""
        command = {
            'type': 'pause_dance',
            'timestamp': self._get_timestamp(),
        }

        all_success = True
        for robot_id in robot_ids:
            if not self.network_service.send_command(robot_id, command):
                all_success = False

        return all_success

    def resume_dance(self, robot_ids: List[str]) -> bool:
        """Resume dance choreography"""
        command = {
            'type': 'resume_dance',
            'timestamp': self._get_timestamp(),
        }

        all_success = True
        for robot_id in robot_ids:
            if not self.network_service.send_command(robot_id, command):
                all_success = False

        return all_success

    def set_robot_speed(self, robot_id: str, speed: float) -> bool:
        """Set robot speed multiplier"""
        command = {
            'type': 'set_speed',
            'speed': max(0.1, min(speed, 3.0)),  # Clamp between 0.1 and 3.0
            'timestamp': self._get_timestamp(),
        }

        return self.network_service.send_command(robot_id, command)

    def emergency_stop(self, robot_id: str) -> bool:
        """Emergency stop for robot"""
        command = {
            'type': 'emergency_stop',
            'timestamp': self._get_timestamp(),
        }

        return self.network_service.send_command(robot_id, command)

    def emergency_stop_all(self, robot_ids: List[str]) -> bool:
        """Emergency stop for all robots"""
        command = {
            'type': 'emergency_stop',
            'timestamp': self._get_timestamp(),
        }

        all_success = True
        for robot_id in robot_ids:
            if not self.network_service.send_command(robot_id, command):
                all_success = False

        return all_success

    def set_led_color(self, robot_id: str, color: str) -> bool:
        """Set robot LED color"""
        command = {
            'type': 'set_led',
            'color': color,
            'timestamp': self._get_timestamp(),
        }

        return self.network_service.send_command(robot_id, command)

    def set_volume(self, robot_id: str, volume: float) -> bool:
        """Set robot sound volume"""
        command = {
            'type': 'set_volume',
            'volume': max(0.0, min(volume, 1.0)),
            'timestamp': self._get_timestamp(),
        }

        return self.network_service.send_command(robot_id, command)

    def make_robot_speak(self, robot_id: str, text: str) -> bool:
        """Make robot speak text"""
        command = {
            'type': 'speak',
            'text': text,
            'timestamp': self._get_timestamp(),
        }

        return self.network_service.send_command(robot_id, command)

    def calibrate_robot(self, robot_id: str) -> bool:
        """Calibrate robot sensors"""
        command = {
            'type': 'calibrate',
            'timestamp': self._get_timestamp(),
        }

        return self.network_service.send_command(robot_id, command)

    def get_robot_battery(self, robot_id: str) -> Optional[Dict[str, Any]]:
        """Get robot battery status via HTTP"""
        from models.robot import Robot

        # Find robot from network service
        if robot_id in self.network_service.active_connections:
            robot = self.network_service.active_connections[robot_id]['robot']
            return self.network_service.get_robot_status(robot)

        return None

    def reboot_robot(self, robot_id: str) -> bool:
        """Reboot robot"""
        command = {
            'type': 'reboot',
            'timestamp': self._get_timestamp(),
        }

        return self.network_service.send_command(robot_id, command)

    def shutdown_robot(self, robot_id: str) -> bool:
        """Shutdown robot"""
        command = {
            'type': 'shutdown',
            'timestamp': self._get_timestamp(),
        }

        return self.network_service.send_command(robot_id, command)

    def _get_timestamp(self) -> int:
        """Get current timestamp"""
        import time
        return int(time.time() * 1000)
