@echo off
cd /d "%~dp0"
python -m pip install --upgrade pyinstaller pillow pygame
python -m PyInstaller --onefile --noconsole --name DeckLauncher deck_launcher.py
echo.
echo Done: dist\DeckLauncher.exe
pause
