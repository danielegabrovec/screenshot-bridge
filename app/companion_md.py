"""Companion .md export: lista descrizioni callout + coordinate normalizzate.

Scopo: dare a Claude un file di testo machine-readable che descrive
*cosa* l'utente ha annotato e *dove*. Le coordinate sono normalizzate (%)
rispetto allo sceneRect, così sono indipendenti dalle dimensioni del PNG.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable

from PyQt6.QtCore import QRectF
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsScene


def _description_for(item: QGraphicsItem) -> str:
    """Legge la descrizione testuale impostata via context-menu, se c'è."""
    from .canvas_editor import ITEM_DESCRIPTION_ROLE
    v = item.data(ITEM_DESCRIPTION_ROLE)
    return str(v) if isinstance(v, str) and v.strip() else ""


def _kind(item: QGraphicsItem) -> str:
    """Etichetta human-readable del tipo di item."""
    cls = type(item).__name__
    mapping = {
        "ArrowItem": "freccia",
        "QGraphicsRectItem": "rettangolo",
        "QGraphicsEllipseItem": "ellisse",
        "QGraphicsTextItem": "testo",
        "QGraphicsSimpleTextItem": "testo",
        "QGraphicsPathItem": "tratto",
        "QGraphicsItemGroup": "stencil",
    }
    return mapping.get(cls, cls.replace("QGraphics", "").replace("Item", "").lower())


def build_markdown(
    scene: QGraphicsScene,
    annotated: Iterable[QGraphicsItem],
    *,
    png_filename: str,
    description: str,
) -> str:
    """Genera il testo Markdown companion."""
    rect: QRectF = scene.sceneRect()
    w = rect.width() or 1.0
    h = rect.height() or 1.0
    lines: list[str] = []
    lines.append(f"# {description or png_filename}")
    lines.append("")
    lines.append(f"- **PNG:** `{png_filename}`")
    lines.append(f"- **Generato:** {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"- **Dimensioni scena:** {int(w)}×{int(h)} px")
    lines.append("")
    callouts = [(it, _description_for(it)) for it in annotated]
    described = [(it, d) for it, d in callouts if d]
    if described:
        lines.append("## Annotazioni con descrizione")
        lines.append("")
        for i, (it, d) in enumerate(described, 1):
            sbr = it.sceneBoundingRect()
            xp = sbr.center().x() / w * 100.0
            yp = sbr.center().y() / h * 100.0
            lines.append(f"{i}. **{_kind(it)}** @ ~({xp:.1f}%, {yp:.1f}%) — {d}")
        lines.append("")
    other = [it for it, d in callouts if not d]
    if other:
        lines.append("## Altre annotazioni (senza descrizione)")
        lines.append("")
        for it in other:
            sbr = it.sceneBoundingRect()
            xp = sbr.center().x() / w * 100.0
            yp = sbr.center().y() / h * 100.0
            lines.append(f"- {_kind(it)} @ ~({xp:.1f}%, {yp:.1f}%)")
        lines.append("")
    return "\n".join(lines)


def write_companion(
    png_path: Path,
    scene: QGraphicsScene,
    annotated: Iterable[QGraphicsItem],
    description: str,
) -> Path:
    """Scrive il file `.md` accanto al PNG. Ritorna il path scritto."""
    md_path = png_path.with_suffix(".md")
    content = build_markdown(
        scene,
        annotated,
        png_filename=png_path.name,
        description=description,
    )
    md_path.write_text(content, encoding="utf-8")
    return md_path
