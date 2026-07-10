#!/usr/bin/env python3
# robot_control_main.py
"""
Unitree GO2 Robot Control - Main Entry Point
机器人控制主程序
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from ui.robot_control_main import RobotControlMain


def setup_high_dpi():
    """Setup high DPI scaling"""
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)


def main():
    """Main entry point"""
    # Setup high DPI BEFORE creating QApplication
    setup_high_dpi()

    # Create application
    app = QApplication(sys.argv)

    # Set application info
    app.setApplicationName("GO2 机器狗群控中心")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Unitree")

    # Set default font
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    # Create and show main window
    window = RobotControlMain()
    window.setWindowTitle("Unitree GO2 机器狗群控中心")
    window.resize(1400, 900)
    window.show()

    # Run event loop
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
