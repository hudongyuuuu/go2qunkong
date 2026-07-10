# ui/settings_page.py
"""
Settings Page - Application settings and configuration
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QScrollArea, QFrame, QFormLayout,
                             QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
                             QComboBox, QTabWidget, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from config import COLORS


class SettingsPage(QWidget):
    """Settings page"""

    def __init__(self):
        super().__init__()

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header = self._create_header()
        layout.addWidget(header)

        # Settings tabs
        tabs = QTabWidget()
        tabs.addTab(self._create_connection_settings(), "Connection")
        tabs.addTab(self._create_robot_settings(), "Robots")
        tabs.addTab(self._create_music_settings(), "Music")
        tabs.addTab(self._create_timeline_settings(), "Timeline")
        tabs.addTab(self._create_appearance_settings(), "Appearance")
        tabs.addTab(self._create_advanced_settings(), "Advanced")
        tabs.addTab(self._create_about_settings(), "About")

        layout.addWidget(tabs)

        # Bottom buttons
        buttons = QHBoxLayout()
        buttons.addStretch()

        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.setProperty("secondary", True)
        self.reset_btn.clicked.connect(self._reset_to_defaults)
        buttons.addWidget(self.reset_btn)

        self.save_btn = QPushButton("Save Settings")
        self.save_btn.clicked.connect(self._save_settings)
        buttons.addWidget(self.save_btn)

        layout.addLayout(buttons)

        self.setLayout(layout)

    def _create_header(self) -> QWidget:
        """Create header section"""
        header = QWidget()
        layout = QHBoxLayout()

        title_label = QLabel("Settings")
        title_label.setProperty("heading", True)
        title_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
        layout.addWidget(title_label)

        layout.addStretch()

        header.setLayout(layout)
        return header

    def _create_connection_settings(self) -> QWidget:
        """Create connection settings panel"""
        panel = QScrollArea()
        panel.setWidgetResizable(True)
        panel.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # HTTP Port
        form_layout = QFormLayout()

        self.http_port_spin = QSpinBox()
        self.http_port_spin.setRange(1, 65535)
        self.http_port_spin.setValue(8080)
        form_layout.addRow("HTTP Port:", self.http_port_spin)

        # WebSocket Port
        self.ws_port_spin = QSpinBox()
        self.ws_port_spin.setRange(1, 65535)
        self.ws_port_spin.setValue(8081)
        form_layout.addRow("WebSocket Port:", self.ws_port_spin)

        # Timeout
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 60)
        self.timeout_spin.setValue(10)
        self.timeout_spin.setSuffix(" s")
        form_layout.addRow("Connection Timeout:", self.timeout_spin)

        # Ping Interval
        self.ping_interval_spin = QSpinBox()
        self.ping_interval_spin.setRange(1, 30)
        self.ping_interval_spin.setValue(5)
        self.ping_interval_spin.setSuffix(" s")
        form_layout.addRow("Ping Interval:", self.ping_interval_spin)

        layout.addLayout(form_layout)

        layout.addStretch()
        content.setLayout(layout)
        panel.setWidget(content)
        return panel

    def _create_robot_settings(self) -> QWidget:
        """Create robot settings panel"""
        panel = QScrollArea()
        panel.setWidgetResizable(True)
        panel.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        form_layout = QFormLayout()

        # Max robots
        self.max_robots_spin = QSpinBox()
        self.max_robots_spin.setRange(1, 100)
        self.max_robots_spin.setValue(20)
        form_layout.addRow("Maximum Robots:", self.max_robots_spin)

        # Connection timeout
        self.robot_timeout_spin = QSpinBox()
        self.robot_timeout_spin.setRange(10, 120)
        self.robot_timeout_spin.setValue(30)
        self.robot_timeout_spin.setSuffix(" s")
        form_layout.addRow("Robot Connection Timeout:", self.robot_timeout_spin)

        # Position update rate
        self.update_rate_spin = QSpinBox()
        self.update_rate_spin.setRange(1, 60)
        self.update_rate_spin.setValue(10)
        self.update_rate_spin.setSuffix(" Hz")
        form_layout.addRow("Position Update Rate:", self.update_rate_spin)

        layout.addLayout(form_layout)

        # Auto-reconnect
        self.auto_reconnect_check = QCheckBox("Automatically reconnect to robots")
        self.auto_reconnect_check.setChecked(True)
        layout.addWidget(self.auto_reconnect_check)

        layout.addStretch()
        content.setLayout(layout)
        panel.setWidget(content)
        return panel

    def _create_music_settings(self) -> QWidget:
        """Create music settings panel"""
        panel = QScrollArea()
        panel.setWidgetResizable(True)
        panel.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        form_layout = QFormLayout()

        # Default volume
        self.default_volume_spin = QDoubleSpinBox()
        self.default_volume_spin.setRange(0.0, 1.0)
        self.default_volume_spin.setValue(0.7)
        self.default_volume_spin.setSingleStep(0.1)
        form_layout.addRow("Default Volume:", self.default_volume_spin)

        # Default BPM
        self.default_bpm_spin = QSpinBox()
        self.default_bpm_spin.setRange(60, 200)
        self.default_bpm_spin.setValue(120)
        form_layout.addRow("Default BPM:", self.default_bpm_spin)

        layout.addLayout(form_layout)

        # Auto-detect BPM
        self.auto_detect_bpm_check = QCheckBox("Automatically detect BPM from audio files")
        self.auto_detect_bpm_check.setChecked(True)
        layout.addWidget(self.auto_detect_bpm_check)

        # Music library path
        music_library_layout = QHBoxLayout()
        music_library_layout.addWidget(QLabel("Music Library:"))

        self.music_library_path = QLineEdit()
        music_library_layout.addWidget(self.music_library_path)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_music_library)
        music_library_layout.addWidget(browse_btn)

        layout.addLayout(music_library_layout)

        layout.addStretch()
        content.setLayout(layout)
        panel.setWidget(content)
        return panel

    def _create_timeline_settings(self) -> QWidget:
        """Create timeline settings panel"""
        panel = QScrollArea()
        panel.setWidgetResizable(True)
        panel.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        form_layout = QFormLayout()

        # Grid snap interval
        self.grid_snap_spin = QSpinBox()
        self.grid_snap_spin.setRange(50, 500)
        self.grid_snap_spin.setValue(100)
        self.grid_snap_spin.setSuffix(" ms")
        self.grid_snap_spin.valueChanged.connect(self._on_grid_snap_changed)
        form_layout.addRow("Grid Snap Interval:", self.grid_snap_spin)

        # Min zoom
        self.min_zoom_spin = QDoubleSpinBox()
        self.min_zoom_spin.setRange(0.1, 1.0)
        self.min_zoom_spin.setValue(0.5)
        form_layout.addRow("Minimum Zoom:", self.min_zoom_spin)

        # Max zoom
        self.max_zoom_spin = QDoubleSpinBox()
        self.max_zoom_spin.setRange(1.0, 5.0)
        self.max_zoom_spin.setValue(3.0)
        form_layout.addRow("Maximum Zoom:", self.max_zoom_spin)

        layout.addLayout(form_layout)

        # Track labels
        layout.addWidget(QLabel("Track Labels:"))

        self.track1_label = QLineEdit("Robot 1")
        self.track2_label = QLineEdit("Robot 2")
        self.track3_label = QLineEdit("Robot 3")
        self.track4_label = QLineEdit("Robot 4")

        track_form = QFormLayout()
        track_form.addRow("Track 1:", self.track1_label)
        track_form.addRow("Track 2:", self.track2_label)
        track_form.addRow("Track 3:", self.track3_label)
        track_form.addRow("Track 4:", self.track4_label)

        layout.addLayout(track_form)

        layout.addStretch()
        content.setLayout(layout)
        panel.setWidget(content)
        return panel

    def _create_appearance_settings(self) -> QWidget:
        """Create appearance settings panel"""
        panel = QScrollArea()
        panel.setWidgetResizable(True)
        panel.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Theme
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Theme:"))

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()

        layout.addLayout(theme_layout)

        # Accent color
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Accent Color:"))

        self.accent_color_combo = QComboBox()
        self.accent_color_combo.addItems(["Blue", "Green", "Purple", "Orange", "Red"])
        color_layout.addWidget(self.accent_color_combo)
        color_layout.addStretch()

        layout.addLayout(color_layout)

        # Font size
        font_layout = QFormLayout()

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(10, 18)
        self.font_size_spin.setValue(14)
        font_layout.addRow("Font Size:", self.font_size_spin)

        layout.addLayout(font_layout)

        # Animations
        self.animations_check = QCheckBox("Enable UI animations")
        self.animations_check.setChecked(True)
        layout.addWidget(self.animations_check)

        layout.addStretch()
        content.setLayout(layout)
        panel.setWidget(content)
        return panel

    def _create_advanced_settings(self) -> QWidget:
        """Create advanced settings panel"""
        panel = QScrollArea()
        panel.setWidgetResizable(True)
        panel.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Logging
        logging_group = QFrame()
        logging_layout = QVBoxLayout()

        logging_title = QLabel("Logging")
        logging_title.setProperty("subheading", True)
        logging_layout.addWidget(logging_title)

        self.enable_logging_check = QCheckBox("Enable logging")
        self.enable_logging_check.setChecked(True)
        logging_layout.addWidget(self.enable_logging_check)

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.setCurrentIndex(1)  # INFO
        logging_layout.addWidget(QLabel("Log Level:"))
        logging_layout.addWidget(self.log_level_combo)

        logging_group.setLayout(logging_layout)
        layout.addWidget(logging_group)

        # Data management
        data_group = QFrame()
        data_layout = QVBoxLayout()

        data_title = QLabel("Data Management")
        data_title.setProperty("subheading", True)
        data_layout.addWidget(data_title)

        clear_db_btn = QPushButton("Clear Database")
        clear_db_btn.setProperty("danger", True)
        clear_db_btn.clicked.connect(self._clear_database)
        data_layout.addWidget(clear_db_btn)

        export_btn = QPushButton("Export Data")
        export_btn.clicked.connect(self._export_data)
        data_layout.addWidget(export_btn)

        import_btn = QPushButton("Import Data")
        import_btn.clicked.connect(self._import_data)
        data_layout.addWidget(import_btn)

        data_group.setLayout(data_layout)
        layout.addWidget(data_group)

        layout.addStretch()
        content.setLayout(layout)
        panel.setWidget(content)
        return panel

    def _create_about_settings(self) -> QWidget:
        """Create about panel"""
        panel = QScrollArea()
        panel.setWidgetResizable(True)
        panel.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # App info
        info_layout = QVBoxLayout()

        title_label = QLabel("Unitree GO2AIR Robot Control")
        title_label.setProperty("heading", True)
        title_label.setFont(QFont("Segoe UI", 18, QFont.Bold))
        info_layout.addWidget(title_label)

        version_label = QLabel("Version: 1.0.0")
        info_layout.addWidget(version_label)

        description_label = QLabel(
            "Desktop application for controlling Unitree GO2AIR robot dogs.\n"
            "Features include robot management, choreography editing, group\n"
            "control, and music synchronization."
        )
        description_label.setWordWrap(True)
        description_label.setProperty("caption", True)
        info_layout.addWidget(description_label)

        layout.addLayout(info_layout)

        layout.addStretch()

        # Links
        links_layout = QVBoxLayout()

        links_layout.addWidget(QLabel("Resources:"))

        docs_btn = QPushButton("Documentation")
        docs_btn.setProperty("secondary", True)
        links_layout.addWidget(docs_btn)

        github_btn = QPushButton("GitHub Repository")
        github_btn.setProperty("secondary", True)
        links_layout.addWidget(github_btn)

        issues_btn = QPushButton("Report Issues")
        issues_btn.setProperty("secondary", True)
        links_layout.addWidget(issues_btn)

        layout.addLayout(links_layout)

        layout.addStretch()
        content.setLayout(layout)
        panel.setWidget(content)
        return panel

    def _browse_music_library(self):
        """Browse for music library directory"""
        directory = QFileDialog.getExistingDirectory(self, "Select Music Library")
        if directory:
            self.music_library_path.setText(directory)

    def _on_grid_snap_changed(self, value: int):
        """Handle grid snap interval changed"""
        # Update timeline config
        pass

    def _clear_database(self):
        """Clear database"""
        reply = QMessageBox.question(
            self,
            "Clear Database",
            "Are you sure you want to clear all data? This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            QMessageBox.information(self, "Success", "Database cleared.")

    def _export_data(self):
        """Export data"""
        QMessageBox.information(self, "Export", "Data exported successfully.")

    def _import_data(self):
        """Import data"""
        QMessageBox.information(self, "Import", "Data imported successfully.")

    def _reset_to_defaults(self):
        """Reset settings to defaults"""
        QMessageBox.information(self, "Reset", "Settings reset to defaults.")

    def _save_settings(self):
        """Save settings"""
        QMessageBox.information(self, "Saved", "Settings saved successfully.")
