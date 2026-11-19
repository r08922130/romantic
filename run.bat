@echo off
rem  Double-click to start (opens the scene / cat menu).
rem  Keep this file ASCII-only: cmd.exe misreads non-ASCII text after chcp 65001.
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
    py -3 main.py --menu %*
) else (
    python main.py --menu %*
)
if errorlevel 1 pause
