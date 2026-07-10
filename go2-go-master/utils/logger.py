# utils/logger.py
"""
Logger Utility
"""

import logging
from pathlib import Path
from datetime import datetime


class Logger:
    """Application logger"""

    _instance = None
    _logger = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._setup_logger()
        return cls._instance

    @classmethod
    def _setup_logger(cls):
        """Setup logger"""
        cls._logger = logging.getLogger('UnitreeRobotControl')
        cls._logger.setLevel(logging.DEBUG)

        # Create logs directory
        log_dir = Path(__file__).parent.parent / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)

        # File handler
        log_file = log_dir / f'app_{datetime.now().strftime("%Y%m%d")}.log'
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        cls._logger.addHandler(file_handler)
        cls._logger.addHandler(console_handler)

    @classmethod
    def debug(cls, message: str):
        """Log debug message"""
        cls._logger.debug(message)

    @classmethod
    def info(cls, message: str):
        """Log info message"""
        cls._logger.info(message)

    @classmethod
    def warning(cls, message: str):
        """Log warning message"""
        cls._logger.warning(message)

    @classmethod
    def error(cls, message: str):
        """Log error message"""
        cls._logger.error(message)

    @classmethod
    def critical(cls, message: str):
        """Log critical message"""
        cls._logger.critical(message)
