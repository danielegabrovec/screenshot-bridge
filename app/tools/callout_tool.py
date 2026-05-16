"""Callout (fumetto/banner) con punta verso un punto.

Drag: il punto di press è la punta del callout, il punto di release è
l'angolo opposto del rettangolo testo. Subito dopo il rilascio il testo
entra in modalità editing così l'utente può scrivere l'ordine di modifica.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QCursor, QFont, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QGraphicsItem,
    QGraphicsItemGroup,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
    QGraphicsTextItem,
)

from .base_tool import BaseTool


def _give_focus_to_text_child(group: QGraphicsItemGroup, scene_pos: QPointF) -> bool:
    """Se sotto scene_pos c'è un QGraphicsTextItem child editabile, gli dà
    il focus e ritorna True. Altrimenti False (l'evento andrà al group)."""
    sc = group.scene()
    if sc is None:
        return False
    for it in sc.items(scene_pos):
        if not isinstance(it, QGraphicsTextItem):
            continue
        # Risali il parent chain: deve essere child del nostro group
        parent = it.parentItem()
        is_child = False
        while parent is not None:
            if parent is group:
                is_child = True
                break
            parent = parent.parentItem()
        if not is_child:
            continue
        if not (it.textInteractionFlags() & Qt.TextInteractionFlag.TextEditorInteraction):
            continue
        # Dai focus immediato
        sc.clearSelection()
        sc.setFocusItem(it, Qt.FocusReason.MouseFocusReason)
        it.setFocus(Qt.FocusReason.MouseFocusReason)
        for view in sc.views():
            view.setFocus(Qt.FocusReason.MouseFocusReason)
        return True
    return False


class _CalloutGroup(QGraphicsItemGroup):
    """Group del callout. Override mousePressEvent per dare priorità al
    text item interno (altrimenti il group movable cattura il click e
    l'editing non parte)."""

    IS_CALLOUT = True

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            if _give_focus_to_text_child(self, event.scenePos()):
                event.accept()
                return
        super().mousePressEvent(event)


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

        group = _CalloutGroup()
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
        text_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        text_item.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        # Default text width per forzare word-wrap dentro al body.
        text_item.setTextWidth(max(60, self._body_start.x() - self._tip.x() - 20))
        text_item.setPos(body_rect.left() + 10, body_rect.top() + 6)
        group.addToGroup(text_item)
        # Marker per identificare i callout fuori dal tool (es. nel canvas
        # per dare focus al text item quando si seleziona il group).
        group.IS_CALLOUT = True  # type: ignore[attr-defined]
        group._callout_text = text_item  # type: ignore[attr-defined]

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
        text_item = self._text_item  # capture prima del clear
        # Entra subito in editing del testo e seleziona "Scrivi qui…".
        # Posticipiamo al prossimo tick con singleShot(0): se chiamiamo
        # setFocus() ora, Qt riassegna il focus al group come "ultimo item
        # cliccato" appena finisce il mouseReleaseEvent. Con il timer il
        # focus arriva DOPO che il release è stato processato.
        if text_item is not None:
            def _grab_focus() -> None:
                sc = text_item.scene()
                if sc is None:
                    return
                # 1. Deseleziona TUTTO (incluso il group del callout) per
                #    evitare che il group rubi il focus al text item.
                sc.clearSelection()
                # 2. Forza il view ad avere keyboard focus (altrimenti gli
                #    eventi tastiera non arrivano a Qt → nessuno digita).
                for view in sc.views():
                    view.setFocus(Qt.FocusReason.OtherFocusReason)
                # 3. Assegna il focus item della scena al text_item.
                sc.setFocusItem(text_item, Qt.FocusReason.OtherFocusReason)
                text_item.setFocus(Qt.FocusReason.OtherFocusReason)
                # 4. Seleziona "Scrivi qui…" così basta digitare per
                #    sostituirlo.
                cursor = text_item.textCursor()
                cursor.select(cursor.SelectionType.Document)
                text_item.setTextCursor(cursor)
            # 50ms invece di 0: dà a Qt il tempo di completare il proprio
            # focus management dopo il mouseReleaseEvent. Con 0 Qt poteva
            # ancora sovrascrivere il focus subito dopo.
            QTimer.singleShot(50, _grab_focus)
        self._group = None
        self._path_item = None
        self._text_item = None
        self._tip = None
        self._body_start = None
        return group
