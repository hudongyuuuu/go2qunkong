# widgets/formation_preview.py
"""
Formation Preview Widget - Visual preview of robot formations
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QBrush, QRadialGradient

from models.group import Formation, FormationType
from config import COLORS


class FormationPreview(QWidget):
    """Formation preview widget using QPainter"""

    def __init__(self):
        super().__init__()

        self.formation = Formation(type=FormationType.LINE)
        self.robot_positions = []
        self.grid_size = 50  # pixels per meter
        self.robot_radius = 15

        self._apply_styles()

    def _apply_styles(self):
        """Apply widget styles"""
        self.setMinimumSize(400, 400)

    def set_formation(self, formation: Formation, robot_ids: list):
        """Set formation and calculate positions"""
        self.formation = formation
        self.robot_positions = formation.calculate_positions(
            robot_ids,
            center_x=0.0,
            center_y=0.0
        )
        self.update()

    def update_positions(self, positions: list):
        """Update robot positions directly"""
        self.robot_positions = positions
        self.update()

    def paintEvent(self, event):
        """Paint the formation preview"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Fill background
        painter.fillRect(self.rect(), QColor(COLORS['background']))

        # Calculate center and scale
        center_x = self.width() // 2
        center_y = self.height() // 2

        # Draw grid
        self._draw_grid(painter, center_x, center_y)

        # Draw formation
        self._draw_formation(painter, center_x, center_y)

        # Draw scale indicator
        self._draw_scale(painter)

    def _draw_grid(self, painter: QPainter, center_x: int, center_y: int):
        """Draw grid lines"""
        grid_pen = QPen(QColor(COLORS['grid']))
        grid_pen.setWidth(1)
        painter.setPen(grid_pen)

        # Draw vertical lines
        for x in range(center_x, self.width(), self.grid_size):
            painter.drawLine(x, 0, x, self.height())
        for x in range(center_x, 0, -self.grid_size):
            painter.drawLine(x, 0, x, self.height())

        # Draw horizontal lines
        for y in range(center_y, self.height(), self.grid_size):
            painter.drawLine(0, y, self.width(), y)
        for y in range(center_y, 0, -self.grid_size):
            painter.drawLine(0, y, self.width(), y)

        # Draw center axes
        axis_pen = QPen(QColor(COLORS['primary']))
        axis_pen.setWidth(2)
        painter.setPen(axis_pen)

        # X axis
        painter.drawLine(0, center_y, self.width(), center_y)
        # Y axis
        painter.drawLine(center_x, 0, center_x, self.height())

        # Draw axis labels
        painter.setPen(QColor(COLORS['text_secondary']))
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(5, center_y - 5, "Y")

        # Draw scale markers
        painter.setFont(QFont("Segoe UI", 8))
        for i in range(1, max(self.width(), self.height()) // self.grid_size):
            if center_x + i * self.grid_size < self.width():
                painter.drawText(center_x + i * self.grid_size - 10, center_y + 15, f"{i}m")
            if center_x - i * self.grid_size > 0:
                painter.drawText(center_x - i * self.grid_size - 10, center_y + 15, f"-{i}m")

    def _draw_formation(self, painter: QPainter, center_x: int, center_y: int):
        """Draw robots in formation"""
        if not self.robot_positions:
            # Draw empty state text
            painter.setPen(QColor(COLORS['text_secondary']))
            painter.setFont(QFont("Segoe UI", 14))
            text = "No robots in formation"
            rect = painter.fontMetrics().boundingRect(text)
            painter.drawText(
                center_x - rect.width() // 2,
                center_y,
                text
            )
            return

        for i, pos in enumerate(self.robot_positions):
            # Convert position to screen coordinates
            screen_x = center_x + int(pos.x * self.grid_size)
            screen_y = center_y - int(pos.y * self.grid_size)  # Flip Y axis

            # Draw robot
            self._draw_robot(painter, screen_x, screen_y, pos.robot_id, pos.rotation)

        # Draw connections between robots
        if len(self.robot_positions) > 1:
            connection_pen = QPen(QColor(COLORS['primary']))
            connection_pen.setWidth(1)
            connection_pen.setStyle(Qt.DotLine)
            painter.setPen(connection_pen)

            for i in range(len(self.robot_positions) - 1):
                pos1 = self.robot_positions[i]
                pos2 = self.robot_positions[i + 1]

                x1 = center_x + int(pos1.x * self.grid_size)
                y1 = center_y - int(pos1.y * self.grid_size)
                x2 = center_x + int(pos2.x * self.grid_size)
                y2 = center_y - int(pos2.y * self.grid_size)

                painter.drawLine(x1, y1, x2, y2)

    def _draw_robot(self, painter: QPainter, x: int, y: int, robot_id: str, rotation: float):
        """Draw a single robot"""
        # Create gradient for 3D effect
        gradient = QRadialGradient(QPointF(x - 3, y - 3), self.robot_radius)
        gradient.setColorAt(0, QColor(COLORS['primary']))
        gradient.setColorAt(1, QColor('#0088AA'))

        # Draw robot body
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(COLORS['accent']), 2))
        painter.drawEllipse(QPointF(x, y), self.robot_radius, self.robot_radius)

        # Draw direction indicator
        painter.setPen(QPen(QColor(COLORS['text_primary']), 2))
        angle_rad = 3.14159 * (90 - rotation) / 180  # Convert to radians and adjust
        end_x = x + int(self.robot_radius * 0.8 * 1.5 * (3.14159 / 180) * (90 - rotation))
        end_y = y + int(self.robot_radius * 0.8 * 1.5)
        painter.drawLine(x, y, x, y - int(self.robot_radius * 0.8))

        # Draw robot ID
        painter.setPen(QColor(COLORS['background']))
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))

        # Extract numeric part of ID
        id_num = ''.join(filter(str.isdigit, robot_id))
        if id_num:
            id_text = id_num[-2:]  # Last 2 digits
        else:
            id_text = robot_id[:2]

        rect = painter.fontMetrics().boundingRect(id_text)
        painter.drawText(
            x - rect.width() // 2,
            y + rect.height() // 3,
            id_text
        )

        # Draw robot name below
        painter.setPen(QColor(COLORS['text_secondary']))
        painter.setFont(QFont("Segoe UI", 8))
        rect = painter.fontMetrics().boundingRect(robot_id)
        painter.drawText(
            x - rect.width() // 2,
            y + self.robot_radius + 12,
            robot_id
        )

    def _draw_scale(self, painter: QPainter):
        """Draw scale indicator"""
        scale_length = self.grid_size  # 1 meter
        x = self.width() - 80
        y = self.height() - 30

        # Draw line
        painter.setPen(QPen(QColor(COLORS['text_primary']), 2))
        painter.drawLine(x, y, x + scale_length, y)

        # Draw end ticks
        painter.drawLine(x, y - 5, x, y + 5)
        painter.drawLine(x + scale_length, y - 5, x + scale_length, y + 5)

        # Draw label
        painter.setPen(QColor(COLORS['text_secondary']))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(x, y - 10, "1 meter")
