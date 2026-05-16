"""Rectangle / Ellipse tools."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QCursor, QPen
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
)

from .base_tool import BaseTool


class _ShapeBase(BaseTool):
    def __init__(self) -> None:
        super().__init__()
        self._start: Optional[QPointF] = None
        self._item: Optional[QGraphicsItem] = None

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.CrossCursor)

    def _make_item(self, rect: QRectF) -> QGraphicsItem:
        raise NotImplementedError

    def _update_rect(self, rect: QRectF) -> None:
        if isinstance(self._item, (QGraphicsRectItem, QGraphicsEllipseItem)):
            self._item.setRect(rect)

    def on_press(
        self,
        scene: QGraphicsScene,
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ):
        self._start = QPointF(pos)
        pen = QPen(self.context.color, self.context.thickness)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        item = self._make_item(QRectF(pos, pos))
        if isinstance(item, (QGraphicsRectItem, QGraphicsEllipseItem)):
            item.setPen(pen)
            item.setBrush(QBrush(Qt.GlobalColor.transparent))
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        scene.addItem(item)
        self._item = item
        return item

    def on_move(
        self,
        scene: QGraphicsScene,
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ) -> None:
        if self._start is None or self._item is None:
            return
        # Shift = vincolo quadrato/cerchio; Alt = disegna dal centro
        rect = BaseTool.constrain_rect(self._start, pos, modifiers)
        self._update_rect(rect)

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


class RectTool(_ShapeBase):
    name = "rect"

    def _make_item(self, rect: QRectF) -> QGraphicsItem:
        return QGraphicsRectItem(rect)


class EllipseTool(_ShapeBase):
    name = "ellipse"

    def _make_item(self, rect: QRectF) -> QGraphicsItem:
        return QGraphicsEllipseItem(rect)


class HighlightRectTool(_ShapeBase):
    """Evidenziatore rettangolare semi-trasparente giallo.

    Differisce dall'HighlighterTool (pen): è un rect pieno con alpha basso,
    ottimo per evidenziare aree intere (paragrafi, blocchi UI) in un colpo.
    """

    name = "highlight_rect"

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.IBeamCursor)

    def _make_item(self, rect: QRectF) -> QGraphicsItem:
        return QGraphicsRectItem(rect)

    def on_press(
        self,
        scene: QGraphicsScene,
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ):
        self._start = QPointF(pos)
        # Pen sottile dello stesso colore, brush semi-trasparente.
        from PyQt6.QtGui import QColor
        col = QColor(self.context.color)
        fill = QColor(col)
        fill.setAlpha(80)
        item = QGraphicsRectItem(QRectF(pos, pos))
        pen = QPen(col, max(1, self.context.thickness // 2))
        item.setPen(pen)
        item.setBrush(QBrush(fill))
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        scene.addItem(item)
        self._item = item
        return item
