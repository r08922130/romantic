@echo off
rem  Double-click: the Fourier epicycles Christmas tree in its own window
rem  (the GUI version - run.bat is the terminal ASCII version).
rem  Keep this file ASCII-only.
cd /d "%~dp0"
where pythonw >nul 2>nul
if errorlevel 1 (
    start "" pyw -3 fourier_gui\app.py %*
) else (
    start "" pythonw fourier_gui\app.py %*
)
