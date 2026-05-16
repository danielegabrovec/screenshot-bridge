# Roadmap — Screenshot Bridge

Stato del progetto e cosa rimane da fare. Aggiornato il **2026-05-16** (sessione completa).

---

## ✅ Fatto fino a v0.3 (2026-05-16)

### Estetica e UX di base
- `app/theme.py` con dataclass `Theme` (30 token), DARK/LIGHT, `ThemeManager` singleton con signal `theme_changed`, persistenza QSettings
- `qss_for(theme)` foglio di stile globale (toolbar, dock, menu, list, tab, scrollbar, tooltip…)
- Toggle ☀/☾ in toolbar + menu *Visualizza › Tema*
- Icone `qtawesome` ricolorate al cambio tema; più volte revisionate per intuitività (mdi.crop-free per corner marker, mdi.tooltip-edit per callout, mdi.hand-paper per Sposta, mdi.broom per Pulisci, ecc.)
- Status bar ricca: 4 slot permanenti (tool, colore, spessore, zoom %)
- HiDPI in `main.py`

### Persistenza
- `app/settings_store.py`: QSettings INI in `%LOCALAPPDATA%\ScreenshotBridge\settings.ini`
- Persistite: geometry finestra, dock state, last_tool, color, thickness, theme, capture countdown, handoff template, snap, tray

### Strumenti di annotazione (22 totali)
- **Cursore/Movimento**: Seleziona (puntatore, rubber-band), Sposta (manina, solo drag)
- **Linee**: Linea retta, Linea tratteggiata, Curva (Bezier con control point modificabile), Freccia, Doppia freccia ↔
- **Forme**: Rettangolo, Cerchio, Testo (con dialog word-wrap)
- **Direttive**: Callout (con punta), Graffa `{ }`, Angoli (4 L-corner marks), Tabella editabile (3×3 default, righe/colonne add/remove)
- **Disegno libero**: Penna, Evidenziatore, Evidenziatore rettangolare
- **Privacy**: Nascondi (Redact con etichetta "REDACTED")
- **Stamp**: Numero (1, 2, 3 incrementale), OK ✓ verde, NO ✗ rosso
- Modificatori: `Shift` (vincoli quadrato/cerchio/45°), `Alt` (centro), `Ctrl+rotella` (zoom)
- Cursori custom per tool attivo
- **Click su elemento esistente con tool di disegno → seleziona invece di disegnare** (comportamento standard di tutte le app grafiche)
- **Doppio click su callout** → riapre editing testo

### Stencil UI (36 totali)
- 5 categorie: Controlli, Form, Testi, Layout, Contenuti
- Filtro per categoria (combo box) + ricerca smart con **keywords/alias** (cercare "btn" trova "Pulsante primario")
- Thumbnail con cache
- Auto-scale al canvas (`target_w = max(160, scene_w * 0.14)`)
- Tooltip mostra le keywords associate

### Edit handles
- 4 corner handles (resize uniforme) + 1 rotation handle
- Frecce: 2 endpoint handle (giallo/arancione)
- Curve: 2 endpoint + 1 control point centrale (azzurro, più grande)
- Scorciatoie tastiera: `+`/`-` scale, `[`/`]` rotate ±5° (Shift = ±15°), `R` reset

### Context menu sugli item
- Aggiungi/Modifica/Rimuovi descrizione (con dialog word-wrap)
- **🎨 Cambia colore…** (QColorDialog, propaga ricorsivamente sui group, preserva alpha dei riempimenti)
- **📏 Cambia spessore…** (1-50px)
- **🌫 Opacità…** (5-100%)
- Ruota ±90°, Reset rotazione/scala
- Duplica, Porta in primo piano/sfondo
- Elimina
- Per tabelle: aggiungi/rimuovi riga/colonna (sopra le altre voci)

### Task panel (lato destro)
- Tab "Da fare" / "Completati" con thumbnail 80×60
- **Checkbox visibile per selezione multipla** + sync con Ctrl+click/Shift+click
- Context menu intelligente: 1 elemento → menu legacy; N elementi → batch ("📋 Copia per Claude (N)", "Copia path (N)", "Marca completati (N)", "Elimina (N)")
- Selection-aware: i pulsanti toolbar **"Copia path"** e **"Copia per Claude"** rispettano la selezione del panel
- `multi_copy_for_claude` produce un formato lista-di-file che Claude Code parsa correttamente

### Claude integration
- `app/companion_md.py`: scrive `<file>.md` accanto al PNG con descrizioni callout e coordinate normalizzate
- `app/storage.py`: status `in_progress` + `mark_in_progress`, gestione `.md` in move/delete
- `claude_handoff_text(task, template)` con placeholder `{png}`, `{description}`, `{md}`
- CLI `sb` (`app/cli.py` + `sb.bat`): comandi `next`, `peek`, `pending`, `done`, `md` per Claude Code da terminale
- Multi-task: formato chiaro per Claude (path nudi numerati + descrizione indentata)
- Feedback visivo: pulsanti diventano **"✓ Copiato!"** verde per 1.5s, status bar mostra preview del testo

### Capture
- Countdown 0-10s configurabile (badge gigante in overlay)
- `F12` cattura schermo intero immediato
- Badge dimensioni live durante drag dell'area

### Robustness e fix subtili
- Word-wrap `WrapAtWordBoundaryOrAnywhere` nel dialog descrizione (gestisce anche stringhe senza spazi)
- Ctrl+V scattare sempre con `ApplicationShortcut` (non viene "mangiato" dal canvas o da text item attivo)
- Paste robusto: 5 strade in cascata (QImage, QPixmap, raw bytes PNG/BMP/JPEG, URL)
- Export PNG include item che escono dallo `sceneRect` originario (commenti laterali non vengono più tagliati)
- Auto-resize del callout/commento collegato in altezza per contenere il testo
- Focus fix robusto sui group container (override `mousePressEvent` su `TableItem`, `_CalloutGroup`, `LinkedCommentItem` per dare priorità al text item interno)

### Distribuzione
- README.md riscritto v0.3 con tutte le feature
- ROADMAP.md (questo file)
- LICENSE MIT
- `.gitignore` (esclude .venv, screenshots personali, cache, settings.ini)
- Repo pubblico https://github.com/danielegabrovec/screenshot-bridge
- Pacchetto zip ~90 KB pronto per distribuzione su WhatsApp/email

---

## 📋 Prossime sessioni

### 🔴 Priorità ALTA

1. **`QUndoStack` vero** (rimandato dal piano originale)
   - Sostituire `_undo_stack` / `_redo_stack` (liste Python) con `QUndoStack`
   - Comandi: `AddItemCommand`, `RemoveItemCommand`, `MoveItemCommand` (con `mergeWith` per drag continui), `TransformItemCommand`, `ChangeDescriptionCommand`, `ChangeZOrderCommand`, `DuplicateItemCommand`, `ChangeColorCommand`, `ChangeThicknessCommand`
   - Connettere `cleanChanged` al titolo finestra (badge "modificato" `*`)
   - **Beneficio**: l'utente può annullare anche rotazioni, descrizioni, z-order, eliminazioni multiple, cambi colore/spessore — oggi sono permanenti

2. **System Tray Icon + hotkey globale**
   - `QSystemTrayIcon` con menu: Mostra/Cattura area/Cattura fullscreen/Incolla/Esci
   - Click sinistro = toggle finestra, doppio click = cattura area (configurabile)
   - Conteggio task pending nel menu
   - `closeEvent` minimizza a tray invece di chiudere
   - **Beneficio**: cattura sempre disponibile senza tenere la finestra aperta

3. **Snap intelligente + smart guides**
   - `app/snap.py` con `compute_snap(rect, candidates, threshold=6.0)` → `SnapResult(dx, dy, guides)`
   - Linee guida ciano `#06b6d4` durante il drag, snap a {left, hcenter, right} × {top, vcenter, bottom}
   - Toggle `G` + voce *Visualizza › Snap intelligente*
   - **Beneficio**: allineare gli stencil diventa banale

### 🟡 Priorità MEDIA

4. **Commento collegato — rifare meglio** (è stato nascosto dalla toolbar perché problematico)
   - Maniglie di resize dedicate sul body (oggi le maniglie generic prendono anche la linea e l'anchor, non si capisce cosa si sta ridimensionando)
   - Possibilità di **ancorare** l'anchor a un item della scena (non solo a coord scene): quando l'item-target si muove, la linea segue
   - Più indicatori visivi: punta dell'anchor highlight quando il commento è selezionato
   - Riattivare il pulsante in `main_window._build_toolbar` quando funziona bene

5. **Edge handles NSEW** (resize non uniforme)
   - 4 handle aggiuntivi in `EditHandleManager._build_generic_handles`
   - `QTransform.scale(sx, sy)` con pivot = lato opposto
   - Disabilitati quando l'item è ruotato (vincolo matematico)

6. **Preview hover grande sugli stencil**
   - `_StencilPreviewPopup(QFrame)` con `QGraphicsView` 400×220
   - `eventFilter` su `_DraggableStencilList`: timer 300ms su hover
   - **Beneficio**: i dettagli degli stencil sono leggibili senza dropparli prima

7. **Cattura finestra attiva** (`Ctrl+Alt+S`)
   - `app/window_enum.py` con `pywin32` opzionale: enum top-level + active window rect
   - Fallback no-op senza pywin32 (menu greyed)

### 🟢 Priorità BASSA / nice-to-have

8. Zoom-pixel loupe durante cattura area (`_ZoomLoupe(QLabel)` 120×120, zoom 4× sotto il cursore)
9. Snap-to-window edges durante cattura (enumera rect delle finestre top-level)
10. Watch mode CLI (`sb watch` con polling/observe di `da-fare/`, stampa il path al cambio)
11. Drag-reorder + icona badge nei task panel (pallino arancione su `in_progress`)
12. Export multi-formato: SVG (vector dello scene), PDF, template salvabili (canvas state → JSON)
13. i18n: stringhe italiane in `.qm` traducibile (EN/FR/ES)
14. Maniglie dedicate per la tabella (non scalare le celle con setScale, ma ridimensionare il rect interno preservando il testo)
15. Allineamento e distribuzione automatica della selezione multipla nel canvas (Figma-like)

---

## Convenzioni mantenute (NON rompere)

- `DockWidgetClosable` mai abilitato sui dock di feature critiche
- `painter.save()/restore()` attorno al disegno di background prima di delegare a `super().paint()`
- `ItemIgnoresTransformations` su decorazioni (handle, callout, frame)
- `_flash_items` set come "exclude from export"
- Scaling proporzionale stencil: `target_w = max(160, scene_w * 0.14)`, clamp 1-4×
- **Palette wireframe di `stencils.py` (OUTLINE/ACCENT/MUTED) NON dipende dal theme host** — gli stencil sono UI dentro l'UI, voluti coerenti indipendentemente dal dark/light dell'app host
- `_DescriptionCallout` resta nei colori storici (testo nero su bianco): finisce nel PNG esportato e deve essere leggibile a prescindere dal tema dell'app
- Override `mousePressEvent` sui group container (TableItem, _CalloutGroup, LinkedCommentItem) per dare priorità ai text items editabili — senza, il group movable cattura il click e il text non riceve mai focus
- Ctrl+V come `ApplicationShortcut` per essere immune al focus capture da text item attivi
- Tutte le copie verso Claude (toolbar pulsanti + context menu) sono **selection-aware** e usano `selected_tasks_active_tab()` come fonte unica
