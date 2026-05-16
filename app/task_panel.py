"""Lateral panel with pending / done task lists."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QGuiApplication, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QMenu,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from . import storage
from .storage import Task

ROLE_TASK_PATH = Qt.ItemDataRole.UserRole + 1
ROLE_TASK_STATUS = Qt.ItemDataRole.UserRole + 2


class _TaskList(QListWidget):
    task_activated = pyqtSignal(Task)
    mark_done_requested = pyqtSignal(Task)
    delete_requested = pyqtSignal(Task)

    def __init__(self, status: str, parent=None) -> None:
        super().__init__(parent)
        self._status = status
        self.setIconSize(QSize(80, 60))
        self.setUniformItemSizes(False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)
        self.itemActivated.connect(self._on_activate)
        self.itemClicked.connect(self._on_activate)

    def populate(self, tasks: list[Task]) -> None:
        self.clear()
        for task in tasks:
            item = QListWidgetItem()
            label = task.description or task.png_path.stem
            ts = task.created_at.replace("T", " ") if task.created_at else ""
            item.setText(f"{label}\n{ts}")
            pix = QPixmap(str(task.png_path))
            if not pix.isNull():
                item.setIcon(QIcon(pix.scaled(80, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)))
            item.setData(ROLE_TASK_PATH, str(task.png_path))
            item.setData(ROLE_TASK_STATUS, task.status)
            item.setToolTip(str(task.png_path))
            self.addItem(item)

    def _task_for_item(self, item: QListWidgetItem) -> Optional[Task]:
        if item is None:
            return None
        png = Path(item.data(ROLE_TASK_PATH) or "")
        if not png.exists():
            return None
        # Rebuild a Task instance lazily
        json_path = png.with_suffix(".json")
        description = item.text().split("\n")[0]
        return Task(png, json_path, description, "", item.data(ROLE_TASK_STATUS))

    def _on_activate(self, item: QListWidgetItem) -> None:
        task = self._task_for_item(item)
        if task is not None:
            self.task_activated.emit(task)

    def _on_context_menu(self, pos) -> None:
        item = self.itemAt(pos)
        if item is None:
            return
        task = self._task_for_item(item)
        if task is None:
            return
        png_path = task.png_path

        menu = QMenu(self)

        # Azioni di "condivisione" del path — sono quelle che la maggior
        # parte degli utenti cerca col tasto destro: aprire, condividere o
        # incollare il path da qualche altra parte (es. nel prompt di
        # Claude). Le mettiamo PRIMA perché sono le più richieste.
        copy_path_action = QAction("Copia path", self)
        copy_path_action.setShortcut("Ctrl+Shift+C")
        copy_path_action.triggered.connect(lambda: self._copy_to_clipboard(str(png_path)))
        menu.addAction(copy_path_action)

        copy_name_action = QAction("Copia nome file", self)
        copy_name_action.triggered.connect(lambda: self._copy_to_clipboard(png_path.name))
        menu.addAction(copy_name_action)

        open_action = QAction("Apri con app predefinita", self)
        open_action.triggered.connect(lambda: self._open_with_default_app(png_path))
        menu.addAction(open_action)

        reveal_action = QAction("Apri cartella contenente", self)
        reveal_action.triggered.connect(lambda: self._reveal_in_explorer(png_path))
        menu.addAction(reveal_action)

        menu.addSeparator()
        if self._status == "pending":
            done_action = QAction("Marca come completato", self)
            done_action.triggered.connect(lambda: self.mark_done_requested.emit(task))
            menu.addAction(done_action)
        delete_action = QAction("Elimina", self)
        delete_action.triggered.connect(lambda: self.delete_requested.emit(task))
        menu.addAction(delete_action)
        menu.exec(self.mapToGlobal(pos))

    @staticmethod
    def _copy_to_clipboard(text: str) -> None:
        cb = QGuiApplication.clipboard()
        if cb is not None:
            cb.setText(text)

    @staticmethod
    def _open_with_default_app(path: Path) -> None:
        if not path.exists():
            return
        # Su Windows usiamo os.startfile (apertura associata di Explorer);
        # su macOS `open`, su Linux `xdg-open`. Evitiamo QDesktopServices
        # perché su alcune build PyQt6 ritorna False senza errore.
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(path))  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except OSError:
            pass

    @staticmethod
    def _reveal_in_explorer(path: Path) -> None:
        if not path.exists():
            return
        try:
            if sys.platform.startswith("win"):
                # `/select,` evidenzia il file nella nuova finestra Explorer.
                subprocess.Popen(["explorer", "/select,", str(path)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", str(path)])
            else:
                # Linux: aprire la cartella padre (xdg-open non supporta /select).
                subprocess.Popen(["xdg-open", str(path.parent)])
        except OSError:
            pass


class TaskPanel(QWidget):
    task_activated = pyqtSignal(Task)
    mark_done_requested = pyqtSignal(Task)
    delete_requested = pyqtSignal(Task)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget(self)
        self.pending_list = _TaskList("pending", self)
        self.done_list = _TaskList("done", self)
        self.tabs.addTab(self.pending_list, "Da fare")
        self.tabs.addTab(self.done_list, "Completati")
        layout.addWidget(self.tabs)

        for lst in (self.pending_list, self.done_list):
            lst.task_activated.connect(self.task_activated)
            lst.mark_done_requested.connect(self.mark_done_requested)
            lst.delete_requested.connect(self.delete_requested)

        self.refresh()

    def refresh(self) -> None:
        self.pending_list.populate(storage.list_pending())
        self.done_list.populate(storage.list_done())
        self.tabs.setTabText(0, f"Da fare ({self.pending_list.count()})")
        self.tabs.setTabText(1, f"Completati ({self.done_list.count()})")
