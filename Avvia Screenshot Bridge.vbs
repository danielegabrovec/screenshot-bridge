' Launcher silenzioso per Screenshot Bridge.
' Doppio click: avvia l'app senza terminale visibile.
' Se il venv non esiste, esegue run.bat (con finestra visibile) per il setup
' iniziale e poi parte invisibile.

Option Explicit

Dim sh, fso, folder, pythonw, mainpy, runbat

Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

folder  = fso.GetParentFolderName(WScript.ScriptFullName)
pythonw = folder & "\.venv\Scripts\pythonw.exe"
mainpy  = folder & "\main.py"
runbat  = folder & "\run.bat"

If fso.FileExists(pythonw) Then
    ' Avvio normale: nessuna finestra, processo separato.
    sh.Run """" & pythonw & """ """ & mainpy & """", 0, False
Else
    ' Primo avvio: lascia che run.bat installi le dipendenze (visibile),
    ' poi run.bat avvia gia' l'app con pythonw e termina.
    sh.Run """" & runbat & """", 1, True
End If
