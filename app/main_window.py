"""Main application window: toolbar + canvas + task panel."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QFileSystemWatcher, Qt
from PyQt6.QtGui import (
    QAction,
    QActionGroup,
    QColor,
    QGuiApplication,
    QKeySequence,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QColorDialog,
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QToolBar,
    QToolButton,
    QWidget,
)

from . import companion_md, storage, stencils
from .canvas_editor import CanvasEditor
from .capture import capture_fullscreen, start_capture
from .settings_store import Settings
from .stencil_panel import StencilPanel
from .storage import Task
from .task_panel import TaskPanel
from .theme import Theme, ThemeManager, icon, repolish
from .tools import (
    ArrowTool,
    BraceTool,
    CalloutTool,
    CheckStampTool,
    CornerMarkerTool,
    CrossStampTool,
    CurveTool,
    DashedLineTool,
    DoubleArrowTool,
    EllipseTool,
    HighlightRectTool,
    HighlighterTool,
    LineTool,
    NumberStampTool,
    PenTool,
    RectTool,
    RedactTool,
    TextTool,
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Screenshot Bridge")
        self.resize(1320, 820)

        storage.ensure_dirs()
        self.settings = Settings()

        self.canvas = CanvasEditor(self)
        self.task_panel = TaskPanel(self)
        self.stencil_panel = StencilPanel(self)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(self.canvas)
        splitter.addWidget(self.task_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([960, 360])
        self.setCentralWidget(splitter)

        stencil_dock = QDockWidget("Stencil UI — trascina o clicca", self)
        stencil_dock.setObjectName("dock_stencils")  # serve a saveState()
        stencil_dock.setWidget(self.stencil_panel)
        stencil_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        # Niente DockWidgetClosable: l'utente non può chiuderlo accidentalmente
        # con la X (dovrà usare il pulsante "Pannello Stencil" in toolbar).
        stencil_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        stencil_dock.setMinimumWidth(260)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, stencil_dock)
        self.resizeDocks([stencil_dock], [290], Qt.Orientation.Horizontal)
        self._stencil_dock = stencil_dock
        self.stencil_panel.stencil_chosen.connect(self._on_stencil_chosen)
        self.canvas.stencil_dropped.connect(self._on_stencil_dropped)

        self.setStatusBar(QStatusBar(self))

        # Carica defaults persistiti
        try:
            self._current_color = QColor(self.settings.color())
            if not self._current_color.isValid():
                self._current_color = QColor("#ef4444")
        except Exception:
            self._current_color = QColor("#ef4444")
        self._current_thickness = max(1, int(self.settings.thickness()))
        self.canvas.set_color(self._current_color)
        self.canvas.set_thickness(self._current_thickness)

        # Tools instanziati una volta sola, riusati al cambio
        self._tools_map = {
            "select": None,
            "arrow": ArrowTool(),
            "double_arrow": DoubleArrowTool(),
            "line": LineTool(),
            "dashed_line": DashedLineTool(),
            "curve": CurveTool(),
            "rect": RectTool(),
            "ellipse": EllipseTool(),
            "text": TextTool(),
            "callout": CalloutTool(),
            "brace": BraceTool(),
            "corner_marker": CornerMarkerTool(),
            "pen": PenTool(),
            "highlighter": HighlighterTool(),
            "highlight_rect": HighlightRectTool(),
            "redact": RedactTool(),
            "number_stamp": NumberStampTool(),
            "check_stamp": CheckStampTool(),
            "cross_stamp": CrossStampTool(),
        }
        self._action_for_tool: dict[str, QAction] = {}
        self._themed_actions: list[tuple[QAction, str]] = []  # (action, qtawesome name)
        self._last_saved: Optional[Task] = None
        self._overlay = None

        self._build_menubar()
        self._build_toolbar()
        self._build_statusbar()
        self._wire_panel()
        self._setup_watcher()

        # Ripristina geometry + dock state
        geo = self.settings.window_geometry()
        if geo is not None:
            self.restoreGeometry(geo)
        state = self.settings.window_state()
        if state is not None:
            self.restoreState(state)

        # Applica/iscrivi tema
        ThemeManager.instance().theme_changed.connect(self._on_theme_changed)
        self._on_theme_changed(ThemeManager.instance().current_theme())

        # Attiva il tool salvato (default seleziona)
        last_tool = self.settings.last_tool()
        if last_tool in self._action_for_tool:
            self._action_for_tool[last_tool].setChecked(True)
            self._activate_tool_key(last_tool)
        else:
            self._action_for_tool["select"].setChecked(True)
            self._activate_tool_key("select")

    # ---- Menu --------------------------------------------------------------

    def _build_menubar(self) -> None:
        # IMPORTANTE: gli shortcut delle azioni "doppione" (Paste/Save/Open/Capture/F12)
        # vivono SOLO nelle QAction della toolbar. Definirli anche qui crea
        # un "Ambiguous shortcut overload" e Qt non scatta nessuna delle due.
        # Le voci di menu sotto sono solo "trigger" senza shortcut.
        mb = self.menuBar()
        m_file = mb.addMenu("&File")
        a_paste = QAction("Incolla dagli appunti", self)
        a_paste.triggered.connect(lambda _=False: self._paste_from_clipboard())
        m_file.addAction(a_paste)
        a_capture = QAction("Cattura area…", self)
        a_capture.triggered.connect(lambda _=False: self._start_capture())
        m_file.addAction(a_capture)
        a_fullscreen = QAction("Cattura schermo intero", self)
        a_fullscreen.triggered.connect(lambda _=False: self._capture_fullscreen())
        m_file.addAction(a_fullscreen)
        a_open = QAction("Apri file…", self)
        a_open.triggered.connect(lambda _=False: self._open_file_dialog())
        m_file.addAction(a_open)
        m_file.addSeparator()
        a_save = QAction("Salva in 'da-fare'…", self)
        a_save.triggered.connect(lambda _=False: self._save_current())
        m_file.addAction(a_save)
        m_file.addSeparator()
        a_quit = QAction("Esci", self)
        a_quit.setShortcut(QKeySequence("Ctrl+Q"))
        a_quit.triggered.connect(self.close)
        m_file.addAction(a_quit)

        m_view = mb.addMenu("&Visualizza")
        self._theme_group = QActionGroup(self)
        self._theme_group.setExclusive(True)
        self._act_theme_dark = QAction("Tema scuro", self)
        self._act_theme_dark.setCheckable(True)
        self._act_theme_dark.triggered.connect(lambda: ThemeManager.instance().set_theme("dark"))
        self._act_theme_light = QAction("Tema chiaro", self)
        self._act_theme_light.setCheckable(True)
        self._act_theme_light.triggered.connect(lambda: ThemeManager.instance().set_theme("light"))
        self._theme_group.addAction(self._act_theme_dark)
        self._theme_group.addAction(self._act_theme_light)
        m_view.addAction(self._act_theme_dark)
        m_view.addAction(self._act_theme_light)
        m_view.addSeparator()
        a_toggle_stencils = QAction("Pannello Stencil", self)
        a_toggle_stencils.setCheckable(True)
        a_toggle_stencils.setChecked(True)
        a_toggle_stencils.toggled.connect(lambda v: self._stencil_dock.setVisible(v))
        self._stencil_dock.visibilityChanged.connect(a_toggle_stencils.setChecked)
        m_view.addAction(a_toggle_stencils)

        m_set = mb.addMenu("&Impostazioni")
        a_countdown = QAction("Countdown cattura…", self)
        a_countdown.triggered.connect(self._configure_countdown)
        m_set.addAction(a_countdown)
        a_template = QAction("Template handoff Claude…", self)
        a_template.triggered.connect(self._configure_handoff_template)
        m_set.addAction(a_template)

        m_help = mb.addMenu("&Aiuto")
        a_shortcuts = QAction("Scorciatoie da tastiera", self)
        a_shortcuts.triggered.connect(self._show_shortcuts)
        m_help.addAction(a_shortcuts)
        a_about = QAction("Informazioni…", self)
        a_about.triggered.connect(self._show_about)
        m_help.addAction(a_about)

    # ---- Toolbar -----------------------------------------------------------

    def _build_toolbar(self) -> None:
        # --- Input toolbar (top row) ---
        tb_in = QToolBar("Acquisizione", self)
        tb_in.setObjectName("toolbar_input")
        tb_in.setMovable(False)
        tb_in.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb_in)

        tb_in.addWidget(self._section_label("Acquisisci"))

        paste_action = self._add_action(
            tb_in, "Incolla", "fa5s.paste",
            shortcut=QKeySequence.StandardKey.Paste,
            tooltip="Incolla l'immagine dagli appunti (es. dopo Win+Shift+S).\nScorciatoia: Ctrl+V",
            callback=self._paste_from_clipboard,
        )
        # Lo shortcut deve scattare anche se il focus è nel QGraphicsView del canvas
        # (che non è una "child window" Qt standard ma intercetta i tasti).
        # ApplicationShortcut bypassa la catena di focus.
        paste_action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self._add_action(
            tb_in, "Cattura area", "fa5s.crop-alt",
            shortcut=QKeySequence("Ctrl+Shift+S"),
            tooltip="Seleziona un'area dello schermo da catturare.\nScorciatoia: Ctrl+Shift+S",
            callback=self._start_capture,
        )
        self._add_action(
            tb_in, "Schermo intero", "fa5s.desktop",
            shortcut=QKeySequence("F12"),
            tooltip="Cattura subito tutto lo schermo (F12)",
            callback=self._capture_fullscreen,
        )
        self._add_action(
            tb_in, "Apri file…", "fa5s.folder-open",
            tooltip="Apri un PNG/JPG dal disco",
            callback=self._open_file_dialog,
        )

        tb_in.addSeparator()
        tb_in.addWidget(self._section_label("Salva e condividi"))

        self._add_action(
            tb_in, "Salva", "fa5s.save",
            shortcut=QKeySequence.StandardKey.Save,
            tooltip="Salva lo screenshot annotato in screenshots/da-fare/.\nScorciatoia: Ctrl+S",
            callback=self._save_current,
        )

        self._copy_path_btn = QPushButton("Copia path", self)
        self._copy_path_btn.setToolTip("Copia negli appunti il percorso del file dell'ultimo screenshot salvato")
        self._copy_path_btn.clicked.connect(self._copy_last_path)
        tb_in.addWidget(self._copy_path_btn)

        self._copy_claude_btn = QPushButton("Copia per Claude", self)
        self._copy_claude_btn.setToolTip(
            "Copia path + descrizione formattati per essere incollati nel terminale di Claude Code"
        )
        # Stile via QSS globale: proprietà dinamica role=primary
        self._copy_claude_btn.setProperty("role", "primary")
        repolish(self._copy_claude_btn)
        self._copy_claude_btn.clicked.connect(self._copy_last_for_claude)
        tb_in.addWidget(self._copy_claude_btn)

        tb_in.addSeparator()

        self._add_action(
            tb_in, "Pannello Stencil", "fa5s.th-large",
            checkable=True, checked=True,
            tooltip="Mostra/nascondi il pannello con i mockup UI (button, input, dropdown…)",
            callback=lambda v=True: self._stencil_dock.setVisible(v),
        )
        # collega anche il toggle al dock (auto-sync)
        self._stencil_dock.visibilityChanged.connect(
            lambda v: self._action_for_tool.get("__stencil_dock", QAction()).setChecked(v)
            if False else None
        )

        # --- Theme toggle in toolbar (icona sun/moon) ---
        tb_in.addSeparator()
        self._theme_btn = QToolButton(self)
        self._theme_btn.setToolTip("Cambia tema (chiaro / scuro)")
        self._theme_btn.clicked.connect(lambda: ThemeManager.instance().toggle())
        tb_in.addWidget(self._theme_btn)

        # --- Annotation toolbar (second row) ---
        self.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)
        tb_an = QToolBar("Annotazioni", self)
        tb_an.setObjectName("toolbar_annotate")
        tb_an.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb_an)

        tb_an.addWidget(self._section_label("Strumento"))

        self._tools_group = QActionGroup(self)
        self._tools_group.setExclusive(True)

        self._action_for_tool["select"] = self._add_tool_action(
            tb_an, "Sposta", "fa5s.hand-paper", "select", checked=True,
            tooltip=(
                "Sposta / seleziona gli elementi (nessun disegno).\n"
                "• Click su un elemento → maniglie di resize/rotate\n"
                "• Drag → sposta\n"
                "• Doppio click su un callout → modifica testo\n"
                "• Canc → elimina selezione"
            ),
        )
        self._action_for_tool["arrow"] = self._add_tool_action(
            tb_an, "Freccia", "fa5s.long-arrow-alt-right", "arrow",
            tooltip="Disegna una freccia. Shift = snap a 45°.",
        )
        self._action_for_tool["double_arrow"] = self._add_tool_action(
            tb_an, "Doppia freccia", "fa5s.arrows-alt-h", "double_arrow",
            tooltip="Freccia bidirezionale ↔ (scambi, misure, simmetrie). Shift = snap 45°.",
        )
        self._action_for_tool["line"] = self._add_tool_action(
            tb_an, "Linea", "fa5s.minus", "line",
            tooltip="Linea retta semplice. Shift = snap a 45°.",
        )
        self._action_for_tool["dashed_line"] = self._add_tool_action(
            tb_an, "Linea trattegg.", "fa5s.grip-lines", "dashed_line",
            tooltip="Linea tratteggiata. Utile per divisioni o assi virtuali.",
        )
        self._action_for_tool["curve"] = self._add_tool_action(
            tb_an, "Curva", "mdi.vector-curve", "curve",
            tooltip="Linea curva (Bezier). Trascina dritto = quasi retta, piega = curva.",
        )
        self._action_for_tool["rect"] = self._add_tool_action(
            tb_an, "Rettangolo", "far.square", "rect",
            tooltip="Disegna un rettangolo. Shift = quadrato. Alt = dal centro.",
        )
        self._action_for_tool["ellipse"] = self._add_tool_action(
            tb_an, "Cerchio", "far.circle", "ellipse",
            tooltip="Disegna un'ellisse. Shift = cerchio. Alt = dal centro.",
        )
        self._action_for_tool["text"] = self._add_tool_action(
            tb_an, "Testo", "fa5s.font", "text",
            tooltip="Inserisce una nota di testo. Click sul canvas per piazzarla.",
        )
        self._action_for_tool["callout"] = self._add_tool_action(
            tb_an, "Callout", "fa5s.comment-dots", "callout",
            tooltip="Banner di commento con punta verso un punto. Drag dalla punta al body.",
        )
        self._action_for_tool["brace"] = self._add_tool_action(
            tb_an, "Graffa", "mdi.code-braces", "brace",
            tooltip="Parentesi graffa { } per raggruppare un'area. Drag verticale o orizzontale.",
        )
        self._action_for_tool["corner_marker"] = self._add_tool_action(
            tb_an, "Angoli", "fa5s.expand", "corner_marker",
            tooltip="4 angoli a 'L' per evidenziare un'area SENZA coprirla.",
        )
        self._action_for_tool["pen"] = self._add_tool_action(
            tb_an, "Penna", "fa5s.pen", "pen",
            tooltip="Disegno a mano libera. Shift = linea retta.",
        )
        self._action_for_tool["highlighter"] = self._add_tool_action(
            tb_an, "Evidenziatore", "fa5s.highlighter", "highlighter",
            tooltip="Tratto semi-trasparente per evidenziare aree",
        )
        self._action_for_tool["highlight_rect"] = self._add_tool_action(
            tb_an, "Evid. rettangolo", "fa5s.marker", "highlight_rect",
            tooltip="Rettangolo evidenziatore semi-trasparente (Shift = quadrato)",
        )
        self._action_for_tool["redact"] = self._add_tool_action(
            tb_an, "Redact", "fa5s.user-secret", "redact",
            tooltip="Copre un'area con un rettangolo 'REDACTED' (privacy)",
        )
        self._action_for_tool["number_stamp"] = self._add_tool_action(
            tb_an, "Numero", "fa5s.list-ol", "number_stamp",
            tooltip="Stampa cerchi numerati 1, 2, 3… ad ogni click (Esc resetta)",
        )
        self._action_for_tool["check_stamp"] = self._add_tool_action(
            tb_an, "OK", "fa5s.check-circle", "check_stamp",
            tooltip="Stampa ✓ verde ad ogni click (va bene così, conferma).",
        )
        self._action_for_tool["cross_stamp"] = self._add_tool_action(
            tb_an, "NO", "fa5s.times-circle", "cross_stamp",
            tooltip="Stampa ✗ rossa ad ogni click (togli questo, sbagliato).",
        )

        tb_an.addSeparator()
        tb_an.addWidget(self._section_label("Stile"))

        self._color_btn = QPushButton("Colore", self)
        self._color_btn.setObjectName("colorBtn")
        self._color_btn.setToolTip("Colore di disegno per gli strumenti di annotazione")
        self._update_color_btn()
        self._color_btn.clicked.connect(self._pick_color)
        tb_an.addWidget(self._color_btn)

        tb_an.addWidget(QLabel(" Spessore: ", self))
        self._thickness_spin = QSpinBox(self)
        self._thickness_spin.setRange(1, 30)
        self._thickness_spin.setValue(self._current_thickness)
        self._thickness_spin.setToolTip("Spessore del tratto in pixel")
        self._thickness_spin.valueChanged.connect(self._on_thickness_changed)
        tb_an.addWidget(self._thickness_spin)

        tb_an.addSeparator()
        tb_an.addWidget(self._section_label("Modifica"))

        self._add_action(
            tb_an, "Annulla", "fa5s.undo",
            shortcut=QKeySequence.StandardKey.Undo,
            tooltip="Annulla l'ultima annotazione (Ctrl+Z)",
            callback=self.canvas.undo,
        )
        self._add_action(
            tb_an, "Ripristina", "fa5s.redo",
            shortcut=QKeySequence.StandardKey.Redo,
            tooltip="Ripristina l'ultima annotazione annullata (Ctrl+Y)",
            callback=self.canvas.redo,
        )
        self._add_action(
            tb_an, "Pulisci", "fa5s.trash-alt",
            tooltip="Rimuove TUTTE le annotazioni (frecce, stencil, testi…) "
                    "mantenendo lo screenshot di base. Chiede conferma.",
            callback=self._clear_annotations,
        )

    # ---- Status bar ricca --------------------------------------------------

    def _build_statusbar(self) -> None:
        bar = self.statusBar()
        # Slot permanenti (allineati a destra dopo i messaggi temporanei)
        self._sb_tool = QLabel("Strumento: —", self)
        self._sb_tool.setProperty("cls", "statusSlotStrong")
        self._sb_color = QLabel("● —", self)
        self._sb_color.setProperty("cls", "statusSlot")
        self._sb_thickness = QLabel("Spessore: —", self)
        self._sb_thickness.setProperty("cls", "statusSlot")
        self._sb_zoom = QLabel("Zoom: —", self)
        self._sb_zoom.setProperty("cls", "statusSlot")
        for w in (self._sb_tool, self._sb_color, self._sb_thickness, self._sb_zoom):
            bar.addPermanentWidget(w)
            repolish(w)
        self._refresh_status_slots()
        self.canvas.zoom_changed.connect(self._on_zoom_changed)

    def _refresh_status_slots(self) -> None:
        tool_key = self.settings.last_tool()
        labels = {
            "select": "Sposta", "arrow": "Freccia",
            "double_arrow": "Doppia freccia", "line": "Linea",
            "dashed_line": "Linea trattegg.", "curve": "Curva",
            "rect": "Rettangolo", "ellipse": "Cerchio", "text": "Testo",
            "callout": "Callout", "brace": "Graffa",
            "corner_marker": "Angoli", "pen": "Penna",
            "highlighter": "Evidenziatore", "highlight_rect": "Evid. rect",
            "redact": "Redact", "number_stamp": "Numero",
            "check_stamp": "OK ✓", "cross_stamp": "NO ✗",
        }
        self._sb_tool.setText(f"Strumento: {labels.get(tool_key, tool_key)}")
        self._sb_color.setText(f"● {self._current_color.name()}")
        self._sb_color.setStyleSheet(
            f"color: {self._current_color.name()}; padding: 0px 8px; font-weight: 600;"
        )
        self._sb_thickness.setText(f"Spessore: {self._current_thickness}px")
        self._sb_zoom.setText("Zoom: 100%")

    def _on_zoom_changed(self, m11: float) -> None:
        pct = int(round(m11 * 100))
        self._sb_zoom.setText(f"Zoom: {pct}%")

    # ---- Theme -------------------------------------------------------------

    def _on_theme_changed(self, theme: Theme) -> None:
        # Aggiorna icone delle action note
        for action, name in self._themed_actions:
            action.setIcon(icon(name, color=theme.text))
        # Icona toggle theme
        moon_sun = "fa5s.moon" if theme.is_dark else "fa5s.sun"
        self._theme_btn.setIcon(icon(moon_sun, color=theme.text))
        self._theme_btn.setText("Tema scuro" if not theme.is_dark else "Tema chiaro")
        # Radio menu
        self._act_theme_dark.setChecked(theme.is_dark)
        self._act_theme_light.setChecked(not theme.is_dark)
        # Color button
        self._update_color_btn()
        self._refresh_status_slots()

    # ---- Helpers di costruzione UI ----------------------------------------

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(f"  {text}: ", self)
        lbl.setProperty("cls", "section")
        repolish(lbl)
        return lbl

    def _add_action(
        self,
        toolbar: QToolBar,
        text: str,
        qta_name: str,
        *,
        shortcut: Optional[QKeySequence | QKeySequence.StandardKey] = None,
        tooltip: str = "",
        callback=None,
        checkable: bool = False,
        checked: bool = False,
    ) -> QAction:
        action = QAction(text, self)
        action.setIcon(icon(qta_name))
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tooltip:
            action.setToolTip(tooltip)
        if checkable:
            action.setCheckable(True)
            action.setChecked(checked)
        if callback is not None:
            if checkable:
                action.toggled.connect(callback)
            else:
                action.triggered.connect(lambda _=False, cb=callback: cb())
        toolbar.addAction(action)
        self._themed_actions.append((action, qta_name))
        return action

    def _add_tool_action(
        self,
        toolbar: QToolBar,
        label: str,
        qta_name: str,
        tool_key: str,
        *,
        checked: bool = False,
        tooltip: str = "",
    ) -> QAction:
        action = QAction(label, self)
        action.setIcon(icon(qta_name))
        action.setCheckable(True)
        action.setChecked(checked)
        if tooltip:
            action.setToolTip(tooltip)
        action.triggered.connect(lambda _checked, k=tool_key: self._activate_tool_key(k))
        self._tools_group.addAction(action)
        toolbar.addAction(action)
        self._themed_actions.append((action, qta_name))
        return action

    def _activate_tool_key(self, key: str) -> None:
        tool = self._tools_map.get(key)
        # Reset counter su NumberStamp ogni volta che lo attivi di nuovo
        if key == "number_stamp" and tool is not None:
            try:
                tool.reset()  # type: ignore[attr-defined]
            except Exception:
                pass
        self.canvas.set_tool(tool)
        self.settings.set_last_tool(key)
        self._refresh_status_slots()

    def _update_color_btn(self) -> None:
        c = self._current_color
        # Bordo dal tema + bg = colore scelto
        theme = ThemeManager.instance().current_theme()
        on_color = "#ffffff" if c.lightness() < 130 else "#0f172a"
        self._color_btn.setStyleSheet(
            f"QPushButton#colorBtn {{"
            f" background-color: {c.name()};"
            f" color: {on_color};"
            f" padding: 4px 12px;"
            f" border: 1px solid {theme.border_strong};"
            f" border-radius: 6px;"
            f"}}"
            f"QPushButton#colorBtn:hover {{ border: 1px solid {theme.accent}; }}"
        )

    # ---- Panel wiring ------------------------------------------------------

    def _wire_panel(self) -> None:
        self.task_panel.task_activated.connect(self._open_task)
        self.task_panel.mark_done_requested.connect(self._mark_done)
        self.task_panel.delete_requested.connect(self._delete_task)

    def _setup_watcher(self) -> None:
        self._watcher = QFileSystemWatcher(self)
        for d in (storage.PENDING_DIR, storage.DONE_DIR):
            self._watcher.addPath(str(d))
        self._watcher.directoryChanged.connect(lambda _p: self.task_panel.refresh())

    # ---- Actions: input ----------------------------------------------------

    def _paste_from_clipboard(self) -> None:
        """Cerca un'immagine negli appunti provando più strade in cascata.

        Su Windows il clipboard contiene immagini in formati eterogenei
        (CF_DIB, CF_BITMAP, image/png raw, file URL). Proviamo:
        1. `clipboard.image()`        → QImage diretta
        2. `clipboard.pixmap()`       → QPixmap (DIB → BMP)
        3. `mimeData().imageData()`   → QVariant convertito a QImage
        4. bytes raw nei format image/png, image/bmp, image/jpeg
        5. URL locali in `mimeData().urls()` (drag dal File Explorer)
        Se proprio non c'è nulla, mostro un dialog con i formati visti.
        """
        from PyQt6.QtGui import QImage, QPixmap
        clipboard = QGuiApplication.clipboard()
        md = clipboard.mimeData()
        # Feedback immediato: l'utente saprà che Ctrl+V è scattato.
        self.statusBar().showMessage("Lettura appunti…", 1500)

        # 1) QImage diretta
        img = clipboard.image()
        if not img.isNull():
            self.canvas.set_read_only(False)
            self.canvas.load_image(img)
            self.statusBar().showMessage(
                f"Immagine incollata ({img.width()}×{img.height()})", 3000)
            return

        # 2) QPixmap (alcuni formati Windows arrivano come bitmap, non image)
        pix = clipboard.pixmap()
        if not pix.isNull():
            self.canvas.set_read_only(False)
            self.canvas.load_pixmap(pix)
            self.statusBar().showMessage(
                f"Immagine incollata ({pix.width()}×{pix.height()})", 3000)
            return

        # 3) imageData() raw QVariant
        try:
            raw = md.imageData()
        except Exception:
            raw = None
        if raw is not None:
            try:
                img2 = QImage(raw)
                if not img2.isNull():
                    self.canvas.set_read_only(False)
                    self.canvas.load_image(img2)
                    self.statusBar().showMessage("Immagine incollata (raw)", 3000)
                    return
            except Exception:
                pass

        # 4) bytes raw in formati comuni
        for fmt in ("image/png", "image/bmp", "image/jpeg", "image/jpg",
                    "application/x-qt-image"):
            if md.hasFormat(fmt):
                data = bytes(md.data(fmt))
                img3 = QImage.fromData(data)
                if not img3.isNull():
                    self.canvas.set_read_only(False)
                    self.canvas.load_image(img3)
                    self.statusBar().showMessage(
                        f"Immagine incollata ({fmt.split('/')[-1].upper()})", 3000)
                    return

        # 5) URL locali (drag/paste da File Explorer)
        if md.hasUrls():
            for url in md.urls():
                if url.isLocalFile() and self.canvas.load_file(url.toLocalFile()):
                    self.canvas.set_read_only(False)
                    self.statusBar().showMessage(
                        f"Caricato: {url.toLocalFile()}", 3000)
                    return

        # Niente di utilizzabile: mostra cosa c'era nel clipboard per debug.
        fmts = ", ".join(md.formats()) or "(vuoto)"
        QMessageBox.information(
            self, "Incolla",
            "Nessuna immagine utilizzabile negli appunti.\n\n"
            f"Formati visti: {fmts}\n\n"
            "Suggerimento: usa Win+Shift+S, poi clicca sulla notifica di "
            "Windows in basso a destra prima di tornare qui (su Windows 11 "
            "alcuni snip vanno nel clipboard solo dopo quel click)."
        )

    def _start_capture(self) -> None:
        self.hide()
        delay = max(0, int(self.settings.capture_countdown()))

        def on_captured(pix: Optional[QPixmap]) -> None:
            self.show()
            self.raise_()
            self.activateWindow()
            if pix is None or pix.isNull():
                self.statusBar().showMessage("Cattura annullata", 2000)
                return
            self.canvas.set_read_only(False)
            self.canvas.load_pixmap(pix)
            self.statusBar().showMessage("Area catturata", 3000)

        # Small delay needed to actually hide on Windows before the overlay shows
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(180, lambda: self._launch_overlay(on_captured, delay))

    def _launch_overlay(self, on_captured, delay_sec: int) -> None:
        self._overlay = start_capture(on_captured, delay_sec=delay_sec)

    def _capture_fullscreen(self) -> None:
        self.hide()

        def grab() -> None:
            pix = capture_fullscreen()
            self.show()
            self.raise_()
            self.activateWindow()
            if pix is None or pix.isNull():
                self.statusBar().showMessage("Cattura fullscreen fallita", 3000)
                return
            self.canvas.set_read_only(False)
            self.canvas.load_pixmap(pix)
            self.statusBar().showMessage("Schermo intero catturato", 3000)

        from PyQt6.QtCore import QTimer
        QTimer.singleShot(220, grab)

    def _open_file_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Apri immagine", "", "Immagini (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            self.canvas.set_read_only(False)
            if not self.canvas.load_file(path):
                QMessageBox.warning(self, "Errore", f"Impossibile caricare: {path}")

    # ---- Actions: style ----------------------------------------------------

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(self._current_color, self, "Scegli colore")
        if color.isValid():
            self._current_color = color
            self.canvas.set_color(color)
            self._update_color_btn()
            self.settings.set_color(color.name())
            self._refresh_status_slots()

    def _on_thickness_changed(self, value: int) -> None:
        self._current_thickness = value
        self.canvas.set_thickness(value)
        self.settings.set_thickness(value)
        self._refresh_status_slots()

    # ---- Settings dialogs --------------------------------------------------

    def _configure_countdown(self) -> None:
        cur = int(self.settings.capture_countdown())
        val, ok = QInputDialog.getInt(
            self, "Countdown cattura",
            "Secondi di attesa prima della cattura (0 = nessun ritardo):",
            cur, 0, 10, 1,
        )
        if ok:
            self.settings.set_capture_countdown(int(val))
            self.statusBar().showMessage(f"Countdown impostato a {val}s", 3000)

    def _configure_handoff_template(self) -> None:
        cur = self.settings.handoff_template()
        text, ok = QInputDialog.getMultiLineText(
            self,
            "Template handoff Claude",
            "Placeholder disponibili: {png}, {description}, {md}",
            cur,
        )
        if ok and text.strip():
            self.settings.set_handoff_template(text.strip())
            self.statusBar().showMessage("Template handoff aggiornato", 3000)

    def _show_shortcuts(self) -> None:
        msg = (
            "<b>Scorciatoie principali</b><br><br>"
            "<table cellpadding='4'>"
            "<tr><td><code>Ctrl+V</code></td><td>Incolla dagli appunti</td></tr>"
            "<tr><td><code>Ctrl+Shift+S</code></td><td>Cattura area</td></tr>"
            "<tr><td><code>F12</code></td><td>Cattura schermo intero</td></tr>"
            "<tr><td><code>Ctrl+S</code></td><td>Salva in da-fare</td></tr>"
            "<tr><td><code>Ctrl+Z / Ctrl+Y</code></td><td>Annulla / Ripristina</td></tr>"
            "<tr><td><code>Canc</code></td><td>Elimina selezione</td></tr>"
            "<tr><td><code>+ / −</code></td><td>Scala item selezionato</td></tr>"
            "<tr><td><code>[ / ]</code></td><td>Ruota di ±5° (Shift = 15°)</td></tr>"
            "<tr><td><code>R</code></td><td>Reset rotazione/scala</td></tr>"
            "<tr><td><code>Shift</code> (drag)</td><td>Vincolo: quadrato, cerchio, 45°</td></tr>"
            "<tr><td><code>Alt</code> (drag)</td><td>Disegna dal centro</td></tr>"
            "<tr><td><code>Ctrl+ruota mouse</code></td><td>Zoom canvas</td></tr>"
            "</table>"
        )
        QMessageBox.information(self, "Scorciatoie", msg)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "Screenshot Bridge",
            "<b>Screenshot Bridge</b><br>"
            "Cattura, annota e passa screenshot a Claude Code.<br><br>"
            "Versione 0.2 — temi DARK/LIGHT, stencil, redact, companion .md."
        )

    # ---- Actions: save / hand-off ------------------------------------------

    def _save_current(self) -> None:
        if not self.canvas.has_image():
            QMessageBox.information(self, "Nulla da salvare", "Carica prima uno screenshot.")
            return
        description, ok = QInputDialog.getText(
            self,
            "Salva task",
            "Descrizione breve (cosa deve fare Claude?):",
        )
        if not ok:
            return
        description = description.strip() or "screenshot"
        png_bytes = self.canvas.export_png_bytes()
        task = storage.save_task(png_bytes, description)
        # Companion .md con descrizioni callout
        try:
            companion_md.write_companion(
                task.png_path,
                self.canvas._scene,  # noqa: SLF001 — accesso interno controllato
                self.canvas.annotated_items(),
                description,
            )
        except Exception:
            pass
        self._last_saved = task
        self.task_panel.refresh()
        self.statusBar().showMessage(f"Salvato: {task.png_path.name}", 5000)

    def _copy_last_path(self) -> None:
        task = self._resolve_handoff_task()
        if task is None:
            return
        text = str(task.png_path)
        QGuiApplication.clipboard().setText(text)
        self._flash_copy_btn(self._copy_path_btn, "Copia path")
        self._toast_copied(text)

    def _copy_last_for_claude(self) -> None:
        task = self._resolve_handoff_task()
        if task is None:
            return
        template = self.settings.handoff_template()
        try:
            text = storage.claude_handoff_text(task, template)
        except (KeyError, ValueError, IndexError) as exc:
            # Template malformato (placeholder sconosciuto, graffa orfana).
            QMessageBox.warning(
                self, "Template non valido",
                f"Il template handoff contiene un errore:\n  {exc}\n\n"
                "Vai in Impostazioni › Template handoff Claude per correggerlo.\n"
                "Placeholder validi: {png}, {description}, {md}",
            )
            return
        QGuiApplication.clipboard().setText(text)
        self._flash_copy_btn(self._copy_claude_btn, "Copia per Claude")
        self._toast_copied(text)

    def _toast_copied(self, text: str) -> None:
        """Status bar message col preview di cosa è stato copiato."""
        preview = text if len(text) <= 80 else text[:77] + "…"
        self.statusBar().showMessage(f"✓ Copiato negli appunti: {preview}", 5000)

    def _flash_copy_btn(self, btn: QPushButton, original_label: str) -> None:
        """Feedback visivo: il bottone diventa 'Copiato!' verde per 1.5s."""
        btn.setText("✓ Copiato!")
        original_role = btn.property("role")
        btn.setProperty("role", "success")
        # success role non esiste nel QSS → forziamo inline come fallback
        theme = ThemeManager.instance().current_theme()
        btn.setStyleSheet(
            f"QPushButton {{ background:{theme.success}; color:white; "
            f"border:1px solid {theme.success}; border-radius:6px; "
            f"padding:5px 12px; font-weight:600; }}"
        )
        from PyQt6.QtCore import QTimer

        def restore() -> None:
            btn.setText(original_label)
            btn.setStyleSheet("")
            if original_role is not None:
                btn.setProperty("role", original_role)
            repolish(btn)

        QTimer.singleShot(1500, restore)

    def _resolve_handoff_task(self) -> Optional[Task]:
        if self._last_saved is not None and self._last_saved.png_path.exists():
            return self._last_saved
        pending = storage.list_pending()
        if pending:
            return pending[0]
        QMessageBox.information(
            self,
            "Nessun task",
            "Salva prima uno screenshot con Ctrl+S.",
        )
        return None

    # ---- Actions: panel ----------------------------------------------------

    def _open_task(self, task: Task) -> None:
        if not task.png_path.exists():
            return
        self.canvas.set_read_only(task.status == "done")
        self.canvas.load_file(str(task.png_path))
        if task.status in ("pending", "in_progress"):
            self._last_saved = task
        self.statusBar().showMessage(
            f"Aperto ({task.status}): {task.png_path.name}", 4000
        )

    def _mark_done(self, task: Task) -> None:
        done = storage.mark_done(task.png_path)
        if self._last_saved and Path(self._last_saved.png_path).name == done.png_path.name:
            self._last_saved = done
        self.task_panel.refresh()
        self.statusBar().showMessage(f"Spostato in completati: {done.png_path.name}", 4000)

    def _on_stencil_chosen(self, key: str) -> None:
        self._insert_stencil(key, scene_pos=None)

    def _on_stencil_dropped(self, key: str, scene_pos) -> None:
        self._insert_stencil(key, scene_pos=scene_pos)

    def _insert_stencil(self, key: str, scene_pos) -> None:
        definition = stencils.by_key(key)
        if definition is None:
            return
        if not self.canvas.has_image():
            blank = QPixmap(1280, 720)
            blank.fill(Qt.GlobalColor.white)
            self.canvas.load_pixmap(blank)
            self.canvas.set_read_only(False)
        item = definition.factory()
        self.canvas.add_stencil(item, scene_pos=scene_pos)
        where = "alla posizione del drop" if scene_pos is not None else "al centro"
        self.statusBar().showMessage(
            f"Aggiunto stencil: {definition.label} ({where})", 3000
        )

    def _clear_annotations(self) -> None:
        """Rimuove tutte le annotazioni mantenendo lo screenshot di base."""
        if not self.canvas.has_image():
            self.statusBar().showMessage("Nessuna immagine: niente da pulire.", 2000)
            return
        count = len(self.canvas.annotated_items())
        if count == 0:
            self.statusBar().showMessage("Niente da pulire: nessuna annotazione.", 2000)
            return
        confirm = QMessageBox.question(
            self,
            "Pulisci annotazioni",
            f"Rimuovere tutte le {count} annotazioni mantenendo lo screenshot?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.canvas.clear_annotations()
        self.statusBar().showMessage(f"{count} annotazioni rimosse.", 3000)

    def _delete_task(self, task: Task) -> None:
        confirm = QMessageBox.question(
            self,
            "Conferma eliminazione",
            f"Eliminare definitivamente '{task.description}'?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        storage.delete_task(task.png_path)
        self.task_panel.refresh()
        self.statusBar().showMessage("Task eliminato", 3000)

    # ---- Close: persistenza ------------------------------------------------

    def closeEvent(self, event) -> None:  # type: ignore[override]
        try:
            self.settings.set_window_geometry(self.saveGeometry())
            self.settings.set_window_state(self.saveState())
            self.settings.sync()
        except Exception:
            pass
        super().closeEvent(event)
