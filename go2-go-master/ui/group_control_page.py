# ui/group_control_page.py
"""
Group Control Page - Manage robot groups and formations
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QListWidget, QListWidgetItem,
                             QSplitter, QFrame, QFormLayout, QSpinBox,
                             QDoubleSpinBox, QDialog, QMessageBox, QLineEdit)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from models.robot import Robot, RobotGroup
from models.group import Formation, FormationType
from widgets.formation_preview import FormationPreview

from services.robot_controller import RobotController
from services.database_service import DatabaseService

from config import COLORS, FORMATION_TYPES


class GroupControlPage(QWidget):
    """Group control and formation management page"""

    def __init__(self, robot_controller: RobotController,
                 database_service: DatabaseService):
        super().__init__()

        self.robot_controller = robot_controller
        self.database_service = database_service

        self.current_group: RobotGroup = None
        self.robots = []
        self.selected_robots = []

        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header = self._create_header()
        layout.addWidget(header)

        # Main content with splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left panel - Group management
        left_panel = self._create_group_panel()
        splitter.addWidget(left_panel)

        # Right panel - Formation preview
        right_panel = self._create_formation_panel()
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)

        # Bottom controls
        controls = self._create_controls()
        layout.addWidget(controls)

        self.setLayout(layout)

    def _create_header(self) -> QWidget:
        """Create header section"""
        header = QWidget()
        layout = QHBoxLayout()

        title_label = QLabel("Group Control")
        title_label.setProperty("heading", True)
        title_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
        layout.addWidget(title_label)

        layout.addStretch()

        self.create_group_btn = QPushButton("+ Create Group")
        self.create_group_btn.clicked.connect(self._create_group)
        layout.addWidget(self.create_group_btn)

        header.setLayout(layout)
        return header

    def _create_group_panel(self) -> QWidget:
        """Create group management panel"""
        panel = QFrame()
        panel.setStyleSheet(f"background-color: {COLORS['card']}; border-radius: 12px;")

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)

        title_label = QLabel("Groups")
        title_label.setProperty("subheading", True)
        title_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(title_label)

        # Groups list
        self.groups_list = QListWidget()
        self.groups_list.itemClicked.connect(self._on_group_selected)
        layout.addWidget(self.groups_list)

        # Group details
        details_frame = QFrame()
        details_layout = QFormLayout()

        self.group_name_label = QLabel("No group selected")
        details_layout.addRow("Name:", self.group_name_label)

        self.formation_label = QLabel("--")
        details_layout.addRow("Formation:", self.formation_label)

        self.robot_count_label = QLabel("0")
        details_layout.addRow("Robots:", self.robot_count_label)

        details_frame.setLayout(details_layout)
        layout.addWidget(details_frame)

        # Formation selection
        formation_layout = QVBoxLayout()
        formation_layout.addWidget(QLabel("Formation Type:"))

        self.formation_combo = QComboBox()
        for key, value in FORMATION_TYPES.items():
            self.formation_combo.addItem(value, key)
        self.formation_combo.currentTextChanged.connect(self._on_formation_changed)
        formation_layout.addWidget(self.formation_combo)

        # Formation parameters
        params_layout = QFormLayout()

        self.spacing_spin = QDoubleSpinBox()
        self.spacing_spin.setRange(0.5, 5.0)
        self.spacing_spin.setValue(1.0)
        self.spacing_spin.setSingleStep(0.1)
        self.spacing_spin.setSuffix(" m")
        self.spacing_spin.valueChanged.connect(self._update_formation)
        params_layout.addRow("Spacing:", self.spacing_spin)

        self.orientation_spin = QDoubleSpinBox()
        self.orientation_spin.setRange(0, 360)
        self.orientation_spin.setValue(0)
        self.orientation_spin.setSuffix(" °")
        self.orientation_spin.valueChanged.connect(self._update_formation)
        params_layout.addRow("Orientation:", self.orientation_spin)

        formation_layout.addLayout(params_layout)
        layout.addLayout(formation_layout)

        panel.setLayout(layout)
        return panel

    def _create_formation_panel(self) -> QWidget:
        """Create formation preview panel"""
        panel = QFrame()
        panel.setStyleSheet(f"background-color: {COLORS['card']}; border-radius: 12px;")

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)

        title_label = QLabel("Formation Preview")
        title_label.setProperty("subheading", True)
        title_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(title_label)

        # Formation preview widget
        self.formation_preview = FormationPreview()
        layout.addWidget(self.formation_preview, 1)

        panel.setLayout(layout)
        return panel

    def _create_controls(self) -> QWidget:
        """Create bottom controls"""
        controls = QFrame()
        controls.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card']};
                border-radius: 12px;
                padding: 12px;
            }}
        """)

        layout = QHBoxLayout()

        # Available robots
        layout.addWidget(QLabel("Available Robots:"))
        self.available_robots_list = QListWidget()
        self.available_robots_list.setSelectionMode(QListWidget.MultiSelection)
        self.available_robots_list.setMaximumHeight(100)
        layout.addWidget(self.available_robots_list, 1)

        # Add/Remove buttons
        btn_layout = QVBoxLayout()
        add_btn = QPushButton(">> Add")
        add_btn.clicked.connect(self._add_robots_to_group)
        btn_layout.addWidget(add_btn)

        remove_btn = QPushButton("<< Remove")
        remove_btn.clicked.connect(self._remove_robots_from_group)
        btn_layout.addWidget(remove_btn)
        layout.addLayout(btn_layout)

        # Group robots
        layout.addWidget(QLabel("Group Robots:"))
        self.group_robots_list = QListWidget()
        self.group_robots_list.setSelectionMode(QListWidget.MultiSelection)
        self.group_robots_list.setMaximumHeight(100)
        layout.addWidget(self.group_robots_list, 1)

        layout.addStretch()

        # Movement controls
        move_btn = QPushButton("Move to Formation")
        move_btn.setProperty("success", True)
        move_btn.clicked.connect(self._move_to_formation)
        layout.addWidget(move_btn)

        controls.setLayout(layout)
        return controls

    def _load_data(self):
        """Load data from database"""
        # Load robots
        self.robots = self.database_service.get_all_robots()

        # Load groups
        groups = self.database_service.get_all_groups()

        # Update UI
        self.available_robots_list.clear()
        for robot in self.robots:
            self.available_robots_list.addItem(robot.name)

        self.groups_list.clear()
        for group in groups:
            self.groups_list.addItem(group.name)

    def _create_group(self):
        """Create new group"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Create Group")
        dialog.setFixedWidth(300)

        layout = QFormLayout()

        name_input = QLineEdit()
        layout.addRow("Group Name:", name_input)

        buttons = QHBoxLayout()
        ok_btn = QPushButton("Create")
        cancel_btn = QPushButton("Cancel")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)

        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addLayout(buttons)
        dialog.setLayout(main_layout)

        if dialog.exec_() == QDialog.Accepted:
            import uuid
            group = RobotGroup(
                group_id=str(uuid.uuid4()),
                name=name_input.text()
            )

            self.database_service.add_group(group)
            self._load_data()

    def _on_group_selected(self, item: QListWidgetItem):
        """Handle group selected"""
        group_name = item.text()
        groups = self.database_service.get_all_groups()

        self.current_group = next((g for g in groups if g.name == group_name), None)

        if self.current_group:
            # Update details
            self.group_name_label.setText(self.current_group.name)
            self.formation_label.setText(self.current_group.formation_type)
            self.robot_count_label.setText(str(len(self.current_group.robots)))

            # Update formation combo
            index = self.formation_combo.findData(self.current_group.formation_type)
            if index >= 0:
                self.formation_combo.setCurrentIndex(index)

            # Update group robots list
            self.group_robots_list.clear()
            for robot_id in self.current_group.robots:
                robot = next((r for r in self.robots if r.id == robot_id), None)
                if robot:
                    self.group_robots_list.addItem(robot.name)

            # Update formation preview
            self._update_formation()

    def _on_formation_changed(self, formation_name: str):
        """Handle formation type changed"""
        if self.current_group:
            self.current_group.formation_type = formation_name
            self._update_formation()

    def _update_formation(self):
        """Update formation preview"""
        if self.current_group:
            formation = Formation(
                type=FormationType(self.current_group.formation_type),
                spacing=self.spacing_spin.value(),
                orientation=self.orientation_spin.value()
            )

            self.formation_preview.set_formation(formation, self.current_group.robots)

    def _add_robots_to_group(self):
        """Add selected robots to group"""
        if not self.current_group:
            QMessageBox.warning(self, "Warning", "Please select a group first.")
            return

        for item in self.available_robots_list.selectedItems():
            robot_name = item.text()
            robot = next((r for r in self.robots if r.name == robot_name), None)

            if robot and robot.id not in self.current_group.robots:
                self.current_group.add_robot(robot.id)
                self.group_robots_list.addItem(robot_name)

        self.robot_count_label.setText(str(len(self.current_group.robots)))
        self._update_formation()

    def _remove_robots_from_group(self):
        """Remove selected robots from group"""
        if not self.current_group:
            return

        for item in self.group_robots_list.selectedItems():
            robot_name = item.text()
            robot = next((r for r in self.robots if r.name == robot_name), None)

            if robot:
                self.current_group.remove_robot(robot.id)
                self.group_robots_list.takeItem(self.group_robots_list.row(item))

        self.robot_count_label.setText(str(len(self.current_group.robots)))
        self._update_formation()

    def _move_to_formation(self):
        """Move robots to formation"""
        if not self.current_group or not self.current_group.robots:
            QMessageBox.warning(self, "Warning", "Please add robots to the group first.")
            return

        formation = Formation(
            type=FormationType(self.current_group.formation_type),
            spacing=self.spacing_spin.value(),
            orientation=self.orientation_spin.value()
        )

        success = self.robot_controller.move_group_to_formation(
            self.current_group.robots,
            formation
        )

        if success:
            QMessageBox.information(self, "Success", "Robots are moving to formation.")
        else:
            QMessageBox.warning(self, "Error", "Failed to send movement commands.")
