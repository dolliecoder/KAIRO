@echo off
rem Builds the packaged Windows app into dist\KAIRO (takes a few minutes). Then: dist\KAIRO\KAIRO.exe --selftest
cd /d "%~dp0"
.venv\Scripts\python -m PyInstaller --noconfirm --clean --name KAIRO --windowed --icon assets\kairo.ico --paths . ^
  --collect-all sqlite_vec --collect-all _sounddevice_data --collect-all tzdata ^
  --copy-metadata apscheduler --collect-submodules apscheduler --collect-submodules sqlalchemy.dialects ^
  --hidden-import pynput.keyboard._win32 --hidden-import pynput.mouse._win32 --hidden-import pystray._win32 ^
  --add-data "assets\phrases;phrases" --hidden-import echo.selftest run_app.py
