"""Filesystem persistence for screenshot tasks."""
from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

ROOT = Path(__file__).resolve().parent.parent / "screenshots"
PENDING_DIR = ROOT / "da-fare"
DONE_DIR = ROOT / "completati"

Status = Literal["pending", "in_progress", "done"]


@dataclass
class Task:
    png_path: Path
    json_path: Path
    description: str
    created_at: str
    status: Status

    @property
    def created_dt(self) -> datetime:
        try:
            return datetime.fromisoformat(self.created_at)
        except ValueError:
            return datetime.fromtimestamp(self.png_path.stat().st_mtime)

    @property
    def md_path(self) -> Path:
        """Path del companion .md (può esistere o no)."""
        return self.png_path.with_suffix(".md")


def ensure_dirs() -> None:
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    DONE_DIR.mkdir(parents=True, exist_ok=True)


def _slugify(text: str, max_len: int = 30) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:max_len] or "screenshot"


def save_task(image_bytes: bytes, description: str) -> Task:
    """Save a PNG + JSON companion in `da-fare/`. Returns the created Task."""
    ensure_dirs()
    now = datetime.now()
    slug = _slugify(description)
    stem = f"{now.strftime('%Y-%m-%d_%H%M%S')}_{slug}"
    png_path = PENDING_DIR / f"{stem}.png"
    json_path = PENDING_DIR / f"{stem}.json"

    png_path.write_bytes(image_bytes)
    meta = {
        "description": description,
        "created_at": now.isoformat(timespec="seconds"),
        "status": "pending",
    }
    json_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return Task(png_path, json_path, description, meta["created_at"], "pending")


def _read_meta(json_path: Path) -> dict:
    if not json_path.exists():
        return {}
    try:
        return json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _write_meta(json_path: Path, meta: dict) -> None:
    json_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def mark_in_progress(png_path: Path) -> Task:
    """Aggiorna lo status del JSON a 'in_progress'. NON sposta il file."""
    png_path = Path(png_path)
    json_path = png_path.with_suffix(".json")
    meta = _read_meta(json_path)
    meta["status"] = "in_progress"
    meta["started_at"] = datetime.now().isoformat(timespec="seconds")
    if json_path.exists() or meta:
        _write_meta(json_path, meta)
    return Task(
        png_path, json_path,
        meta.get("description", png_path.stem),
        meta.get("created_at", ""),
        "in_progress",
    )


def mark_done(png_path: Path) -> Task:
    """Move PNG + JSON (+ optional .md) from `da-fare/` to `completati/`."""
    ensure_dirs()
    png_path = Path(png_path)
    json_path = png_path.with_suffix(".json")
    md_path = png_path.with_suffix(".md")

    new_png = DONE_DIR / png_path.name
    new_json = DONE_DIR / json_path.name
    new_md = DONE_DIR / md_path.name

    shutil.move(str(png_path), str(new_png))
    if json_path.exists():
        shutil.move(str(json_path), str(new_json))
        meta = _read_meta(new_json)
        meta["status"] = "done"
        meta["completed_at"] = datetime.now().isoformat(timespec="seconds")
        _write_meta(new_json, meta)
    else:
        meta = {"description": png_path.stem, "status": "done"}
    if md_path.exists():
        shutil.move(str(md_path), str(new_md))

    return Task(
        new_png,
        new_json,
        meta.get("description", png_path.stem),
        meta.get("created_at", ""),
        "done",
    )


def delete_task(png_path: Path) -> None:
    png_path = Path(png_path)
    json_path = png_path.with_suffix(".json")
    md_path = png_path.with_suffix(".md")
    for p in (png_path, json_path, md_path):
        if p.exists():
            try:
                p.unlink()
            except OSError:
                pass


def _scan(folder: Path, status_fallback: Status) -> list[Task]:
    if not folder.exists():
        return []
    tasks: list[Task] = []
    for png in sorted(folder.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True):
        json_path = png.with_suffix(".json")
        description = png.stem
        created_at = ""
        status: Status = status_fallback
        if json_path.exists():
            meta = _read_meta(json_path)
            description = meta.get("description", description)
            created_at = meta.get("created_at", "")
            s = meta.get("status")
            if s in ("pending", "in_progress", "done"):
                status = s  # type: ignore[assignment]
        tasks.append(Task(png, json_path, description, created_at, status))
    return tasks


def list_pending() -> list[Task]:
    """Tutti i task in `da-fare/` (sia pending sia in_progress)."""
    return _scan(PENDING_DIR, "pending")


def list_done() -> list[Task]:
    return _scan(DONE_DIR, "done")


def claude_handoff_text(task: Task, template: Optional[str] = None) -> str:
    """Markdown line ready to paste in Claude Code terminal.

    Il template può contenere i placeholder `{png}`, `{description}`, `{md}`.
    Se assente, usa il default.
    """
    tpl = template or "Vedi screenshot: {png} — Da fare: {description}"
    return tpl.format(
        png=str(task.png_path),
        description=task.description,
        md=str(task.md_path) if task.md_path.exists() else "",
    )
