#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GO2 AIR 动作模拟器
用于在没有真实机器狗的情况下模拟动作执行
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QGroupBox, QCheckBox, QTextEdit,
    QSplitter, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPolygonF
from PyQt5.QtCore import QPointF
import random
from datetime import datetime


class GO2DogWidget(QWidget):
    """单只机器狗的可视化组件"""

    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.current_action = "待机"
        self.current_color = QColor(200, 200, 200)  # 默认灰色
        self.action_progress = 0.0
        self.is_executing = False

        # 动画相关
        self.scale_factor = 1.0
        self.rotation_angle = 0.0
        self.jump_offset = 0.0

        self.setMinimumSize(150, 150)
        self.setMaximumSize(200, 200)

    def set_action(self, action: str, color: QColor):
        """设置当前动作"""
        self.current_action = action
        self.current_color = color
        self.is_executing = True
        self.action_progress = 0.0
        self.update()

    def update_progress(self, progress: float):
        """更新动作进度"""
        self.action_progress = progress
        self.update()

    def complete_action(self):
        """完成动作"""
        self.is_executing = False
        self.action_progress = 1.0
        QTimer.singleShot(500, self.reset_to_idle)

    def reset_to_idle(self):
        """重置为待机状态"""
        self.current_action = "待机"
        self.current_color = QColor(200, 200, 200)
        self.is_executing = False
        self.action_progress = 0.0
        self.scale_factor = 1.0
        self.rotation_angle = 0.0
        self.jump_offset = 0.0
        self.update()

    def paintEvent(self, event):
        """绘制机器狗"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 背景圆
        rect = self.rect().adjusted(10, 10, -10, -10)
        center = rect.center()

        # 绘制背景圆（根据动作改变大小）
        bg_rect = rect
        if self.is_executing:
            # 执行时稍微放大
            scale = 1.0 + 0.1 * (1 - self.action_progress)
            painter.save()
            painter.translate(center)
            painter.scale(scale, scale)
            painter.translate(-center)
            bg_rect = rect.adjusted(-10, -10, 10, 10)

        # 背景渐变
        painter.setBrush(QBrush(self.current_color))
        painter.setPen(QPen(QColor(50, 50, 50), 2))
        painter.drawEllipse(bg_rect)

        if self.is_executing:
            painter.restore()

        # 绘制机器狗图标（简化版）
        painter.setPen(QPen(QColor(255, 255, 255), 3))
        painter.setBrush(QBrush(QColor(255, 255, 255, 200)))

        # 身体
        body_rect = bg_rect.adjusted(20, 40, -20, -40)
        painter.drawRoundRect(body_rect, 20, 20)

        # 头部
        head_rect = body_rect.adjusted(10, -25, 10, -15)
        painter.drawEllipse(head_rect)

        # 眼睛
        eye_color = QColor(0, 200, 255) if not self.is_executing else QColor(255, 200, 0)
        painter.setBrush(QBrush(eye_color))
        painter.setPen(Qt.NoPen)

        left_eye = head_rect.adjusted(10, 10, -25, -5)
        painter.drawEllipse(left_eye)

        right_eye = head_rect.adjusted(25, 10, 0, -5)
        painter.drawEllipse(right_eye)

        # 腿（四条）
        painter.setBrush(QBrush(QColor(100, 100, 100)))
        painter.setPen(QPen(QColor(50, 50, 50), 2))

        leg_width = 8
        leg_height = 20

        # 前左腿
        fl_rect = body_rect.adjusted(5, 10, -30, -5)
        painter.drawRoundRect(fl_rect, 5, 5)

        # 前右腿
        fr_rect = body_rect.adjusted(35, 10, 0, -5)
        painter.drawRoundRect(fr_rect, 5, 5)

        # 后左腿
        bl_rect = body_rect.adjusted(5, 25, -30, -20)
        painter.drawRoundRect(bl_rect, 5, 5)

        # 后右腿
        br_rect = body_rect.adjusted(35, 25, 0, -20)
        painter.drawRoundRect(br_rect, 5, 5)

        # 进度条
        if self.is_executing and self.action_progress > 0:
            progress_rect = bg_rect.adjusted(20, bg_rect.height() - 25, -20, -15)
            painter.setBrush(QBrush(QColor(0, 0, 0, 150)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundRect(progress_rect, 5, 5)

            # 进度填充
            fill_width = progress_rect.width() * self.action_progress
            fill_rect = progress_rect.adjusted(0, 0, -(progress_rect.width() - fill_width), 0)
            painter.setBrush(QBrush(QColor(0, 255, 100)))
            painter.drawRoundRect(fill_rect, 5, 5)

        # 名称和状态文本
        painter.setPen(QColor(0, 0, 0))
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.drawText(bg_rect.adjusted(0, 0, 0, -40), Qt.AlignCenter, self.name)

        painter.setFont(QFont("Arial", 8))
        painter.drawText(bg_rect.adjusted(0, 25, 0, -20), Qt.AlignCenter, self.current_action)


class GO2SimulatorPanel(QWidget):
    """GO2 模拟器主面板"""

    action_executed = pyqtSignal(str, str, float)  # robot_name, action, duration

    def __init__(self):
        super().__init__()
        self.dog_widgets = {}  # name -> GO2DogWidget
        self.selected_dogs = set()  # 选中的机器狗
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # 标题
        title = QLabel("🤖 GO2 AIR 动作模拟器")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 控制面板
        control_group = QGroupBox("模拟器控制")
        control_layout = QHBoxLayout(control_group)

        add_dog_btn = QPushButton("➕ 添加模拟狗")
        add_dog_btn.clicked.connect(self.add_simulated_dog)
        control_layout.addWidget(add_dog_btn)

        remove_dog_btn = QPushButton("➖ 移除选中")
        remove_dog_btn.clicked.connect(self.remove_selected_dogs)
        control_layout.addWidget(remove_dog_btn)

        clear_all_btn = QPushButton("🗑️ 清空全部")
        clear_all_btn.clicked.connect(self.clear_all_dogs)
        control_layout.addWidget(clear_all_btn)

        layout.addWidget(control_group)

        # 机器狗显示区域
        dogs_group = QGroupBox("模拟机器狗")
        dogs_layout = QVBoxLayout(dogs_group)

        # 滚动区域
        from PyQt5.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(300)

        self.dogs_container = QWidget()
        self.dogs_layout = QHBoxLayout(self.dogs_container)
        self.dogs_layout.setAlignment(Qt.AlignLeft)
        scroll.setWidget(self.dogs_container)

        dogs_layout.addWidget(scroll)
        layout.addWidget(dogs_group)

        # 动作日志
        log_group = QGroupBox("动作执行日志")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_group)

        # 添加初始的3只模拟狗
        for i in range(1, 4):
            self.add_dog_widget(f"模拟狗-{i}")

    def add_dog_widget(self, name: str):
        """添加机器狗组件"""
        if name in self.dog_widgets:
            return

        # 创建复选框和狗组件的容器
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(5, 5, 5, 5)

        # 复选框
        checkbox = QCheckBox(name)
        checkbox.setChecked(True)
        checkbox.stateChanged.connect(lambda state, n=name: self.on_dog_selected(n, state))
        container_layout.addWidget(checkbox)

        # 狗组件
        dog_widget = GO2DogWidget(name)
        container_layout.addWidget(dog_widget)

        self.dogs_layout.addWidget(container)
        self.dog_widgets[name] = {
            'widget': dog_widget,
            'checkbox': checkbox,
            'container': container
        }
        self.selected_dogs.add(name)

        self.log(f"添加模拟狗: {name}")

    def add_simulated_dog(self):
        """添加新的模拟狗"""
        count = len(self.dog_widgets) + 1
        name = f"模拟狗-{count}"
        self.add_dog_widget(name)

    def remove_selected_dogs(self):
        """移除选中的狗"""
        to_remove = [name for name in self.selected_dogs]
        for name in to_remove:
            self.remove_dog(name)

    def clear_all_dogs(self):
        """清空所有狗"""
        for name in list(self.dog_widgets.keys()):
            self.remove_dog(name)

    def remove_dog(self, name: str):
        """移除单个狗"""
        if name not in self.dog_widgets:
            return

        dog_info = self.dog_widgets[name]
        self.dogs_layout.removeWidget(dog_info['container'])
        dog_info['container'].deleteLater()
        del self.dog_widgets[name]
        self.selected_dogs.discard(name)

        self.log(f"移除模拟狗: {name}")

    def on_dog_selected(self, name: str, state: int):
        """狗选择状态改变"""
        if state == Qt.Checked:
            self.selected_dogs.add(name)
        else:
            self.selected_dogs.discard(name)

    def execute_action(self, action_name: str, duration: float):
        """执行动作（所有选中的狗）"""
        print(f"\n[模拟器] ========================================")
        print(f"[模拟器] 收到动作: {action_name}, 时长: {duration}秒")
        print(f"[模拟器] 当前选中的狗: {list(self.selected_dogs)}")
        print(f"[模拟器] ========================================\n")

        # 动作颜色映射（扩展版）
        color_map = {
            "站立": QColor(76, 175, 80),      # 绿色
            "蹲下": QColor(33, 150, 243),     # 蓝色
            "打招呼": QColor(255, 193, 7),    # 黄色
            "停止": QColor(128, 128, 128),    # 灰色
            "前进": QColor(156, 39, 176),     # 紫色
            "后退": QColor(156, 39, 176),
            "左转": QColor(255, 87, 34),      # 橙色
            "右转": QColor(255, 87, 34),
            "Turn_Left": QColor(255, 87, 34),
            "Turn_Right": QColor(255, 87, 34),
            "舞蹈": QColor(233, 30, 99),      # 粉色
            "Dance1": QColor(233, 30, 99),
            "Dance2": QColor(233, 30, 99),
            "Dance3": QColor(233, 30, 99),
            "Dance4": QColor(233, 30, 99),
            "Dance5": QColor(233, 30, 99),
            "跳跃": QColor(255, 0, 0),        # 红色
            "Jump": QColor(255, 0, 0),
            "伸展": QColor(0, 200, 255),      # 青色
            "Stretch": QColor(0, 200, 255),
            "Sit": QColor(100, 150, 200),
            "HandStand": QColor(200, 100, 50),
            "Roll": QColor(150, 100, 50),
            "Flip": QColor(200, 50, 50),
            "Beg": QColor(255, 150, 100),
            "ShakeHand": QColor(255, 180, 100),
            "HighFive": QColor(255, 200, 100),
            "Trot": QColor(100, 200, 150),
            "Pace": QColor(100, 180, 150),
            "Bound": QColor(50, 200, 150),
            "Gallop": QColor(50, 180, 200),
        }

        # 根据动作名称选择颜色
        color = QColor(100, 100, 100)  # 默认灰色
        for key, c in color_map.items():
            if key in action_name or action_name in key:
                color = c
                print(f"[模拟器] 匹配颜色: {key} -> {color.name()}")
                break

        # 对所有选中的狗执行动作
        executed = []
        for name in self.selected_dogs:
            dog_widget = self.dog_widgets[name]['widget']
            dog_widget.set_action(action_name, color)
            executed.append(name)
            print(f"[模拟器] {name} 开始执行: {action_name}")

            # 模拟进度动画
            self.animate_action(dog_widget, duration)

        if executed:
            self.log(f"执行动作: {action_name} ({duration}秒) - {', '.join(executed)}")
            print(f"[模拟器] 已发送给 {len(executed)} 只模拟狗")

            # 发送信号给主窗口（用于真实执行）
            for name in executed:
                self.action_executed.emit(name, action_name, duration)
                print(f"[模拟器] 发送信号: action_executed('{name}', '{action_name}', {duration})")
        else:
            print(f"[模拟器] ⚠️ 没有选中的模拟狗！")
            self.log("⚠️ 没有选中的模拟狗")

    def animate_action(self, dog_widget: GO2DogWidget, duration: float):
        """动作进度动画"""
        total_steps = 20
        step_duration = (duration * 1000) / total_steps  # 毫秒

        for i in range(total_steps + 1):
            QTimer.singleShot(int(i * step_duration),
                           lambda progress=i/total_steps, dw=dog_widget:
                           dw.update_progress(progress))

        # 动作完成
        QTimer.singleShot(int(duration * 1000),
                        lambda dw=dog_widget: dw.complete_action())

    def log(self, message: str):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")


class GO2SimulatorWindow(QWidget):
    """独立的模拟器窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GO2 AIR 动作模拟器")
        self.setGeometry(100, 100, 800, 600)

        layout = QVBoxLayout(self)

        # 创建模拟器面板
        self.simulator = GO2SimulatorPanel()
        layout.addWidget(self.simulator)

        # 测试按钮
        test_group = QGroupBox("快速测试")
        test_layout = QHBoxLayout(test_group)

        test_actions = [
            ("站立", 2),
            ("蹲下", 2),
            ("打招呼", 3),
            ("前进", 2),
            ("舞蹈", 5),
            ("跳跃", 3),
        ]

        for action, duration in test_actions:
            btn = QPushButton(action)
            btn.clicked.connect(lambda checked, a=action, d=duration:
                               self.simulator.execute_action(a, d))
            test_layout.addWidget(btn)

        layout.addWidget(test_group)


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = GO2SimulatorWindow()
    window.show()
    sys.exit(app.exec_())
