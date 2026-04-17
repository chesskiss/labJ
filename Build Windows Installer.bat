@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

where node >nul 2>&1
if errorlevel 1 (
  echo [LabJ] Node.js is not installed.
  pause
  exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
  echo [LabJ] npm is not available.
  pause
  exit /b 1
)

where py >nul 2>&1
if errorlevel 1 (
  where python >nul 2>&1
)
if errorlevel 1 (
  echo [LabJ] Python 3.10+ is required to bundle the desktop runtime.
  pause
  exit /b 1
)

if not exist ".env" (
  echo [LabJ] Missing .env in repo root. Create .env before building installer.
  pause
  exit /b 1
)

cd desktop
call npm install
if errorlevel 1 (
  echo [LabJ] npm install failed.
  pause
  exit /b 1
)

call npm run dist:win
if errorlevel 1 (
  echo [LabJ] Windows installer build failed.
  pause
  exit /b 1
)

echo [LabJ] Done. Installer is in desktop\release\
pause
