# ui/robot_test_page.py
"""
Test Page for GO2 Robot Control
Simple interface to add and connect to robots
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QFormLayout, QFrame,
                             QMessageBox, QTextEdit, QGroupBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from config import COLORS


class RobotTestPage(QWidget):
    """Simple test page for robot control"""

    def __init__(self, go2_controller):
        super().__init__()

        self.go2_controller = go2_controller
        self._setup_ui()
        self._connect_signals()

        # Connect to controller signals
        self.go2_controller.robot_connected.connect(self._on_robot_connected)
        self.go2_controller.robot_disconnected.connect(self._on_robot_disconnected)
        self.go2_controller.connection_error.connect(self._on_connection_error)
        self.go2_controller.robot_state_changed.connect(self._on_robot_state_changed)

    def _setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Title
        title = QLabel("GO2 Robot Control Test")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['primary']};")
        layout.addWidget(title)

        # Add Robot Section
        add_group = QGroupBox("Add Robot")
        add_group.setStyleSheet(f"""
            QGroupBox {{
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                color: {COLORS['primary']};
            }}
        """)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.robot_id_input = QLineEdit()
        self.robot_id_input.setPlaceholderText("e.g., robot_001")
        form_layout.addRow("Robot ID:", self.robot_id_input)

        self.robot_name_input = QLineEdit()
        self.robot_name_input.setPlaceholderText("e.g., Robot 1")
        form_layout.addRow("Name:", self.robot_name_input)

        self.robot_ip_input = QLineEdit()
        self.robot_ip_input.setPlaceholderText("e.g., 192.168.123.1")
        form_layout.addRow("IP Address:", self.robot_ip_input)

        self.robot_port_input = QLineEdit()
        self.robot_port_input.setText("8080")
        form_layout.addRow("Port:", self.robot_port_input)

        add_btn = QPushButton("Add Robot")
        add_btn.setFixedHeight(36)
        add_btn.clicked.connect(self._add_robot)
        form_layout.addRow("", add_btn)

        add_group.setLayout(form_layout)
        layout.addWidget(add_group)

        # Robot List Section
        list_group = QGroupBox("Robots")
        list_group.setStyleSheet(f"""
            QGroupBox {{
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                color: {COLORS['primary']};
            }}
        """)

        list_layout = QVBoxLayout()

        self.robot_list_text = QTextEdit()
        self.robot_list_text.setReadOnly(True)
        self.robot_list_text.setMaximumHeight(200)
        self.robot_list_text.setPlaceholderText("No robots added yet...")
        list_layout.addWidget(self.robot_list_text)

        list_group.setLayout(list_layout)
        layout.addWidget(list_group)

        # Control Section
        control_group = QGroupBox("Control")
        control_group.setStyleSheet(f"""
            QGroupBox {{
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                color: {COLORS['primary']};
            }}
        """)

        control_layout = QHBoxLayout()

        self.connect_btn = QPushButton("Connect Selected")
        self.connect_btn.setFixedHeight(36)
        self.connect_btn.clicked.connect(self._connect_selected)
        control_layout.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("Disconnect Selected")
        self.disconnect_btn.setFixedHeight(36)
        self.disconnect_btn.clicked.connect(self._disconnect_selected)
        control_layout.addWidget(self.disconnect_btn)

        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        # Command Section
        cmd_group = QGroupBox("Commands")
        cmd_group.setStyleSheet(f"""
            QGroupBox {{
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                color: {COLORS['primary']};
            }}
        """)

        cmd_layout = QHBoxLayout()

        stand_btn = QPushButton("Stand")
        stand_btn.setFixedHeight(36)
        stand_btn.clicked.connect(lambda: self._send_command("stand"))
        cmd_layout.addWidget(stand_btn)

        sit_btn = QPushButton("Sit")
        sit_btn.setFixedHeight(36)
        sit_btn.clicked.connect(lambda: self._send_command("sit"))
        cmd_layout.addWidget(sit_btn)

        walk_btn = QPushButton("Walk")
        walk_btn.setFixedHeight(36)
        walk_btn.clicked.connect(lambda: self._send_command("walk", {'distance': 1.0, 'speed': 0.5}))
        cmd_layout.addWidget(walk_btn)

        stop_btn = QPushButton("Stop")
        stop_btn.setFixedHeight(36)
        stop_btn.clicked.connect(lambda: self._send_command("stop"))
        cmd_layout.addWidget(stop_btn)

        cmd_group.setLayout(cmd_layout)
        layout.addWidget(cmd_group)

        # Log Section
        log_group = QGroupBox("Log")
        log_group.setStyleSheet(f"""
            QGroupBox {{
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                color: {COLORS['primary']};
            }}
        """)

        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        layout.addStretch()
        self.setLayout(layout)

    def _connect_signals(self):
        """Connect internal signals"""
        pass

    def _add_robot(self):
        """Add robot to controller"""
        robot_id = self.robot_id_input.text().strip()
        name = self.robot_name_input.text().strip()
        ip = self.robot_ip_input.text().strip()

        if not robot_id or not name or not ip:
            QMessageBox.warning(self, "Input Error", "Please fill in all fields")
            return

        try:
            port = int(self.robot_port_input.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Port must be a number")
            return

        success = self.go2_controller.add_robot(robot_id, name, ip, port)

        if success:
            self._log(f"Added robot: {name} ({robot_id}) at {ip}:{port}")
            self._update_robot_list()
            QMessageBox.information(self, "Success", f"Robot {name} added successfully")
        else:
            QMessageBox.critical(self, "Error", "Failed to add robot")

    def _update_robot_list(self):
        """Update robot list display"""
        robots = self.go2_controller.get_all_robots()

        if not robots:
            self.robot_list_text.setText("No robots added yet...")
            return

        text = ""
        for robot in robots:
            status = "🟢 Connected" if robot.connection_status.value == "connected" else "🔴 Disconnected"
            text += f"{status} {robot.name} ({robot.id})\n"
            text += f"  IP: {robot.ip}:{robot.port}\n"
            text += f"  State: {robot.state.value}\n\n"

        self.robot_list_text.setText(text)

    def _connect_selected(self):
        """Connect to selected robot"""
        # For simplicity, connect to first robot
        robots = self.go2_controller.get_all_robots()
        if not robots:
            QMessageBox.warning(self, "No Robots", "Please add a robot first")
            return

        robot = robots[0]
        self._log(f"Connecting to {robot.name}...")
        self.go2_controller.connect_robot(robot.id)

    def _disconnect_selected(self):
        """Disconnect from robot"""
        robots = self.go2_controller.get_all_robots()
        if not robots:
            return

        robot = robots[0]
        self._log(f"Disconnecting from {robot.name}...")
        self.go2_controller.disconnect_robot(robot.id)

    def _send_command(self, command, params=None):
        """Send command to robot"""
        robots = self.go2_controller.get_all_robots()
        if not robots:
            QMessageBox.warning(self, "No Robots", "Please add and connect to a robot first")
            return

        robot = robots[0]

        if robot.connection_status.value != "connected":
            QMessageBox.warning(self, "Not Connected", "Please connect to the robot first")
            return

        self._log(f"Sending command '{command}' to {robot.name}...")
        self.go2_controller.send_command(robot.id, command, params)

    def _log(self, message):
        """Add message to log"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    # Signal handlers
    def _on_robot_connected(self, robot_id):
        """Handle robot connected"""
        self._log(f"Robot {robot_id} connected!")
        self._update_robot_list()
        QMessageBox.information(self, "Connected", f"Robot {robot_id} connected successfully!")

    def _on_robot_disconnected(self, robot_id):
        """Handle robot disconnected"""
        self._log(f"Robot {robot_id} disconnected")
        self._update_robot_list()

    def _on_connection_error(self, robot_id, error_msg):
        """Handle connection error"""
        self._log(f"Error: {robot_id} - {error_msg}")
        self._update_robot_list()
        QMessageBox.critical(self, "Connection Error", f"Failed to connect to {robot_id}:\n{error_msg}")

    def _on_robot_state_changed(self, robot_id, state):
        """Handle robot state changed"""
        self._update_robot_list()
