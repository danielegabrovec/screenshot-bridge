# Roadmap — Screenshot Bridge

Stato del progetto e cosa rimane da fare. Aggiornato il **2026-05-16**.

## ✅ Fatto nella sessione 2026-05-16

### Salto grafico
- `app/theme.py` con dataclass `Theme` (30 token), istanze `DARK_THEME` e `LIGHT_THEME`
- `ThemeManager` singleton con signal `theme_changed`, persistenza su QSettings
- `qss_for(theme)` foglio di stile globale completo (toolbar, dock, menu, list, tab, scrollbar, tooltip…)
- Toggle tema da toolbar (icona ☀/☾) e da menu *Visualizza › Tema*
- Icone `qtawesome` su tutta la toolbar e i menu, ricolorate al cambio tema
- Status bar ricca: 4 slot permanenti (tool, colore, spessore, zoom %)
- HiDPI: `setHighDpiScaleFactorRoundingPolicy(PassThrough)` in `main.py`
- `_DescriptionCallout` resta nei colori storici (testo nero su bianco) perché finisce nel PNG esportato e deve essere leggibile indipendentemente dal tema dell'app

### Fondamenta UX
- `app/settings_store.py` wrapper `Settings` su `QSettings` con formato INI in `%LOCALAPPDATA%\ScreenshotBridge\settings.ini`
- Persistenza di: geometry finestra, dock state, ultimo tool, colore, spessore, tema, countdown cattura, template handoff
- Ripristino su `__init__`, salvataggio su `closeEvent`

### Tool e stencil potenziati
- `BaseTool` estesa con `modifiers: Qt.KeyboardModifier` (firma retro-compatibile)
- Helper statici `constrain_rect(origin, current, modifiers)` (Shift/Alt) e `constrain_line(...)` (Shift snap 45°)
- `RectTool`, `EllipseTool`, `ArrowTool`, `PenTool` ora rispettano i modificatori
- Ogni tool espone `cursor()` per cursore custom sul viewport
- 3 nuovi tool: `HighlightRectTool`, `RedactTool` (rettangolo nero "REDACTED"), `NumberStampTool` (cerchio numerato)
- 12 nuovi stencil in `app/stencils.py`: `data_table`, `breadcrumb`, `progress_bar`, `slider`, `badge`, `tooltip`, `chart_bar`, `chart_line`, `calendar_picker`, `stepper`, `file_upload`, `toast_notification`
- `edit_handles.py` ora legge la palette da `ThemeManager` e ridipinge i handle al cambio tema

### Claude integration + Capture+
- `app/companion_md.py`: scrive `<file>.md` accanto al PNG con descrizioni callout e coordinate normalizzate
- `app/storage.py`: status `in_progress`, `mark_in_progress()`, gestione del file `.md` in move/delete
- `app/cli.py` + `sb.bat`: comandi `next | peek | pending | done | md` per Claude Code
- `claude_handoff_text(task, template)` con placeholder `{png}`, `{description}`, `{md}`
- `capture.py`: countdown 3-2-1 configurabile, badge dimensioni live, `capture_fullscreen()`
- Tasto `F12` per cattura schermo intero, menu *Impostazioni › Countdown cattura*

---

## 📋 Prossime sessioni (ordinate per impatto/effort)

### Priorità ALTA

1. **QUndoStack vero** (fase 2 originale, rimandata)
   - Sostituire le liste `_undo_stack` / `_redo_stack` in `canvas_editor.py` con `QUndoStack`
   - Comandi: `AddItemCommand`, `RemoveItemCommand`, `MoveItemCommand` (con `mergeWith` per drag continui), `TransformItemCommand`, `ChangeDescriptionCommand`, `ChangeZOrderCommand`, `DuplicateItemCommand`
   - Connettere `undo_stack.cleanChanged` al titolo finestra per badge "modificato"
   - **Beneficio**: l'utente può annullare anche rotazioni, descrizioni, z-order, eliminazioni multiple

2. **System Tray Icon**
   - `QSystemTrayIcon` con menu: Mostra/Cattura area/Cattura fullscreen/Incolla/Esci
   - Click sinistro = toggle finestra, doppio click = cattura area (configurabile)
   - Conteggio task in sospeso nel menu
   - `closeEvent` minimizza a tray invece di chiudere (configurabile)
   - **Beneficio**: cattura sempre disponibile senza tenere la finestra in vista

3. **Snap intelligente + smart guides** (fase 3 originale)
   - `app/snap.py` con `compute_snap(moving_rect, candidates, threshold=6.0)` → `SnapResult(dx, dy, guides)`
   - Quando si trascina un item: confronta `{left, hcenter, right}` con tutti gli altri item
   - Disegna linee guida ciano `#06b6d4` durante il drag
   - Toggle `G` + voce *Visualizza › Snap intelligente*
   - **Beneficio**: allineare gli stencil diventa banale, niente più "occhio"

### Priorità MEDIA

4. **Edge handles NSEW** (resize non uniforme)
   - 4 handle aggiuntivi in `EditHandleManager._build_generic_handles`
   - `QTransform.scale(sx, sy)` con pivot = lato opposto
   - Disabilitati quando l'item è ruotato (vincolo matematico)
   - **Beneficio**: stretchare un rettangolo solo in larghezza/altezza

5. **Preview hover grande sugli stencil** + thumbnail cache
   - `_StencilPreviewPopup(QFrame)` con `QGraphicsView` 400×220
   - `eventFilter` su `_DraggableStencilList`: timer 300ms su hover
   - Cache `_thumb_cache: dict[str, QPixmap]`, invalidata al `theme_changed`
   - **Beneficio**: i dettagli degli stencil sono leggibili senza dropparlo prima

6. **Shortcut globali OS** (cattura ad app minimizzata)
   - Opzione A: dipendenza `keyboard` o `pynput` (rischio admin su Windows)
   - Opzione B: solo via tray icon (più sicuro, già pianificato)

### Priorità BASSA / nice-to-have

7. **Cattura finestra attiva** (`Ctrl+Alt+S`)
   - `app/window_enum.py` con `pywin32` opzionale: enum top-level + active window rect
   - Fallback no-op senza pywin32 (menu greyed)

8. **Zoom-pixel loupe** durante cattura area
   - `_ZoomLoupe(QLabel)` 120×120 che renderizza ritaglio 30×30 zoom 4×
   - Segue il cursore durante il drag

9. **Snap-to-window edges** durante cattura
   - Enumera rect delle finestre top-level, snap del rect di selezione quando vicino

10. **Watch mode CLI** (`sb watch`)
    - Polling/observe di `da-fare/` con `watchdog` o `QFileSystemWatcher`
    - Stampa il path appena un nuovo task viene salvato
    - Permette pipe verso Claude in continuo

11. **Drag-reorder + multi-select nei task panel**
    - Bulk mark-as-done / delete
    - Icona badge per stato `in_progress` (pallino arancione)

12. **Export multi-formato**
    - SVG (vector dello scene)
    - PDF (per allegati formali)
    - Templates salvabili (`canvas state` → JSON serializzato)

13. **HiDPI loupe avanzato**: render del canvas a risoluzione doppia in export per stampa

14. **i18n**: estrarre tutte le stringhe italiane in un file `.qm` traducibile (EN/FR/ES)

---

## Note di refactor consigliati

- **`canvas_editor.py`** è cresciuto a ~600 righe: valuta di estrarre il context-menu sugli item in `app/item_context_menu.py` quando si aggiunge la QUndoStack.
- **`main_window.py`** è ~580 righe: ok per ora; se cresce ulteriormente con tray + shortcut globali, estrarre la costruzione toolbar/menu in `app/ui_builders.py`.
- **`_shallow_clone`** in `canvas_editor.py` non clona gli stencil compositi: serve un `clone()` polimorfico sui factory. Si può rimandare finché non si introduce QUndoStack che richiede clone-as-redo.

## Convenzioni mantenute (non rompere)

- `DockWidgetClosable` mai abilitato (utente lo chiude per sbaglio)
- `painter.save()/restore()` attorno al disegno di background prima di delegare a `super().paint()` (bug testo bianco su bianco già risolto)
- `ItemIgnoresTransformations` su decorazioni (handle, callout, frame)
- `_flash_items` set come "exclude from export": qualsiasi item registrato lì viene nascosto in `export_png_bytes`
- Scaling proporzionale degli stencil: `target_w = max(160, scene_w * 0.14)`, clamp 1–4×
- Palette wireframe di `stencils.py` (OUTLINE/ACCENT/MUTED) **non** dipende dal tema host: gli stencil rappresentano un'estetica wireframe coerente, indipendente dal dark/light dell'app
