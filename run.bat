@echo off
rem  Double-click to start (opens the scene / cat menu).
rem  Keep this file ASCII-only: cmd.exe misreads non-ASCII text after chcp 65001.
rem
rem  The window is maximised (--maximize), so the scene is drawn at its
rem  biggest size. Windows Terminal does not let a program resize its window
rem  (and on Windows 11 a double-clicked .bat opens there by default), so
rem  this always re-opens itself in the classic console window (conhost).
if not defined ROMANCE_CONHOST (
    set ROMANCE_CONHOST=1
    start "" conhost.exe cmd.exe /c call "%~f0" %*
    if not errorlevel 1 exit /b
)
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
    py -3 main.py --menu --maximize %*
) else (
    python main.py --menu --maximize %*
)
if errorlevel 1 pause
