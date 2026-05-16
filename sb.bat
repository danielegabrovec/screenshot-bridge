@echo off
REM CLI wrapper per Screenshot Bridge.
REM Permette a Claude Code di chiamare:
REM   sb next      -> stampa il path del prossimo task pending, lo marca in_progress
REM   sb peek      -> stampa il path senza modificare lo stato
REM   sb pending   -> JSON con tutti i task in da-fare/
REM   sb done <p>  -> sposta in completati/
REM   sb md <p>    -> stampa il companion .md (se esiste)

setlocal
set "SCRIPT_DIR=%~dp0"
set "PYW=%SCRIPT_DIR%.venv\Scripts\python.exe"
if not exist "%PYW%" set "PYW=python"
"%PYW%" -m app.cli %*
endlocal
