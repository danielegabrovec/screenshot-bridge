"""Arrow tool: line + triangular arrowhead.

Uses a custom `ArrowItem` (QGraphicsPathItem subclass) that remembers its
start/end endpoints in item-local coordinates. This way the edit handles
can directly move an endpoint and call `set_endpoints()` to redraw the
arrow path, without losing precision through scale/rotation maths.
"""
from __future__ import annotations

import math
from typing import Optional

from PyQt6.QtCore import QLineF, QPointF, Qt
from PyQt6.QtGui import QBrush, QCursor, QPainterPath, QPen, QPolygonF
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QGraphicsScene

from .base_tool import BaseTool


HEAD_LENGTH = 18
HEAD_ANGLE = math.radians(28)


def _build_arrow_path(start: QPointF, end: QPointF, thickness: int) -> QPainterPath:
    path = QPainterPath()
    line = QLineF(start, end)
    if line.length() < 1:
        path.moveTo(start)
        path.lineTo(end)
        return path

    path.moveTo(start)
    path.lineTo(end)

    angle = math.atan2(end.y() - start.y(), end.x() - start.x())
    head_len = max(HEAD_LENGTH, thickness * 4)
    left = QPointF(
        end.x() - head_len * math.cos(angle - HEAD_ANGLE),
        end.y() - head_len * math.sin(angle - HEAD_ANGLE),
    )
    right = QPointF(
        end.x() - head_len * math.cos(angle + HEAD_ANGLE),
        end.y() - head_len * math.sin(angle + HEAD_ANGLE),
    )
    head = QPolygonF([end, left, right])
    path.addPolygon(head)
    path.closeSubpath()
    return path


class ArrowItem(QGraphicsPathItem):
    """Freccia con endpoint tracciati esplicitamente in coordinate item-local.

    Permette agli edit handle di muovere singolarmente l'origine o la fine
    chiamando `set_endpoints(start, end)`.
    """

    IS_ARROW = True  # marker per il handle manager

    def __init__(self, start: QPointF, end: QPointF, thickness: int) -> None:
        super().__init__(_build_arrow_path(start, end, thickness))
        self._start = QPointF(start)
        self._end = QPointF(end)
        self._thickness = thickness
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)

    # ---- Endpoints ---------------------------------------------------------

    def endpoints(self) -> tuple[QPointF, QPointF]:
        return QPointF(self._start), QPointF(self._end)

    def thickness(self) -> int:
        return self._thickness

    def set_endpoints(self, start: QPointF, end: QPointF) -> None:
        self.prepareGeometryChange()
        self._start = QPointF(start)
        self._end = QPointF(end)
        self.setPath(_build_arrow_path(self._start, self._end, self._thickness))

    def set_thickness(self, thickness: int) -> None:
        self._thickness = max(1, int(thickness))
        self.setPath(_build_arrow_path(self._start, self._end, self._thickness))


class ArrowTool(BaseTool):
    name = "arrow"

    def __init__(self) -> None:
        super().__init__()
        self._start: Optional[QPointF] = None
        self._item: Optional[ArrowItem] = None

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.CrossCursor)

    def on_press(
        self,
        scene: QGraphicsScene,
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ):
        self._start = QPointF(pos)
        pen = QPen(self.context.color, self.context.thickness)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        self._item = ArrowItem(pos, pos, self.context.thickness)
        self._item.setPen(pen)
        self._item.setBrush(QBrush(self.context.color))
        scene.addItem(self._item)
        return self._item

    def on_move(
        self,
        scene: QGraphicsScene,
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ) -> None:
        if self._item is None or self._start is None:
            return
        # Shift = snap a multipli di 45°
        end = BaseTool.constrain_line(self._start, pos, modifiers)
        self._item.set_endpoints(self._start, end)

    def on_release(
        self,
        scene: QGraphicsScene,
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ):
        item = self._item
        self._item = None
        self._start = None
        return item
