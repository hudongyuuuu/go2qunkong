# ui/main_window.py
"""
Main Window - Application main window
"""

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTabWidget, QStackedWidget, QLabel, QStatusBar,
                             QFrame, QPushButton, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QFont

import sys
from pathlib import Path

from config import COLORS, UI_CONFIG
from ui.dashboard_page import DashboardPage
from ui.robot_list_page import RobotListPage
from ui.timeline_editor import TimelineEditor
from ui.group_control_page import GroupControlPage
from ui.settings_page import SettingsPage

from services.network_service import NetworkService
from services.robot_controller import RobotController
from services.music_service import MusicService
from services.database_service import DatabaseService

from widgets.music_player import MusicPlayer
from models.robot import Robot


class MainWindow(QMainWindow):
    """Main application window"""

    # Signals
    robot_selected = pyqtSignal(str)
    music_playback_started = pyqtSignal()
    music_playback_paused = pyqtSignal()
    music_playback_stopped = pyqtSignal()

    def __init__(self):
        super().__init__()

        # Initialize services
        self.network_service = NetworkService()
        self.robot_controller = RobotController(self.network_service)
        self.music_service = MusicService()
        self.database_service = DatabaseService()

        # Connect to network service signals
        self.network_service.connected.connect(self._on_robot_connected)
        self.network_service.disconnected.connect(self._on_robot_disconnected)

        # Setup UI
        self._setup_ui()
        self._apply_styles()
        self._connect_signals()

        # Load initial data
        self._load_initial_data()

    def _setup_ui(self):
        """Setup UI components"""
        self.setWindowTitle(UI_CONFIG['window_title'])
        self.resize(UI_CONFIG['window_width'], UI_CONFIG['window_height'])
        self.setMinimumSize(UI_CONFIG['min_window_width'], UI_CONFIG['min_window_height'])

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create navigation bar
        self.nav_bar = self._create_navigation_bar()
        main_layout.addWidget(self.nav_bar)

        # Create stacked widget for pages
        self.pages_stack = QStackedWidget()
        self._create_pages()
        main_layout.addWidget(self.pages_stack)

        # Create bottom panel (music player)
        self.bottom_panel = self._create_bottom_panel()
        main_layout.addWidget(self.bottom_panel)

        central_widget.setLayout(main_layout)

        # Create status bar
        self._create_status_bar()

    def _create_navigation_bar(self) -> QFrame:
        """Create navigation bar"""
        nav_frame = QFrame()
        nav_frame.setFixedHeight(60)
        nav_frame.setStyleSheet(f"background-color: {COLORS['card']}; border-bottom: 1px solid {COLORS['border']};")

        layout = QHBoxLayout()
        layout.setContentsMargins(20, 8, 20, 8)

        # Logo/Title
        title_label = QLabel("Unitree GO2AIR")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title_label.setStyleSheet(f"color: {COLORS['primary']};")
        layout.addWidget(title_label)

        layout.addStretch()

        # Navigation buttons
        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "Dashboard"),
            ("robots", "Robots"),
            ("timeline", "Timeline"),
            ("group", "Group Control"),
            ("settings", "Settings"),
        ]

        for key, text in nav_items:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setFixedHeight(40)
            btn.setMinimumWidth(100)
            btn.clicked.connect(lambda checked, k=key: self._navigate_to(k))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {COLORS['text_secondary']};
                    border: none;
                    font-size: 14px;
                    font-weight: 500;
                    padding: 8px 16px;
                }}
                QPushButton:checked {{
                    color: {COLORS['primary']};
                    background-color: rgba(0, 212, 255, 0.1);
                    border-bottom: 2px solid {COLORS['primary']};
                }}
                QPushButton:hover:!checked {{
                    color: {COLORS['accent']};
                }}
            """)
            layout.addWidget(btn)
            self.nav_buttons[key] = btn

        # Set first button as checked
        self.nav_buttons["dashboard"].setChecked(True)

        nav_frame.setLayout(layout)
        return nav_frame

    def _create_pages(self):
        """Create all pages"""
        # Dashboard page
        self.dashboard_page = DashboardPage(self.database_service)
        self.pages_stack.addWidget(self.dashboard_page)

        # Robot list page
        self.robot_list_page = RobotListPage(
            self.network_service,
            self.robot_controller,
            self.database_service
        )
        self.pages_stack.addWidget(self.robot_list_page)

        # Timeline editor
        self.timeline_editor = TimelineEditor(
            self.robot_controller,
            self.music_service,
            self.database_service
        )
        self.pages_stack.addWidget(self.timeline_editor)

        # Group control page
        self.group_control_page = GroupControlPage(
            self.robot_controller,
            self.database_service
        )
        self.pages_stack.addWidget(self.group_control_page)

        # Settings page
        self.settings_page = SettingsPage()
        self.pages_stack.addWidget(self.settings_page)

    def _create_bottom_panel(self) -> QFrame:
        """Create bottom panel with music player"""
        panel = QFrame()
        panel.setFixedHeight(100)
        panel.setStyleSheet(f"background-color: {COLORS['card']}; border-top: 1px solid {COLORS['border']};")

        layout = QHBoxLayout()
        layout.setContentsMargins(20, 10, 20, 10)

        # Music player
        self.music_player = MusicPlayer()
        self.music_player.setFixedHeight(80)

        # Connect music player signals
        self.music_player.play_clicked.connect(self._on_play_clicked)
        self.music_player.pause_clicked.connect(self._on_pause_clicked)
        self.music_player.stop_clicked.connect(self._on_stop_clicked)

        layout.addWidget(self.music_player)
        layout.addStretch()

        panel.setLayout(layout)
        return panel

    def _create_status_bar(self):
        """Create status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Status labels
        self.connection_status_label = QLabel("Connected: 0 robots")
        self.status_bar.addPermanentWidget(self.connection_status_label)

        self.music_status_label = QLabel("")
        self.status_bar.addPermanentWidget(self.music_status_label)

    def _apply_styles(self):
        """Apply application styles"""
        # Load stylesheet
        style_path = Path(__file__).parent.parent / "resources" / "styles" / "dark_theme.qss"
        if style_path.exists():
            with open(style_path, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())

    def _connect_signals(self):
        """Connect signals"""
        # Connect music service signals
        self.music_service.track_loaded.connect(self._on_track_loaded)
        self.music_service.playback_started.connect(self._on_playback_started)
        self.music_service.playback_paused.connect(self._on_playback_paused)
        self.music_service.playback_stopped.connect(self._on_playback_stopped)
        self.music_service.position_changed.connect(self._on_position_changed)

    def _navigate_to(self, page_key: str):
        """Navigate to page"""
        # Update buttons
        for key, btn in self.nav_buttons.items():
            btn.setChecked(key == page_key)

        # Update pages
        page_map = {
            "dashboard": 0,
            "robots": 1,
            "timeline": 2,
            "group": 3,
            "settings": 4,
        }

        self.pages_stack.setCurrentIndex(page_map.get(page_key, 0))

    def _load_initial_data(self):
        """Load initial data from database"""
        # Load robots
        robots = self.database_service.get_all_robots()

        # Update status
        self._update_connection_status()

    def _update_connection_status(self):
        """Update connection status label"""
        connected_count = len(self.network_service.active_connections)
        self.connection_status_label.setText(f"Connected: {connected_count} robots")

    # Network service callbacks
    def _on_robot_connected(self, robot_id: str):
        """Handle robot connected"""
        self.status_bar.showMessage(f"Robot {robot_id} connected", 3000)
        self._update_connection_status()

    def _on_robot_disconnected(self, robot_id: str):
        """Handle robot disconnected"""
        self.status_bar.showMessage(f"Robot {robot_id} disconnected", 3000)
        self._update_connection_status()

    # Music service callbacks
    def _on_track_loaded(self, track):
        """Handle track loaded"""
        self.music_player.load_track(track)
        self.music_status_label.setText(f"Track: {track.name}")

    def _on_play_clicked(self):
        """Handle play button clicked"""
        self.music_service.play()

    def _on_pause_clicked(self):
        """Handle pause button clicked"""
        self.music_service.pause()

    def _on_stop_clicked(self):
        """Handle stop button clicked"""
        self.music_service.stop()

    def _on_playback_started(self):
        """Handle playback started"""
        self.music_player.set_playing(True)
        self.music_status_label.setText("Playing")

    def _on_playback_paused(self):
        """Handle playback paused"""
        self.music_player.set_playing(False)
        self.music_status_label.setText("Paused")

    def _on_playback_stopped(self):
        """Handle playback stopped"""
        self.music_player.set_playing(False)
        self.music_player.set_position(0)
        self.music_status_label.setText("Stopped")

    def _on_position_changed(self, position_ms: float):
        """Handle position changed"""
        self.music_player.set_position(position_ms)

    def closeEvent(self, event):
        """Handle window close"""
        # Stop timers
        if hasattr(self.dashboard_page, 'refresh_timer'):
            self.dashboard_page.refresh_timer.stop()

        # Cleanup services
        self.network_service.shutdown()
        self.music_service.cleanup()
        self.database_service.close()

        event.accept()
