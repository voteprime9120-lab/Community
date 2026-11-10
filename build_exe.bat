@echo off
cd /d "%~dp0"
python -m pip install --upgrade pyinstaller pillow pygame
python -m PyInstaller --onefile --noconsole --clean --name DeckLauncher --icon assets\icon.ico --add-data "assets;assets" deck_launcher.py
echo.
echo Done: dist\DeckLauncher.exe
pause
