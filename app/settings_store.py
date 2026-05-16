"""Tiny typed wrapper around QSettings.

Su Windows i valori finiscono in `HKCU\\Software\\ScreenshotBridge\\Screenshot Bridge`.
Per evitare di "perderli" nel registro forziamo il formato INI con file accanto
all'app: `%LOCALAPPDATA%\\ScreenshotBridge\\settings.ini`. L'utente può
ispezionarlo, copiarlo o cancellarlo per reset.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from PyQt6.QtCore import QByteArray, QSettings


# Forziamo il formato INI in un percorso prevedibile.
_INI_INSTALLED = False


def _install_ini_format() -> None:
    global _INI_INSTALLED
    if _INI_INSTALLED:
        return
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".config")
    folder = Path(base) / "ScreenshotBridge"
    folder.mkdir(parents=True, exist_ok=True)
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(folder),
    )
    _INI_INSTALLED = True


class Settings:
    """Adapter tipato per le chiavi note dell'app."""

    def __init__(self) -> None:
        _install_ini_format()
        self._s = QSettings()

    # ---- generic helpers ---------------------------------------------------

    def _get(self, key: str, default: Any, type_: Optional[type] = None) -> Any:
        if type_ is None:
            return self._s.value(key, default)
        return self._s.value(key, default, type=type_)

    def _set(self, key: str, value: Any) -> None:
        self._s.setValue(key, value)

    def sync(self) -> None:
        self._s.sync()

    # ---- window geometry / dock state -------------------------------------

    def window_geometry(self) -> Optional[QByteArray]:
        v = self._get("window/geometry", None)
        return v if isinstance(v, QByteArray) else None

    def set_window_geometry(self, value: QByteArray) -> None:
        self._set("window/geometry", value)

    def window_state(self) -> Optional[QByteArray]:
        v = self._get("window/state", None)
        return v if isinstance(v, QByteArray) else None

    def set_window_state(self, value: QByteArray) -> None:
        self._set("window/state", value)

    # ---- tool defaults -----------------------------------------------------

    def last_tool(self) -> str:
        return self._get("tool/last", "select", str)

    def set_last_tool(self, value: str) -> None:
        self._set("tool/last", value)

    def color(self) -> str:
        return self._get("tool/color", "#ef4444", str)

    def set_color(self, value: str) -> None:
        self._set("tool/color", value)

    def thickness(self) -> int:
        return int(self._get("tool/thickness", 4, int))

    def set_thickness(self, value: int) -> None:
        self._set("tool/thickness", int(value))

    # ---- capture settings --------------------------------------------------

    def capture_countdown(self) -> int:
        return int(self._get("capture/countdown", 0, int))

    def set_capture_countdown(self, value: int) -> None:
        self._set("capture/countdown", int(value))

    # ---- snap --------------------------------------------------------------

    def snap_enabled(self) -> bool:
        return bool(self._get("ui/snap", True, bool))

    def set_snap_enabled(self, value: bool) -> None:
        self._set("ui/snap", bool(value))

    # ---- tray --------------------------------------------------------------

    def tray_enabled(self) -> bool:
        return bool(self._get("tray/enabled", True, bool))

    def set_tray_enabled(self, value: bool) -> None:
        self._set("tray/enabled", bool(value))

    def minimize_on_close(self) -> bool:
        return bool(self._get("tray/minimize_on_close", False, bool))

    def set_minimize_on_close(self, value: bool) -> None:
        self._set("tray/minimize_on_close", bool(value))

    # ---- claude handoff template -------------------------------------------

    def handoff_template(self) -> str:
        return self._get(
            "claude/handoff_format",
            "Vedi screenshot: {png} — Da fare: {description}",
            str,
        )

    def set_handoff_template(self, value: str) -> None:
        self._set("claude/handoff_format", value)
