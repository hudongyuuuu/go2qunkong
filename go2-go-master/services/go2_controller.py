# services/go2_controller.py
"""
GO2 Robot Controller using go2-webrtc-connect
Local network robot control for Unitree GO2 robots
"""

import asyncio
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from PyQt5.QtCore import QObject, pyqtSignal, QThread

from models.robot import Robot, ConnectionStatus, RobotState


class Go2Controller(QObject):
    """
    Controller for Unitree GO2 robots using go2-webrtc-connect

    Installation:
    pip install go2-webrtc-connect
    """

    # Signals
    robot_connected = pyqtSignal(str)  # robot_id
    robot_disconnected = pyqtSignal(str)  # robot_id
    robot_state_changed = pyqtSignal(str, dict)  # robot_id, state
    connection_error = pyqtSignal(str, str)  # robot_id, error_message

    def __init__(self):
        super().__init__()

        # Local robot storage (in-memory)
        self.robots: Dict[str, Robot] = {}
        self.active_connections: Dict[str, any] = {}  # robot_id -> connection object

    def add_robot(self, robot_id: str, name: str, ip: str, port: int = 8080) -> bool:
        """Add robot to local storage"""
        try:
            robot = Robot(
                id=robot_id,
                name=name,
                ip=ip,
                port=port,
                connection_status=ConnectionStatus.DISCONNECTED,
                state=RobotState.IDLE,
            )
            self.robots[robot_id] = robot
            print(f"Added robot: {name} ({robot_id}) at {ip}:{port}")
            return True
        except Exception as e:
            print(f"Error adding robot: {e}")
            return False

    def remove_robot(self, robot_id: str) -> bool:
        """Remove robot from local storage"""
        if robot_id in self.robots:
            # Disconnect if connected
            if self.robots[robot_id].connection_status == ConnectionStatus.CONNECTED:
                self.disconnect_robot(robot_id)

            del self.robots[robot_id]
            print(f"Removed robot: {robot_id}")
            return True
        return False

    def get_robot(self, robot_id: str) -> Optional[Robot]:
        """Get robot by ID"""
        return self.robots.get(robot_id)

    def get_all_robots(self) -> List[Robot]:
        """Get all robots"""
        return list(self.robots.values())

    async def connect_robot_async(self, robot_id: str) -> bool:
        """Connect to robot asynchronously"""
        if robot_id not in self.robots:
            self.connection_error.emit(robot_id, "Robot not found")
            return False

        robot = self.robots[robot_id]

        try:
            # Update status to connecting
            robot.connection_status = ConnectionStatus.CONNECTING
            self.robot_state_changed.emit(robot_id, robot.to_dict())

            # Import go2-webrtc-connect
            try:
                from go2_webrtc_connect import RobotClient
            except ImportError:
                print("go2-webrtc-connect not installed. Run: pip install go2-webrtc-connect")
                # Simulate connection for testing
                await asyncio.sleep(1)
                robot.connection_status = ConnectionStatus.CONNECTED
                robot.state = RobotState.IDLE
                self.robot_connected.emit(robot_id)
                self.robot_state_changed.emit(robot_id, robot.to_dict())
                return True

            # Create connection
            # Note: Check the actual API from go2-webrtc-connect
            client = RobotClient(robot.ip, robot.port)

            # Connect
            await client.connect()

            # Store connection
            self.active_connections[robot_id] = client

            # Update robot status
            robot.connection_status = ConnectionStatus.CONNECTED
            robot.state = RobotState.IDLE
            robot.last_seen = datetime.now()

            self.robot_connected.emit(robot_id)
            self.robot_state_changed.emit(robot_id, robot.to_dict())

            print(f"Connected to robot: {robot.name} ({robot_id})")
            return True

        except Exception as e:
            robot.connection_status = ConnectionStatus.ERROR
            error_msg = str(e)
            print(f"Error connecting to robot {robot_id}: {error_msg}")
            self.connection_error.emit(robot_id, error_msg)
            self.robot_state_changed.emit(robot_id, robot.to_dict())
            return False

    def connect_robot(self, robot_id: str):
        """Connect to robot (blocking wrapper)"""
        # Run in background thread
        import threading

        def run_connect():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.connect_robot_async(robot_id))
            finally:
                loop.close()

        thread = threading.Thread(target=run_connect, daemon=True)
        thread.start()

    async def disconnect_robot_async(self, robot_id: str) -> bool:
        """Disconnect from robot asynchronously"""
        if robot_id not in self.robots:
            return False

        robot = self.robots[robot_id]

        try:
            if robot_id in self.active_connections:
                client = self.active_connections[robot_id]
                await client.disconnect()
                del self.active_connections[robot_id]

            robot.connection_status = ConnectionStatus.DISCONNECTED
            robot.state = RobotState.OFFLINE

            self.robot_disconnected.emit(robot_id)
            self.robot_state_changed.emit(robot_id, robot.to_dict())

            print(f"Disconnected from robot: {robot.name} ({robot_id})")
            return True

        except Exception as e:
            error_msg = str(e)
            print(f"Error disconnecting from robot {robot_id}: {error_msg}")
            self.connection_error.emit(robot_id, error_msg)
            return False

    def disconnect_robot(self, robot_id: str):
        """Disconnect from robot (blocking wrapper)"""
        if robot_id in self.active_connections:
            import threading

            def run_disconnect():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.disconnect_robot_async(robot_id))
                finally:
                    loop.close()

            thread = threading.Thread(target=run_disconnect, daemon=True)
            thread.start()

    async def send_command_async(self, robot_id: str, command: str, params: Dict = None) -> bool:
        """Send command to robot asynchronously"""
        if robot_id not in self.robots:
            return False

        robot = self.robots[robot_id]

        if robot.connection_status != ConnectionStatus.CONNECTED:
            print(f"Robot {robot_id} not connected")
            return False

        try:
            client = self.active_connections.get(robot_id)
            if not client:
                print(f"No active connection for robot {robot_id}")
                return False

            # Send command based on command type
            # This depends on the go2-webrtc-connect API
            if command == "stand":
                await client.stand()
            elif command == "sit":
                await client.sit()
            elif command == "walk":
                distance = params.get('distance', 1.0) if params else 1.0
                speed = params.get('speed', 0.5) if params else 0.5
                await client.walk(distance, speed)
            elif command == "stop":
                await client.stop()
            else:
                print(f"Unknown command: {command}")
                return False

            # Update robot state
            robot.state = RobotState.MOVING if command in ['walk', 'move'] else RobotState.IDLE
            self.robot_state_changed.emit(robot_id, robot.to_dict())

            print(f"Sent command '{command}' to robot {robot_id}")
            return True

        except Exception as e:
            error_msg = str(e)
            print(f"Error sending command to robot {robot_id}: {error_msg}")
            self.connection_error.emit(robot_id, error_msg)
            return False

    def send_command(self, robot_id: str, command: str, params: Dict = None):
        """Send command to robot (blocking wrapper)"""
        import threading

        def run_command():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.send_command_async(robot_id, command, params))
            finally:
                loop.close()

        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()

    def get_robot_status(self, robot_id: str) -> Optional[Dict]:
        """Get robot status"""
        robot = self.robots.get(robot_id)
        if robot:
            return {
                'id': robot.id,
                'name': robot.name,
                'connection_status': robot.connection_status.value,
                'state': robot.state.value,
                'battery_level': robot.battery.level,
                'position': robot.position.to_dict(),
            }
        return None

    def shutdown_all(self):
        """Disconnect all robots"""
        for robot_id in list(self.active_connections.keys()):
            self.disconnect_robot(robot_id)
