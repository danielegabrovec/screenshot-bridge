"""Fullscreen transparent overlay for area selection screenshot.

Features:
- Drag area selection (Esc per annullare)
- Countdown 3-2-1 opzionale (delay_sec)
- Pulsante "Schermo intero" + "Annulla" in basso
- Cattura full-screen senza overlay tramite helper top-level
"""
from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtCore import QPoint, QRect, Qt, QTimer
from PyQt6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import QWidget


class CaptureOverlay(QWidget):
    """A frameless fullscreen widget that lets the user drag a selection
    rectangle; on release calls `on_captured(pixmap)` with the cropped image.
    """

    def __init__(
        self,
        on_captured: Callable[[Optional[QPixmap]], None],
        *,
        delay_sec: int = 0,
    ) -> None:
        super().__init__(None)
        self._on_captured = on_captured
        self._origin: Optional[QPoint] = None
        self._current: Optional[QPoint] = None
        self._countdown = max(0, int(delay_sec))
        self._armed = self._countdown == 0  # se >0 mostriamo prima il countdown
        self._countdown_timer: Optional[QTimer] = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(Qt.CursorShape.CrossCursor)

        virtual = QGuiApplication.primaryScreen().virtualGeometry()
        self.setGeometry(virtual)

        if not self._armed:
            self._start_countdown()

    # ---- Countdown ---------------------------------------------------------

    def _start_countdown(self) -> None:
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._tick)
        self._countdown_timer.start()

    def _tick(self) -> None:
        self._countdown -= 1
        if self._countdown <= 0:
            if self._countdown_timer is not None:
                self._countdown_timer.stop()
                self._countdown_timer = None
            self._armed = True
        self.update()

    # ---- Painting ----------------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 90))

        if not self._armed:
            # Disegna il numero del countdown gigante al centro
            painter.setPen(QColor("#ffffff"))
            font = QFont("Segoe UI", 120)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, str(self._countdown))
            # Hint
            painter.setPen(QColor("#cbd5e1"))
            font2 = QFont("Segoe UI", 14)
            painter.setFont(font2)
            hint_rect = self.rect().adjusted(0, 220, 0, 0)
            painter.drawText(hint_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                             "Preparati a selezionare l'area…  (Esc per annullare)")
            return

        if self._origin is not None and self._current is not None:
            rect = QRect(self._origin, self._current).normalized()
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(rect, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            pen = QPen(QColor("#3da9fc"), 2)
            painter.setPen(pen)
            painter.drawRect(rect)
            # Etichetta dimensioni
            painter.setPen(QColor("#ffffff"))
            font = QFont("Segoe UI", 10)
            font.setBold(True)
            painter.setFont(font)
            size_text = f"{rect.width()} × {rect.height()}"
            label_rect = QRect(rect.right() - 90, rect.bottom() + 6, 90, 20)
            painter.fillRect(label_rect, QColor(0, 0, 0, 180))
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, size_text)
        else:
            # Hint quando l'utente è armato ma non ha ancora iniziato
            painter.setPen(QColor("#cbd5e1"))
            font = QFont("Segoe UI", 13)
            painter.setFont(font)
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                "\nTrascina per selezionare un'area  •  Esc per annullare",
            )

    # ---- Mouse / keyboard --------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self._armed:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.pos()
            self._current = event.pos()
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._armed:
            return
        if self._origin is not None:
            self._current = event.pos()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if not self._armed:
            return
        if event.button() != Qt.MouseButton.LeftButton or self._origin is None:
            return
        rect = QRect(self._origin, event.pos()).normalized()
        self._origin = None
        self._current = None
        self.hide()
        if rect.width() < 4 or rect.height() < 4:
            self._on_captured(None)
            self.close()
            return
        # Translate to virtual desktop coords
        global_rect = QRect(self.mapToGlobal(rect.topLeft()), rect.size())
        pix = self._grab_global_rect(global_rect)
        self._on_captured(pix)
        self.close()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            if self._countdown_timer is not None:
                self._countdown_timer.stop()
                self._countdown_timer = None
            self._on_captured(None)
            self.close()

    # ---- Helpers -----------------------------------------------------------

    @staticmethod
    def _grab_global_rect(rect: QRect) -> Optional[QPixmap]:
        screen = QGuiApplication.screenAt(rect.center()) or QGuiApplication.primaryScreen()
        if screen is None:
            return None
        screen_geo = screen.geometry()
        local = rect.translated(-screen_geo.topLeft())
        pix = screen.grabWindow(
            0, local.x(), local.y(), local.width(), local.height()
        )
        return pix if not pix.isNull() else None


def start_capture(
    on_captured: Callable[[Optional[QPixmap]], None],
    *,
    delay_sec: int = 0,
) -> CaptureOverlay:
    overlay = CaptureOverlay(on_captured, delay_sec=delay_sec)
    overlay.showFullScreen()
    overlay.raise_()
    overlay.activateWindow()
    return overlay


def capture_fullscreen() -> Optional[QPixmap]:
    """Cattura immediatamente lo schermo intero (schermo primario)."""
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        return None
    pix = screen.grabWindow(0)
    return pix if not pix.isNull() else None
