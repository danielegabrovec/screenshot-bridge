"""Canvas: pixmap base + annotation layer with strategy-pattern tools."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QBuffer, QIODevice, QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QContextMenuEvent,
    QDragEnterEvent,
    QDropEvent,
    QFont,
    QImage,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QInputDialog,
    QLabel,
    QMenu,
)

from .edit_handles import (
    EditHandleManager,
    apply_rotation_delta,
    apply_uniform_scale_delta,
    reset_transformation,
)
from .theme import Theme, ThemeManager
from .tools import BaseTool, ToolContext


# Custom data role per associare una descrizione persistente a un item.
# La descrizione viene mostrata come callout (riquadro testuale) sotto l'item
# e finisce nel PNG esportato.
ITEM_DESCRIPTION_ROLE = 1
# Riferimento al QGraphicsSimpleTextItem callout figlio (così possiamo aggiornarlo
# o eliminarlo quando la descrizione cambia).
ITEM_DESCRIPTION_CALLOUT_ROLE = 2


STENCIL_MIME = "application/x-screenshotbridge-stencil"


class CanvasEditor(QGraphicsView):
    image_loaded = pyqtSignal()
    stencil_dropped = pyqtSignal(str, QPointF)  # key, scene position
    zoom_changed = pyqtSignal(float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setAcceptDrops(True)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

        self._background: Optional[QGraphicsPixmapItem] = None
        self._tool: Optional[BaseTool] = None
        self._tool_context = ToolContext(color=QColor("red"), thickness=4)
        self._undo_stack: list[QGraphicsItem] = []
        self._redo_stack: list[QGraphicsItem] = []
        self._read_only = False
        self._stencil_cascade = 0
        self._flash_items: set[QGraphicsItem] = set()
        self._modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier
        # Se True, il press ha effettivamente iniziato un nuovo disegno;
        # mouse move/release vanno al tool. Se False (es. click sopra un
        # item esistente), gli eventi sono delegati a QGraphicsView per
        # selezione + drag standard.
        self._drawing = False
        # Abilita gli eventi di hover sul viewport (per cambiare cursore
        # quando passiamo sopra un item esistente).
        self.viewport().setMouseTracking(True)

        # Handle manager: mostra maniglie di resize/rotate sull'item selezionato
        # e endpoint handle sulle frecce. I suoi handle vengono registrati in
        # `_flash_items` cosi' sono esclusi dall'export PNG.
        self._handles = EditHandleManager(self._scene, self._flash_items)

        # Welcome overlay shown while the canvas has no background image.
        self._welcome = QLabel(self.viewport())
        self._welcome.setTextFormat(Qt.TextFormat.RichText)
        self._welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._welcome.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._welcome.setStyleSheet("QLabel { background: transparent; }")

        # Applica il tema iniziale e iscriviti ai cambi futuri.
        self.apply_theme(ThemeManager.instance().current_theme())
        ThemeManager.instance().theme_changed.connect(self.apply_theme)
        self._reposition_welcome()

    # ---- Theme -------------------------------------------------------------

    def apply_theme(self, theme: Theme) -> None:
        """Aggiorna sfondo canvas + testo del welcome overlay col tema corrente."""
        self.setBackgroundBrush(QColor(theme.canvas_bg))
        self._welcome.setText(self._build_welcome_html(theme))

    @staticmethod
    def _build_welcome_html(theme: Theme) -> str:
        return (
            f"<div style='font-family:Segoe UI; color:{theme.welcome_body}; text-align:center;'>"
            f"<div style='font-size:26pt; font-weight:700; margin-bottom:18px; color:{theme.welcome_title};'>"
            "Carica uno screenshot"
            "</div>"
            "<div style='font-size:13pt; line-height:1.7;'>"
            "<b>Ctrl+V</b> &nbsp;incolla dagli appunti<br>"
            "<b>Ctrl+Shift+S</b> &nbsp;cattura un'area dello schermo<br>"
            "trascina qui un file <code>.png</code> / <code>.jpg</code><br>"
            "oppure usa il pulsante <b>Apri file...</b> in toolbar"
            "</div>"
            f"<div style='font-size:11pt; margin-top:22px; color:{theme.welcome_hint};'>"
            "Puoi anche cominciare cliccando uno <b>stencil</b> nel pannello a sinistra."
            "</div>"
            "</div>"
        )

    # ---- Tool / style ------------------------------------------------------

    def set_tool(self, tool: Optional[BaseTool]) -> None:
        self._tool = tool
        if tool is not None:
            tool.set_context(self._tool_context)
            # Cursore custom per indicare il tool attivo.
            try:
                self.viewport().setCursor(tool.cursor())
            except Exception:
                self.viewport().unsetCursor()
        else:
            self.viewport().unsetCursor()
        if tool is None:
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        else:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)

    def set_color(self, color: QColor) -> None:
        self._tool_context.color = QColor(color)
        if self._tool is not None:
            self._tool.set_context(self._tool_context)

    def set_thickness(self, thickness: int) -> None:
        self._tool_context.thickness = max(1, int(thickness))
        if self._tool is not None:
            self._tool.set_context(self._tool_context)

    def set_read_only(self, value: bool) -> None:
        self._read_only = value

    # ---- Image loading -----------------------------------------------------

    def load_pixmap(self, pixmap: QPixmap) -> None:
        # Detach handles prima di clear() altrimenti restano riferimenti orfani
        self._handles.detach()
        self._scene.clear()
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._stencil_cascade = 0
        self._flash_items.clear()
        self._background = QGraphicsPixmapItem(pixmap)
        self._background.setZValue(-1000)
        self._scene.addItem(self._background)
        self._scene.setSceneRect(self._background.boundingRect())
        self.fitInView(self._background, Qt.AspectRatioMode.KeepAspectRatio)
        self._welcome.hide()
        self.image_loaded.emit()

    def load_image(self, image: QImage) -> None:
        self.load_pixmap(QPixmap.fromImage(image))

    def load_file(self, path: str) -> bool:
        pix = QPixmap(path)
        if pix.isNull():
            return False
        self.load_pixmap(pix)
        return True

    def has_image(self) -> bool:
        return self._background is not None

    def add_stencil(
        self,
        item: QGraphicsItem,
        scene_pos: Optional[QPointF] = None,
    ) -> None:
        """Insert a stencil item on the canvas.

        Stencils have fixed pixel sizes (~140x36 for a button). When the
        canvas hosts a large screenshot (e.g. 1920x1080), the stencil would
        appear microscopic or disappear behind the image. We auto-scale the
        stencil so its width is a reasonable fraction (~14%) of the scene
        width, with a minimum visual size.

        If `scene_pos` is provided (e.g. a drop point), the stencil is
        centered there. Otherwise it's placed at the viewport center with a
        small cascade offset to avoid stacking.
        """
        if self._read_only:
            return

        # Auto-scale based on scene size (only when we have a real background)
        scene_w = self._scene.sceneRect().width() if self._scene.sceneRect().isValid() else 0
        base_w = item.boundingRect().width()
        if scene_w > 0 and base_w > 0:
            target_w = max(160.0, scene_w * 0.14)
            scale = target_w / base_w
            scale = max(1.0, min(scale, 4.0))
            if scale != 1.0:
                item.setScale(scale)

        self._scene.addItem(item)
        br = item.sceneBoundingRect()

        if scene_pos is not None:
            item.setPos(scene_pos.x() - br.width() / 2, scene_pos.y() - br.height() / 2)
        else:
            center = self.mapToScene(self.viewport().rect().center())
            offset = (self._stencil_cascade % 6) * (br.height() * 0.25 + 12)
            item.setPos(
                center.x() - br.width() / 2 + offset,
                center.y() - br.height() / 2 + offset,
            )
            self._stencil_cascade += 1

        self._scene.clearSelection()
        item.setSelected(True)
        self.ensureVisible(item, 40, 40)
        self._flash_item(item)
        self._undo_stack.append(item)
        self._redo_stack.clear()

    def _flash_item(self, item: QGraphicsItem) -> None:
        """Brief blue highlight rectangle so the user notices the new stencil.

        Tracked in `_flash_items` so it is excluded from PNG export.
        """
        theme = ThemeManager.instance().current_theme()
        rect = item.sceneBoundingRect().adjusted(-6, -6, 6, 6)
        highlight = QGraphicsRectItem(rect)
        accent = QColor(theme.accent)
        pen = QPen(accent, 3)
        pen.setCosmetic(True)
        highlight.setPen(pen)
        fill = QColor(accent)
        fill.setAlpha(60)
        highlight.setBrush(fill)
        highlight.setZValue(10_000)
        self._scene.addItem(highlight)
        self._flash_items.add(highlight)

        def _remove() -> None:
            self._flash_items.discard(highlight)
            if highlight.scene() is self._scene:
                self._scene.removeItem(highlight)

        QTimer.singleShot(700, _remove)

    # ---- Export ------------------------------------------------------------

    def export_png_bytes(self) -> bytes:
        rect = self._scene.sceneRect().toRect()
        image = QImage(rect.size(), QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # Salviamo la selezione corrente per ripristinarla dopo l'export
        # (clearSelection rimuoverebbe gli edit handles via selectionChanged).
        previously_selected = list(self._scene.selectedItems())
        self._scene.clearSelection()

        # Hide transient flash highlights AND edit handles during export so
        # they don't end up baked into the saved PNG. `_flash_items` ora
        # contiene anche handles/cornice di selezione (registrati dal manager).
        hidden = [h for h in self._flash_items if h.isVisible()]
        for h in hidden:
            h.setVisible(False)
        try:
            self._scene.render(
                painter,
                target=QRectF(image.rect()),
                source=self._scene.sceneRect(),
            )
        finally:
            for h in hidden:
                h.setVisible(True)
            for it in previously_selected:
                if it.scene() is self._scene:
                    it.setSelected(True)
        painter.end()

        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buf, "PNG")
        return bytes(buf.data())

    def annotated_items(self) -> list[QGraphicsItem]:
        """Items utente (esclude background, flash, handle)."""
        out: list[QGraphicsItem] = []
        for it in self._scene.items():
            if it is self._background:
                continue
            if it in self._flash_items:
                continue
            if it.parentItem() is not None:
                # children (es. callout) li ignoriamo: il "principale" è il parent
                continue
            out.append(it)
        return out

    # ---- Mouse / keyboard --------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._read_only or self._tool is None or event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        self._modifiers = event.modifiers()
        pos = self.mapToScene(event.position().toPoint())

        # Comportamento standard delle app grafiche (Figma, Inkscape, …):
        # se sotto al cursore c'è già un elemento selezionabile, NON iniziare
        # un nuovo disegno — passa la mano a QGraphicsView per selezione+drag.
        existing = self._top_user_item_at(pos)
        if existing is not None and bool(
            existing.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
        ):
            self._drawing = False
            return super().mousePressEvent(event)

        self._drawing = True
        item = self._tool.on_press(self._scene, pos, modifiers=self._modifiers)
        if item is not None:
            self._undo_stack.append(item)
            self._redo_stack.clear()
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._read_only or self._tool is None:
            return super().mouseMoveEvent(event)
        self._modifiers = event.modifiers()
        pos = self.mapToScene(event.position().toPoint())

        if not self._drawing:
            # Hover: cambia cursore per indicare "click qui = selezione" vs
            # "click qui = disegno nuovo elemento".
            existing = self._top_user_item_at(pos)
            if existing is not None and bool(
                existing.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            ):
                self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                try:
                    self.viewport().setCursor(self._tool.cursor())
                except Exception:
                    self.viewport().unsetCursor()
            return super().mouseMoveEvent(event)

        self._tool.on_move(self._scene, pos, modifiers=self._modifiers)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mouseReleaseEvent(event)
        if self._read_only or self._tool is None or not self._drawing:
            self._drawing = False
            return super().mouseReleaseEvent(event)
        self._modifiers = event.modifiers()
        pos = self.mapToScene(event.position().toPoint())
        self._tool.on_release(self._scene, pos, modifiers=self._modifiers)
        self._drawing = False
        event.accept()

    def wheelEvent(self, event) -> None:  # type: ignore[override]
        # Ctrl+ruota: zoom della vista. Notifica zoom_changed in % rispetto al fit.
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            angle = event.angleDelta().y()
            if angle == 0:
                return
            factor = 1.15 if angle > 0 else (1 / 1.15)
            self.scale(factor, factor)
            try:
                m = self.transform().m11()
                self.zoom_changed.emit(float(m))
            except Exception:
                pass
            event.accept()
            return
        super().wheelEvent(event)

    # ---- Context menu sugli item ------------------------------------------
    #
    # L'utente clicca col tasto destro su uno stencil/freccia/testo e si
    # aspetta un menu di azioni rapide (aggiungi descrizione, elimina,
    # duplica, z-order). Senza questo menu l'app sembra "laboriosa" perché
    # ogni azione richiede di selezionare l'item, andare in toolbar o usare
    # scorciatoie non documentate.

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        if self._read_only:
            return super().contextMenuEvent(event)
        scene_pos = self.mapToScene(event.pos())
        item = self._top_user_item_at(scene_pos)
        if item is None:
            return super().contextMenuEvent(event)
        # Selezioniamo l'item cliccato così l'utente vede immediatamente su
        # cosa sta agendo, anche se non lo aveva selezionato prima.
        self._scene.clearSelection()
        item.setSelected(True)

        menu = QMenu(self)
        has_desc = bool(self._get_item_description(item))
        desc_action = QAction(
            "Modifica descrizione…" if has_desc else "Aggiungi descrizione…",
            self,
        )
        desc_action.triggered.connect(lambda: self._prompt_description(item))
        menu.addAction(desc_action)
        if has_desc:
            clear_action = QAction("Rimuovi descrizione", self)
            clear_action.triggered.connect(lambda: self._set_item_description(item, ""))
            menu.addAction(clear_action)
        menu.addSeparator()
        rot_left = QAction("Ruota di -90°", self)
        rot_left.triggered.connect(lambda: (apply_rotation_delta(item, -90), self._handles.refresh()))
        menu.addAction(rot_left)
        rot_right = QAction("Ruota di +90°", self)
        rot_right.triggered.connect(lambda: (apply_rotation_delta(item, 90), self._handles.refresh()))
        menu.addAction(rot_right)
        reset_act = QAction("Reset rotazione/scala", self)
        reset_act.triggered.connect(lambda: (reset_transformation(item), self._handles.refresh()))
        menu.addAction(reset_act)
        menu.addSeparator()
        dup_action = QAction("Duplica", self)
        dup_action.triggered.connect(lambda: self._duplicate_item(item))
        menu.addAction(dup_action)
        front_action = QAction("Porta in primo piano", self)
        front_action.triggered.connect(lambda: self._bring_to_front(item))
        menu.addAction(front_action)
        back_action = QAction("Porta sullo sfondo", self)
        back_action.triggered.connect(lambda: self._send_to_back(item))
        menu.addAction(back_action)
        menu.addSeparator()
        del_action = QAction("Elimina", self)
        del_action.triggered.connect(lambda: self._remove_item(item))
        menu.addAction(del_action)
        menu.exec(event.globalPos())

    def _top_user_item_at(self, scene_pos: QPointF) -> Optional[QGraphicsItem]:
        """Topmost item utente sotto il cursore, escludendo background e flash."""
        for it in self._scene.items(scene_pos):
            if it is self._background:
                continue
            if it in self._flash_items:
                continue
            # Esclude i callout di descrizione: il menu va sull'item "padre".
            parent = it.parentItem()
            if parent is not None and parent.data(ITEM_DESCRIPTION_CALLOUT_ROLE) is it:
                return parent
            return it
        return None

    def _prompt_description(self, item: QGraphicsItem) -> None:
        # QInputDialog.getMultiLineText usa QPlainTextEdit in modalità senza
        # word-wrap → linee lunghe escono dal bordo. Usiamo un dialog custom
        # con WrapMode.WordWrap, che è il comportamento atteso da un editor.
        from PyQt6.QtGui import QTextOption
        from PyQt6.QtWidgets import (
            QDialog, QDialogButtonBox, QPlainTextEdit, QVBoxLayout,
        )
        current = self._get_item_description(item)
        dlg = QDialog(self)
        dlg.setWindowTitle("Descrizione elemento")
        dlg.resize(560, 300)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel(
            "Testo descrittivo (verrà mostrato sotto l'elemento e finirà nel PNG esportato):",
            dlg,
        ))
        edit = QPlainTextEdit(current, dlg)
        # WrapAtWordBoundaryOrAnywhere: preferisce spezzare sui confini di parola
        # ma se la "parola" è lunga quanto tutta la riga (es. tante 'r' senza
        # spazi, o un URL lungo) va a capo comunque — WordWrap "puro" non lo
        # fa e produce scrollbar orizzontale.
        edit.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        # Disabilita la scrollbar orizzontale: con il wrap-anywhere non serve,
        # e se compare significa che qualcosa non sta wrappando (bug).
        edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        edit.setTabChangesFocus(True)
        layout.addWidget(edit, stretch=1)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            parent=dlg,
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        edit.setFocus()
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self._set_item_description(item, edit.toPlainText().strip())

    def _get_item_description(self, item: QGraphicsItem) -> str:
        v = item.data(ITEM_DESCRIPTION_ROLE)
        return str(v) if isinstance(v, str) else ""

    def _set_item_description(self, item: QGraphicsItem, text: str) -> None:
        item.setData(ITEM_DESCRIPTION_ROLE, text)
        # Rimuovo callout esistente (se c'è) e ne creo uno nuovo se text non vuoto.
        old = item.data(ITEM_DESCRIPTION_CALLOUT_ROLE)
        if isinstance(old, QGraphicsItem) and old.scene() is self._scene:
            self._scene.removeItem(old)
            item.setData(ITEM_DESCRIPTION_CALLOUT_ROLE, None)
        if not text:
            return
        callout = _DescriptionCallout(text, item)
        # ItemIgnoresTransformations: tieni il callout sempre alla stessa
        # dimensione in pixel, anche se l'item parent è scalato 4x. Altrimenti
        # su stencil grandi il testo diventerebbe enorme.
        callout.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        callout.setZValue(item.zValue() + 0.5)
        item.setData(ITEM_DESCRIPTION_CALLOUT_ROLE, callout)
        # Posizionamento iniziale sotto l'item (in local coordinates del parent).
        br = item.boundingRect()
        callout.setPos(br.left(), br.bottom() + 6)
        # Porta in vista: se l'item è scalato/ruotato il callout potrebbe finire
        # fuori dal viewport — `ensureVisible` scrolla il canvas se serve.
        self.ensureVisible(callout, 20, 20)

    def _duplicate_item(self, item: QGraphicsItem) -> None:
        clone = _shallow_clone(item)
        if clone is None:
            return
        clone.setPos(item.pos().x() + 20, item.pos().y() + 20)
        self._scene.addItem(clone)
        self._scene.clearSelection()
        clone.setSelected(True)
        self._undo_stack.append(clone)
        self._redo_stack.clear()

    def _bring_to_front(self, item: QGraphicsItem) -> None:
        max_z = 0.0
        for it in self._scene.items():
            if it is self._background:
                continue
            if it.zValue() > max_z:
                max_z = it.zValue()
        item.setZValue(max_z + 1.0)

    def _send_to_back(self, item: QGraphicsItem) -> None:
        min_z = 0.0
        for it in self._scene.items():
            if it is self._background:
                continue
            if it.zValue() < min_z:
                min_z = it.zValue()
        item.setZValue(min_z - 1.0)

    def _remove_item(self, item: QGraphicsItem) -> None:
        callout = item.data(ITEM_DESCRIPTION_CALLOUT_ROLE)
        if isinstance(callout, QGraphicsItem) and callout.scene() is self._scene:
            self._scene.removeItem(callout)
        if item.scene() is self._scene:
            self._scene.removeItem(item)
        if item in self._undo_stack:
            self._undo_stack.remove(item)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self._read_only:
            return super().keyPressEvent(event)
        if event.key() == Qt.Key.Key_Delete:
            for item in list(self._scene.selectedItems()):
                if item is self._background:
                    continue
                self._handles.detach()
                self._scene.removeItem(item)
                if item in self._undo_stack:
                    self._undo_stack.remove(item)
            event.accept()
            return

        # Scorciatoie di trasformazione sull'item selezionato.
        sel = [it for it in self._scene.selectedItems() if it is not self._background]
        if len(sel) == 1:
            target = sel[0]
            key = event.key()
            # Scaling: + / - (e numpad). Shift accelera.
            step = 1.20 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1.10
            if key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
                apply_uniform_scale_delta(target, step)
                self._handles.refresh()
                event.accept(); return
            if key in (Qt.Key.Key_Minus, Qt.Key.Key_Underscore):
                apply_uniform_scale_delta(target, 1.0 / step)
                self._handles.refresh()
                event.accept(); return
            # Rotazione: [ / ] (e , / . come fallback). Shift = 15°.
            delta = 15.0 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 5.0
            if key in (Qt.Key.Key_BracketLeft, Qt.Key.Key_Comma):
                apply_rotation_delta(target, -delta)
                self._handles.refresh()
                event.accept(); return
            if key in (Qt.Key.Key_BracketRight, Qt.Key.Key_Period):
                apply_rotation_delta(target, delta)
                self._handles.refresh()
                event.accept(); return
            # Reset trasformazione: R
            if key == Qt.Key.Key_R and not event.modifiers():
                reset_transformation(target)
                self._handles.refresh()
                event.accept(); return

        if event.matches(event.StandardKey.Undo) if hasattr(event, "StandardKey") else False:
            self.undo()
            return
        super().keyPressEvent(event)

    def undo(self) -> None:
        if not self._undo_stack:
            return
        item = self._undo_stack.pop()
        if item.scene() is self._scene:
            self._scene.removeItem(item)
        self._redo_stack.append(item)

    def redo(self) -> None:
        if not self._redo_stack:
            return
        item = self._redo_stack.pop()
        self._scene.addItem(item)
        self._undo_stack.append(item)

    # ---- Drag & drop -------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        md = event.mimeData()
        if md.hasFormat(STENCIL_MIME) or md.hasUrls() or md.hasImage():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        md = event.mimeData()
        if md.hasFormat(STENCIL_MIME) or md.hasUrls() or md.hasImage():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        md = event.mimeData()
        if md.hasFormat(STENCIL_MIME):
            key = bytes(md.data(STENCIL_MIME)).decode("utf-8", errors="replace")
            if key:
                scene_pos = self.mapToScene(event.position().toPoint())
                self.stencil_dropped.emit(key, scene_pos)
                event.acceptProposedAction()
                return
        if md.hasImage():
            img = QImage(md.imageData())
            if not img.isNull():
                self.load_image(img)
                event.acceptProposedAction()
                return
        if md.hasUrls():
            for url in md.urls():
                if url.isLocalFile() and self.load_file(url.toLocalFile()):
                    event.acceptProposedAction()
                    return
        super().dropEvent(event)

    # ---- Fit on resize -----------------------------------------------------

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._background is not None:
            self.fitInView(self._background, Qt.AspectRatioMode.KeepAspectRatio)
        self._reposition_welcome()

    def _reposition_welcome(self) -> None:
        if not hasattr(self, "_welcome"):
            return
        vp = self.viewport().rect()
        # Cover the whole viewport so the message is always centered.
        self._welcome.setGeometry(vp)


class _DescriptionCallout(QGraphicsSimpleTextItem):
    """Callout testuale renderizzato sotto un item, con sfondo bianco semitrasparente.

    Implementato come QGraphicsSimpleTextItem con override di paint per
    disegnare un riquadro di background prima del testo. Vive come child
    dell'item commentato così si muove e si scala con esso.
    """

    def __init__(self, text: str, parent: QGraphicsItem) -> None:
        super().__init__(text, parent)
        font = QFont("Segoe UI", 10)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        self.setFont(font)
        self.setBrush(QBrush(QColor("#111827")))

    def boundingRect(self) -> QRectF:
        base = super().boundingRect()
        # Allarghiamo il bounding rect per includere il padding del background.
        return base.adjusted(-6, -4, 6, 4)

    def paint(self, painter, option, widget=None) -> None:  # type: ignore[override]
        text_rect = super().boundingRect()
        bg_rect = text_rect.adjusted(-6, -4, 6, 4)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # Salviamo lo stato del painter: il super().paint() di QGraphicsSimpleTextItem
        # usa il `brush` del painter per il colore del testo. Se non ripristiniamo
        # il brush dopo aver disegnato lo sfondo bianco, il testo finisce bianco
        # su sfondo bianco e diventa invisibile (bug riscontrato in produzione).
        painter.save()
        painter.setBrush(QColor(255, 255, 255, 235))
        pen = QPen(QColor("#94a3b8"))
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.drawRoundedRect(bg_rect, 4, 4)
        painter.restore()
        super().paint(painter, option, widget)


def _shallow_clone(item: QGraphicsItem) -> Optional[QGraphicsItem]:
    """Crea un clone "best effort" di un item generico.

    Strategia: serializziamo il bounding rect e ricreiamo un QGraphicsRectItem
    placeholder solo per i tipi che non hanno un clone nativo. Per i tipi più
    comuni del canvas (QGraphicsRectItem, QGraphicsEllipseItem, ecc.) usiamo
    i costruttori delle classi specifiche replicando pen/brush.
    """
    # Import locali per evitare cicli e non gonfiare l'header.
    from PyQt6.QtWidgets import (
        QGraphicsEllipseItem,
        QGraphicsLineItem,
        QGraphicsPathItem,
        QGraphicsTextItem,
        QGraphicsItemGroup,
        QGraphicsSimpleTextItem as _Simple,
    )

    if isinstance(item, QGraphicsRectItem):
        clone = QGraphicsRectItem(item.rect())
        clone.setPen(item.pen())
        clone.setBrush(item.brush())
        return clone
    if isinstance(item, QGraphicsEllipseItem):
        clone = QGraphicsEllipseItem(item.rect())
        clone.setPen(item.pen())
        clone.setBrush(item.brush())
        return clone
    if isinstance(item, QGraphicsLineItem):
        clone = QGraphicsLineItem(item.line())
        clone.setPen(item.pen())
        return clone
    if isinstance(item, QGraphicsPathItem):
        clone = QGraphicsPathItem(item.path())
        clone.setPen(item.pen())
        clone.setBrush(item.brush())
        return clone
    if isinstance(item, QGraphicsTextItem):
        clone = QGraphicsTextItem(item.toPlainText())
        clone.setFont(item.font())
        clone.setDefaultTextColor(item.defaultTextColor())
        return clone
    if isinstance(item, _Simple):
        clone = _Simple(item.text())
        clone.setFont(item.font())
        clone.setBrush(item.brush())
        return clone
    if isinstance(item, QGraphicsItemGroup):
        rect = item.boundingRect()
        clone = QGraphicsRectItem(rect)
        pen = QPen(QColor("#64748b"), 1, Qt.PenStyle.DashLine)
        clone.setPen(pen)
        return clone
    return None
