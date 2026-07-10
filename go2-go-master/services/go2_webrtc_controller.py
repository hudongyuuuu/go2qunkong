#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
services/go2_webrtc_controller.py
GO2 WebRTC 机器人控制器 - 使用 go2-webrtc-driver 库
支持局域网 (LocalSTA) 和热点模式 (LocalAP)
"""

import asyncio
import logging
import threading
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTimer

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """连接状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class Go2Robot:
    """GO2 机器人数据"""
    id: str
    name: str
    ip: str
    port: int = 9991
    state: ConnectionState = ConnectionState.DISCONNECTED
    battery_level: float = 0.0
    last_command: str = ""
    last_seen: Optional[datetime] = None
    error_message: str = ""

    # WebRTC 连接对象
    webrtc_connection: Optional[object] = field(default=None, repr=False)

    # 命令队列
    command_queue: List[dict] = field(default_factory=list)

    # 重连配置
    auto_reconnect: bool = True
    max_retries: int = 3
    retry_count: int = 0
    reconnect_interval: int = 5  # 秒

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'ip': self.ip,
            'port': self.port,
            'state': self.state.value,
            'battery_level': self.battery_level,
            'last_command': self.last_command,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'error_message': self.error_message,
        }


class WebRTCAPI:
    """
    GO2 WebRTC API 封装

    使用 go2_webrtc_driver 库进行连接和控制
    """

    @staticmethod
    async def connect(ip: str, connection_method: str = "LocalSTA") -> Optional[object]:
        """
        连接到 GO2 机器人

        Args:
            ip: 机器人 IP 地址
            connection_method: 连接方式 (LocalSTA, LocalAP, Remote)

        Returns:
            WebRTC 连接对象
        """
        try:
            from go2_webrtc_driver.webrtc_driver import Go2WebRTCConnection
            from go2_webrtc_driver.constants import WebRTCConnectionMethod

            # 根据连接方式选择枚举
            if connection_method == "LocalSTA":
                method = WebRTCConnectionMethod.LocalSTA
            elif connection_method == "LocalAP":
                method = WebRTCConnectionMethod.LocalAP
            elif connection_method == "Remote":
                method = WebRTCConnectionMethod.Remote
            else:
                method = WebRTCConnectionMethod.LocalSTA

            # 创建连接对象
            connection = Go2WebRTCConnection(
                connectionMethod=method,
                ip=ip
            )

            # 执行连接
            await connection.connect()

            if connection.isConnected:
                logger.info(f"成功连接到 {ip}")
                return connection
            else:
                logger.error(f"连接失败: {ip}")
                return None

        except ImportError:
            logger.error("go2_webrtc_driver 未安装，请运行: pip install go2-webrtc-connect")
            return None
        except Exception as e:
            logger.error(f"连接出错: {e}")
            return None

    @staticmethod
    async def disconnect(connection: object) -> bool:
        """断开连接"""
        try:
            await connection.disconnect()
            return True
        except Exception as e:
            logger.error(f"断开连接出错: {e}")
            return False

    @staticmethod
    async def send_command(connection: object, command: str, params: dict = None) -> bool:
        """
        发送命令到机器人

        支持的命令：
        - stand_up: 站立
        - stand_down: 蹲下
        - hello: 挥手
        - move: 移动
        - stop: 停止
        """
        try:
            if not connection or not connection.isConnected:
                logger.error("未连接到机器人")
                return False

            # 根据命令类型调用相应 API
            datachannel = connection.datachannel

            if command == "stand_up":
                await datachannel.send_api_command("StandUp", {})
            elif command == "stand_down":
                await datachannel.send_api_command("StandDown", {})
            elif command == "hello":
                await datachannel.send_api_command("Hello", {})
            elif command == "stop":
                await datachannel.send_api_command("StopMove", {})
            elif command == "move":
                # 移动命令需要参数
                params = params or {}
                await datachannel.send_api_command("Move", params)
            else:
                logger.warning(f"未知命令: {command}")
                return False

            logger.info(f"命令已发送: {command}")
            return True

        except Exception as e:
            logger.error(f"发送命令出错: {e}")
            return False

    @staticmethod
    def get_robot_info(connection: object) -> Optional[dict]:
        """获取机器人信息"""
        try:
            if not connection or not connection.isConnected:
                return None

            # 这里可以根据 API 获取机器人状态
            # 例如电量、模式等
            return {
                'connected': connection.isConnected,
                'battery': 0,  # 需要从 API 获取
                'mode': 'unknown'
            }
        except Exception as e:
            logger.error(f"获取机器人信息出错: {e}")
            return None


class Go2WebRTCController(QObject):
    """
    GO2 WebRTC 机器人控制器

    特性：
    - 支持多机器人同时连接
    - 自动重连机制
    - 命令队列管理
    - 连接保活
    - PyQt5 信号集成
    """

    # 信号
    robot_connected = pyqtSignal(str)  # robot_id
    robot_disconnected = pyqtSignal(str)  # robot_id
    robot_state_changed = pyqtSignal(str, dict)  # robot_id, state_dict
    connection_error = pyqtSignal(str, str)  # robot_id, error_message
    command_sent = pyqtSignal(str, str)  # robot_id, command
    command_failed = pyqtSignal(str, str, str)  # robot_id, command, error

    def __init__(self):
        super().__init__()

        # 机器人存储
        self.robots: Dict[str, Go2Robot] = {}

        # 事件循环（在单独线程中运行）
        self._event_loop = None
        self._event_loop_thread = None
        self._running = False

        # 启动事件循环
        self._start_event_loop()

        # 连接保活定时器
        self._keepalive_timer = QTimer()
        self._keepalive_timer.timeout.connect(self._keepalive)
        self._keepalive_timer.start(30000)  # 每 30 秒检查一次

    def _start_event_loop(self):
        """在后台线程启动事件循环"""
        def run_loop():
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)
            self._running = True
            self._event_loop.run_forever()

        self._event_loop_thread = threading.Thread(target=run_loop, daemon=True)
        self._event_loop_thread.start()

        # 等待事件循环启动
        while self._event_loop is None:
            time.sleep(0.01)

        logger.info("事件循环已启动")

    def _run_async(self, coro):
        """在事件循环中运行协程"""
        if not self._event_loop:
            logger.error("事件循环未启动")
            return None

        future = asyncio.run_coroutine_threadsafe(coro, self._event_loop)

        # 可以选择等待结果或立即返回
        return future

    def add_robot(self, robot_id: str, name: str, ip: str, port: int = 9991,
                  auto_reconnect: bool = True) -> bool:
        """
        添加机器人

        Args:
            robot_id: 机器人唯一 ID
            name: 显示名称
            ip: IP 地址
            port: 端口号（默认 9991）
            auto_reconnect: 是否自动重连

        Returns:
            是否成功添加
        """
        if robot_id in self.robots:
            logger.warning(f"机器人 {robot_id} 已存在")
            return False

        robot = Go2Robot(
            id=robot_id,
            name=name,
            ip=ip,
            port=port,
            auto_reconnect=auto_reconnect
        )

        self.robots[robot_id] = robot
        logger.info(f"添加机器人: {name} ({robot_id}) @ {ip}:{port}")

        return True

    def remove_robot(self, robot_id: str) -> bool:
        """
        移除机器人

        Args:
            robot_id: 机器人 ID

        Returns:
            是否成功移除
        """
        if robot_id not in self.robots:
            logger.warning(f"机器人 {robot_id} 不存在")
            return False

        # 先断开连接
        robot = self.robots[robot_id]
        if robot.state == ConnectionState.CONNECTED:
            self.disconnect_robot(robot_id)

        del self.robots[robot_id]
        logger.info(f"移除机器人: {robot_id}")

        return True

    def connect_robot(self, robot_id: str) -> bool:
        """
        连接机器人

        Args:
            robot_id: 机器人 ID

        Returns:
            是否开始连接
        """
        if robot_id not in self.robots:
            logger.error(f"机器人 {robot_id} 不存在")
            return False

        robot = self.robots[robot_id]

        # 如果已连接，直接返回
        if robot.state == ConnectionState.CONNECTED:
            logger.info(f"机器人 {robot_id} 已连接")
            return True

        # 更新状态
        robot.state = ConnectionState.CONNECTING
        robot.error_message = ""
        self.robot_state_changed.emit(robot_id, robot.to_dict())

        # 在后台执行连接
        self._run_async(self._connect_robot_async(robot))

        return True

    async def _connect_robot_async(self, robot: Go2Robot):
        """异步连接机器人"""
        try:
            logger.info(f"正在连接 {robot.name} ({robot.ip})...")

            # 连接
            connection = await WebRTCAPI.connect(robot.ip)

            if connection and connection.isConnected:
                # 更新状态
                robot.webrtc_connection = connection
                robot.state = ConnectionState.CONNECTED
                robot.last_seen = datetime.now()
                robot.retry_count = 0

                self.robot_connected.emit(robot.id)
                self.robot_state_changed.emit(robot.id, robot.to_dict())

                logger.info(f"✓ 连接成功: {robot.name}")
            else:
                # 连接失败
                robot.state = ConnectionState.ERROR
                robot.error_message = "连接失败"

                self.connection_error.emit(robot.id, "连接失败")
                self.robot_state_changed.emit(robot.id, robot.to_dict())

                # 尝试重连
                if robot.auto_reconnect and robot.retry_count < robot.max_retries:
                    robot.retry_count += 1
                    logger.info(f"尝试重连 ({robot.retry_count}/{robot.max_retries})...")

                    await asyncio.sleep(robot.reconnect_interval)
                    await self._connect_robot_async(robot)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"连接出错: {error_msg}")

            robot.state = ConnectionState.ERROR
            robot.error_message = error_msg

            self.connection_error.emit(robot.id, error_msg)
            self.robot_state_changed.emit(robot.id, robot.to_dict())

    def disconnect_robot(self, robot_id: str) -> bool:
        """
        断开机器人连接

        Args:
            robot_id: 机器人 ID

        Returns:
            是否开始断开
        """
        if robot_id not in self.robots:
            return False

        robot = self.robots[robot_id]

        if robot.state != ConnectionState.CONNECTED:
            logger.warning(f"机器人 {robot_id} 未连接")
            return False

        # 在后台执行断开
        self._run_async(self._disconnect_robot_async(robot))

        return True

    async def _disconnect_robot_async(self, robot: Go2Robot):
        """异步断开机器人"""
        try:
            if robot.webrtc_connection:
                await WebRTCAPI.disconnect(robot.webrtc_connection)
                robot.webrtc_connection = None

            robot.state = ConnectionState.DISCONNECTED
            robot.retry_count = 0

            self.robot_disconnected.emit(robot.id)
            self.robot_state_changed.emit(robot.id, robot.to_dict())

            logger.info(f"✓ 断开连接: {robot.name}")

        except Exception as e:
            logger.error(f"断开连接出错: {e}")

    def send_command(self, robot_id: str, command: str, params: dict = None) -> bool:
        """
        发送命令到机器人

        Args:
            robot_id: 机器人 ID
            command: 命令类型
            params: 命令参数

        Returns:
            是否开始发送
        """
        if robot_id not in self.robots:
            logger.error(f"机器人 {robot_id} 不存在")
            return False

        robot = self.robots[robot_id]

        if robot.state != ConnectionState.CONNECTED:
            logger.warning(f"机器人 {robot_id} 未连接")
            self.command_failed.emit(robot_id, command, "未连接")
            return False

        # 添加到命令队列
        robot.command_queue.append({
            'command': command,
            'params': params,
            'timestamp': datetime.now()
        })

        # 在后台执行命令
        self._run_async(self._send_command_async(robot, command, params))

        return True

    async def _send_command_async(self, robot: Go2Robot, command: str, params: dict):
        """异步发送命令"""
        try:
            # 执行命令
            success = await WebRTCAPI.send_command(
                robot.webrtc_connection,
                command,
                params
            )

            if success:
                robot.last_command = command
                robot.last_seen = datetime.now()

                self.command_sent.emit(robot.id, command)
                self.robot_state_changed.emit(robot.id, robot.to_dict())

                logger.info(f"✓ 命令已发送: {robot.name} - {command}")
            else:
                self.command_failed.emit(robot.id, command, "发送失败")
                logger.error(f"✗ 命令发送失败: {robot.name} - {command}")

            # 从队列移除
            if robot.command_queue:
                robot.command_queue.pop(0)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"发送命令出错: {error_msg}")

            self.command_failed.emit(robot.id, command, error_msg)

            # 从队列移除
            if robot.command_queue:
                robot.command_queue.pop(0)

    def _keepalive(self):
        """定期检查连接状态"""
        for robot_id, robot in self.robots.items():
            if robot.state == ConnectionState.CONNECTED:
                # 检查连接是否还活跃
                self._run_async(self._check_connection_async(robot))

    async def _check_connection_async(self, robot: Go2Robot):
        """检查连接状态"""
        try:
            if robot.webrtc_connection and robot.webrtc_connection.isConnected:
                # 连接正常
                pass
            else:
                # 连接断开，尝试重连
                logger.warning(f"检测到连接断开: {robot.name}")
                robot.state = ConnectionState.DISCONNECTED
                self.robot_disconnected.emit(robot.id)

                if robot.auto_reconnect:
                    await self._connect_robot_async(robot)

        except Exception as e:
            logger.error(f"检查连接出错: {e}")

    def get_robot(self, robot_id: str) -> Optional[Go2Robot]:
        """获取机器人对象"""
        return self.robots.get(robot_id)

    def get_all_robots(self) -> List[Go2Robot]:
        """获取所有机器人"""
        return list(self.robots.values())

    def get_connected_robots(self) -> List[Go2Robot]:
        """获取已连接的机器人"""
        return [r for r in self.robots.values() if r.state == ConnectionState.CONNECTED]

    def shutdown_all(self):
        """断开所有连接"""
        logger.info("正在断开所有连接...")

        for robot_id in list(self.robots.keys()):
            self.disconnect_robot(robot_id)

        # 停止事件循环
        if self._event_loop:
            self._event_loop.call_soon_threadsafe(self._event_loop.stop)

        if self._event_loop_thread:
            self._event_loop_thread.join(timeout=2)

        logger.info("所有连接已断开")


# 便捷函数
def create_controller() -> Go2WebRTCController:
    """创建控制器实例"""
    return Go2WebRTCController()
