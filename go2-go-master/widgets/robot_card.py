# widgets/robot_card.py
"""
Robot Card Widget - Display robot information in a card
"""

from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                             QProgressBar, QPushButton, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont

from models.robot import Robot, ConnectionStatus
from widgets.status_indicator import StatusIndicator
from config import COLORS


class RobotCard(QFrame):
    """Robot card widget - compact horizontal layout"""

    # Signals
    connect_clicked = pyqtSignal(str)
    disconnect_clicked = pyqtSignal(str)
    card_clicked = pyqtSignal(str)

    def __init__(self, robot: Robot):
        super().__init__()

        self.robot = robot
        self._setup_ui()
        self._update_display()

    def _setup_ui(self):
        """Setup UI components - compact vertical layout"""
        self.setFrameStyle(QFrame.NoFrame)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card']};
                border-radius: 8px;
                border: 1px solid {COLORS['border']};
            }}
            QFrame:hover {{
                background-color: {COLORS['card_hover']};
                border: 1px solid {COLORS['primary']};
            }}
        """)
        self.setMinimumHeight(120)
        self.setMaximumHeight(140)
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        # Left side - Status indicator
        self.status_indicator = StatusIndicator()
        self.status_indicator.setFixedSize(50, 50)
        layout.addWidget(self.status_indicator)

        # Middle - Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        # Name and ID
        self.name_label = QLabel(self.robot.name)
        self.name_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.name_label.setStyleSheet(f"color: {COLORS['text_primary']};")
        info_layout.addWidget(self.name_label)

        self.id_label = QLabel(f"ID: {self.robot.id}")
        self.id_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        info_layout.addWidget(self.id_label)

        # IP and Model
        details_text = f"{self.robot.ip}:{self.robot.port} | {self.robot.model}"
        self.details_label = QLabel(details_text)
        self.details_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        info_layout.addWidget(self.details_label)

        layout.addLayout(info_layout)
        layout.addStretch()

        # Right side - Battery and State
        right_layout = QVBoxLayout()
        right_layout.setSpacing(4)

        # Battery
        battery_layout = QVBoxLayout()
        battery_layout.setSpacing(2)

        battery_label = QLabel("Battery")
        battery_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 10px;")
        battery_layout.addWidget(battery_label)

        self.battery_bar = QProgressBar()
        self.battery_bar.setFixedHeight(16)
        self.battery_bar.setFixedWidth(100)
        self.battery_bar.setTextVisible(False)
        battery_layout.addWidget(self.battery_bar)

        self.battery_label = QLabel("")
        self.battery_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 10px;")
        self.battery_label.setAlignment(Qt.AlignRight)
        battery_layout.addWidget(self.battery_label)

        right_layout.addLayout(battery_layout)

        # State
        self.state_label = QLabel(f"{self.robot.state.value.title()}")
        self.state_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        self.state_label.setAlignment(Qt.AlignRight)
        right_layout.addWidget(self.state_label)

        layout.addLayout(right_layout)

        self.setLayout(layout)

    def _update_display(self):
        """Update display with robot data"""
        # Update status indicator
        status_map = {
            ConnectionStatus.CONNECTED: 'connected',
            ConnectionStatus.CONNECTING: 'connecting',
            ConnectionStatus.DISCONNECTED: 'disconnected',
            ConnectionStatus.ERROR: 'error',
        }
        self.status_indicator.set_status(status_map.get(self.robot.connection_status, 'disconnected'))

        # Update battery
        self.battery_bar.setValue(int(self.robot.battery.level))
        self.battery_label.setText(f"{self.robot.battery.level:.1f}%")

        # Color code battery
        if self.robot.is_critical_battery():
            self.battery_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {COLORS['error']}; }}")
        elif self.robot.is_low_battery():
            self.battery_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {COLORS['warning']}; }}")
        else:
            self.battery_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {COLORS['success']}; }}")

    def _on_connect_clicked(self):
        """Handle connect button click"""
        if self.robot.is_connected():
            self.disconnect_clicked.emit(self.robot.id)
        else:
            self.connect_clicked.emit(self.robot.id)

    def _on_view_clicked(self):
        """Handle view details click"""
        self.card_clicked.emit(self.robot.id)

    def update_robot(self, robot: Robot):
        """Update robot data"""
        self.robot = robot
        self._update_display()

    def mouseDoubleClickEvent(self, event):
        """Handle double click"""
        self.card_clicked.emit(self.robot.id)
        super().mouseDoubleClickEvent(event)
