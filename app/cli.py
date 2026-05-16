"""CLI `sb` per integrazione Claude Code.

Uso da terminale:
    sb next      # marca il prossimo task come in_progress e stampa il path
    sb peek      # stampa il path del prossimo task senza modificare lo stato
    sb pending   # JSON con tutti i task pending/in_progress
    sb done <path>  # marca completato
    sb md <path>    # stampa il companion .md (se esiste)

Il comando si registra in `pyproject.toml` come entry point oppure è
invocabile via `python -m app.cli`. Non importa PyQt: è pensato per
girare in un terminale dove Claude Code sta lavorando.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Sequence

from . import storage


def cmd_next() -> int:
    """Prende il task pending più vecchio, lo marca in_progress, stampa il path."""
    tasks = storage.list_pending()
    # Filtra fuori quelli già in_progress (preferisci pending puri).
    pure_pending = [t for t in tasks if t.status == "pending"]
    if not pure_pending:
        # Se non ci sono pending puri ma ci sono in_progress, ritorna il più vecchio
        if tasks:
            t = tasks[-1]
            print(str(t.png_path))
            return 0
        sys.stderr.write("Nessun task pending.\n")
        return 1
    # `list_pending` ordina dal più recente al più vecchio; vogliamo il più vecchio (FIFO)
    task = pure_pending[-1]
    storage.mark_in_progress(task.png_path)
    print(str(task.png_path))
    return 0


def cmd_peek() -> int:
    tasks = storage.list_pending()
    if not tasks:
        sys.stderr.write("Nessun task pending.\n")
        return 1
    task = tasks[-1]
    print(str(task.png_path))
    return 0


def cmd_pending() -> int:
    tasks = storage.list_pending()
    out = [
        {
            "png": str(t.png_path),
            "description": t.description,
            "created_at": t.created_at,
            "status": t.status,
            "md": str(t.md_path) if t.md_path.exists() else None,
        }
        for t in tasks
    ]
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_done(path: str) -> int:
    p = Path(path)
    if not p.exists():
        sys.stderr.write(f"File non trovato: {p}\n")
        return 1
    storage.mark_done(p)
    print(f"OK: {p.name} → completati/")
    return 0


def cmd_md(path: str) -> int:
    p = Path(path)
    md = p.with_suffix(".md")
    if not md.exists():
        sys.stderr.write(f"Companion .md non trovato per {p.name}\n")
        return 1
    sys.stdout.write(md.read_text(encoding="utf-8"))
    return 0


def cmd_help() -> int:
    print(__doc__ or "")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args or args[0] in {"-h", "--help", "help"}:
        return cmd_help()
    cmd = args[0]
    rest = args[1:]
    try:
        if cmd == "next":
            return cmd_next()
        if cmd == "peek":
            return cmd_peek()
        if cmd == "pending":
            return cmd_pending()
        if cmd == "done":
            if not rest:
                sys.stderr.write("Uso: sb done <path>\n")
                return 2
            return cmd_done(rest[0])
        if cmd == "md":
            if not rest:
                sys.stderr.write("Uso: sb md <path>\n")
                return 2
            return cmd_md(rest[0])
    except Exception as exc:  # pragma: no cover - safety
        sys.stderr.write(f"Errore: {exc}\n")
        return 3
    sys.stderr.write(f"Comando sconosciuto: {cmd}\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
