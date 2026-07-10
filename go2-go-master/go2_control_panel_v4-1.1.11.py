#!/usr/bin/env python3
"""
GO2 机器狗控制面板 v4.0 - 面向1.1.11
增加舞蹈序列中并行动作功能
增加舞蹈序列中选择执行的狗的功能
修复部分动作无法执行的bug
修复1.1.11版本的狗无法连接的bug
增加休止动作更新一些动作
问题：
无法实现切换步态
有时候舞蹈序列中跳动作（不能写太多一块执行，写一个执行一下

"""

import sys
import os
import subprocess
import platform
import socket
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem, QGroupBox,
    QMessageBox, QTextEdit, QCheckBox, QGridLayout, QDialog,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QInputDialog, QComboBox, QSpinBox, QDoubleSpinBox, QSplitter,
    QTabWidget, QScrollArea, QFrame, QLineEdit, QAbstractItemView
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer, QSize
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import QFileDialog

import logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ============================================================================
# 导入 GO2 库 (unitree_webrtc_connect 2.x，支持固件 1.1.11)
# ============================================================================
GO2_AVAILABLE = False
try:
    from unitree_webrtc_connect import UnitreeWebRTCConnection, WebRTCConnectionMethod, RTC_TOPIC, SPORT_CMD
    GO2_AVAILABLE = True
    logger.info("✓ GO2 库已加载 (unitree_webrtc_connect)")
except Exception as e:
    logger.warning(f"GO2 库加载失败: {e}")
    GO2_AVAILABLE = False

# ============================================================================
# 完整的 GO2 Air 动作列表
# ============================================================================
GO2_ACTIONS = {
    # === 基础动作 ===
    "StandUp": {"name": "站立", "category": "基础", "duration": 2},
    "StandDown": {"name": "蹲下", "category": "基础", "duration": 2},
    "RecoveryStand": {"name": "恢复站立", "category": "基础", "duration": 2},
    "BalanceStand": {"name": "平衡站立", "category": "基础", "duration": 2},
    "StopMove": {"name": "停止", "category": "基础", "duration": 1},
    "Damp": {"name": "急停(阻尼)", "category": "基础", "duration": 1},
    "Rest": {"name": "休止", "category": "基础", "duration": 2},

    # === 运动动作 (需要 normal 模式才能生效) ===
    "Move_Forward": {"name": "前进", "category": "运动", "duration": 2,
                      "params": {"x": 0.5, "y": 0.0, "z": 0.0}, "mode": "normal"},
    "Move_Backward": {"name": "后退", "category": "运动", "duration": 2,
                       "params": {"x": -0.5, "y": 0.0, "z": 0.0}, "mode": "normal"},
    "Move_Left": {"name": "左平移", "category": "运动", "duration": 2,
                  "params": {"x": 0.0, "y": 0.5, "z": 0.0}, "mode": "normal"},
    "Move_Right": {"name": "右平移", "category": "运动", "duration": 2,
                   "params": {"x": 0.0, "y": -0.5, "z": 0.0}, "mode": "normal"},
    "Turn_Left": {"name": "左转", "category": "运动", "duration": 1.5,
                  "params": {"x": 0.0, "y": 0.0, "z": 0.5}, "mode": "normal"},
    "Turn_Right": {"name": "右转", "category": "运动", "duration": 1.5,
                   "params": {"x": 0.0, "y": 0.0, "z": -0.5}, "mode": "normal"},

    # === 舞蹈动作 ===
    "Dance1": {"name": "舞蹈1", "category": "舞蹈", "duration": 8},
    "Dance2": {"name": "舞蹈2", "category": "舞蹈", "duration": 10},
    "WiggleHips": {"name": "扭屁股", "category": "舞蹈", "duration": 5},
    "Content": {"name": "开心", "category": "舞蹈", "duration": 4},
    "FingerHeart": {"name": "比心", "category": "舞蹈", "duration": 4},

    # === 特技动作 ===
    "FrontJump": {"name": "前跳", "category": "特技", "duration": 3},
    "FrontPounce": {"name": "扑人", "category": "特技", "duration": 3},
    "Stretch": {"name": "伸懒腰", "category": "特技", "duration": 4},
    "Sit": {"name": "坐下", "category": "特技", "duration": 3},
    "RiseSit": {"name": "坐起", "category": "特技", "duration": 2},
    "FrontFlip": {"name": "前空翻", "category": "特技", "duration": 5},
    "BackFlip": {"name": "后空翻", "category": "特技", "duration": 5},
    "LeftFlip": {"name": "左空翻", "category": "特技", "duration": 5},
    "Handstand": {"name": "倒立", "category": "特技", "duration": 5},
    "Bound": {"name": "并腿跑", "category": "特技", "duration": 4},

    # === 交互动作 ===
    "Hello": {"name": "打招呼", "category": "交互", "duration": 3},
    "Pose": {"name": "摆姿势", "category": "交互", "duration": 3},
    "Scrape": {"name": "拜年作揖", "category": "交互", "duration": 3},

    # === 步态动作 (需要通过 motion_switcher 切换) ===
    "FreeWalk": {"name": "灵动模式", "category": "步态", "duration": 3, "mode": "advanced"},
    "ContinuousGait": {"name": "连续步态", "category": "步态", "duration": 4, "mode": "advanced"},
    "EconomicGait": {"name": "续航模式", "category": "步态", "duration": 3, "mode": "advanced"},
    "MoonWalk": {"name": "太空步", "category": "步态", "duration": 5, "mode": "advanced"},
    "CrossStep": {"name": "交叉步", "category": "步态", "duration": 4, "mode": "advanced"},
    "NormalMode": {"name": "恢复常规(可Move)", "category": "步态", "duration": 2, "mode": "normal"},
}

# 按分类组织动作
ACTION_CATEGORIES = {
    "基础": ["StandUp", "StandDown", "RecoveryStand", "BalanceStand", "StopMove", "Damp", "Rest"],
    "运动": ["Move_Forward", "Move_Backward", "Move_Left", "Move_Right",
             "Turn_Left", "Turn_Right"],
    "舞蹈": ["Dance1", "Dance2", "WiggleHips", "Content", "FingerHeart"],
    "特技": ["FrontJump", "FrontPounce", "Stretch", "Sit", "RiseSit",
             "FrontFlip", "BackFlip", "LeftFlip", "Handstand", "Bound"],
    "交互": ["Hello", "Pose", "Scrape"],
    "步态": ["FreeWalk", "ContinuousGait", "EconomicGait", "MoonWalk", "CrossStep", "NormalMode"],
}

# ============================================================================
# 预设3分钟舞蹈序列
# ============================================================================
PRESET_DANCE_3MIN = [
    # 开场 (0-30秒)
    {"action": "StandUp", "duration": 2},
    {"action": "Hello", "duration": 3},
    {"action": "Dance1", "duration": 10},
    {"action": "Hello", "duration": 3},
    {"action": "Stretch", "duration": 4},
    {"action": "StandDown", "duration": 2},
    {"action": "StandUp", "duration": 2},

    # 快节奏部分 (30-60秒)
    {"action": "FrontJump", "duration": 3},
    {"action": "Move_Forward", "duration": 2},
    {"action": "FrontJump", "duration": 3},
    {"action": "Move_Backward", "duration": 2},
    {"action": "Turn_Left", "duration": 2},
    {"action": "Turn_Right", "duration": 2},
    {"action": "Dance2", "duration": 10},

    # 互动部分 (60-90秒)
    {"action": "Content", "duration": 4},
    {"action": "Pose", "duration": 3},
    {"action": "FingerHeart", "duration": 4},
    {"action": "Scrape", "duration": 3},
    {"action": "Hello", "duration": 3},
    {"action": "WiggleHips", "duration": 5},
    {"action": "Dance1", "duration": 8},

    # 技巧展示 (90-120秒)
    {"action": "Handstand", "duration": 5},
    {"action": "RecoveryStand", "duration": 2},
    {"action": "FrontFlip", "duration": 5},
    {"action": "RecoveryStand", "duration": 2},
    {"action": "Dance2", "duration": 10},
    {"action": "Stretch", "duration": 4},

    # 节奏部分 (120-150秒)
    {"action": "FreeWalk", "duration": 3},
    {"action": "Move_Forward", "duration": 2},
    {"action": "Turn_Left", "duration": 2},
    {"action": "MoonWalk", "duration": 5},
    {"action": "Move_Backward", "duration": 2},
    {"action": "Turn_Right", "duration": 2},
    {"action": "CrossStep", "duration": 4},
    {"action": "Dance1", "duration": 8},

    # 结尾 (150-180秒)
    {"action": "StandDown", "duration": 2},
    {"action": "FrontJump", "duration": 3},
    {"action": "RecoveryStand", "duration": 2},
    {"action": "Hello", "duration": 3},
    {"action": "Content", "duration": 4},
    {"action": "Stretch", "duration": 4},
    {"action": "StopMove", "duration": 2},
]

# ============================================================================
# 动作序列数据类
# ============================================================================
class ActionStep:
    """动作步骤"""
    def __init__(self, action_id: str, duration: float = None, params: dict = None, devices: list = None):
        self.action_id = action_id
        self.action_name = GO2_ACTIONS.get(action_id, {}).get("name", action_id)
        self.duration = duration or GO2_ACTIONS.get(action_id, {}).get("duration", 2)
        self.params = params or GO2_ACTIONS.get(action_id, {}).get("params", {})
        self.devices = devices or []

    def to_dict(self):
        d = {
            "action": self.action_id,
            "duration": self.duration,
            "params": self.params
        }
        if self.devices:
            d["devices"] = self.devices
        return d

    @classmethod
    def from_dict(cls, data):
        return cls(data["action"], data.get("duration"), data.get("params"), data.get("devices"))


class ParallelGroup:
    """并行动作组 - 多个动作同时执行"""
    def __init__(self, steps: List[ActionStep] = None):
        self.steps = steps or []

    @property
    def duration(self):
        return max(step.duration for step in self.steps) if self.steps else 0

    @property
    def action_name(self):
        parts = []
        for step in self.steps:
            devs = ",".join([str(d) for d in step.devices]) if step.devices else "全"
            parts.append(f"狗{devs}:{step.action_name}")
        return " | ".join(parts)

    def to_dict(self):
        return {"parallel": [step.to_dict() for step in self.steps]}

    @classmethod
    def from_dict(cls, data):
        steps = [ActionStep.from_dict(s) for s in data["parallel"]]
        return cls(steps)

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
        self.selected = False

# ============================================================================
# 网络扫描器
# ============================================================================
class ScanThread(QThread):
    """扫描线程（使用 NetworkScanner）"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(list)  # devices

    def __init__(self, network: str):
        super().__init__()
        self.network = network
        self.scanner = None

    def run(self):
        try:
            from services.network_scanner import NetworkScanner
            self.scanner = NetworkScanner()

            # 连接信号
            self.scanner.scan_progress.connect(self._on_progress)
            self.scanner.device_found.connect(self._on_device_found)

            # 开始扫描
            devices = self.scanner.scan_network(self.network)
            self.finished.emit(devices)

        except Exception as e:
            self.progress.emit(f"扫描失败: {e}")
            self.finished.emit([])

    def _on_progress(self, current, total):
        """进度更新"""
        percent = int(current / total * 100)
        self.progress.emit(f"扫描进度: {current}/{total} ({percent}%)")

    def _on_device_found(self, device):
        """发现设备"""
        from services.network_scanner import DiscoveredDevice
        if device.is_go2:
            ports_str = ",".join(map(str, device.open_ports))
            self.progress.emit(f"✓ 发现GO2设备: {device.ip} - 端口: {ports_str}")

    def stop(self):
        """停止扫描"""
        if self.scanner:
            self.scanner.stop_scan()
        self.progress.emit("扫描已停止")

# ============================================================================
# 连接线程 (已重构，使用全局事件循环)
# ============================================================================
class ConnectThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, robots: List[RobotDevice], global_loop):
        super().__init__()
        self.robots = robots
        self.global_loop = global_loop

    def run(self):
        try:
            if self.global_loop:
                future = asyncio.run_coroutine_threadsafe(self._connect(), self.global_loop)
                future.result()  # 等待异步任务完成
            else:
                self.progress.emit("错误: 未提供全局事件循环")
        except Exception as e:
            self.progress.emit(f"错误: {e}")
        finally:
            self.finished.emit()

    async def _connect(self):
        for robot in self.robots:
            if not robot.selected:
                continue

            self.progress.emit(f"正在连接 {robot.name} ({robot.ip})...")

            try:
                connection = UnitreeWebRTCConnection(
                    connectionMethod=WebRTCConnectionMethod.LocalSTA,
                    ip=robot.ip
                )
                await connection.connect()

                if connection.isConnected:
                    robot.connection = connection
                    robot.connected = True
                    robot.status = "在线"
                    self.progress.emit(f"✓ {robot.name} 连接成功")
                else:
                    robot.status = "连接失败"
                    self.progress.emit(f"✗ {robot.name} 连接失败")
            except Exception as e:
                robot.status = "错误"
                self.progress.emit(f"✗ {robot.name} 连接错误: {e}")

# ============================================================================
# 命令线程（单个动作）(已重构，使用全局事件循环)
# ============================================================================
class CommandThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, robots: List[RobotDevice], action: str, action_name: str, params: dict = None, global_loop=None):
        super().__init__()
        self.robots = robots
        self.action = action
        self.action_name = action_name
        self.params = params or {}
        self.global_loop = global_loop

    def run(self):
        try:
            if self.global_loop:
                future = asyncio.run_coroutine_threadsafe(self._send_command(), self.global_loop)
                future.result()
            else:
                self.progress.emit("错误: 未提供全局事件循环")
        except Exception as e:
            self.progress.emit(f"错误: {e}")
        finally:
            self.finished.emit()

    async def _send_command(self):
        connected_robots = [r for r in self.robots if r.connected and r.selected]

        if not connected_robots:
            self.progress.emit("没有已连接的设备被选中")
            return

        # 检查是否需要模式切换
        action_info = GO2_ACTIONS.get(self.action, {})
        mode = action_info.get("mode")

        for robot in connected_robots:
            try:
                pub_sub = robot.connection.datachannel.pub_sub

                if self.action == "NormalMode":
                    await pub_sub.publish_request_new(
                        RTC_TOPIC["MOTION_SWITCHER"],
                        {"api_id": 1001, "parameter": {"name": "normal"}}
                    )
                    self.progress.emit(f"✓ {robot.name}: 已切回 normal 模式")
                    continue

                if mode == "normal":
                    await pub_sub.publish_request_new(
                        RTC_TOPIC["MOTION_SWITCHER"],
                        {"api_id": 1001, "parameter": {"name": "normal"}}
                    )
                    await asyncio.sleep(0.3)
                elif mode == "advanced":
                    await pub_sub.publish_request_new(
                        RTC_TOPIC["MOTION_SWITCHER"],
                        {"api_id": 1001, "parameter": {"name": "advanced"}}
                    )
                    await asyncio.sleep(0.3)

                cmd = self._get_cmd(self.action)
                if not cmd:
                    self.progress.emit(f"未知动作: {self.action}")
                    return

                await pub_sub.publish_request_new(RTC_TOPIC["SPORT_MOD"], cmd)
                self.progress.emit(f"✓ {robot.name}: {self.action_name}")
                await asyncio.sleep(0.2)
            except Exception as e:
                self.progress.emit(f"✗ {robot.name}: {str(e)}")

    @staticmethod
    def _get_cmd(action):
        cmd_map = {
            "StandUp": {"api_id": SPORT_CMD["StandUp"]},
            "StandDown": {"api_id": SPORT_CMD["StandDown"]},
            "RecoveryStand": {"api_id": SPORT_CMD["RecoveryStand"]},
            "BalanceStand": {"api_id": SPORT_CMD["BalanceStand"]},
            "StopMove": {"api_id": SPORT_CMD["StopMove"]},
            "Damp": {"api_id": SPORT_CMD["Damp"]},
            "Move_Forward": {"api_id": SPORT_CMD["Move"], "parameter": {"x": 0.5, "y": 0.0, "z": 0.0}},
            "Move_Backward": {"api_id": SPORT_CMD["Move"], "parameter": {"x": -0.5, "y": 0.0, "z": 0.0}},
            "Move_Left": {"api_id": SPORT_CMD["Move"], "parameter": {"x": 0.0, "y": 0.5, "z": 0.0}},
            "Move_Right": {"api_id": SPORT_CMD["Move"], "parameter": {"x": 0.0, "y": -0.5, "z": 0.0}},
            "Turn_Left": {"api_id": SPORT_CMD["Move"], "parameter": {"x": 0.0, "y": 0.0, "z": 0.5}},
            "Turn_Right": {"api_id": SPORT_CMD["Move"], "parameter": {"x": 0.0, "y": 0.0, "z": -0.5}},
            "Dance1": {"api_id": SPORT_CMD["Dance1"]},
            "Dance2": {"api_id": SPORT_CMD["Dance2"]},
            "WiggleHips": {"api_id": SPORT_CMD["WiggleHips"]},
            "Content": {"api_id": SPORT_CMD["Content"]},
            "FingerHeart": {"api_id": SPORT_CMD["FingerHeart"]},
            "FrontJump": {"api_id": SPORT_CMD["FrontJump"]},
            "FrontPounce": {"api_id": SPORT_CMD["FrontPounce"]},
            "Stretch": {"api_id": SPORT_CMD["Stretch"]},
            "Sit": {"api_id": SPORT_CMD["Sit"]},
            "RiseSit": {"api_id": SPORT_CMD["RiseSit"]},
            "FrontFlip": {"api_id": SPORT_CMD["FrontFlip"]},
            "BackFlip": {"api_id": SPORT_CMD["BackFlip"]},
            "LeftFlip": {"api_id": SPORT_CMD["LeftFlip"]},
            "Handstand": {"api_id": SPORT_CMD["Handstand"]},
            "Bound": {"api_id": SPORT_CMD["Bound"]},
            "Hello": {"api_id": SPORT_CMD["Hello"]},
            "Pose": {"api_id": SPORT_CMD["Pose"]},
            "Scrape": {"api_id": SPORT_CMD["Scrape"]},
            "FreeWalk": {"api_id": SPORT_CMD["FreeWalk"]},
            "ContinuousGait": {"api_id": SPORT_CMD["ContinuousGait"]},
            "EconomicGait": {"api_id": SPORT_CMD["EconomicGait"]},
            "MoonWalk": {"api_id": SPORT_CMD["MoonWalk"]},
            "CrossStep": {"api_id": SPORT_CMD["CrossStep"]},
        }
        return cmd_map.get(action)

# ============================================================================
# 执行模式选择对话框
# ============================================================================
class ExecuteModeDialog(QDialog):
    """执行模式选择对话框"""

    def __init__(self, robots: List, parent=None):
        super().__init__(parent)
        self.robots = robots
        self.robot_checkboxes = {}
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("选择执行模式")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # 执行模式
        mode_group = QGroupBox("执行模式")
        mode_layout = QVBoxLayout(mode_group)

        self.mode_real = QCheckBox("🔴 真实设备执行")
        self.mode_real.setChecked(True)
        self.mode_real.stateChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.mode_real)

        self.mode_simulator = QCheckBox("🟢 模拟器执行")
        self.mode_simulator.setChecked(False)
        self.mode_simulator.stateChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.mode_simulator)

        layout.addWidget(mode_group)

        # 真实设备选择
        self.real_devices_group = QGroupBox("选择真实设备")
        real_layout = QVBoxLayout(self.real_devices_group)

        for robot in self.robots:
            if robot.connected:
                checkbox = QCheckBox(f"{robot.name} ({robot.ip})")
                checkbox.setChecked(robot.selected)
                real_layout.addWidget(checkbox)
                self.robot_checkboxes[robot] = checkbox

        if not self.robots or not any(r.connected for r in self.robots):
            real_layout.addWidget(QLabel("没有已连接的设备"))

        layout.addWidget(self.real_devices_group)

        # 说明
        info = QLabel("💡 提示: 可以同时选择真实设备和模拟器执行")
        info.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(info)

        # 按钮
        button_layout = QHBoxLayout()

        ok_btn = QPushButton("▶️ 开始执行")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        button_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("❌ 取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

        # 初始状态
        self.on_mode_changed()

    def on_mode_changed(self):
        """模式选择改变"""
        use_real = self.mode_real.isChecked()
        use_sim = self.mode_simulator.isChecked()

        # 启用/禁用真实设备选择
        self.real_devices_group.setEnabled(use_real)

        # 如果两个都没选，自动选一个
        if not use_real and not use_sim:
            # 当前正在改变的那个，不允许两个都不选
            if self.sender() == self.mode_real:
                self.mode_simulator.setChecked(True)
            else:
                self.mode_real.setChecked(True)

    def get_execution_mode(self) -> str:
        """获取执行模式"""
        real = self.mode_real.isChecked()
        sim = self.mode_simulator.isChecked()

        if real and sim:
            return "混合模式（真实+模拟）"
        elif real:
            return "真实设备"
        elif sim:
            return "模拟器"
        else:
            return "未选择"

    def get_selected_real_robots(self) -> List:
        """获取选中的真实设备"""
        if not self.mode_real.isChecked():
            return []

        selected = []
        for robot, checkbox in self.robot_checkboxes.items():
            if checkbox.isChecked():
                selected.append(robot)
        return selected

    def use_simulator(self) -> bool:
        """是否使用模拟器"""
        return self.mode_simulator.isChecked()


# ============================================================================
# 添加并行动作对话框
# ============================================================================
class AddParallelDialog(QDialog):
    """为每只狗分别选择动作，组成并行组"""

    def __init__(self, dog_count: int, parent=None):
        super().__init__(parent)
        self.dog_count = dog_count
        self.rows = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("添加并行动作")
        self.setMinimumWidth(600)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("为每只狗分别选择动作（不需要的狗留空即可）:"))

        grid = QGridLayout()
        grid.addWidget(QLabel("设备"), 0, 0)
        grid.addWidget(QLabel("动作"), 0, 1)
        grid.addWidget(QLabel("时长(秒)"), 0, 2)

        for i in range(self.dog_count):
            label = QLabel(f"狗{i+1}")
            combo = QComboBox()
            combo.addItem("-- 不执行 --", "")
            for action_id, info in sorted(GO2_ACTIONS.items()):
                combo.addItem(f"[{info['category']}] {info['name']}", action_id)
            spin = QDoubleSpinBox()
            spin.setRange(0.5, 60)
            spin.setValue(2)
            spin.setSingleStep(0.5)

            grid.addWidget(label, i + 1, 0)
            grid.addWidget(combo, i + 1, 1)
            grid.addWidget(spin, i + 1, 2)
            self.rows.append((combo, spin))

        layout.addLayout(grid)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定添加")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def get_parallel_group(self) -> Optional[ParallelGroup]:
        steps = []
        for i, (combo, spin) in enumerate(self.rows):
            action_id = combo.currentData()
            if not action_id:
                continue
            duration = spin.value()
            step = ActionStep(action_id, duration, devices=[i + 1])
            steps.append(step)
        if len(steps) < 1:
            return None
        return ParallelGroup(steps)


# ============================================================================
# 动作序列执行线程 (已重构，使用全局事件循环)
# ============================================================================
class DanceSequenceThread(QThread):
    progress = pyqtSignal(str)
    current_action = pyqtSignal(str)  # 当前执行的动作
    progress_percent = pyqtSignal(int)  # 进度百分比
    action_index = pyqtSignal(int)  # 当前动作索引
    simulator_action = pyqtSignal(str, str, float)  # 模拟器动作信号
    finished = pyqtSignal()
    stopped = False

    def __init__(self, robots: List[RobotDevice], sequence: List[ActionStep], use_simulator: bool = False, global_loop=None):
        super().__init__()
        self.robots = robots
        self.sequence = sequence
        self.use_simulator = use_simulator
        self.current_index = 0
        self.global_loop = global_loop

    def run(self):
        try:
            if self.global_loop:
                future = asyncio.run_coroutine_threadsafe(self._execute_sequence(), self.global_loop)
                future.result()
            else:
                self.progress.emit("错误: 未提供全局事件循环")
        except Exception as e:
            self.progress.emit(f"执行错误: {e}")
        finally:
            self.finished.emit()

    def stop(self):
        """停止执行"""
        self.stopped = True

    async def _execute_sequence(self):
        print(f"\n{'='*80}")
        print(f"[序列执行] ========== 开始执行舞蹈序列 ==========")
        print(f"[序列执行] 序列包含 {len(self.sequence)} 个动作")
        print(f"[序列执行] 使用模拟器: {self.use_simulator}")
        print(f"{'='*80}\n")

        connected_robots = [r for r in self.robots if r.connected and r.selected]
        print(f"[序列执行] 已连接的设备: {len(connected_robots)}")
        for robot in connected_robots:
            print(f"[序列执行]   - {robot.name} ({robot.ip})")

        if not connected_robots and not self.use_simulator:
            self.progress.emit("没有已连接的设备被选中")
            print(f"[序列执行] ✗ 没有设备也没有模拟器，退出")
            return

        total_duration = sum(step.duration for step in self.sequence)
        self.progress.emit(f"开始执行舞蹈序列，共 {len(self.sequence)} 个动作，总时长约 {total_duration:.0f} 秒")
        self.progress.emit(f"已连接设备: {', '.join([r.name for r in connected_robots])}")

        # 构建完整的命令映射
        from unitree_webrtc_connect import RTC_TOPIC, SPORT_CMD

        cmd_map = {
            # 基础动作
            "StandUp": {"api_id": SPORT_CMD["StandUp"]},
            "StandDown": {"api_id": SPORT_CMD["StandDown"]},
            "RecoveryStand": {"api_id": SPORT_CMD["RecoveryStand"]},
            "BalanceStand": {"api_id": SPORT_CMD["BalanceStand"]},
            "StopMove": {"api_id": SPORT_CMD["StopMove"]},
            "Damp": {"api_id": SPORT_CMD["Damp"]},

            # 运动动作 (Move接口: vx, vy, vyaw)
            "Move_Forward": {"api_id": SPORT_CMD["Move"], "parameter": {"x": 0.5, "y": 0.0, "z": 0.0}},
            "Move_Backward": {"api_id": SPORT_CMD["Move"], "parameter": {"x": -0.5, "y": 0.0, "z": 0.0}},
            "Move_Left": {"api_id": SPORT_CMD["Move"], "parameter": {"x": 0.0, "y": 0.5, "z": 0.0}},
            "Move_Right": {"api_id": SPORT_CMD["Move"], "parameter": {"x": 0.0, "y": -0.5, "z": 0.0}},
            "Turn_Left": {"api_id": SPORT_CMD["Move"], "parameter": {"x": 0.0, "y": 0.0, "z": 0.5}},
            "Turn_Right": {"api_id": SPORT_CMD["Move"], "parameter": {"x": 0.0, "y": 0.0, "z": -0.5}},

            # 舞蹈动作
            "Dance1": {"api_id": SPORT_CMD["Dance1"]},
            "Dance2": {"api_id": SPORT_CMD["Dance2"]},
            "WiggleHips": {"api_id": SPORT_CMD["WiggleHips"]},
            "Content": {"api_id": SPORT_CMD["Content"]},
            "FingerHeart": {"api_id": SPORT_CMD["FingerHeart"]},

            # 特技动作
            "FrontJump": {"api_id": SPORT_CMD["FrontJump"]},
            "FrontPounce": {"api_id": SPORT_CMD["FrontPounce"]},
            "Stretch": {"api_id": SPORT_CMD["Stretch"]},
            "Sit": {"api_id": SPORT_CMD["Sit"]},
            "RiseSit": {"api_id": SPORT_CMD["RiseSit"]},
            "FrontFlip": {"api_id": SPORT_CMD["FrontFlip"]},
            "BackFlip": {"api_id": SPORT_CMD["BackFlip"]},
            "LeftFlip": {"api_id": SPORT_CMD["LeftFlip"]},
            "Handstand": {"api_id": SPORT_CMD["Handstand"]},
            "Bound": {"api_id": SPORT_CMD["Bound"]},

            # 交互动作
            "Hello": {"api_id": SPORT_CMD["Hello"]},
            "Pose": {"api_id": SPORT_CMD["Pose"]},
            "Scrape": {"api_id": SPORT_CMD["Scrape"]},

            # 步态动作
            "FreeWalk": {"api_id": SPORT_CMD["FreeWalk"]},
            "ContinuousGait": {"api_id": SPORT_CMD["ContinuousGait"]},
            "EconomicGait": {"api_id": SPORT_CMD["EconomicGait"]},
            "MoonWalk": {"api_id": SPORT_CMD["MoonWalk"]},
            "CrossStep": {"api_id": SPORT_CMD["CrossStep"]},
        }

        self.progress.emit(f"命令映射包含 {len(cmd_map)} 个动作")

        total_steps = len(self.sequence)
        total_duration = sum(step.duration for step in self.sequence)
        elapsed_time = 0

        for i, step in enumerate(self.sequence):
            if self.stopped:
                self.progress.emit("舞蹈序列已停止")
                return

            self.current_index = i

            # 发送进度信号
            progress = int((i / total_steps) * 100)
            self.progress_percent.emit(progress)
            self.action_index.emit(i)

            # 判断是并行组还是单个动作
            is_parallel = isinstance(step, ParallelGroup)
            step_duration = step.duration
            step_name = step.action_name if is_parallel else step.action_name

            self.current_action.emit(f"{i+1}/{total_steps}: {step_name} ({step_duration}秒)")
            self.progress.emit(f"[{i+1}/{total_steps}] 执行: {step_name}")

            if is_parallel:
                # === 并行组执行：同时发送多个动作到不同设备 ===
                if self.use_simulator:
                    self.simulator_action.emit("模拟狗-全部", step_name, step_duration)

                if connected_robots:
                    async def _send_parallel_step(sub_step):
                        action_info = GO2_ACTIONS.get(sub_step.action_id, {})
                        mode = action_info.get("mode")
                        cmd = cmd_map.get(sub_step.action_id)
                        if not cmd and sub_step.action_id != "NormalMode" and sub_step.action_id != "Rest":
                            return
                        if sub_step.action_id == "Rest":
                            return

                        if sub_step.devices:
                            targets = [connected_robots[d - 1] for d in sub_step.devices if d - 1 < len(connected_robots)]
                        else:
                            targets = connected_robots

                        for robot in targets:
                            try:
                                pub_sub = robot.connection.datachannel.pub_sub
                                if sub_step.action_id == "NormalMode":
                                    await pub_sub.publish_request_new(
                                        RTC_TOPIC["MOTION_SWITCHER"],
                                        {"api_id": 1001, "parameter": {"name": "normal"}}
                                    )
                                    continue
                                if mode == "normal":
                                    await pub_sub.publish_request_new(
                                        RTC_TOPIC["MOTION_SWITCHER"],
                                        {"api_id": 1001, "parameter": {"name": "normal"}}
                                    )
                                    await asyncio.sleep(0.3)
                                elif mode == "advanced":
                                    await pub_sub.publish_request_new(
                                        RTC_TOPIC["MOTION_SWITCHER"],
                                        {"api_id": 1001, "parameter": {"name": "advanced"}}
                                    )
                                    await asyncio.sleep(0.3)
                                await pub_sub.publish_request_new(RTC_TOPIC["SPORT_MOD"], cmd)
                                self.progress.emit(f"✓ {robot.name}: {sub_step.action_name}")
                            except Exception as e:
                                self.progress.emit(f"✗ {robot.name}: {str(e)}")

                    await asyncio.gather(*[_send_parallel_step(s) for s in step.steps])

            else:
                # === 单个动作执行 ===
                if self.use_simulator:
                    self.simulator_action.emit("模拟狗-全部", step.action_name, step.duration)
                    self.progress.emit(f"🟢 模拟器: {step.action_name}")

                action_info = GO2_ACTIONS.get(step.action_id, {})
                mode = action_info.get("mode")
                cmd = cmd_map.get(step.action_id)

                if connected_robots and (cmd or step.action_id == "NormalMode"):
                    if step.devices:
                        target_robots = [connected_robots[d - 1] for d in step.devices if d - 1 < len(connected_robots)]
                    else:
                        target_robots = connected_robots

                    if target_robots:
                        async def _send_to_robot(robot):
                            try:
                                pub_sub = robot.connection.datachannel.pub_sub
                                if step.action_id == "NormalMode":
                                    await pub_sub.publish_request_new(
                                        RTC_TOPIC["MOTION_SWITCHER"],
                                        {"api_id": 1001, "parameter": {"name": "normal"}}
                                    )
                                    return True
                                if mode == "normal":
                                    await pub_sub.publish_request_new(
                                        RTC_TOPIC["MOTION_SWITCHER"],
                                        {"api_id": 1001, "parameter": {"name": "normal"}}
                                    )
                                    await asyncio.sleep(0.3)
                                elif mode == "advanced":
                                    await pub_sub.publish_request_new(
                                        RTC_TOPIC["MOTION_SWITCHER"],
                                        {"api_id": 1001, "parameter": {"name": "advanced"}}
                                    )
                                    await asyncio.sleep(0.3)
                                await pub_sub.publish_request_new(RTC_TOPIC["SPORT_MOD"], cmd)
                                self.progress.emit(f"✓ {robot.name}: {step.action_name}")
                                return True
                            except Exception as e:
                                self.progress.emit(f"✗ {robot.name}: {str(e)}")
                                return False

                        await asyncio.gather(*[_send_to_robot(r) for r in target_robots])

            # 等待动作完成（分割成短等待，以便及时响应停止）
            wait_time = step_duration
            check_interval = 0.1
            while wait_time > 0 and not self.stopped:
                sleep_time = min(check_interval, wait_time)
                await asyncio.sleep(sleep_time)
                wait_time -= sleep_time

                elapsed_partial = elapsed_time + (step_duration - wait_time)
                progress = int((elapsed_partial / total_duration) * 100)
                self.progress_percent.emit(progress)

            elapsed_time += step_duration

            if self.stopped:
                self.progress.emit("舞蹈序列已停止")
                return

            self.progress.emit(f"动作 {i+1} 完成，继续下一个...")

        # 完成
        self.progress_percent.emit(100)
        print(f"\n{'='*80}")
        print(f"[序列执行] ========== 序列执行完成 ==========")
        print(f"[序列执行] 总共执行了 {len(self.sequence)} 个动作")
        print(f"[序列执行] 总时长: {total_duration:.0f} 秒")
        print(f"{'='*80}\n")

        self.progress.emit(f"舞蹈序列执行完成！共 {len(self.sequence)} 个动作")
        self.current_action.emit("完成")

# ============================================================================
# 辅助函数
# ============================================================================
def get_local_ip() -> str:
    """获取本机IP地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            return local_ip
        except Exception:
            return "127.0.0.1"


def get_network_from_ip(ip: str) -> str:
    """从IP地址获取网段"""
    parts = ip.split('.')
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
    return "192.168.71.0/24"


# ============================================================================
# 主窗口
# ============================================================================
class GO2ControlPanel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GO2 机器狗控制面板 v4.1 - 修复联机异步Bug")
        self.setGeometry(100, 100, 1200, 800)

        self.robots: List[RobotDevice] = []
        self.scan_thread = None
        self.connect_thread = None
        self.command_thread = None
        self.dance_thread = None

        import threading

        # 初始化一个全局循环
        self.global_loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self.global_loop.run_forever, daemon=True)
        self.loop_thread.start()

        self.action_sequence = []
        self.simulator_window = None
        self.log_text = None

        self.init_ui()
        self.show_info()

    def init_ui(self):
        """初始化UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)

        # 左侧面板
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)

        # 右侧面板（标签页）
        right_panel = QTabWidget()

        # 动作选择标签
        action_tab = self.create_action_tab()
        right_panel.addTab(action_tab, "动作选择")

        # 舞蹈序列标签
        dance_tab = self.create_dance_sequence_tab()
        right_panel.addTab(dance_tab, "舞蹈序列")

        # 预设舞蹈标签
        preset_tab = self.create_preset_dance_tab()
        right_panel.addTab(preset_tab, "预设舞蹈")

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        main_layout.addWidget(splitter)

        # 底部日志
        log_group = QGroupBox("执行日志")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)

    def create_left_panel(self) -> QWidget:
        """创建左侧面板"""
        panel = QFrame()
        layout = QVBoxLayout(panel)

        # 网络扫描
        scan_group = QGroupBox("网络扫描")
        scan_layout = QVBoxLayout()

        info_layout = QHBoxLayout()
        info_label = QLabel("💡 提示: 可自动获取本机网段")
        info_label.setStyleSheet("color: #666; font-size: 11px;")
        info_layout.addWidget(info_label)
        scan_layout.addLayout(info_layout)

        network_layout = QHBoxLayout()
        network_layout.addWidget(QLabel("网段:"))
        self.network_input = QLineEdit()
        try:
            local_ip = get_local_ip()
            network = get_network_from_ip(local_ip)
            self.network_input.setText(network)
        except Exception as e:
            self.network_input.setText("192.168.71.0/24")
        network_layout.addWidget(self.network_input)
        scan_layout.addLayout(network_layout)

        refresh_btn_layout = QHBoxLayout()
        self.refresh_ip_btn = QPushButton("🔄 刷新本机IP")
        self.refresh_ip_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 11px;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.refresh_ip_btn.clicked.connect(self.refresh_local_ip)
        refresh_btn_layout.addWidget(self.refresh_ip_btn)
        refresh_btn_layout.addStretch()
        scan_layout.addLayout(refresh_btn_layout)

        btn_layout = QHBoxLayout()
        self.scan_btn = QPushButton("扫描网络")
        self.scan_btn.clicked.connect(self.start_scan)
        btn_layout.addWidget(self.scan_btn)

        self.stop_scan_btn = QPushButton("停止")
        self.stop_scan_btn.setEnabled(False)
        self.stop_scan_btn.clicked.connect(self.stop_scan)
        btn_layout.addWidget(self.stop_scan_btn)
        scan_layout.addLayout(btn_layout)

        self.scan_progress = QProgressBar()
        self.scan_progress.setVisible(False)
        scan_layout.addWidget(self.scan_progress)

        scan_group.setLayout(scan_layout)
        layout.addWidget(scan_group)

        # 手动添加IP
        manual_group = QGroupBox("手动添加IP")
        manual_layout = QVBoxLayout()

        ip_input_layout = QHBoxLayout()
        ip_input_layout.addWidget(QLabel("IP地址:"))
        self.manual_ip_input = QLineEdit()
        self.manual_ip_input.setPlaceholderText("192.168.71.31")
        ip_input_layout.addWidget(self.manual_ip_input)
        manual_layout.addLayout(ip_input_layout)

        add_btn = QPushButton("添加设备")
        add_btn.clicked.connect(self.add_manual_ip)
        manual_layout.addWidget(add_btn)

        quick_layout = QHBoxLayout()
        self.quick_ip_1_btn = QPushButton("IP1")
        self.quick_ip_1_btn.clicked.connect(lambda: self.add_quick_ip("192.168.71.31"))
        quick_layout.addWidget(self.quick_ip_1_btn)

        self.quick_ip_2_btn = QPushButton("IP2")
        self.quick_ip_2_btn.clicked.connect(lambda: self.add_quick_ip("192.168.71.32"))
        quick_layout.addWidget(self.quick_ip_2_btn)

        self.quick_ip_3_btn = QPushButton("IP3")
        self.quick_ip_3_btn.clicked.connect(lambda: self.add_quick_ip("192.168.71.33"))
        quick_layout.addWidget(self.quick_ip_3_btn)

        manual_layout.addLayout(quick_layout)
        manual_group.setLayout(manual_layout)
        layout.addWidget(manual_group)

        # 设备列表
        device_group = QGroupBox("发现的设备")
        device_layout = QVBoxLayout()

        self.device_table = QTableWidget()
        self.device_table.setColumnCount(5)
        self.device_table.setHorizontalHeaderLabels(["选择", "名称", "IP", "端口", "状态"])
        self.device_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.device_table.setMaximumHeight(200)
        device_layout.addWidget(self.device_table)

        device_btn_layout = QHBoxLayout()
        self.connect_btn = QPushButton("连接选中设备")
        self.connect_btn.clicked.connect(self.connect_selected)
        self.connect_btn.setEnabled(False)
        device_btn_layout.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("断开所有")
        self.disconnect_btn.clicked.connect(self.disconnect_all)
        device_btn_layout.addWidget(self.disconnect_btn)
        device_layout.addLayout(device_btn_layout)

        simulator_btn_layout = QHBoxLayout()
        self.simulator_btn = QPushButton("🟢 打开模拟器")
        self.simulator_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 12px;
                font-weight: bold;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.simulator_btn.clicked.connect(self.open_simulator)
        simulator_btn_layout.addWidget(self.simulator_btn)
        device_layout.addLayout(simulator_btn_layout)

        device_group.setLayout(device_layout)
        layout.addWidget(device_group)

        layout.addStretch()
        return panel

    def create_action_tab(self) -> QWidget:
        """创建动作选择标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        categories = ["基础", "运动", "舞蹈", "特技", "交互", "步态"]
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        for category in categories:
            group = QGroupBox(f"{category}动作")
            grid = QGridLayout(group)

            actions = ACTION_CATEGORIES[category]
            for idx, action_id in enumerate(actions):
                action_info = GO2_ACTIONS[action_id]
                btn = QPushButton(action_info["name"])
                btn.setToolTip(f"时长: {action_info['duration']}秒")
                btn.clicked.connect(lambda checked, a=action_id, n=action_info["name"]:
                    self.send_action(a, n))
                row = idx // 3
                col = idx % 3
                grid.addWidget(btn, row, col)

            scroll_layout.addWidget(group)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        return widget

    def create_dance_sequence_tab(self) -> QWidget:
        """创建舞蹈序列标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 参与狗数量设置
        dog_count_group = QGroupBox("参与设备设置")
        dog_count_layout = QHBoxLayout(dog_count_group)
        dog_count_layout.addWidget(QLabel("参与狗数:"))
        self.dog_count_spin = QSpinBox()
        self.dog_count_spin.setRange(1, 20)
        self.dog_count_spin.setValue(2)
        self.dog_count_spin.valueChanged.connect(self.on_dog_count_changed)
        dog_count_layout.addWidget(self.dog_count_spin)
        dog_count_layout.addWidget(QLabel("(每个动作可单独选择哪些狗执行)"))
        dog_count_layout.addStretch()
        layout.addWidget(dog_count_group)

        control_group = QGroupBox("动作控制")
        control_layout = QHBoxLayout(control_group)

        control_layout.addWidget(QLabel("动作:"))
        self.action_combo = QComboBox()
        for action_id, info in sorted(GO2_ACTIONS.items()):
            self.action_combo.addItem(info["name"], action_id)
        control_layout.addWidget(self.action_combo)

        control_layout.addWidget(QLabel("时长(秒):"))
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.5, 60)
        self.duration_spin.setValue(2)
        self.duration_spin.setSingleStep(0.5)
        control_layout.addWidget(self.duration_spin)

        control_layout.addWidget(QLabel("设备:"))
        self.device_checkboxes_container = QWidget()
        self.device_checkboxes_layout = QHBoxLayout(self.device_checkboxes_container)
        self.device_checkboxes_layout.setContentsMargins(0, 0, 0, 0)
        self.device_checkboxes_layout.setSpacing(2)
        self.device_checkboxes = []
        self._rebuild_device_checkboxes(2)
        control_layout.addWidget(self.device_checkboxes_container)

        self.add_action_btn = QPushButton("➕ 添加")
        self.add_action_btn.clicked.connect(self.add_action_to_sequence)
        control_layout.addWidget(self.add_action_btn)

        self.add_parallel_btn = QPushButton("➕ 添加并行")
        self.add_parallel_btn.clicked.connect(self.add_parallel_to_sequence)
        self.add_parallel_btn.setToolTip("为不同的狗同时设置不同动作")
        control_layout.addWidget(self.add_parallel_btn)

        self.remove_action_btn = QPushButton("❌ 删除选中")
        self.remove_action_btn.clicked.connect(self.remove_action_from_sequence)
        control_layout.addWidget(self.remove_action_btn)

        self.clear_sequence_btn = QPushButton("🗑️ 清空")
        self.clear_sequence_btn.clicked.connect(self.clear_sequence)
        control_layout.addWidget(self.clear_sequence_btn)

        layout.addWidget(control_group)

        timeline_group = QGroupBox("时间轴 (可拖拽调整)")
        timeline_layout = QVBoxLayout(timeline_group)

        time_ruler = QWidget()
        time_ruler.setFixedHeight(30)
        time_ruler.setStyleSheet("background-color: #e0e0e0; border: 1px solid #999;")
        self.time_ruler_layout = QHBoxLayout(time_ruler)
        self.time_ruler_layout.setContentsMargins(0, 0, 0, 0)
        timeline_layout.addWidget(time_ruler)

        self.timeline_list = QListWidget()
        self.timeline_list.setMinimumHeight(250)
        self.timeline_list.setMaximumHeight(350)
        self.timeline_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.timeline_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.timeline_list.model().rowsMoved.connect(self.on_timeline_reordered)
        timeline_layout.addWidget(self.timeline_list)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("准备就绪")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #05B8CC;
            }
        """)
        timeline_layout.addWidget(self.progress_bar)

        self.current_action_label = QLabel("未执行")
        self.current_action_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #0066cc;
            background-color: #f0f0f0;
            padding: 10px;
            border-radius: 5px;
        """)
        self.current_action_label.setAlignment(Qt.AlignCenter)
        timeline_layout.addWidget(self.current_action_label)

        layout.addWidget(timeline_group)

        # 合并/拆分按钮
        merge_layout = QHBoxLayout()
        self.merge_btn = QPushButton("🔗 合并选中为并行")
        self.merge_btn.setToolTip("选中多个动作后合并为同时执行的并行组")
        self.merge_btn.clicked.connect(self.merge_selected)
        merge_layout.addWidget(self.merge_btn)

        self.split_btn = QPushButton("✂️ 拆分并行组")
        self.split_btn.setToolTip("将选中的并行组拆分为独立动作")
        self.split_btn.clicked.connect(self.split_selected)
        merge_layout.addWidget(self.split_btn)
        merge_layout.addStretch()
        layout.addLayout(merge_layout)

        exec_layout = QHBoxLayout()

        self.save_sequence_btn = QPushButton("💾 保存序列")
        self.save_sequence_btn.clicked.connect(self.save_sequence)
        exec_layout.addWidget(self.save_sequence_btn)

        self.load_sequence_btn = QPushButton("📂 加载序列")
        self.load_sequence_btn.clicked.connect(self.load_sequence)
        exec_layout.addWidget(self.load_sequence_btn)

        exec_layout.addStretch()

        self.execute_sequence_btn = QPushButton("▶️ 执行序列")
        self.execute_sequence_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.execute_sequence_btn.clicked.connect(self.execute_sequence)
        exec_layout.addWidget(self.execute_sequence_btn)

        self.stop_sequence_btn = QPushButton("⏹️ 停止")
        self.stop_sequence_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.stop_sequence_btn.clicked.connect(self.stop_sequence)
        self.stop_sequence_btn.setEnabled(False)
        exec_layout.addWidget(self.stop_sequence_btn)

        layout.addLayout(exec_layout)

        return widget

    def on_timeline_reordered(self, parent, start, end, destination, row):
        """时间轴重排后更新数据"""
        if start < end:
            item = self.action_sequence.pop(start)
            self.action_sequence.insert(end - 1, item)
        else:
            item = self.action_sequence.pop(start)
            self.action_sequence.insert(end, item)
        self.log(f"时间轴已重新排序: {start} → {end}")

    def on_dog_count_changed(self, count):
        """参与狗数量改变时重建设备checkbox"""
        self._rebuild_device_checkboxes(count)

    def _rebuild_device_checkboxes(self, count):
        """根据狗数量重建设备选择checkbox"""
        # 清除旧的
        for cb in self.device_checkboxes:
            cb.setParent(None)
            cb.deleteLater()
        self.device_checkboxes.clear()

        # 创建新的
        for i in range(1, count + 1):
            cb = QCheckBox(f"{i}")
            cb.setChecked(True)
            cb.setToolTip(f"狗{i}")
            self.device_checkboxes.append(cb)
            self.device_checkboxes_layout.addWidget(cb)

    def create_preset_dance_tab(self) -> QWidget:
        """创建预设舞蹈标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        preset_group = QGroupBox("预设舞蹈")
        preset_layout = QVBoxLayout(preset_group)

        preset_info = QLabel("3分钟完整舞蹈 - 包含 60+ 个动作")
        preset_info.setStyleSheet("color: #0066cc; font-weight: bold;")
        preset_layout.addWidget(preset_info)

        preview_list = QListWidget()
        preview_list.setMaximumHeight(250)
        for step in PRESET_DANCE_3MIN:
            action_name = GO2_ACTIONS.get(step["action"], {}).get("name", step["action"])
            preview_list.addItem(f"{action_name} - {step['duration']}秒")
        preset_layout.addWidget(preview_list)

        exec_layout = QHBoxLayout()
        self.execute_preset_btn = QPushButton("执行3分钟舞蹈")
        self.execute_preset_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff6600;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #ff8533;
            }
        """)
        self.execute_preset_btn.clicked.connect(self.execute_preset_dance)
        exec_layout.addWidget(self.execute_preset_btn)

        self.stop_preset_btn = QPushButton("停止")
        self.stop_preset_btn.clicked.connect(self.stop_sequence)
        self.stop_preset_btn.setEnabled(False)
        exec_layout.addWidget(self.stop_preset_btn)
        preset_layout.addLayout(exec_layout)

        layout.addWidget(preset_group)

        stats_group = QGroupBox("舞蹈统计")
        stats_layout = QGridLayout(stats_group)

        total_steps = len(PRESET_DANCE_3MIN)
        total_duration = sum(step["duration"] for step in PRESET_DANCE_3MIN)

        stats_layout.addWidget(QLabel("动作总数:"), 0, 0)
        stats_layout.addWidget(QLabel(f"{total_steps} 个"), 0, 1)
        stats_layout.addWidget(QLabel("总时长:"), 1, 0)
        stats_layout.addWidget(QLabel(f"{total_duration:.0f} 秒 ({total_duration/60:.1f} 分钟)"), 1, 1)

        category_counts = {}
        for step in PRESET_DANCE_3MIN:
            category = GO2_ACTIONS.get(step["action"], {}).get("category", "其他")
            category_counts[category] = category_counts.get(category, 0) + 1

        row = 2
        for category, count in category_counts.items():
            stats_layout.addWidget(QLabel(f"{category}:"), row, 0)
            stats_layout.addWidget(QLabel(f"{count} 个"), row, 1)
            row += 1

        layout.addWidget(stats_group)
        layout.addStretch()
        return widget

    def refresh_local_ip(self):
        """刷新本机IP"""
        try:
            local_ip = get_local_ip()
            network = get_network_from_ip(local_ip)
            self.network_input.setText(network)
            self.log(f"🔄 刷新本机IP: {local_ip}")
            self.log(f"🔄 网段已更新: {network}")
            QMessageBox.information(self, "刷新成功", f"本机IP: {local_ip}\n网段: {network}")
        except Exception as e:
            self.log(f"✗ 刷新失败: {e}")
            QMessageBox.warning(self, "刷新失败", f"无法获取本机IP: {e}")

    def start_scan(self):
        """开始扫描"""
        network = self.network_input.text().strip()
        if not network:
            QMessageBox.warning(self, "输入错误", "请输入网段")
            return

        self.scan_btn.setEnabled(False)
        self.scan_progress.setVisible(True)
        self.scan_progress.setRange(0, 254)

        self.device_table.setRowCount(0)
        self.robots.clear()

        self.log(f"开始扫描: {network}")

        self.scan_thread = ScanThread(network)
        self.scan_thread.progress.connect(self.log)
        self.scan_thread.finished.connect(self.on_scan_finished)
        self.scan_thread.start()

    def on_scan_finished(self, devices: list):
        """扫描完成"""
        self.scan_btn.setEnabled(True)
        self.scan_progress.setVisible(False)
        self.device_table.setRowCount(0)

        if not devices:
            self.log("未发现设备")
            return

        for device in devices:
            ip = device.ip
            ports = device.open_ports
            is_go2 = device.is_go2

            row = self.device_table.rowCount()
            self.device_table.insertRow(row)

            checkbox = QCheckBox()
            checkbox.setChecked(is_go2)
            self.device_table.setCellWidget(row, 0, checkbox)

            name = f"GO2-{row+1}" if is_go2 else f"Device-{row+1}"
            self.device_table.setItem(row, 1, QTableWidgetItem(name))
            self.device_table.setItem(row, 2, QTableWidgetItem(ip))
            self.device_table.setItem(row, 3, QTableWidgetItem(str(ports)))
            self.device_table.setItem(row, 4, QTableWidgetItem("未连接"))

            robot = RobotDevice(ip, row)
            robot.name = name
            robot.is_go2 = is_go2
            robot.open_ports = ports
            self.robots.append(robot)

        go2_count = sum(1 for r in self.robots if r.is_go2)
        self.log(f"扫描完成，发现 {len(self.robots)} 台设备，其中 {go2_count} 台 GO2")
        self.connect_btn.setEnabled(True)
        self.stop_scan_btn.setEnabled(False)

    def stop_scan(self):
        """停止扫描"""
        if self.scan_thread and self.scan_thread.isRunning():
            self.scan_thread.terminate()
            self.scan_thread.wait(1000)
            self.log("扫描已停止")

        self.scan_btn.setEnabled(True)
        self.stop_scan_btn.setEnabled(False)
        self.scan_progress.setVisible(False)

    def add_manual_ip(self):
        """手动添加IP地址"""
        ip = self.manual_ip_input.text().strip()
        if not ip:
            QMessageBox.warning(self, "输入错误", "请输入IP地址")
            return

        import re
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(ip_pattern, ip):
            QMessageBox.warning(self, "输入错误", "IP地址格式不正确\n正确格式: 192.168.71.31")
            return

        for robot in self.robots:
            if robot.ip == ip:
                QMessageBox.warning(self, "设备已存在", f"IP {ip} 已经在列表中了")
                return

        row = self.device_table.rowCount()
        self.device_table.insertRow(row)

        checkbox = QCheckBox()
        checkbox.setChecked(True)
        self.device_table.setCellWidget(row, 0, checkbox)

        name = f"GO2-{row+1}"
        self.device_table.setItem(row, 1, QTableWidgetItem(name))
        self.device_table.setItem(row, 2, QTableWidgetItem(ip))
        self.device_table.setItem(row, 3, QTableWidgetItem("[9991]"))
        self.device_table.setItem(row, 4, QTableWidgetItem("未连接"))

        robot = RobotDevice(ip, row)
        robot.name = name
        robot.is_go2 = True
        robot.open_ports = [9991]
        self.robots.append(robot)

        self.log(f"✓ 已添加设备: {name} @ {ip}")
        self.connect_btn.setEnabled(True)
        self.manual_ip_input.clear()

    def add_quick_ip(self, ip: str):
        """快速添加IP"""
        self.manual_ip_input.setText(ip)
        self.add_manual_ip()

    def connect_selected(self):
        """连接选中的设备"""
        for i in range(self.device_table.rowCount()):
            checkbox = self.device_table.cellWidget(i, 0)
            if checkbox:
                self.robots[i].selected = checkbox.isChecked()

        selected = [r for r in self.robots if r.selected]
        if not selected:
            QMessageBox.warning(self, "未选择", "请先勾选要连接的设备")
            return

        self.log(f"正在连接 {len(selected)} 台设备...")

        self.connect_thread = ConnectThread(self.robots, self.global_loop)
        self.connect_thread.progress.connect(self.log)
        self.connect_thread.finished.connect(self.on_connect_finished)
        self.connect_thread.start()

    def on_connect_finished(self):
        """连接完成"""
        self.disconnect_btn.setEnabled(True)

        for i, robot in enumerate(self.robots):
            status_text = "在线" if robot.connected else robot.status
            self.device_table.setItem(i, 4, QTableWidgetItem(status_text))

        connected_count = sum(1 for r in self.robots if r.connected)
        self.log(f"连接完成，已连接 {connected_count} 台设备")

    def disconnect_all(self):
        """断开所有连接（非阻塞更新）"""
        try:
            for robot in self.robots:
                if robot.connected:
                    asyncio.run_coroutine_threadsafe(robot.connection.disconnect(), self.global_loop)
                    robot.connected = False
                    robot.status = "已断开"

            for i in range(self.device_table.rowCount()):
                self.device_table.setItem(i, 4, QTableWidgetItem("已断开"))

            self.log("已断开所有连接")
            self.disconnect_btn.setEnabled(False)
        except Exception as e:
            self.log(f"断开连接错误: {e}")

    def send_action(self, action: str, action_name: str):
        selected_robots = [r for r in self.robots if r.connected and r.selected]
        
        if not selected_robots:
            QMessageBox.warning(self, "未选择", "请先勾选要控制的设备")
            return

        self.log(f"尝试执行: {action_name}")

        for robot in selected_robots:
            asyncio.run_coroutine_threadsafe(
                self._async_send(robot, action), 
                self.global_loop
            )

    async def _async_send(self, robot, action):
        """异步执行指令发布"""
        try:
            from unitree_webrtc_connect import SPORT_CMD, RTC_TOPIC

            # 步态切换需要通过 motion_switcher
            action_info = GO2_ACTIONS.get(action, {})
            mode = action_info.get("mode")

            if robot.connection and robot.connection.datachannel:
                pub_sub = robot.connection.datachannel.pub_sub

                if action == "NormalMode":
                    # 切回 normal 模式，恢复 Move 控制
                    await pub_sub.publish_request_new(
                        RTC_TOPIC["MOTION_SWITCHER"],
                        {"api_id": 1001, "parameter": {"name": "normal"}}
                    )
                    print(f"✅ {robot.name}: 已切回 normal 模式，Move 可用")
                    return

                if mode == "normal":
                    # Move 类命令需要 normal 模式，自动切回
                    await pub_sub.publish_request_new(
                        RTC_TOPIC["MOTION_SWITCHER"],
                        {"api_id": 1001, "parameter": {"name": "normal"}}
                    )
                    await asyncio.sleep(0.3)
                elif mode == "advanced":
                    # 先切到 advanced 模式，再发步态命令
                    await pub_sub.publish_request_new(
                        RTC_TOPIC["MOTION_SWITCHER"],
                        {"api_id": 1001, "parameter": {"name": "advanced"}}
                    )
                    await asyncio.sleep(0.3)

                cmd_map = {
                    "StandUp": {"api_id": SPORT_CMD["StandUp"]},
                    "StandDown": {"api_id": SPORT_CMD["StandDown"]},
                    "RecoveryStand": {"api_id": SPORT_CMD["RecoveryStand"]},
                    "BalanceStand": {"api_id": SPORT_CMD["BalanceStand"]},
                    "StopMove": {"api_id": SPORT_CMD["StopMove"]},
                    "Damp": {"api_id": SPORT_CMD["Damp"]},
                    "Move_Forward": {"api_id": SPORT_CMD["Move"], "parameter": {"x": 0.5, "y": 0.0, "z": 0.0}},
                    "Move_Backward": {"api_id": SPORT_CMD["Move"], "parameter": {"x": -0.5, "y": 0.0, "z": 0.0}},
                    "Move_Left": {"api_id": SPORT_CMD["Move"], "parameter": {"x": 0.0, "y": 0.5, "z": 0.0}},
                    "Move_Right": {"api_id": SPORT_CMD["Move"], "parameter": {"x": 0.0, "y": -0.5, "z": 0.0}},
                    "Turn_Left": {"api_id": SPORT_CMD["Move"], "parameter": {"x": 0.0, "y": 0.0, "z": 0.5}},
                    "Turn_Right": {"api_id": SPORT_CMD["Move"], "parameter": {"x": 0.0, "y": 0.0, "z": -0.5}},
                    "Dance1": {"api_id": SPORT_CMD["Dance1"]},
                    "Dance2": {"api_id": SPORT_CMD["Dance2"]},
                    "WiggleHips": {"api_id": SPORT_CMD["WiggleHips"]},
                    "Content": {"api_id": SPORT_CMD["Content"]},
                    "FingerHeart": {"api_id": SPORT_CMD["FingerHeart"]},
                    "FrontJump": {"api_id": SPORT_CMD["FrontJump"]},
                    "FrontPounce": {"api_id": SPORT_CMD["FrontPounce"]},
                    "Stretch": {"api_id": SPORT_CMD["Stretch"]},
                    "Sit": {"api_id": SPORT_CMD["Sit"]},
                    "RiseSit": {"api_id": SPORT_CMD["RiseSit"]},
                    "FrontFlip": {"api_id": SPORT_CMD["FrontFlip"]},
                    "BackFlip": {"api_id": SPORT_CMD["BackFlip"]},
                    "LeftFlip": {"api_id": SPORT_CMD["LeftFlip"]},
                    "Handstand": {"api_id": SPORT_CMD["Handstand"]},
                    "Bound": {"api_id": SPORT_CMD["Bound"]},
                    "Hello": {"api_id": SPORT_CMD["Hello"]},
                    "Pose": {"api_id": SPORT_CMD["Pose"]},
                    "Scrape": {"api_id": SPORT_CMD["Scrape"]},
                    "FreeWalk": {"api_id": SPORT_CMD["FreeWalk"]},
                    "ContinuousGait": {"api_id": SPORT_CMD["ContinuousGait"]},
                    "EconomicGait": {"api_id": SPORT_CMD["EconomicGait"]},
                    "MoonWalk": {"api_id": SPORT_CMD["MoonWalk"]},
                    "CrossStep": {"api_id": SPORT_CMD["CrossStep"]},
                }

                cmd = cmd_map.get(action)
                if not cmd:
                    print(f"⚠️ 未知动作 ID: {action}")
                    return

                await pub_sub.publish_request_new(RTC_TOPIC["SPORT_MOD"], cmd)
                print(f"✅ {robot.name}: 指令 {action} ({cmd['api_id']}) 已发出")
            else:
                print(f"❌ {robot.name}: 连接对象或 DataChannel 为空")

        except Exception as e:
            print(f"⚠️ 发送失败，原因: {e}")

    # ==================== 舞蹈序列相关方法 ====================

    def add_action_to_sequence(self):
        """添加动作到序列（时间轴样式）"""
        action_id = self.action_combo.currentData()
        duration = self.duration_spin.value()

        # 获取选中的设备编号
        selected_devices = []
        for i, cb in enumerate(self.device_checkboxes):
            if cb.isChecked():
                selected_devices.append(i + 1)

        dog_count = self.dog_count_spin.value()
        # 如果全选则存空列表（表示全部）
        if len(selected_devices) == dog_count:
            selected_devices = []

        step = ActionStep(action_id, duration, devices=selected_devices)
        self.action_sequence.append(step)

        action_name = GO2_ACTIONS[action_id]["name"]
        category = GO2_ACTIONS[action_id]["category"]

        # 设备显示文本
        if not selected_devices:
            device_text = "全部"
        else:
            device_text = ",".join([f"狗{d}" for d in selected_devices])

        item = QListWidgetItem()
        item.setText(f"[{category}] {action_name}  ⏱️ {duration}秒  🐕{device_text}")

        color_map = {
            "基础": "#4CAF50",    
            "运动": "#2196F3",    
            "舞蹈": "#FF9800",    
            "特技": "#F44336",    
            "交互": "#9C27B0",    
            "步态": "#00BCD4",    
        }
        bg_color = color_map.get(category, "#999999")

        item.setBackground(QColor(bg_color))
        item.setForeground(QColor("#000000"))

        self.timeline_list.addItem(item)
        self.update_time_ruler()
        self.log(f"添加动作: {action_name} ({duration}秒)")

    def add_parallel_to_sequence(self):
        """通过对话框添加并行动作组"""
        dog_count = self.dog_count_spin.value()
        dialog = AddParallelDialog(dog_count, self)
        if dialog.exec_() != QDialog.Accepted:
            return

        group = dialog.get_parallel_group()
        if not group or len(group.steps) < 1:
            QMessageBox.warning(self, "无效", "请至少为一只狗选择动作")
            return

        self.action_sequence.append(group)
        self._add_parallel_item_to_list(group)
        self.update_time_ruler()
        self.log(f"添加并行组: {len(group.steps)} 个动作同时执行")

    def _add_parallel_item_to_list(self, group: ParallelGroup):
        """将并行组添加到时间轴列表显示"""
        item = QListWidgetItem()
        item.setText(f"[并行] {group.action_name}  ⏱️{group.duration}秒")
        item.setBackground(QColor("#FFD700"))
        item.setForeground(QColor("#000000"))
        self.timeline_list.addItem(item)

    def merge_selected(self):
        """将选中的多个动作合并为并行组"""
        selected_rows = sorted([idx.row() for idx in self.timeline_list.selectedIndexes()])
        if len(selected_rows) < 2:
            QMessageBox.warning(self, "选择不足", "请选中至少 2 个动作进行合并")
            return

        # 收集选中的步骤
        steps_to_merge = []
        for row in selected_rows:
            item = self.action_sequence[row]
            if isinstance(item, ParallelGroup):
                steps_to_merge.extend(item.steps)
            else:
                steps_to_merge.append(item)

        group = ParallelGroup(steps_to_merge)

        # 从后往前删除选中项
        for row in reversed(selected_rows):
            self.timeline_list.takeItem(row)
            self.action_sequence.pop(row)

        # 在最小行位置插入并行组
        insert_pos = selected_rows[0]
        self.action_sequence.insert(insert_pos, group)

        item = QListWidgetItem()
        item.setText(f"[并行] {group.action_name}  ⏱️{group.duration}秒")
        item.setBackground(QColor("#FFD700"))
        item.setForeground(QColor("#000000"))
        self.timeline_list.insertItem(insert_pos, item)

        self.update_time_ruler()
        self.log(f"已合并 {len(selected_rows)} 个动作为并行组")

    def split_selected(self):
        """将选中的并行组拆分为独立动作"""
        selected_rows = sorted([idx.row() for idx in self.timeline_list.selectedIndexes()])
        if len(selected_rows) != 1:
            QMessageBox.warning(self, "选择错误", "请选中一个并行组进行拆分")
            return

        row = selected_rows[0]
        item = self.action_sequence[row]
        if not isinstance(item, ParallelGroup):
            QMessageBox.warning(self, "非并行组", "选中的不是并行组，无法拆分")
            return

        # 删除并行组
        self.timeline_list.takeItem(row)
        self.action_sequence.pop(row)

        # 在原位置插入各个独立动作
        for i, step in enumerate(item.steps):
            self.action_sequence.insert(row + i, step)

            action_name = step.action_name
            category = GO2_ACTIONS.get(step.action_id, {}).get("category", "其他")
            device_text = ",".join([f"狗{d}" for d in step.devices]) if step.devices else "全部"

            list_item = QListWidgetItem()
            list_item.setText(f"[{category}] {action_name}  ⏱️{step.duration}秒  🐕{device_text}")
            color_map = {
                "基础": "#4CAF50", "运动": "#2196F3", "舞蹈": "#FF9800",
                "特技": "#F44336", "交互": "#9C27B0", "步态": "#00BCD4",
            }
            list_item.setBackground(QColor(color_map.get(category, "#999999")))
            list_item.setForeground(QColor("#000000"))
            self.timeline_list.insertItem(row + i, list_item)

        self.update_time_ruler()
        self.log(f"已拆分并行组为 {len(item.steps)} 个独立动作")

    def remove_action_from_sequence(self):
        """从序列删除动作"""
        current_row = self.timeline_list.currentRow()
        if current_row >= 0:
            self.timeline_list.takeItem(current_row)
            self.action_sequence.pop(current_row)
            self.update_time_ruler()
            self.log(f"删除第 {current_row + 1} 个动作")

    def clear_sequence(self):
        """清空序列"""
        reply = QMessageBox.question(
            self, "确认清空", "确定要清空所有动作吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.timeline_list.clear()
            self.action_sequence.clear()
            self.update_time_ruler()
            self.log("序列已清空")

    def update_time_ruler(self):
        """更新时间刻度"""
        while self.time_ruler_layout.count():
            child = self.time_ruler_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        total_duration = sum(step.duration for step in self.action_sequence)

        for i in range(0, int(total_duration) + 10, 5):
            label = QLabel(f"{i}s")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font-size: 10px; color: #666;")
            self.time_ruler_layout.addWidget(label)

        self.time_ruler_layout.addStretch()

    def save_sequence(self):
        """保存序列"""
        if not self.action_sequence:
            QMessageBox.warning(self, "序列为空", "请先添加动作到序列")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存序列", "", "JSON Files (*.json)"
        )

        if file_path:
            sequence_data = {
                "dog_count": self.dog_count_spin.value(),
                "steps": [step.to_dict() for step in self.action_sequence]
            }
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(sequence_data, f, indent=2, ensure_ascii=False)
                self.log(f"序列已保存: {file_path}")
                QMessageBox.information(self, "保存成功", f"已保存 {len(self.action_sequence)} 个动作")
            except Exception as e:
                QMessageBox.critical(self, "保存失败", f"错误: {e}")

    def load_sequence(self):
        """加载序列"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "加载序列", "", "JSON Files (*.json)"
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)

                # 兼容旧格式（纯列表）和新格式（带 dog_count 的字典）
                if isinstance(raw_data, list):
                    steps_data = raw_data
                    dog_count = 2
                else:
                    steps_data = raw_data.get("steps", [])
                    dog_count = raw_data.get("dog_count", 2)

                self.dog_count_spin.setValue(dog_count)
                self.timeline_list.clear()
                self.action_sequence.clear()

                for step_data in steps_data:
                    if "parallel" in step_data:
                        group = ParallelGroup.from_dict(step_data)
                        self.action_sequence.append(group)
                        self._add_parallel_item_to_list(group)
                    else:
                        step = ActionStep.from_dict(step_data)
                        self.action_sequence.append(step)

                        action_name = GO2_ACTIONS.get(step.action_id, {}).get("name", step.action_id)
                        category = GO2_ACTIONS.get(step.action_id, {}).get("category", "其他")

                        if not step.devices:
                            device_text = "全部"
                        else:
                            device_text = ",".join([f"狗{d}" for d in step.devices])

                        item = QListWidgetItem()
                        item.setText(f"[{category}] {action_name}  ⏱️ {step.duration}秒  🐕{device_text}")

                        color_map = {
                            "基础": "#4CAF50",
                            "运动": "#2196F3",
                            "舞蹈": "#FF9800",
                            "特技": "#F44336",
                            "交互": "#9C27B0",
                            "步态": "#00BCD4",
                        }
                        bg_color = color_map.get(category, "#999999")
                        item.setBackground(QColor(bg_color))
                        item.setForeground(QColor("#000000"))

                        self.timeline_list.addItem(item)

                self.update_time_ruler()
                self.log(f"序列已加载: {len(self.action_sequence)} 个动作, {dog_count}只狗")
                QMessageBox.information(self, "加载成功", f"已加载 {len(self.action_sequence)} 个动作")
            except Exception as e:
                QMessageBox.critical(self, "加载失败", f"错误: {e}")

    def execute_sequence(self):
        """执行序列"""
        if not self.action_sequence:
            QMessageBox.warning(self, "序列为空", "请先添加动作到序列")
            return

        dialog = ExecuteModeDialog(self.robots, self)
        if dialog.exec_() != QDialog.Accepted:
            return

        mode = dialog.get_execution_mode()
        real_robots = dialog.get_selected_real_robots()
        use_simulator = dialog.use_simulator()

        if not real_robots and not use_simulator:
            QMessageBox.warning(self, "未选择", "请至少选择一种执行方式：真实设备或模拟器")
            return

        total_duration = sum(step.duration for step in self.action_sequence)

        summary = f"执行模式: {mode}\n"
        summary += f"动作数量: {len(self.action_sequence)} 个\n"
        summary += f"总时长: 约 {total_duration:.0f} 秒\n\n"

        if real_robots:
            summary += f"真实设备: {', '.join([r.name for r in real_robots])}\n"
        if use_simulator:
            summary += f"模拟器: 是"

        reply = QMessageBox.question(
            self, "确认执行", summary,
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.execute_sequence_btn.setEnabled(False)
            self.stop_sequence_btn.setEnabled(True)
            self.stop_preset_btn.setEnabled(True)
            self.progress_bar.setValue(0)

            self.dance_thread = DanceSequenceThread(
                real_robots,
                self.action_sequence,
                use_simulator=use_simulator,
                global_loop=self.global_loop
            )
            self.dance_thread.progress.connect(self.log)

            if use_simulator and self.simulator_window:
                self.dance_thread.simulator_action.connect(
                    self.simulator_window.simulator.execute_action
                )

            self.dance_thread.current_action.connect(self.on_action_changed)
            self.dance_thread.progress_percent.connect(self.on_progress_update)
            self.dance_thread.action_index.connect(self.on_action_index_changed)
            self.dance_thread.finished.connect(self.on_sequence_finished)
            self.dance_thread.start()

    def execute_preset_dance(self):
        """执行预设舞蹈"""
        selected_robots = [r for r in self.robots if r.connected and r.selected]
        if not selected_robots:
            QMessageBox.warning(self, "未选择", "请先勾选要控制的设备")
            return

        sequence = [ActionStep.from_dict(step) for step in PRESET_DANCE_3MIN]

        reply = QMessageBox.question(
            self, "确认执行",
            f"确定要执行3分钟舞蹈吗？\n共 {len(sequence)} 个动作，总时长约 180 秒",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.execute_preset_btn.setEnabled(False)
            self.execute_sequence_btn.setEnabled(False)
            self.stop_preset_btn.setEnabled(True)
            self.stop_sequence_btn.setEnabled(True)

            self.dance_thread = DanceSequenceThread(
                selected_robots, 
                sequence, 
                use_simulator=False, 
                global_loop=self.global_loop
            )
            self.dance_thread.progress.connect(self.log)
            self.dance_thread.current_action.connect(self.on_action_changed)
            self.dance_thread.finished.connect(self.on_sequence_finished)
            self.dance_thread.start()

    def stop_sequence(self):
        """停止序列"""
        if self.dance_thread and self.dance_thread.isRunning():
            self.dance_thread.stop()
            self.log("正在停止序列...")
            self.current_action_label.setText("停止中...")

            if not self.dance_thread.wait(2000):
                self.dance_thread.terminate()
                self.log("⚠ 序列已强制停止")

            try:
                self.dance_thread.finished.disconnect(self.on_sequence_finished)
            except:
                pass

            self.execute_sequence_btn.setEnabled(True)
            self.execute_preset_btn.setEnabled(True)
            self.stop_sequence_btn.setEnabled(False)
            self.stop_preset_btn.setEnabled(False)
            self.current_action_label.setText("已停止")
            self.log("序列已停止")

            self.dance_thread = None

    def on_action_changed(self, action_text: str):
        """当前动作改变"""
        self.current_action_label.setText(action_text)

    def on_progress_update(self, percent: int):
        """更新进度条"""
        self.progress_bar.setValue(percent)
        self.progress_bar.setFormat(f"执行进度: {percent}%")

    def on_action_index_changed(self, index: int):
        """高亮当前执行的动作"""
        for i in range(self.timeline_list.count()):
            item = self.timeline_list.item(i)
            item.setSelected(False)

        if 0 <= index < self.timeline_list.count():
            current_item = self.timeline_list.item(index)
            current_item.setSelected(True)
            self.timeline_list.scrollToItem(current_item)

    def on_sequence_finished(self):
        """序列执行完成"""
        self.execute_sequence_btn.setEnabled(True)
        self.execute_preset_btn.setEnabled(True)
        self.stop_sequence_btn.setEnabled(False)
        self.stop_preset_btn.setEnabled(False)
        self.current_action_label.setText("完成")
        self.progress_bar.setFormat("完成")
        self.progress_bar.setValue(100)

        for i in range(self.timeline_list.count()):
            item = self.timeline_list.item(i)
            item.setSelected(False)

        self.log("=" * 60)

    def log(self, message: str):
        """添加日志"""
        if self.log_text is None:
            print(f"[LOG] {message}")
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    def show_info(self):
        """显示信息"""
        self.log("=" * 60)
        self.log("GO2 机器狗控制面板 v4.1 - 修复联机异步Bug")
        self.log("=" * 60)

        if GO2_AVAILABLE:
            self.log("✓ GO2 库已加载，支持完整功能")
            self.log("🟢 模拟器已集成，可离线使用")
        else:
            self.log("✗ GO2 库不可用，仅支持扫描")
        self.log("=" * 60)

    def open_simulator(self):
        """打开模拟器窗口"""
        if self.simulator_window is None:
            try:
                from go2_simulator import GO2SimulatorWindow
                self.simulator_window = GO2SimulatorWindow()
                self.simulator_window.simulator.action_executed.connect(self.on_simulator_action)
                self.log("✓ 模拟器已启动")
            except Exception as e:
                self.log(f"✗ 模拟器启动失败: {e}")
                QMessageBox.critical(self, "错误", f"模拟器启动失败: {e}")
                return

        self.simulator_window.show()
        self.simulator_window.raise_()
        self.simulator_window.activateWindow()

    def on_simulator_action(self, robot_name: str, action: str, duration: float):
        """模拟器动作回调"""
        self.log(f"🟢 模拟器[{robot_name}]: {action} ({duration}秒)")

    def closeEvent(self, event):
        """关闭事件"""
        if self.simulator_window:
            self.simulator_window.close()

        if self.dance_thread and self.dance_thread.isRunning():
            self.dance_thread.stop()
            self.dance_thread.wait()

        if self.robots:
            self.disconnect_all()

        event.accept()

# ============================================================================
# 主程序
# ============================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GO2ControlPanel()
    window.show()
    sys.exit(app.exec_())