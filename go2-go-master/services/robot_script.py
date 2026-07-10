# services/robot_script.py
"""
Robot Script Service - Record and playback robot action sequences
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTimer


@dataclass
class ScriptAction:
    """Single action in a script"""
    robot_id: str           # Target robot ID
    action_type: str        # Action type (stand, sit, walk, etc.)
    params: Dict[str, Any]  # Action parameters
    timestamp: float        # Time offset in milliseconds
    duration: float = 0.0   # Action duration in seconds


@dataclass
class RobotScript:
    """A sequence of actions for robots"""
    name: str
    description: str
    actions: List[ScriptAction]
    created_at: str
    total_duration: float  # Total duration in milliseconds

    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'description': self.description,
            'actions': [asdict(a) for a in self.actions],
            'created_at': self.created_at,
            'total_duration': self.total_duration,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'RobotScript':
        return cls(
            name=data['name'],
            description=data.get('description', ''),
            actions=[ScriptAction(**a) for a in data.get('actions', [])],
            created_at=data.get('created_at', datetime.now().isoformat()),
            total_duration=data.get('total_duration', 0),
        )


class ScriptExecutor(QThread):
    """Execute robot script in background thread"""

    # Signals
    action_started = pyqtSignal(str, str, float)  # robot_id, action, timestamp
    action_completed = pyqtSignal(str, str)  # robot_id, action
    action_failed = pyqtSignal(str, str, str)  # robot_id, action, error
    log_message = pyqtSignal(str)  # log message
    script_finished = pyqtSignal()
    script_stopped = pyqtSignal()

    def __init__(self, script: RobotScript, controller):
        super().__init__()
        self.script = script
        self.controller = controller
        self._is_running = True
        self._is_paused = False

    def stop(self):
        """Stop execution"""
        self._is_running = False
        self.log_message.emit("Script stopped by user")

    def pause(self):
        """Pause execution"""
        self._is_paused = True
        self.log_message.emit("Script paused")

    def resume(self):
        """Resume execution"""
        self._is_paused = False
        self.log_message.emit("Script resumed")

    def run(self):
        """Execute script"""
        self.log_message.emit("=" * 60)
        self.log_message.emit(f"Starting script: {self.script.name}")
        self.log_message.emit(f"Total actions: {len(self.script.actions)}")
        self.log_message.emit("=" * 60)

        start_time = datetime.now()

        for i, action in enumerate(self.script.actions, 1):
            if not self._is_running:
                break

            # Wait if paused
            while self._is_paused and self._is_running:
                self.msleep(100)

            # Wait until action timestamp
            current_time = (datetime.now() - start_time).total_seconds() * 1000
            wait_time = action.timestamp - current_time

            if wait_time > 0:
                self.log_message.emit(f"Waiting {wait_time/1000:.2f}s before action {i}")
                # Wait in small chunks to check for stop/pause
                wait_ms = int(wait_time)
                chunk = 100
                while wait_ms > 0 and self._is_running:
                    if self._is_paused:
                        self.msleep(100)
                        wait_ms += 100  # Compensate for paused time
                    else:
                        sleep_time = min(chunk, wait_ms)
                        self.msleep(sleep_time)
                        wait_ms -= sleep_time

            if not self._is_running:
                break

            # Execute action
            self.log_message.emit(f"\n[{i}] Executing: {action.action_type} on {action.robot_id}")
            self.action_started.emit(action.robot_id, action.action_type, action.timestamp)

            try:
                # Send command to robot
                if hasattr(self.controller, 'send_command_async'):
                    # Use async if available
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        success = loop.run_until_complete(
                            self.controller.send_command_async(
                                action.robot_id,
                                action.action_type,
                                action.params
                            )
                        )
                    finally:
                        loop.close()
                else:
                    # Use sync method
                    self.controller.send_command(
                        action.robot_id,
                        action.action_type,
                        action.params
                    )
                    success = True

                if success:
                    self.log_message.emit(f"✓ Action completed successfully")
                    self.action_completed.emit(action.robot_id, action.action_type)
                else:
                    self.log_message.emit(f"✗ Action failed")
                    self.action_failed.emit(action.robot_id, action.action_type, "Unknown error")

            except Exception as e:
                error_msg = str(e)
                self.log_message.emit(f"✗ Error: {error_msg}")
                self.action_failed.emit(action.robot_id, action.action_type, error_msg)

        if self._is_running:
            total_time = (datetime.now() - start_time).total_seconds()
            self.log_message.emit("=" * 60)
            self.log_message.emit(f"Script completed in {total_time:.2f}s")
            self.log_message.emit("=" * 60)
            self.script_finished.emit()
        else:
            self.log_message.emit("Script execution stopped")
            self.script_stopped.emit()


class ScriptService(QObject):
    """Service for managing robot scripts"""

    # Signals
    script_list_changed = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.scripts: Dict[str, RobotScript] = {}
        self.scripts_dir = Path(__file__).parent.parent / "scripts"
        self.scripts_dir.mkdir(exist_ok=True)

        # Current script being recorded/edited
        self.current_script: Optional[RobotScript] = None
        self.recording_start_time: Optional[datetime] = None
        self._is_recording = False

        # Load existing scripts
        self._load_scripts()

    def _load_scripts(self):
        """Load scripts from directory"""
        try:
            for script_file in self.scripts_dir.glob("*.json"):
                with open(script_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    script = RobotScript.from_dict(data)
                    self.scripts[script.name] = script
            print(f"Loaded {len(self.scripts)} scripts")
        except Exception as e:
            print(f"Error loading scripts: {e}")

    def create_script(self, name: str, description: str = "") -> RobotScript:
        """Create a new script"""
        script = RobotScript(
            name=name,
            description=description,
            actions=[],
            created_at=datetime.now().isoformat(),
            total_duration=0,
        )
        self.scripts[name] = script
        self._save_script(script)
        self.script_list_changed.emit()
        return script

    def save_script(self, script: RobotScript):
        """Save script to file"""
        # Calculate total duration
        if script.actions:
            script.total_duration = max(a.timestamp for a in script.actions)

        script_file = self.scripts_dir / f"{script.name}.json"
        with open(script_file, 'w', encoding='utf-8') as f:
            json.dump(script.to_dict(), f, indent=2, ensure_ascii=False)

        self.scripts[script.name] = script
        self.script_list_changed.emit()

    def load_script(self, name: str) -> Optional[RobotScript]:
        """Load script from file"""
        if name in self.scripts:
            return self.scripts[name]

        script_file = self.scripts_dir / f"{name}.json"
        if script_file.exists():
            with open(script_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                script = RobotScript.from_dict(data)
                self.scripts[name] = script
                return script
        return None

    def delete_script(self, name: str) -> bool:
        """Delete script"""
        if name in self.scripts:
            script_file = self.scripts_dir / f"{name}.json"
            if script_file.exists():
                script_file.unlink()
            del self.scripts[name]
            self.script_list_changed.emit()
            return True
        return False

    def get_all_scripts(self) -> List[RobotScript]:
        """Get all scripts"""
        return list(self.scripts.values())

    def start_recording(self, script_name: str, description: str = ""):
        """Start recording actions"""
        self.current_script = RobotScript(
            name=script_name,
            description=description,
            actions=[],
            created_at=datetime.now().isoformat(),
            total_duration=0,
        )
        self.recording_start_time = datetime.now()
        self._is_recording = True
        print(f"Started recording: {script_name}")

    def stop_recording(self) -> Optional[RobotScript]:
        """Stop recording and save script"""
        if not self._is_recording:
            return None

        self._is_recording = False

        # Calculate total duration
        if self.current_script.actions:
            self.current_script.total_duration = max(a.timestamp for a in self.current_script.actions)

        # Save script
        self.save_script(self.current_script)

        script = self.current_script
        self.current_script = None
        self.recording_start_time = None

        print(f"Stopped recording: {script.name}")
        return script

    def record_action(self, robot_id: str, action_type: str, params: Dict = None, duration: float = 0.0):
        """Record an action

        Args:
            robot_id: Target robot ID
            action_type: Action type
            params: Action parameters (optional)
            duration: Action duration in seconds (optional, auto-detected if not provided)
        """
        if not self._is_recording or not self.current_script:
            return

        # Calculate timestamp from start
        elapsed = (datetime.now() - self.recording_start_time).total_seconds() * 1000

        # Auto-detect duration if not provided
        if duration == 0.0:
            duration = self.get_action_duration(action_type)

        action = ScriptAction(
            robot_id=robot_id,
            action_type=action_type,
            params=params or {},
            timestamp=elapsed,
            duration=duration,
        )

        self.current_script.actions.append(action)
        print(f"Recorded action: {action_type} on {robot_id} at {elapsed:.0f}ms (duration: {duration}s)")

    def execute_script(self, script: RobotScript, controller, parent=None) -> ScriptExecutor:
        """Execute a script"""
        executor = ScriptExecutor(script, controller)

        # Connect to parent if provided for logging
        if parent:
            executor.log_message.connect(parent._on_log_message)
            executor.action_started.connect(parent._on_action_started)
            executor.action_completed.connect(parent._on_action_completed)
            executor.action_failed.connect(parent._on_action_failed)
            executor.script_finished.connect(parent._on_script_finished)
            executor.script_stopped.connect(parent._on_script_stopped)

        executor.start()
        return executor

    def get_builtin_actions(self) -> Dict[str, List[Dict]]:
        """Get all built-in actions organized by category

        预估时间长度说明：
        - 基础动作: 1-3秒
        - 移动: 2-5秒（可连续）
        - 转向: 1-3秒
        - 特殊动作: 2-4秒
        - 舞蹈动作: 3-6秒
        - 全身动作: 3-8秒
        """
        return {
            "基础动作": [
                {"name": "站立", "type": "stand", "icon": "🧍", "duration": 1.5, "desc": "从蹲坐姿态站立"},
                {"name": "坐下", "type": "sit", "icon": "🧘", "duration": 2.0, "desc": "坐下休息姿态"},
                {"name": "趴下", "type": "lie_down", "icon": "🛌", "duration": 2.5, "desc": "趴卧姿态"},
                {"name": "站立伸展", "type": "stand_up", "icon": "🙆", "duration": 2.0, "desc": "伸展站立"},
            ],
            "移动": [
                {"name": "前进", "type": "move_forward", "icon": "⬆️", "duration": 3.0, "desc": "向前移动一步"},
                {"name": "后退", "type": "move_backward", "icon": "⬇️", "duration": 3.0, "desc": "向后移动一步"},
                {"name": "向左移", "type": "move_left", "icon": "⬅️", "duration": 2.5, "desc": "向左横移一步"},
                {"name": "向右移", "type": "move_right", "icon": "➡️", "duration": 2.5, "desc": "向右横移一步"},
                {"name": "行走", "type": "walk", "icon": "🚶", "duration": 4.0, "desc": "正常行走"},
                {"name": "小跑", "type": "trot", "icon": "🏃", "duration": 3.5, "desc": "小跑步态"},
                {"name": "奔跑", "type": "run", "icon": "💨", "duration": 5.0, "desc": "快速奔跑"},
            ],
            "转向": [
                {"name": "左转", "type": "turn_left", "icon": "↩️", "duration": 2.0, "desc": "向左转90度"},
                {"name": "右转", "type": "turn_right", "icon": "↪️", "duration": 2.0, "desc": "向右转90度"},
                {"name": "原地旋转", "type": "spin", "icon": "🔄", "duration": 3.0, "desc": "原地旋转360度"},
            ],
            "特殊动作": [
                {"name": "跳跃", "type": "jump", "icon": "🦘", "duration": 2.5, "desc": "原地跳跃"},
                {"name": "挥手", "type": "wave_hand", "icon": "👋", "duration": 3.0, "desc": "前腿挥手致意"},
                {"name": "作揖", "type": "bow", "icon": "🙏", "duration": 3.5, "desc": "作揖鞠躬动作"},
                {"name": "爬行", "type": "crawl", "icon": "🐍", "duration": 4.0, "desc": "低姿态爬行"},
                {"name": "翻滚", "type": "roll_over", "icon": "🔄", "duration": 4.5, "desc": "侧身翻滚"},
            ],
            "舞蹈动作": [
                {"name": "舞蹈1", "type": "dance_move_1", "icon": "💃", "duration": 4.0, "desc": "基础舞蹈动作1"},
                {"name": "舞蹈2", "type": "dance_move_2", "icon": "🕺", "duration": 4.5, "desc": "基础舞蹈动作2"},
                {"name": "舞蹈3", "type": "dance_move_3", "icon": "💃", "duration": 5.0, "desc": "基础舞蹈动作3"},
                {"name": "舞蹈4", "type": "dance_move_4", "icon": "🕺", "duration": 5.5, "desc": "进阶舞蹈动作1"},
                {"name": "舞蹈5", "type": "dance_move_5", "icon": "💃", "duration": 6.0, "desc": "进阶舞蹈动作2"},
                {"name": "太空步", "type": "moonwalk", "icon": "🌙", "duration": 5.0, "desc": "太空步滑行"},
            ],
            "全身动作": [
                {"name": "俯卧撑", "type": "pushup", "icon": "💪", "duration": 6.0, "desc": "做俯卧撑动作"},
                {"name": "伸展运动", "type": "stretch", "icon": "🤸", "duration": 5.0, "desc": "全身伸展"},
                {"name": "踢腿", "type": "kick", "icon": "🦵", "duration": 3.0, "desc": "后腿踢高"},
                {"name": "后空翻", "type": "backflip", "icon": "🔄", "duration": 8.0, "desc": "后空翻特技"},
            ],
        }

    def get_action_duration(self, action_type: str) -> float:
        """Get estimated duration for an action type in seconds"""
        actions = self.get_builtin_actions()
        for category_actions in actions.values():
            for action in category_actions:
                if action['type'] == action_type:
                    return action.get('duration', 2.0)
        return 2.0  # Default duration
