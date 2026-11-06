@echo off
rem Starts KAIRO with a console window so you can watch the Prisma / Gemini / Timbre log.
cd /d "%~dp0"
.venv\Scripts\python -m echo.app
