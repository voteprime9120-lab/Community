@echo off
cd /d "%~dp0"
python -m pip install --upgrade pyinstaller pillow pygame
python -m PyInstaller --onefile --noconsole --name DeckLauncher deck_launcher.py
echo.
echo dist\DeckLauncher.exe 가 만들어졌습니다.
pause
