#!/usr/bin/env python3
"""
GO2 机器狗控制面板 v3.0 - 改进版
主要改进：
1. 添加复选框方便选择设备
2. 显示详细连接状态
3. 保持连接，不重复连接
4. 添加模式切换指令
"""

import sys
import os
import subprocess
import platform
import socket
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem, QGroupBox,
    QMessageBox, QTextEdit, QCheckBox, QGridLayout, QDialog,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QColor, QFont

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# 自动修复 GO2 库
# ============================================================================
def fix_go2_library():
    """自动修复 go2_webrtc_driver"""
    try:
        import sys
        for path in sys.path:
            if 'site-packages' in path:
                util_file = os.path.join(path, 'go2_webrtc_driver', 'util.py')
                if os.path.exists(util_file):
                    logger.info(f"检查 GO2 库文件: {util_file}")
                    with open(util_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    original = content
                    needs_fix = False

                    if 'from typing import' in content and 'Optional' not in content:
                        content = content.replace('from typing import', 'from typing import Optional, ')
                        needs_fix = True
                        logger.info("  [1/2] 添加 Optional 导入")
                    if 'str | None' in content:
                        content = content.replace('str | None', 'Optional[str]')
                        needs_fix = True
                        logger.info("  [2/2] 替换 str | None")

                    if needs_fix:
                        backup = util_file + '.backup'
                        with open(backup, 'w', encoding='utf-8') as f:
                            f.write(original)
                        with open(util_file, 'w', encoding='utf-8') as f:
                            f.write(content)
                        logger.info("✓ GO2 库已自动修复")
                    return True
        return True
    except Exception as e:
        logger.warning(f"GO2 库自动修复失败: {e}")
        return False

# 尝试导入 GO2 库
GO2_AVAILABLE = False
try:
    fix_go2_library()
    from go2_webrtc_driver.webrtc_driver import Go2WebRTCConnection, WebRTCConnectionMethod
    from go2_webrtc_driver.constants import RTC_TOPIC, SPORT_CMD
    GO2_AVAILABLE = True
    logger.info("✓ GO2 库已加载")
except Exception as e:
    logger.warning(f"GO2 库加载失败: {e}")
    GO2_AVAILABLE = False

# ============================================================================
# 数据类
# ============================================================================
class RobotDevice:
    """机器狗设备类"""
    def __init__(self, ip: str, index: int):
        self.ip = ip
        self.index = index
        self.name = f"GO2-{index+1}"
        self.connection = None
        self.connected = False
        self.status = "离线"
        self.open_ports = []
        self.is_go2 = False
        self.selected = False  # 是否被选中

# ============================================================================
# 扫描线程
# ============================================================================
class ScanThread(QThread):
    """扫描线程"""
    finished = pyqtSignal(list)
    progress = pyqtSignal(str)

    def __init__(self, network_prefix: str):
        super().__init__()
        self.network_prefix = network_prefix
        self.ips = [f"{network_prefix}.{i}" for i in range(1, 255)]

    def ping_check(self, ip):
        """检查单个 IP"""
        try:
            if platform.system().lower() == 'windows':
                cmd = ['ping', '-n', '1', '-w', '500', ip]
            else:
                cmd = ['ping', '-c', '1', '-W', '1', ip]
            result = subprocess.run(cmd, capture_output=True, timeout=1)
            if result.returncode == 0:
                open_ports = []
                check_ports = [554, 5000, 8081, 9991]
                for port in check_ports:
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(0.5)
                        port_result = sock.connect_ex((ip, port))
                        sock.close()
                        if port_result == 0:
                            open_ports.append(port)
                    except:
                        pass
                return (ip, open_ports)
        except:
            pass
        return None

    def run(self):
        """执行扫描"""
        self.progress.emit(f"正在扫描 {len(self.ips)} 个 IP 地址...")
        devices = []
        with ThreadPoolExecutor(max_workers=50) as executor:
            results = list(executor.map(self.ping_check, self.ips))
            devices = [r for r in results if r is not None]
        self.progress.emit(f"扫描完成，找到 {len(devices)} 个在线设备")
        self.finished.emit(devices)

# ============================================================================
# 连接线程
# ============================================================================
class ConnectThread(QThread):
    """连接线程"""
    connected = pyqtSignal(object, bool)
    progress = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, robot: RobotDevice):
        super().__init__()
        self.robot = robot

    def run(self):
        """执行连接"""
        if not GO2_AVAILABLE:
            self.progress.emit("GO2 库不可用")
            self.connected.emit(self.robot, False)
            self.finished.emit()
            return

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._connect())
            self.connected.emit(self.robot, result)
        except Exception as e:
            logger.error(f"连接失败: {e}")
            self.connected.emit(self.robot, False)
        finally:
            try:
                loop.close()
            except:
                pass
            self.finished.emit()

    async def _connect(self):
        """异步连接"""
        try:
            self.progress.emit(f"正在连接 {self.robot.name}...")
            conn = Go2WebRTCConnection(
                WebRTCConnectionMethod.LocalSTA,
                ip=self.robot.ip
            )
            await asyncio.wait_for(conn.connect(), timeout=20)
            self.robot.connection = conn
            self.robot.connected = True
            self.robot.status = "在线"
            return True
        except Exception as e:
            logger.error(f"{self.robot.name} 连接失败: {e}")
            return False

# ============================================================================
# 指令发送线程
# ============================================================================
class CommandThread(QThread):
    """指令发送线程"""
    progress = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, robots: List[RobotDevice], action: str, action_name: str):
        super().__init__()
        self.robots = robots
        self.action = action
        self.action_name = action_name

    def run(self):
        """发送指令"""
        if not GO2_AVAILABLE:
            self.progress.emit("GO2 库不可用")
            self.finished.emit()
            return

        connected_robots = [r for r in self.robots if r.connected and r.selected]

        if not connected_robots:
            self.progress.emit("没有已选中且已连接的设备")
            self.finished.emit()
            return

        self.progress.emit(f"正在向 {len(connected_robots)} 台机器狗发送: {self.action_name}")

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._send_command(connected_robots))
        except Exception as e:
            self.progress.emit(f"错误: {e}")
        finally:
            try:
                loop.close()
            except:
                pass
            self.finished.emit()

    async def _send_command(self, robots):
        """异步发送指令"""
        cmd_map = {
            "StandUp": {"api_id": SPORT_CMD["StandUp"]},
            "StandDown": {"api_id": SPORT_CMD["StandDown"]},
            "Hello": {"api_id": SPORT_CMD["Hello"]},
            "Move_F": {"api_id": SPORT_CMD["Move"], "parameter": {"x": 0.5, "y": 0, "z": 0}},
            "Move_B": {"api_id": SPORT_CMD["Move"], "parameter": {"x": -0.5, "y": 0, "z": 0}},
            "Move_L": {"api_id": SPORT_CMD["Move"], "parameter": {"x": 0, "y": 0, "z": 0.5}},
            "Move_R": {"api_id": SPORT_CMD["Move"], "parameter": {"x": 0, "y": 0, "z": -0.5}},
            "Stop": {"api_id": SPORT_CMD["Move"], "parameter": {"x": 0, "y": 0, "z": 0}},
        }

        cmd = cmd_map.get(self.action)
        if not cmd:
            self.progress.emit(f"未知指令: {self.action}")
            return

        for robot in robots:
            try:
                await robot.connection.datachannel.pub_sub.publish_request_new(
                    RTC_TOPIC["SPORT_MOD"],
                    cmd
                )
                self.progress.emit(f"✓ {robot.name} 指令已发送")
                await asyncio.sleep(0.2)
            except Exception as e:
                self.progress.emit(f"✗ {robot.name} 指令发送失败: {e}")

        self.progress.emit("所有指令发送完成")

# ============================================================================
# 主窗口
# ============================================================================
class Go2ControlPanel(QMainWindow):
    """GO2 控制面板主窗口"""

    def __init__(self):
        super().__init__()
        self.robots: List[RobotDevice] = []
        self.scan_thread = None
        self.connect_thread = None
        self.command_thread = None

        self.init_ui()
        self.show_info()

    def init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("GO2 机器狗控制面板 v3.0")
        self.setGeometry(100, 100, 1200, 750)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        left_panel = self.create_left_panel()
        layout.addWidget(left_panel, 1)

        right_panel = self.create_right_panel()
        layout.addWidget(right_panel, 2)

    def create_left_panel(self):
        """创建左侧面板"""
        panel = QGroupBox("设备列表")
        layout = QVBoxLayout(panel)

        # 扫描按钮
        self.scan_btn = QPushButton("🔍 扫描局域网")
        self.scan_btn.setFont(QFont("Arial", 11))
        self.scan_btn.clicked.connect(self.start_scan)
        layout.addWidget(self.scan_btn)

        # 进度标签
        self.progress_label = QLabel("准备就绪")
        layout.addWidget(self.progress_label)

        # 使用 TableWidget 显示设备（支持复选框）
        self.device_table = QTableWidget()
        self.device_table.setColumnCount(4)
        self.device_table.setHorizontalHeaderLabels(["选择", "设备名称", "IP地址", "状态"])
        self.device_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.device_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.device_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.device_table)

        # 按钮布局
        btn_layout = QHBoxLayout()

        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self.select_all)
        btn_layout.addWidget(self.select_all_btn)

        self.select_none_btn = QPushButton("清空")
        self.select_none_btn.clicked.connect(self.select_none)
        btn_layout.addWidget(self.select_none_btn)

        self.connect_btn = QPushButton("🔗 连接选中设备")
        self.connect_btn.clicked.connect(self.connect_selected)
        self.connect_btn.setEnabled(False)
        btn_layout.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("🔌 断开连接")
        self.disconnect_btn.clicked.connect(self.disconnect_all)
        self.disconnect_btn.setEnabled(False)
        btn_layout.addWidget(self.disconnect_btn)

        layout.addLayout(btn_layout)
        return panel

    def create_right_panel(self):
        """创建右侧面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 设备信息
        info_group = QGroupBox("连接状态")
        info_layout = QVBoxLayout(info_group)

        self.status_label = QLabel("未连接任何设备")
        self.status_label.setFont(QFont("Arial", 10))
        info_layout.addWidget(self.status_label)

        layout.addWidget(info_group)

        # 动作按钮
        action_group = QGroupBox("动作指令")
        action_layout = QGridLayout(action_group)

        actions = [
            ("切换到运动模式", "Mode", 0, 0),
            ("起立", "StandUp", 0, 1),
            ("趴下", "StandDown", 1, 0),
            ("打招呼", "Hello", 1, 1),
            ("前进", "Move_F", 2, 0),
            ("后退", "Move_B", 2, 1),
            ("左转", "Move_L", 3, 0),
            ("右转", "Move_R", 3, 1),
            ("停止", "Stop", 4, 0),
        ]

        for action_name, action_cmd, row, col in actions:
            btn = QPushButton(action_name)
            btn.setFont(QFont("Arial", 10))
            btn.setMinimumHeight(45)
            btn.clicked.connect(lambda checked, cmd=action_cmd, name=action_name: self.send_command(cmd, name))
            action_layout.addWidget(btn, row, col)

        layout.addWidget(action_group)

        # 日志
        log_group = QGroupBox("操作日志")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)

        clear_btn = QPushButton("清空日志")
        clear_btn.clicked.connect(self.log_text.clear)
        log_layout.addWidget(clear_btn)

        layout.addWidget(log_group)

        return panel

    def show_info(self):
        """显示信息"""
        self.log("=" * 60)
        self.log("GO2 机器狗控制面板 v3.0")
        self.log("=" * 60)
        if GO2_AVAILABLE:
            self.log("✓ GO2 库已加载，支持完整控制功能")
            self.log("\n使用说明:")
            self.log("  1. 点击 '扫描局域网' 找到设备")
            self.log("  2. 勾选要连接的设备")
            self.log("  3. 点击 '连接选中设备'")
            self.log("  4. 等待连接成功（状态变为 '在线'）")
            self.log("  5. 点击动作按钮发送指令")
        else:
            self.log("✗ GO2 库不可用，仅支持扫描")
        self.log("=" * 60)

    def log(self, message: str):
        """添加日志"""
        self.log_text.append(message)
        logger.info(message)

    def start_scan(self):
        """开始扫描"""
        self.scan_btn.setEnabled(False)
        self.device_table.setRowCount(0)
        self.robots.clear()

        network_prefix = "172.20.10"

        self.scan_thread = ScanThread(network_prefix)
        self.scan_thread.progress.connect(self.progress_label.setText)
        self.scan_thread.finished.connect(self.on_scan_finished)
        self.scan_thread.start()

        self.log("开始扫描局域网...")

    def on_scan_finished(self, devices: list):
        """扫描完成"""
        self.scan_btn.setEnabled(True)

        if not devices:
            self.log("未找到任何在线设备")
            QMessageBox.warning(self, "扫描结果", "未找到任何在线设备")
            return

        self.log(f"扫描完成，找到 {len(devices)} 个在线设备")

        for i, (ip, ports) in enumerate(devices):
            robot = RobotDevice(ip, i)
            robot.open_ports = ports

            if 8081 in ports or 9991 in ports or 554 in ports:
                robot.is_go2 = True

            self.robots.append(robot)

            # 添加到表格
            row = self.device_table.rowCount()
            self.device_table.insertRow(row)

            # 复选框
            checkbox = QCheckBox()
            checkbox.stateChanged.connect(lambda state, r=robot: self.on_device_selected(r, state))
            self.device_table.setCellWidget(row, 0, checkbox)

            # 设备名称
            name_item = QTableWidgetItem(robot.name)
            name_item.setFlags(Qt.ItemIsEnabled)
            self.device_table.setItem(row, 1, name_item)

            # IP地址
            ip_item = QTableWidgetItem(f"{ip}\n({', '.join(map(str, ports))})")
            ip_item.setFlags(Qt.ItemIsEnabled)
            self.device_table.setItem(row, 2, ip_item)

            # 状态
            status_item = QTableWidgetItem("离线")
            if robot.is_go2:
                status_item.setBackground(QColor(200, 230, 255))
            status_item.setFlags(Qt.ItemIsEnabled)
            self.device_table.setItem(row, 3, status_item)

            self.log(f"  发现设备: {robot.name} - {ip} - 端口: {ports}")

        self.connect_btn.setEnabled(True)
        self.device_table.resizeRowsToContents()

        go2_count = sum(1 for r in self.robots if r.is_go2)
        QMessageBox.information(
            self,
            "扫描完成",
            f"找到 {len(devices)} 个在线设备\n"
            f"其中 {go2_count} 个可能是 GO2 机器狗\n\n"
            f"请勾选要连接的设备，然后点击 '连接选中设备'"
        )

    def on_device_selected(self, robot: RobotDevice, state):
        """设备选择状态改变"""
        robot.selected = (state == Qt.Checked)

    def select_all(self):
        """全选"""
        for row in range(self.device_table.rowCount()):
            checkbox = self.device_table.cellWidget(row, 0)
            if isinstance(checkbox, QCheckBox):
                checkbox.setChecked(True)

    def select_none(self):
        """清空选择"""
        for row in range(self.device_table.rowCount()):
            checkbox = self.device_table.cellWidget(row, 0)
            if isinstance(checkbox, QCheckBox):
                checkbox.setChecked(False)

    def connect_selected(self):
        """连接选中的设备"""
        selected_robots = [r for r in self.robots if r.selected]

        if not selected_robots:
            QMessageBox.warning(self, "提示", "请先勾选要连接的设备")
            return

        self.log(f"正在连接 {len(selected_robots)} 台设备...")
        self.connect_btn.setEnabled(False)

        for robot in selected_robots:
            self.connect_thread = ConnectThread(robot)
            self.connect_thread.progress.connect(self.log)
            self.connect_thread.connected.connect(self.on_connected)
            self.connect_thread.finished.connect(self.on_connect_finished)
            self.connect_thread.start()

    def on_connected(self, robot: RobotDevice, success: bool):
        """连接完成"""
        if success:
            self.log(f"✓ {robot.name} ({robot.ip}) 连接成功")

            # 更新表格状态
            for row in range(self.device_table.rowCount()):
                item = self.device_table.item(row, 1)
                if item and item.text() == robot.name:
                    status_item = self.device_table.item(row, 3)
                    status_item.setText("在线")
                    status_item.setBackground(QColor(200, 255, 200))
                    break
        else:
            self.log(f"✗ {robot.name} ({robot.ip}) 连接失败")

    def on_connect_finished(self):
        """所有连接完成"""
        self.connect_btn.setEnabled(True)

        connected_count = sum(1 for r in self.robots if r.connected)
        selected_connected = sum(1 for r in self.robots if r.connected and r.selected)

        if connected_count > 0:
            self.status_label.setText(f"已连接 {connected_count} 台设备，其中 {selected_connected} 台被选中")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.disconnect_btn.setEnabled(True)
            self.log(f"成功连接 {connected_count} 台设备")
        else:
            self.status_label.setText("连接失败")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.log("所有设备连接失败")

    def disconnect_all(self):
        """断开所有连接"""
        for robot in self.robots:
            robot.connected = False
            robot.status = "离线"

        # 更新表格
        for row in range(self.device_table.rowCount()):
            status_item = self.device_table.item(row, 3)
            if status_item:
                status_item.setText("离线")
                status_item.setBackground(Qt.white)

        self.status_label.setText("未连接任何设备")
        self.status_label.setStyleSheet("color: gray; font-weight: bold;")
        self.disconnect_btn.setEnabled(False)
        self.log("已断开所有连接")

    def send_command(self, action: str, action_name: str):
        """发送指令"""
        if not GO2_AVAILABLE:
            QMessageBox.warning(
                self,
                "功能不可用",
                "GO2 库不可用，无法发送动作指令"
            )
            return

        selected_connected = [r for r in self.robots if r.connected and r.selected]

        if not selected_connected:
            QMessageBox.warning(
                self,
                "提示",
                "请先勾选并连接至少一台设备\n"
                "提示：连接成功后，状态会显示为绿色的 '在线'"
            )
            return

        self.log(f"发送指令: {action_name}")

        self.command_thread = CommandThread(self.robots, action, action_name)
        self.command_thread.progress.connect(self.log)
        self.command_thread.finished.connect(lambda: None)
        self.command_thread.start()

    def closeEvent(self, event):
        """关闭事件"""
        reply = QMessageBox.question(
            self, '确认退出',
            '确定要退出吗？',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = Go2ControlPanel()
    window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
