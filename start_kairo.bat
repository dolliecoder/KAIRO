@echo off
rem Starts KAIRO in the background (tray icon only, no console window). Log: data\echo.log
start "" "%~dp0.venv\Scripts\pythonw.exe" -m echo.app
