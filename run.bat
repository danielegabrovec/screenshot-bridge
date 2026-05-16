@echo off
setlocal
cd /d "%~dp0"

REM Preferiamo Python 3.13 / 3.12 (PyQt6 ha wheel piu' stabili). Fallback a 3.14, poi a "python".
set "PY_CMD="
where py >nul 2>&1
if not errorlevel 1 (
    py -3.13 -c "import sys" >nul 2>&1 && set "PY_CMD=py -3.13"
    if not defined PY_CMD py -3.12 -c "import sys" >nul 2>&1 && set "PY_CMD=py -3.12"
    if not defined PY_CMD py -3.14 -c "import sys" >nul 2>&1 && set "PY_CMD=py -3.14"
)
if not defined PY_CMD set "PY_CMD=python"

if not exist ".venv\Scripts\pythonw.exe" (
    echo [Screenshot Bridge] Primo avvio: creo ambiente virtuale con %PY_CMD% ...
    %PY_CMD% -m venv .venv
    if errorlevel 1 (
        echo ERRORE: impossibile creare venv. Verifica che Python sia installato.
        pause
        exit /b 1
    )
    echo [Screenshot Bridge] Aggiorno pip e installo dipendenze...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ERRORE: installazione dipendenze fallita.
        pause
        exit /b 1
    )
)

REM Lancia con pythonw.exe (no console) e termina subito il cmd.
REM `start "" /B` evita di aprire una nuova finestra; pythonw stesso non ne crea.
start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0main.py"
exit /b 0
