# models/group.py
"""
Group and Formation Data Models
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import math


class FormationType(Enum):
    """Formation types for robot groups"""
    LINE = "line"
    COLUMN = "column"
    SQUARE = "square"
    CIRCLE = "circle"
    V_SHAPE = "v_shape"
    TRIANGLE = "triangle"
    DIAMOND = "diamond"
    ARROW = "arrow"
    CUSTOM = "custom"


@dataclass
class FormationPosition:
    """Position in a formation"""
    robot_id: str
    x: float
    y: float
    rotation: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'robot_id': self.robot_id,
            'x': self.x,
            'y': self.y,
            'rotation': self.rotation,
        }


@dataclass
class Formation:
    """Formation configuration"""
    type: FormationType
    spacing: float = 1.0  # meters between robots
    orientation: float = 0.0  # degrees
    custom_positions: List[FormationPosition] = field(default_factory=list)

    def calculate_positions(self, robot_ids: List[str], center_x: float = 0.0, center_y: float = 0.0) -> List[FormationPosition]:
        """Calculate positions for robots in this formation"""
        positions = []
        count = len(robot_ids)

        if self.type == FormationType.CUSTOM and self.custom_positions:
            # Use custom positions
            return self.custom_positions

        elif self.type == FormationType.LINE:
            # Horizontal line
            total_width = (count - 1) * self.spacing
            start_x = center_x - total_width / 2

            for i, robot_id in enumerate(robot_ids):
                positions.append(FormationPosition(
                    robot_id=robot_id,
                    x=start_x + i * self.spacing,
                    y=center_y,
                    rotation=self.orientation
                ))

        elif self.type == FormationType.COLUMN:
            # Vertical line
            total_height = (count - 1) * self.spacing
            start_y = center_y - total_height / 2

            for i, robot_id in enumerate(robot_ids):
                positions.append(FormationPosition(
                    robot_id=robot_id,
                    x=center_x,
                    y=start_y + i * self.spacing,
                    rotation=self.orientation
                ))

        elif self.type == FormationType.SQUARE:
            # Square/Rectangle formation
            side = math.ceil(math.sqrt(count))
            total_width = (side - 1) * self.spacing
            total_height = (side - 1) * self.spacing
            start_x = center_x - total_width / 2
            start_y = center_y - total_height / 2

            for i, robot_id in enumerate(robot_ids):
                row = i // side
                col = i % side
                positions.append(FormationPosition(
                    robot_id=robot_id,
                    x=start_x + col * self.spacing,
                    y=start_y + row * self.spacing,
                    rotation=self.orientation
                ))

        elif self.type == FormationType.CIRCLE:
            # Circle formation
            radius = (count * self.spacing) / (2 * math.pi)

            for i, robot_id in enumerate(robot_ids):
                angle = (2 * math.pi * i) / count + math.radians(self.orientation)
                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
                positions.append(FormationPosition(
                    robot_id=robot_id,
                    x=x,
                    y=y,
                    rotation=math.degrees(angle) + 90  # Face outward
                ))

        elif self.type == FormationType.V_SHAPE:
            # V-formation (like geese flying)
            for i, robot_id in enumerate(robot_ids):
                if i == 0:
                    # Leader at center front
                    positions.append(FormationPosition(
                        robot_id=robot_id,
                        x=center_x,
                        y=center_y + 2 * self.spacing,
                        rotation=self.orientation
                    ))
                else:
                    # Alternating left and right
                    side = 1 if i % 2 == 1 else -1
                    row = (i + 1) // 2
                    offset_x = side * row * self.spacing
                    offset_y = center_y + 2 * self.spacing - row * self.spacing

                    positions.append(FormationPosition(
                        robot_id=robot_id,
                        x=center_x + offset_x,
                        y=offset_y,
                        rotation=self.orientation
                    ))

        elif self.type == FormationType.TRIANGLE:
            # Triangle formation
            positions.extend(self._create_triangle(robot_ids, center_x, center_y))

        elif self.type == FormationType.DIAMOND:
            # Diamond formation
            positions.extend(self._create_diamond(robot_ids, center_x, center_y))

        elif self.type == FormationType.ARROW:
            # Arrow formation
            positions.extend(self._create_arrow(robot_ids, center_x, center_y))

        return positions

    def _create_triangle(self, robot_ids: List[str], center_x: float, center_y: float) -> List[FormationPosition]:
        """Create triangle formation"""
        positions = []
        count = len(robot_ids)

        if count >= 1:
            # Tip
            positions.append(FormationPosition(
                robot_id=robot_ids[0],
                x=center_x,
                y=center_y + 2 * self.spacing,
                rotation=self.orientation
            ))

        if count >= 3:
            # Middle row
            mid_start_x = center_x - self.spacing / 2
            for i in range(min(2, count - 1)):
                if 1 + i < count:
                    positions.append(FormationPosition(
                        robot_id=robot_ids[1 + i],
                        x=mid_start_x + i * self.spacing,
                        y=center_y + self.spacing,
                        rotation=self.orientation
                    ))

        if count >= 6:
            # Back row
            back_start_x = center_x - self.spacing
            for i in range(min(3, count - 3)):
                if 3 + i < count:
                    positions.append(FormationPosition(
                        robot_id=robot_ids[3 + i],
                        x=back_start_x + i * self.spacing,
                        y=center_y,
                        rotation=self.orientation
                    ))

        # Fill remaining in back
        if count > 6:
            extra_start_x = center_x - 1.5 * self.spacing
            for i in range(count - 6):
                if 6 + i < count:
                    positions.append(FormationPosition(
                        robot_id=robot_ids[6 + i],
                        x=extra_start_x + (i % 4) * self.spacing,
                        y=center_y - self.spacing,
                        rotation=self.orientation
                    ))

        return positions

    def _create_diamond(self, robot_ids: List[str], center_x: float, center_y: float) -> List[FormationPosition]:
        """Create diamond formation"""
        positions = []
        count = len(robot_ids)

        if count >= 1:
            # Top
            positions.append(FormationPosition(
                robot_id=robot_ids[0],
                x=center_x,
                y=center_y + 2 * self.spacing,
                rotation=self.orientation
            ))

        if count >= 3:
            # Middle row
            for i in range(min(2, count - 1)):
                offset = -self.spacing / 2 if i == 0 else self.spacing / 2
                if 1 + i < count:
                    positions.append(FormationPosition(
                        robot_id=robot_ids[1 + i],
                        x=center_x + offset,
                        y=center_y + self.spacing,
                        rotation=self.orientation
                    ))

        if count >= 5:
            # Center
            if 3 < count:
                positions.append(FormationPosition(
                    robot_id=robot_ids[3],
                    x=center_x,
                    y=center_y,
                    rotation=self.orientation
                ))

        if count >= 7:
            # Bottom row
            for i in range(min(2, count - 4)):
                offset = -self.spacing / 2 if i == 0 else self.spacing / 2
                if 4 + i < count:
                    positions.append(FormationPosition(
                        robot_id=robot_ids[4 + i],
                        x=center_x + offset,
                        y=center_y - self.spacing,
                        rotation=self.orientation
                    ))

        if count >= 8:
            # Bottom
            if 7 < count:
                positions.append(FormationPosition(
                    robot_id=robot_ids[7],
                    x=center_x,
                    y=center_y - 2 * self.spacing,
                    rotation=self.orientation
                ))

        # Fill remaining
        for i in range(8, count):
            positions.append(FormationPosition(
                robot_id=robot_ids[i],
                x=center_x + ((i - 8) % 3 - 1) * self.spacing,
                y=center_y - 2 * self.spacing - ((i - 8) // 3) * self.spacing,
                rotation=self.orientation
            ))

        return positions

    def _create_arrow(self, robot_ids: List[str], center_x: float, center_y: float) -> List[FormationPosition]:
        """Create arrow formation"""
        positions = []
        count = len(robot_ids)

        # Arrow tip
        if count >= 1:
            positions.append(FormationPosition(
                robot_id=robot_ids[0],
                x=center_x,
                y=center_y + 2 * self.spacing,
                rotation=self.orientation
            ))

        # Arrow head sides
        if count >= 3:
            head_start_x = center_x - self.spacing
            for i in range(min(2, count - 1)):
                if 1 + i < count:
                    positions.append(FormationPosition(
                        robot_id=robot_ids[1 + i],
                        x=head_start_x + i * self.spacing,
                        y=center_y + self.spacing,
                        rotation=self.orientation
                    ))

        # Arrow body (vertical line)
        if count > 3:
            for i in range(count - 3):
                if 3 + i < count:
                    positions.append(FormationPosition(
                        robot_id=robot_ids[3 + i],
                        x=center_x,
                        y=center_y - i * self.spacing,
                        rotation=self.orientation
                    ))

        return positions

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'type': self.type.value,
            'spacing': self.spacing,
            'orientation': self.orientation,
            'custom_positions': [p.to_dict() for p in self.custom_positions],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Formation':
        """Create from dictionary"""
        return cls(
            type=FormationType(data['type']),
            spacing=data.get('spacing', 1.0),
            orientation=data.get('orientation', 0.0),
            custom_positions=[
                FormationPosition(**p) for p in data.get('custom_positions', [])
            ]
        )
