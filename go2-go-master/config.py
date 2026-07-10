# config.py
"""
Unitree GO2AIR Robot Control - Global Configuration
"""

import os
from pathlib import Path

# Project Paths
PROJECT_ROOT = Path(__file__).parent
RESOURCES_DIR = PROJECT_ROOT / "resources"
STYLES_DIR = RESOURCES_DIR / "styles"
ICONS_DIR = RESOURCES_DIR / "icons"
FONTS_DIR = RESOURCES_DIR / "fonts"
DATABASE_PATH = PROJECT_ROOT / "data" / "robot_control.db"

# Theme Colors (Light Theme)
COLORS = {
    'background': '#F5F7FA',      # Light gray background
    'card': '#FFFFFF',            # White card
    'card_hover': '#F8FAFC',      # Card hover
    'primary': '#1976D2',         # Deep blue primary
    'accent': '#00BCF4',          # Cyan accent
    'success': '#10B981',         # Green success
    'warning': '#F59E0B',         # Orange warning
    'error': '#EF4444',           # Red error
    'text_primary': '#2D3748',    # Dark gray text
    'text_secondary': '#64748B',  # Medium gray text
    'border': '#E2E8F0',          # Light gray border
    'grid': '#EDF2F7',            # Grid lines
    'shadow': 'rgba(0, 0, 0, 0.08)', # Shadow
}

# Network Configuration
NETWORK_CONFIG = {
    'default_http_port': 8080,
    'default_ws_port': 8081,
    'timeout': 10,
    'max_retries': 3,
    'ping_interval': 5,  # seconds
}

# Robot Configuration
ROBOT_CONFIG = {
    'max_robots': 20,
    'connection_timeout': 30,
    'default_position_update_rate': 10,  # Hz
}

# Timeline Configuration
TIMELINE_CONFIG = {
    'grid_snap_ms': 100,          # Grid snap interval
    'min_zoom': 0.5,              # Minimum zoom level
    'max_zoom': 3.0,              # Maximum zoom level
    'default_zoom': 1.0,          # Default zoom level
    'tracks': ['Robot 1', 'Robot 2', 'Robot 3', 'Robot 4'],
}

# Music Configuration
MUSIC_CONFIG = {
    'supported_formats': ['.mp3', '.wav', '.ogg', '.flac'],
    'default_volume': 0.7,
    'default_bpm': 120,
}

# Formation Types
FORMATION_TYPES = {
    'line': 'Line',
    'column': 'Column',
    'square': 'Square',
    'circle': 'Circle',
    'v_shape': 'V-Shape',
    'triangle': 'Triangle',
    'diamond': 'Diamond',
    'custom': 'Custom',
}

# Action Types
ACTION_TYPES = {
    'stand': 'Stand',
    'sit': 'Sit',
    'walk': 'Walk',
    'trot': 'Trot',
    'run': 'Run',
    'jump': 'Jump',
    'turn_left': 'Turn Left',
    'turn_right': 'Turn Right',
    'wave_hand': 'Wave Hand',
    'dance_move_1': 'Dance Move 1',
    'dance_move_2': 'Dance Move 2',
    'dance_move_3': 'Dance Move 3',
    'custom': 'Custom',
}

# Database Configuration
DATABASE_CONFIG = {
    'name': 'robot_control.db',
    'path': str(PROJECT_ROOT / 'data'),
}

# Logging Configuration
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file_path': str(PROJECT_ROOT / 'logs' / 'app.log'),
}

# UI Configuration
UI_CONFIG = {
    'window_title': 'Unitree GO2AIR Robot Control',
    'window_width': 1400,
    'window_height': 900,
    'min_window_width': 1200,
    'min_window_height': 700,
    'status_bar_height': 30,
    'nav_bar_height': 60,
}
