#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
services/network_scanner.py
GO2 Robot Network Scanner - 局域网扫描服务
扫描 192.168.x.x 网段中的 GO2 机器人（端口 9991）
"""

import socket
import subprocess
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Optional, Callable
from dataclasses import dataclass
from PyQt5.QtCore import QObject, pyqtSignal

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class DiscoveredDevice:
    """发现的设备"""
    ip: str
    open_ports: List[int]
    is_go2: bool = False
    latency_ms: float = 0.0

    def __str__(self):
        ports_str = ",".join(map(str, self.open_ports)) if self.open_ports else "无"
        go2_tag = "[GO2]" if self.is_go2 else ""
        return f"{self.ip} - 端口: [{ports_str}] {go2_tag}"


class NetworkScanner(QObject):
    """
    网络扫描器 - 扫描局域网中的 GO2 机器人

    特性：
    - 快速 ping 扫描
    - 端口扫描（9991 WebRTC, 554 RTSP, 5000, 8081）
    - 线程池并发扫描
    - 实时进度报告
    """

    # 信号
    scan_progress = pyqtSignal(int, int)  # current, total
    device_found = pyqtSignal(object)  # DiscoveredDevice
    scan_complete = pyqtSignal(list)  # List[DiscoveredDevice]
    scan_error = pyqtSignal(str)  # error_message

    # GO2 机器人端口
    GO2_PORTS = [9991, 554, 5000, 8081]

    def __init__(self):
        super().__init__()
        self._is_scanning = False
        self._should_stop = False

    def scan_network(self, network: str = "192.168.71.0/24", progress_callback: Optional[Callable] = None) -> List[DiscoveredDevice]:
        """
        扫描网络中的 GO2 机器人

        Args:
            network: 网络段，如 "192.168.71.0/24"
            progress_callback: 进度回调函数 (current, total)

        Returns:
            List[DiscoveredDevice]: 发现的设备列表
        """
        if self._is_scanning:
            logger.warning("扫描正在进行中")
            return []

        self._is_scanning = True
        self._should_stop = False

        executor = None
        try:
            # 解析网络段
            base_ip = network.split('/')[0].rsplit('.', 1)[0]
            ips = [f"{base_ip}.{i}" for i in range(1, 255)]

            logger.info(f"开始扫描网络: {network}")
            logger.info(f"共 {len(ips)} 个 IP 地址")

            devices = []

            # 使用线程池并发扫描
            executor = ThreadPoolExecutor(max_workers=50)

            # 分批提交任务，避免一次性提交太多
            batch_size = 50
            future_to_ip = {}

            for i in range(0, len(ips), batch_size):
                if self._should_stop:
                    break

                batch = ips[i:i + batch_size]
                for ip in batch:
                    try:
                        future = executor.submit(self._scan_ip, ip)
                        future_to_ip[future] = ip
                    except Exception as e:
                        # 解释器关闭时可能抛出异常
                        logger.debug(f"无法提交扫描任务: {e}")
                        if "shutdown" in str(e).lower() or "interpreter" in str(e).lower():
                            self._should_stop = True
                            break

                if self._should_stop:
                    break

            # 处理结果
            completed = 0
            for future in as_completed(future_to_ip):
                if self._should_stop:
                    break

                completed += 1

                # 更新进度
                if progress_callback:
                    try:
                        progress_callback(completed, len(ips))
                    except:
                        pass
                try:
                    self.scan_progress.emit(completed, len(ips))
                except:
                    pass

                try:
                    result = future.result(timeout=3)
                    if result:
                        ip, ports, is_go2, latency = result
                        device = DiscoveredDevice(ip=ip, open_ports=ports, is_go2=is_go2, latency_ms=latency)
                        devices.append(device)
                        try:
                            self.device_found.emit(device)
                        except:
                            pass
                        logger.info(f"发现设备: {device}")

                except Exception as e:
                    logger.debug(f"扫描出错: {e}")

            logger.info(f"扫描完成，找到 {len(devices)} 台设备")
            try:
                self.scan_complete.emit(devices)
            except:
                pass

            return devices

        except Exception as e:
            error_msg = f"扫描失败: {str(e)}"
            logger.error(error_msg)
            try:
                self.scan_error.emit(error_msg)
            except:
                pass
            return []

        finally:
            self._is_scanning = False
            # 确保 executor 被正确关闭
            if executor is not None:
                try:
                    executor.shutdown(wait=False, cancel_futures=True)
                except:
                    pass

    def _scan_ip(self, ip: str) -> Optional[Tuple[str, List[int], bool, float]]:
        """
        扫描单个 IP

        Returns:
            (ip, [ports], is_go2, latency_ms) or None
        """
        import time

        # 先 ping 检查是否在线
        start_time = time.time()
        if not self._ping_ip(ip):
            return None

        latency = (time.time() - start_time) * 1000  # 转换为毫秒

        # 在线则检查端口
        open_ports = []
        for port in self.GO2_PORTS:
            if self._check_port(ip, port):
                open_ports.append(port)

        if not open_ports:
            return None

        # 判断是否为 GO2 设备
        is_go2 = 9991 in open_ports or 554 in open_ports or 8081 in open_ports

        return (ip, open_ports, is_go2, latency)

    def _ping_ip(self, ip: str, timeout: float = 1.0) -> bool:
        """
        Ping 检查 IP 是否在线

        Args:
            ip: IP 地址
            timeout: 超时时间（秒）

        Returns:
            是否在线
        """
        try:
            # Windows: ping -n 1 -w 1000 IP
            # Linux/Mac: ping -c 1 -W 1 IP
            import platform
            system = platform.system().lower()

            if system == "windows":
                cmd = ['ping', '-n', '1', '-w', str(int(timeout * 1000)), ip]
            else:
                cmd = ['ping', '-c', '1', '-W', str(int(timeout)), ip]

            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout + 0.5
            )

            return result.returncode == 0

        except Exception:
            return False

    def _check_port(self, ip: str, port: int, timeout: float = 0.5) -> bool:
        """
        检查 IP 的端口是否开放

        Args:
            ip: IP 地址
            port: 端口号
            timeout: 超时时间（秒）

        Returns:
            端口是否开放
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def stop_scan(self):
        """停止扫描"""
        self._should_stop = True
        logger.info("正在停止扫描...")

    def quick_scan(self, target_ips: List[str]) -> List[DiscoveredDevice]:
        """
        快速扫描指定的 IP 列表

        Args:
            target_ips: 要扫描的 IP 列表

        Returns:
            发现的设备列表
        """
        devices = []

        logger.info(f"快速扫描 {len(target_ips)} 个目标 IP...")

        executor = None
        try:
            executor = ThreadPoolExecutor(max_workers=20)
            future_to_ip = {}

            for ip in target_ips:
                try:
                    future = executor.submit(self._scan_ip, ip)
                    future_to_ip[future] = ip
                except Exception as e:
                    if "shutdown" in str(e).lower() or "interpreter" in str(e).lower():
                        break

            for future in as_completed(future_to_ip):
                try:
                    result = future.result(timeout=2)
                    if result:
                        ip, ports, is_go2, latency = result
                        device = DiscoveredDevice(ip=ip, open_ports=ports, is_go2=is_go2, latency_ms=latency)
                        devices.append(device)
                        try:
                            self.device_found.emit(device)
                        except:
                            pass
                        logger.info(f"发现设备: {device}")
                except Exception as e:
                    logger.debug(f"扫描出错: {e}")

        except Exception as e:
            logger.error(f"快速扫描失败: {e}")

        finally:
            if executor is not None:
                try:
                    executor.shutdown(wait=False, cancel_futures=True)
                except:
                    pass

        logger.info(f"快速扫描完成，找到 {len(devices)} 台设备")
        try:
            self.scan_complete.emit(devices)
        except:
            pass

        return devices


# 便捷函数
def scan_for_go2_robots(network: str = "192.168.71.0/24") -> List[DiscoveredDevice]:
    """
    扫描 GO2 机器人（同步版本）

    Args:
        network: 网络段

    Returns:
        发现的 GO2 设备列表
    """
    scanner = NetworkScanner()
    devices = scanner.scan_network(network)
    # 只返回 GO2 设备
    return [d for d in devices if d.is_go2]


if __name__ == "__main__":
    # 测试
    print("=" * 60)
    print("GO2 网络扫描器测试")
    print("=" * 60)

    scanner = NetworkScanner()

    def on_progress(current, total):
        percent = int(current / total * 100)
        print(f"\r扫描进度: [{'=' * (percent // 2)}{' ' * (50 - percent // 2)}] {percent}% ({current}/{total})", end='')

    def on_device_found(device):
        if device.is_go2:
            print(f"\n✓ 发现 GO2 设备: {device}")

    def on_complete(devices):
        go2_devices = [d for d in devices if d.is_go2]
        print(f"\n\n扫描完成！")
        print(f"总共发现: {len(devices)} 台设备")
        print(f"GO2 设备: {len(go2_devices)} 台")
        print()

        if go2_devices:
            print("GO2 机器人列表:")
            for i, device in enumerate(go2_devices, 1):
                print(f"  {i}. {device}")
        else:
            print("未发现 GO2 设备")

    # 连接信号
    scanner.scan_progress.connect(on_progress)
    scanner.device_found.connect(on_device_found)
    scanner.scan_complete.connect(on_complete)

    # 开始扫描
    devices = scanner.scan_network("192.168.71.0/24")

    print()
