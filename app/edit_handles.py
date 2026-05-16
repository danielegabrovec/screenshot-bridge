"""Edit handles for selected items: resize corners + rotation + arrow endpoints.

Architecture
------------
* `EditHandleManager` listens to `scene.selectionChanged` and, when exactly
  one item is selected, attaches the appropriate set of handles.
* Each handle is a small `QGraphicsEllipseItem` with
  `ItemIgnoresTransformations` so it stays the same pixel size regardless of
  the view zoom or the parent's scale.
* Handles register themselves in the manager's `flash_items_set` so they
  are excluded from the exported PNG (the same mechanism that hides the
  blue flash on stencil add).
* On drag, a handle calls back into the manager which mutates the target
  item (scale, rotation or endpoint).
* La palette dei colori dei handle è letta dinamicamente da `ThemeManager`,
  così al toggle del tema cornice/handle si aggiornano in tempo reale.

Why a manager and not children of the item: we don't want handles to move
*with* the item's local transform. They need to live in scene coordinates
and be re-laid-out whenever the item changes geometry. Keeping them as
top-level scene items, with `ItemIgnoresTransformations` and an
event-driven re-layout, gives us that flexibility.
"""
from __future__ import annotations

import math
from typing import Callable, Optional

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QPen
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
)

from .theme import Theme, ThemeManager


HANDLE_SIZE = 11.0  # diametro in pixel di viewport (ignorato dalle trasformazioni)
EDGE_HANDLE_SIZE = 9.0
ROTATE_OFFSET = 28.0  # distanza in pixel del rotate handle dall'item


class _Handle(QGraphicsEllipseItem):
    """Singolo handle. Cattura il drag del mouse e invia delta al callback."""

    def __init__(
        self,
        fill: QColor,
        border: QColor,
        on_drag: Callable[[QPointF], None],
        on_press: Optional[Callable[[QPointF], None]] = None,
        cursor: Qt.CursorShape = Qt.CursorShape.SizeAllCursor,
        diameter: float = HANDLE_SIZE,
    ) -> None:
        d = diameter
        super().__init__(QRectF(-d / 2, -d / 2, d, d))
        self.setBrush(QBrush(fill))
        pen = QPen(border, 1.5)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        self.setZValue(20_000)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setCursor(cursor)
        self._on_drag = on_drag
        self._on_press = on_press
        self._fill = fill
        self._border = border

    def restyle(self, fill: QColor, border: QColor) -> None:
        self._fill = fill
        self._border = border
        self.setBrush(QBrush(fill))
        pen = QPen(border, 1.5)
        pen.setCosmetic(True)
        self.setPen(pen)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._on_press is not None:
            self._on_press(event.scenePos())
        event.accept()

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self._on_drag(event.scenePos())
        event.accept()

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        event.accept()


class _SelectionFrame(QGraphicsRectItem):
    """Cornice tratteggiata blu attorno all'item selezionato."""

    def __init__(self, border: QColor) -> None:
        super().__init__()
        pen = QPen(border, 1, Qt.PenStyle.DashLine)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.setBrush(Qt.GlobalColor.transparent)
        self.setZValue(19_999)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, False)

    def restyle(self, border: QColor) -> None:
        pen = QPen(border, 1, Qt.PenStyle.DashLine)
        pen.setCosmetic(True)
        self.setPen(pen)


def _is_arrow(item: QGraphicsItem) -> bool:
    return getattr(item, "IS_ARROW", False) is True


class EditHandleManager:
    """Maintains a set of edit handles around the currently selected item."""

    def __init__(self, scene: QGraphicsScene, flash_items_set: set[QGraphicsItem]) -> None:
        self._scene = scene
        self._flash = flash_items_set
        self._target: Optional[QGraphicsItem] = None
        self._frame: Optional[_SelectionFrame] = None
        self._rot_line: Optional[QGraphicsLineItem] = None
        self._handles: list[_Handle] = []
        # Salva il tema applicato per evitare restyle ridondanti.
        self._theme: Theme = ThemeManager.instance().current_theme()

        # Drag state
        self._drag_start_scene: Optional[QPointF] = None
        self._drag_initial_scale: float = 1.0
        self._drag_initial_rotation: float = 0.0
        self._drag_pivot_scene: Optional[QPointF] = None
        self._drag_initial_distance: float = 1.0
        self._drag_initial_pos: Optional[QPointF] = None

        scene.selectionChanged.connect(self._sync)
        scene.changed.connect(self._on_scene_changed)
        ThemeManager.instance().theme_changed.connect(self.apply_theme)

    # ---- Public API --------------------------------------------------------

    def refresh(self) -> None:
        """Force a relayout of the current handles (after mutating the item)."""
        if self._target is None:
            return
        self._layout()

    def apply_theme(self, theme: Theme) -> None:
        """Aggiorna i colori dei handle/cornice quando cambia il tema."""
        self._theme = theme
        if self._frame is not None:
            self._frame.restyle(QColor(theme.selection_border))
        if self._rot_line is not None:
            pen = QPen(QColor(theme.selection_border), 1, Qt.PenStyle.DashLine)
            pen.setCosmetic(True)
            self._rot_line.setPen(pen)
        if self._target is not None:
            arrow = _is_arrow(self._target)
            for h in self._handles:
                if arrow:
                    h.restyle(
                        QColor(theme.handle_endpoint_fill),
                        QColor(theme.handle_endpoint_border),
                    )
                else:
                    # ultimo handle è rotate (fill diverso)
                    if h is self._handles[-1] and len(self._handles) >= 5:
                        h.restyle(QColor(theme.rotate_fill), QColor(theme.handle_border))
                    else:
                        h.restyle(QColor(theme.handle_fill), QColor(theme.handle_border))

    def detach(self) -> None:
        """Remove all handles from the scene (e.g. on read-only or before export)."""
        for h in self._handles:
            self._remove(h)
        self._handles = []
        if self._frame is not None:
            self._remove(self._frame)
            self._frame = None
        if self._rot_line is not None:
            self._remove(self._rot_line)
            self._rot_line = None
        self._target = None

    # ---- Internals ---------------------------------------------------------

    def _remove(self, item: QGraphicsItem) -> None:
        self._flash.discard(item)
        if item.scene() is self._scene:
            self._scene.removeItem(item)

    def _add(self, item: QGraphicsItem) -> None:
        self._scene.addItem(item)
        # Marchio "flash-like" — escluso dall'export PNG.
        self._flash.add(item)

    def _on_scene_changed(self, _regions) -> None:
        # Riallinea solo se abbiamo un target — economico ma necessario perché
        # quando l'utente trascina l'intero item (non un handle) i nostri
        # handle devono spostarsi di conseguenza.
        if self._target is not None:
            self._layout()

    def _sync(self) -> None:
        sel = self._scene.selectedItems()
        # Esponiamo handle solo quando un singolo item utente è selezionato.
        if len(sel) != 1:
            self.detach()
            return
        item = sel[0]
        # Ignora i nostri stessi handle e cornice che potrebbero finire
        # erroneamente in selectedItems (non dovrebbero, ma siamo difensivi).
        if item in self._handles or item is self._frame:
            return
        if self._target is item:
            self._layout()
            return
        self.detach()
        self._attach(item)

    def _attach(self, item: QGraphicsItem) -> None:
        self._target = item

        self._frame = _SelectionFrame(QColor(self._theme.selection_border))
        self._add(self._frame)

        if _is_arrow(item):
            self._build_arrow_handles(item)
        else:
            self._build_generic_handles(item)
        self._layout()

    # ---- Handle factories --------------------------------------------------

    def _build_arrow_handles(self, arrow: QGraphicsItem) -> None:
        theme = self._theme

        def make_endpoint(which: str) -> _Handle:
            def on_press(_scene_pos: QPointF) -> None:
                pass

            def on_drag(scene_pos: QPointF) -> None:
                target = self._target
                if target is None or not _is_arrow(target):
                    return
                # Converti scene_pos in coordinate item-local (lo stesso sistema
                # in cui ArrowItem.set_endpoints si aspetta i punti).
                local = target.mapFromScene(scene_pos)
                start, end = target.endpoints()
                if which == "start":
                    target.set_endpoints(local, end)
                else:
                    target.set_endpoints(start, local)
                self._layout()

            return _Handle(
                QColor(theme.handle_endpoint_fill),
                QColor(theme.handle_endpoint_border),
                on_drag=on_drag, on_press=on_press,
                cursor=Qt.CursorShape.SizeAllCursor,
            )

        self._handles.append(make_endpoint("start"))
        self._handles.append(make_endpoint("end"))
        for h in self._handles:
            self._add(h)

    def _build_generic_handles(self, item: QGraphicsItem) -> None:
        # 4 corner handle per resize uniforme attorno al centro.
        corners = ["nw", "ne", "se", "sw"]
        for corner in corners:
            h = self._make_corner_handle(item, corner)
            self._handles.append(h)
            self._add(h)

        # Rotation handle
        rot = self._make_rotate_handle(item)
        self._handles.append(rot)
        self._add(rot)

        # Linea che connette il rotate handle alla parte alta dell'item.
        self._rot_line = QGraphicsLineItem()
        pen = QPen(QColor(self._theme.selection_border), 1, Qt.PenStyle.DashLine)
        pen.setCosmetic(True)
        self._rot_line.setPen(pen)
        self._rot_line.setZValue(19_998)
        self._add(self._rot_line)

    def _make_corner_handle(self, item: QGraphicsItem, corner: str) -> _Handle:
        cursor_map = {
            "nw": Qt.CursorShape.SizeFDiagCursor,
            "se": Qt.CursorShape.SizeFDiagCursor,
            "ne": Qt.CursorShape.SizeBDiagCursor,
            "sw": Qt.CursorShape.SizeBDiagCursor,
        }

        def on_press(scene_pos: QPointF) -> None:
            self._drag_initial_scale = item.scale()
            self._drag_pivot_scene = item.sceneBoundingRect().center()
            self._drag_initial_distance = max(
                1.0,
                math.hypot(
                    scene_pos.x() - self._drag_pivot_scene.x(),
                    scene_pos.y() - self._drag_pivot_scene.y(),
                ),
            )

        def on_drag(scene_pos: QPointF) -> None:
            if self._drag_pivot_scene is None:
                return
            dist = math.hypot(
                scene_pos.x() - self._drag_pivot_scene.x(),
                scene_pos.y() - self._drag_pivot_scene.y(),
            )
            ratio = max(0.05, dist / self._drag_initial_distance)
            new_scale = self._drag_initial_scale * ratio
            # Manteniamo il centro dell'item fisso mentre lo scaliamo.
            old_center = item.sceneBoundingRect().center()
            item.setScale(new_scale)
            new_center = item.sceneBoundingRect().center()
            item.moveBy(old_center.x() - new_center.x(), old_center.y() - new_center.y())
            self._layout()

        return _Handle(
            QColor(self._theme.handle_fill),
            QColor(self._theme.handle_border),
            on_drag=on_drag, on_press=on_press,
            cursor=cursor_map[corner],
        )

    def _make_rotate_handle(self, item: QGraphicsItem) -> _Handle:
        def on_press(scene_pos: QPointF) -> None:
            self._drag_initial_rotation = item.rotation()
            self._drag_pivot_scene = item.sceneBoundingRect().center()
            self._drag_start_scene = scene_pos

        def on_drag(scene_pos: QPointF) -> None:
            if self._drag_pivot_scene is None or self._drag_start_scene is None:
                return
            cx, cy = self._drag_pivot_scene.x(), self._drag_pivot_scene.y()
            a0 = math.degrees(math.atan2(
                self._drag_start_scene.y() - cy,
                self._drag_start_scene.x() - cx,
            ))
            a1 = math.degrees(math.atan2(scene_pos.y() - cy, scene_pos.x() - cx))
            delta = a1 - a0
            # Rotazione attorno al centro: setRotation ruota attorno al
            # transform origin point, che impostiamo al centro dell'item.
            self._set_rotation_around_center(item, self._drag_initial_rotation + delta)
            self._layout()

        return _Handle(
            QColor(self._theme.rotate_fill),
            QColor(self._theme.handle_border),
            on_drag=on_drag, on_press=on_press,
            cursor=Qt.CursorShape.PointingHandCursor,
        )

    @staticmethod
    def _set_rotation_around_center(item: QGraphicsItem, angle_deg: float) -> None:
        """Imposta la rotazione mantenendo il centro dell'item invariato in scene."""
        old_center = item.sceneBoundingRect().center()
        item.setTransformOriginPoint(item.boundingRect().center())
        item.setRotation(angle_deg)
        new_center = item.sceneBoundingRect().center()
        item.moveBy(old_center.x() - new_center.x(), old_center.y() - new_center.y())

    # ---- Layout ------------------------------------------------------------

    def _layout(self) -> None:
        item = self._target
        if item is None or item.scene() is not self._scene:
            return

        sbr = item.sceneBoundingRect()
        if self._frame is not None:
            self._frame.setRect(sbr.adjusted(-2, -2, 2, 2))

        if _is_arrow(item) and len(self._handles) == 2:
            start, end = item.endpoints()
            scene_start = item.mapToScene(start)
            scene_end = item.mapToScene(end)
            self._handles[0].setPos(scene_start)
            self._handles[1].setPos(scene_end)
            return

        # Generic: 4 corners + 1 rotation
        if len(self._handles) == 5:
            self._handles[0].setPos(sbr.topLeft())
            self._handles[1].setPos(sbr.topRight())
            self._handles[2].setPos(sbr.bottomRight())
            self._handles[3].setPos(sbr.bottomLeft())
            top_mid = QPointF((sbr.left() + sbr.right()) / 2, sbr.top())
            rot_pos = QPointF(top_mid.x(), top_mid.y() - ROTATE_OFFSET)
            self._handles[4].setPos(rot_pos)
            if self._rot_line is not None:
                self._rot_line.setLine(top_mid.x(), top_mid.y(), rot_pos.x(), rot_pos.y())


def apply_uniform_scale_delta(item: QGraphicsItem, factor: float) -> None:
    """Helper per scorciatoie tastiera: scala mantenendo il centro fisso."""
    old_center = item.sceneBoundingRect().center()
    item.setScale(max(0.05, item.scale() * factor))
    new_center = item.sceneBoundingRect().center()
    item.moveBy(old_center.x() - new_center.x(), old_center.y() - new_center.y())


def apply_rotation_delta(item: QGraphicsItem, delta_deg: float) -> None:
    """Helper per scorciatoie tastiera: ruota attorno al centro."""
    old_center = item.sceneBoundingRect().center()
    item.setTransformOriginPoint(item.boundingRect().center())
    item.setRotation(item.rotation() + delta_deg)
    new_center = item.sceneBoundingRect().center()
    item.moveBy(old_center.x() - new_center.x(), old_center.y() - new_center.y())


def reset_transformation(item: QGraphicsItem) -> None:
    """Reset rotazione e scala a 1, mantenendo la posizione centrata."""
    old_center = item.sceneBoundingRect().center()
    item.setRotation(0)
    item.setScale(1)
    new_center = item.sceneBoundingRect().center()
    item.moveBy(old_center.x() - new_center.x(), old_center.y() - new_center.y())
