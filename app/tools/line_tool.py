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


def _quadratic_path(start: QPointF, control: QPointF, end: QPointF) -> QPainterPath:
    path = QPainterPath()
    path.moveTo(start)
    path.quadTo(control, end)
    return path


def _default_control(start: QPointF, end: QPointF) -> QPointF:
    """Control point a metà segmento, spostato perpendicolarmente del 30%."""
    dx = end.x() - start.x()
    dy = end.y() - start.y()
    length = math.hypot(dx, dy)
    if length < 1:
        nx, ny = 0.0, 0.0
    else:
        nx, ny = -dy / length, dx / length
    bend = length * 0.30
    return QPointF(
        (start.x() + end.x()) / 2.0 + nx * bend,
        (start.y() + end.y()) / 2.0 + ny * bend,
    )


class CurveItem(QGraphicsPathItem):
    """Curva Bezier quadratica con endpoint e control point modificabili.

    Mantiene start/control/end in coordinate item-local così l'EditHandle
    manager può muovere ciascuno indipendentemente (analogo a ArrowItem).
    Marker `IS_CURVE = True` per il riconoscimento nel manager.
    """

    IS_CURVE = True  # marker per EditHandleManager

    def __init__(self, start: QPointF, end: QPointF) -> None:
        ctrl = _default_control(start, end)
        super().__init__(_quadratic_path(start, ctrl, end))
        self._start = QPointF(start)
        self._end = QPointF(end)
        self._control = QPointF(ctrl)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)

    def endpoints(self) -> tuple[QPointF, QPointF]:
        return QPointF(self._start), QPointF(self._end)

    def control_point(self) -> QPointF:
        return QPointF(self._control)

    def set_endpoints(self, start: QPointF, end: QPointF) -> None:
        self.prepareGeometryChange()
        self._start = QPointF(start)
        self._end = QPointF(end)
        self.setPath(_quadratic_path(self._start, self._control, self._end))

    def set_control_point(self, control: QPointF) -> None:
        self.prepareGeometryChange()
        self._control = QPointF(control)
        self.setPath(_quadratic_path(self._start, self._control, self._end))


class CurveTool(BaseTool):
    """Linea curva Bezier con control point handle modificabile.

    Drag dal punto A al punto B; il control point è inizializzato a metà
    del segmento, spostato perpendicolarmente del 30%. Dopo il rilascio
    l'utente può selezionare la curva e trascinare la maniglia del
    control point per modellarla.
    """

    name = "curve"

    def __init__(self) -> None:
        super().__init__()
        self._start: Optional[QPointF] = None
        self._item: Optional[CurveItem] = None

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
        item = CurveItem(pos, pos)
        pen = QPen(self.context.color, self.context.thickness)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        item.setPen(pen)
        item.setBrush(QBrush(Qt.GlobalColor.transparent))
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
        # Aggiorniamo endpoint+control automaticamente (control resta
        # proporzionalmente "in mezzo, perpendicolare").
        new_end = pos
        new_ctrl = _default_control(self._start, new_end)
        self._item.set_endpoints(self._start, new_end)
        self._item.set_control_point(new_ctrl)

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
