@echo off
chcp 65001 >nul
echo ========================================
echo   FScr — Build Script
echo ========================================
echo.

echo [1/3] Installing dependencies...
python -m pip install mss Pillow pywin32 pystray keyboard --quiet

echo.
echo [2/3] Building with PyInstaller...
python -m PyInstaller --onefile --noconsole --name "FScr" --distpath "dist_noconsole" FScr.py

echo.
echo [3/3] Building console version...
python -m PyInstaller --onefile --name "FScr" --distpath "dist_console" FScr.py

echo.
echo ========================================
echo   Build Complete!
echo ========================================
echo.
echo Executables:
echo   dist_noconsole\FScr.exe
echo   dist_console\FScr.exe
echo.
pause
