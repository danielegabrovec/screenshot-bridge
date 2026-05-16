"""Free-hand pen + highlighter variant."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QCursor, QPainterPath, QPen
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QGraphicsScene

from .base_tool import BaseTool


class PenTool(BaseTool):
    name = "pen"
    alpha: int = 255
    width_multiplier: float = 1.0

    def __init__(self) -> None:
        super().__init__()
        self._path: Optional[QPainterPath] = None
        self._item: Optional[QGraphicsPathItem] = None
        self._start: Optional[QPointF] = None

    def cursor(self) -> QCursor:
        # Cursor a "+" centrato è meglio della freccia di sistema per il disegno
        return QCursor(Qt.CursorShape.CrossCursor)

    def _pen(self) -> QPen:
        color = QColor(self.context.color)
        color.setAlpha(self.alpha)
        pen = QPen(color, max(1, int(self.context.thickness * self.width_multiplier)))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        return pen

    def on_press(
        self,
        scene: QGraphicsScene,
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ):
        self._start = QPointF(pos)
        self._path = QPainterPath(pos)
        self._item = QGraphicsPathItem(self._path)
        self._item.setPen(self._pen())
        self._item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self._item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        scene.addItem(self._item)
        return self._item

    def on_move(
        self,
        scene: QGraphicsScene,
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ) -> None:
        if self._path is None or self._item is None or self._start is None:
            return
        # Shift in pen mode = linea retta dall'origine (resetta path ogni move)
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            end = BaseTool.constrain_line(self._start, pos, modifiers)
            new_path = QPainterPath(self._start)
            new_path.lineTo(end)
            self._path = new_path
            self._item.setPath(new_path)
            return
        self._path.lineTo(pos)
        self._item.setPath(self._path)

    def on_release(
        self,
        scene: QGraphicsScene,
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ):
        item = self._item
        self._item = None
        self._path = None
        self._start = None
        return item


class HighlighterTool(PenTool):
    name = "highlighter"
    alpha = 100
    width_multiplier = 4.0
