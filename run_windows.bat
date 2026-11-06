@echo off
REM Jalankan script repo ini dengan Python dari venv (BUKAN python3).
REM Pakai: run_windows.bat <script.py> [argumen...]
REM Contoh: run_windows.bat login_csv.py --headed
REM          run_windows.bat auto.py --mode random --max-rounds 2
setlocal
cd /d "%~dp0"

if "%~1"=="" (
  echo Pakai: run_windows.bat ^<script.py^> [argumen...]
  echo Contoh: run_windows.bat login_csv.py --headed
  echo         run_windows.bat auto.py --mode random --max-rounds 2
  pause
  exit /b 1
)

if not exist venv\Scripts\python.exe (
  echo venv belum ada. Jalankan dulu: setup_windows.bat
  pause
  exit /b 1
)

call venv\Scripts\activate.bat
python %*
pause
