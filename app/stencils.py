"""Wireframe-style UI stencils (button, input, dropdown, ...) for the canvas.

Each factory function returns a `QGraphicsItemGroup` that is selectable and
movable. Stencils are visual only — they exist to communicate UI intent to
Claude, not to behave like real widgets.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPainterPath, QPen, QPolygonF
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsItemGroup,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsPolygonItem,
    QGraphicsRectItem,
    QGraphicsSimpleTextItem,
)


# Palette (wireframe look: dark outline on light fill)
OUTLINE = QColor("#1f2933")
FILL = QColor("#ffffff")
ACCENT = QColor("#3b82f6")
ACCENT_FILL = QColor("#dbeafe")
MUTED = QColor("#6b7280")
DASH_FILL = QColor("#f3f4f6")


def _pen(color: QColor = OUTLINE, width: float = 1.5, dashed: bool = False) -> QPen:
    p = QPen(color, width)
    p.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setCapStyle(Qt.PenCapStyle.RoundCap)
    if dashed:
        p.setStyle(Qt.PenStyle.DashLine)
    return p


def _font(size: int = 11, bold: bool = False) -> QFont:
    f = QFont("Segoe UI")
    f.setPointSize(size)
    f.setBold(bold)
    return f


def _make_group() -> QGraphicsItemGroup:
    group = QGraphicsItemGroup()
    group.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
    group.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
    return group


def _text(text: str, font: QFont, color: QColor = OUTLINE) -> QGraphicsSimpleTextItem:
    item = QGraphicsSimpleTextItem(text)
    item.setFont(font)
    item.setBrush(QBrush(color))
    return item


def _center_text(text_item: QGraphicsSimpleTextItem, rect: QRectF) -> None:
    br = text_item.boundingRect()
    x = rect.x() + (rect.width() - br.width()) / 2
    y = rect.y() + (rect.height() - br.height()) / 2
    text_item.setPos(x, y)


# ---------------------------------------------------------------------------
# Stencils
# ---------------------------------------------------------------------------


def button_primary(text: str = "Pulsante") -> QGraphicsItemGroup:
    group = _make_group()
    rect = QRectF(0, 0, 140, 36)
    body = QGraphicsRectItem(rect)
    body.setPen(_pen(ACCENT))
    body.setBrush(QBrush(ACCENT))
    # rounded look via path
    path = QPainterPath()
    path.addRoundedRect(rect, 6, 6)
    rounded = QGraphicsPathItem(path)
    rounded.setPen(_pen(ACCENT))
    rounded.setBrush(QBrush(ACCENT))
    group.addToGroup(rounded)
    label = _text(text, _font(11, bold=True), QColor("#ffffff"))
    _center_text(label, rect)
    group.addToGroup(label)
    return group


def button_secondary(text: str = "Pulsante") -> QGraphicsItemGroup:
    group = _make_group()
    rect = QRectF(0, 0, 140, 36)
    path = QPainterPath()
    path.addRoundedRect(rect, 6, 6)
    rounded = QGraphicsPathItem(path)
    rounded.setPen(_pen(OUTLINE, 1.5))
    rounded.setBrush(QBrush(FILL))
    group.addToGroup(rounded)
    label = _text(text, _font(11), OUTLINE)
    _center_text(label, rect)
    group.addToGroup(label)
    return group


def text_input(placeholder: str = "Inserisci testo...") -> QGraphicsItemGroup:
    group = _make_group()
    rect = QRectF(0, 0, 220, 34)
    path = QPainterPath()
    path.addRoundedRect(rect, 4, 4)
    body = QGraphicsPathItem(path)
    body.setPen(_pen(OUTLINE))
    body.setBrush(QBrush(FILL))
    group.addToGroup(body)
    label = _text(placeholder, _font(10), MUTED)
    label.setPos(rect.x() + 10, rect.y() + (rect.height() - label.boundingRect().height()) / 2)
    group.addToGroup(label)
    return group


def textarea(placeholder: str = "Testo...") -> QGraphicsItemGroup:
    group = _make_group()
    rect = QRectF(0, 0, 260, 90)
    path = QPainterPath()
    path.addRoundedRect(rect, 4, 4)
    body = QGraphicsPathItem(path)
    body.setPen(_pen(OUTLINE))
    body.setBrush(QBrush(FILL))
    group.addToGroup(body)
    label = _text(placeholder, _font(10), MUTED)
    label.setPos(rect.x() + 10, rect.y() + 8)
    group.addToGroup(label)
    return group


def label(text: str = "Etichetta") -> QGraphicsItemGroup:
    group = _make_group()
    item = _text(text, _font(12), OUTLINE)
    group.addToGroup(item)
    return group


def heading(text: str = "Titolo sezione") -> QGraphicsItemGroup:
    group = _make_group()
    title = _text(text, _font(18, bold=True), OUTLINE)
    group.addToGroup(title)
    # underline accent
    br = title.boundingRect()
    line = QGraphicsRectItem(QRectF(0, br.height() + 4, 40, 3))
    line.setPen(_pen(ACCENT, 0))
    line.setBrush(QBrush(ACCENT))
    group.addToGroup(line)
    return group


def checkbox(text: str = "Opzione", checked: bool = False) -> QGraphicsItemGroup:
    group = _make_group()
    box = QGraphicsRectItem(QRectF(0, 0, 18, 18))
    box.setPen(_pen(OUTLINE))
    box.setBrush(QBrush(FILL))
    group.addToGroup(box)
    if checked:
        check = QGraphicsPathItem()
        path = QPainterPath()
        path.moveTo(3, 9)
        path.lineTo(8, 14)
        path.lineTo(15, 4)
        check.setPath(path)
        check.setPen(_pen(ACCENT, 2.5))
        group.addToGroup(check)
    lbl = _text(text, _font(11), OUTLINE)
    lbl.setPos(26, (18 - lbl.boundingRect().height()) / 2)
    group.addToGroup(lbl)
    return group


def radio(text: str = "Opzione", selected: bool = False) -> QGraphicsItemGroup:
    group = _make_group()
    outer = QGraphicsEllipseItem(QRectF(0, 0, 18, 18))
    outer.setPen(_pen(OUTLINE))
    outer.setBrush(QBrush(FILL))
    group.addToGroup(outer)
    if selected:
        inner = QGraphicsEllipseItem(QRectF(4, 4, 10, 10))
        inner.setPen(_pen(ACCENT, 0))
        inner.setBrush(QBrush(ACCENT))
        group.addToGroup(inner)
    lbl = _text(text, _font(11), OUTLINE)
    lbl.setPos(26, (18 - lbl.boundingRect().height()) / 2)
    group.addToGroup(lbl)
    return group


def toggle_switch(on: bool = True) -> QGraphicsItemGroup:
    group = _make_group()
    rect = QRectF(0, 0, 44, 22)
    path = QPainterPath()
    path.addRoundedRect(rect, 11, 11)
    track = QGraphicsPathItem(path)
    color = ACCENT if on else MUTED
    track.setPen(_pen(color, 0))
    track.setBrush(QBrush(color))
    group.addToGroup(track)
    knob_x = 24 if on else 2
    knob = QGraphicsEllipseItem(QRectF(knob_x, 2, 18, 18))
    knob.setPen(_pen(QColor("#ffffff"), 0))
    knob.setBrush(QBrush(QColor("#ffffff")))
    group.addToGroup(knob)
    return group


def dropdown(text: str = "Seleziona...") -> QGraphicsItemGroup:
    group = _make_group()
    rect = QRectF(0, 0, 220, 34)
    path = QPainterPath()
    path.addRoundedRect(rect, 4, 4)
    body = QGraphicsPathItem(path)
    body.setPen(_pen(OUTLINE))
    body.setBrush(QBrush(FILL))
    group.addToGroup(body)
    lbl = _text(text, _font(10), OUTLINE)
    lbl.setPos(10, (rect.height() - lbl.boundingRect().height()) / 2)
    group.addToGroup(lbl)
    # chevron
    chev = QGraphicsPolygonItem(
        QPolygonF([QPointF(200, 14), QPointF(210, 14), QPointF(205, 21)])
    )
    chev.setPen(_pen(OUTLINE, 0))
    chev.setBrush(QBrush(OUTLINE))
    group.addToGroup(chev)
    return group


def card(title: str = "Titolo card", body: str = "Contenuto della card...") -> QGraphicsItemGroup:
    group = _make_group()
    rect = QRectF(0, 0, 260, 140)
    path = QPainterPath()
    path.addRoundedRect(rect, 8, 8)
    body_rect = QGraphicsPathItem(path)
    body_rect.setPen(_pen(OUTLINE))
    body_rect.setBrush(QBrush(FILL))
    group.addToGroup(body_rect)
    t = _text(title, _font(13, bold=True), OUTLINE)
    t.setPos(14, 14)
    group.addToGroup(t)
    b = _text(body, _font(10), MUTED)
    b.setPos(14, 42)
    group.addToGroup(b)
    sep = QGraphicsLineItem(14, 110, 246, 110)
    sep.setPen(_pen(MUTED, 0.8, dashed=True))
    group.addToGroup(sep)
    return group


def image_placeholder(label_text: str = "Immagine") -> QGraphicsItemGroup:
    group = _make_group()
    rect = QRectF(0, 0, 180, 120)
    body = QGraphicsRectItem(rect)
    body.setPen(_pen(OUTLINE, dashed=True))
    body.setBrush(QBrush(DASH_FILL))
    group.addToGroup(body)
    # diagonal cross
    d1 = QGraphicsLineItem(0, 0, 180, 120)
    d2 = QGraphicsLineItem(0, 120, 180, 0)
    for ln in (d1, d2):
        ln.setPen(_pen(MUTED, 0.8))
        group.addToGroup(ln)
    lbl = _text(label_text, _font(10), MUTED)
    lbl.setPos(
        (180 - lbl.boundingRect().width()) / 2,
        (120 - lbl.boundingRect().height()) / 2,
    )
    group.addToGroup(lbl)
    return group


def icon_placeholder() -> QGraphicsItemGroup:
    group = _make_group()
    rect = QRectF(0, 0, 32, 32)
    body = QGraphicsRectItem(rect)
    body.setPen(_pen(OUTLINE))
    body.setBrush(QBrush(FILL))
    group.addToGroup(body)
    star = QGraphicsPolygonItem(
        QPolygonF([
            QPointF(16, 4), QPointF(20, 13), QPointF(29, 13),
            QPointF(22, 19), QPointF(25, 28), QPointF(16, 23),
            QPointF(7, 28), QPointF(10, 19), QPointF(3, 13),
            QPointF(12, 13),
        ])
    )
    star.setPen(_pen(OUTLINE, 1))
    star.setBrush(QBrush(QColor("#fcd34d")))
    group.addToGroup(star)
    return group


def navbar(brand: str = "Brand", items: tuple[str, ...] = ("Home", "Pagina", "Contatti")) -> QGraphicsItemGroup:
    group = _make_group()
    rect = QRectF(0, 0, 520, 48)
    body = QGraphicsRectItem(rect)
    body.setPen(_pen(OUTLINE))
    body.setBrush(QBrush(QColor("#111827")))
    group.addToGroup(body)
    b = _text(brand, _font(13, bold=True), QColor("#ffffff"))
    b.setPos(16, (48 - b.boundingRect().height()) / 2)
    group.addToGroup(b)
    x = rect.width() - 16
    for it in reversed(items):
        t = _text(it, _font(11), QColor("#e5e7eb"))
        tw = t.boundingRect().width()
        x -= tw
        t.setPos(x, (48 - t.boundingRect().height()) / 2)
        group.addToGroup(t)
        x -= 20
    return group


def tab_bar(items: tuple[str, ...] = ("Generale", "Account", "Preferenze"), active: int = 0) -> QGraphicsItemGroup:
    group = _make_group()
    rect = QRectF(0, 0, 360, 36)
    underline = QGraphicsLineItem(rect.x(), rect.bottom(), rect.right(), rect.bottom())
    underline.setPen(_pen(OUTLINE, 1))
    group.addToGroup(underline)
    x = 0
    for i, name in enumerate(items):
        t = _text(name, _font(11, bold=(i == active)), OUTLINE if i == active else MUTED)
        tw = t.boundingRect().width()
        t.setPos(x + 16, (36 - t.boundingRect().height()) / 2)
        group.addToGroup(t)
        if i == active:
            mark = QGraphicsRectItem(QRectF(x + 16, rect.bottom() - 2, tw, 3))
            mark.setPen(_pen(ACCENT, 0))
            mark.setBrush(QBrush(ACCENT))
            group.addToGroup(mark)
        x += tw + 32
    return group


def list_row(text: str = "Elemento elenco", subtitle: str = "descrizione") -> QGraphicsItemGroup:
    group = _make_group()
    rect = QRectF(0, 0, 320, 56)
    body = QGraphicsRectItem(rect)
    body.setPen(_pen(OUTLINE))
    body.setBrush(QBrush(FILL))
    group.addToGroup(body)
    avatar = QGraphicsEllipseItem(QRectF(12, 12, 32, 32))
    avatar.setPen(_pen(OUTLINE))
    avatar.setBrush(QBrush(ACCENT_FILL))
    group.addToGroup(avatar)
    t = _text(text, _font(11, bold=True), OUTLINE)
    t.setPos(56, 10)
    group.addToGroup(t)
    s = _text(subtitle, _font(9), MUTED)
    s.setPos(56, 30)
    group.addToGroup(s)
    return group


def modal_dialog(title: str = "Titolo modale", body: str = "Messaggio descrittivo della dialog...") -> QGraphicsItemGroup:
    group = _make_group()
    rect = QRectF(0, 0, 380, 200)
    path = QPainterPath()
    path.addRoundedRect(rect, 10, 10)
    body_rect = QGraphicsPathItem(path)
    body_rect.setPen(_pen(OUTLINE, 2))
    body_rect.setBrush(QBrush(FILL))
    group.addToGroup(body_rect)
    t = _text(title, _font(14, bold=True), OUTLINE)
    t.setPos(20, 18)
    group.addToGroup(t)
    b = _text(body, _font(10), MUTED)
    b.setPos(20, 54)
    group.addToGroup(b)
    # action buttons (rendered as children, but the modal stays a single group)
    cancel = button_secondary("Annulla")
    cancel.setPos(180, 150)
    group.addToGroup(cancel)
    confirm = button_primary("Conferma")
    confirm.setPos(330 - 110, 150)  # right aligned
    confirm.setPos(rect.right() - 14 - 140, 150)
    group.addToGroup(confirm)
    return group


def section_panel(title: str = "Sezione") -> QGraphicsItemGroup:
    group = _make_group()
    rect = QRectF(0, 0, 320, 200)
    body = QGraphicsRectItem(rect)
    body.setPen(_pen(OUTLINE, dashed=True))
    body.setBrush(QBrush(QColor(0, 0, 0, 0)))
    group.addToGroup(body)
    t = _text(title, _font(11, bold=True), MUTED)
    t.setPos(10, 8)
    group.addToGroup(t)
    return group


# ---------------------------------------------------------------------------
# Stencils aggiuntivi (estensione sessione 2026-05-16)
# ---------------------------------------------------------------------------


def data_table(rows: int = 4, cols: int = 3) -> QGraphicsItemGroup:
    """Tabella dati con header colorato e righe alternate."""
    group = _make_group()
    cell_w, cell_h = 90.0, 28.0
    width = cell_w * cols
    # header
    header = QGraphicsRectItem(QRectF(0, 0, width, cell_h))
    header.setPen(_pen(OUTLINE))
    header.setBrush(QBrush(ACCENT_FILL))
    group.addToGroup(header)
    for c in range(cols):
        t = _text(f"Col {c + 1}", _font(10, bold=True), OUTLINE)
        t.setPos(c * cell_w + 8, 6)
        group.addToGroup(t)
    # rows
    for r in range(rows):
        y = cell_h + r * cell_h
        row_bg = QGraphicsRectItem(QRectF(0, y, width, cell_h))
        row_bg.setPen(_pen(OUTLINE, 0.8))
        row_bg.setBrush(QBrush(FILL if r % 2 == 0 else DASH_FILL))
        group.addToGroup(row_bg)
        for c in range(cols):
            t = _text("•••", _font(10), MUTED)
            t.setPos(c * cell_w + 8, y + 6)
            group.addToGroup(t)
    return group


def breadcrumb(items: tuple[str, ...] = ("Home", "Sezione", "Pagina")) -> QGraphicsItemGroup:
    """Breadcrumb di navigazione: A › B › C (ultimo bold)."""
    group = _make_group()
    x = 0.0
    for i, name in enumerate(items):
        is_last = i == len(items) - 1
        t = _text(name, _font(11, bold=is_last), OUTLINE if is_last else MUTED)
        t.setPos(x, 0)
        group.addToGroup(t)
        x += t.boundingRect().width() + 8
        if not is_last:
            sep = _text("›", _font(11), MUTED)
            sep.setPos(x, 0)
            group.addToGroup(sep)
            x += sep.boundingRect().width() + 8
    return group


def progress_bar(percent: int = 65) -> QGraphicsItemGroup:
    """Barra di progresso orizzontale."""
    group = _make_group()
    width, height = 240.0, 12.0
    pct = max(0, min(100, percent))
    track_path = QPainterPath()
    track_path.addRoundedRect(QRectF(0, 0, width, height), 6, 6)
    track = QGraphicsPathItem(track_path)
    track.setPen(_pen(OUTLINE, 0))
    track.setBrush(QBrush(DASH_FILL))
    group.addToGroup(track)
    fill_w = width * pct / 100.0
    fill_path = QPainterPath()
    fill_path.addRoundedRect(QRectF(0, 0, max(6, fill_w), height), 6, 6)
    fill = QGraphicsPathItem(fill_path)
    fill.setPen(_pen(ACCENT, 0))
    fill.setBrush(QBrush(ACCENT))
    group.addToGroup(fill)
    lbl = _text(f"{pct}%", _font(9, bold=True), OUTLINE)
    lbl.setPos(width + 8, -2)
    group.addToGroup(lbl)
    return group


def slider(percent: int = 40) -> QGraphicsItemGroup:
    """Slider orizzontale con knob circolare."""
    group = _make_group()
    width = 220.0
    pct = max(0, min(100, percent))
    knob_x = width * pct / 100.0
    # track inattivo
    track_off = QGraphicsRectItem(QRectF(0, 8, width, 4))
    track_off.setPen(_pen(MUTED, 0))
    track_off.setBrush(QBrush(MUTED))
    group.addToGroup(track_off)
    # track attivo
    track_on = QGraphicsRectItem(QRectF(0, 8, knob_x, 4))
    track_on.setPen(_pen(ACCENT, 0))
    track_on.setBrush(QBrush(ACCENT))
    group.addToGroup(track_on)
    # knob
    knob = QGraphicsEllipseItem(QRectF(knob_x - 9, 1, 18, 18))
    knob.setPen(_pen(ACCENT, 1.5))
    knob.setBrush(QBrush(FILL))
    group.addToGroup(knob)
    return group


def badge(text: str = "NEW", filled: bool = True) -> QGraphicsItemGroup:
    """Badge / pill colorato."""
    group = _make_group()
    label_item = _text(text, _font(9, bold=True), QColor("#ffffff") if filled else ACCENT)
    pad_x, pad_y = 8.0, 3.0
    br = label_item.boundingRect()
    rect = QRectF(0, 0, br.width() + pad_x * 2, br.height() + pad_y * 2)
    path = QPainterPath()
    path.addRoundedRect(rect, rect.height() / 2, rect.height() / 2)
    body = QGraphicsPathItem(path)
    body.setPen(_pen(ACCENT, 1))
    body.setBrush(QBrush(ACCENT if filled else FILL))
    group.addToGroup(body)
    label_item.setPos(pad_x, pad_y)
    group.addToGroup(label_item)
    return group


def tooltip(text: str = "Suggerimento utile") -> QGraphicsItemGroup:
    """Tooltip scuro con freccia in basso."""
    group = _make_group()
    label_item = _text(text, _font(10), QColor("#ffffff"))
    pad_x, pad_y = 10.0, 6.0
    br = label_item.boundingRect()
    rect = QRectF(0, 0, br.width() + pad_x * 2, br.height() + pad_y * 2)
    path = QPainterPath()
    path.addRoundedRect(rect, 4, 4)
    body = QGraphicsPathItem(path)
    body.setPen(_pen(QColor("#111827"), 0))
    body.setBrush(QBrush(QColor("#111827")))
    group.addToGroup(body)
    label_item.setPos(pad_x, pad_y)
    group.addToGroup(label_item)
    # punta sotto
    arrow_y = rect.bottom()
    cx = rect.width() / 2
    tip = QGraphicsPolygonItem(
        QPolygonF([
            QPointF(cx - 6, arrow_y),
            QPointF(cx + 6, arrow_y),
            QPointF(cx, arrow_y + 7),
        ])
    )
    tip.setPen(_pen(QColor("#111827"), 0))
    tip.setBrush(QBrush(QColor("#111827")))
    group.addToGroup(tip)
    return group


def chart_bar() -> QGraphicsItemGroup:
    """Grafico a barre 5 colonne (placeholder)."""
    group = _make_group()
    rect = QRectF(0, 0, 220, 130)
    body = QGraphicsRectItem(rect)
    body.setPen(_pen(OUTLINE))
    body.setBrush(QBrush(FILL))
    group.addToGroup(body)
    # asse
    axis_y = QGraphicsLineItem(20, 16, 20, 110)
    axis_x = QGraphicsLineItem(20, 110, 210, 110)
    for ax in (axis_y, axis_x):
        ax.setPen(_pen(MUTED, 1))
        group.addToGroup(ax)
    # 5 bars
    heights = [45.0, 70.0, 35.0, 85.0, 60.0]
    bar_w = 22.0
    for i, h in enumerate(heights):
        x = 32 + i * 36
        bar = QGraphicsRectItem(QRectF(x, 110 - h, bar_w, h))
        col = ACCENT if i == 3 else ACCENT_FILL
        bar.setPen(_pen(ACCENT, 1))
        bar.setBrush(QBrush(col))
        group.addToGroup(bar)
    return group


def chart_line() -> QGraphicsItemGroup:
    """Grafico a linea con punti."""
    group = _make_group()
    rect = QRectF(0, 0, 220, 130)
    body = QGraphicsRectItem(rect)
    body.setPen(_pen(OUTLINE))
    body.setBrush(QBrush(FILL))
    group.addToGroup(body)
    pts = [(30, 80), (70, 50), (110, 70), (150, 30), (190, 55)]
    path = QPainterPath()
    path.moveTo(*pts[0])
    for p in pts[1:]:
        path.lineTo(*p)
    line = QGraphicsPathItem(path)
    pen = _pen(ACCENT, 2)
    line.setPen(pen)
    line.setBrush(QBrush(Qt.GlobalColor.transparent))
    group.addToGroup(line)
    for (x, y) in pts:
        dot = QGraphicsEllipseItem(QRectF(x - 4, y - 4, 8, 8))
        dot.setPen(_pen(ACCENT, 1.5))
        dot.setBrush(QBrush(FILL))
        group.addToGroup(dot)
    return group


def calendar_picker() -> QGraphicsItemGroup:
    """Calendar mini con un giorno selezionato."""
    group = _make_group()
    rect = QRectF(0, 0, 200, 170)
    body = QGraphicsRectItem(rect)
    body.setPen(_pen(OUTLINE))
    body.setBrush(QBrush(FILL))
    group.addToGroup(body)
    # header
    hdr = _text("Maggio 2026", _font(11, bold=True), OUTLINE)
    hdr.setPos(12, 8)
    group.addToGroup(hdr)
    # giorni della settimana
    days = ["L", "M", "M", "G", "V", "S", "D"]
    cell_w = 28.0
    for i, d in enumerate(days):
        t = _text(d, _font(9), MUTED)
        t.setPos(12 + i * cell_w + 9, 30)
        group.addToGroup(t)
    # griglia 5×7
    for row in range(5):
        for col in range(7):
            x = 12 + col * cell_w
            y = 46 + row * 22
            n = row * 7 + col + 1
            if n > 31:
                continue
            if n == 12:
                pill = QGraphicsEllipseItem(QRectF(x + 4, y - 2, 22, 22))
                pill.setPen(_pen(ACCENT, 0))
                pill.setBrush(QBrush(ACCENT))
                group.addToGroup(pill)
                t = _text(str(n), _font(9, bold=True), QColor("#ffffff"))
            else:
                t = _text(str(n), _font(9), OUTLINE)
            t.setPos(x + 9, y)
            group.addToGroup(t)
    return group


def stepper(steps: tuple[str, ...] = ("Profilo", "Indirizzo", "Pagamento"), active: int = 1) -> QGraphicsItemGroup:
    """Stepper orizzontale per wizard / form a step."""
    group = _make_group()
    x = 0.0
    radius = 14.0
    for i, name in enumerate(steps):
        cx = x + radius
        cy = radius
        is_done = i < active
        is_active = i == active
        circle = QGraphicsEllipseItem(QRectF(x, 0, radius * 2, radius * 2))
        if is_active or is_done:
            circle.setPen(_pen(ACCENT, 1.5))
            circle.setBrush(QBrush(ACCENT if is_active else ACCENT_FILL))
        else:
            circle.setPen(_pen(MUTED))
            circle.setBrush(QBrush(FILL))
        group.addToGroup(circle)
        num = _text(str(i + 1), _font(10, bold=True),
                    QColor("#ffffff") if is_active else (ACCENT if is_done else MUTED))
        nb = num.boundingRect()
        num.setPos(cx - nb.width() / 2, cy - nb.height() / 2)
        group.addToGroup(num)
        label_item = _text(name, _font(10, bold=is_active),
                           OUTLINE if (is_active or is_done) else MUTED)
        label_item.setPos(x + radius * 2 + 8, radius - label_item.boundingRect().height() / 2)
        group.addToGroup(label_item)
        x += radius * 2 + 8 + label_item.boundingRect().width() + 20
        if i < len(steps) - 1:
            line = QGraphicsLineItem(x - 18, radius, x - 4, radius)
            line.setPen(_pen(MUTED, 1.5))
            group.addToGroup(line)
    return group


def file_upload() -> QGraphicsItemGroup:
    """Dropzone tratteggiata 'Trascina qui...'."""
    group = _make_group()
    rect = QRectF(0, 0, 280, 110)
    path = QPainterPath()
    path.addRoundedRect(rect, 6, 6)
    body = QGraphicsPathItem(path)
    body.setPen(_pen(ACCENT, 1.5, dashed=True))
    body.setBrush(QBrush(QColor("#eff6ff")))
    group.addToGroup(body)
    icon = _text("⬆", _font(20, bold=True), ACCENT)
    ib = icon.boundingRect()
    icon.setPos(rect.center().x() - ib.width() / 2, 14)
    group.addToGroup(icon)
    label_item = _text("Trascina qui un file", _font(10, bold=True), OUTLINE)
    lb = label_item.boundingRect()
    label_item.setPos(rect.center().x() - lb.width() / 2, 56)
    group.addToGroup(label_item)
    sub = _text("oppure clicca per sfogliare", _font(9), MUTED)
    sb = sub.boundingRect()
    sub.setPos(rect.center().x() - sb.width() / 2, 78)
    group.addToGroup(sub)
    return group


def toast_notification(text: str = "Operazione completata") -> QGraphicsItemGroup:
    """Toast notification con bordo sinistro colorato."""
    group = _make_group()
    rect = QRectF(0, 0, 280, 56)
    path = QPainterPath()
    path.addRoundedRect(rect, 6, 6)
    body = QGraphicsPathItem(path)
    body.setPen(_pen(OUTLINE, 1))
    body.setBrush(QBrush(FILL))
    group.addToGroup(body)
    # barra colorata sinistra
    bar = QGraphicsRectItem(QRectF(0, 0, 5, 56))
    bar.setPen(_pen(QColor("#22c55e"), 0))
    bar.setBrush(QBrush(QColor("#22c55e")))
    group.addToGroup(bar)
    # icona check
    icon = _text("✓", _font(14, bold=True), QColor("#22c55e"))
    icon.setPos(18, 16)
    group.addToGroup(icon)
    title = _text(text, _font(11, bold=True), OUTLINE)
    title.setPos(42, 10)
    group.addToGroup(title)
    sub = _text("Tutto è stato salvato correttamente.", _font(9), MUTED)
    sub.setPos(42, 30)
    group.addToGroup(sub)
    return group


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StencilDef:
    key: str
    label: str
    category: str
    factory: Callable[[], QGraphicsItemGroup]


CATALOG: tuple[StencilDef, ...] = (
    StencilDef("button_primary", "Pulsante primario", "Controlli", lambda: button_primary()),
    StencilDef("button_secondary", "Pulsante secondario", "Controlli", lambda: button_secondary()),
    StencilDef("text_input", "Campo testo", "Form", lambda: text_input()),
    StencilDef("textarea", "Area di testo", "Form", lambda: textarea()),
    StencilDef("dropdown", "Menu a tendina", "Form", lambda: dropdown()),
    StencilDef("checkbox", "Checkbox", "Form", lambda: checkbox(checked=True)),
    StencilDef("radio", "Radio button", "Form", lambda: radio(selected=True)),
    StencilDef("toggle", "Toggle / switch", "Form", lambda: toggle_switch(on=True)),
    StencilDef("label", "Etichetta", "Testi", lambda: label()),
    StencilDef("heading", "Titolo", "Testi", lambda: heading()),
    StencilDef("navbar", "Barra di navigazione", "Layout", lambda: navbar()),
    StencilDef("tabs", "Tab", "Layout", lambda: tab_bar()),
    StencilDef("card", "Card", "Layout", lambda: card()),
    StencilDef("section", "Sezione/Pannello", "Layout", lambda: section_panel()),
    StencilDef("list_row", "Riga lista", "Contenuti", lambda: list_row()),
    StencilDef("image", "Immagine (placeholder)", "Contenuti", lambda: image_placeholder()),
    StencilDef("icon", "Icona", "Contenuti", lambda: icon_placeholder()),
    StencilDef("modal", "Modale / Dialog", "Layout", lambda: modal_dialog()),
    # --- estensione (sessione 2026-05-16) ---
    StencilDef("badge", "Badge / Pill", "Controlli", lambda: badge()),
    StencilDef("progress_bar", "Barra di progresso", "Form", lambda: progress_bar()),
    StencilDef("slider", "Slider", "Form", lambda: slider()),
    StencilDef("file_upload", "Upload file", "Form", lambda: file_upload()),
    StencilDef("calendar_picker", "Date picker", "Form", lambda: calendar_picker()),
    StencilDef("breadcrumb", "Breadcrumb", "Layout", lambda: breadcrumb()),
    StencilDef("stepper", "Stepper / Wizard", "Layout", lambda: stepper()),
    StencilDef("data_table", "Tabella dati", "Contenuti", lambda: data_table()),
    StencilDef("chart_bar", "Grafico a barre", "Contenuti", lambda: chart_bar()),
    StencilDef("chart_line", "Grafico a linea", "Contenuti", lambda: chart_line()),
    StencilDef("tooltip", "Tooltip", "Contenuti", lambda: tooltip()),
    StencilDef("toast", "Toast notification", "Contenuti", lambda: toast_notification()),
)


def by_key(key: str) -> StencilDef | None:
    for s in CATALOG:
        if s.key == key:
            return s
    return None


def categories() -> list[str]:
    seen: list[str] = []
    for s in CATALOG:
        if s.category not in seen:
            seen.append(s.category)
    return seen
