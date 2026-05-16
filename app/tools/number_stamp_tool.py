"""Number stamp tool: ogni click stampa un cerchio numerato (1, 2, 3...).

Utile per tutorial passo-passo: l'utente identifica i punti con numeri
crescenti, e Claude può riferirsi a "punto 1", "punto 2" nei suoi commenti.
Esc resetta il contatore.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QCursor, QFont, QPen
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsItemGroup,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
)

from .base_tool import BaseTool


STAMP_RADIUS = 16


class NumberStampTool(BaseTool):
    name = "number_stamp"

    def __init__(self) -> None:
        super().__init__()
        self._counter = 0

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.PointingHandCursor)

    def reset(self) -> None:
        self._counter = 0

    def on_press(
        self,
        scene: QGraphicsScene,
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ) -> Optional[QGraphicsItem]:
        self._counter += 1
        n = self._counter
        radius = max(STAMP_RADIUS, self.context.thickness * 4)

        group = QGraphicsItemGroup()
        group.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        group.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)

        circle = QGraphicsEllipseItem(
            QRectF(-radius, -radius, radius * 2, radius * 2)
        )
        col = QColor(self.context.color)
        circle.setBrush(QBrush(col))
        pen = QPen(QColor("#ffffff"), 2)
        circle.setPen(pen)
        group.addToGroup(circle)

        text = QGraphicsSimpleTextItem(str(n))
        font = QFont("Segoe UI", max(10, int(radius * 0.75)))
        font.setBold(True)
        text.setFont(font)
        text.setBrush(QBrush(QColor("#ffffff")))
        br = text.boundingRect()
        text.setPos(-br.width() / 2, -br.height() / 2)
        group.addToGroup(text)

        group.setPos(pos)
        scene.addItem(group)
        return group
