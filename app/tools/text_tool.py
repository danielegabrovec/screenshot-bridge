"""Text annotation: click places an editable text item."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QCursor, QFont
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsScene, QGraphicsTextItem

from .base_tool import BaseTool


class TextTool(BaseTool):
    name = "text"

    def __init__(self) -> None:
        super().__init__()
        self._item: Optional[QGraphicsTextItem] = None

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.IBeamCursor)

    def on_press(
        self,
        scene: QGraphicsScene,
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ):
        item = QGraphicsTextItem("Testo")
        font = QFont()
        font.setPointSize(max(12, self.context.thickness * 4))
        item.setFont(font)
        item.setDefaultTextColor(self.context.color)
        item.setPos(pos)
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)
        item.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        scene.addItem(item)
        item.setFocus()
        self._item = item
        return item

    def on_release(
        self,
        scene: QGraphicsScene,
        pos: QPointF,
        *,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ):
        item = self._item
        self._item = None
        return item
