# ui/dashboard_page.py
"""
Dashboard Page - Overview of robot status and statistics
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLabel, QFrame, QScrollArea, QPushButton, QProgressBar)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

from models.robot import Robot, ConnectionStatus
from widgets.robot_card import RobotCard
from services.database_service import DatabaseService
from config import COLORS


class DashboardPage(QWidget):
    """Dashboard page showing robot overview"""

    def __init__(self, database_service: DatabaseService):
        super().__init__()

        self.database_service = database_service
        self.robots = []
        self.robot_cards = {}  # robot_id -> RobotCard

        self._setup_ui()
        self._load_data()

        # Refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_data)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds

    def _setup_ui(self):
        """Setup UI components"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create scroll area for main content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.NoFrame)

        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)

        # Header
        header = self._create_header()
        content_layout.addWidget(header)

        # Statistics cards
        stats_layout = self._create_statistics()
        content_layout.addLayout(stats_layout)

        # Robots section
        robots_section = self._create_robots_section()
        content_layout.addWidget(robots_section)

        # Add stretch at bottom for scrolling
        content_layout.addStretch()

        content_widget.setLayout(content_layout)
        scroll_area.setWidget(content_widget)

        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

    def _create_header(self) -> QFrame:
        """Create header section"""
        header = QFrame()
        header.setFixedHeight(50)
        layout = QHBoxLayout()

        title_label = QLabel("Dashboard")
        title_label.setProperty("heading", True)
        title_label.setFont(QFont("Segoe UI", 20, QFont.Bold))
        layout.addWidget(title_label)

        layout.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFixedHeight(32)
        refresh_btn.clicked.connect(self._refresh_data)
        layout.addWidget(refresh_btn)

        header.setLayout(layout)
        return header

    def _create_statistics(self) -> QGridLayout:
        """Create statistics cards grid"""
        grid = QGridLayout()
        grid.setSpacing(10)
        grid.setContentsMargins(0, 0, 0, 0)

        # Define stats
        stats = [
            ("Total Robots", "0", COLORS['primary'], "total_robots"),
            ("Connected", "0", COLORS['success'], "connected_robots"),
            ("Offline", "0", COLORS['text_secondary'], "offline_robots"),
            ("Low Battery", "0", COLORS['warning'], "low_battery"),
            ("Errors", "0", COLORS['error'], "errors"),
            ("Groups", "0", COLORS['accent'], "groups"),
        ]

        self.stats_labels = {}

        for i, (title, value, color, key) in enumerate(stats):
            card = self._create_stat_card(title, value, color, key)
            grid.addWidget(card, i // 3, i % 3)
            self.stats_labels[key] = card.findChild(QLabel, f"{key}_value")

        return grid

    def _create_stat_card(self, title: str, value: str, color: str, key: str) -> QFrame:
        """Create a statistics card"""
        card = QFrame()
        card.setMinimumHeight(100)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                padding: 12px;
            }}
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setProperty("caption", True)
        title_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setObjectName(f"{key}_value")
        value_label.setFont(QFont("Segoe UI", 20, QFont.Bold))
        value_label.setStyleSheet(f"color: {color};")
        layout.addWidget(value_label)

        layout.addStretch()

        card.setLayout(layout)
        return card

    def _create_robots_section(self) -> QFrame:
        """Create robots list section - vertical layout"""
        section = QFrame()
        section.setStyleSheet(f"background-color: {COLORS['card']}; border-radius: 12px; border: 1px solid {COLORS['border']};")
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()

        title_label = QLabel("Robots Overview")
        title_label.setProperty("subheading", True)
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        robot_count_label = QLabel("0 robots")
        robot_count_label.setProperty("caption", True)
        robot_count_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.robot_count_label = robot_count_label
        header_layout.addWidget(robot_count_label)

        layout.addLayout(header_layout)

        # Robot cards container - vertical layout
        self.robots_container = QWidget()
        self.robots_layout = QVBoxLayout()
        self.robots_layout.setSpacing(10)
        self.robots_layout.setAlignment(Qt.AlignTop)
        self.robots_container.setLayout(self.robots_layout)

        layout.addWidget(self.robots_container)

        section.setLayout(layout)
        return section

    def _load_data(self):
        """Load data - using local data only"""
        try:
            # Use empty list for now - robots will be added via NetworkService
            self.robots = []

            # Update statistics
            self._update_statistics()

            # Update robot cards
            self._update_robot_cards()
        except Exception as e:
            print(f"Error loading data: {e}")

    def _refresh_data(self):
        """Refresh data"""
        self._load_data()

    def _update_statistics(self):
        """Update statistics display"""
        try:
            total = len(self.robots)
            connected = sum(1 for r in self.robots if r.connection_status == ConnectionStatus.CONNECTED)
            offline = total - connected
            low_battery = sum(1 for r in self.robots if r.is_low_battery())
            errors = sum(1 for r in self.robots if r.connection_status == ConnectionStatus.ERROR)

            # Use 0 for groups since we're not using database
            groups = 0

            # Update labels
            self.stats_labels["total_robots"].setText(str(total))
            self.stats_labels["connected_robots"].setText(str(connected))
            self.stats_labels["offline_robots"].setText(str(offline))
            self.stats_labels["low_battery"].setText(str(low_battery))
            self.stats_labels["errors"].setText(str(errors))
            self.stats_labels["groups"].setText(str(groups))

            # Update robot count label
            if hasattr(self, 'robot_count_label'):
                self.robot_count_label.setText(f"{total} robots")
        except Exception as e:
            print(f"Error updating statistics: {e}")

    def _update_robot_cards(self):
        """Update robot cards display"""
        # Clear existing cards
        for card in self.robot_cards.values():
            card.setParent(None)
        self.robot_cards.clear()

        # Add cards for first 6 robots
        for robot in self.robots[:6]:
            card = RobotCard(robot)
            self.robots_layout.addWidget(card)
            self.robot_cards[robot.id] = card
