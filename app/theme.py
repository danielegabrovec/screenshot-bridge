"""Theme manager: DARK / LIGHT palettes + global QSS + icon helper.

Architettura
------------
* `Theme` è un dataclass frozen con ~30 token semantici (sfondi, testo,
  accenti, colori dei handle e del welcome overlay).
* `DARK_THEME` e `LIGHT_THEME` sono le due istanze concrete.
* `ThemeManager.instance()` è un singleton `QObject` con signal
  `theme_changed(Theme)` e persistenza su `QSettings("ui/theme")`.
* `qss_for(theme)` genera un foglio di stile Qt coerente per tutti i
  widget principali (toolbar, dock, menu, list, status bar, ecc.).
* `icon(name, color=None)` è un wrapper su `qtawesome.icon(...)` con
  fallback `QIcon()` vuoto se la libreria non è installata — in quel
  caso la toolbar resta solo-testo, senza crash.

Property dinamiche QSS
----------------------
Per stilare bottoni "primary" senza inline-stylesheet usiamo:
    btn.setProperty("role", "primary")
    _repolish(btn)  # forza Qt a rivalutare il selettore

Il QSS globale ha la regola `QPushButton[role="primary"] { ... }`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PyQt6.QtCore import QObject, QSettings, pyqtSignal
from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtWidgets import QApplication, QWidget

try:  # qtawesome è opzionale: senza, la toolbar resta solo testo
    import qtawesome as _qta  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - import fallback
    _qta = None


@dataclass(frozen=True)
class Theme:
    name: str
    is_dark: bool
    # superfici
    bg: str
    surface: str
    surface_alt: str
    surface_hover: str
    border: str
    border_strong: str
    # testo
    text: str
    text_muted: str
    text_disabled: str
    # accenti
    accent: str
    accent_hover: str
    accent_pressed: str
    on_accent: str
    danger: str
    success: str
    warning: str
    # canvas e overlay
    canvas_bg: str
    welcome_title: str
    welcome_body: str
    welcome_hint: str
    # handles
    handle_fill: str
    handle_border: str
    handle_endpoint_fill: str
    handle_endpoint_border: str
    rotate_fill: str
    selection_border: str
    edge_handle_fill: str
    # snap & tooltip
    snap_guide: str
    tooltip_bg: str
    tooltip_text: str
    # scrollbar
    scrollbar: str
    scrollbar_hover: str


DARK_THEME = Theme(
    name="dark",
    is_dark=True,
    bg="#1e1f22",
    surface="#2b2d31",
    surface_alt="#232428",
    surface_hover="#35373c",
    border="#3a3d44",
    border_strong="#4b4f57",
    text="#e6e6e6",
    text_muted="#a0a3a8",
    text_disabled="#6b6e74",
    accent="#3b82f6",
    accent_hover="#2563eb",
    accent_pressed="#1d4ed8",
    on_accent="#ffffff",
    danger="#ef4444",
    success="#22c55e",
    warning="#f59e0b",
    canvas_bg="#2b2b2b",
    welcome_title="#e2e8f0",
    welcome_body="#cbd5e1",
    welcome_hint="#94a3b8",
    handle_fill="#ffffff",
    handle_border="#3b82f6",
    handle_endpoint_fill="#fef3c7",
    handle_endpoint_border="#d97706",
    rotate_fill="#dbeafe",
    selection_border="#3b82f6",
    edge_handle_fill="#e0f2fe",
    snap_guide="#06b6d4",
    tooltip_bg="#0f172a",
    tooltip_text="#e6e6e6",
    scrollbar="#4b4f57",
    scrollbar_hover="#6b7280",
)


LIGHT_THEME = Theme(
    name="light",
    is_dark=False,
    bg="#f8fafc",
    surface="#ffffff",
    surface_alt="#f1f5f9",
    surface_hover="#e2e8f0",
    border="#cbd5e1",
    border_strong="#94a3b8",
    text="#0f172a",
    text_muted="#475569",
    text_disabled="#94a3b8",
    accent="#2563eb",
    accent_hover="#1d4ed8",
    accent_pressed="#1e40af",
    on_accent="#ffffff",
    danger="#dc2626",
    success="#16a34a",
    warning="#d97706",
    canvas_bg="#e2e8f0",
    welcome_title="#0f172a",
    welcome_body="#334155",
    welcome_hint="#64748b",
    handle_fill="#ffffff",
    handle_border="#2563eb",
    handle_endpoint_fill="#fef3c7",
    handle_endpoint_border="#b45309",
    rotate_fill="#dbeafe",
    selection_border="#2563eb",
    edge_handle_fill="#bae6fd",
    snap_guide="#0891b2",
    tooltip_bg="#1e293b",
    tooltip_text="#f8fafc",
    scrollbar="#cbd5e1",
    scrollbar_hover="#94a3b8",
)


_THEMES = {DARK_THEME.name: DARK_THEME, LIGHT_THEME.name: LIGHT_THEME}


def qss_for(t: Theme) -> str:
    """Foglio di stile globale coerente con il theme."""
    return f"""
    /* ---- Base ---- */
    QMainWindow, QDialog, QWidget {{
        background-color: {t.bg};
        color: {t.text};
        font-family: "Segoe UI", "Inter", "Helvetica Neue", system-ui;
        font-size: 9.5pt;
    }}
    QFrame#sbCard {{
        background: {t.surface};
        border: 1px solid {t.border};
        border-radius: 8px;
    }}

    /* ---- Toolbar ---- */
    QToolBar {{
        background: {t.surface};
        border: none;
        border-bottom: 1px solid {t.border};
        padding: 4px 6px;
        spacing: 4px;
    }}
    QToolBar::separator {{
        background: {t.border};
        width: 1px;
        margin: 4px 6px;
    }}
    QToolButton {{
        background: transparent;
        color: {t.text};
        border: 1px solid transparent;
        border-radius: 6px;
        padding: 5px 9px;
    }}
    QToolButton:hover {{
        background: {t.surface_hover};
        border-color: {t.border};
    }}
    QToolButton:checked {{
        background: {t.accent};
        color: {t.on_accent};
        border-color: {t.accent_hover};
    }}
    QToolButton:pressed {{ background: {t.accent_pressed}; color: {t.on_accent}; }}
    QToolButton:disabled {{ color: {t.text_disabled}; }}

    /* ---- Push button ---- */
    QPushButton {{
        background: {t.surface_alt};
        color: {t.text};
        border: 1px solid {t.border};
        border-radius: 6px;
        padding: 5px 12px;
    }}
    QPushButton:hover {{ background: {t.surface_hover}; }}
    QPushButton:disabled {{ color: {t.text_disabled}; }}
    QPushButton[role="primary"] {{
        background: {t.accent};
        color: {t.on_accent};
        border: 1px solid {t.accent_hover};
        font-weight: 600;
    }}
    QPushButton[role="primary"]:hover {{ background: {t.accent_hover}; }}
    QPushButton[role="primary"]:pressed {{ background: {t.accent_pressed}; }}
    QPushButton[role="danger"] {{
        background: {t.danger}; color: {t.on_accent};
        border: 1px solid {t.danger};
    }}

    /* ---- Section label in toolbar ---- */
    QLabel[cls="section"] {{
        color: {t.text_muted};
        font-size: 8.5pt;
        font-weight: 600;
        padding-left: 6px;
        padding-right: 2px;
    }}
    QLabel[cls="statusSlot"] {{
        color: {t.text_muted};
        font-size: 9pt;
        padding: 0px 8px;
    }}
    QLabel[cls="statusSlotStrong"] {{
        color: {t.text};
        font-size: 9pt;
        font-weight: 600;
        padding: 0px 8px;
    }}

    /* ---- Inputs ---- */
    QLineEdit, QSpinBox, QPlainTextEdit, QTextEdit {{
        background: {t.surface};
        color: {t.text};
        border: 1px solid {t.border};
        border-radius: 6px;
        padding: 4px 8px;
        selection-background-color: {t.accent};
        selection-color: {t.on_accent};
    }}
    QLineEdit:focus, QSpinBox:focus, QPlainTextEdit:focus, QTextEdit:focus {{
        border-color: {t.accent};
    }}
    QSpinBox::up-button, QSpinBox::down-button {{
        width: 16px;
        background: transparent;
        border: none;
    }}

    /* ---- Menu bar / menu ---- */
    QMenuBar {{
        background: {t.surface};
        color: {t.text};
        border-bottom: 1px solid {t.border};
    }}
    QMenuBar::item {{
        padding: 4px 10px;
        background: transparent;
    }}
    QMenuBar::item:selected {{
        background: {t.surface_hover};
    }}
    QMenu {{
        background: {t.surface};
        color: {t.text};
        border: 1px solid {t.border};
        padding: 4px;
    }}
    QMenu::item {{
        padding: 5px 22px 5px 22px;
        border-radius: 4px;
    }}
    QMenu::item:selected {{
        background: {t.accent};
        color: {t.on_accent};
    }}
    QMenu::separator {{
        height: 1px;
        background: {t.border};
        margin: 4px 8px;
    }}

    /* ---- Status bar ---- */
    QStatusBar {{
        background: {t.surface};
        color: {t.text_muted};
        border-top: 1px solid {t.border};
    }}
    QStatusBar::item {{ border: none; }}

    /* ---- Dock widget ---- */
    QDockWidget {{
        color: {t.text};
        titlebar-close-icon: none;
        titlebar-normal-icon: none;
    }}
    QDockWidget::title {{
        background: {t.surface_alt};
        color: {t.text_muted};
        padding: 6px 10px;
        border-bottom: 1px solid {t.border};
        font-weight: 600;
    }}

    /* ---- List widgets ---- */
    QListWidget, QTreeWidget {{
        background: {t.surface};
        color: {t.text};
        border: 1px solid {t.border};
        border-radius: 6px;
        outline: 0;
        padding: 2px;
    }}
    QListWidget::item {{
        padding: 4px;
        border-radius: 4px;
    }}
    QListWidget::item:hover {{
        background: {t.surface_hover};
    }}
    QListWidget::item:selected {{
        background: {t.accent};
        color: {t.on_accent};
    }}

    /* ---- Tab widget ---- */
    QTabWidget::pane {{
        border: 1px solid {t.border};
        border-radius: 6px;
        top: -1px;
        background: {t.surface};
    }}
    QTabBar::tab {{
        background: transparent;
        color: {t.text_muted};
        padding: 6px 12px;
        border: 1px solid transparent;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 2px;
    }}
    QTabBar::tab:hover {{
        color: {t.text};
    }}
    QTabBar::tab:selected {{
        background: {t.surface};
        color: {t.text};
        border: 1px solid {t.border};
        border-bottom: 1px solid {t.surface};
        font-weight: 600;
    }}

    /* ---- Scrollbars ---- */
    QScrollBar:vertical {{
        background: transparent;
        width: 12px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {t.scrollbar};
        min-height: 24px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {t.scrollbar_hover}; }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 12px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal {{
        background: {t.scrollbar};
        min-width: 24px;
        border-radius: 5px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {t.scrollbar_hover}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

    /* ---- Tooltip ---- */
    QToolTip {{
        background: {t.tooltip_bg};
        color: {t.tooltip_text};
        border: 1px solid {t.border_strong};
        border-radius: 4px;
        padding: 4px 8px;
    }}

    /* ---- Splitter ---- */
    QSplitter::handle {{
        background: {t.border};
    }}
    QSplitter::handle:horizontal {{ width: 1px; }}
    QSplitter::handle:vertical {{ height: 1px; }}

    /* ---- Group box ---- */
    QGroupBox {{
        border: 1px solid {t.border};
        border-radius: 6px;
        margin-top: 14px;
        padding: 6px;
        color: {t.text_muted};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 6px;
    }}

    /* ---- Checkbox / radio ---- */
    QCheckBox, QRadioButton {{ color: {t.text}; spacing: 6px; }}
    """


class ThemeManager(QObject):
    """Singleton: gestisce il tema corrente e notifica i listener.

    Uso tipico:
        ThemeManager.instance().theme_changed.connect(self._on_theme)
        theme = ThemeManager.instance().current_theme()
    """

    theme_changed = pyqtSignal(object)  # emette Theme

    _instance: Optional["ThemeManager"] = None

    @classmethod
    def instance(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = ThemeManager()
        return cls._instance

    def __init__(self) -> None:
        super().__init__()
        self._theme: Theme = DARK_THEME

    def current_theme(self) -> Theme:
        return self._theme

    def available(self) -> list[str]:
        return list(_THEMES.keys())

    def set_theme(self, name: str, *, persist: bool = True) -> None:
        if name not in _THEMES:
            return
        theme = _THEMES[name]
        if theme is self._theme:
            return
        self._theme = theme
        if persist:
            QSettings().setValue("ui/theme", name)
        self._apply_to_app(theme)
        self.theme_changed.emit(theme)

    def toggle(self) -> None:
        self.set_theme("light" if self._theme.is_dark else "dark")

    def apply_initial(self) -> None:
        """Da chiamare DOPO QApplication() e setOrganizationName()."""
        stored = QSettings().value("ui/theme", "dark", type=str)
        if stored not in _THEMES:
            stored = "dark"
        self._theme = _THEMES[stored]
        self._apply_to_app(self._theme)
        self.theme_changed.emit(self._theme)

    @staticmethod
    def _apply_to_app(theme: Theme) -> None:
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(qss_for(theme))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def icon(name: str, color: Optional[str] = None) -> QIcon:
    """Wrapper su qtawesome.icon con fallback se qta non è installato."""
    if _qta is None:
        return QIcon()
    if color is None:
        color = ThemeManager.instance().current_theme().text
    try:
        return _qta.icon(name, color=color)
    except Exception:
        return QIcon()


def icon_color_pair(name: str, normal: str, active: str) -> QIcon:
    """Icona con colori distinti per normal/active (per toggle stile)."""
    if _qta is None:
        return QIcon()
    try:
        return _qta.icon(name, color=normal, color_active=active)
    except Exception:
        return QIcon()


def repolish(widget: QWidget) -> None:
    """Forza Qt a rivalutare i selettori QSS dipendenti da proprietà dinamiche."""
    style = widget.style()
    if style is None:
        return
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def has_qtawesome() -> bool:
    return _qta is not None
