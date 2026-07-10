# widgets/status_indicator.py
"""
Status Indicator Widget - Animated connection status indicator
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QRadialGradient


class StatusIndicator(QWidget):
    """Animated status indicator widget"""

    STATUS_COLORS = {
        'connected': '#00FF88',    # Green
        'connecting': '#FFB800',   # Yellow
        'disconnected': '#5A6A8A', # Gray
        'error': '#FF4757',        # Red
        'busy': '#FFB800',         # Yellow
    }

    def __init__(self, status: str = 'disconnected', size: int = 16):
        super().__init__()
        self._status = status
        self._size = size
        self._animation_step = 0
        self._is_animating = False

        self.setFixedSize(size, size)

        # Animation timer
        self._animation_timer = QTimer()
        self._animation_timer.timeout.connect(self._update_animation)
        self._animation_timer.setInterval(50)  # 20 FPS

    def set_status(self, status: str):
        """Set status"""
        self._status = status

        # Animate for connecting and busy states
        if status in ['connecting', 'busy']:
            if not self._is_animating:
                self._is_animating = True
                self._animation_timer.start()
        else:
            self._is_animating = False
            self._animation_timer.stop()
            self._animation_step = 0

        self.update()

    def get_status(self) -> str:
        """Get current status"""
        return self._status

    def _update_animation(self):
        """Update animation step"""
        self._animation_step = (self._animation_step + 1) % 20
        self.update()

    def paintEvent(self, event):
        """Paint the status indicator"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Get base color
        color = QColor(self.STATUS_COLORS.get(self._status, '#5A6A8A'))

        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = min(self.width(), self.height()) / 2 - 1

        if self._is_animating:
            # Draw pulsing animation
            pulse_radius = radius * (0.5 + 0.5 * (1 + self._animation_step) / 20)
            alpha = int(255 * (1 - (self._animation_step / 20)))

            gradient = QRadialGradient(QPointF(center_x, center_y), pulse_radius)
            gradient.setColorAt(0, QColor(color.red(), color.green(), color.blue(), alpha))
            gradient.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))

            painter.setBrush(gradient)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(center_x, center_y), pulse_radius, pulse_radius)

        # Draw main circle
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(center_x, center_y), radius, radius)

        # Draw inner highlight
        painter.setBrush(QColor(255, 255, 255, 100))
        painter.drawEllipse(QPointF(center_x - radius * 0.3, center_y - radius * 0.3),
                           radius * 0.2, radius * 0.2)
