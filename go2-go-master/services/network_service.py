# services/network_service.py
"""
Network Service - HTTP and WebSocket communication
"""

import asyncio
import json
from typing import Dict, Any, Optional, Callable
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTimer

import requests
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from models.robot import Robot, ConnectionStatus
from config import NETWORK_CONFIG


class NetworkService(QObject):
    """Network service for robot communication"""

    # Signals
    connected = pyqtSignal(str)  # robot_id
    disconnected = pyqtSignal(str)  # robot_id
    connection_error = pyqtSignal(str, str)  # robot_id, error_message
    data_received = pyqtSignal(str, dict)  # robot_id, data
    state_update = pyqtSignal(str, dict)  # robot_id, state_data

    def __init__(self):
        super().__init__()

        self.active_connections: Dict[str, Any] = {}  # robot_id -> websocket
        self.http_session = requests.Session()
        self.http_session.timeout = NETWORK_CONFIG['timeout']

        # Ping timer
        self.ping_timer = QTimer()
        self.ping_timer.timeout.connect(self._ping_all)
        self.ping_interval = NETWORK_CONFIG['ping_interval'] * 1000  # Convert to ms

    def connect_robot(self, robot: Robot) -> bool:
        """Connect to robot via WebSocket"""
        try:
            # First, try HTTP connection
            url = f"http://{robot.ip}:{robot.port}/api/status"
            response = self.http_session.get(url, timeout=NETWORK_CONFIG['timeout'])

            if response.status_code == 200:
                # Then establish WebSocket
                ws_url = f"ws://{robot.ip}:{robot.port + 1}/ws"

                # Start WebSocket connection in thread
                thread = WebSocketThread(robot.id, ws_url)
                thread.connected.connect(lambda rid=robot.id: self.connected.emit(rid))
                thread.disconnected.connect(lambda rid=robot.id: self._on_disconnected(rid))
                thread.error.connect(lambda rid=robot.id, err="": self.connection_error.emit(rid, err))
                thread.data_received.connect(lambda rid=robot.id, data={}: self.data_received.emit(rid, data))
                thread.start()

                self.active_connections[robot.id] = {
                    'thread': thread,
                    'robot': robot,
                }

                return True

            return False

        except requests.RequestException as e:
            self.connection_error.emit(robot.id, str(e))
            return False
        except Exception as e:
            self.connection_error.emit(robot.id, f"Connection failed: {str(e)}")
            return False

    def disconnect_robot(self, robot_id: str):
        """Disconnect from robot"""
        if robot_id in self.active_connections:
            conn = self.active_connections[robot_id]
            conn['thread'].stop()
            conn['thread'].wait()
            del self.active_connections[robot_id]
            self.disconnected.emit(robot_id)

    def send_command(self, robot_id: str, command: Dict[str, Any]) -> bool:
        """Send command to robot"""
        if robot_id not in self.active_connections:
            return False

        try:
            conn = self.active_connections[robot_id]
            conn['thread'].send(command)
            return True
        except Exception as e:
            self.connection_error.emit(robot_id, str(e))
            return False

    def send_http_command(self, robot: Robot, endpoint: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send HTTP command to robot"""
        try:
            url = f"http://{robot.ip}:{robot.port}{endpoint}"
            response = self.http_session.post(url, json=data, timeout=NETWORK_CONFIG['timeout'])

            if response.status_code == 200:
                return response.json()
            else:
                self.connection_error.emit(robot.id, f"HTTP {response.status_code}")
                return None

        except requests.RequestException as e:
            self.connection_error.emit(robot.id, str(e))
            return None

    def get_robot_status(self, robot: Robot) -> Optional[Dict[str, Any]]:
        """Get robot status via HTTP"""
        try:
            url = f"http://{robot.ip}:{robot.port}/api/status"
            response = self.http_session.get(url, timeout=NETWORK_CONFIG['timeout'])

            if response.status_code == 200:
                return response.json()
            return None

        except requests.RequestException:
            return None

    def _on_disconnected(self, robot_id: str):
        """Handle disconnection"""
        if robot_id in self.active_connections:
            del self.active_connections[robot_id]
        self.disconnected.emit(robot_id)

    def _ping_all(self):
        """Ping all connected robots"""
        for robot_id, conn in list(self.active_connections.items()):
            self.send_command(robot_id, {'type': 'ping', 'timestamp': self._get_timestamp()})

    def _get_timestamp(self) -> int:
        """Get current timestamp"""
        import time
        return int(time.time() * 1000)

    def start_ping_timer(self):
        """Start ping timer"""
        self.ping_timer.start(self.ping_interval)

    def stop_ping_timer(self):
        """Stop ping timer"""
        self.ping_timer.stop()

    def shutdown(self):
        """Shutdown network service"""
        self.stop_ping_timer()

        for robot_id in list(self.active_connections.keys()):
            self.disconnect_robot(robot_id)

        self.http_session.close()


class WebSocketThread(QThread):
    """WebSocket connection thread"""

    connected = pyqtSignal(str)
    disconnected = pyqtSignal(str)
    error = pyqtSignal(str, str)
    data_received = pyqtSignal(str, dict)

    def __init__(self, robot_id: str, ws_url: str):
        super().__init__()

        self.robot_id = robot_id
        self.ws_url = ws_url
        self.websocket = None
        self._running = True
        self._send_queue = []

    def run(self):
        """Run WebSocket connection"""
        import asyncio

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            loop.run_until_complete(self._connect())

            while self._running:
                loop.run_until_complete(self._process_messages())

            loop.close()

        except Exception as e:
            self.error.emit(self.robot_id, str(e))

    async def _connect(self):
        """Connect to WebSocket"""
        try:
            self.websocket = await websockets.connect(self.ws_url)
            self.connected.emit(self.robot_id)
        except Exception as e:
            self.error.emit(self.robot_id, f"WebSocket connection failed: {str(e)}")

    async def _process_messages(self):
        """Process incoming messages"""
        try:
            if self.websocket and self.websocket.open:
                # Process send queue
                while self._send_queue:
                    message = self._send_queue.pop(0)
                    await self.websocket.send(json.dumps(message))

                # Receive message
                message = await asyncio.wait_for(self.websocket.recv(), timeout=0.1)
                data = json.loads(message)
                self.data_received.emit(self.robot_id, data)

        except asyncio.TimeoutError:
            pass
        except ConnectionClosed:
            self.disconnected.emit(self.robot_id)
            self._running = False
        except WebSocketException as e:
            self.error.emit(self.robot_id, str(e))

    def send(self, message: Dict[str, Any]):
        """Queue message to send"""
        self._send_queue.append(message)

    def stop(self):
        """Stop the thread"""
        self._running = False
        if self.websocket:
            import asyncio
            asyncio.create_task(self.websocket.close())
