"""Tabella con celle editabili.

Differente dallo stencil `data_table` che è puro wireframe statico:
qui ogni cella è un QGraphicsTextItem in TextEditorInteraction — basta
doppio click per scrivere dentro.

Workflow:
- Trascina sul canvas: crea una tabella 3×3 (header riga 0 evidenziato).
- Doppio click su una cella: editing in place.
- Tasto destro sulla tabella → Aggiungi/Rimuovi riga/colonna (in
  CanvasEditor.contextMenuEvent quando item.IS_TABLE è True).
- Ridimensiona via maniglie d'angolo come ogni altro elemento.
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
    QGraphicsSceneMouseEvent,
    QGraphicsTextItem,
)

from .base_tool import BaseTool


DEFAULT_ROWS = 3
DEFAULT_COLS = 3
MIN_CELL_W = 50.0
MIN_CELL_H = 24.0
HEADER_FILL = QColor("#dbeafe")
CELL_FILL = QColor("#ffffff")
CELL_BORDER = QColor("#94a3b8")
TEXT_COLOR = QColor("#0f172a")


class TableItem(QGraphicsItemGroup):
    """Tabella editabile con celle in stile spreadsheet.

    Stato interno:
      _rect:  bounding rectangle in coordinate locali (origine 0,0)
      _rows / _cols
      _cells: matrix di QGraphicsTextItem editabili
      _cell_bgs: matrix di QGraphicsRectItem (sfondo + bordo cella)
    """

    IS_TABLE = True  # marker per CanvasEditor / EditHandleManager

    def __init__(
        self,
        rect: QRectF,
        rows: int = DEFAULT_ROWS,
        cols: int = DEFAULT_COLS,
    ) -> None:
        super().__init__()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self._rect = QRectF(rect)
        self._rows = max(1, int(rows))
        self._cols = max(1, int(cols))
        self._cells: list[list[QGraphicsTextItem]] = []
        self._cell_bgs: list[list[QGraphicsRectItem]] = []
        self._rebuild(preserve=False)

    # ---- public api --------------------------------------------------------

    def rows(self) -> int:
        return self._rows

    def cols(self) -> int:
        return self._cols

    def set_rect(self, rect: QRectF) -> None:
        if rect.width() < MIN_CELL_W * self._cols:
            rect.setWidth(MIN_CELL_W * self._cols)
        if rect.height() < MIN_CELL_H * self._rows:
            rect.setHeight(MIN_CELL_H * self._rows)
        self._rect = QRectF(rect)
        self._rebuild(preserve=True)

    def add_row(self) -> None:
        self._rows += 1
        # Allarga il rect verticalmente per non comprimere le righe esistenti.
        self._rect.setHeight(self._rect.height() + (self._rect.height() / max(1, self._rows - 1)))
        self._rebuild(preserve=True)

    def add_col(self) -> None:
        self._cols += 1
        self._rect.setWidth(self._rect.width() + (self._rect.width() / max(1, self._cols - 1)))
        self._rebuild(preserve=True)

    def remove_row(self) -> None:
        if self._rows <= 1:
            return
        # Comprimi proporzionalmente il rect.
        self._rect.setHeight(self._rect.height() * (self._rows - 1) / self._rows)
        self._rows -= 1
        self._rebuild(preserve=True)

    def remove_col(self) -> None:
        if self._cols <= 1:
            return
        self._rect.setWidth(self._rect.width() * (self._cols - 1) / self._cols)
        self._cols -= 1
        self._rebuild(preserve=True)

    # ---- internal ----------------------------------------------------------

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:  # type: ignore[override]
        """Click su una cella → focus al text item interno per editing.
        Click su area non-cella (bordo, fra le celle) → drag del group."""
        if event.button() == Qt.MouseButton.LeftButton:
            sc = self.scene()
            if sc is not None:
                for it in sc.items(event.scenePos()):
                    if not isinstance(it, QGraphicsTextItem):
                        continue
                    # Verifica sia child di questo TableItem
                    parent = it.parentItem()
                    is_child = False
                    while parent is not None:
                        if parent is self:
                            is_child = True
                            break
                        parent = parent.parentItem()
                    if not is_child:
                        continue
                    sc.clearSelection()
                    sc.setFocusItem(it, Qt.FocusReason.MouseFocusReason)
                    it.setFocus(Qt.FocusReason.MouseFocusReason)
                    for view in sc.views():
                        view.setFocus(Qt.FocusReason.MouseFocusReason)
                    event.accept()
                    return
        super().mousePressEvent(event)

    def _rebuild(self, *, preserve: bool) -> None:
        # Salva contenuti correnti prima di distruggere
        old_contents: list[list[str]] = []
        if preserve:
            for row_cells in self._cells:
                old_contents.append([t.toPlainText() for t in row_cells])

        # Rimuovi tutti i children dal group e dalla scene
        for child in list(self.childItems()):
            self.removeFromGroup(child)
            sc = child.scene()
            if sc is not None:
                sc.removeItem(child)
        self._cells = []
        self._cell_bgs = []

        cw = self._rect.width() / self._cols
        ch = self._rect.height() / self._rows

        for r in range(self._rows):
            row_cells: list[QGraphicsTextItem] = []
            row_bgs: list[QGraphicsRectItem] = []
            for c in range(self._cols):
                cell_rect = QRectF(
                    self._rect.x() + c * cw,
                    self._rect.y() + r * ch,
                    cw,
                    ch,
                )
                bg = QGraphicsRectItem(cell_rect)
                is_header = r == 0
                bg.setBrush(QBrush(HEADER_FILL if is_header else CELL_FILL))
                bg.setPen(QPen(CELL_BORDER, 1))
                self.addToGroup(bg)
                row_bgs.append(bg)

                # Contenuto di default
                if preserve and r < len(old_contents) and c < len(old_contents[r]):
                    initial = old_contents[r][c]
                elif is_header:
                    initial = f"Col {c + 1}"
                else:
                    initial = ""

                txt = QGraphicsTextItem(initial)
                font = QFont("Segoe UI", 10)
                font.setBold(is_header)
                txt.setFont(font)
                txt.setDefaultTextColor(TEXT_COLOR)
                txt.setPos(cell_rect.x() + 6, cell_rect.y() + 3)
                txt.setTextWidth(max(20, cw - 12))
                txt.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)
                txt.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
                txt.setTextInteractionFlags(
                    Qt.TextInteractionFlag.TextEditorInteraction
                )
                self.addToGroup(txt)
                row_cells.append(txt)

            self._cells.append(row_cells)
            self._cell_bgs.append(row_bgs)
        # Forza ricalcolo bounding rect del group
        self.prepareGeometryChange()


class TableTool(BaseTool):
    """Trascina per definire l'area, rilascia per creare una tabella 3×3."""

    name = "table"

    def __init__(self) -> None:
        super().__init__()
        self._start: Optional[QPointF] = None
        self._item: Optional[TableItem] = None

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
        # Crea tabella minima 1×1 (verrà ridimensionata da on_move)
        rect = QRectF(0, 0, MIN_CELL_W * DEFAULT_COLS, MIN_CELL_H * DEFAULT_ROWS)
        item = TableItem(rect, rows=DEFAULT_ROWS, cols=DEFAULT_COLS)
        item.setPos(pos)
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
        # Lavoriamo in coord locali del group (origine al press point)
        local_rect = QRectF(0, 0, max(rect.width(), MIN_CELL_W * DEFAULT_COLS),
                            max(rect.height(), MIN_CELL_H * DEFAULT_ROWS))
        # Posiziona il group sul punto top-left del rect (constrain può
        # produrre rect spostato rispetto allo start, es. con Alt = centro).
        self._item.setPos(rect.topLeft())
        self._item.set_rect(local_rect)

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
