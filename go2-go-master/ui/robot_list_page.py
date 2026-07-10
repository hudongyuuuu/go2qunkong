# ui/robot_list_page.py
"""
Robot List Page - Manage robot connections and details
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLabel, QLineEdit, QPushButton, QComboBox, QDialog,
                             QFormLayout, QSpinBox, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox, QMenu, QAction)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from models.robot import Robot, ConnectionStatus
from services.network_service import NetworkService
from services.robot_controller import RobotController
from services.database_service import DatabaseService
from widgets.robot_card import RobotCard
from config import COLORS


class RobotListPage(QWidget):
    """Robot list and management page"""

    robot_updated = pyqtSignal(str)

    def __init__(self, network_service: NetworkService,
                 robot_controller: RobotController,
                 database_service: DatabaseService):
        super().__init__()

        self.network_service = network_service
        self.robot_controller = robot_controller
        self.database_service = database_service

        self.robots = []
        self.current_view = "grid"  # grid or list
        self.filter_text = ""

        self._setup_ui()
        self._load_robots()

        # Connect signals
        self.network_service.connected.connect(self._on_robot_connected)
        self.network_service.disconnected.connect(self._on_robot_disconnected)

    def _setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        header = self._create_header()
        layout.addWidget(header)

        # Controls
        controls = self._create_controls()
        layout.addWidget(controls)

        # Content area
        self.content_widget = QWidget()
        self.content_layout = QGridLayout()
        self.content_layout.setSpacing(15)
        self.content_widget.setLayout(self.content_layout)
        layout.addWidget(self.content_widget)

        self.setLayout(layout)

    def _create_header(self) -> QWidget:
        """Create header section"""
        header = QWidget()
        layout = QHBoxLayout()

        title_label = QLabel("Robot Management")
        title_label.setProperty("heading", True)
        title_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
        layout.addWidget(title_label)

        layout.addStretch()

        # Add robot button
        self.add_robot_btn = QPushButton("+ Add Robot")
        self.add_robot_btn.clicked.connect(self._show_add_robot_dialog)
        layout.addWidget(self.add_robot_btn)

        header.setLayout(layout)
        return header

    def _create_controls(self) -> QWidget:
        """Create control panel"""
        controls = QWidget()
        controls.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['card']};
                border-radius: 12px;
                padding: 12px;
            }}
        """)

        layout = QHBoxLayout()

        # Search input
        search_label = QLabel("Search:")
        search_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name or ID...")
        self.search_input.textChanged.connect(self._on_search_changed)
        layout.addWidget(self.search_input)

        # View toggle
        layout.addStretch()

        view_label = QLabel("View:")
        view_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(view_label)

        self.grid_view_btn = QPushButton("Grid")
        self.grid_view_btn.setCheckable(True)
        self.grid_view_btn.setChecked(True)
        self.grid_view_btn.clicked.connect(lambda: self._set_view("grid"))
        layout.addWidget(self.grid_view_btn)

        self.list_view_btn = QPushButton("List")
        self.list_view_btn.setCheckable(True)
        self.list_view_btn.clicked.connect(lambda: self._set_view("list"))
        layout.addWidget(self.list_view_btn)

        controls.setLayout(layout)
        return controls

    def _load_robots(self):
        """Load robots from database"""
        self.robots = self.database_service.get_all_robots()
        self._update_display()

    def _update_display(self):
        """Update robot display"""
        # Clear existing
        for i in reversed(range(self.content_layout.count())):
            widget = self.content_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # Filter robots
        filtered_robots = [
            r for r in self.robots
            if self.filter_text.lower() in r.name.lower()
            or self.filter_text.lower() in r.id.lower()
        ]

        if self.current_view == "grid":
            self._display_grid(filtered_robots)
        else:
            self._display_list(filtered_robots)

    def _display_grid(self, robots: list):
        """Display robots in grid view"""
        columns = 4
        for i, robot in enumerate(robots):
            card = RobotCard(robot)

            # Connect signals
            card.connect_clicked.connect(self._on_connect_clicked)
            card.card_clicked.connect(self._show_robot_details)

            row = i // columns
            col = i % columns
            self.content_layout.addWidget(card, row, col)

    def _display_list(self, robots: list):
        """Display robots in table view"""
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["Name", "ID", "IP Address", "Status", "Battery", "State"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setRowCount(len(robots))

        for row, robot in enumerate(robots):
            table.setItem(row, 0, QTableWidgetItem(robot.name))
            table.setItem(row, 1, QTableWidgetItem(robot.id))
            table.setItem(row, 2, QTableWidgetItem(f"{robot.ip}:{robot.port}"))
            table.setItem(row, 3, QTableWidgetItem(robot.connection_status.value))
            table.setItem(row, 4, QTableWidgetItem(f"{robot.battery.level:.1f}%"))
            table.setItem(row, 5, QTableWidgetItem(robot.state.value))

        self.content_layout.addWidget(table)

    def _set_view(self, view: str):
        """Set view mode"""
        self.current_view = view
        self.grid_view_btn.setChecked(view == "grid")
        self.list_view_btn.setChecked(view == "list")
        self._update_display()

    def _on_search_changed(self, text: str):
        """Handle search text changed"""
        self.filter_text = text
        self._update_display()

    def _on_connect_clicked(self, robot_id: str):
        """Handle connect button clicked"""
        robot = next((r for r in self.robots if r.id == robot_id), None)
        if robot:
            if robot.connection_status == ConnectionStatus.CONNECTED:
                self.network_service.disconnect_robot(robot_id)
            else:
                self.network_service.connect_robot(robot)

    def _on_robot_connected(self, robot_id: str):
        """Handle robot connected"""
        self._load_robots()

    def _on_robot_disconnected(self, robot_id: str):
        """Handle robot disconnected"""
        self._load_robots()

    def _show_add_robot_dialog(self):
        """Show add robot dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Robot")
        dialog.setFixedWidth(400)

        layout = QFormLayout()

        name_input = QLineEdit()
        id_input = QLineEdit()
        ip_input = QLineEdit()
        port_input = QSpinBox()
        port_input.setRange(1, 65535)
        port_input.setValue(8080)

        layout.addRow("Name:", name_input)
        layout.addRow("Robot ID:", id_input)
        layout.addRow("IP Address:", ip_input)
        layout.addRow("Port:", port_input)

        buttons = QHBoxLayout()
        ok_btn = QPushButton("Add")
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
            robot = Robot(
                id=id_input.text(),
                name=name_input.text(),
                ip=ip_input.text(),
                port=port_input.value(),
            )

            self.database_service.add_robot(robot)
            self._load_robots()

    def _show_robot_details(self, robot_id: str):
        """Show robot details dialog"""
        robot = next((r for r in self.robots if r.id == robot_id), None)
        if not robot:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Robot Details - {robot.name}")
        dialog.setFixedWidth(500)

        layout = QFormLayout()

        # Display robot info
        layout.addRow("Name:", QLabel(robot.name))
        layout.addRow("ID:", QLabel(robot.id))
        layout.addRow("Model:", QLabel(robot.model))
        layout.addRow("IP:", QLabel(f"{robot.ip}:{robot.port}"))
        layout.addRow("Status:", QLabel(robot.connection_status.value))
        layout.addRow("State:", QLabel(robot.state.value))
        layout.addRow("Battery:", QLabel(f"{robot.battery.level:.1f}%"))
        layout.addRow("Position:", QLabel(f"({robot.position.x:.2f}, {robot.position.y:.2f})"))
        layout.addRow("Firmware:", QLabel(robot.firmware_version))

        # Action buttons
        buttons = QHBoxLayout()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        buttons.addWidget(close_btn)

        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addLayout(buttons)
        dialog.setLayout(main_layout)

        dialog.exec_()
