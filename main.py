"""Screenshot Bridge — entry point."""
from __future__ import annotations

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.theme import ThemeManager


def main() -> int:
    # HiDPI: in PyQt6 lo scaling è già attivo di default; le QIcon
    # high-dpi richiedono ancora questo flag (no-op silenzioso se assente).
    try:
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception:
        pass

    app = QApplication(sys.argv)
    # Necessari prima di QSettings() costruttore senza argomenti:
    # su Windows determinano la chiave HKCU\Software\<Org>\<App>.
    app.setOrganizationName("ScreenshotBridge")
    app.setApplicationName("Screenshot Bridge")

    # Applica il tema salvato (default DARK al primo avvio).
    ThemeManager.instance().apply_initial()

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
