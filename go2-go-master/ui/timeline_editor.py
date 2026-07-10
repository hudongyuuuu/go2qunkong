# ui/timeline_editor.py
"""
Timeline Editor - Choreography and action timeline editor
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
                             QFileDialog, QSplitter, QFrame, QScrollArea,
                             QListWidget, QListWidgetItem)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont

from models.action import Action, ActionLibrary
from models.music import MusicTrack, Choreography
from models.robot import Robot

from widgets.timeline_widget import TimelineWidget
from widgets.action_block import ActionBlock

from services.robot_controller import RobotController
from services.music_service import MusicService
from services.database_service import DatabaseService

from config import COLORS


class TimelineEditor(QWidget):
    """Timeline editor for choreography"""

    def __init__(self, robot_controller: RobotController,
                 music_service: MusicService,
                 database_service: DatabaseService):
        super().__init__()

        self.robot_controller = robot_controller
        self.music_service = music_service
        self.database_service = database_service

        self.current_choreography: Choreography = None
        self.selected_track = 0
        self.block_counter = 0

        self._setup_ui()
        self._connect_signals()

        # Load actions
        self._filter_actions("All")

        # Create empty choreography
        self._new_choreography()

    def _setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header = self._create_header()
        layout.addWidget(header)

        # Main content area with splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left panel - Action library
        left_panel = self._create_action_panel()
        splitter.addWidget(left_panel)

        # Right panel - Timeline
        right_panel = self._create_timeline_panel()
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        layout.addWidget(splitter)

        # Bottom controls
        controls = self._create_playback_controls()
        layout.addWidget(controls)

        self.setLayout(layout)

    def _create_header(self) -> QWidget:
        """Create header section"""
        header = QWidget()
        layout = QHBoxLayout()

        title_label = QLabel("Timeline Editor")
        title_label.setProperty("heading", True)
        title_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
        layout.addWidget(title_label)

        layout.addStretch()

        # Choreography controls
        self.save_btn = QPushButton("Save Choreography")
        self.save_btn.clicked.connect(self._save_choreography)
        layout.addWidget(self.save_btn)

        self.load_btn = QPushButton("Load Choreography")
        self.load_btn.clicked.connect(self._load_choreography)
        layout.addWidget(self.load_btn)

        self.new_btn = QPushButton("New")
        self.new_btn.clicked.connect(self._new_choreography)
        layout.addWidget(self.new_btn)

        header.setLayout(layout)
        return header

    def _create_action_panel(self) -> QWidget:
        """Create action library panel"""
        panel = QFrame()
        panel.setStyleSheet(f"background-color: {COLORS['card']}; border-radius: 12px;")
        panel.setMinimumWidth(250)

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)

        title_label = QLabel("Action Library")
        title_label.setProperty("subheading", True)
        title_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(title_label)

        # Category filter
        filter_label = QLabel("Category:")
        filter_label.setProperty("caption", True)
        layout.addWidget(filter_label)

        self.category_combo = QComboBox()
        self.category_combo.addItems(["All", "Basic", "Movement", "Rotation", "Special", "Dance"])
        self.category_combo.currentTextChanged.connect(self._filter_actions)
        layout.addWidget(self.category_combo)

        # Action list
        self.action_list = QListWidget()
        self.action_list.itemDoubleClicked.connect(self._add_action_to_timeline)
        layout.addWidget(self.action_list)

        # Action parameters
        params_group = QFrame()
        params_layout = QVBoxLayout()
        params_layout.setSpacing(4)

        params_title = QLabel("Action Parameters")
        params_title.setProperty("caption", True)
        params_layout.addWidget(params_title)

        params_input_layout = QVBoxLayout()
        params_input_layout.setSpacing(2)
        params_input_layout.addWidget(QLabel("Duration (s):"))
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.1, 10.0)
        self.duration_spin.setValue(2.0)
        self.duration_spin.setSingleStep(0.1)
        params_input_layout.addWidget(self.duration_spin)

        params_input_layout.addWidget(QLabel("Speed:"))
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.1, 3.0)
        self.speed_spin.setValue(1.0)
        self.speed_spin.setSingleStep(0.1)
        params_input_layout.addWidget(self.speed_spin)

        params_layout.addLayout(params_input_layout)

        add_btn = QPushButton("Add to Timeline")
        add_btn.setFixedHeight(32)
        add_btn.clicked.connect(self._add_action_to_timeline)
        params_layout.addWidget(add_btn)

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        panel.setLayout(layout)
        return panel

    def _create_timeline_panel(self) -> QWidget:
        """Create timeline panel"""
        panel = QFrame()
        panel.setStyleSheet(f"background-color: {COLORS['card']}; border-radius: 12px;")

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)

        # Timeline controls
        controls = QHBoxLayout()

        controls.addWidget(QLabel("Track:"))
        self.track_combo = QComboBox()
        self.track_combo.addItems(["Robot 1", "Robot 2", "Robot 3", "Robot 4"])
        self.track_combo.currentIndexChanged.connect(self._on_track_changed)
        controls.addWidget(self.track_combo)

        controls.addStretch()

        self.load_music_btn = QPushButton("Load Music")
        self.load_music_btn.clicked.connect(self._load_music)
        controls.addWidget(self.load_music_btn)

        self.bpm_label = QLabel("BPM: --")
        controls.addWidget(self.bpm_label)

        layout.addLayout(controls)

        # Timeline widget
        self.timeline = TimelineWidget()
        layout.addWidget(self.timeline)

        panel.setLayout(layout)
        return panel

    def _create_playback_controls(self) -> QWidget:
        """Create playback controls"""
        controls = QFrame()
        controls.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card']};
                border-radius: 12px;
                padding: 12px;
            }}
        """)

        layout = QHBoxLayout()

        # Playback buttons
        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self._play_choreography)
        layout.addWidget(self.play_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self._stop_choreography)
        layout.addWidget(self.stop_btn)

        layout.addStretch()

        # Timeline position
        layout.addWidget(QLabel("Position:"))
        self.position_spin = QSpinBox()
        self.position_spin.setRange(0, 60000)
        self.position_spin.setSuffix(" ms")
        self.position_spin.valueChanged.connect(self._on_position_changed)
        layout.addWidget(self.position_spin)

        controls.setLayout(layout)
        return controls

    def _connect_signals(self):
        """Connect signals"""
        self.timeline.block_selected.connect(self._on_block_selected)

    def _filter_actions(self, category: str):
        """Filter action library by category"""
        self.action_list.clear()

        actions = ActionLibrary.get_all_actions()

        for action in actions:
            if category == "All" or self._get_action_category(action.type) == category:
                item = QListWidgetItem(action.name)
                item.setData(Qt.UserRole, action)
                self.action_list.addItem(item)

    def _get_action_category(self, action_type) -> str:
        """Get category for action type"""
        basic = ["stand", "sit", "lie_down"]
        movement = ["walk", "trot", "run", "move_forward", "move_backward", "move_left", "move_right"]
        rotation = ["turn_left", "turn_right"]
        special = ["jump", "wave_hand", "spin"]
        dance = ["dance_move_1", "dance_move_2", "dance_move_3", "dance_move_4", "dance_move_5"]

        if action_type.value in basic:
            return "Basic"
        elif action_type.value in movement:
            return "Movement"
        elif action_type.value in rotation:
            return "Rotation"
        elif action_type.value in special:
            return "Special"
        elif action_type.value in dance:
            return "Dance"
        else:
            return "All"

    def _add_action_to_timeline(self):
        """Add selected action to timeline"""
        current_item = self.action_list.currentItem()
        if not current_item:
            return

        action = current_item.data(Qt.UserRole)

        # Create action block
        duration = self.duration_spin.value() * 1000  # Convert to ms
        block = ActionBlock(action, 0, duration)
        block_id = f"block_{self.block_counter}"
        self.block_counter += 1

        self.timeline.add_action_block(block_id, block, self.selected_track)

    def _on_track_changed(self, index: int):
        """Handle track selection changed"""
        self.selected_track = index

    def _on_block_selected(self, block_info: dict):
        """Handle block selected"""
        pass  # Could show block details

    def _on_position_changed(self, position: int):
        """Handle position changed"""
        self.timeline.set_playhead_position(float(position))

    def _load_music(self):
        """Load music file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Music",
            "",
            "Audio Files (*.mp3 *.wav *.ogg *.flac)"
        )

        if file_path:
            track = self.music_service.load_track(file_path)
            if track:
                self.current_choreography.music_track = track
                self.bpm_label.setText(f"BPM: {track.bpm}")

    def _new_choreography(self):
        """Create new choreography"""
        import uuid
        self.current_choreography = Choreography(
            id=str(uuid.uuid4()),
            name="New Choreography"
        )
        self.timeline.clear_all_blocks()
        self.block_counter = 0

    def _save_choreography(self):
        """Save choreography to database"""
        self.current_choreography.name = f"Choreography_{self.block_counter}"
        self.database_service.save_choreography(self.current_choreography)

    def _load_choreography(self):
        """Load choreography from database"""
        # Show dialog to select choreography
        choreographies = self.database_service.get_all_choreographies()

        if choreographies:
            # For now, just load the first one
            self.current_choreography = choreographies[0]

    def _play_choreography(self):
        """Play choreography"""
        # This would send commands to robots
        pass

    def _stop_choreography(self):
        """Stop choreography"""
        # This would stop all robots
        pass
