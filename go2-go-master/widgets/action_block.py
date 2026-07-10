# widgets/action_block.py
"""
Action Block Widget - Draggable action block for timeline
"""

from PyQt5.QtWidgets import (QGraphicsItem, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QFrame)
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QBrush

from models.action import Action
from config import COLORS


class ActionBlock(QGraphicsItem):
    """Draggable action block for timeline"""

    # Signals
    block_clicked = pyqtSignal(str)
    block_double_clicked = pyqtSignal(str)

    # Color mapping for action types
    ACTION_COLORS = {
        'stand': '#00FF88',
        'sit': '#FFB800',
        'walk': '#00D4FF',
        'trot': '#00FFFF',
        'run': '#FF4757',
        'jump': '#FF6B9D',
        'turn_left': '#A855F7',
        'turn_right': '#A855F7',
        'wave_hand': '#F472B6',
        'dance_move_1': '#34D399',
        'dance_move_2': '#60A5FA',
        'dance_move_3': '#A78BFA',
        'dance_move_4': '#F472B6',
        'dance_move_5': '#FBBF24',
    }

    def __init__(self, action: Action, start_time: float, duration: float):
        super().__init__()

        self.action = action
        self.start_time = start_time  # in milliseconds
        self.duration = duration  # in milliseconds
        self._height = 60
        self._min_width = 100

        # Make item selectable and movable
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

        self._is_hovered = False

    @property
    def end_time(self) -> float:
        """Get end time"""
        return self.start_time + self.duration

    def get_color(self) -> QColor:
        """Get color for this action type"""
        color_hex = self.ACTION_COLORS.get(
            self.action.type.value,
            COLORS['primary']
        )
        return QColor(color_hex)

    def boundingRect(self) -> QRectF:
        """Get bounding rectangle"""
        return QRectF(0, 0, max(self._min_width, self.duration), self._height)

    def paint(self, painter: QPainter, option: QWidget, widget: QWidget = None):
        """Paint the action block"""
        # Setup painter
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.boundingRect()

        # Draw background
        if self.isSelected():
            # Selected state
            painter.setBrush(self.get_color().lighter(120))
            painter.setPen(QPen(QColor(COLORS['accent']), 3))
        elif self._is_hovered:
            # Hover state
            painter.setBrush(self.get_color().lighter(110))
            painter.setPen(QPen(QColor(COLORS['primary']), 2))
        else:
            # Normal state
            painter.setBrush(self.get_color())
            painter.setPen(QPen(QColor(COLORS['background']), 2))

        # Draw rounded rectangle
        radius = 8
        painter.drawRoundedRect(rect, radius, radius)

        # Draw action name
        painter.setPen(QColor(COLORS['background']))
        painter.setFont(QFont("Segoe UI", 11, QFont.Bold))

        name_rect = rect.adjusted(10, 5, -10, -35)
        painter.drawText(name_rect, Qt.AlignLeft | Qt.AlignTop, self.action.name)

        # Draw action type
        painter.setFont(QFont("Segoe UI", 9))
        type_rect = rect.adjusted(10, 25, -10, -5)
        painter.drawText(type_rect, Qt.AlignLeft | Qt.AlignTop, self.action.type.value)

        # Draw duration
        duration_text = f"{self.duration / 1000:.1f}s"
        painter.drawText(type_rect, Qt.AlignRight | Qt.AlignTop, duration_text)

        # Draw grip handle
        grip_rect = QRectF(5, rect.height() - 20, 10, 15)
        painter.setBrush(QColor(COLORS['background']).darker(120))
        painter.drawRect(grip_rect)

        # Draw resize handle on right
        resize_rect = QRectF(rect.width() - 15, rect.height() - 20, 10, 15)
        painter.setBrush(QColor(COLORS['background']).darker(120))
        painter.drawRect(resize_rect)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        """Handle item changes"""
        if change == QGraphicsItem.ItemPositionHasChanged:
            # Snap to grid (100ms)
            new_x = round(value.x() / 100) * 100
            new_y = round(value.y() / 60) * 60  # Snap to track height
            self.setPos(new_x, new_y)

        return super().itemChange(change, value)

    def hoverEnterEvent(self, event):
        """Handle hover enter"""
        self._is_hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Handle hover leave"""
        self._is_hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        """Handle mouse press"""
        if event.button() == Qt.LeftButton:
            self.block_clicked.emit(self.action.id)

        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Handle double click"""
        self.block_double_clicked.emit(self.action.id)
        super().mouseDoubleClickEvent(event)

    def set_start_time(self, time_ms: float):
        """Set start time"""
        self.start_time = time_ms
        self.setPos(time_ms, self.y())

    def set_duration(self, duration_ms: float):
        """Set duration"""
        self.duration = max(100, duration_ms)  # Minimum 100ms

    def get_info(self) -> dict:
        """Get action block info"""
        return {
            'action_id': self.action.id,
            'action_name': self.action.name,
            'action_type': self.action.type.value,
            'start_time': self.start_time,
            'duration': self.duration,
            'end_time': self.end_time,
        }
