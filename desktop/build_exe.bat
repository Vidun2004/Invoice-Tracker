@echo off
REM Build InvoiceTracker.exe with embedded Supabase + icon
cd /d "%~dp0"
call venv\Scripts\activate 2>nul
python build_embed.py || exit /b 1
python -m PyInstaller --noconfirm --clean --onefile --windowed --name InvoiceTracker --icon assets\icon.ico --add-data "assets;assets" --collect-all customtkinter --collect-all tkcalendar main.py || exit /b 1
echo.
echo DONE - dist\InvoiceTracker.exe (no .env needed beside it)
pause
