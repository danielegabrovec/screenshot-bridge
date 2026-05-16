"""Strategy interface for annotation tools."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QCursor

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QGraphicsItem, QGraphicsScene


@dataclass
class ToolContext:
    color: QColor
    thickness: int


class BaseTool:
    """Tools translate mouse events into QGraphicsItems on the scene.

    Subclasses override on_press/on_move/on_release. They return the item
    they created (if any) so the canvas can register it in the undo stack.

    `modifiers` permette ai tool di reagire a Shift/Alt/Ctrl per:
      - Shift: vincoli (quadrati, cerchi, angoli 45°)
      - Alt: forme disegnate dal centro
      - Ctrl: snap-to-grid (gestito dal canvas)
    """

    name: str = "base"

    def __init__(self) -> None:
        self.context: Optional[ToolContext] = None

    def set_context(self, context: ToolContext) -> None:
        self.context = context

    def cursor(self) -> QCursor:
        """Cursore custom mostrato sul viewport quando il tool è attivo."""
        return QCursor(Qt.CursorShape.CrossCursor)

    def on_press(
        self,
        scene: "QGraphicsScene",
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ) -> Optional["QGraphicsItem"]:
        return None

    def on_move(
        self,
        scene: "QGraphicsScene",
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ) -> None:
        return None

    def on_release(
        self,
        scene: "QGraphicsScene",
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ) -> Optional["QGraphicsItem"]:
        return None

    # ---- shared helpers ----------------------------------------------------

    @staticmethod
    def constrain_rect(
        origin: QPointF,
        current: QPointF,
        modifiers: Qt.KeyboardModifier,
    ) -> QRectF:
        """Calcola il rect finale rispettando Shift (quadrato) e Alt (centro)."""
        dx = current.x() - origin.x()
        dy = current.y() - origin.y()
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            s = max(abs(dx), abs(dy))
            dx = s if dx >= 0 else -s
            dy = s if dy >= 0 else -s
        if modifiers & Qt.KeyboardModifier.AltModifier:
            return QRectF(
                origin.x() - abs(dx),
                origin.y() - abs(dy),
                2 * abs(dx),
                2 * abs(dy),
            )
        return QRectF(
            QPointF(origin.x(), origin.y()),
            QPointF(origin.x() + dx, origin.y() + dy),
        ).normalized()

    @staticmethod
    def constrain_line(
        origin: QPointF,
        current: QPointF,
        modifiers: Qt.KeyboardModifier,
    ) -> QPointF:
        """Con Shift, snappa l'endpoint al multiplo di 45° più vicino."""
        if not (modifiers & Qt.KeyboardModifier.ShiftModifier):
            return current
        import math
        dx = current.x() - origin.x()
        dy = current.y() - origin.y()
        if dx == 0 and dy == 0:
            return current
        length = math.hypot(dx, dy)
        angle = math.atan2(dy, dx)
        step = math.pi / 4  # 45°
        snapped = round(angle / step) * step
        return QPointF(
            origin.x() + length * math.cos(snapped),
            origin.y() + length * math.sin(snapped),
        )
