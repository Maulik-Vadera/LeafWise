@echo off
setlocal
cd /d "%~dp0"
py -3.12 --version >nul 2>&1
if errorlevel 1 (
  echo Leafwise needs Python 3.12 64-bit.
  echo Install it from https://www.python.org/downloads/windows/
  echo You can keep other Python versions installed.
  echo Then double-click this file again.
  pause
  exit /b 1
)
py -3.12 scripts\bootstrap.py
if errorlevel 1 (
  echo.
  echo Leafwise stopped. Read the message above and START_HERE.md.
  pause
  exit /b 1
)
