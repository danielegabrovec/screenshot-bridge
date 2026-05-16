"""Marker tools: marcatori senza riempimento per indicare aree o stati.

- CornerMarkerTool: 4 angoli "L" come crop-marks per evidenziare un'area
  senza coprirla (utile quando vuoi indicare "questa parte" senza
  oscurare il contenuto sottostante).
- CheckStampTool: ad ogni click stampa un ✓ verde (per "OK / va bene così").
- CrossStampTool: ad ogni click stampa una ✗ rossa (per "togli questo").
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QCursor, QFont, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QGraphicsItem,
    QGraphicsItemGroup,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
)

from .base_tool import BaseTool


def _corner_marker_path(rect: QRectF, arm: float = 22.0) -> QPainterPath:
    """4 angoli a 'L' che marcano gli angoli del rect senza congiungerli."""
    p = QPainterPath()
    a = min(arm, rect.width() / 3, rect.height() / 3)
    # top-left
    p.moveTo(rect.left(), rect.top() + a)
    p.lineTo(rect.left(), rect.top())
    p.lineTo(rect.left() + a, rect.top())
    # top-right
    p.moveTo(rect.right() - a, rect.top())
    p.lineTo(rect.right(), rect.top())
    p.lineTo(rect.right(), rect.top() + a)
    # bottom-right
    p.moveTo(rect.right(), rect.bottom() - a)
    p.lineTo(rect.right(), rect.bottom())
    p.lineTo(rect.right() - a, rect.bottom())
    # bottom-left
    p.moveTo(rect.left() + a, rect.bottom())
    p.lineTo(rect.left(), rect.bottom())
    p.lineTo(rect.left(), rect.bottom() - a)
    return p


class CornerMarkerTool(BaseTool):
    name = "corner_marker"

    def __init__(self) -> None:
        super().__init__()
        self._start: Optional[QPointF] = None
        self._item: Optional[QGraphicsPathItem] = None

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
        rect = QRectF(pos, pos)
        item = QGraphicsPathItem(_corner_marker_path(rect))
        pen = QPen(self.context.color, max(2, self.context.thickness))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
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
        rect = BaseTool.constrain_rect(self._start, pos, modifiers)
        if rect.width() < 12:
            rect.setWidth(12)
        if rect.height() < 12:
            rect.setHeight(12)
        self._item.setPath(_corner_marker_path(rect))

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


def _make_stamp(glyph: str, color: QColor, radius: int) -> QGraphicsItemGroup:
    """Cerchietto colorato con bordo bianco + glyph centrato."""
    group = QGraphicsItemGroup()
    group.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
    group.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
    bg_rect = QRectF(-radius, -radius, radius * 2, radius * 2)
    bg_path = QPainterPath()
    bg_path.addEllipse(bg_rect)
    bg = QGraphicsPathItem(bg_path)
    bg.setBrush(QBrush(color))
    bg.setPen(QPen(QColor("#ffffff"), 2))
    group.addToGroup(bg)
    text = QGraphicsSimpleTextItem(glyph)
    font = QFont("Segoe UI", max(10, int(radius * 0.95)))
    font.setBold(True)
    text.setFont(font)
    text.setBrush(QBrush(QColor("#ffffff")))
    br = text.boundingRect()
    text.setPos(-br.width() / 2, -br.height() / 2)
    group.addToGroup(text)
    return group


class CheckStampTool(BaseTool):
    """Click → stampa un ✓ verde (OK / va bene)."""
    name = "check_stamp"

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.PointingHandCursor)

    def on_press(
        self,
        scene: QGraphicsScene,
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ):
        radius = max(14, self.context.thickness * 4)
        stamp = _make_stamp("✓", QColor("#22c55e"), radius)
        stamp.setPos(pos)
        scene.addItem(stamp)
        return stamp


class CrossStampTool(BaseTool):
    """Click → stampa una ✗ rossa (no / togli questo)."""
    name = "cross_stamp"

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.PointingHandCursor)

    def on_press(
        self,
        scene: QGraphicsScene,
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ):
        radius = max(14, self.context.thickness * 4)
        stamp = _make_stamp("✗", QColor("#ef4444"), radius)
        stamp.setPos(pos)
        scene.addItem(stamp)
        return stamp
