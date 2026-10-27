@echo off
REM Double-click to run the whole analysis on Windows.
REM Finds Anaconda/Python, installs duckdb if missing, runs src\run_analysis.py, log -> output\run_log.txt
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
if exist output\RUNNING.lock (
  echo [INFO] Analysis is already running in another window. Close this window.
  pause & exit /b 0
)
if not exist output mkdir output
echo running > output\RUNNING.lock

set "PY="
for %%D in ("%USERPROFILE%\anaconda3" "%USERPROFILE%\miniconda3" "%LOCALAPPDATA%\anaconda3" "%PROGRAMDATA%\anaconda3" "%PROGRAMDATA%\Anaconda3" "C:\anaconda3" "D:\anaconda3" "D:\Anaconda3") do (
  if not defined PY if exist "%%~D\python.exe" set "PY=%%~D\python.exe"
)
if not defined PY for /f "delims=" %%P in ('where python 2^>nul') do if not defined PY set "PY=%%P"
if not defined PY (
  echo [ERROR] Python not found. > output\run_log.txt
  echo [ERROR] Python not found. Please install Anaconda.
  del output\RUNNING.lock 2>nul
  pause & exit /b 1
)
echo Using Python: %PY%
echo Using Python: %PY% > output\run_log.txt

"%PY%" -c "import duckdb" 2>nul || (
  echo Installing duckdb ...
  "%PY%" -m pip install duckdb >> output\run_log.txt 2>&1 || "%PY%" -m pip install duckdb -i https://pypi.tuna.tsinghua.edu.cn/simple >> output\run_log.txt 2>&1
)

set ENGINE=duckdb
"%PY%" -c "import duckdb" 2>nul || set ENGINE=sqlite
echo Engine: %ENGINE%
"%PY%" -u src\run_analysis.py --engine %ENGINE% > output\run_log_main.txt 2>&1
echo EXIT_CODE=%ERRORLEVEL% >> output\run_log_main.txt
del output\RUNNING.lock 2>nul
type output\run_log_main.txt
echo.
echo ===== Done. See output\report.md and output\charts =====
pause
