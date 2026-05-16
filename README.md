# Screenshot Bridge

App desktop per catturare, annotare e passare screenshot a **Claude Code** da terminale, senza
mai uscire dal flusso di lavoro: cattura → annota con stencil UI / frecce / redact → un click
per copiare il path già formattato per il terminale.

![](docs/screenshot-placeholder.png) <!-- aggiungere screenshot quando disponibile -->

## Novità v0.2

- **Temi DARK e LIGHT** unificati: toolbar, dock, menu, status bar e canvas finalmente coerenti
  fra loro. Si alternano dal pulsante sole/luna in toolbar o dal menu *Visualizza › Tema*.
- **Status bar ricca**: tool attivo, colore (con badge), spessore e zoom % sempre visibili.
- **Persistenza preferenze**: posizione finestra, dock, ultimo tool, colore, spessore e tema
  vengono ripristinati ad ogni avvio (file `%LOCALAPPDATA%\ScreenshotBridge\settings.ini`).
- **Modificatori da tastiera durante il disegno**:
  - `Shift` → vincoli (quadrato, cerchio, angoli a 45°, linea retta in penna)
  - `Alt` → forma disegnata dal centro
  - `Ctrl + ruota mouse` → zoom canvas (la % appare nella status bar)
- **3 nuovi tool**: *Redact* (privacy: copre un'area con un rettangolo "REDACTED"),
  *Evidenziatore rettangolare* (rect semi-trasparente), *Stamp numerico* (cerchi numerati
  1, 2, 3… per tutorial passo-passo).
- **+12 stencil**: badge, progress bar, slider, file upload, calendar, breadcrumb, stepper,
  data table, chart bar, chart line, tooltip, toast notification.
- **Companion `.md`**: salvando un task, accanto al PNG viene scritto un file `.md` con
  descrizione, coordinate normalizzate e annotazioni con descrizione — pronto da leggere
  per Claude.
- **CLI `sb`** (vedi sotto) per integrare Claude Code via terminale.
- **Capture+**: countdown configurabile (0–10s) e cattura schermo intero con `F12`.
- **Cattura overlay** con badge dimensioni in tempo reale.
- **Template handoff** personalizzabile (placeholder `{png}`, `{description}`, `{md}`).

## Avvio rapido

**Uso quotidiano:** doppio click su **`Avvia Screenshot Bridge.vbs`** — l'app parte senza
finestra di terminale.

**Primo avvio:** doppio click su `run.bat`. Crea il venv e installa PyQt6, Pillow e qtawesome
(mostra il terminale solo finché installa). Al termine lancia l'app.

Setup manuale:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pythonw main.py
```

## Come si usa

1. **Cattura un'immagine** in uno di questi modi:
   - `Ctrl+Shift+S` → overlay fullscreen, trascini per selezionare l'area
   - `F12` → cattura immediata di tutto lo schermo
   - `Win+Shift+S` (Snipping di Windows) → torna nell'app → `Ctrl+V`
   - Trascini un PNG/JPG dentro la finestra dell'app
   - Pulsante **Apri file…** per caricare da disco

2. **Annota** scegliendo uno strumento in toolbar:
   - **Freccia**, **Rettangolo**, **Cerchio**, **Testo**, **Penna**, **Evidenziatore**
   - **Evid. rettangolo** (rect semi-trasparente per blocchi interi)
   - **Redact** per privacy: copre un'area con un rettangolo "REDACTED"
   - **Numero**: stamp circolari numerati progressivi per tutorial step-by-step
   - Modificatori: `Shift` vincola (quadrato/cerchio/45°), `Alt` disegna dal centro
   - Colore e spessore sono nella stessa toolbar

3. **Stencil UI** dal dock laterale (30 elementi):
   - **Trascina** sul canvas per inserirlo nel punto del drop
   - **Click** sullo stencil per inserirlo al centro
   - Gli stencil si scalano in proporzione al canvas (su un 1920×1080 un bottone è ~270px)
   - Cerca per nome con il campo in alto al dock

4. **Modifica un elemento dopo averlo inserito**:
   - Selezionalo (click) → compaiono maniglie agli angoli e una di rotazione
   - **Tasto destro** → menu rapido: descrizione, ruota ±90°, duplica, z-order, elimina
   - **Frecce**: maniglie arancioni agli endpoint per cambiare direzione/lunghezza

5. **Salva** con `Ctrl+S`. Ti chiede una descrizione breve (es. "sposta bottone login a destra")
   e crea in `screenshots/da-fare/`:
   - `<timestamp>_<slug>.png` — l'immagine annotata
   - `<timestamp>_<slug>.json` — metadati (descrizione, data, stato)
   - `<timestamp>_<slug>.md` — companion con annotazioni e coordinate per Claude

6. **Passa a Claude Code**:
   - **Copia path** → solo il percorso assoluto
   - **Copia per Claude** → markdown formattato (template configurabile da
     *Impostazioni › Template handoff Claude*). Default:
     ```
     Vedi screenshot: C:\...\2026-05-16_143022_sposta-bottone.png — Da fare: sposta bottone login
     ```
   Incolla nel terminale di Claude Code con `Ctrl+V`.

7. **Quando Claude ha applicato la modifica**: tasto destro sul task → *Marca come completato*
   → file spostato in `screenshots/completati/`.

## CLI `sb` (integrazione Claude Code)

Lo script `sb.bat` permette a Claude Code di pescare/marcare task senza interagire con la GUI.

```bat
sb pending       :: JSON con tutti i task in da-fare/ (id, path, descrizione, .md)
sb peek          :: stampa solo il path del prossimo task
sb next          :: marca il prossimo task come in_progress e stampa il path
sb done <path>   :: sposta il task in completati/
sb md <path>     :: stampa il companion .md (se esiste)
```

Esempio di flusso end-to-end con Claude:

```
> sb next
C:\...\screenshots\da-fare\2026-05-16_143022_sposta-bottone.png

> sb md C:\...\screenshots\da-fare\2026-05-16_143022_sposta-bottone.png
# sposta bottone login a destra
- **PNG:** `2026-05-16_143022_sposta-bottone.png`
- **Dimensioni scena:** 1920×1080 px
## Annotazioni con descrizione
1. **freccia** @ ~(72.3%, 41.5%) — qui ci va il nuovo bottone
```

## Scorciatoie

| Scorciatoia | Azione |
|-------------|--------|
| `Ctrl+V` | Incolla immagine da clipboard |
| `Ctrl+Shift+S` | Cattura area dello schermo |
| `F12` | Cattura schermo intero |
| `Ctrl+S` | Salva in `da-fare/` |
| `Ctrl+O` | Apri file… |
| `Ctrl+Z` / `Ctrl+Y` | Annulla / Ripristina |
| `Canc` | Elimina selezione |
| `+` / `-` | Scala elemento selezionato (Shift = più veloce) |
| `[` / `]` | Ruota ±5° (Shift = ±15°) |
| `R` | Reset rotazione/scala |
| `Shift` (durante drag) | Vincolo: quadrato, cerchio, 45°, linea retta |
| `Alt` (durante drag) | Disegna dal centro |
| `Ctrl + ruota mouse` | Zoom canvas |
| `Ctrl+Q` | Esci |

Vedi anche *Aiuto › Scorciatoie da tastiera* dentro l'app.

## Struttura cartelle

```
screenshot-bridge/
├── main.py                       # entry point GUI
├── sb.bat                        # CLI per Claude Code
├── requirements.txt              # PyQt6, Pillow, qtawesome
├── Avvia Screenshot Bridge.vbs   # launcher silenzioso quotidiano
├── run.bat                       # setup + lancio (mostra console al primo avvio)
├── app/
│   ├── main_window.py            # toolbar doppia + menu + dock + statusbar ricca
│   ├── canvas_editor.py          # QGraphicsView, welcome dinamico, export PNG
│   ├── edit_handles.py           # maniglie resize/rotate, palette dinamica
│   ├── capture.py                # overlay cattura + countdown + fullscreen
│   ├── storage.py                # save/list/mark_done/mark_in_progress/delete
│   ├── companion_md.py           # export .md companion con coordinate
│   ├── cli.py                    # CLI `sb` per Claude Code
│   ├── settings_store.py         # QSettings wrapper tipato (INI in %LOCALAPPDATA%)
│   ├── theme.py                  # ThemeManager (DARK/LIGHT) + qss_for() + icon()
│   ├── stencils.py               # 30 stencil UI (5 categorie)
│   ├── stencil_panel.py          # dock catalogo con drag + ricerca
│   ├── task_panel.py             # tab Da fare/Completati + menu contestuale
│   └── tools/                    # base_tool, arrow, shape, text, pen, blur, number_stamp
└── screenshots/
    ├── da-fare/                  # PNG + JSON + MD in attesa
    └── completati/               # spostati qui dopo "marca completato"
```

## Stack

Python 3.10+ con PyQt6 ≥ 6.6, Pillow ≥ 10, qtawesome ≥ 1.3.
Tutto offline, nessuna dipendenza di rete.

## Cosa si può ancora implementare

Vedi [ROADMAP.md](ROADMAP.md) per la lista dettagliata delle prossime sessioni:

- **Snap intelligente** + smart guides ciano tra item della scena
- **Edge handles** NSEW per resize non uniforme
- **QUndoStack** vero con macro (descrizione/z-order/transform annullabili)
- **System tray** con hotkey globale (cattura ad app minimizzata)
- **Preview hover grande** sugli stencil + cache thumbnail
- **Snap-to-window** durante la cattura area + zoom-pixel loupe
- **Cattura finestra attiva** (Ctrl+Alt+S, richiede `pywin32`)
- **Watch mode** del CLI `sb` per pipe verso Claude in tempo reale

## Licenza

MIT (vedi `LICENSE`).
