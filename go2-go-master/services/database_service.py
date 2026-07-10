# services/database_service.py
"""
Database Service - SQLite database for data persistence
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from models.robot import Robot, RobotGroup, ConnectionStatus, RobotState
from models.action import Action, ActionLibrary
from models.group import Formation, FormationType
from models.music import MusicTrack, Choreography


class DatabaseService:
    """Database service for data persistence"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            # Default path
            project_root = Path(__file__).parent.parent
            data_dir = project_root / 'data'
            data_dir.mkdir(exist_ok=True)
            db_path = data_dir / 'robot_control.db'

        self.db_path = db_path
        self.conn = None
        self.connect()
        self._create_tables()

    def connect(self):
        """Connect to database"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        """Close database connection"""
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
            self.conn = None

    def _ensure_connection(self):
        """Ensure database connection is open"""
        if self.conn is None:
            self.connect()

    def _execute_query(self, query, params=()):
        """Execute a query with connection check"""
        self._ensure_connection()
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor

    def _create_tables(self):
        """Create database tables"""
        cursor = self.conn.cursor()

        # Robots table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS robots (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                ip TEXT NOT NULL,
                port INTEGER DEFAULT 8080,
                model TEXT DEFAULT 'GO2AIR',
                firmware_version TEXT DEFAULT '1.0.0',
                group_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Groups table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                group_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                formation_type TEXT DEFAULT 'line',
                formation_params TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Group members table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_members (
                group_id TEXT,
                robot_id TEXT,
                position_index INTEGER DEFAULT 0,
                PRIMARY KEY (group_id, robot_id),
                FOREIGN KEY (group_id) REFERENCES groups(group_id) ON DELETE CASCADE,
                FOREIGN KEY (robot_id) REFERENCES robots(id) ON DELETE CASCADE
            )
        """)

        # Music tracks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS music_tracks (
                track_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                duration REAL NOT NULL,
                bpm REAL DEFAULT 120.0,
                beat_markers TEXT,
                volume REAL DEFAULT 0.7,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Choreographies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS choreographies (
                choreo_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                music_track_id TEXT,
                timeline_duration REAL DEFAULT 60000.0,
                actions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (music_track_id) REFERENCES music_tracks(track_id) ON DELETE SET NULL
            )
        """)

        # Action history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS action_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                robot_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                params TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN DEFAULT TRUE,
                error_message TEXT,
                FOREIGN KEY (robot_id) REFERENCES robots(id) ON DELETE CASCADE
            )
        """)

        self.conn.commit()

    # Robot CRUD operations
    def add_robot(self, robot: Robot) -> bool:
        """Add robot to database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO robots (id, name, ip, port, model, firmware_version, group_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (robot.id, robot.name, robot.ip, robot.port, robot.model,
                 robot.firmware_version, robot.group_id))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error adding robot: {e}")
            return False

    def get_robot(self, robot_id: str) -> Optional[Robot]:
        """Get robot by ID"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM robots WHERE id = ?", (robot_id,))
            row = cursor.fetchone()

            if row:
                return Robot(
                    id=row['id'],
                    name=row['name'],
                    ip=row['ip'],
                    port=row['port'],
                    model=row['model'],
                    firmware_version=row['firmware_version'],
                    group_id=row['group_id'],
                )
            return None
        except sqlite3.Error as e:
            print(f"Error getting robot: {e}")
            return None

    def get_all_robots(self) -> List[Robot]:
        """Get all robots"""
        try:
            self._ensure_connection()
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM robots ORDER BY name")
            rows = cursor.fetchall()

            robots = []
            for row in rows:
                robots.append(Robot(
                    id=row['id'],
                    name=row['name'],
                    ip=row['ip'],
                    port=row['port'],
                    model=row['model'],
                    firmware_version=row['firmware_version'],
                    group_id=row['group_id'],
                ))
            return robots
        except sqlite3.Error as e:
            print(f"Error getting robots: {e}")
            return []

    def delete_robot(self, robot_id: str) -> bool:
        """Delete robot from database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM robots WHERE id = ?", (robot_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error deleting robot: {e}")
            return False

    # Group CRUD operations
    def add_group(self, group: RobotGroup) -> bool:
        """Add group to database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO groups (group_id, name, formation_type, formation_params, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (group.group_id, group.name, group.formation_type,
                 json.dumps(group.formation_params)))
            self.conn.commit()

            # Add group members
            for i, robot_id in enumerate(group.robots):
                cursor.execute("""
                    INSERT OR REPLACE INTO group_members (group_id, robot_id, position_index)
                    VALUES (?, ?, ?)
                """, (group.group_id, robot_id, i))

            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error adding group: {e}")
            return False

    def get_all_groups(self) -> List[RobotGroup]:
        """Get all groups"""
        try:
            self._ensure_connection()
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM groups ORDER BY name")
            rows = cursor.fetchall()

            groups = []
            for row in rows:
                group = RobotGroup(row['group_id'], row['name'])
                group.formation_type = row['formation_type']
                group.formation_params = json.loads(row['formation_params']) if row['formation_params'] else {}

                # Get group members
                cursor.execute("""
                    SELECT robot_id FROM group_members
                    WHERE group_id = ? ORDER BY position_index
                """, (row['group_id'],))
                group.robots = [r['robot_id'] for r in cursor.fetchall()]

                groups.append(group)
            return groups
        except sqlite3.Error as e:
            print(f"Error getting groups: {e}")
            return []

    def delete_group(self, group_id: str) -> bool:
        """Delete group from database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM groups WHERE group_id = ?", (group_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error deleting group: {e}")
            return False

    # Music track operations
    def add_music_track(self, track: MusicTrack) -> bool:
        """Add music track to database"""
        try:
            cursor = self.conn.cursor()
            beat_markers_json = json.dumps([m.to_dict() for m in track.beat_markers])
            cursor.execute("""
                INSERT OR REPLACE INTO music_tracks (track_id, name, file_path, duration, bpm, beat_markers, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (track.id, track.name, track.file_path, track.duration,
                 track.bpm, beat_markers_json, track.volume))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error adding music track: {e}")
            return False

    def get_all_music_tracks(self) -> List[MusicTrack]:
        """Get all music tracks"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM music_tracks ORDER BY name")
            rows = cursor.fetchall()

            tracks = []
            for row in rows:
                beat_markers = []
                if row['beat_markers']:
                    markers_data = json.loads(row['beat_markers'])
                    beat_markers = [BeatMarker.from_dict(m) for m in markers_data]

                tracks.append(MusicTrack(
                    id=row['track_id'],
                    name=row['name'],
                    file_path=row['file_path'],
                    duration=row['duration'],
                    bpm=row['bpm'],
                    beat_markers=beat_markers,
                    volume=row['volume'],
                ))
            return tracks
        except sqlite3.Error as e:
            print(f"Error getting music tracks: {e}")
            return []

    def delete_music_track(self, track_id: str) -> bool:
        """Delete music track from database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM music_tracks WHERE track_id = ?", (track_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error deleting music track: {e}")
            return False

    # Choreography operations
    def save_choreography(self, choreography: Choreography) -> bool:
        """Save choreography to database"""
        try:
            cursor = self.conn.cursor()
            actions_json = json.dumps(choreography.actions)
            cursor.execute("""
                INSERT OR REPLACE INTO choreographies (choreo_id, name, music_track_id, timeline_duration, actions, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (choreography.id, choreography.name,
                 choreography.music_track.id if choreography.music_track else None,
                 choreography.timeline_duration, actions_json))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error saving choreography: {e}")
            return False

    def get_all_choreographies(self) -> List[Choreography]:
        """Get all choreographies"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM choreographies ORDER BY name")
            rows = cursor.fetchall()

            choreographies = []
            for row in rows:
                actions = json.loads(row['actions']) if row['actions'] else {}

                choreography = Choreography(
                    id=row['choreo_id'],
                    name=row['name'],
                    actions=actions,
                    timeline_duration=row['timeline_duration'],
                )

                # Load music track if exists
                if row['music_track_id']:
                    cursor.execute("SELECT * FROM music_tracks WHERE track_id = ?",
                                  (row['music_track_id'],))
                    track_row = cursor.fetchone()
                    if track_row:
                        beat_markers = []
                        if track_row['beat_markers']:
                            markers_data = json.loads(track_row['beat_markers'])
                            beat_markers = [BeatMarker.from_dict(m) for m in markers_data]

                        choreography.music_track = MusicTrack(
                            id=track_row['track_id'],
                            name=track_row['name'],
                            file_path=track_row['file_path'],
                            duration=track_row['duration'],
                            bpm=track_row['bpm'],
                            beat_markers=beat_markers,
                            volume=track_row['volume'],
                        )

                choreographies.append(choreography)
            return choreographies
        except sqlite3.Error as e:
            print(f"Error getting choreographies: {e}")
            return []

    # Action history operations
    def log_action(self, robot_id: str, action_type: str, params: Dict[str, Any],
                   success: bool, error_message: str = None) -> bool:
        """Log action to history"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO action_history (robot_id, action_type, params, success, error_message)
                VALUES (?, ?, ?, ?, ?)
            """, (robot_id, action_type, json.dumps(params), success, error_message))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error logging action: {e}")
            return False

    def get_action_history(self, robot_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get action history for robot"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT * FROM action_history
                WHERE robot_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (robot_id, limit))
            rows = cursor.fetchall()

            history = []
            for row in rows:
                history.append({
                    'id': row['id'],
                    'robot_id': row['robot_id'],
                    'action_type': row['action_type'],
                    'params': json.loads(row['params']) if row['params'] else {},
                    'timestamp': row['timestamp'],
                    'success': row['success'],
                    'error_message': row['error_message'],
                })
            return history
        except sqlite3.Error as e:
            print(f"Error getting action history: {e}")
            return []
