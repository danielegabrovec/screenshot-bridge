"""Left dock panel showing the stencil catalog with preview thumbnails."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QMimeData, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QDrag, QIcon, QImage, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGraphicsScene,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from . import stencils
from .stencils import StencilDef


ROLE_KEY = Qt.ItemDataRole.UserRole + 1
ROLE_IS_HEADER = Qt.ItemDataRole.UserRole + 2
STENCIL_MIME = "application/x-screenshotbridge-stencil"


def _render_thumbnail(definition: StencilDef, size: QSize = QSize(180, 90)) -> QPixmap:
    """Render a stencil into a thumbnail pixmap (used as list icon)."""
    scene = QGraphicsScene()
    item = definition.factory()
    scene.addItem(item)
    rect = scene.itemsBoundingRect().adjusted(-4, -4, 4, 4)

    image = QImage(size, QImage.Format.Format_ARGB32)
    image.fill(QColor("#fafafa"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    target = QRectF(0, 0, size.width(), size.height())
    scene.render(painter, target=target, source=rect)
    painter.end()
    return QPixmap.fromImage(image)


class _DraggableStencilList(QListWidget):
    """QListWidget that starts a drag carrying the stencil key as mime data."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        item = self.itemAt(event.position().toPoint())
        if item is not None and item.data(ROLE_KEY):
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.unsetCursor()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self.unsetCursor()
        super().leaveEvent(event)

    def startDrag(self, supportedActions) -> None:  # type: ignore[override]
        item = self.currentItem()
        if item is None:
            return
        key = item.data(ROLE_KEY)
        if not key:
            return

        mime = QMimeData()
        mime.setData(STENCIL_MIME, key.encode("utf-8"))
        mime.setText(f"stencil:{key}")

        drag = QDrag(self)
        drag.setMimeData(mime)
        icon = item.icon()
        if not icon.isNull():
            pix = icon.pixmap(QSize(180, 90))
            drag.setPixmap(pix)
            drag.setHotSpot(pix.rect().center())
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        try:
            drag.exec(Qt.DropAction.CopyAction)
        finally:
            self.unsetCursor()


class StencilPanel(QWidget):
    """Lista degli stencil con ricerca smart (label + keywords + key) e
    filtro per categoria. Emette `stencil_chosen(key)` al click, oppure
    permette di trascinare l'elemento sul canvas."""

    stencil_chosen = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(240)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Titolo + contatore (aggiornato al volo)
        title_row = QHBoxLayout()
        title = QLabel("Stencil UI", self)
        title.setStyleSheet("QLabel { font-weight: bold; font-size: 12pt; }")
        title_row.addWidget(title)
        title_row.addStretch()
        self._counter = QLabel(self)
        self._counter.setStyleSheet("QLabel { color:#6b7280; font-size: 9pt; }")
        title_row.addWidget(self._counter)
        layout.addLayout(title_row)

        hint = QLabel(
            "<b>Trascina</b> uno stencil sul canvas per posizionarlo dove vuoi, "
            "oppure <b>click</b> per aggiungerlo al centro.",
            self,
        )
        hint.setStyleSheet("QLabel { color: #6b7280; font-size: 9pt; }")
        hint.setWordWrap(True)
        hint.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(hint)

        # Filtri: categoria + ricerca
        filter_row = QHBoxLayout()
        self._category_combo = QComboBox(self)
        self._category_combo.addItem("Tutte le categorie", "")
        for cat in stencils.categories():
            self._category_combo.addItem(cat, cat)
        self._category_combo.currentIndexChanged.connect(self._apply_filter)
        filter_row.addWidget(self._category_combo, stretch=1)
        layout.addLayout(filter_row)

        self._search = QLineEdit(self)
        self._search.setPlaceholderText("Cerca per nome o parola chiave…")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._apply_filter)
        layout.addWidget(self._search)

        self._list = _DraggableStencilList(self)
        self._list.setIconSize(QSize(180, 90))
        self._list.setSpacing(4)
        self._list.setUniformItemSizes(False)
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.itemActivated.connect(self._on_item_clicked)
        layout.addWidget(self._list, stretch=1)

        # Cache thumbnail per non rigenerare ad ogni filter.
        self._thumb_cache: dict[str, QPixmap] = {}

        self._apply_filter()

    # ---- Populating + filtering -------------------------------------------

    def _thumbnail_for(self, definition: StencilDef) -> QPixmap:
        if definition.key not in self._thumb_cache:
            self._thumb_cache[definition.key] = _render_thumbnail(definition)
        return self._thumb_cache[definition.key]

    def _apply_filter(self) -> None:
        needle = self._search.text()
        category = self._category_combo.currentData() or ""
        results = stencils.search(needle, category=category)

        self._list.clear()
        current_category: Optional[str] = None
        for definition in results:
            # Header di categoria solo se mostriamo "Tutte le categorie".
            if not category and definition.category != current_category:
                current_category = definition.category
                header = QListWidgetItem(f"— {current_category} —")
                header.setFlags(Qt.ItemFlag.NoItemFlags)
                font = header.font()
                font.setBold(True)
                header.setFont(font)
                header.setForeground(QColor("#6b7280"))
                header.setData(ROLE_IS_HEADER, True)
                self._list.addItem(header)

            item = QListWidgetItem(definition.label)
            item.setData(ROLE_KEY, definition.key)
            item.setIcon(QIcon(self._thumbnail_for(definition)))
            item.setSizeHint(QSize(0, 100))
            # Tooltip ricco mostra le keywords (così l'utente capisce perché
            # uno stencil è apparso/non apparso in ricerca).
            tip_parts = [f"<b>{definition.label}</b>"]
            if definition.keywords:
                tip_parts.append(
                    f"<span style='color:#6b7280'>alias: {', '.join(definition.keywords)}</span>"
                )
            item.setToolTip("<br>".join(tip_parts))
            self._list.addItem(item)

        total = len([s for s in results])
        self._counter.setText(f"{total} / {len(stencils.CATALOG)}")

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        key = item.data(ROLE_KEY)
        if key:
            self.stencil_chosen.emit(key)
