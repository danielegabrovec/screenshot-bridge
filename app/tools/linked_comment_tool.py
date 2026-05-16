"""Commento collegato: callout body + linea tratteggiata persistente.

A differenza del CalloutTool (punta triangolare solida), questo tool
mantiene una linea tratteggiata fra un "anchor point" fisso sulla scena
e il bordo del callout. Il callout può essere spostato liberamente:
la linea segue sempre, riaggrappandosi al lato del callout più vicino
all'anchor.

Workflow:
- Click sul punto da commentare (anchor point).
- Drag fino al punto dove vuoi piazzare il body del callout.
- Rilascia: il body entra in editing testo.
- Sposta poi il commento ovunque, la linea segue.

Implementazione:
- LinkedCommentItem è un QGraphicsItemGroup che contiene il body+testo+linea.
- L'anchor point è memorizzato in scene-coords ASSOLUTE.
- itemChange(ItemPositionHasChanged) ricalcola la linea ad ogni movimento
  del group, mantenendo l'anchor fisso.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QCursor, QFont, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QGraphicsItem,
    QGraphicsItemGroup,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsTextItem,
)

from .base_tool import BaseTool


class LinkedCommentItem(QGraphicsItemGroup):
    """Callout box + testo + linea tratteggiata verso un anchor fisso."""

    IS_LINKED_COMMENT = True  # marker simile a IS_CALLOUT

    def __init__(
        self,
        anchor_scene: QPointF,
        body_rect_scene: QRectF,
        color: QColor,
    ) -> None:
        super().__init__()
        # NB: inizializza gli attributi richiesti da _update_link() PRIMA di
        # chiamare setPos() o di abilitare ItemSendsGeometryChanges, altrimenti
        # itemChange viene invocato durante il costruttore e crasha.
        self._anchor_scene = QPointF(anchor_scene)
        self._color = QColor(color)
        self._local_rect = QRectF(0, 0, body_rect_scene.width(), body_rect_scene.height())

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)

        # Body in coord LOCALI: posizioniamo il group sul topLeft del body_rect
        # e usiamo coordinate locali con origine (0, 0).
        self.setPos(body_rect_scene.topLeft())
        local_rect = self._local_rect

        # Box arrotondato
        path = QPainterPath()
        path.addRoundedRect(local_rect, 8, 8)
        self._body = QGraphicsPathItem(path)
        self._body.setPen(QPen(self._color, 2))
        fill = QColor(self._color)
        fill.setAlpha(35)
        self._body.setBrush(QBrush(fill))
        self.addToGroup(self._body)

        # Linea tratteggiata: parte dal nostro lato più vicino all'anchor.
        # È figlia del group ma la disegniamo in coord LOCALI; la ricalcoliamo
        # ad ogni itemChange.
        self._line = QGraphicsLineItem()
        line_pen = QPen(self._color, 2, Qt.PenStyle.DashLine)
        line_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self._line.setPen(line_pen)
        self.addToGroup(self._line)
        # Piccolo cerchio sull'anchor per chiarezza visiva.
        self._anchor_dot = QGraphicsPathItem()
        dot_path = QPainterPath()
        dot_path.addEllipse(-4, -4, 8, 8)
        self._anchor_dot.setPath(dot_path)
        self._anchor_dot.setBrush(QBrush(self._color))
        self._anchor_dot.setPen(QPen(QColor("#ffffff"), 1))
        self.addToGroup(self._anchor_dot)

        # Testo editabile
        self._text = QGraphicsTextItem("Scrivi qui…")
        self._text.setFont(QFont("Segoe UI", 10))
        self._text.setDefaultTextColor(QColor("#0f172a") if QColor(color).lightness() > 130 else self._color)
        self._text.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)
        self._text.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self._text.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        self._text.setPos(10, 6)
        self._text.setTextWidth(max(60, local_rect.width() - 20))
        self.addToGroup(self._text)

        # Quando il testo cambia, ridimensioniamo il body in altezza per
        # contenerlo. La larghezza resta fissa (così Qt fa word-wrap),
        # cresce solo in basso. Connessione "compressa" via QTimer per non
        # ricalcolare ad ogni carattere.
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(40)
        self._resize_timer.timeout.connect(self._auto_resize_to_text)
        self._text.document().contentsChanged.connect(self._resize_timer.start)

        # Abilita le notifiche di movimento SOLO ora che tutti gli attributi
        # sono inizializzati, così _update_link può girare in itemChange.
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self._update_link()

    # ---- public ------------------------------------------------------------

    def set_body_rect(self, rect_scene: QRectF) -> None:
        """Aggiorna la dimensione del body (in scene-coords)."""
        # Re-base sul nuovo topLeft scene
        self.setPos(rect_scene.topLeft())
        local = QRectF(0, 0, rect_scene.width(), rect_scene.height())
        self._local_rect = local
        new_path = QPainterPath()
        new_path.addRoundedRect(local, 8, 8)
        self._body.setPath(new_path)
        self._text.setTextWidth(max(60, local.width() - 20))
        self._update_link()

    def local_rect(self) -> QRectF:
        return QRectF(self._local_rect)

    def anchor_scene(self) -> QPointF:
        return QPointF(self._anchor_scene)

    def set_anchor_scene(self, p: QPointF) -> None:
        self._anchor_scene = QPointF(p)
        self._update_link()

    def _auto_resize_to_text(self) -> None:
        """Cresce in altezza per contenere il testo (la larghezza è fissa)."""
        # textRect altezza = dimensione naturale del documento
        doc_h = self._text.document().size().height()
        needed_h = doc_h + 14  # padding top+bottom
        new_h = max(self._local_rect.height(), needed_h)
        if abs(new_h - self._local_rect.height()) < 0.5:
            return
        new_local = QRectF(0, 0, self._local_rect.width(), new_h)
        self._local_rect = new_local
        path = QPainterPath()
        path.addRoundedRect(new_local, 8, 8)
        self._body.setPath(path)
        self._update_link()
        self.prepareGeometryChange()

    def text_item(self) -> QGraphicsTextItem:
        return self._text

    # ---- internals ---------------------------------------------------------

    def _update_link(self) -> None:
        """Ricalcola la linea tratteggiata dal lato più vicino all'anchor."""
        # Posizione attuale del body in scene coords
        body_scene = QRectF(self.pos(), self._local_rect.size())
        # Determina il "punto d'attacco" sul perimetro del body:
        # cerchiamo il bordo più vicino all'anchor in linea retta.
        ax, ay = self._anchor_scene.x(), self._anchor_scene.y()
        cx = body_scene.center().x()
        cy = body_scene.center().y()
        # Clamp del punto sull'anchor verso il body, per il punto di attacco.
        ax_c = max(body_scene.left(), min(body_scene.right(), ax))
        ay_c = max(body_scene.top(), min(body_scene.bottom(), ay))
        # Se l'anchor è dentro al body (raro ma possibile), evitiamo linea zero
        if body_scene.contains(self._anchor_scene):
            # Attacca al lato verticale più vicino al centro
            attach_scene = QPointF(body_scene.left() if ax < cx else body_scene.right(), ay)
        else:
            attach_scene = QPointF(ax_c, ay_c)
        # Convertiamo entrambi in coord LOCALI (il group ha pos = body topLeft).
        attach_local = QPointF(attach_scene.x() - self.pos().x(),
                               attach_scene.y() - self.pos().y())
        anchor_local = QPointF(self._anchor_scene.x() - self.pos().x(),
                               self._anchor_scene.y() - self.pos().y())
        self._line.setLine(anchor_local.x(), anchor_local.y(),
                           attach_local.x(), attach_local.y())
        self._anchor_dot.setPos(anchor_local)

    def itemChange(self, change, value):  # type: ignore[override]
        # Quando il group si muove, ricalcoliamo la linea per mantenere
        # l'anchor fisso in scene-coords.
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self._update_link()
        return super().itemChange(change, value)


class LinkedCommentTool(BaseTool):
    name = "linked_comment"

    def __init__(self) -> None:
        super().__init__()
        self._anchor: Optional[QPointF] = None
        self._item: Optional[LinkedCommentItem] = None

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.CrossCursor)

    def on_press(
        self,
        scene: QGraphicsScene,
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ):
        self._anchor = QPointF(pos)
        # Body iniziale piccolo, offset diagonale dall'anchor
        body_rect = QRectF(pos.x() + 30, pos.y() + 30, 160, 56)
        item = LinkedCommentItem(self._anchor, body_rect, self.context.color)
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
        if self._anchor is None or self._item is None:
            return
        # Body cresce dal punto di press fino al cursore.
        new_rect = QRectF(self._anchor, pos).normalized()
        if new_rect.width() < 100:
            new_rect.setWidth(100)
        if new_rect.height() < 42:
            new_rect.setHeight(42)
        # Sposta l'origine del body un po' lontano dall'anchor per avere la linea
        # visibile invece di sovrapposta.
        if new_rect.contains(self._anchor):
            new_rect.translate(20, 20)
        self._item.set_body_rect(new_rect)

    def on_release(
        self,
        scene: QGraphicsScene,
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ):
        item = self._item
        text_item = item.text_item() if item is not None else None
        # Entra subito in editing testo (vedi callout_tool per il rationale).
        if text_item is not None:
            def _grab() -> None:
                sc = text_item.scene()
                if sc is None:
                    return
                # Forza il focus item nella scena (vedi callout_tool per il
                # rationale: il group catturerebbe il focus altrimenti).
                sc.setFocusItem(text_item, Qt.FocusReason.MouseFocusReason)
                text_item.setFocus(Qt.FocusReason.MouseFocusReason)
                cursor = text_item.textCursor()
                cursor.select(cursor.SelectionType.Document)
                text_item.setTextCursor(cursor)
            QTimer.singleShot(0, _grab)
        self._item = None
        self._anchor = None
        return item
