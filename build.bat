@echo off
rem Full Auto 360 - double-click to build the PC version.
rem Gets the latest project files from GitHub, then runs scripts\build-windows.ps1.
setlocal
cd /d "%~dp0"
title Full Auto 360 - build

if exist ".git" (
  where git >nul 2>nul && (
    echo Updating project files from GitHub...
    git pull --ff-only
    echo.
  )
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build-windows.ps1" %*
exit /b %errorlevel%
