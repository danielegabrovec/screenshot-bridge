"""Tool linea: linea retta, linea tratteggiata, linea curva (Bezier).

Tutti supportano Shift per vincolare a multipli di 45° (le rette) e
muoversi con le maniglie come ogni altro item.
"""
from __future__ import annotations

import math
from typing import Optional

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QBrush, QCursor, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsScene,
)

from .base_tool import BaseTool


class LineTool(BaseTool):
    """Linea retta semplice senza punta di freccia."""

    name = "line"

    def __init__(self) -> None:
        super().__init__()
        self._start: Optional[QPointF] = None
        self._item: Optional[QGraphicsLineItem] = None
        self._dashed = False  # subclass DashedLineTool lo override

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.CrossCursor)

    def _make_pen(self) -> QPen:
        pen = QPen(self.context.color, self.context.thickness)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        if self._dashed:
            pen.setStyle(Qt.PenStyle.DashLine)
            # CapStyle Flat tiene i trattini netti; RoundCap li sfalsa.
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        return pen

    def on_press(
        self,
        scene: QGraphicsScene,
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ):
        self._start = QPointF(pos)
        item = QGraphicsLineItem(pos.x(), pos.y(), pos.x(), pos.y())
        item.setPen(self._make_pen())
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
        end = BaseTool.constrain_line(self._start, pos, modifiers)
        self._item.setLine(self._start.x(), self._start.y(), end.x(), end.y())

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


class DashedLineTool(LineTool):
    """Linea tratteggiata. Utile per indicare divisioni o asse virtuale."""

    name = "dashed_line"

    def __init__(self) -> None:
        super().__init__()
        self._dashed = True


class CurveTool(BaseTool):
    """Linea curva (Bezier quadratica).

    Drag dal punto A al punto B; il control point è calcolato a metà del
    segmento spostato perpendicolarmente di una frazione della lunghezza
    (verso il lato dove l'utente trascina). Risultato: trascinando dritto
    si ottiene una linea quasi retta, "piegando" durante il drag si curva.
    """

    name = "curve"

    def __init__(self) -> None:
        super().__init__()
        self._start: Optional[QPointF] = None
        self._item: Optional[QGraphicsPathItem] = None

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.CrossCursor)

    @staticmethod
    def _curve_path(start: QPointF, end: QPointF) -> QPainterPath:
        # Control point a metà del segmento, spostato perpendicolarmente
        # di un offset proporzionale alla distanza tra start ed end.
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        length = math.hypot(dx, dy)
        # Normale unitaria al segmento (ruotata di 90° CCW)
        if length < 1:
            nx, ny = 0.0, 0.0
        else:
            nx, ny = -dy / length, dx / length
        # Magnitudine: 30% della lunghezza
        bend = length * 0.30
        mid_x = (start.x() + end.x()) / 2.0 + nx * bend
        mid_y = (start.y() + end.y()) / 2.0 + ny * bend
        path = QPainterPath()
        path.moveTo(start)
        path.quadTo(mid_x, mid_y, end.x(), end.y())
        return path

    def on_press(
        self,
        scene: QGraphicsScene,
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ):
        self._start = QPointF(pos)
        item = QGraphicsPathItem(self._curve_path(pos, pos))
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
        self._item.setPath(self._curve_path(self._start, pos))

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


class DoubleArrowTool(BaseTool):
    """Linea con freccia a entrambi gli estremi: ↔.

    Utile per indicare distanze, scambi ("scambia A con B"), simmetrie.
    """

    name = "double_arrow"

    def __init__(self) -> None:
        super().__init__()
        self._start: Optional[QPointF] = None
        self._item: Optional[QGraphicsPathItem] = None

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.CrossCursor)

    @staticmethod
    def _path(start: QPointF, end: QPointF, thickness: int) -> QPainterPath:
        path = QPainterPath()
        path.moveTo(start)
        path.lineTo(end)
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        length = math.hypot(dx, dy)
        if length < 4:
            return path
        head_len = max(14.0, thickness * 3.5)
        head_ang = math.radians(28)
        ang = math.atan2(dy, dx)
        # punta a "end"
        l1 = QPointF(
            end.x() - head_len * math.cos(ang - head_ang),
            end.y() - head_len * math.sin(ang - head_ang),
        )
        r1 = QPointF(
            end.x() - head_len * math.cos(ang + head_ang),
            end.y() - head_len * math.sin(ang + head_ang),
        )
        path.moveTo(l1)
        path.lineTo(end)
        path.lineTo(r1)
        # punta a "start" (angolo + π)
        ang2 = ang + math.pi
        l2 = QPointF(
            start.x() - head_len * math.cos(ang2 - head_ang),
            start.y() - head_len * math.sin(ang2 - head_ang),
        )
        r2 = QPointF(
            start.x() - head_len * math.cos(ang2 + head_ang),
            start.y() - head_len * math.sin(ang2 + head_ang),
        )
        path.moveTo(l2)
        path.lineTo(start)
        path.lineTo(r2)
        return path

    def on_press(
        self,
        scene: QGraphicsScene,
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ):
        self._start = QPointF(pos)
        item = QGraphicsPathItem(self._path(pos, pos, self.context.thickness))
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
        end = BaseTool.constrain_line(self._start, pos, modifiers)
        self._item.setPath(self._path(self._start, end, self.context.thickness))

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
