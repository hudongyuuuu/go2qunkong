# utils/config_manager.py
"""
Configuration Manager
"""

import json
from pathlib import Path
from typing import Dict, Any


class ConfigManager:
    """Manage application configuration"""

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.json"

        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.load()

    def load(self):
        """Load configuration from file"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
                self.config = {}
        else:
            self.config = self.get_default_config()
            self.save()

    def save(self):
        """Save configuration to file"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def set(self, key: str, value: Any):
        """Set configuration value"""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self.save()

    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "network": {
                "timeout": 10,
                "max_retries": 3,
                "ping_interval": 5,
            },
            "robots": [],
            "music": {
                "volume": 0.7,
                "auto_detect_bpm": True,
            },
            "ui": {
                "theme": "dark",
                "window_size": {
                    "width": 1400,
                    "height": 900,
                },
            },
        }
