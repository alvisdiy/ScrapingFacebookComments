@echo off
REM Setup sekali di Windows: bikin venv (kalau belum ada), install
REM dependensi, install browser Playwright. Jalankan dengan double-klik
REM atau dari PowerShell/CMD di folder repo ini.
setlocal
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
  echo Python tidak ditemukan di PATH. Install Python 3 dari python.org
  echo (centang "Add Python to PATH" saat install), lalu jalankan lagi.
  pause
  exit /b 1
)

if not exist venv\Scripts\python.exe (
  echo Membuat venv...
  python -m venv venv
  if errorlevel 1 (
    echo Gagal membuat venv.
    pause
    exit /b 1
  )
)

call venv\Scripts\activate.bat
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo pip install gagal.
  pause
  exit /b 1
)
python -m playwright install chromium
if errorlevel 1 (
  echo Install Chromium gagal - tidak apa-apa kalau Google Chrome sudah
  echo terinstall, script otomatis fallback ke Chrome sistem.
)
python -c "import playwright; print('Cek: playwright OK')"
echo.
echo Setup selesai. Jalankan: run_windows.bat login_csv.py --headed
echo (atau script lain, mis. run_windows.bat auto.py --mode random)
pause
