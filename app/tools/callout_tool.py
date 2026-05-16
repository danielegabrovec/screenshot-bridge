"""Callout (fumetto/banner) con punta verso un punto.

Drag: il punto di press è la punta del callout, il punto di release è
l'angolo opposto del rettangolo testo. Subito dopo il rilascio il testo
entra in modalità editing così l'utente può scrivere l'ordine di modifica.
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
    QGraphicsTextItem,
)

from .base_tool import BaseTool


def _build_callout_path(tip: QPointF, body_rect: QRectF) -> QPainterPath:
    """Disegna un rounded-rect col body + un triangolo "punta" verso `tip`.

    La punta esce dal lato del body più vicino a `tip`.
    """
    path = QPainterPath()
    path.addRoundedRect(body_rect, 8, 8)

    # Determina il lato di uscita
    cx = body_rect.center().x()
    cy = body_rect.center().y()
    dx = tip.x() - cx
    dy = tip.y() - cy
    # Punta lateralmente se più "orizzontale" che verticale
    if abs(dx) > abs(dy):
        # esce a sinistra o destra
        side_x = body_rect.right() if dx > 0 else body_rect.left()
        y_anchor = max(body_rect.top() + 12, min(body_rect.bottom() - 12, tip.y()))
        triangle = QPainterPath()
        triangle.moveTo(side_x, y_anchor - 8)
        triangle.lineTo(tip.x(), tip.y())
        triangle.lineTo(side_x, y_anchor + 8)
        triangle.closeSubpath()
        path.addPath(triangle)
    else:
        side_y = body_rect.bottom() if dy > 0 else body_rect.top()
        x_anchor = max(body_rect.left() + 12, min(body_rect.right() - 12, tip.x()))
        triangle = QPainterPath()
        triangle.moveTo(x_anchor - 8, side_y)
        triangle.lineTo(tip.x(), tip.y())
        triangle.lineTo(x_anchor + 8, side_y)
        triangle.closeSubpath()
        path.addPath(triangle)
    return path


class CalloutTool(BaseTool):
    name = "callout"

    def __init__(self) -> None:
        super().__init__()
        self._tip: Optional[QPointF] = None
        self._body_start: Optional[QPointF] = None
        self._group: Optional[QGraphicsItemGroup] = None
        self._path_item: Optional[QGraphicsPathItem] = None
        self._text_item: Optional[QGraphicsTextItem] = None

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.CrossCursor)

    def on_press(
        self,
        scene: QGraphicsScene,
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ):
        self._tip = QPointF(pos)
        # Body iniziale: piccolo riquadro a partire dalla punta.
        self._body_start = QPointF(pos.x() + 40, pos.y() + 40)

        group = QGraphicsItemGroup()
        group.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        group.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)

        body_rect = QRectF(self._tip, self._body_start).normalized()
        path_item = QGraphicsPathItem(_build_callout_path(self._tip, body_rect))
        path_item.setPen(QPen(self.context.color, max(1, self.context.thickness)))
        # Fill semi-trasparente del colore selezionato così è leggibile su
        # qualsiasi sfondo.
        fill = QColor(self.context.color)
        fill.setAlpha(40)
        path_item.setBrush(QBrush(fill))
        group.addToGroup(path_item)

        text_item = QGraphicsTextItem("Scrivi qui…")
        font = QFont("Segoe UI", max(10, self.context.thickness * 3))
        text_item.setFont(font)
        text_item.setDefaultTextColor(self.context.color)
        text_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)
        text_item.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        text_item.setPos(body_rect.left() + 10, body_rect.top() + 6)
        group.addToGroup(text_item)

        scene.addItem(group)
        self._group = group
        self._path_item = path_item
        self._text_item = text_item
        return group

    def on_move(
        self,
        scene: QGraphicsScene,
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ) -> None:
        if self._tip is None or self._path_item is None:
            return
        body_rect = QRectF(self._tip, pos).normalized()
        # Garantisce un minimo per la dimensione del body
        if body_rect.width() < 80:
            body_rect.setWidth(80)
        if body_rect.height() < 36:
            body_rect.setHeight(36)
        self._path_item.setPath(_build_callout_path(self._tip, body_rect))
        if self._text_item is not None:
            self._text_item.setPos(body_rect.left() + 10, body_rect.top() + 6)
            self._text_item.setTextWidth(max(60, body_rect.width() - 20))

    def on_release(
        self,
        scene: QGraphicsScene,
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ):
        group = self._group
        # Entra subito in editing del testo e seleziona "Scrivi qui…"
        if self._text_item is not None:
            self._text_item.setFocus()
            cursor = self._text_item.textCursor()
            cursor.select(cursor.SelectionType.Document)
            self._text_item.setTextCursor(cursor)
        self._group = None
        self._path_item = None
        self._text_item = None
        self._tip = None
        self._body_start = None
        return group
