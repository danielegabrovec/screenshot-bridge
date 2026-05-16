"""Left dock panel showing the stencil catalog with preview thumbnails."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QMimeData, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QDrag, QIcon, QImage, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QGraphicsScene,
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
        self._hover_row = -1

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
    """Lista degli stencil disponibili. Emette `stencil_chosen(key)` al click,
    oppure permette di trascinare l'elemento direttamente sul canvas."""

    stencil_chosen = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(240)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        title = QLabel("Stencil UI", self)
        title.setStyleSheet("QLabel { font-weight: bold; font-size: 12pt; }")
        layout.addWidget(title)

        hint = QLabel(
            "<b>Trascina</b> uno stencil sul canvas per posizionarlo dove vuoi, "
            "oppure <b>click</b> per aggiungerlo al centro.",
            self,
        )
        hint.setStyleSheet("QLabel { color: #6b7280; font-size: 9pt; }")
        hint.setWordWrap(True)
        hint.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(hint)

        self._search = QLineEdit(self)
        self._search.setPlaceholderText("Cerca stencil...")
        self._search.textChanged.connect(self._filter)
        layout.addWidget(self._search)

        self._list = _DraggableStencilList(self)
        self._list.setIconSize(QSize(180, 90))
        self._list.setSpacing(4)
        self._list.setUniformItemSizes(False)
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.itemActivated.connect(self._on_item_clicked)
        layout.addWidget(self._list)

        self._populate()

    def _populate(self) -> None:
        current_category: Optional[str] = None
        for definition in stencils.CATALOG:
            if definition.category != current_category:
                current_category = definition.category
                header = QListWidgetItem(f"— {current_category} —")
                header.setFlags(Qt.ItemFlag.NoItemFlags)
                font = header.font()
                font.setBold(True)
                header.setFont(font)
                header.setForeground(QColor("#6b7280"))
                self._list.addItem(header)

            item = QListWidgetItem(definition.label)
            item.setData(ROLE_KEY, definition.key)
            item.setIcon(QIcon(_render_thumbnail(definition)))
            item.setSizeHint(QSize(0, 100))
            self._list.addItem(item)

    def _filter(self, text: str) -> None:
        needle = text.strip().lower()
        for i in range(self._list.count()):
            item = self._list.item(i)
            key = item.data(ROLE_KEY)
            if key is None:
                # Category headers: keep visible when filter is empty
                item.setHidden(bool(needle))
                continue
            item.setHidden(bool(needle) and needle not in item.text().lower())

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        key = item.data(ROLE_KEY)
        if key:
            self.stencil_chosen.emit(key)
