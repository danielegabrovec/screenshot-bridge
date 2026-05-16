"""Parentesi graffa { o } per indicare un range / un gruppo di elementi.

Il tool rileva automaticamente dall'asse del drag se la graffa è verticale
(drag mostly vertical) o orizzontale (drag mostly horizontal). La punta
della graffa esce dal lato perpendicolare verso il centro del drag — così
l'utente la posiziona accanto agli elementi che vuole raggruppare e la
punta indica naturalmente "questi elementi qui dentro".

Per cambiare orientamento dopo l'inserimento: tasto destro → Ruota di ±90°.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QBrush, QColor, QCursor, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsScene,
)

from .base_tool import BaseTool


def _build_brace_path(start: QPointF, end: QPointF) -> QPainterPath:
    """Costruisce la path della graffa fra `start` ed `end`.

    - Se |dy| > |dx|: graffa verticale, la punta sporge in orizzontale
      verso il lato opposto al verso del drag.
    - Altrimenti: graffa orizzontale, punta in verticale.
    """
    path = QPainterPath()
    dx = end.x() - start.x()
    dy = end.y() - start.y()

    if abs(dy) >= abs(dx):
        # Verticale. Estremi top/bot e punta che sporge orizzontalmente.
        top, bot = (start, end) if start.y() <= end.y() else (end, start)
        x = (start.x() + end.x()) / 2.0
        mid_y = (top.y() + bot.y()) / 2.0
        # Decidiamo il verso della punta: prefer "verso destra" quando il
        # drag punta verso destra (dx >= 0), altrimenti verso sinistra.
        tip_dx = 14.0 if dx >= 0 else -14.0
        path.moveTo(x, top.y())
        # Prima metà: curva da top a mid (con bump verso il "naso")
        path.cubicTo(
            x - tip_dx * 0.4, top.y() + (mid_y - top.y()) * 0.4,
            x + tip_dx, mid_y - (mid_y - top.y()) * 0.15,
            x + tip_dx, mid_y,
        )
        # Seconda metà: simmetrica verso bot
        path.cubicTo(
            x + tip_dx, mid_y + (bot.y() - mid_y) * 0.15,
            x - tip_dx * 0.4, mid_y + (bot.y() - mid_y) * 0.6,
            x, bot.y(),
        )
    else:
        # Orizzontale. Estremi left/right e punta verticale.
        lf, rt = (start, end) if start.x() <= end.x() else (end, start)
        y = (start.y() + end.y()) / 2.0
        mid_x = (lf.x() + rt.x()) / 2.0
        tip_dy = 14.0 if dy >= 0 else -14.0
        path.moveTo(lf.x(), y)
        path.cubicTo(
            lf.x() + (mid_x - lf.x()) * 0.4, y - tip_dy * 0.4,
            mid_x - (mid_x - lf.x()) * 0.15, y + tip_dy,
            mid_x, y + tip_dy,
        )
        path.cubicTo(
            mid_x + (rt.x() - mid_x) * 0.15, y + tip_dy,
            mid_x + (rt.x() - mid_x) * 0.6, y - tip_dy * 0.4,
            rt.x(), y,
        )
    return path


class BraceTool(BaseTool):
    name = "brace"

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
        path = _build_brace_path(pos, pos)
        item = QGraphicsPathItem(path)
        pen = QPen(self.context.color, self.context.thickness)
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
        # Shift = vincola alla verticale o orizzontale pura (asse maggiore).
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            dx = abs(pos.x() - self._start.x())
            dy = abs(pos.y() - self._start.y())
            if dy >= dx:
                pos = QPointF(self._start.x(), pos.y())
            else:
                pos = QPointF(pos.x(), self._start.y())
        self._item.setPath(_build_brace_path(self._start, pos))

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
