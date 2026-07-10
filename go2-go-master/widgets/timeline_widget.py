# widgets/timeline_widget.py
"""
Timeline Widget - Visual timeline editor for robot actions
"""

from PyQt5.QtWidgets import (QGraphicsView, QGraphicsScene, QWidget,
                             QVBoxLayout, QHBoxLayout, QScrollBar,
                             QLabel, QPushButton, QSlider)
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QBrush

from widgets.action_block import ActionBlock
from config import COLORS, TIMELINE_CONFIG


class TimelineWidget(QWidget):
    """Timeline editor widget - container for graphics view and controls"""

    # Signals
    block_selected = pyqtSignal(dict)
    block_moved = pyqtSignal(str, float, float)  # block_id, start_time, track
    play_position_changed = pyqtSignal(float)
    add_action_requested = pyqtSignal(float, int)  # position_ms, track

    def __init__(self):
        super().__init__()

        self.zoom = TIMELINE_CONFIG['default_zoom']
        self.grid_interval = TIMELINE_CONFIG['grid_snap_ms']
        self.track_height = 80  # Increased from 60
        self.header_height = 40
        self.playhead_position = 0  # milliseconds

        self.tracks = TIMELINE_CONFIG['tracks']
        self.action_blocks = {}  # block_id -> ActionBlock

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top controls
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(8, 4, 8, 4)

        self.zoom_label = QLabel("Zoom:")
        self.zoom_label.setStyleSheet("color: #A0AEC0; font-size: 12px;")
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(50, 300)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(150)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)

        controls_layout.addWidget(self.zoom_label)
        controls_layout.addWidget(self.zoom_slider)
        controls_layout.addStretch()

        self.time_display = QLabel("00:00.000")
        self.time_display.setProperty("caption", True)
        controls_layout.addWidget(self.time_display)

        layout.addLayout(controls_layout)

        # Create graphics view and scene
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(0, 0, 60000, self.header_height + len(self.tracks) * self.track_height)

        self.graphics_view = QGraphicsView()
        self.graphics_view.setScene(self.scene)
        self.graphics_view.setRenderHint(QPainter.Antialiasing)
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphics_view.setMinimumHeight(self.header_height + len(self.tracks) * self.track_height)

        layout.addWidget(self.graphics_view)

        # Custom horizontal scrollbar
        self.h_scroll = QScrollBar(Qt.Horizontal)
        self.h_scroll.setRange(0, 60000)
        self.h_scroll.valueChanged.connect(self._on_scroll_changed)

        # Custom vertical scrollbar
        self.v_scroll = QScrollBar(Qt.Vertical)
        self.v_scroll.setRange(0, len(self.tracks) * self.track_height)
        self.v_scroll.valueChanged.connect(self._on_scroll_changed)

        # Scrollbars container
        scrollbars_layout = QHBoxLayout()
        scrollbars_layout.addWidget(self.v_scroll)
        scrollbars_layout.addWidget(self.h_scroll)

        layout.addLayout(scrollbars_layout)

        self.setLayout(layout)

        # Connect signals
        self.scene.selectionChanged.connect(self._on_selection_changed)

        # Draw timeline elements
        self._draw_timeline()

    def _draw_timeline(self):
        """Draw timeline elements"""
        # Clear scene
        self.scene.clear()

        # Draw tracks
        for i, track_name in enumerate(self.tracks):
            y = self.header_height + i * self.track_height

            # Track background (alternating colors)
            if i % 2 == 0:
                bg_color = QColor(COLORS['card'])
            else:
                bg_color = QColor(COLORS['background'])

            track_rect = QRectF(0, y, 60000, self.track_height)
            self.scene.addRect(track_rect, QPen(Qt.NoPen), QBrush(bg_color))

            # Track border
            self.scene.addLine(0, y + self.track_height, 60000, y + self.track_height,
                              QPen(QColor(COLORS['grid']), 1))

            # Track label
            text = self.scene.addText(track_name)
            text.setDefaultTextColor(QColor(COLORS['text_secondary']))
            text.setFont(QFont("Segoe UI", 12, QFont.Bold))
            text.setPos(8, y + 8)

        # Draw header
        header_rect = QRectF(0, 0, 60000, self.header_height)
        self.scene.addRect(header_rect, QPen(Qt.NoPen), QBrush(QColor(COLORS['card'])))

        # Draw time markers
        self._draw_time_markers()

        # Draw vertical grid lines
        self._draw_grid_lines()

        # Draw playhead
        self._draw_playhead()

    def _draw_time_markers(self):
        """Draw time markers in header"""
        # Draw markers every second (1000ms)
        for seconds in range(0, 60):  # 60 seconds
            x = seconds * 1000
            text = self.scene.addText(f"{seconds}s")
            text.setDefaultTextColor(QColor(COLORS['text_secondary']))
            text.setFont(QFont("Segoe UI", 8))
            text.setPos(x + 2, 5)

            # Draw tick mark
            self.scene.addLine(x, self.header_height - 5, x, self.header_height,
                              QPen(QColor(COLORS['grid']), 1))

    def _draw_grid_lines(self):
        """Draw vertical grid lines"""
        # Draw beat markers (every 500ms)
        for ms in range(0, 60000, 500):
            x = ms
            if ms % 1000 == 0:
                # Major beat
                pen = QPen(QColor(COLORS['primary']), 1)
            else:
                # Minor beat
                pen = QPen(QColor(COLORS['grid']), 1, Qt.DotLine)

            self.scene.addLine(x, self.header_height, x,
                              self.header_height + len(self.tracks) * self.track_height, pen)

    def _draw_playhead(self):
        """Draw playhead at current position"""
        y_start = 0
        y_end = self.header_height + len(self.tracks) * self.track_height
        x = self.playhead_position

        # Draw playhead line
        self.scene.addLine(x, y_start, x, y_end, QPen(QColor(COLORS['accent']), 2))

        # Draw playhead triangle
        triangle = [
            QPointF(x - 8, 0),
            QPointF(x + 8, 0),
            QPointF(x, 12)
        ]
        from PyQt5.QtGui import QPolygonF
        self.scene.addPolygon(QPolygonF(triangle), QPen(QColor(COLORS['accent']), 2),
                              QBrush(QColor(COLORS['accent'])))

    def add_action_block(self, block_id: str, block: 'ActionBlock', track: int):
        """Add action block to timeline"""
        if track < 0 or track >= len(self.tracks):
            return

        y = self.header_height + track * self.track_height
        block.setPos(block.start_time, y)

        self.scene.addItem(block)
        self.action_blocks[block_id] = block

    def remove_action_block(self, block_id: str):
        """Remove action block from timeline"""
        if block_id in self.action_blocks:
            block = self.action_blocks[block_id]
            self.scene.removeItem(block)
            del self.action_blocks[block_id]

    def get_action_block(self, block_id: str):
        """Get action block by ID"""
        return self.action_blocks.get(block_id)

    def clear_all_blocks(self):
        """Clear all action blocks"""
        for block in self.action_blocks.values():
            self.scene.removeItem(block)
        self.action_blocks.clear()

    def set_playhead_position(self, position_ms: float):
        """Set playhead position"""
        self.playhead_position = max(0, min(position_ms, 60000))

        # Update time display
        minutes = int(self.playhead_position / 60000)
        seconds = int((self.playhead_position % 60000) / 1000)
        milliseconds = int(self.playhead_position % 1000)
        self.time_display.setText(f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}")

        # Redraw playhead
        self._draw_timeline()
        self._add_blocks_back()

        self.play_position_changed.emit(self.playhead_position)

    def _add_blocks_back(self):
        """Re-add blocks to scene after redraw"""
        for block_id, block in self.action_blocks.items():
            if block.scene() != self.scene:
                self.scene.addItem(block)

    def _on_selection_changed(self):
        """Handle selection change"""
        selected = self.scene.selectedItems()
        if selected and isinstance(selected[0], ActionBlock):
            block = selected[0]
            self.block_selected.emit(block.get_info())

    def _on_zoom_changed(self, value):
        """Handle zoom change"""
        self.zoom = value / 100.0

    def _on_scroll_changed(self, value):
        """Handle scroll change"""
        # Update scrollbars
        pass

    def mousePressEvent(self, event):
        """Handle mouse press"""
        if event.button() == Qt.LeftButton:
            # Update playhead position
            pos = self.graphics_view.mapToScene(self.graphics_view.mapFromGlobal(event.globalPos()))
            # Need to map properly from widget coordinates
            local_pos = self.graphics_view.mapFromParent(event.pos())
            scene_pos = self.graphics_view.mapToScene(local_pos)
            self.set_playhead_position(max(0, scene_pos.x()))

        super().mousePressEvent(event)

    def wheelEvent(self, event):
        """Handle mouse wheel for zoom"""
        if event.modifiers() == Qt.ControlModifier:
            # Zoom
            delta = event.angleDelta().y()
            new_value = self.zoom_slider.value() + (delta // 10)
            self.zoom_slider.setValue(max(50, min(300, new_value)))
        else:
            # Scroll
            super().wheelEvent(event)
