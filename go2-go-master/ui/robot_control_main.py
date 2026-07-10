# ui/robot_control_main.py
"""
Main Robot Control Interface
- Left: Robot list with status
- Center: Action panel & script editor
- Bottom: Log output
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QLineEdit, QTextEdit,
                             QListWidget, QListWidgetItem, QSplitter,
                             QGroupBox, QTabWidget, QComboBox,
                             QFrame, QMessageBox, QFileDialog,
                             QCheckBox, QScrollArea, QMenu, QAction,
                             QStatusBar, QApplication, QGridLayout,
                             QButtonGroup, QSizePolicy, QSpacerItem,
                             QProgressBar)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QFont, QColor

from services.robot_script import ScriptService, ScriptAction, RobotScript
from services.network_scanner import NetworkScanner, DiscoveredDevice
from services.go2_webrtc_controller import Go2WebRTCController
from config import COLORS


class RobotControlMain(QWidget):
    """Main robot control interface"""

    def __init__(self):
        super().__init__()

        # Initialize UI components first
        self.robot_name_input = None
        self.robot_id_input = None
        self.robot_ip_input = None
        self.robot_list = None
        self.target_robot_combo = None
        self.robot_checkboxes = {}  # robot_id -> checkbox
        self.robot_selection_widget = None
        self.status_bar = None
        self.actions_list = None
        self.actions_scroll_area = None
        self.action_buttons = {}  # Store action buttons: action_type -> button
        self.script_name_input = None
        self.script_preview = None
        self.start_recording_btn = None
        self.stop_recording_btn = None
        self.save_script_btn = None
        self.execute_script_btn = None
        self.stop_script_btn = None
        self.script_list_widget = None
        self.load_script_btn = None
        self.delete_script_btn = None
        self.refresh_scripts_btn = None
        self.load_file_btn = None
        self.export_file_btn = None
        self.log_text = None
        self.executor = None

        # Initialize services
        # 直接使用 WebRTC 控制器作为唯一核心控制器
        self.controller = Go2WebRTCController()
        self.script_service = ScriptService()

        # Network scanner (用于扫描局域网)
        self.network_scanner = NetworkScanner()
        self.is_scanning = False

        self._setup_ui()
        self._connect_signals()

        # Connect to controller signals
        self.controller.robot_connected.connect(self._on_robot_connected)
        self.controller.robot_disconnected.connect(self._on_robot_disconnected)
        self.controller.connection_error.connect(self._on_connection_error)
        self.controller.robot_state_changed.connect(self._on_robot_state_changed)

        # Connect to scanner signals
        self.network_scanner.scan_progress.connect(self._on_scan_progress)
        self.network_scanner.device_found.connect(self._on_device_found)
        self.network_scanner.scan_complete.connect(self._on_scan_complete)
        self.network_scanner.scan_error.connect(self._on_scan_error)

    def _setup_ui(self):
        """Setup UI components"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Top: Title
        title = QLabel("Unitree GO2 机器狗群控中心")
        title.setFont(QFont("Microsoft YaHei", 20, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['primary']}; padding: 10px;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Main content splitter (vertical for top/bottom resize)
        vertical_splitter = QSplitter(Qt.Vertical)

        # Horizontal splitter (for left/right resize)
        horizontal_splitter = QSplitter(Qt.Horizontal)

        # Left: Robot list
        left_panel = self._create_robot_list_panel()
        horizontal_splitter.addWidget(left_panel)

        # Right: Action & Script panel
        right_panel = self._create_action_panel()
        horizontal_splitter.addWidget(right_panel)

        horizontal_splitter.setStretchFactor(0, 1)
        horizontal_splitter.setStretchFactor(1, 3)

        vertical_splitter.addWidget(horizontal_splitter)

        # Bottom: Log
        log_panel = self._create_log_panel()
        vertical_splitter.addWidget(log_panel)

        vertical_splitter.setStretchFactor(0, 3)
        vertical_splitter.setStretchFactor(1, 1)

        main_layout.addWidget(vertical_splitter)

        # Add status bar at the bottom
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(f"""
            QStatusBar {{
                background-color: {COLORS['card']};
                border-top: 1px solid {COLORS['border']};
                color: {COLORS['text_secondary']};
                font-size: 12px;
                padding: 3px;
            }}
        """)
        main_layout.addWidget(self.status_bar)

        # Initial status message
        self.status_bar.showMessage("就绪")

        self.setLayout(main_layout)

    def _create_robot_list_panel(self) -> QWidget:
        """Create left robot list panel"""
        panel = QFrame()
        panel.setMinimumWidth(280)
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card']};
                border-radius: 8px;
                border: 1px solid {COLORS['border']};
            }}
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Title
        title = QLabel("机器人列表")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        layout.addWidget(title)

        # Network scan group
        scan_group = QGroupBox("网络扫描")
        scan_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {COLORS['primary']};
                border-radius: 5px;
                margin-top: 10px;
                padding: 5px;
                color: {COLORS['primary']};
            }}
        """)
        scan_layout = QVBoxLayout()
        scan_layout.setSpacing(8)

        # Network input
        network_input_layout = QHBoxLayout()
        network_input_layout.addWidget(QLabel("网段:"))
        self.network_input = QLineEdit()
        self.network_input.setText("192.168.71.0/24")
        self.network_input.setPlaceholderText("192.168.71.0/24")
        network_input_layout.addWidget(self.network_input)
        scan_layout.addLayout(network_input_layout)

        # Scan button
        scan_btn_layout = QHBoxLayout()
        self.scan_btn = QPushButton("扫描网络")
        self.scan_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent']};
            }}
            QPushButton:disabled {{
                background-color: {COLORS['text_secondary']};
            }}
        """)
        self.scan_btn.clicked.connect(self._start_network_scan)
        scan_btn_layout.addWidget(self.scan_btn)

        self.stop_scan_btn = QPushButton("停止")
        self.stop_scan_btn.setEnabled(False)
        self.stop_scan_btn.clicked.connect(self._stop_network_scan)
        scan_btn_layout.addWidget(self.stop_scan_btn)

        scan_layout.addLayout(scan_btn_layout)

        # Progress bar
        self.scan_progress = QProgressBar()
        self.scan_progress.setVisible(False)
        self.scan_progress.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                text-align: center;
                height: 20px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['primary']};
            }}
        """)
        scan_layout.addWidget(self.scan_progress)

        scan_group.setLayout(scan_layout)
        layout.addWidget(scan_group)

        # Discovered devices (initially hidden)
        self.discovered_devices_group = QGroupBox("发现的设备")
        self.discovered_devices_group.setVisible(False)
        discovered_layout = QVBoxLayout()

        self.discovered_list = QListWidget()
        self.discovered_list.setMaximumHeight(150)
        discovered_layout.addWidget(self.discovered_list)

        # Add selected devices button
        add_selected_btn = QPushButton("添加选中的设备")
        add_selected_btn.clicked.connect(self._add_selected_discovered_devices)
        add_selected_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px;
            }}
            QPushButton:hover {{
                background-color: #27AE60;
            }}
        """)
        discovered_layout.addWidget(add_selected_btn)

        self.discovered_devices_group.setLayout(discovered_layout)
        layout.addWidget(self.discovered_devices_group)

        # Manual add form
        form_group = QGroupBox("手动添加")
        form_layout = QVBoxLayout()
        form_layout.setSpacing(8)

        self.robot_name_input = QLineEdit()
        self.robot_name_input.setPlaceholderText("名称 (如: Robot 1)")
        form_layout.addWidget(QLabel("名称:"))
        form_layout.addWidget(self.robot_name_input)

        self.robot_id_input = QLineEdit()
        self.robot_id_input.setPlaceholderText("ID (如: robot_001)")
        form_layout.addWidget(QLabel("ID:"))
        form_layout.addWidget(self.robot_id_input)

        self.robot_ip_input = QLineEdit()
        self.robot_ip_input.setPlaceholderText("IP (如: 192.168.71.31)")
        form_layout.addWidget(QLabel("IP地址:"))
        form_layout.addWidget(self.robot_ip_input)

        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self._add_robot)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px;
            }}
            QPushButton:hover {{
                background-color: #27AE60;
            }}
        """)
        form_layout.addWidget(add_btn)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # Robot list
        list_group = QGroupBox()
        list_group.setTitle(f"已添加 ({self._get_total_count()})")
        list_group.setObjectName("robot_list_group")
        list_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #2A3A5A;
                border-radius: 5px;
                margin-top: 10px;
                padding: 5px;
                color: #00D4FF;
            }
        """)

        list_layout = QVBoxLayout()
        self.robot_list = QListWidget()
        self.robot_list.setIconSize(QSize(50, 50))
        self.robot_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.robot_list.customContextMenuRequested.connect(self._show_robot_list_context_menu)
        list_layout.addWidget(self.robot_list)

        list_group.setLayout(list_layout)
        layout.addWidget(list_group)

        panel.setLayout(layout)
        return panel

    def _create_action_panel(self) -> QWidget:
        """Create right action panel"""
        panel = QFrame()
        panel.setMinimumWidth(400)
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card']};
                border-radius: 8px;
                border: 1px solid {COLORS['border']};
            }}
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self._create_control_tab(), "动作控制")
        tabs.addTab(self._create_script_tab(), "脚本编辑")
        tabs.addTab(self._create_script_list_tab(), "脚本库")

        layout.addWidget(tabs)
        panel.setLayout(layout)
        return panel

    def _create_control_tab(self) -> QWidget:
        """Create control tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # Robot selection group
        selection_group = QGroupBox("选择目标机器狗（右键全选/清空）")
        selection_layout = QVBoxLayout()

        # Robot checkboxes scroll area (resizable)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(100)

        self.robot_selection_widget = QWidget()
        self.robot_selection_layout = QVBoxLayout()
        self.robot_selection_layout.setSpacing(8)
        self.robot_selection_layout.setContentsMargins(5, 5, 5, 5)
        self.robot_selection_widget.setLayout(self.robot_selection_layout)

        # Enable context menu for right-click
        self.robot_selection_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.robot_selection_widget.customContextMenuRequested.connect(self._show_selection_context_menu)

        scroll_area.setWidget(self.robot_selection_widget)
        selection_layout.addWidget(scroll_area)

        selection_group.setLayout(selection_layout)
        layout.addWidget(selection_group, 1)  # Give it stretch factor

        # Actions list
        actions_group = QGroupBox("内置动作")
        actions_layout = QVBoxLayout()

        # Create scrollable area for action buttons
        self.actions_scroll_area = QScrollArea()
        self.actions_scroll_area.setWidgetResizable(True)
        self.actions_scroll_area.setMinimumHeight(300)

        # Container widget for all action buttons
        self.actions_container = QWidget()
        self.actions_container_layout = QVBoxLayout()
        self.actions_container_layout.setSpacing(15)
        self.actions_container.setLayout(self.actions_container_layout)

        self.actions_scroll_area.setWidget(self.actions_container)
        actions_layout.addWidget(self.actions_scroll_area)

        # Quick control buttons (now for current selected action)
        quick_layout = QHBoxLayout()

        self.execute_btn = QPushButton("执行选中动作")
        self.execute_btn.setEnabled(False)
        self.execute_btn.clicked.connect(self._execute_current_action)
        quick_layout.addWidget(self.execute_btn)

        self.record_btn = QPushButton("录制到脚本")
        self.record_btn.setEnabled(False)
        self.record_btn.clicked.connect(self._record_current_action)
        quick_layout.addWidget(self.record_btn)

        # Info label
        self.selected_action_label = QLabel("未选择动作")
        self.selected_action_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-style: italic;")
        self.selected_action_label.setAlignment(Qt.AlignCenter)
        quick_layout.addWidget(self.selected_action_label)

        actions_layout.addLayout(quick_layout)

        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group, 2)  # Give it more stretch

        widget.setLayout(layout)
        return widget

    def _create_script_tab(self) -> QWidget:
        """Create script editor tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # Script info
        info_layout = QHBoxLayout()

        info_layout.addWidget(QLabel("脚本名称:"))
        self.script_name_input = QLineEdit()
        self.script_name_input.setPlaceholderText("我的动作脚本")
        info_layout.addWidget(self.script_name_input)

        layout.addLayout(info_layout)

        # Recording controls
        record_controls = QHBoxLayout()

        self.start_recording_btn = QPushButton("开始录制")
        self.start_recording_btn.clicked.connect(self._start_recording)
        record_controls.addWidget(self.start_recording_btn)

        self.stop_recording_btn = QPushButton("停止录制")
        self.stop_recording_btn.setEnabled(False)
        self.stop_recording_btn.clicked.connect(self._stop_recording)
        record_controls.addWidget(self.stop_recording_btn)

        self.save_script_btn = QPushButton("保存脚本")
        self.save_script_btn.clicked.connect(self._save_current_script)
        record_controls.addWidget(self.save_script_btn)

        layout.addLayout(record_controls)

        # Script preview
        preview_group = QGroupBox("脚本预览")
        preview_layout = QVBoxLayout()

        self.script_preview = QTextEdit()
        self.script_preview.setReadOnly(True)
        self.script_preview.setMaximumHeight(200)
        preview_layout.addWidget(self.script_preview)

        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        # Execution controls
        exec_layout = QHBoxLayout()

        self.execute_script_btn = QPushButton("执行脚本")
        self.execute_script_btn.clicked.connect(self._execute_current_script)
        exec_layout.addWidget(self.execute_script_btn)

        self.stop_script_btn = QPushButton("停止执行")
        self.stop_script_btn.setEnabled(False)
        self.stop_script_btn.clicked.connect(self._stop_script_execution)
        exec_layout.addWidget(self.stop_script_btn)

        layout.addLayout(exec_layout)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_script_list_tab(self) -> QWidget:
        """Create script library tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # Script list
        list_group = QGroupBox("已保存的脚本")
        list_layout = QVBoxLayout()

        self.script_list_widget = QListWidget()
        self.script_list_widget.itemDoubleClicked.connect(self._load_selected_script)
        list_layout.addWidget(self.script_list_widget)

        # Buttons
        btn_layout = QHBoxLayout()

        self.load_script_btn = QPushButton("加载脚本")
        self.load_script_btn.clicked.connect(self._load_selected_script)
        btn_layout.addWidget(self.load_script_btn)

        self.delete_script_btn = QPushButton("删除脚本")
        self.delete_script_btn.clicked.connect(self._delete_selected_script)
        btn_layout.addWidget(self.delete_script_btn)

        self.refresh_scripts_btn = QPushButton("刷新列表")
        self.refresh_scripts_btn.clicked.connect(self._refresh_script_list)
        btn_layout.addWidget(self.refresh_scripts_btn)

        list_layout.addLayout(btn_layout)

        list_group.setLayout(list_layout)
        layout.addWidget(list_group)

        # Load script file
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("从文件加载:"))

        self.load_file_btn = QPushButton("选择文件")
        self.load_file_btn.clicked.connect(self._load_script_from_file)
        file_layout.addWidget(self.load_file_btn)

        file_layout.addStretch()

        self.export_file_btn = QPushButton("导出脚本")
        self.export_file_btn.clicked.connect(self._export_script_to_file)
        file_layout.addWidget(self.export_file_btn)

        layout.addLayout(file_layout)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_log_panel(self) -> QFrame:
        """Create log panel"""
        panel = QFrame()
        panel.setMinimumHeight(150)
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card']};
                border-radius: 8px;
                border: 1px solid {COLORS['border']};
            }}
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        header = QHBoxLayout()
        header.addWidget(QLabel("执行日志"))
        header.addStretch()

        clear_btn = QPushButton("清空")
        clear_btn.setMaximumWidth(60)
        header.addWidget(clear_btn)

        layout.addLayout(header)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        # Connect clear button
        clear_btn.clicked.connect(self.log_text.clear)

        panel.setLayout(layout)
        return panel

    def _connect_signals(self):
        """Connect signals"""
        self._load_builtin_actions()
        self._refresh_script_list()

    # ========== Robot Management ==========

    def _add_robot(self):
        """Add robot"""
        name = self.robot_name_input.text().strip()
        robot_id = self.robot_id_input.text().strip()
        ip = self.robot_ip_input.text().strip()

        if not name or not robot_id or not ip:
            QMessageBox.warning(self, "输入错误", "请填写所有字段")
            return

        # 使用 WebRTC 默认端口 9991
        success = self.controller.add_robot(robot_id, name, ip, 9991)

        if success:
            self._log(f"✓ 添加机器人: {name} ({robot_id}) @ {ip}")
            self._update_robot_list()
            self._update_target_robot_combo()
            self.robot_name_input.clear()
            self.robot_id_input.clear()
            self.robot_ip_input.clear()
        else:
            QMessageBox.critical(self, "错误", "添加机器人失败")

    def _update_robot_list(self):
        """Update robot list display"""
        self.robot_list.clear()

        robots = self.controller.get_all_robots()
        for robot in robots:
            is_connected = robot.state.value == "connected"
            status_icon = "🟢" if is_connected else "🔴"
            battery = f"{robot.battery_level:.0f}%" if hasattr(robot, 'battery_level') else "0%"
            state = robot.state.value.title() if hasattr(robot, 'state') else "Unknown"

            item = QListWidgetItem(f"{status_icon} {robot.name}\nID: {robot.id}\n电量: {battery} | 状态: {state}")
            item.setData(Qt.UserRole, robot.id)
            self.robot_list.addItem(item)

        # Update group title
        connected = self._get_connected_count()
        for child in self.findChildren(QGroupBox):
            if child.objectName() == "robot_list_group":
                child.setTitle(f"已连接 ({connected}/{len(robots)})")

        # Update robot selection checkboxes
        self._update_robot_selection()

    def _get_connected_count(self) -> int:
        """Get connected robot count"""
        robots = self.controller.get_all_robots()
        return sum(1 for r in robots if hasattr(r, 'state') and r.state.value == "connected")

    def _update_robot_selection(self):
        """Update robot selection checkboxes with detailed status"""
        if not self.robot_selection_widget:
            return

        # Clear existing checkboxes
        for i in reversed(range(self.robot_selection_layout.count())):
            widget = self.robot_selection_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        self.robot_checkboxes.clear()

        # Add checkboxes for each robot
        robots = self.controller.get_all_robots()
        if not robots:
            no_robot_label = QLabel("暂无机器人，请先添加")
            no_robot_label.setStyleSheet("color: #A0AEC0; font-style: italic; padding: 10px;")
            no_robot_label.setAlignment(Qt.AlignCenter)
            self.robot_selection_layout.addWidget(no_robot_label)
            self._update_selected_count()
            return

        for robot in robots:
            # Create robot card with detailed info
            robot_card = QFrame()
            robot_card.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['card_hover']};
                    border-radius: 6px;
                    border: 1px solid {COLORS['border']};
                    padding: 5px;
                }}
                QFrame:hover {{
                    background-color: {COLORS['background']};
                    border: 1px solid {COLORS['primary']};
                }}
            """)

            card_layout = QVBoxLayout()
            card_layout.setSpacing(3)
            card_layout.setContentsMargins(8, 5, 8, 5)

            # Top row: checkbox + name + status
            top_row = QHBoxLayout()

            checkbox = QCheckBox()
            checkbox.setText(f"{robot.name}")
            checkbox.setStyleSheet("font-weight: bold; font-size: 13px;")
            is_connected = hasattr(robot, 'state') and robot.state.value == "connected"
            checkbox.setChecked(is_connected)
            checkbox.stateChanged.connect(self._update_selected_count)

            # Store checkbox by robot_id
            self.robot_checkboxes[robot.id] = checkbox

            top_row.addWidget(checkbox)
            top_row.addStretch()

            # Connection status
            status_label = QLabel("🟢 已连接" if is_connected else "🔴 未连接")
            status_label.setStyleSheet(f"""
                color: {COLORS['success'] if is_connected else COLORS['error']};
                font-size: 11px;
                font-weight: bold;
            """)
            top_row.addWidget(status_label)

            card_layout.addLayout(top_row)

            # Bottom row: details (ID, battery, state, IP)
            details_row = QHBoxLayout()
            details_row.setSpacing(15)

            # ID
            id_label = QLabel(f"ID: {robot.id}")
            id_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
            details_row.addWidget(id_label)

            # Battery
            battery_level = robot.battery_level if hasattr(robot, 'battery_level') else 0
            battery_color = COLORS['success'] if battery_level > 50 else COLORS['warning'] if battery_level > 20 else COLORS['error']
            battery_label = QLabel(f"🔋 {battery_level:.0f}%")
            battery_label.setStyleSheet(f"color: {battery_color}; font-size: 11px; font-weight: bold;")
            details_row.addWidget(battery_label)

            # State
            state_text = robot.state.value.title() if hasattr(robot, 'state') and robot.state else "Unknown"
            state_label = QLabel(f"状态: {state_text}")
            state_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
            details_row.addWidget(state_label)

            # IP
            if hasattr(robot, 'ip') and robot.ip:
                ip_label = QLabel(f"IP: {robot.ip}")
                ip_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
                details_row.addWidget(ip_label)

            details_row.addStretch()
            card_layout.addLayout(details_row)

            robot_card.setLayout(card_layout)
            self.robot_selection_layout.addWidget(robot_card)

        # Add stretch to push everything to top
        self.robot_selection_layout.addStretch()

        self._update_selected_count()

    def _update_target_robot_combo(self):
        """This method is deprecated - using checkboxes instead"""
        pass

    def _select_all_robots(self):
        """Select all robots"""
        for checkbox in self.robot_checkboxes.values():
            checkbox.setChecked(True)
        self._update_selected_count()

    def _clear_robot_selection(self):
        """Clear robot selection"""
        for checkbox in self.robot_checkboxes.values():
            checkbox.setChecked(False)
        self._update_selected_count()

    def _get_selected_robots(self) -> list:
        """Get list of selected robot IDs"""
        selected = []
        for robot_id, checkbox in self.robot_checkboxes.items():
            if checkbox.isChecked():
                selected.append(robot_id)
        return selected

    def _update_selected_count(self):
        """Update selected robots count in status bar"""
        if self.status_bar:
            count = len(self._get_selected_robots())
            total = len(self.robot_checkboxes)
            self.status_bar.showMessage(f"已选择 {count} 台机器狗 (共 {total} 台)")

    def _show_selection_context_menu(self, pos):
        """Show context menu for robot selection"""
        menu = QMenu(self)

        select_all_action = QAction("全选", self)
        select_all_action.triggered.connect(self._select_all_robots)
        menu.addAction(select_all_action)

        clear_action = QAction("清空选择", self)
        clear_action.triggered.connect(self._clear_robot_selection)
        menu.addAction(clear_action)

        # Show menu at cursor position
        menu.exec_(self.robot_selection_widget.mapToGlobal(pos))

    # ========== Action Control ==========

    def _load_builtin_actions(self):
        """Load built-in actions as icon buttons"""
        actions_dict = self.script_service.get_builtin_actions()

        # Clear existing buttons
        for i in reversed(range(self.actions_container_layout.count())):
            widget = self.actions_container_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        self.action_buttons.clear()

        # Create action buttons for each category
        for category, actions in actions_dict.items():
            # Create category group
            category_group = QGroupBox(category)
            category_group.setStyleSheet(f"""
                QGroupBox {{
                    font-weight: bold;
                    font-size: 14px;
                    color: {COLORS['primary']};
                    border: 2px solid {COLORS['primary']};
                    border-radius: 8px;
                    margin-top: 10px;
                    padding: 10px;
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    padding: 5px 10px;
                    background-color: {COLORS['card']};
                }}
            """)

            category_layout = QGridLayout()
            category_layout.setSpacing(10)
            category_layout.setHorizontalSpacing(10)

            # Create action buttons in grid
            cols = 4  # 4 buttons per row
            for idx, action in enumerate(actions):
                action_button = self._create_action_button(action)
                self.action_buttons[action['type']] = {
                    'button': action_button,
                    'data': action
                }

                row = idx // cols
                col = idx % cols
                category_layout.addWidget(action_button, row, col)

            category_layout.addItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Expanding), category_layout.rowCount(), 0)
            category_group.setLayout(category_layout)

            self.actions_container_layout.addWidget(category_group)

        # Add stretch at the end
        self.actions_container_layout.addStretch()

    def _create_action_button(self, action_data):
        """Create an action button with icon and name"""
        button = QPushButton()
        button.setCheckable(True)
        button.setFixedSize(130, 100)

        # Get duration and description
        duration = action_data.get('duration', 0)
        desc = action_data.get('desc', '')

        # Button layout with icon and text
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['card']};
                border: 2px solid {COLORS['border']};
                border-radius: 10px;
                padding: 8px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {COLORS['card_hover']};
                border: 2px solid {COLORS['primary']};
            }}
            QPushButton:checked {{
                background-color: {COLORS['primary']};
                border: 2px solid {COLORS['primary']};
                color: white;
            }}
            QPushButton:checked:hover {{
                background-color: {COLORS['accent']};
            }}
        """)

        # Create button content layout
        layout = QVBoxLayout()
        layout.setSpacing(5)

        # Icon (large emoji)
        icon_label = QLabel(action_data['icon'])
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 32px;")
        layout.addWidget(icon_label)

        # Action name
        name_label = QLabel(action_data['name'])
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet("font-size: 13px; font-weight: bold;")
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

        # Duration
        if duration > 0:
            duration_label = QLabel(f"{duration}s")
            duration_label.setAlignment(Qt.AlignCenter)
            duration_label.setStyleSheet(f"font-size: 11px; color: {COLORS['text_secondary']};")
            layout.addWidget(duration_label)

        layout.addStretch()

        button.setLayout(layout)

        # Connect click event
        button.clicked.connect(lambda: self._on_action_clicked(action_data))

        return button

    def _on_action_clicked(self, action_data):
        """Handle action button click"""
        # Uncheck all other buttons
        for btn_info in self.action_buttons.values():
            if btn_info['data']['type'] != action_data['type']:
                btn_info['button'].setChecked(False)

        # Enable execute and record buttons
        self.execute_btn.setEnabled(True)
        self.record_btn.setEnabled(True)

        # Update selected action label
        duration = action_data.get('duration', 0)
        desc = action_data.get('desc', '')
        label_text = f"{action_data['icon']} {action_data['name']}"
        if duration > 0:
            label_text += f" ({duration}秒)"
        self.selected_action_label.setText(label_text)
        self.selected_action_label.setStyleSheet(f"""
            color: {COLORS['primary']};
            font-weight: bold;
            font-size: 13px;
        """)

    def _get_current_action(self):
        """Get currently selected action data"""
        for btn_info in self.action_buttons.values():
            if btn_info['button'].isChecked():
                return btn_info['data']
        return None

    def _execute_current_action(self):
        """Execute currently selected action"""
        action_data = self._get_current_action()
        if not action_data:
            return

        selected_robot_ids = self._get_selected_robots()
        if not selected_robot_ids:
            QMessageBox.warning(self, "未选择", "请先选择目标机器狗")
            return

        action_type = action_data['type']
        action_name = action_data['name']

        # Execute action on all selected robots
        success_count = 0
        failed_robots = []

        for robot_id in selected_robot_ids:
            robot = self.controller.get_robot(robot_id)
            if robot and hasattr(robot, 'state') and robot.state.value == "connected":
                try:
                    self.controller.send_command(robot_id, action_type)
                    self._log(f"✓ 执行动作: {action_name} -> {robot.name} ({robot_id})")
                    success_count += 1
                except Exception as e:
                    failed_robots.append(f"{robot.name} ({robot_id}): {str(e)}")
            else:
                failed_robots.append(f"{robot_id}: 未连接")

        # Log summary
        if success_count > 0:
            self._log(f"动作执行完成: 成功 {success_count} 台", update_status=True)

        if failed_robots:
            self._log(f"执行失败 {len(failed_robots)} 台:")
            for fail in failed_robots:
                self._log(f"  ✗ {fail}")

    def _record_current_action(self):
        """Record currently selected action to script"""
        if not self.script_service._is_recording:
            QMessageBox.warning(self, "未录制", "请先开始录制脚本")
            return

        action_data = self._get_current_action()
        if not action_data:
            return

        selected_robot_ids = self._get_selected_robots()
        if not selected_robot_ids:
            QMessageBox.warning(self, "未选择", "请先选择目标机器狗")
            return

        action_type = action_data['type']
        action_name = action_data['name']
        duration = self.script_service.get_action_duration(action_type)

        # Record action for each selected robot
        for robot_id in selected_robot_ids:
            self.script_service.record_action(robot_id, action_type, params={}, duration=duration)

        robot_names = [self.controller.get_robot(rid).name if self.controller.get_robot(rid) else rid
                       for rid in selected_robot_ids]
        self._log(f"录制动作: {action_name} -> {', '.join(robot_names)}", update_status=True)

        self._update_script_preview()

    # ========== Script Management ==========

    def _start_recording(self):
        """Start script recording"""
        name = self.script_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "输入错误", "请输入脚本名称")
            return

        self.script_service.start_recording(name)
        self.start_recording_btn.setEnabled(False)
        self.stop_recording_btn.setEnabled(True)

        self._log(f"开始录制脚本: {name}")
        self._update_script_preview()

    def _stop_recording(self):
        """Stop script recording"""
        script = self.script_service.stop_recording()

        self.start_recording_btn.setEnabled(True)
        self.stop_recording_btn.setEnabled(False)

        if script:
            self._log(f"停止录制: {script.name}, 共 {len(script.actions)} 个动作")
            self._refresh_script_list()

    def _save_current_script(self):
        """Save current script"""
        if not self.script_service.current_script:
            QMessageBox.warning(self, "无脚本", "没有正在编辑的脚本")
            return

        self.script_service.save_script(self.script_service.current_script)
        self._log(f"保存脚本: {self.script_service.current_script.name}")
        self._refresh_script_list()

    def _update_script_preview(self):
        """Update script preview"""
        if not self.script_service.current_script:
            self.script_preview.setText("无脚本")
            return

        script = self.script_service.current_script
        text = f"脚本: {script.name}\n"
        text += f"动作数量: {len(script.actions)}\n\n"

        for i, action in enumerate(script.actions, 1):
            text += f"{i}. [{action.timestamp/1000:.2f}s] {action.robot_id} - {action.action_type}\n"

        self.script_preview.setText(text)

    def _execute_current_script(self):
        """Execute current script"""
        if not self.script_service.current_script:
            QMessageBox.warning(self, "无脚本", "请先创建或加载脚本")
            return

        self._execute_script(self.script_service.current_script)

    def _execute_script(self, script):
        """Execute a script"""
        self.execute_script_btn.setEnabled(False)
        self.stop_script_btn.setEnabled(True)

        self._log("="*60)
        self._log(f"开始执行脚本: {script.name}")

        self.executor = self.script_service.execute_script(script, self.controller, self)

    def _stop_script_execution(self):
        """Stop script execution"""
        if self.executor and self.executor.isRunning():
            self.executor.stop()
            self._log("正在停止脚本...")

    def _load_selected_script(self):
        """Load selected script"""
        current_item = self.script_list_widget.currentItem()
        if not current_item:
            return

        script_name = current_item.text()
        script = self.script_service.load_script(script_name)

        if script:
            self.script_service.current_script = script
            self.script_name_input.setText(script.name)
            self._update_script_preview()
            self._log(f"加载脚本: {script_name}")

    def _delete_selected_script(self):
        """Delete selected script"""
        current_item = self.script_list_widget.currentItem()
        if not current_item:
            return

        script_name = current_item.text()

        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除脚本 '{script_name}' 吗?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.script_service.delete_script(script_name)
            self._refresh_script_list()
            self._log(f"删除脚本: {script_name}")

    def _refresh_script_list(self):
        """Refresh script list"""
        self.script_list_widget.clear()

        scripts = self.script_service.get_all_scripts()
        for script in scripts:
            self.script_list_widget.addItem(script.name)

    def _load_script_from_file(self):
        """Load script from file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "加载脚本", "", "JSON Files (*.json)"
        )

        if file_path:
            # Load and add to library
            try:
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    script = RobotScript.from_dict(data)

                # Save to library
                self.script_service.save_script(script)
                self._refresh_script_list()
                self._log(f"从文件加载脚本: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载脚本失败: {e}")

    def _export_script_to_file(self):
        """Export script to file"""
        if not self.script_service.current_script:
            QMessageBox.warning(self, "无脚本", "请先创建或加载脚本")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出脚本", f"{self.script_service.current_script.name}.json",
            "JSON Files (*.json)"
        )

        if file_path:
            try:
                import json
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.script_service.current_script.to_dict(), f, indent=2, ensure_ascii=False)

                self._log(f"导出脚本到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出脚本失败: {e}")

    # ========== Log ==========

    def _log(self, message, update_status=False):
        """Add log message

        Args:
            message: Log message
            update_status: If True, also update status bar with this message
        """
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

        # Update status bar for important messages
        if update_status and self.status_bar:
            # Keep selection count if message is about selection
            if "已选择" in message or "选择" in message:
                self.status_bar.showMessage(message)
            else:
                # Show message briefly, then restore selection count
                self.status_bar.showMessage(message, 3000)
                QTimer.singleShot(3000, self._update_selected_count)

    # ========== Signal Handlers ==========

    def _on_robot_connected(self, robot_id):
        """Handle robot connected"""
        self._log(f"✓ 机器人已连接: {robot_id}")
        self._update_robot_list()

    def _on_robot_disconnected(self, robot_id):
        """Handle robot disconnected"""
        self._log(f"✗ 机器人已断开: {robot_id}")
        self._update_robot_list()

    def _on_connection_error(self, robot_id, error_msg):
        """Handle connection error"""
        self._log(f"✗ 连接错误 {robot_id}: {error_msg}")

    def _on_robot_state_changed(self, robot_id, state):
        """Handle robot state changed"""
        pass  # Can update UI here

    def _on_log_message(self, message):
        """Handle log from executor"""
        self._log(message)

    def _on_action_started(self, robot_id, action, timestamp):
        """Handle action started"""
        pass

    def _on_action_completed(self, robot_id, action):
        """Handle action completed"""
        pass

    def _on_action_failed(self, robot_id, action, error):
        """Handle action failed"""
        self._log(f"✗ 动作失败 {robot_id}.{action}: {error}")

    def _on_script_finished(self):
        """Handle script finished"""
        self.execute_script_btn.setEnabled(True)
        self.stop_script_btn.setEnabled(False)

    def _on_script_stopped(self):
        """Handle script stopped"""
        self.execute_script_btn.setEnabled(True)
        self.stop_script_btn.setEnabled(False)

    # ========== Network Scanning ==========

    def _start_network_scan(self):
        """开始网络扫描"""
        if self.is_scanning:
            return

        network = self.network_input.text().strip()
        if not network:
            QMessageBox.warning(self, "输入错误", "请输入网段地址")
            return

        self.is_scanning = True
        self.scan_btn.setEnabled(False)
        self.stop_scan_btn.setEnabled(True)
        self.scan_progress.setVisible(True)
        self.scan_progress.setValue(0)
        self.discovered_list.clear()
        self.discovered_devices_group.setVisible(False)

        self._log(f"开始扫描网络: {network}")
        self.status_bar.showMessage("正在扫描网络...")

        # 在后台线程执行扫描
        import threading
        def scan_thread():
            devices = self.network_scanner.scan_network(network)

        thread = threading.Thread(target=scan_thread, daemon=True)
        thread.start()

    def _stop_network_scan(self):
        """停止网络扫描"""
        if self.is_scanning:
            self.network_scanner.stop_scan()
            self._log("正在停止扫描...")

    def _on_scan_progress(self, current, total):
        """扫描进度更新"""
        percent = int(current / total * 100)
        self.scan_progress.setValue(percent)
        self.status_bar.showMessage(f"扫描进度: {current}/{total} ({percent}%)")

    def _on_device_found(self, device: DiscoveredDevice):
        """发现设备"""
        # 显示发现的设备列表
        self.discovered_devices_group.setVisible(True)

        # 添加到列表
        if device.is_go2:
            ports_str = ",".join(map(str, device.open_ports))
            item_text = f"[GO2] {device.ip} - 端口: {ports_str}"
        else:
            item_text = f"{device.ip} - 端口: {device.open_ports}"

        self.discovered_list.addItem(item_text)
        self._log(f"发现设备: {device}")

    def _on_scan_complete(self, devices: list):
        """扫描完成"""
        self.is_scanning = False
        self.scan_btn.setEnabled(True)
        self.stop_scan_btn.setEnabled(False)
        self.scan_progress.setValue(100)

        go2_count = sum(1 for d in devices if d.is_go2)
        self._log(f"扫描完成: 发现 {len(devices)} 台设备，其中 {go2_count} 台 GO2 设备")
        self.status_bar.showMessage(f"扫描完成: 发现 {go2_count} 台 GO2 设备", 5000)

        # 3秒后隐藏进度条
        QTimer.singleShot(3000, lambda: self.scan_progress.setVisible(False))

    def _on_scan_error(self, error_msg: str):
        """扫描错误"""
        self.is_scanning = False
        self.scan_btn.setEnabled(True)
        self.stop_scan_btn.setEnabled(False)
        self.scan_progress.setVisible(False)

        self._log(f"扫描失败: {error_msg}")
        QMessageBox.critical(self, "扫描失败", error_msg)

    def _add_selected_discovered_devices(self):
        """添加选中的发现设备"""
        selected_items = self.discovered_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "未选择", "请先选择要添加的设备")
            return

        count = 0
        for item in selected_items:
            # 从文本中解析 IP
            text = item.text()
            ip = text.split()[1] if "[" in text else text.split()[0]

            # 生成自动 ID 和名称
            robot_id = f"go2_{ip.replace('.', '_')}"
            name = f"GO2 {ip.split('.')[-1]}"

            # 添加到控制器
            if self.controller.add_robot(robot_id, name, ip, 9991):
                self._log(f"添加设备: {name} @ {ip}")
                count += 1

        if count > 0:
            self._update_robot_list()
            QMessageBox.information(self, "添加成功", f"已添加 {count} 台设备")

    def _get_total_count(self) -> int:
        """获取总机器人数"""
        return len(self.controller.get_all_robots())

    def _show_robot_list_context_menu(self, pos):
        """显示机器人列表右键菜单"""
        item = self.robot_list.itemAt(pos)
        if not item:
            return

        robot_id = item.data(Qt.UserRole)

        menu = QMenu(self)

        # 连接/断开
        robot = self.controller.get_robot(robot_id)
        if robot:
            if hasattr(robot, 'state') and robot.state.value == "connected":
                disconnect_action = QAction("断开连接", self)
                disconnect_action.triggered.connect(lambda: self._disconnect_robot(robot_id))
                menu.addAction(disconnect_action)
            else:
                connect_action = QAction("连接", self)
                connect_action.triggered.connect(lambda: self._connect_robot(robot_id))
                menu.addAction(connect_action)

        # 删除
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self._delete_robot(robot_id))
        menu.addAction(delete_action)

        menu.exec_(self.robot_list.mapToGlobal(pos))

    def _connect_robot(self, robot_id: str):
        """连接机器人（使用 WebRTC）"""
        robot = self.controller.get_robot(robot_id)
        if robot:
            self._log(f"正在连接 {robot.name}...")
            self.controller.connect_robot(robot_id)

    def _disconnect_robot(self, robot_id: str):
        """断开机器人连接"""
        self._log(f"断开连接: {robot_id}")
        self.controller.disconnect_robot(robot_id)

    def _delete_robot(self, robot_id: str):
        """删除机器人"""
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除机器人 '{robot_id}' 吗?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.controller.remove_robot(robot_id)
            self._log(f"删除机器人: {robot_id}")
            self._update_robot_list()
            QMessageBox.information(self, "删除成功", f"已删除机器人: {robot_id}")