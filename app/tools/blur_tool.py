"""Redact tool: rettangolo nero opaco con etichetta 'REDACTED' al centro.

NB: implementato come rettangolo nero pieno + testo bianco, NON come blur
gaussiano vero. Motivo: `QGraphicsBlurEffect` non viene catturato bene da
`QGraphicsScene.render()` su QPainter target, l'export PNG ne risulta
incoerente. Per privacy/handoff a Claude è preferibile uno stato visibile
("REDACTED") rispetto a un blur reversibile.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QCursor, QFont, QPen
from PyQt6.QtWidgets import (
    QGraphicsItem,
    QGraphicsItemGroup,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
)

from .base_tool import BaseTool


class RedactTool(BaseTool):
    name = "redact"

    def __init__(self) -> None:
        super().__init__()
        self._start: Optional[QPointF] = None
        self._group: Optional[QGraphicsItemGroup] = None
        self._rect_item: Optional[QGraphicsRectItem] = None
        self._label: Optional[QGraphicsSimpleTextItem] = None

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.ForbiddenCursor)

    def on_press(
        self,
        scene: QGraphicsScene,
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ):
        self._start = QPointF(pos)
        rect = QRectF(pos, pos)
        group = QGraphicsItemGroup()
        group.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        group.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)

        rect_item = QGraphicsRectItem(rect)
        rect_item.setPen(QPen(QColor("#0f172a"), 1))
        rect_item.setBrush(QBrush(QColor("#0f172a")))
        group.addToGroup(rect_item)

        label = QGraphicsSimpleTextItem("REDACTED")
        font = QFont("Segoe UI", 9)
        font.setBold(True)
        label.setFont(font)
        label.setBrush(QBrush(QColor("#ef4444")))
        group.addToGroup(label)

        scene.addItem(group)
        self._group = group
        self._rect_item = rect_item
        self._label = label
        return group

    def on_move(
        self,
        scene: QGraphicsScene,
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ) -> None:
        if self._start is None or self._rect_item is None or self._label is None:
            return
        rect = BaseTool.constrain_rect(self._start, pos, modifiers)
        self._rect_item.setRect(rect)
        # Centra l'etichetta se la box è abbastanza grande.
        br = self._label.boundingRect()
        if rect.width() > br.width() + 12 and rect.height() > br.height() + 8:
            self._label.setVisible(True)
            self._label.setPos(
                rect.x() + (rect.width() - br.width()) / 2,
                rect.y() + (rect.height() - br.height()) / 2,
            )
        else:
            self._label.setVisible(False)

    def on_release(
        self,
        scene: QGraphicsScene,
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ):
        group = self._group
        self._group = None
        self._rect_item = None
        self._label = None
        self._start = None
        return group
