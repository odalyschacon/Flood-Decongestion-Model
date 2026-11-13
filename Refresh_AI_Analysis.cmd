@echo off
cd /d "%~dp0"
set "FLOODLAB_PYTHON=%USERPROFILE%\anaconda3\envs\gb10\python.exe"
if not exist "%FLOODLAB_PYTHON%" (
  echo Activate your existing Python environment and run python api_evidence.py --refresh.
  pause
  exit /b 1
)
"%FLOODLAB_PYTHON%" api_evidence.py --refresh
if errorlevel 1 (
  echo API analysis did not complete. Existing results are preserved.
  pause
  exit /b 1
)
"%FLOODLAB_PYTHON%" run_analysis.py
pause
